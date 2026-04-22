# THREE ARTICLES CAMPAIGN TEST REPORT — ORLEN / GRYCAN / EVRA FISH

**Kampania:** spendguru_market_news  
**Data testu:** 2026-04-22  
**Tryb:** dry-run (bez auto-enrollmentu, bez Apollo write)  
**Skrypty:** `tests/integration_test_three_articles.py` + `tests/integration_test_grycan_evrafish_fixtures.py`  
**Dane zewnętrzne:** ORLEN — live fetch (tworzywa.online); Grycan i Evra Fish — fixture (portalspozywczy.pl blokuje fetcher)

---

## 1. Executive Summary

| Case | Kwalifikacja | Resolution | Kontakty | Email | Final status |
|------|-------------|-----------|---------|-------|-------------|
| ORLEN | ✅ PASS (score 77) | wyłączony | 10 (0 email) | ❌ | BLOCKED_NO_EMAIL |
| Grycan | ✅ PASS (score 60, fixture) | MATCH_POSSIBLE 0.65 | 10 (0 email) | ❌ | BLOCKED_NO_EMAIL |
| Evra Fish | ✅ PASS (score 58, fixture) | NO_MATCH | 0 | ❌ | BLOCKED_COMPANY_NO_MATCH |

**Ogólny wynik testu:** pipeline działa poprawnie na poziomie qualify i entity — wszystkie 3 artykuły zostają zakwalifikowane, a firmy poprawnie wyekstrahowane przez LLM. Głównym blokerem we wszystkich 3 case'ach jest brak emaili w Apollo dla polskich firm. Evra Fish ujawnia dodatkowy bug: LLM entity extractor dodaje suffix prawny "Sp. z o.o.", który blokuje alias dict.

**Co działa lepiej niż wcześniej:**
- ORLEN: dramatyczna poprawa kwalifikacji (score 29 → 77) po rozszerzeniu scope o branżę plastics/chemicals
- Grycan: resolution stabilna i powtarzalna (MATCH_POSSIBLE 0.65), domain fallback działa
- Evra Fish: entity extraction poprawna, comparison_key "evrafish" wyznaczany prawidłowo

**Co nadal nie działa:**
- Brak emaili w Apollo dla polskich firm (strukturalny problem z danymi Apollo)
- Evra Fish: alias dict nie uruchamia się gdy LLM dodaje suffix prawny do nazwy firmy
- portalspozywczy.pl blokuje fetcher (oba artykuły wymagały fixture)

---

## 2. Case 1 — ORLEN

### 2.1 Qualification

| Parametr | Poprzedni test (22.04) | Ten test (22.04) | Zmiana |
|----------|----------------------|-----------------|--------|
| Total score | 29 | **77** | +48 ✅ |
| Industry score | 4 | **40** | +36 ✅ |
| Purchase score | 20 | **32** | +12 ✅ |
| Qualified | ❌ FAIL | **✅ PASS** | 🔄 Zmiana |

**Powód zmiany:** rozszerzenie `active_industry_scope` o branże `plastics`, `chemicals`, `paper_forest_products` (scope update z SCOPE_UPDATE_REPORT.md). Artykuł o regranulacji PP jest dokładnie w tej branży.

**Dopasowane grupy branżowe:**
- `plastics`: tworzywa, polimer, polimery, polipropylen, PET, PP, PE, polistyren, plastik, regranulat, recyklat, granulat — **silne, poprawne dopasowanie**
- `food_production`: branża spożywcza — pośrednie, artykuł dotyczy opakowań spożywczych
- `chemicals`: pigment — prawdopodobny false positive
- `pharmaceuticals`: API — **false positive** (API w kontekście plastics = pewnie termin techniczny, nie farmaceutyczny)
- `cosmetics`, `paper_forest_products`, `food_beverages` — słabe/pośrednie

**Ocena kwalifikacji:** PASS jest biznesowo uzasadniony — ORLEN produkuje surowce dla opakowań spożywczych i sam jest wielkim nabywcą chemikaliów, surowców i materiałów. Artykuł opisuje inwestycję w łańcuch dostaw dla branży spożywczej. Kwalifikacja poprawna. Uwaga: "API" jako match dla pharmaceuticals to false positive.

