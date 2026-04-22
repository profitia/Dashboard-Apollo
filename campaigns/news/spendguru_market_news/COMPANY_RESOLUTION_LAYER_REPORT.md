# COMPANY RESOLUTION LAYER REPORT — spendguru_market_news

**Data:** 2026-04-22
**Wersja:** v1
**Autor:** AI Copilot / Tomasz Uściński
**Podstawa:** Implementacja warstwy resolution po normalizacji nazw firm (2026-04-22)

---

## 1. Executive Summary

### Co wdrożono

Nową lekką warstwę Company Resolution Layer, która działa pomiędzy `entity_extractor` a `contact_finder` w pipeline'ie `spendguru_market_news`. Warstwa przyjmuje firmę wyekstrahowaną z artykułu, szuka kandydatów organizacyjnych w Apollo, ocenia ich dopasowanie i zwraca strukturyzowany wynik resolution.

### Jak działa warstwa

1. Pipeline wyciąga firmę z artykułu (entity_extractor, LLM lub heurystyka)
2. Jeśli toggle `use_company_resolution: true`, resolution layer:
   - Szuka organizacji w Apollo po nazwie canonical i source (max 2 zapytania, deduplikowane)
   - Ocenia każdego kandydata heurystycznie (comparison_key, name similarity, domain, industry)
   - Opcjonalnie weryfikuje stronę www kandydata (lekkie 8KB HTML)
   - Przekazuje ustrukturyzowany pakiet dowodów do LLM (do 5 kandydatów)
   - Podejmuje finalną decyzję na podstawie sumy confidence heurystycznej + korekty LLM
3. Wynik to `ResolutionResult` ze statusem: MATCH_CONFIDENT / MATCH_POSSIBLE / AMBIGUOUS_HOLD / NO_MATCH
4. Przy MATCH_CONFIDENT / MATCH_POSSIBLE: `resolved_company_name` i `resolved_domain` trafiają do `find_contacts_for_company`
5. Przy błędzie resolution layer: fallback do oryginalnej nazwy firmy (backward compatibility)

### Jakie ma ograniczenia

- Jakość zależy od pokrycia Apollo (firma musi być w bazie Apollo)
- Przy firmach z bardzo krótką lub bardzo generyczną nazwą — wysoki ryzyko false positive
- LLM ocenia kandydatów na podstawie opisów, nie widzi pełnych profili firm
- Website check jest opcjonalny i wolniejszy — domyślnie wyłączony
- `use_company_resolution: false` domyślnie — wymaga świadomego włączenia

---

## 2. Resolution Architecture

### Miejsce w pipeline

```
ArticleFetcher
     ↓
RelevanceScorer   (score_result: RelevanceResult)
     ↓
EntityExtractor   (company: CompanyInfo)
     ↓
[CompanyResolver] ← nowa warstwa (opcjonalna, toggle: use_company_resolution)
     ↓
ContactFinder     (używa resolved_company_name zamiast company.name)
     ↓
MessageGenerator
     ↓
SequenceBuilder
```

### Wejście do `resolve_company()`

| Parametr | Źródło w pipeline |
|----------|-------------------|
| `source_company_name` | `company.source_name` (nazwa z artykułu) |
| `canonical_name` | `company.canonical_name` (preferowana forma) |
| `comparison_key` | `company.name_normalized` (klucz dedup) |
| `article_title` | `article.title` |
| `article_lead` | `article.lead` |
| `article_body_excerpt` | `article.body[:600]` |
| `article_industry_context` | matchowane termy branżowe ze scorer (joined) |
| `article_purchase_context` | matchowane purchase terms ze scorer |
| `campaign_config` | z `_load_campaign_configs()` |

### Wyjście: `ResolutionResult`

```python
@dataclass
class ResolutionResult:
    resolved_company_name: str
    resolved_company_id: str | None
    resolved_domain: str | None
    resolution_confidence: float          # 0.0–1.0
    resolution_status: str                # MATCH_CONFIDENT | MATCH_POSSIBLE | AMBIGUOUS_HOLD | NO_MATCH
    resolution_reason: str
    candidate_summary: list[dict]         # lista kandydatów ze scorami
    requires_manual_review: bool
```

