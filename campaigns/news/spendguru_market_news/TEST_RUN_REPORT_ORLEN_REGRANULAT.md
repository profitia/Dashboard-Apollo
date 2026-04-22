# TEST RUN REPORT — ORLEN Regranulat Integration Test

**Kampania:** `spendguru_market_news`
**Data testu:** 2026-04-22
**Tryb:** dry-run → full 7-phase (live + dedup skipped z powodu braku emaili)
**Skrypt:** `tests/integration_test_bio_planet.py --url ... --test-id orlen_regranulat`

---

## 1. Test scope

| Parametr | Wartość |
|---|---|
| URL artykułu | `https://tworzywa.online/wiadomosci/orlen-testuje-regranulat-pp-do-opakowan-spozywczych/` |
| Tytuł artykułu | ORLEN testuje regranulat PP do opakowań spożywczych |
| Źródło | tworzywa.online (portal przetwórców tworzyw sztucznych) |
| Data publikacji | 2026-01-30 |
| State file | `data/test/orlen_regranulat_test_state.json` (testowy, nie produkcyjny) |
| Enrollment | auto_enroll=False przez cały test |
| Raw JSON | `outputs/news/spendguru_market_news/20260422_140207_orlen_regranulat_integration_test.json` |

**Kontekst artykułu:** ORLEN zakończył testy seryjnej produkcji opakowań z regranulatu polipropylenowego (rPP) w ramach projektu Nextloopp. Testy przeprowadzono we współpracy z Pollena Kurowski (producent opakowań). Artykuł dotyczy innowacji materiałowej, nie zakupów/zaopatrzenia konkretnej firmy spożywczej.

---

## 2. Qualification result

| Parametr | Wartość |
|---|---|
| Wynik | **FAIL** |
| Skor całkowity | 29 (min. 40) |
| Skor branżowy | 4 (min. 15) |
| Skor sygnałów zakupowych | 20 (min. 15) ✅ |
| Grupy branżowe dopasowane | `food_production` |
| Powód odrzucenia | Industry score too low: 4.0 (min 15). Matched groups: ['food_production'] |

**Sygnały zidentyfikowane przez scorer:**
- `[Industry/food_production]`: branża spożywcza
- `[Signal/investment_capacity]`: inwestycja, zwiększenie mocy
- `[Signal/supply_chain]`: surowce
- `[Signal/energy_packaging]`: opakowania, recykling

**Ocena:** Kwalifikacja FAIL jest **oczekiwanym i poprawnym** zachowaniem dla tego artykułu. Artykuł pochodzi z portalu branży tworzyw sztucznych, nie z branży spożywczej. ORLEN jest dostawcą materiałów (petrochemia), nie firmą FMCG kupującą od dostawców. Skor zakupowy 20 (wyższy niż min. 15) potwierdza, że artykuł ZAWIERA sygnały zakupowe, ale dotyczy niewłaściwej branży/sektora. Pipeline poprawnie filtruje.

**Uwaga: skor zakupowy 20 jest najwyższy ze wszystkich artykułów testowanych do tej pory** — wyższy niż Bio Planet (0). To dobry sygnał: scorer rozpoznaje treści zakupowe w artykule.

---

## 3. Entity extraction result

| Parametr | Wartość |
|---|---|
| Wynik | **PASS** |
| Metoda | LLM (gpt-4.1 via OpenAI API) |
| Firma wyekstrahowana | ORLEN S.A. |
| Typ firmy | `other` |
| Eligible | True |
| Confidence | 0.96–0.97 (stabilny przez dwa uruchomienia) |

**Ocena:** LLM poprawnie zidentyfikował ORLEN S.A. jako główną firmę artykułu, z wysokim confidence. Typ `other` (nie `producer`, `retailer`, `distributor`) jest trafny — ORLEN to koncern paliwowo-petrochemiczny. `eligible=True` jest debatable — ORLEN jest podmiotem w artykule, ale nie jest idealnym targetem SpendGuru (jest dostawcą materiałów, nie nabywcą).

