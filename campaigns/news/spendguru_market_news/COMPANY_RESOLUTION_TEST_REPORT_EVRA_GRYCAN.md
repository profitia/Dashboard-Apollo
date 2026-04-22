# Company Resolution Layer — Test Report: Evra Fish & Grycan
*Data testu: 2026-04-21 | Scope: spendguru_market_news pipeline*

---

## 1. Zakres testu

**Cel:** Zweryfikować działanie Company Resolution Layer na dwóch realnych przypadkach z polskiego portalu spożywczego. Ocenić, czy resolver poprawnie identyfikuje firmy w Apollo, jakie mają być dalsze kroki w pipeline oraz czy alias dictionary wnosi realną wartość.

**Przypadki testowe:**
- **Case 1 — Evra Fish:** Przetwórca i dystrybutor ryb/owoców morza. Media: "Evra Fish", branding firmy: "EvraFish" (jedno słowo bez spacji).
- **Case 2 — Grycan:** Producent lodów premium. Nazwa medialna: "Grycan", pełna nazwa prawna: "Grycan - Lody od pokoleń Sp. z o.o."

**Konfiguracja testu:**
- `use_company_resolution: true` (wymuszone przez skrypt diagnostyczny)
- `company_resolution_use_website_check: false`
- `company_resolution_min_confidence: 0.45`
- `company_resolution_confident_threshold: 0.72`
- Artykuły: fetch z portalspozywczy.pl — HTTP 200 (realny fetch), ale body JS-rendered ("Reklama") — resolver użył title + lead.

---

## 2. Case 1 — Evra Fish

### Wejście
| Pole | Wartość |
|------|---------|
| source_company_name | "Evra Fish" |
| canonical_name | "Evra Fish" |
| comparison_key | "evrafish" |
| article_title | "Evra Fish: Wzrost spożycia ryb w Polsce nie wydarzy się w tradycyjnych formatach" |
| article_lead | Real (HTTP 200) — zawierał kontekst ekspansji w convenience/HoReCa |

### Wyniki Apollo

| Etap | Wynik |
|------|-------|
| Org search "Evra Fish" | 0 kandydatów |
| People search fallback "Evra Fish" | 0 kandydatów |
| **Alias dict kick-in** | "Evra Fish" → canonical_name_override: "EvraFish" |
| Org search "EvraFish" (alias) | **1 kandydat: "Evrafish"** |
| Org search "Evra Fish" (source fallback) | 0 kandydatów |

### Scoring

| Sygnał | Wartość | Score |
|--------|---------|-------|
| comparison_key_exact_match: "evrafish" | ✅ | +0.45 |
| name_similarity_high (Evrafish ≈ EvraFish) | ✅ | +0.20 |
| domain_matches_key: evrafish.com | ✅ | +0.20 |
| **Suma heurystyczna** | | **0.85** |
| LLM adjustment | +0.05 | |
| **Finalna confidence** | | **0.90** |
| **Status** | | **MATCH_CONFIDENT** |

### Apollo org znaleziony
- **Nazwa:** Evrafish
- **Domena:** evrafish.com
- **Czas LLM:** ~825s (patrz §6 — bug timeoutu, naprawiony)

### Wniosek
Bez alias dictionary: **NO_MATCH** (0 wyników org search dla "Evra Fish"). Alias dict jest **kluczowy** dla tej firmy — bez niego pipeline pomija artykuł mimo realnie istniejącego kontaktu w Apollo.

---

## 3. Case 2 — Grycan

### Wejście
| Pole | Wartość |
|------|---------|
| source_company_name | "Grycan" |
| canonical_name | "Grycan" |
| comparison_key | "grycan" |
| article_title | "Przyspieszony start sezonu lodowego. Grycan: Początek sezonu przynosi pozytywne sygnały" |

### Wyniki Apollo

| Etap | Wynik |
|------|-------|
| Org search "Grycan" | 0 kandydatów |
| People search fallback "Grycan" | **1 org: "Grycan - Lody od pokoleń"** (brak domeny w Apollo) |
| Alias dict kick-in | "Grycan" → domain_hint: "grycan.pl", extra_queries: ["Grycan lody", "Grycan ice cream"] |
| Org search z extra_queries | 0 kandydatów |
| People search fallback z alias | 1 org (ta sama, deduplikowana) |

### Scoring

| Sygnał | Wartość | Score |
|--------|---------|-------|
| comparison_key_partial_match: "grycanlodyodpokoleń" ↔ "grycan" | ✅ | +0.25 |
| domain_hint (grycan.pl) → domain_matches_key | ✅ (alias dict) | +0.20 |
| **Suma heurystyczna** | | **0.45** |
| LLM adjustment | +0.20 | |
| **Finalna confidence** | | **0.65** |
| **Status** | | **MATCH_POSSIBLE** |

### Apollo org znaleziony
- **Nazwa:** Grycan - Lody od pokoleń
- **Domena:** grycan.pl (z alias dict — Apollo nie miał)
- **Czas LLM:** ~3s (normalny)

### Wniosek
People search fallback znalazł organizację mimo zerowych wyników org search. Domain hint z alias dict podniósł score z 0.25 (poniżej min_confidence) do 0.45 (granica MATCH_POSSIBLE) — umożliwiając LLM podniesienie do 0.65. Alias dict był **pomocniczy ale istotny** — bez domain_hint wynik byłby graniczny.

---

## 4. Obserwacje przekrojowe

### Ranking strategii (od najważniejszej)

