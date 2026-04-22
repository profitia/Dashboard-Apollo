# RELEVANCE AND APOLLO AUDIT — spendguru_market_news

**Data audytu:** 2026-04-22
**Audytor:** GitHub Copilot (AI Outreach Pipeline review)
**Scope:** kwalifikacja artykułów + Apollo contact search flow
**Kampania:** `campaigns/news/spendguru_market_news`

---

## 1. Executive Summary

### Kwalifikacja artykułów — ocena ogólna

Obecna logika kwalifikacji jest **zbyt literalna i zbyt wąska**. Scorer oparty jest wyłącznie na keyword-matchingu. Brak jakiejkolwiek warstwy semantycznej, inferencyjnej ani LLM-based relevance check. Pipeline rozpoznaje tylko artykuły, w których słowa kluczowe z konfiguracji **dosłownie pojawiają się w tekście**. Artykuły o pośrednim wpływie na zakupy — np. innowacje materiałowe, zmiany regulacyjne dotyczące kategorii, upstream supply chain — są odrzucane mimo wysokiej wartości zakupowej.

Dodatkowo grupy branżowe (`industry_keywords`) definiują branżę zbyt wąsko — jako "firmę w aktywnym sektorze GTM" (producent żywności, sieć handlowa, FMCG). Brak rozumienia upstream relevance: artykuły o materiałach, komponentach, opakowaniach, surowcach mogą być równie ważne procurement-clic, ale nie przechodzą filtru branżowego.

### Apollo contact flow — ocena ogólna

Flow Apollo jest **w większości poprawnie zaimplementowany**. Listy Tier 1/2/3 (`PL Tier 1 do market_news VSC` itp.) są używane wyłącznie jako **destination**, nie jako source search. Kontakty są szukane w globalnej bazie Apollo (people prospecting), co jest właściwym podejściem.

Znaleziono dwa ryzyka techniczne:
1. Rozbieżność między metodami wyszukiwania w `apollo_client.py` vs `contact_finder.py` (różne URL patterns).
2. Brak fallback na wyszukiwanie po domenie, gdy `q_organization_name` zwraca 0 emaili.

### Najważniejsze ryzyka

| Ryzyko | Severity | Obszar |
|---|---|---|
| Procurement-relevant artykuły odrzucane przez keyword gap | CRITICAL | Scorer / keywords.yaml |
| Brak inferencji pośredniej relevance | HIGH | Scorer — brak LLM layer |
| Brak grup "opakowania", "surowce", "materiały" jako industry | HIGH | keywords.yaml |
| Kontakty firm upstream odrzucane przez industry filter | HIGH | Scorer / entity_extractor |
| Brak domain-based fallback search w Apollo | MEDIUM | contact_finder.py |
| Rozbieżność URL pattern w apollo_client vs contact_finder | LOW | apollo_client.py / contact_finder.py |

---

## 2. Article Qualification Audit

### 2.1 Current Logic

Scorer (`src/news/relevance/scorer.py`) jest czystym **keyword-matching engine**. Algorytm:

```
total_score = industry_score (max 40)
            + purchase_signal_score (max 40)
            + freshness_bonus (max 20)
            + amplifier_bonus (max 10)
            + procurement_vocabulary_bonus (max 5)
```

Kwalifikacja wymaga jednoczesnego spełnienia trzech warunków:
```yaml
min_relevance_score: 40     # total_score >= 40
min_industry_score: 15      # industry_score >= 15
min_purchase_signal_score: 15  # purchase_signal_score >= 15
```

Mechanizm liczenia:
- Dla każdej grupy w `industry_keywords` / `purchase_signals`: liczba dopasowań × waga grupy
- Bonus ×2 za trafienie w tytule artykułu
- Caps: industry_score = min(40, raw_score), purchase_score = min(40, raw_score)
- Tagi artykułu mają podwójną wagę (dodawane do search_text 2×)

**Brak warstwy semantycznej.** Nie ma żadnego wywołania LLM ani wnioskowania kontekstowego. Nie ma rozumienia zdaniowego — system sprawdza wyłącznie, czy konkretny string/term pojawia się w tekście.

### 2.2 Weak Points

#### 2.2.1 Industry groups — zbyt wąskie, GTM-centric

Obecne grupy branżowe (`keywords.yaml`):