### Główne kroki w `resolve_company()`

1. `_collect_candidates()` — szuka org w Apollo po canonical + source name
2. `_score_candidate_heuristic()` — ocena każdego kandydata (0.0–1.0)
3. Opcjonalnie: `_fetch_website_signals()` + `_website_signal_score()`
4. `_llm_evaluate_candidates()` — LLM ocenia pakiet z dowodami
5. Finalna decyzja: MATCH_CONFIDENT / MATCH_POSSIBLE / AMBIGUOUS_HOLD / NO_MATCH

---

## 3. Candidate Matching Logic

### Sygnały heurystyczne (wagi sumaryczne do 1.0)

| Sygnał | Waga | Typ | Opis |
|--------|------|-----|------|
| `comparison_key` exact match | +0.45 | **twarda** | Kluczowy sygnał: `evrafish == evrafish` |
| `comparison_key` partial overlap (min 4 znaki) | +0.25 | twarda | Jeden zawiera drugi |
| Name similarity ≥ 0.90 | +0.20 | twarda | SequenceMatcher ratio ≥ 90% |
| Name similarity 0.70–0.90 | +0.10 | twarda | SequenceMatcher ratio 70–90% |
| Name similarity 0.50–0.70 | +0.05 | twarda | SequenceMatcher ratio 50–70% |
| Domain matches comparison_key | +0.20 | twarda | `evrafish.com` → `evrafish` |
| Domain matches canonical key | +0.15 | twarda | Fallback: canonical zamiast source |
| Industry keyword overlap | +0.05–0.10 | miękka | Wspólne słowa 4+ znaków |
| Apollo keywords in article | +0.02–0.05 | miękka | Keywords Apollo obecne w artykule |
| Website title/meta/h1 match | +0.04–0.10 | miękka | Opcjonalne, website_check=true |

### Co jest heurystyką

Wszystkie powyższe sygnały. Deterministyczne, przewidywalne, szybkie. Tworzą `heuristic_score` 0.0–1.0.

### Co jest oceniane przez LLM

LLM otrzymuje **pakiet dowodów** (nie surowe dane):

- Dla każdego z max 5 kandydatów: nazwa Apollo, domena, branża Apollo, słowa kluczowe, heuristic_score, sygnały
- Kontekst: source_company_name, canonical_name, branża artykułu, tytuł, lead, fragment

LLM odpowiada:
- `best_candidate_index`: numer 1–N (lub 0 jeśli żaden)
- `confidence_adjustment`: float −0.20 do +0.20 (korekta do heuristic_score)
- `rationale`: max 2 zdania

LLM nie może samodzielnie wybrać kandydata poza top heurystycznym jeśli wynik jest drastycznie słabszy (próg: 70% score topu).

---

## 4. Apollo Usage

### Endpoint

`POST /v1/mixed_companies/search` — przez `ApolloClient.search_organizations()` (istniejąca metoda).

Payload: `{"q_organization_name": "<query>", "per_page": 8}`

### Jak pobierani są kandydaci

1. Pierwsze zapytanie: `canonical_name` (preferred)
2. Drugie zapytanie: `source_company_name` (tylko jeśli różni się od canonical)
3. Wyniki scalane i deduplikowane po `org_id` (jeśli dostępne) lub `comparison_key` nazwy

Max kandydatów: 8 per zapytanie, max 2 zapytania → max 16 przed deduplication.

### Jakie dane organizacyjne są używane

| Pole Apollo | Zastosowanie |
|-------------|--------------|
| `name` | comparison_key + name similarity |
| `id` | deduplikacja, przekazywany jako `resolved_company_id` |
| `primary_domain` | domain match, website check |
| `industry` | industry overlap scoring |
| `keywords` | keyword context overlap |

---

## 5. Website Verification

### Czy została wdrożona

Tak, jako opcjonalna warstwa. Domyślnie wyłączona: `company_resolution_use_website_check: false`.

### Jak działa

1. `_fetch_website_signals(domain)` — pobiera max 8KB HTML z HTTPS
2. Parsuje: `<title>`, `<meta name="description">`, pierwszy `<h1>`
3. `_website_signal_score()` sprawdza:
   - Czy `comparison_key` pojawia się w połączonym tekście strony
   - Czy `canonical_name` pojawia się na stronie
   - Ile wspólnych słów (4+ znaki) ma strona z `article_industry_context`