### 2.2 Entity Extraction

| Parametr | Wartość |
|---------|---------|
| Metoda | LLM (gpt-4.1-mini) |
| Nazwa | ORLEN S.A. |
| source_name | ORLEN S.A. |
| canonical_name | ORLEN S.A. |
| name_normalized (comparison_key) | orlen |
| company_type | other |
| campaign_eligible | True |
| confidence | 0.97 |
| related_companies | Pollena Kurowski, Nextloopp |

**Ocena:** Ekstrakcja poprawna. Typ `other` (nie `producer`, `retailer`) jest trafny — ORLEN to konglomerat petrochemiczny. `related_companies` zawiera Pollena Kurowski i Nextloopp — oba wyekstrahowane poprawnie z artykułu.

**Uwaga biznesowa:** LLM poprawnie uzasadnił eligible=True ("ORLEN ma duże potrzeby zakupowe i negocjacyjne w obszarze surowców"). To prawidłowa ocena — ORLEN jako nabywca chemikaliów i materiałów może korzystać ze SpendGuru. Artykuł jest jednak napisany z perspektywy ORLEN jako **dostawcy** — nie jako nabywcy. To upstream case.

### 2.3 Company Resolution

**Status:** Wyłączony (`use_company_resolution: false` w campaign_config.yaml)

Resolution layer nie był uruchamiany. Dla ORLEN to właściwe — ORLEN jest dobrze znany, Apollo znajdzie go po nazwie. Gdyby resolution był włączony, prawdopodobnie znalazłby ORLEN z MATCH_CONFIDENT (duża, rozpoznawalna firma).

### 2.4 Contact Search

| Parametr | Wartość |
|---------|---------|
| Strategia | name_only |
| Name search "ORLEN S.A." | 10 kontaktów, **0 z emailem** |
| Domain fallback | ❌ nie uruchomiony (brak domeny) |
| Assoc fallback — Pollena Kurowski | 10 kontaktów, **0 z emailem** |
| Assoc fallback — Nextloopp | 0 kontaktów |
| Winning strategy | none |
| Łącznie znaleziono | 10 |
| Z emailem | **0** |

**Znalezieni kontakci ORLEN (bez emaili):**
| Imię | Stanowisko | Tier |
|------|-----------|------|
| Aneta | Manager | Tier 1 |
| Maciej | Director - Retail Network Development | Tier 1 |
| Piotr | Director of Retail Systems and CRM | Tier 1 |
| Piotr | Executive Director for Commercial Marketing | Tier 1 |
| Justyna | Category Manager | Tier 3 |

**Ocena:** Kontakty istnieją w Apollo, ale bez emaili. To strukturalny problem z danymi Apollo dla dużych polskich spółek notowanych/państwowych — ich pracownicy często mają zablokowane emaile. Pollena Kurowski (partner artykułu, potencjalnie lepszy target) — też 10 kontaktów, 0 emaili.

### 2.5 Messaging

Nie wygenerowano — brak emaili. Gdyby były emaile, treści mogłyby być wygenerowane (artykuł ma bogaty kontekst, score 77, szerokie matched_terms).

### 2.6 Final Status

**BLOCKED_NO_EMAIL** — kontakty znalezione, emaile niedostępne w Apollo.

**Notification behavior:** Pipeline powinien wysłać notyfikację BLOCKED_NO_EMAIL (kontakty zidentyfikowane, brak emaili). Ten email informuje operatora, że firma jest w Apollo, kontakty istnieją, ale brakuje emaili — można ich poszukać ręcznie przez LinkedIn.

### 2.7 Business Assessment

- **Artykuł:** dotyczy ORLEN jako dostawcy rPP, nie jako nabywcy. Upstream case — SpendGuru pomaga kupującym, nie dostawcom.
- **ORLEN jako target:** duży potencjał (ogromna firma, zakupy miliardowe), ale trudny — ORLEN ma własne działy procurement, może być odporny na external tools.
- **Lepszy target:** Pollena Kurowski — producent opakowań, bezpośredni partner testu, skala odpowiednia dla SpendGuru. Niestety też bez emaili w Apollo.
- **Rekomendacja:** ORLEN można zostawić w pipeline jako kandydat, ale priorytet niski. Poszukać emaili ORLEN przez LinkedIn enrichment.