**Firmy powiązane wspomniane w artykule (znalezione ręcznie w body):**
- **Pollena Kurowski** — producent opakowań z 60-letnim doświadczeniem, bezpośredni partner testów

---

## 4. Apollo contact availability pre-check

### ORLEN S.A. (firma główna)

| Parametr | Wartość |
|---|---|
| Kontakty znalezione | 10 |
| Kontakty z emailem | **0** |

| Imię | Stanowisko | Tier | Email |
|---|---|---|---|
| Maciej | Director - Retail Network Development | tier_1 | BRAK |
| Aneta | Manager | tier_1 | BRAK |
| Piotr | Executive Director for Commercial | tier_1 | BRAK |
| Piotr | Director of Retail Systems | tier_1 | BRAK |
| Justyna | Category Manager | tier_3 | BRAK |
| Magdalena | Project Manager | tier_uncertain | BRAK |
| Maciej | Project Manager | tier_uncertain | BRAK |
| Robert | IT Manager | tier_uncertain | BRAK |
| Anna | Project Manager / Strategy | tier_uncertain | BRAK |
| Lukasz | Project Manager | tier_uncertain | BRAK |

### Pollena Kurowski (firma powiązana — dodatkowe sprawdzenie ręczne)

| Parametr | Wartość |
|---|---|
| Endpoint | `POST /v1/mixed_people/api_search` |
| Kontakty znalezione | 10 |
| Kontakty z emailem | **0** |

| Imię | Stanowisko | Email |
|---|---|---|
| Martyna | New Business Sales Manager | BRAK |
| Marta | HSE Manager | BRAK |
| Eliza | Key Account Manager | BRAK |
| Monika | Business Development Manager | BRAK |
| Karolina | Marketing and Sales Director | BRAK |
| Magdalena | Sales Manager | BRAK |
| Bogdan | Manager | BRAK |
| Aleksander | Manager of Procurement | BRAK |
| Anna | Key Account Manager | BRAK |
| Vladimir | Director | BRAK |

**Ocena:** Obie firmy mają kontakty w Apollo (10+), ale żadna nie ma emaila. To **luka danych Apollo dla polskich firm przemysłowych** — nie błąd pipeline'u. Live write i dedup test nie mogły zostać wykonane.

---

## 5. Dry-run result

| Parametr | Wartość |
|---|---|
| Wynik | **PASS** |
| Nazwa sekwencji | `NEWS-2026-01-30-orlen-sa-orlen-testuje-regranulat-pp-do-opakowan-` |
| Listy Apollo docelowe | `[]` (brak kontaktów z emailem) |
| auto_enroll | False |
| Approval email checks | **7/7 passed** |

**Approval email checks:**

| Check | Wynik |
|---|---|
| contains_article_title | ✅ |
| contains_article_url | ✅ |
| contains_company_name | ✅ |
| contains_stage ("News pipeline - drafted") | ✅ |
| contains_campaign_name ("spendguru_market_news") | ✅ |
| contains_approval_status ("czeka na zatwierdzenie") | ✅ |
| contacts_in_email | ✅ (brak kontaktów → `all([])` = True) |

Dry-run PASS — infrastruktura pipeline (approval email, naming, stage) działa prawidłowo.

---

## 6. Live-run result

| Parametr | Wartość |
|---|---|
| Wynik | **SKIP** |
| Powód | 0 kontaktów z emailem → `create_news_sequence` nie wywołane |

Fazy LIVE i DEDUP zostały pominięte. Poniższe operacje **nie zostały przetestowane** dla tego artykułu:
- `_find_or_create_apollo_contact`
- `_add_to_apollo_list`
- `_set_contact_stage` → "News pipeline - drafted"
- `_outreach_pack_to_custom_fields` (sg_market_news_email_step_N_*)
- wysyłka approval email (Office365)
- weryfikacja no-enroll

---

## 7. Dedupe rerun result