4. Bonus do heuristic_score: +0.04 do +0.10 (max 3 sygnały × 0.04)

### Kiedy jest używana

Tylko gdy:
- `company_resolution_use_website_check: true` w campaign_config.yaml
- Kandydat ma `primary_domain` (nie pusty)
- Heuristic_score przed website check ≥ 0.25 (żeby nie weryfikować słabych kandydatów)

### Ograniczenia

- Timeout 5 sekund per strona → może spowolnić pipeline przy wielu kandydatach
- Może nie działać dla stron za CDN blokiem (403/429)
- 8KB może być za mało dla stron z heavy JS (SPA)

---

## 6. Decision Model

### Statusy decyzji

| Status | Warunek | Akcja pipeline |
|--------|---------|----------------|
| `MATCH_CONFIDENT` | `final_score >= 0.72` (domyślnie) | Przekaż `resolved_company_name` do contact_finder |
| `MATCH_POSSIBLE` | `final_score >= 0.45` | Przekaż `resolved_company_name` do contact_finder |
| `AMBIGUOUS_HOLD` | Top-2 kandydaci blisko score + obaj ≥ min_confidence + top < confident_threshold | `requires_manual_review=True`, brak sekwencji |
| `NO_MATCH` | Brak kandydatów z Apollo LUB best score < min_confidence | Pomiń artykuł |

### Confidence logic

```
final_confidence = heuristic_score + llm_adjustment (capped 0.0–1.0)
```

Gdzie `llm_adjustment` ∈ [−0.20, +0.20].

Przykład: heuristic=0.65, LLM adjustment=+0.10 → final=0.75 → MATCH_CONFIDENT.

### Warunek AMBIGUOUS

AMBIGUOUS_HOLD gdy jednocześnie:
1. Jest przynajmniej 2 kandydatów
2. Drugi kandydat ma score ≥ `min_confidence` (0.45)
3. Różnica między top a drugim < 0.15 punktu
4. Top score < `confident_threshold` (0.72)

Interpretacja: nie ma wyraźnego zwycięzcy — bezpieczniej wstrzymać.

### Manual review

- `AMBIGUOUS_HOLD` → `requires_manual_review=True`, artykuł zapisywany ze statusem `resolution_ambiguous`
- `NO_MATCH` → artykuł zapisywany ze statusem `resolution_no_match`, brak review (brak danych)

### Config thresholds

```yaml
company_resolution_min_confidence: 0.45        # dolna granica → MATCH_POSSIBLE
company_resolution_confident_threshold: 0.72   # górna granica → MATCH_CONFIDENT
```

---

## 7. Example Flows

### 7.1 Evra Fish → EvraFish

**Artykuł:** portalspozywczy.pl pisze "Evra Fish" (z spacją). Firma branduje się jako "EvraFish" (bez spacji).

**Krok 1 — entity_extractor:**
- `source_name = "Evra Fish"`
- `canonical_name = "Evra Fish"` (LLM nie zna brandingu)
- `comparison_key = "evrafish"` (make_comparison_key usuwa spację)

**Krok 2 — Apollo search:**
- Zapytanie 1: `"Evra Fish"` → może zwrócić "EvraFish" i inne ryby
- Zapytanie 2: (pominięte — source = canonical)

**Krok 3 — Heuristic scoring dla kandydata "EvraFish":**
- `comparison_key("EvraFish") = "evrafish"` == `comparison_key("Evra Fish") = "evrafish"` → **+0.45**
- Name similarity("Evra Fish", "EvraFish") ≈ 0.89 → **+0.10**
- Domain `evrafish.com` → `_domain_contains_key("evrafish.com", "evrafish")` = True → **+0.20**
- Industry: spożywczy/ryby overlap → **+0.05**
- **Suma: 0.80** → przed LLM już MATCH_CONFIDENT