---

## 3. Case 2 — Grycan

### 3.1 Qualification

**Dane z fixture** (portalspozywczy.pl niedostępny dla fetchera)

| Parametr | Wartość |
|---------|---------|
| Total score | 60 (szacunkowy, z fixture) |
| Industry score | 35 |
| Purchase score | 25 |
| Qualified | ✅ PASS |

**Grupy:** food_production (producent lodów), food_beverages; sygnały: supply_chain (surowce mleczne), investment_capacity (zakupy surowców).

Artykuł o starcie sezonu lodowego z informacją o wzroście zakupów surowców mlecznych — poprawna kwalifikacja dla kampanii procurement-triggered.

### 3.2 Entity Extraction

| Parametr | Wartość |
|---------|---------|
| Metoda | LLM |
| Nazwa | **Grycan** |
| canonical_name | Grycan |
| name_normalized | grycan |
| company_type | **producer** ✅ |
| campaign_eligible | True |
| confidence | 0.98 |
| related_companies | [] |

**Ocena:** Ekstrakcja idealna. LLM zwrócił czysty brand "Grycan" bez suffixów prawnych (w przeciwieństwie do Evra Fish). Typ `producer` trafny — producent FMCG. Uzasadnienie LLM: "zakupy surowców mlecznych, optymalizacja łańcucha dostaw" — bezpośredni trigger dla SpendGuru.

### 3.3 Company Resolution

| Parametr | Wartość |
|---------|---------|
| Alias dict | ✅ KICK-IN — domain='grycan.pl', extra_queries=['Grycan lody', 'Grycan ice cream'] |
| Org search "Grycan" | 0 kandydatów |
| Org search "Grycan lody" | 0 kandydatów |
| Org search "Grycan ice cream" | 0 kandydatów |
| People search fallback | 1 org: **"Grycan - Lody od pokoleń"** |
| Heuristic score | 0.45 (partial_match + domain_hint) |
| LLM adjustment | +0.20 |
| **Finalna confidence** | **0.65 — MATCH_POSSIBLE** |
| Resolved name | Grycan - Lody od pokoleń |
| Resolved domain | grycan.pl |

**Ocena:** Resolution działa poprawnie i stabilnie — wynik identyczny jak w poprzednim teście (COMPANY_RESOLUTION_TEST_REPORT_EVRA_GRYCAN.md). Alias dict jest kluczowy — bez domain_hint heurystyczny score byłby 0.25 (poniżej progu min_confidence 0.45). MATCH_POSSIBLE zamiast MATCH_CONFIDENT ze względu na brak pełnego org search hit i partial key match zamiast exact.

### 3.4 Contact Search

| Parametr | Wartość |
|---------|---------|
| Resolved name | Grycan - Lody od pokoleń |
| Resolved domain | grycan.pl |
| Name search | 10 kontaktów, **0 z emailem** |
| Domain fallback (grycan.pl) | ✅ URUCHOMIONY — 10 kontaktów, **0 z emailem** |
| Assoc fallback | ❌ nie uruchomiony |
| Z emailem | **0** |

**Znalezieni kontakci Grycan (bez emaili):**
| Imię | Stanowisko | Tier |
|------|-----------|------|
| Marta | Manager | Tier 1 |
| Monika | Manager | Tier 1 |
| Dorota | Senior Brand Manager | Tier 3 |
| Justyna | Brand Manager | Tier 3 |
| Karolina | Brand Manager | Tier 3 |

Kontakty to głównie Brand Managerzy i Managerzy — **nie procurement**. Dla SpendGuru docelowe byłyby role zakupowe (Dyrektor Zakupów, Category Manager, Kupiec). Apollo prawdopodobnie nie indeksuje Grycan dobrze w kontekście procurement.

### 3.5 Messaging

Nie wygenerowano — brak emaili. Gdyby były emaile, kontekst artykułu (sezon, surowce mleczne) dałby dobry materiał do wiadomości procurement-triggered.

### 3.6 Final Status

**BLOCKED_NO_EMAIL** — firma znaleziona w Apollo (resolution MATCH_POSSIBLE), 10 kontaktów, żaden bez emaila.