| Parametr | Wartość |
|---|---|
| Wynik | **SKIP** |
| Powód | Brak kontaktów z emailem → nie można testować idempotencji |

---

## 8. Issues found

| # | Problem | Severity | Plik / Moduł | Dokładne zachowanie | Rekomendacja | Status |
|---|---|---|---|---|---|---|
| 1 | Zły tytuł artykułu — scraping tworzywa.online | HIGH | `src/news/ingestion/article_fetcher.py` | Fetcher wybierał pierwszy `h1` na stronie (= nazwa portalu "Portal przetwórców tworzyw sztucznych") zamiast tytułu artykułu, który był w drugim `h1` i `.entry-title` | Dodano fallback do `og:title` w `article_fetcher.py`: jeśli wyciągnięty `h1` odpowiada zawartości `<title>` (generyczna nazwa portalu), używany jest `og:title` bez sufiksu nazwy serwisu | ✅ NAPRAWIONE |
| 2 | tworzywa.online nieobecny w sources.yaml | MEDIUM | `campaigns/news/spendguru_market_news/config/sources.yaml` | Brak wpisu → pipeline używał fallback source_id `wiadomosci_handlowe` i pustych selektorów; tytuł/lead/body nie były optymalnie wyciągane | Dodano wpis `tworzywa_online` z selektorem `.entry-title` dla tytułu i `time[datetime]` dla daty | ✅ NAPRAWIONE |
| 3 | Industry score 4 < min 15 dla artykułu | FINDING | `src/news/relevance/scorer.py` | Artykuł z portalu tworzyw sztucznych uzyskuje niski skor branżowy mimo wzmianki o "branży spożywczej". Skor zakupowy 20 > min 15 | Poprawne zachowanie. Artykuł dotyczy przemysłu tworzyw, nie firm FMCG jako podmiotów. Do rozważenia: dodanie grupy `packaging_materials` do keywords.yaml dla artykułów o opakowaniach kierowanych do sektora spożywczego | 📝 DOKUMENTACJA |
| 4 | ORLEN S.A. — type=other, nie idealny target SpendGuru | FINDING | `src/news/entity/entity_extractor.py` | LLM zaklasyfikował ORLEN jako `other` (poprawnie — to koncern paliwowy). `eligible=True` jest automatyczne, ale ORLEN jako dostawca materiałów nie jest docelową personą SpendGuru (zakupy, CFO, CEO producenta FMCG) | Rozważyć filtrowanie firm type=other na etapie entity jeśli nie są producentami/retailerami | 📝 DOKUMENTACJA |
| 5 | ORLEN S.A. i Pollena Kurowski — 0 emaili w Apollo | FINDING | Apollo API / dane | 10+10 kontaktów bez emaila. Blokuje etapy LIVE i DEDUP | Luka danych Apollo dla dużych polskich firm przemysłowych. Nie jest to błąd pipeline'u | 📝 DOKUMENTACJA |

---

## 9. Zmiany kodu wprowadzone podczas testu

### `src/news/ingestion/article_fetcher.py`
Dodano fallback tytułu na `og:title`: gdy wyciągnięty `h1` pokrywa się z zawartością `<title>` (czyli jest generyczną nazwą portalu), fetcher próbuje wziąć `og:title` i odciąć sufiks ` - Serwis` lub ` | Serwis`. To rozwiązuje problem z portalami, gdzie logo/nazwa serwisu jest pierwszym `h1` na stronie.