**Krok 4 — LLM:**
- Pakiet: 1 silny kandydat "EvraFish" z score 0.80 i sygnałami
- LLM: `best_candidate_index=1, confidence_adjustment=+0.05, rationale="EvraFish matches exactly by comparison key and domain"`
- Final: 0.80 + 0.05 = 0.85 → **MATCH_CONFIDENT**

**Wynik:**
```
resolved_company_name = "EvraFish"
resolved_domain = "evrafish.com"
resolution_confidence = 0.85
resolution_status = "MATCH_CONFIDENT"
```

**contact_finder** szuka kontaktów dla "EvraFish" — correct Apollo match.

---

### 7.2 Grycan

**Artykuł:** "Grycan inwestuje w linię produkcji lodów premium"
**Pełna nazwa prawna:** "Grycan - Lody od pokoleń Sp. z o.o."

**Krok 1 — entity_extractor:**
- `source_name = "Grycan"` (LLM wyciąga brand name)
- `comparison_key = "grycan"`

**Krok 2 — Apollo search:**
- Zapytanie: `"Grycan"` → Apollo zwraca "Grycan - Lody od pokoleń Sp. z o.o."

**Krok 3 — Heuristic scoring:**
- `comparison_key("Grycan - Lody od pokoleń Sp. z o.o.")` → `"grycanlodyodpokole"` (nie pasuje do `"grycan"`)
- Ale name similarity("Grycan", "Grycan - Lody od pokoleń Sp. z o.o.") ≈ 0.50 → **+0.05**
- Partial comparison_key check: "grycan" in "grycanlodyodpokole" → True → **+0.25**
- Domain: `grycan.pl` → `_domain_contains_key("grycan.pl", "grycan")` = True → **+0.20**
- Industry: lody/żywność/FMCG overlap → **+0.05**
- **Suma: ~0.55** → MATCH_POSSIBLE (powyżej min_confidence 0.45, poniżej 0.72)

**Krok 4 — LLM:**
- Widzi: kandydat "Grycan - Lody od pokoleń" z domeną `grycan.pl`, artykuł o "Grycan lody"
- LLM: `confidence_adjustment=+0.15, rationale="Brand name 'Grycan' is core of full legal name; domain confirms"`
- Final: 0.55 + 0.15 = 0.70 → **MATCH_POSSIBLE** (blisko granicy confident)

**Wynik:**
```
resolved_company_name = "Grycan - Lody od pokoleń Sp. z o.o."
resolved_domain = "grycan.pl"
resolution_confidence = 0.70
resolution_status = "MATCH_POSSIBLE"
```

---

### 7.3 Edge case — AMBIGUOUS_HOLD: "Stella Pack"

**Artykuł:** "Stella Pack rozszerza produkcję opakowań"
**W Apollo:** kilka firm z podobną nazwą (Stella Pack S.A., Stella Packaging Ltd., Pack Stella)

**Heuristic scoring:**
- "Stella Pack S.A.": comparison_key "stellapack" == "stellapack" → **0.65** (domain nie znaleziony)
- "Stella Packaging Ltd.": similarity 0.70 → **0.35**

**Warunek AMBIGUOUS:** top=0.65 (poniżej 0.72), drugi=0.35 (poniżej min_confidence 0.45) → NIE AMBIGUOUS.
→ Top wygrywa z MATCH_POSSIBLE.

**Wariant trudniejszy:** gdyby oba kandydaty miały podobne score (0.60 vs 0.55):
- Różnica 0.05 < 0.15 → AMBIGUOUS_HOLD
- `requires_manual_review=True`, brak sekwencji, artykuł oznaczony jako `resolution_ambiguous`

---

## 8. Files Changed

| Plik | Zmiana |
|------|--------|
| `src/news/entity/company_resolver.py` | **NOWY** — główny moduł resolution layer: `ResolutionResult`, `resolve_company()`, scoring heurystyczny, website check, LLM evaluation |
| `src/news/orchestrator.py` | Zintegrowano resolution layer w `run_build_sequence()`: import, wywołanie po cooldown check, obsługa statusów, fallback przy błędzie |
| `campaigns/news/spendguru_market_news/config/campaign_config.yaml` | Dodano 4 nowe toggles: `use_company_resolution`, `company_resolution_use_website_check`, `company_resolution_min_confidence`, `company_resolution_confident_threshold` |