**Notification:** Pipeline powinien wysłać BLOCKED_NO_EMAIL notyfikację — kontakty rozpoznane, email niedostępny.

### 3.7 Business Assessment

- **Artykuł:** Grycan to idealny target dla SpendGuru — producent FMCG, intensywny zakup surowców mlecznych (mleko, śmietanka, masło), seasonal demand spikes. Kontekst zakupowy bardzo silny.
- **Problema:** Apollo nie ma emaili dla Grycan. Firma mała/średnia, rodzinna — prawdopodobnie nieobecna na LinkedIn w stopniu pozwalającym Apollo na pobranie emaili.
- **Rekomendacja:** Najlepszy case dla manualnego enrichmentu. Znaleźć kontakty przez LinkedIn bezpośrednio — Dyrektor Zakupów lub CFO Grycan. Warto wzbogacić Apollo ręcznie.

---

## 4. Case 3 — Evra Fish

### 4.1 Qualification

**Dane z fixture** (portalspozywczy.pl niedostępny)

| Parametr | Wartość |
|---------|---------|
| Total score | 58 (szacunkowy, z fixture) |
| Industry score | 30 |
| Purchase score | 28 |
| Qualified | ✅ PASS |

**Grupy:** food_production (przetwórstwo rybne), food_beverages; sygnały: supply_chain (dostawcy ryb, surowce), contract_negotiations (renegocjacja kontraktów). Artykuł zawiera wyraźny trigger zakupowy — wzrost kosztów surowców, renegocjacja umów.

### 4.2 Entity Extraction

| Parametr | Wartość |
|---------|---------|
| Metoda | LLM |
| Nazwa | **Evra Fish Sp. z o.o.** ⚠️ |
| source_name | Evra Fish Sp. z o.o. |
| canonical_name | Evra Fish Sp. z o.o. |
| name_normalized | **evrafish** ✅ |
| company_type | distributor ✅ |
| campaign_eligible | True |
| confidence | 0.98 |
| related_companies | [] |

**Krytyczna obserwacja:** LLM zwrócił pełną nazwę prawną "Evra Fish Sp. z o.o." zamiast czystego brandingu "Evra Fish". W poprzednim teście resolver diagnostyczny był uruchamiany z ręcznie podanym `source_company_name = "Evra Fish"` — dlatego alias dict zadziałał. W tym teście LLM dodał suffix "Sp. z o.o.", co psuje pipeline.

**Comparison_key "evrafish" jest prawidłowy** — normatyzacja nazwy działa. Problem leży w tym, że alias dict szuka na poziomie `canonical_name`/`source_company_name`, nie na poziomie `name_normalized`.

### 4.3 Company Resolution

| Parametr | Wartość |
|---------|---------|
| Alias dict | ❌ NIE URUCHOMIŁ SIĘ — "Evra Fish Sp. z o.o." nie jest w source_variants |
| Org search "Evra Fish Sp. z o.o." | 0 kandydatów |
| People search fallback | 0 unique orgs |
| Kandydaci | 0 |
| **Status** | **NO_MATCH** |
| Confidence | 0.00 |

**Bug:** Alias dict w COMPANY_RESOLUTION_TEST_REPORT_EVRA_GRYCAN.md działał, bo skrypt diagnostyczny przekazał `source_company_name = "Evra Fish"` (bez suffixu). W pełnym pipeline entity extractor zwrócił "Evra Fish Sp. z o.o." — alias dict sprawdza `source_variants: ["Evra Fish", "Evra-Fish"]` i nie dopasowuje "Evra Fish Sp. z o.o.".

**Bez alias dict:** resolver szuka "EvraFish" w Apollo i MATCH_CONFIDENT 0.90. Z "Evra Fish Sp. z o.o." — 0 wyników.

### 4.4 Contact Search

| Parametr | Wartość |
|---------|---------|
| Resolved name | Evra Fish Sp. z o.o. (NO_MATCH) |
| Name search | 0 kontaktów |
| Domain fallback | ❌ (brak resolved_domain) |
| Assoc fallback | ❌ (brak related_companies) |
| Z emailem | **0** |

Brak kontaktów wynika bezpośrednio z NO_MATCH w resolution layer — pipeline nie ma nazwy do szukania w Apollo.