### `campaigns/news/spendguru_market_news/config/sources.yaml`
Dodano źródło `tworzywa_online` (https://tworzywa.online) z selektorem `.entry-title` dla tytułu artykułu, `time[datetime]` dla daty, `.entry-content` dla body i `link[rel='canonical']` dla canonicala.

### `tests/integration_test_bio_planet.py`
Dodano parametry `--url` i `--test-id`: skrypt może teraz być uruchamiany dla dowolnego artykułu bez edycji kodu. State file i plik JSON output są automatycznie nazywane na podstawie `--test-id`.

---

## 10. Final verdict

### Werdykt testu: **FAIL Z PEŁNYM KONTEKSTEM**

Wszystkie 3 CRITICAL issues mają znane, udokumentowane przyczyny niebędące błędami pipeline'u:

1. **QUALIFY FAIL** — poprawne zachowanie. Artykuł z portalu tworzyw sztucznych nie spełnia kryterium branżowego (industry=4, min 15). Skor zakupowy 20 jest dobry (wyższy niż min 15), ale niewystarczający gdy nie ma pasującej grupy branżowej.

2. **CONTACTS — 0 emaili** — Apollo nie ma emaili dla ORLEN S.A. ani Pollena Kurowski. To luka danych dla dużych polskich firm przemysłowych, nie błąd kodu.

3. **LIVE + DEDUP SKIP** — bezpośrednia konsekwencja braku emaili.

**Co działa poprawnie:**
- Fetch artykułu (po naprawie selektora tytułu) ✅
- Scoring (poprawne odrzucenie z dobrym purchase signal) ✅
- Ekstrakcja firmy via LLM (ORLEN S.A. z confidence 0.97) ✅
- Apollo people search (10 kontaktów dla ORLEN) ✅
- Dry-run preview (7/7 approval email checks) ✅
- auto_enroll=False ✅
- Smoke testy: 29/29 bez regresji ✅

---

## Recommendation — czy artykuł nadaje się do przyszłego regression testingu?

### ❌ NIE rekomendowane do regression testów pipeline

**Powody:**

1. **Industry mismatch** — artykuł z portalu tworzyw sztucznych. Pipeline poprawnie go odrzuca, ale testy powinny weryfikować przypadki, gdzie kwalifikacja PRZECHODZI.

2. **Brak emaili w Apollo** — obie firmy (ORLEN, Pollena Kurowski) mają 0 emaili → fazy LIVE i DEDUP nie mogą być przetestowane.

3. **ORLEN nie jest idealnym targetem SpendGuru** — to dostawca materiałów, nie nabywca narzędzia do negocjacji zakupowych.

4. **Artykuł ma potencjał jako edge case / negatywny test** — dobry do weryfikacji, że pipeline poprawnie ODRZUCA artykuły z branży tworzyw, mimo że zawierają słowo "opakowania spożywcze".

### ✅ Co byłoby dobrym artykułem do regression testu?

Artykuł spełniający wszystkie kryteria:
- **Branża:** producent żywności / FMCG / sieć handlowa → industry score ≥ 15
- **Sygnał zakupowy:** zmiana dostawcy, nowy kontrakt, przetarg, wzrost zamówień → purchase score ≥ 15
- **Firma docelowa:** producent FMCG lub retailer (nie dostawca materiałów)
- **Apollo data:** firma z emailami w Apollo (najlepiej większa firma FMCG)
- **Przykłady portali:** `wiadomoscihandlowe.pl`, `portalspozywczy.pl`, `rynekspozywczy.pl`

---

## Podsumowanie (quick view)

| Check | Wynik |
|---|---|
| Qualification | ❌ FAIL (score=29/40, industry=4/15, purchase=20/15) |
| Recognized company | ORLEN S.A. (type=other, confidence=0.97) |
| Contacts with email | ❌ NIE (0/10 dla ORLEN, 0/10 dla Pollena Kurowski) |
| Live write executed | ❌ NIE (brak emaili) |
| Approval email sent | ❌ NIE (brak emaili) |
| Auto-enroll skipped | ✅ TAK (auto_enroll=False w konfiguracji) |
| Dedupe rerun passed | ❌ NIE (brak danych do testu) |

---

*Raport wygenerowany: 2026-04-22*
*Skrypt testowy: `tests/integration_test_bio_planet.py`*
*Raw JSON: `outputs/news/spendguru_market_news/20260422_140207_orlen_regranulat_integration_test.json`*