---

## 9. Risks and Limitations

### Czego ta metoda nadal nie rozwiązuje

| Ryzyko | Opis | Mitygacja |
|--------|------|-----------|
| Firma poza bazą Apollo | Apollo nie zwróci żadnego kandydata → NO_MATCH, brak sekwencji dla potencjalnie dobrej firmy | Fallback do oryginalnego flow gdy `use_company_resolution: false` |
| Generyczna nazwa firmy | "Polskie Zakłady" → wiele kandydatów w Apollo → AMBIGUOUS lub fałszywy MATCH | AMBIGUOUS_HOLD chroni przed automatycznym złym wyborem |
| Firma z rebrandingiem | Stara nazwa w artykule, nowa w Apollo → comparison_key nie pasuje | Sygnały domeny i industry pomogą; w ekstremalnym razie: NO_MATCH |
| LLM halucynacje | LLM może uzasadnić błędny wybór przekonująco | LLM ma mały wpływ (max ±0.20); heurystyka dominuje |
| Rate limiting Apollo | Każdy artykuł = 1-2 zapytania org search w Apollo | Przy dużej skali: dodać throttling lub cache kandydatów |
| Website check timeout | Strona wolna lub blokuje boty → 5s timeout + puste sygnały | Bonus 0 = nie pomaga, ale nie szkodzi; website_check domyślnie false |
| Firmy zależne grupy kapitałowej | "ORLEN Polyolefins" vs "PKN ORLEN" → różny comparison_key | Brak automatycznej obsługi grup; przyszłość: associated_companies lookup |

### Gdzie nadal potrzebny jest review

- Każdy status `AMBIGUOUS_HOLD` → bezwzględnie manual review
- Pierwszy miesiąc działania `use_company_resolution: true` → monitoring `MATCH_POSSIBLE` vs `MATCH_CONFIDENT` proporcji
- Firmy z bardzo krótkim comparison_key (< 5 znaków) → ryzyko collision

---

## 10. Final Recommendation

### Czy rozwiązanie jest wystarczające na tym etapie?

**TAK** — z warunkiem uruchamiania stopniowego.

Uzasadnienie:
- Warstwa jest domyślnie wyłączona (`use_company_resolution: false`) — zero ryzyka dla obecnego flow
- Backward compatible: jeśli resolution layer rzuci wyjątek, pipeline używa oryginalnej nazwy firmy
- Heurystyczny scoring zapewnia przewidywalność — LLM tylko koryguje
- Evra Fish → EvraFish: comparison_key match daje pewne MATCH_CONFIDENT
- Smoke tests: 29/29 PASS po integracji

### Rekomendowany plan uruchomienia

**Etap 1 (teraz):** Testuj z kilkoma artykułami ręcznie:
```bash
python src/news/orchestrator.py build-sequence --campaign spendguru_market_news \
  --single-article-url <url> --dry-run
```

**Etap 2:** Ustaw `use_company_resolution: true` + `company_resolution_use_website_check: false` i uruchom dry-run na batchu artykułów. Monitoruj statusy (`MATCH_CONFIDENT`, `MATCH_POSSIBLE`, `AMBIGUOUS_HOLD`, `NO_MATCH`).

**Etap 3 (opcjonalnie):** Włącz `company_resolution_use_website_check: true` dla kampanii z wysoko zróżnicowanymi brandingami.

### Co zrobić później

1. **Cache kandydatów Apollo** — przy tej samej firmie w wielu artykułach: nie szukaj każdorazowo, cache w RAM dla sesji `run-daily`
2. **Słownik aliasów** — `data/reference/company_aliases.yaml` z ręcznie zweryfikowanymi mapowaniami (Evra Fish → EvraFish)
3. **Associated companies lookup** — sprawdź `associated_companies` z entity_extractor jako dodatkowych kandydatów
4. **Logowanie resolution stats** — dodaj liczniki do run report (ile CONFIDENT, POSSIBLE, AMBIGUOUS, NO_MATCH)

---

*Raport wygenerowany po implementacji Company Resolution Layer. Zmiany są backward-compatible — istniejące kampanie nie wymagają modyfikacji.*