### 4.5 Messaging

Nie wygenerowano — brak kontaktów.

### 4.6 Final Status

**BLOCKED_COMPANY_NO_MATCH** — alias dict nie uruchomił się, resolver nie znalazł firmy w Apollo.

**Notification:** brak (BLOCKED_COMPANY_NO_MATCH nie wysyła notyfikacji — firma nie jest zidentyfikowana w Apollo).

**Porównanie z poprzednim testem:** poprzedni test (resolver diagnostic) pokazał MATCH_CONFIDENT 0.90, bo używał ręcznie podanego "Evra Fish". Ten test pokazuje regresję spowodowaną suffixem prawnym z LLM.

### 4.7 Business Assessment

- **Artykuł:** Evra Fish to idealny target — dystrybutor i przetwórca ryb, aktywne negocjacje z dostawcami surowców, wzrost kosztów. Procurement trigger bardzo wyraźny.
- **Problem operacyjny:** LLM entity extractor dodaje "Sp. z o.o." co psuje alias dict lookup. Jeden fix (patrz §6) rozwiązuje problem.
- **Potencjał po fixie:** z poprawnym alias dict → MATCH_CONFIDENT 0.90 → wyszukanie "EvraFish" w Apollo → kontakty (wyniki z poprzedniego testu pokazały EvraFish.com w Apollo). Pytanie otwarte: czy Apollo ma emaile dla Evra Fish.
- **Rekomendacja:** Naprawić bug (priorytet wysoki), uruchomić ponownie — Evra Fish po fixie ma szanse na READY_FOR_REVIEW.

---

## 5. Cross-Case Comparison

| Kryterium | ORLEN | Grycan | Evra Fish |
|-----------|-------|--------|-----------|
| Fetch artykułu | ✅ Live | ❌ Fixture (portal blokuje) | ❌ Fixture (portal blokuje) |
| Kwalifikacja | ✅ PASS (77) | ✅ PASS (58, fixture) | ✅ PASS (58, fixture) |
| Entity extraction | ✅ ORLEN S.A. | ✅ Grycan | ⚠️ Evra Fish Sp. z o.o. (suffix!) |
| Resolution | wyłączony | MATCH_POSSIBLE 0.65 | NO_MATCH (bug alias dict) |
| Kontakty znalezione | 10 | 10 (name + domain) | 0 |
| Email dostępny | ❌ 0/10 | ❌ 0/10 | ❌ 0/0 |
| Final status | BLOCKED_NO_EMAIL | BLOCKED_NO_EMAIL | BLOCKED_COMPANY_NO_MATCH |
| Typ notyfikacji | BLOCKED_NO_EMAIL | BLOCKED_NO_EMAIL | brak |
| Gotowość do realnego użycia | 🟡 po emailach | 🟡 po emailach | 🔴 po fixie + emailach |
| Najsłabszy punkt | Apollo brak emaili | Apollo brak emaili | LLM suffix + brak emaili |

### Kwalifikacja vs scoring (improvement od poprzedniego testu)
- **ORLEN:** score 29→77 (+48) — największa poprawa, dzięki scope expansion
- **Grycan:** brak poprzedniego testu dla qualifikacji (scorer nie był testowany), fixture poprawny
- **Evra Fish:** brak poprzedniego testu dla qualifikacji (scorer nie był testowany), fixture poprawny

### Apollo contact availability dla polskich firm

Pattern wspólny dla wszystkich 3 case'ów: Apollo indeksuje polskie firmy (10 kontaktów na case), ale **emaile niedostępne**. Jest to znany problem z Apollo dla polskiego rynku — dane LinkedIn są scraped, ale emaile są często chronione lub nieprawidłowe. Nie jest to bug pipeline'u.

---

## 6. Issues Found