1. **Alias dictionary (search_variant)** — krytyczny dla Evra Fish. Pozwala szukać po prawidłowej formie brandingowej gdy media używają wariantu bez spacji.
2. **People search fallback** — krytyczny dla Grycan. Małe polskie firmy z ograniczoną obecnością w Apollo org search są często dostępne przez indeks LinkedIn (ludzie → org).
3. **Domain hint z alias dict** — pomocniczy. Gdy Apollo nie ma domeny, hint podnosi score heurystyczny o +0.20 (sygnał: domain_matches_key).
4. **Comparison key exact match** — silny sygnał (+0.45) gdy org name w Apollo zgadza się co do klucza z canonical_name.
5. **LLM adjustment** — korekta ±0.20 działa poprawnie dla Grycan. Dla Evra Fish zadziałał po 825s (bug, naprawiony).

### Portalspozywczy.pl — body artykułów

- Fetch HTTP 200 działa, ale body artykułu = "Reklama" (JS-rendered).
- Resolver używa title + lead — to wystarczy dla scoring i kontekstu LLM.
- Fixture vs real: identyczny wynik dla resolution (body nieużywany).

---

## 5. Alias Dictionary — ocena wdrożenia

**Wniosek: alias dictionary jest wartościowy i uzasadniony.**

| Kryterium | Ocena |
|-----------|-------|
| Czy wnosi wartość dla Evra Fish? | **TAK — krytyczny** (bez niego: NO_MATCH) |
| Czy wnosi wartość dla Grycan? | **TAK — istotny** (domain_hint umożliwia przejście progu) |
| Czy jest ciężki w utrzymaniu? | **NIE** — prosty YAML, 1-2 wpisy na firmę |
| Czy można pominąć? | **NIE** dla firm z rozbieżnością media vs Apollo |
| Format | `source_variants` + `canonical_name` + `search_variants` + `domain` |

**Plik:** `campaigns/news/spendguru_market_news/data/company_aliases.yaml`

**Schemat wpisu:**
```yaml
- source_variants: ["Evra Fish", "Evra-Fish"]
  canonical_name: "EvraFish"
  search_variants: ["EvraFish"]
  domain: ""
  notes: "Media ze spacją, Apollo jako jedno słowo"
```

**Kiedy dodawać wpis:** gdy pipeline zwraca NO_MATCH lub MATCH_POSSIBLE z niskim confidence dla firmy, która logicznie powinna być w Apollo. Alias dict = ręczna korekta nazwy — lekka i celowa.

---

## 6. Znalezione problemy i naprawy

### Problem 1: LLM timeout (NAPRAWIONY)

**Symptom:** LLM evaluation dla Evra Fish trwała 825 sekund (13+ minut).
**Przyczyna:** OpenAI SDK bez skonfigurowanego timeoutu; provider GitHub Models może mieć długi czas retry przy rate limit lub błędach sieciowych.
**Naprawa:** `concurrent.futures.ThreadPoolExecutor` z `timeout=45s` wokół wywołania `generate_json()` w `_llm_evaluate_candidates()`. Po timeoucie resolver kontynuuje bez LLM (fallback do heurystyki).
**Plik:** `src/news/entity/company_resolver.py` — funkcja `_llm_evaluate_candidates()`

### Problem 2: Article body puste (ZNANE, NIEBLOKUJĄCE)

**Symptom:** body_excerpt = "Reklama" — portal renderuje artykuł przez JS.
**Wpływ:** Brak wpływu na resolution (resolver używa title + lead, które są w meta/og tags i fetchują poprawnie).
**Akcja:** Brak — nie naprawiać. Fixture zapasowe działają i mają pełny kontekst.

### Problem 3: Grycan comparison_key rozbieżność (ZNANE, OBSŁUGIWANE)

**Symptom:** Apollo org_name = "Grycan - Lody od pokoleń" → comparison_key = "grycanlodyodpokoleń" ≠ "grycan".
**Skutek:** Heurystyka klasyfikuje jako `partial_match` (+0.25) zamiast `exact_match` (+0.45).
**Obsługiwane przez:** domain_hint z alias dict (+0.20) + LLM (+0.20) → wystarczy do MATCH_POSSIBLE.
**Czy naprawiać:** NIE — resolver działa poprawnie. Byłoby naprawione gdyby canonical_name z alias dict był "Grycan - Lody od pokoleń" (wtedy partial match też na 0.45), ale nie jest konieczne.

---

## 7. Verdict

| Case | Status | Confidence | Źródło org | Alias Dict | Czas LLM |
|------|--------|------------|------------|------------|---------|
| Evra Fish | MATCH_CONFIDENT | 0.90 | org search (via alias EvraFish) | KRYTYCZNY | 825s (bug naprawiony) |
| Grycan | MATCH_POSSIBLE | 0.65 | people search fallback | POMOCNICZY | 3s |

**Company Resolution Layer działa poprawnie.** Oba przypadki rozwiązane pozytywnie. Trzy komponenty są niezbędne razem:
1. Alias dictionary (search variants)
2. People search fallback (gdy org search = 0)
3. Domain hint z alias dict (gdy Apollo nie ma domeny)

**Rekomendacja produkcyjna:**
- Włącz `use_company_resolution: true` w campaign_config gdy pipeline gotowy do testów live.
- Utrzymuj `company_aliases.yaml` jako living document — dodawaj wpisy reaktywnie gdy pojawiają się NO_MATCH dla znanych firm.
- Monitoruj logi `[Resolver]` w trybie verbose przy pierwszych uruchomieniach.