| Grupa | Waga | Charakter |
|---|---|---|
| `retail_chains` | 3 | Sieci handlowe — bardzo specyficzne nazwy |
| `fmcg_trade` | 3 | FMCG / dystrybucja |
| `food_production` | 4 | Producenci żywności |
| `manufacturing` | 2 | Ogólna produkcja — bardzo generyczne |

**Brakuje:**
- `packaging_materials` — producenci opakowań, materiały opakowaniowe
- `ingredients_suppliers` — dostawcy składników, surowców spożywczych
- `chemicals_materials` — branża chemiczna upstream (PET, PP, polimery)
- `cold_chain_logistics` — logistyka chłodnicza (istotna dla FMCG)
- `beverage_production` — napoje (inny zestaw słów niż food)

W efekcie artykuł o innowacji opakowaniowej (ORLEN rPP) ma industry_score=4, bo jedyne trafienie to "branża spożywcza" wspomniana kontekstowo — choć cały artykuł dotyczy kategorii zakupowej (opakowania) używanej przez firmy spożywcze.

#### 2.2.2 Purchase signals — brakuje pośrednich sygnałów

Obecne grupy purchase signals:

| Grupa | Waga | Charakter |
|---|---|---|
| `investment_capacity` | 5 | Inwestycje, nowe fabryki |
| `cost_pressure` | 5 | Koszty, inflacja, marże |
| `supply_chain` | 4 | Dostawcy, dostawy, surowce |
| `energy_packaging` | 3 | Energia + opakowania (!) |
| `retail_requirements` | 4 | Przetargi, kontrakty z sieciami |
| `regulatory` | 3 | Regulacje, dyrektywy, ESG |
| `expansion` | 3 | Ekspansja, fuzje |

**Brakuje:**
- `material_innovation` — testy nowych materiałów, nowe technologie produkcji, zmiana komponentów
- `packaging_change` — zmiana opakowań, nowy format opakowania
- `ingredient_substitution` — zamiana składnika, nowe źródło surowca
- `compliance_deadline` — konkretne deadliny regulacyjne wymuszające zakupy
- `new_product_launch` — nowy produkt = nowe surowce / opakowania = trigger zakupowy

Artykuł o testach rPP (ORLEN): miał `purchase_signal_score=20` — czyli PRZESZEDŁ purchase threshold — dzięki słowom z grupy `supply_chain` ("surowce") i `energy_packaging` ("opakowania", "recykling"). Ale nie miał przemysłowego dopasowania.

#### 2.2.3 Brak inferencji — pipeline nie "łączy kropek"

Przykład luki:
- Artykuł: "Firma X testuje nowy materiał do opakowań spożywczych z 35% regranulatu"
- System widzi: "opakowania" ✓, "recykling" ✓ → energy_packaging = match
- System NIE wnioskuje: "testy nowego materiału oznaczają zmianę dostawcy opakowań → trigger zakupowy dla każdej firmy spożywczej kupującej od Pollena Kurowski"

Nie ma rozumienia, że:
- testy materiałowe → przyszłe zamówienia
- regulacja EU → konkretny termin compliance → konieczne zakupy przed datą
- zmiana producenta → przetarg / renegocjacja kontraktu

#### 2.2.4 Brak upstream/downstream relevance

Scorer nie rozumie łańcucha wartości. Artykuł o dostawcy (ORLEN = producent rPP) jest równie relevantny dla kupca w firmie FMCG co artykuł o samej firmie FMCG — bo informuje o zmianie dostępności i ceny materiału. Scorer tego nie widzi.

#### 2.2.5 Scoring jest addytywny bez kontekstu zdaniowego

Scorer zlicza wystąpienia terminów w całym tekście. Jedno słowo "opakowania" w zdaniu "ORLEN testuje opakowania z rPP" i "firma X rezygnuje z opakowań plastikowych" mają tę samą wagę w scorerze. Brak rozumienia, że to różne konteksty.

### 2.3 Analysis — Bio Planet Case

**Wynik:** FAIL — score=9, industry=0, purchase=0