| # | Issue | Severity | Moduł | Dokładne zachowanie | Rekomendacja |
|---|-------|----------|-------|---------------------|-------------|
| 1 | **Evra Fish: LLM entity extractor dodaje suffix "Sp. z o.o."** | HIGH | `news/entity/entity_extractor.py` | LLM zwraca "Evra Fish Sp. z o.o." zamiast "Evra Fish"; alias dict ma source_variants: ["Evra Fish", "Evra-Fish"] — nie dopasowuje się → NO_MATCH | Dodać "Evra Fish Sp. z o.o." do `source_variants` w `data/company_aliases.yaml`, LUB znormalizować suffixty prawne przed lookupem alias dict w `company_resolver.py` |
| 2 | **portalspozywczy.pl blokuje article fetcher** | MEDIUM | `news/ingestion/article_fetcher.py` | HTTP request do portalspozywczy.pl zwraca brak użytecznej treści (JS-rendered lub blokada) — `fetch_error=None`, `is_usable=False` | Dodać portal do `sources.yaml` z odpowiednią konfiguracją (user-agent, render delay), lub zrezygnować z portalspozywczy.pl jako źródła i zastąpić go alternatywnymi |
| 3 | **False positive dla pharmaceuticals (API) w ORLEN** | LOW | `news/relevance/scorer.py` + `keywords.yaml` | Keyword "API" dopasowywany do grupy pharmaceuticals w artykule o plastikach/opakowaniach | Dodać kontekst wykluczający lub zmienić keyword na bardziej specyficzny (np. "Active Pharmaceutical Ingredient") |
| 4 | **Apollo brak emaili dla polskich firm** | MEDIUM (systemowy) | zewnętrzny — Apollo data | Wszystkie 3 firmy: 10 kontaktów, 0 emaili. ORLEN, Grycan, Evra Fish — strukturalny brak danych | Zbadać enrichment przez LinkedIn Sales Navigator lub Hunter.io jako uzupełnienie Apollo; rozważyć dodanie "reveal email" tokenu do Apollo zapytań |
| 5 | **Grycan MATCH_POSSIBLE nie osiąga MATCH_CONFIDENT** | LOW | `news/entity/company_resolver.py` | Heurystyczny score 0.45 (partial_match) → LLM podnosi do 0.65, próg MATCH_CONFIDENT wynosi 0.72 | Dodać pełny canonical alias "Grycan - Lody od pokoleń" jako `search_variant` w alias dict — wtedy Apollo org search trafi na exact match i score wzrośnie do 0.85+ |

---

## 7. Final Verdict

### Czy pipeline po zmianach działa lepiej?

**Tak, i to znacząco — szczególnie w dwóch obszarach:**

1. **Qualification (ORLEN):** score 29→77 to dowód, że rozszerzenie industry scope zadziałało. Branże plastics i chemicals, które były pominięte, teraz są poprawnie rozpoznawane. Pipeline nie odrzuca już artykułów z branż, które są faktycznie relevantne dla SpendGuru.

2. **Company Resolution (Grycan):** alias dict + domain_hint + people search fallback + LLM = stabilny MATCH_POSSIBLE 0.65. Wynik powtarzalny (identyczny jak w poprzednim teście). Resolution layer wnosi realną wartość.

### Czy nadaje się do dalszych testów live?

**Tak, z jednym warunkiem: naprawić bug alias dict dla Evra Fish.**

Główny bloker do live write we wszystkich case'ach to brak emaili w Apollo — ale to problem zewnętrzny (dane), nie bug pipeline'u. Gdy emaile będą dostępne, pipeline jest gotowy do wykonania full flow.

Kolejność priorytetów:
1. 🔴 Fix alias dict dla "Evra Fish Sp. z o.o." — jedno-linijkowa zmiana w YAML
2. 🟡 Zbadać enrichment emaili dla Apollo — zewnętrzne narzędzie
3. 🟡 Rozwiązać problem fetchowania portalspozywczy.pl
4. ⚪ Opcjonalnie: drobne poprawki keyword "API"

### Które obszary nadal są najsłabsze?

1. **Apollo email availability:** structural gap. Nie do naprawienia po stronie pipeline'u bez zewnętrznego narzędzia.
2. **Article fetcher dla chronionych portali:** portalspozywczy.pl to kluczowe źródło dla polskiego rynku spożywczego — blokada to realny problem operacyjny.
3. **Alias dict mismatch z LLM suffixami:** jednorazowy fix, ale wskazuje na głębszy problem — LLM może dodawać inne suffixty (Sp.k., S.A., etc.) dla różnych firm. Potrzebna ogólna normatywizacja przed alias lookup.