Bio Planet to sieć sklepów ze zdrową żywnością. Artykuł (https://www.wiadomoscihandlowe.pl) mówił o Bio Planet jako firmie, np. o jej wynikach, planach, ekspansji.

**Dlaczego score=0 dla obu kategorii?**

Możliwe przyczyny (na podstawie scores z integration test — industry=0, purchase=0):
1. Artykuł mógł być krótki lub paywalled (body_truncated=True) → mało tekstu do scoringu
2. "Bio Planet" jako brand nie pojawia się w żadnej grupie keyword — nie ma "Bio Planet" w `retail_chains.terms`
3. Artykuł mógł opisywać wyniki finansowe językiem nieobecnym w keywordach ("wyniki", "sprzedaż", "obroty") — żadne z tych słów nie jest w grupach purchase_signals
4. Artykuł mógł nie zawierać żadnego bezpośredniego terminu zakupowego

**Co powinien wykryć scorer:**
- Bio Planet = sieć → powinien trafić w `retail_chains` (industry)
- "Wyniki sprzedaży" / "ekspansja" / "nowe sklepy" → powinien trafić w `expansion` (purchase) lub `investment_capacity`

**Wniosek:** scorer przegapia artykuł, bo terminy opisujące sieć handlową są na poziomie zdaniowym, a słowa kluczowe są zbyt dosłowne. "Bio Planet" powinno być dodane do terms w `retail_chains`, lub — lepiej — powinna być warstwa LLM klasyfikująca typ podmiotu.

### 2.4 Analysis — ORLEN Regranulat Case

**Wynik:** FAIL — score=29, industry=4, purchase=20

**Dlaczego industry=4 (za mało)?**

Jedyne trafienie w industry: `food_production` → 1 hit ("branża spożywcza" wspomniana kontekstowo) × weight=4 = 4 pkt.

Artykuł jest o:
- ORLEN (petrochemia, plastics) — brak tej grupy w industry_keywords
- Pollena Kurowski (packaging manufacturer) — brak "producent opakowań" w industry_keywords
- Nextloopp (projekt rPP) — brak
- Regulacja EU o opakowaniach — trafia w `regulatory` (purchase signals, weight=3) ale nie w industry

**Dlaczego purchase=20 (wystarczający)?**

Artykuł trafił w:
- `supply_chain`: "surowce" (rPP jako surowiec)
- `energy_packaging`: "opakowania", "recykling" × 2 hits
- `investment_capacity`: "zwiększenie mocy" (ORLEN zwiększa moce recyklingowe)
- Łącznie: 20 punktów

**Czy wynik był logiczny w kontekście obecnej logiki?** Tak — reguły działają poprawnie.

**Czy wynik był logiczny biznesowo?** Nie do końca. Artykuł o ORLEN rPP jest **pośrednio wysokorelewantny zakupowo** dla:
- Dyrektorów Zakupów w firmach spożywczych (zmiana dostępności i ceny opakowań)
- Category Managerów ds. opakowań
- CFO firm FMCG (implikacje kosztowe regulacji EU 2030/2040)

Ale scorer odrzuca go, bo nie widzi żadnej firmy spożywczej jako głównego podmiotu — a artykuł dotyczy dostawcy w łańcuchu wartości.

**Co powinien wykryć lepszy system:**
- Artykuł mówi o regulacji EU wymuszającej 35% recyklatu do 2030 — to jest **compliance deadline trigger** dla kupców opakowań
- Testowanie na liniach produkcyjnych Pollena Kurowski → implikacja: przyszła dostępność nowego materiału, potencjalna zmiana cen opakowań
- Zmiana ORLEN: moce recyklingowe 40k → 250k ton/rok → zmiana w supply chain kategorii "opakowania PP"

### 2.5 Recommended New Qualification Model

Proponowany model trójwarstwowy:

```
WARSTWA 1: Keyword Pre-filter (szybki, tani)
  → odrzuca: artykuły 100% irrelevantne (polityka, sport, pogoda)
  → nie kwalifikuje: tylko wstępnie filtruje
  → wynik: PASS / SKIP (do warstwy 2) / HARD_REJECT

WARSTWA 2: LLM Relevance Classifier (wolniejszy, kosztowny — tylko dla PASS z W1)
  → wejście: tytuł + lead + pierwsze 500 znaków body
  → zadanie: ocen 4 wymiary (0-10 każdy):
      a) direct_procurement_relevance — czy artykuł opisuje firmę kupującą/zmieniającą coś
      b) indirect_procurement_relevance — czy artykuł opisuje zmianę w kategorii zakupowej
      c) icp_industry_fit — czy podmiot artykułu należy do ICP (FMCG, retail, food)
      d) trigger_strength — jak silny jest sygnał do outreachu (konkretny event vs ogólnik)
  → kwalifikacja: direct >= 6 OR (indirect >= 7 AND icp_fit >= 5)

WARSTWA 3: Entity + Contact Fit Check (jeśli W2 = PASS)
  → sprawdź: czy extrahowana firma to dobry target SpendGuru
  → sprawdź: czy Apollo ma kontakty z emailem
  → wynik: GO / NO_GO (dokumentuj powód)
```

**Konkretne zmiany konfiguracyjne (niskie ryzyko):**

1. Dodać grupę `packaging_materials` do `industry_keywords`:
   ```yaml
   packaging_materials:
     label: "Opakowania / Materiały opakowaniowe"
     weight: 3
     terms: [producent opakowań, materiały opakowaniowe, opakowania spożywcze, folia, PP, PET, karton, laminat, recykling opakowań, opakowanie plastikowe, packaging]
   ```

2. Dodać grupę `material_innovation` do `purchase_signals`:
   ```yaml
   material_innovation:
     label: "Innowacje materiałowe / Nowe komponenty"
     weight: 4
     terms: [nowy materiał, test materiału, nowa technologia produkcji, zmiana surowca, nowy składnik, alternatywny surowiec, zamiennik, regranulat, bioplastik, recyklat, innowacja opakowaniowa]
   ```

3. Dodać grupę `compliance_trigger` do `purchase_signals`:
   ```yaml
   compliance_trigger:
     label: "Termin regulacyjny / Wymóg prawny"
     weight: 5
     terms: [do 2025, do 2026, do 2030, termin wdrożenia, wymóg od, obowiązkowy od, regulacja EU, dyrektywa opakowaniowa, PPWR, EPR]
   ```

4. Obniżyć `min_industry_score` z 15 na 10 **tylko przy wysokim purchase_signal (>=25)**:
   ```yaml
   # Alternatywna logika: OR zamiast AND dla ekstremum
   min_relevance_score: 40
   min_industry_score: 10      # obniżone z 15
   min_purchase_signal_score: 20  # podwyższone z 15 jeśli industry low
   ```

**Docelowo — implementacja LLM Classifier (warstwa 2):**

Osobny agent `RelevanceClassifierAgent` wywoływany po keyword pre-filter. Prompt systemowy: opisuje ICP SpendGuru, purchase triggers, czym jest SpendGuru. Wejście: tytuł + lead + 500 znaków body. Wyjście: JSON z 4 skorami + uzasadnieniem. Koszt: ~0.001 USD/artykuł z gpt-4.1-mini. Przy 10 artykułach/dzień = grosz.

---

## 3. Apollo Contact Search Audit

### 3.1 Current Search Flow

Obecny flow wyszukiwania kontaktów (od artykułu do draft w Apollo):

```
[ArticleFetcher] fetch + parse article
    ↓
[Scorer] keyword scoring → qualified=True/False
    ↓ (jeśli qualified)
[EntityExtractor] LLM → company_name, type, eligible, confidence
    ↓
[ContactFinder._search_apollo_contacts]
    POST /v1/mixed_people/api_search
    payload: { q_organization_name, person_seniorities, per_page, page }
    → zwraca: lista people z Apollo global database
    ↓
[ContactFinder.find_contacts_for_company]
    mapuje people → ContactRecord (tier, email, confidence)
    filtruje po email (valid_email=True required for threshold)
    ↓
[MessageGenerator] generuje OutreachPack (3 emaile) per kontakt
    ↓
[SequenceBuilder.create_news_sequence]
    per kontakt:
        1. _find_or_create_apollo_contact (search CRM by email → create if missing, run_dedupe=True)
        2. _add_to_apollo_list (POST labels/{id}/add_contact_ids)
        3. _set_contact_stage (POST contacts/{id}, stage=News pipeline - drafted)
        4. update_contact (custom fields: sg_market_news_email_step_N_*)
    po wszystkich kontaktach:
        5. _send_draft_approval_email (Office365)
```

### 3.2 Endpoints Actually Used

| Krok | Endpoint | Metoda | Payload | Rola |
|---|---|---|---|---|
| People search (prospecting) | `POST /v1/mixed_people/api_search` | POST | `{q_organization_name, person_seniorities, per_page, page}` | Szukaj osób w globalnej bazie Apollo |
| Contact search (CRM) | `POST /v1/contacts/search` | POST | `{q_keywords: email, page: 1, per_page: 1}` | Sprawdź, czy kontakt już jest w CRM |
| Contact create | `POST /v1/contacts` | POST | `{first_name, last_name, email, title, organization_name, run_dedupe: true}` | Utwórz kontakt w CRM z dedupem |
| Labels (lists) read | `GET /v1/labels` | GET | - | Pobierz ID listy docelowej |
| Add to list | `POST /v1/labels/{id}/add_contact_ids` | POST | `{contact_ids: [id]}` | Dodaj kontakt do listy Tier N |
| Stage lookup | `GET /v1/contact_stages` | GET | - | Pobierz ID stage'u po nazwie |
| Stage set / custom fields | `PATCH /v1/contacts/{id}` | via `update_contact` | stage_id, typed_custom_fields | Ustaw stage + custom fields |
| Custom fields definitions | `GET /v1/typed_custom_fields` | GET | - | Mapowanie nazwa↔ID custom fields (w `__init__`) |

### 3.3 Lists as Destination vs Source

**Pytanie kluczowe: czy listy PL Tier N do market_news VSC są używane jako SOURCE search?**

**Odpowiedź: NIE. Listy są używane wyłącznie jako DESTINATION.**

Dowód z kodu:

```python
# campaign_config.yaml — konfiguracja list
apollo_lists:
  tier_1: "PL Tier 1 do market_news VSC"
  tier_2: "PL Tier 2 do market_news VSC"
  tier_3: "PL Tier 3 do market_news VSC"

# sequence_builder.py — użycie list
tier_list_map = {
    "tier_1_c_level": apollo_lists.get("tier_1", "PL Tier 1 do market_news VSC"),
    "tier_2_procurement_management": apollo_lists.get("tier_2", "PL Tier 2 do market_news VSC"),
    "tier_3_buyers_operational": apollo_lists.get("tier_3", "PL Tier 3 do market_news VSC"),
}
# ... używane TYLKO w _add_to_apollo_list() — DODAWANIE, nie szukanie
```

Wyszukiwanie kontaktów NIE używa list jako filtra. Zawsze:
1. `contact_finder.py` → `POST /v1/mixed_people/api_search` (globalna baza Apollo)
2. Znaleziony kontakt → `_find_or_create_apollo_contact` → sprawdź CRM → utwórz jeśli brak
3. **Po** zapisaniu → `_add_to_apollo_list` → kontakt trafia na listę

To jest **poprawna logika** — source=globalna baza Apollo, destination=lista Tier N. ✅

### 3.4 Recommended Correct Flow

Poniżej docelowy model (z oceną, czy obecna implementacja go spełnia):

| Krok | Opis | Status |
|---|---|---|
| 1 | Wyszukaj osobę w Apollo people search (globalny prospecting) | ✅ używa `mixed_people/api_search` |
| 2 | Wybierz najlepszego kandydata (tier_1 > tier_2 > tier_3, email required) | ✅ sortowanie po tier_priority + confidence |
| 3 | Sprawdź email — walidacja regex + require_email_for_sequence | ✅ `_is_valid_email()` + threshold check |
| 4 | Sprawdź czy kontakt istnieje w CRM (search_contact by email) | ✅ `_find_or_create_apollo_contact` |
| 5 | Jeśli brak — utwórz z run_dedupe=True | ✅ `POST /v1/contacts` + run_dedupe: true |
| 6 | Zapisz custom fields (sg_market_news_email_step_N_*) | ✅ `_outreach_pack_to_custom_fields` |
| 7 | Przypisz do właściwej listy Tier N | ✅ `_add_to_apollo_list` |
| 8 | Ustaw stage "News pipeline - drafted" | ✅ `_set_contact_stage` |
| 9 | Wyślij approval email | ✅ `_send_draft_approval_email` |
| 10 | Brak auto-enrollmentu | ✅ `auto_enroll: false` w config + w logice |

### 3.5 Gaps / Risks / Required Verifications

#### Gap 1 — Rozbieżność URL pattern (LOW RISK, ale do weryfikacji)

`apollo_client.py` zawiera dwie metody szukania osób:

```python
# Metoda 1: search_people() — własny URL pattern
resp = requests.post(
    f"{APOLLO_BASE_URL.replace('/v1', '')}/api/v1/mixed_people/api_search",
    ...
)

# Metoda 2: _post() — używana w contact_finder.py
client._post("mixed_people/api_search", {...})
# → f"{APOLLO_BASE_URL}/mixed_people/api_search"
# jeśli APOLLO_BASE_URL = "https://api.apollo.io/v1" → "https://api.apollo.io/v1/mixed_people/api_search"
```

`search_people()` buduje URL jako `https://api.apollo.io/api/v1/...` (z `/api/v1/`).
`_post()` buduje URL jako `https://api.apollo.io/v1/...` (bez `/api/`).

Obie mogą działać (Apollo akceptuje oba prefixes), ale **`search_people()` nie jest używana w pipeline** — `contact_finder.py` używa `client._post()`. Metoda `search_people()` jest martwym kodem w kontekście tego pipeline'u.

**Ryzyko:** jeśli ktoś zamieni `_post` na `search_people()`, URL będzie się różnił. Wymaga weryfikacji, który URL Apollo akceptuje.

#### Gap 2 — Brak domain-based fallback search (MEDIUM RISK)

Gdy `q_organization_name` zwraca 10 kontaktów ale 0 emaili, pipeline zatrzymuje się.

Brak alternatywnego searchowania:
- Po domenie firmy: `q_organization_domains_list: ["orlen.pl"]`
- Po branży + lokalizacji: `person_locations: ["Poland"]` + `person_titles: ["Procurement Director"]`

Implementacja `client.search_people()` w apollo_client.py obsługuje `q_organization_domains_list` — ale `contact_finder.py` tego nie używa.

#### Gap 3 — Brak ponownego searchowania firmy powiązanej z artykułem (MEDIUM RISK)

Gdy firma główna (np. ORLEN) ma 0 emaili, pipeline nie próbuje automatycznie znaleźć firmy powiązanej wymienionej w artykule (np. Pollena Kurowski). Ten krok był wykonywany **manualnie** w integration test.

Brak logiki: "jeśli company_type=`other` i 0 emaili → sprawdź associated_companies z EntityExtractor".

#### Gap 4 — `search_contact` używa `q_keywords` (email) — może zwrócić false positives (LOW RISK)

```python
def search_contact(self, email):
    data = self._post("contacts/search", {
        "q_keywords": email,
        "page": 1,
        "per_page": 1,
    })
```

`q_keywords` to search fulltext — może dopasować inne kontakty, których notka/tag zawiera ten email. Apollo ma dedykowane pole `email` do searchowania. Może zwrócić false positive, przez co nie zostanie created nowy kontakt dla słusznego emaila.

**Rekomendacja:** użyć `{"email": email}` zamiast `{"q_keywords": email}` jeśli Apollo API to obsługuje (wymaga weryfikacji live).

#### Gap 5 — Stage lookup nie cachuje (LOW RISK, ale wasteful)

`_set_contact_stage` robi `GET /v1/contact_stages` **per kontakt**. Przy 10 kontaktach = 10 identycznych requestów do Apollo. Powinno być cached na poziomie sesji.

#### Gap 6 — Brak weryfikacji, że lista Tier N istnieje w Apollo (MEDIUM RISK)

`_add_to_apollo_list` sprawdza, czy lista istnieje przez `GET /v1/labels`. Jeśli nie istnieje — loguje warning i zwraca False. Nie ma mechanizmu tworzenia listy gdy jej brak. Jeśli nazwy list w `campaign_config.yaml` różnią się od nazw w Apollo (choćby o spację/capital) — kontakt nie jest przypisywany, bez zatrzymania procesu.

---

## 4. Concrete Recommendations

| Obszar | Rekomendacja | Priorytet | Zmiana kodu | Live test |
|---|---|---|---|---|
| Scorer — keyword gap | Dodaj grupy `packaging_materials`, `material_innovation`, `compliance_trigger` do keywords.yaml | WYSOKI | Nie (tylko YAML) | Nie |
| Scorer — thresholds | Obniż `min_industry_score` z 15 na 10 (ewentualnie z warunkowym podwyższeniem purchase) | WYSOKI | Nie (tylko YAML) | Tak (weryfikacja false positives) |
| Scorer — LLM layer | Dodaj `RelevanceClassifierAgent` jako opcjonalna warstwa 2 po keyword pre-filter | ŚREDNI | Tak | Tak |
| Industry scope | Przepisz `industry_keywords` tak, by obejmowała upstream/downstream (dostawców, branżę opakowań) | WYSOKI | Nie (tylko YAML) | Nie |
| Contact search — domain fallback | Gdy company ma 0 emaili: retry search po domenie firmy (`q_organization_domains_list`) | ŚREDNI | Tak | Tak (live Apollo) |
| Contact search — associated company | Gdy company_type=`other` i 0 emaili: spróbuj associated_company z EntityExtractor | ŚREDNI | Tak | Tak (live Apollo) |
| Apollo URL pattern | Ujednolicić URL building w apollo_client — `search_people()` używa innego base URL niż `_post()` | NISKI | Tak (refaktor) | Tak |
| search_contact payload | Zamień `q_keywords: email` na `email: email` w `search_contact()` | NISKI | Tak (1 linijka) | Tak (live Apollo) |
| Stage lookup cache | Cache result `GET /v1/contact_stages` na poziomie sesji, nie per kontakt | NISKI | Tak | Nie |
| Lista Tier N — auto-create | Dodaj auto-tworzenie listy gdy nie istnieje w Apollo | NISKI | Tak | Tak (live Apollo) |

---

## 5. Proposed Implementation Plan

**Faza 1 — natychmiastowe, bezpieczne, zero ryzyka (YAML only)**

Krok 1: Dodaj `packaging_materials` do `industry_keywords` w `keywords.yaml`
Krok 2: Dodaj `material_innovation` i `compliance_trigger` do `purchase_signals` w `keywords.yaml`
Krok 3: Obniż `min_industry_score` z 15 na 10 w `campaign_config.yaml`
Krok 4: Uruchom smoke tests (powinny dalej przechodzić 29/29)
Krok 5: Re-run integration test ORLEN — sprawdź czy teraz kwalifikuje

**Faza 2 — małe zmiany kodu, niskie ryzyko**

Krok 6: Dodaj domain-based fallback w `contact_finder._search_apollo_contacts` — gdy 0 emaili przy company_name search, retry z domain
Krok 7: Popraw `search_contact` — zmień `q_keywords` na `email` (live API test needed)
Krok 8: Cache stage lookup w `sequence_builder`
Krok 9: Weryfikacja live: czy listy Tier N istnieją w Apollo z dokładnymi nazwami z config

**Faza 3 — LLM Relevance Classifier (nowa funkcja)**

Krok 10: Stwórz `RelevanceClassifierAgent` (nowy plik `src/news/relevance/llm_classifier.py`)
Krok 11: Napisz prompt: ICP SpendGuru + typy triggerów + 4 skale (0-10)
Krok 12: Zintegruj jako opcjonalną warstwę po keyword scorer (toggle w campaign_config.yaml: `use_llm_relevance_check: true/false`)
Krok 13: Test na zbiorze artykułów (Bio Planet, ORLEN, artykuły WH)

**Faza 4 — advanced search (wymaga živé API research)**

Krok 14: Associated company search — gdy type=`other` lub 0 emaili → szukaj Pollena Kurowski, etc.
Krok 15: Upstream/downstream company extraction w EntityExtractor — LLM zwraca listę firm powiązanych
Krok 16: Multi-company scoring — artykuł może triggerować outreach do wielu firm jednocześnie

---

## 6. Appendix — Evidence

### A. scorer.py — linia 120-145 (scoring loop)

```python
# File: src/news/relevance/scorer.py
# Function: score_article

for group_id, group in industry_kw.items():
    weight = group.get("weight", 1)
    terms = group.get("terms", [])
    hits = _count_hits(search_text, terms)
    title_hits = _count_hits(title, terms)
    score_contribution = (len(hits) * weight) + (len(title_hits) * weight)
    if hits:
        matched_industry[group_id] = hits
        industry_score += score_contribution
```

**Dlaczego to jest problem:** Każde wystąpienie termu dodaje `weight` punktów. Bez żadnego kontekstu semantycznego — "opakowania" w zdaniu "ORLEN testuje opakowania" i "firma spożywcza zmieniła opakowania po negocjacjach z dostawcą" mają tę samą wagę. Brak rozumienia, kto jest podmiotem i czy to jest trigger zakupowy.

### B. contact_finder.py — _search_apollo_contacts (linia ~112-140)

```python
# File: src/news/contacts/contact_finder.py
# Function: _search_apollo_contacts
# WHY IT MATTERS: Tutaj decyduje się, SKĄD bierzemy kontakty.

result = client._post("mixed_people/api_search", {
    "q_organization_name": company_name,
    "person_seniorities": seniority_list,
    "per_page": max_contacts,
    "page": 1,
})
```

To jest Apollo's **global people search** (prospecting database) — poprawnie. NIE jest to search po listach Tier 1/2/3. Kontakty nie muszą wcześniej istnieć w CRM.

### C. sequence_builder.py — create_news_sequence (linia ~280-310)

```python
# File: src/news/apollo/sequence_builder.py
# Function: create_news_sequence
# WHY IT MATTERS: Tutaj listy Tier N są używane jako DESTINATION.

tier_list_map = {
    "tier_1_c_level": apollo_lists.get("tier_1", "PL Tier 1 do market_news VSC"),
    "tier_2_procurement_management": apollo_lists.get("tier_2", "PL Tier 2 do market_news VSC"),
    "tier_3_buyers_operational": apollo_lists.get("tier_3", "PL Tier 3 do market_news VSC"),
}
# ...
list_name = tier_list_map.get(contact.tier, "")
if list_name:
    added = _add_to_apollo_list(client, contact_id, list_name)
```

Listy są używane **wyłącznie** do przypisania znalezionego kontaktu. Poprawna logika: source=Apollo database, destination=lista. ✅

### D. apollo_client.py — rozbieżność URL (linia ~150-175)

```python
# File: Integracje/apollo_client.py
# WHY IT MATTERS: Dwie różne metody, różne URL patterns

# search_people() — metodą NIESTOSOWANĄ w pipeline:
f"{APOLLO_BASE_URL.replace('/v1', '')}/api/v1/mixed_people/api_search"
# = https://api.apollo.io/api/v1/mixed_people/api_search

# _post() — metodą STOSOWANĄ w contact_finder:
f"{APOLLO_BASE_URL}/mixed_people/api_search"
# = https://api.apollo.io/v1/mixed_people/api_search
```

Obie mogą działać, ale nie zostało to zweryfikowane live. `search_people()` jest de facto martwym kodem w aktualnym pipeline.

### E. campaign_config.yaml — thresholds

```yaml
# File: campaigns/news/spendguru_market_news/config/campaign_config.yaml
# WHY IT MATTERS: Te progi decydują o kwalifikacji.

min_relevance_score: 40          # total
min_industry_score: 15           # ← zbyt wysoki dla upstream/indirect artykułów
min_purchase_signal_score: 15    # ← OK, ale brakuje terminów pośrednich w keywords
```

Artykuł ORLEN: total=29, industry=4, purchase=20.
Przy `min_industry_score: 10` → **kwalifikowałby** (total=29 < 40 wciąż za mało, ale po dodaniu keyword grup → ok).

---

## Podsumowanie końcowe

**Czy zgadzam się, że ORLEN/regranulat powinien mieć wyższy procurement relevance?**

**Tak.** Artykuł o testach rPP przez ORLEN jest pośrednio wysokorelewantny zakupowo:
- Dotyczy kategorii zakupowej (opakowania PP) stosowanej przez firmy spożywcze
- Opisuje zmianę dostępności i struktury kosztów tej kategorii
- Wskazuje konkretny termin regulacyjny (2030/2040) — compliance trigger
- Firma Pollena Kurowski (partner testów) jest potencjalnym targetem (kupcy w firmach współpracujących z Pollena Kurowski)

System poprawnie go odrzuca **według własnych reguł** — ale reguły są zbyt wąskie. Brakuje grupy `packaging_materials` w industry i grupy `material_innovation` w purchase signals.

**Czy listy Tier 1/2/3 są dziś poprawnie traktowane jako destination lists, a nie source search?**

**Tak.** Listy są używane wyłącznie w `_add_to_apollo_list()` po znalezieniu i zapisaniu kontaktu. Nie są nigdzie używane jako filtr searchowania. Flow jest poprawny architekturalnie.

---

*Raport wygenerowany: 2026-04-22*
*Pliki objęte audytem: `src/news/relevance/scorer.py`, `campaigns/news/spendguru_market_news/config/keywords.yaml`, `campaigns/news/spendguru_market_news/config/campaign_config.yaml`, `src/news/contacts/contact_finder.py`, `src/news/apollo/sequence_builder.py`, `Integracje/apollo_client.py`*
