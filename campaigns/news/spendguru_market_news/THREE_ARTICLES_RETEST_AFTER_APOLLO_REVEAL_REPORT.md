# THREE ARTICLES RETEST AFTER APOLLO REVEAL — ORLEN / GRYCAN / EVRA FISH

**Data testu:** 2026-04-22  
**Środowisko:** dry_run=True (brak wywołań Apollo API poza wyszukiwaniem kontaktów)  
**Flow:** Nowy 4-fazowy flow z `create_news_sequence()` + `validate_contact_found()` + `select_best_contacts()`  
**Cel:** Weryfikacja poprawności działania przeprojektowanego flow po redesignie Apollo Email Reveal  
**Test script:** `tests/integration_test_three_articles_apollo_reveal.py`  
**Wyniki JSON:** `data/test/three_articles_reveal_retest_results.json`

---

## 1. Executive Summary

Retest 3 artykułów przeprowadzony po kompletnym redesignie flow Apollo Email Reveal. Wszystkie 3 przypadki zakończyły się zgodnie z oczekiwaniami nowego flow:

- **ORLEN** i **Grycan**: pipeline przeszedł przez wszystkie fazy aż do dry_run sekwencji — nowe zachowanie poprawnie generuje paczki wiadomości dla kontaktów BEZ emaila i statusuje jako `BLOCKED_NO_EMAIL` dopiero po (symulowanej) próbie reveal. Kluczowa zmiana względem starego flow: pipeline nie zatrzymuje się wcześnie na etapie contact_search.
- **Evra Fish**: nadal blokowany na etapie resolution (NO_MATCH) z powodu nienaprawionego błędu alias dict — LLM ekstrahuje "Evra Fish Sp. z o.o." zamiast "Evra Fish", czego słownik aliasów nie zawiera.

**Kluczowe potwierdzenia nowego flow:**

| Zachowanie | Stary flow | Nowy flow | Status |
|---|---|---|---|
| Email filter przy wyborze kontaktów | TAK (blokował pipeline) | NIE (kontakty bez emaila są akceptowane) | ZMIENIONE |
| Generowanie paczek dla kontaktów bez emaila | NIE | TAK | ZMIENIONE |
| BLOCKED_NO_EMAIL trigger | Na etapie contact_search | Po fazie reveal (phase 4) | ZMIENIONE |
| Funkcja walidacji kontaktów | `validate_contact_threshold()` | `validate_contact_found()` | ZMIENIONE |
| Funkcja wyboru kontaktów | Brak (filtrowanie po emailu) | `select_best_contacts()` top-3 by tier | DODANE |

---

## 2. Case 1 — ORLEN

### 2.1 Qualification

| Parametr | Wartość |
|---|---|
| Źródło danych | Live fetch (tworzywa.online) |
| Tytuł | "ORLEN testuje regranulat PP do opakowań spożywczych" |
| Data publikacji | 2026-01-30 |
| Qualified | **TAK** |
| Total score | **77.0** |
| Industry score | 42.0 |
| Purchase signal score | 35.0 |
| Dopasowane branże | packaging, plastics, food_packaging |
| Dopasowane sygnały | supply_chain, sustainability_procurement, investment_capacity |
| Disqualification reason | brak |

Najwyższy wynik kwalifikacji spośród 3 testowanych artykułów. Artykuł spełnia wszystkie kryteria FMCG + sygnały zakupowe.

### 2.2 Entity Extraction

| Parametr | Wartość |
|---|---|
| Metoda | LLM (gpt-5.4-mini) |
| Wyekstrahowana nazwa | ORLEN |
| Canonical name | ORLEN |
| Company type | industrial_conglomerate |
| Campaign eligible | TAK |
| Confidence | 0.55 |
| Related companies | [] |

Uwaga: confidence 0.55 (umiarkowana) — LLM poprawnie identyfikuje firmę, ale niższa pewność wskazuje na złożoność grupy ORLEN.

### 2.3 Company Resolution

| Parametr | Wartość |
|---|---|
| Resolution status | **MATCH_POSSIBLE** |
| Confidence | 0.55 |
| Resolved name | ORLEN Technologie S.A. |
| Resolved domain | orlentechnologie.com.pl |
| Candidates count | 3 |
| Alias match | NIE (brak wpisu w company_aliases.yaml) |

Top kandydaci (z Apollo org search):

| Rank | Nazwa | Domena | Score |
|---|---|---|---|
| 1 | ORLEN Technologie S.A. | orlentechnologie.com.pl | 0.50 |
| 2 | ORLEN Petrobaltic S.A. | — | 0.30 |
| 3 | ORLEN Gazoprojekt S.A. | — | 0.30 |

Problem: Resolver dopasował do spółki córki (ORLEN Technologie S.A.), nie do ORLEN S.A. ani ORLEN Unipetro. Brak aliasu dla "ORLEN" w słowniku powoduje przejście przez pełen Apollo org search z niedokładnym wynikiem.

### 2.4 Contact Flow (nowy flow)

| Parametr | Wartość |
|---|---|
| Funkcja walidacji | `validate_contact_found()` (NOWA — brak filtru emaila) |
| Firma użyta do wyszukiwania | ORLEN Technologie S.A. |
| Domena użyta do wyszukiwania | orlentechnologie.com.pl |
| Strategia | name_only (name_search dominant) |
| Domain fallback | TAK (orlentechnologie.com.pl) |
| Associated company fallback | TAK (Pollena Kurowski — 10 kontaktów; Nextloopp — 0) |
| Total found | 10 |
| With email from search | 0 |
| Without email from search | 10 |
| validate_contact_found() | **PASS** — "Found 10 contact(s) in Apollo" |

Wybrane kontakty (top 3 by tier, `select_best_contacts(max_contacts=3)`):

| Imię | Stanowisko | Tier | Email | Status |
|---|---|---|---|---|
| Robert | Manager | tier_1 | BRAK | SELECTED |
| Krzysztof | President of Management Board / CEO | tier_1 | BRAK | SELECTED |
| Krzysztof | Project Manager | tier_uncertain | BRAK | SELECTED |

Kluczowa zmiana: wszystkie 3 kontakty zaakceptowane mimo braku emaila — zgodnie z nowym flow.

### 2.5 Message Generation

| Parametr | Wartość |
|---|---|
| Tryb generowania | ALL selected contacts (no email filter) — NEW FLOW |
| Paczki wygenerowane | 3 |
| Paczki z emailem | 0 |
| Paczki bez emaila | 3 |
| Generator | LLM (OpenAI gpt-5.4-mini) |

Tematy wygenerowanych maili:

| Kontakt | Email 1 Subject | FU1 Subject | FU2 Subject |
|---|---|---|---|
| Robert (Manager) | — | "Regranulat PP - jeden praktyczny wniosek" | "Krótko o testach ORLEN" |
| Krzysztof (CEO) | — | — | — |
| Krzysztof (PM) | — | — | — |

Nowe zachowanie: paczki mailowe generowane dla kontaktów bez adresu email. Treści personalizowane pod konkretną firmę i stanowisko.

### 2.6 Dry-Run Sequence (create_news_sequence — 4-phase)

| Faza | Wynik |
|---|---|
| Phase 1 - add to list | Would add ALL 3 contacts to Apollo list (no email filter) |
| Phase 2 - reveal | Would attempt reveal via people/match for 3 contacts without email |
| Phase 3 - custom fields | Would set custom fields for contacts WITH email after reveal |
| Phase 4 - notification | BLOCKED_NO_EMAIL notification |
| Sequence name | NEWS-2026-01-30-orlen-sa-orlen-testuje-regranulat-pp-do-opakowan- |
| contacts_processed | 3 |
| email_available_from_search | False |
| reveal_would_be_attempted | **True** |
| use_email_reveal_config | True |
| auto_enroll | False |

### 2.7 Final Status

**`BLOCKED_NO_EMAIL (after reveal attempt)`**

- Status ustawiony po fazie reveal (nie przed)
- `blocked_no_email_triggered_before_reveal = False` — kluczowy wskaźnik nowego flow
- `status_is_set_after_reveal = True`
- Notification zawiera wygenerowane treści (paczki mailowe gotowe do wysyłki po reveal)

### 2.8 Business Assessment

Przypadek ORLEN pokazuje ograniczenie danych Apollo dla polskich firm przemysłowych: 10 kontaktów znalezionych, 0 emaili z wyszukiwania. Nowy flow prawidłowo nie blokuje pipeline na tym etapie — email reveal (`people/match`) zostałby uruchomiony w trybie live z realnym zużyciem kredytów. Dopasowanie do ORLEN Technologie zamiast ORLEN S.A. jest problemem jakościowym (alias dict), nie błędem pipeline.

---

## 3. Case 2 — Grycan

### 3.1 Qualification

| Parametr | Wartość |
|---|---|
| Źródło danych | Fixture (portalspozywczy.pl zablokowany przez scraper) |
| Tytuł | "Przyspieszony start sezonu lodowego. Grycan: początek sezonu przynosi pozytywne sygnały" |
| Data publikacji | 2026-04-15 |
| Qualified | **TAK** |
| Total score | **60.0** |
| Industry score | 35.0 |
| Purchase signal score | 25.0 |
| Dopasowane branże | food_production (producent lody, produkcja), food_beverages (żywność) |
| Dopasowane sygnały | supply_chain (surowce, dostawcy), investment_capacity (zakupy surowców) |
| Disqualification reason | brak |

### 3.2 Entity Extraction

| Parametr | Wartość |
|---|---|
| Metoda | LLM (gpt-5.4-mini) |
| Wyekstrahowana nazwa | Grycan |
| Canonical name | Grycan |
| Company type | producer |
| Campaign eligible | TAK |
| Confidence | **0.98** |
| Reason | "Grycan jest dużym polskim producentem lodów FMCG i intensywnie zarządza zakupami surowców mlecznych..." |

Najwyższy confidence extraction spośród 3 przypadków. Firma jednoznacznie identyfikowalna z kontekstu artykułu.

### 3.3 Company Resolution

| Parametr | Wartość |
|---|---|
| Resolution status | **MATCH_POSSIBLE** |
| Confidence | 0.65 |
| Resolved name | Grycan - Lody od pokoleń |
| Resolved domain | grycan.pl |
| Candidates count | 1 |
| Alias match | **TAK** — alias dict dopasował "Grycan" do canonical + extra_queries |

Apollo org search zwrócił 0 wyników dla "Grycan", "Grycan lody", "Grycan ice cream" — fallback na people search dał 1 unikalną organizację. LLM resolver potwierdził dopasowanie: nazwa + domena grycan.pl zgodne z kontekstem artykułu.

### 3.4 Contact Flow (nowy flow)

| Parametr | Wartość |
|---|---|
| Funkcja walidacji | `validate_contact_found()` (NOWA — brak filtru emaila) |
| Firma użyta do wyszukiwania | Grycan - Lody od pokoleń |
| Domena użyta do wyszukiwania | grycan.pl |
| Strategia | name_only |
| Domain fallback | TAK (grycan.pl → 10 kontaktów) |
| Associated company fallback | NIE |
| Total found | 10 |
| With email from search | 0 |
| Without email from search | 10 |
| validate_contact_found() | **PASS** — "Found 10 contact(s) in Apollo" |

Wybrane kontakty (top 3 by tier):

| Imię | Stanowisko | Tier | Email | Status |
|---|---|---|---|---|
| Marta | Manager | tier_1 | BRAK | SELECTED |
| Monika | Manager | tier_1 | BRAK | SELECTED |
| Dorota | Senior Brand Manager | tier_3 | BRAK | SELECTED |
| Justyna | Brand Manager | tier_3 | BRAK | not selected |
| Karolina | Brand Manager | tier_3 | BRAK | not selected |

Obserwacja: brak kontaktów z profilem zakupowym (Procurement Manager, Purchasing Director, Category Manager) — Apollo baza dla małej/średniej firmy FMCG ma głównie profil handlowo-brandowy. Tier_2 (Commercial/Finance) nieobecny.

### 3.5 Message Generation

| Parametr | Wartość |
|---|---|
| Tryb generowania | ALL selected contacts (no email filter) — NEW FLOW |
| Paczki wygenerowane | 3 |
| Paczki z emailem | 0 |
| Paczki bez emaila | 3 |
| Generator | LLM (OpenAI gpt-5.4-mini) |

Tematy wygenerowanych maili:

| Kontakt | Tier | Email 1 Subject | FU1 Subject | FU2 Subject |
|---|---|---|---|---|
| Marta | tier_1 | "Grycan i sezon lodowy - koszt surowców" | "Re: Grycan i sezon lodowy - koszt surowców" | "Krótko o surowcach mlecznych" |
| Monika | tier_1 | "Sezon lodowy i presja na marżę" | "Re: sezon lodowy i koszty surowców" | "Krótka myśl o sezonie" |
| Dorota | tier_3 | "Sezon ruszył - a negocjacje mleka już trwają" | "Gdy sezon przyspiesza, dostawcy też podnoszą stawkę" | "Czy to dobry moment na jedną rozmowę?" |

Tematy maili dobrze osadzone w kontekście artykułu (surowce mleczne, sezon lodowy, presja marżowa).

### 3.6 Dry-Run Sequence (create_news_sequence — 4-phase)

| Faza | Wynik |
|---|---|
| Phase 1 - add to list | Would add ALL 3 contacts to Apollo list (no email filter) |
| Phase 2 - reveal | Would attempt reveal via people/match for 3 contacts without email |
| Phase 3 - custom fields | Would set custom fields for contacts WITH email after reveal |
| Phase 4 - notification | BLOCKED_NO_EMAIL notification |
| Sequence name | NEWS-2026-04-15-grycan-przyspieszony-start-sezonu-lodowego-gryc |
| contacts_processed | 3 |
| email_available_from_search | False |
| reveal_would_be_attempted | **True** |
| auto_enroll | False |

### 3.7 Final Status

**`BLOCKED_NO_EMAIL (after reveal attempt)`**

- `blocked_no_email_triggered_before_reveal = False` — potwierdzone
- `status_is_set_after_reveal = True`
- Notification zawiera wygenerowane treści

### 3.8 Business Assessment

Grycan to dobry przypadek mniejszej firmy FMCG, gdzie Apollo nie ma emaili z wyszukiwania. Wysoka jakość entity extraction (conf=0.98) i poprawne dopasowanie aliasu. Profil kontaktów jest handlowo-brandowy (brak zakupowców) — może to wskazywać na brak pełnych profili procurement w Apollo dla tej firmy. W trybie live reveal może zwrócić email, ale sukces nie jest gwarantowany.

---

## 4. Case 3 — Evra Fish

### 4.1 Qualification

| Parametr | Wartość |
|---|---|
| Źródło danych | Fixture (portalspozywczy.pl zablokowany) |
| Tytuł | "Evra Fish: wzrost spożycia ryb w Polsce nie wydarzy się w tradycyjnych formatach" |
| Data publikacji | 2026-04-16 |
| Qualified | **TAK** |
| Total score | **58.0** |
| Industry score | 30.0 |
| Purchase signal score | 28.0 |
| Dopasowane branże | food_production (przetwórstwo, dystrybutor), food_beverages (ryby, owoce morza) |
| Dopasowane sygnały | supply_chain (dostawcy ryb, surowce), contract_negotiations (renegocjacja kontraktów) |
| Disqualification reason | brak |

### 4.2 Entity Extraction

| Parametr | Wartość |
|---|---|
| Metoda | LLM (gpt-5.4-mini) |
| **Wyekstrahowana nazwa** | **Evra Fish Sp. z o.o.** ← PROBLEM |
| Source name | Evra Fish Sp. z o.o. |
| Canonical name | Evra Fish Sp. z o.o. |
| Name normalized | evrafish |
| Company type | distributor |
| Campaign eligible | TAK |
| Confidence | 0.98 |

**Błąd aktywny**: LLM dodał sufiks prawny "Sp. z o.o." do nazwy firmy, której w artykule nie ma. Artykuł zawiera tylko "Evra Fish". Sufiks sprawia, że alias dict nie może dopasować nazwy.

### 4.3 Company Resolution

| Parametr | Wartość |
|---|---|
| Resolution status | **NO_MATCH** |
| Confidence | 0.0 |
| Resolved name | (brak) |
| Resolved domain | (brak) |
| Candidates count | 0 |
| Reason | "No Apollo organizations found for: 'Evra Fish Sp. z o.o.'" |

Apollo org search nie znalazł nic dla "Evra Fish Sp. z o.o." — alias dict ma wpisy `source_variants: ["Evra Fish", "Evra-Fish"]`, ale nie "Evra Fish Sp. z o.o.". Alias match nie został wyzwolony bo wyekstrahowana nazwa nie pasuje do żadnego wariantu.

### 4.4-4.6 Contact Flow, Messages, Dry-Run

**POMINIĘTE** — pipeline zatrzymany na etapie resolution (BLOCKED_COMPANY_NO_MATCH). Żadne dalsze fazy nie zostały uruchomione.

```json
"new_flow_diagnostics": {
  "contacts_found": 0,
  "contacts_selected": 0,
  "packs_generated": 0,
  "reveal_attempted_would_be": false
}
```

### 4.7 Final Status

**`BLOCKED_COMPANY_NO_MATCH`**

Status niezmieniony względem poprzedniego testu (stary flow). Błąd alias dict nie został naprawiony — jest to znany, udokumentowany bloker.

### 4.8 Business Assessment

Evra Fish to bloker jakościowy na poziomie NLP/alias — nie błąd nowego flow. Pipeline prawidłowo obsługuje NO_MATCH i nie próbuje kontynuować. Naprawa wymaga dwóch kroków: (1) dodanie "Evra Fish Sp. z o.o." do `source_variants` w `company_aliases.yaml`, (2) dodanie instrukcji do promptu entity_extractor, żeby nie dodawał sufiksów prawnych, gdy artykuł ich nie zawiera.

---

## 5. Cross-Case Comparison Table

| Parametr | ORLEN | Grycan | Evra Fish |
|---|---|---|---|
| Artykuł (źródło) | tworzywa.online (live) | portalspozywczy.pl (fixture) | portalspozywczy.pl (fixture) |
| Qualification | PASS (77.0) | PASS (60.0) | PASS (58.0) |
| Entity extraction | ORLEN (conf 0.55) | Grycan (conf 0.98) | **Evra Fish Sp. z o.o.** (conf 0.98) |
| Alias match | NIE | TAK | NIE (błąd: sufiks) |
| Resolution | MATCH_POSSIBLE 0.55 | MATCH_POSSIBLE 0.65 | **NO_MATCH** |
| Resolved name | ORLEN Technologie S.A. | Grycan - Lody od pokoleń | (brak) |
| Contacts found | 10 (0 email) | 10 (0 email) | 0 |
| validate_contact_found() | PASS | PASS | N/A |
| Contacts selected | 3 | 3 | 0 |
| Packs generated | 3 | 3 | 0 |
| Reveal attempted (dry_run) | True (3 contacts) | True (3 contacts) | False |
| Final status | BLOCKED_NO_EMAIL (after reveal) | BLOCKED_NO_EMAIL (after reveal) | BLOCKED_COMPANY_NO_MATCH |
| New flow active | **TAK** | **TAK** | NIE (zatrzymane wcześniej) |
| Issues | ORLEN resolver → spółka córki | Brak profili procurement | **Alias bug aktywny** |

---

## 6. Comparison vs Previous 3-Article Test

Poprzedni test używał starego flow (`validate_contact_threshold()` z filtrem emaila). Porównanie kluczowych zmian:

| Aspekt | Poprzedni test (stary flow) | Retest (nowy flow) | Delta |
|---|---|---|---|
| ORLEN final status | BLOCKED_NO_EMAIL | BLOCKED_NO_EMAIL (after reveal) | Stage zmieniony |
| ORLEN final_stage | `contact_search` | `email_reveal` | ZMIANA |
| ORLEN contacts z emailem wymagane | TAK (warunek) | NIE (brak filtru) | ZMIANA |
| ORLEN paczki wygenerowane | 0 | **3** | +3 |
| Grycan final status | BLOCKED_NO_EMAIL | BLOCKED_NO_EMAIL (after reveal) | Stage zmieniony |
| Grycan final_stage | `contact_search` | `email_reveal` | ZMIANA |
| Grycan paczki wygenerowane | 0 | **3** | +3 |
| Evra Fish final status | BLOCKED_COMPANY_NO_MATCH | BLOCKED_COMPANY_NO_MATCH | BEZ ZMIAN |
| Evra Fish alias bug | Aktywny | Aktywny | BEZ ZMIAN |
| Funkcja walidacji kontaktów | `validate_contact_threshold()` | `validate_contact_found()` | ZMIANA |
| Funkcja wyboru kontaktów | brak (filtr email) | `select_best_contacts()` | DODANA |
| Faza reveal w pipeline | BRAK | Phase 2 create_news_sequence | DODANA |
| Powiadomienie BLOCKED_NO_EMAIL | Z orchestrator | Z create_news_sequence | PRZENIESIONE |

**Kluczowy wniosek**: Dla ORLEN i Grycan pipeline przeszedł o 4 fazy dalej niż wcześniej. Zamiast zatrzymywać się na braku emaila przy wyszukiwaniu kontaktów, pipeline generuje teraz paczki wiadomości i symuluje próbę reveal. Status BLOCKED_NO_EMAIL jest teraz semantycznie poprawny — oznacza "reveal nie zwrócił emaila" nie "wyszukiwanie nie zwróciło emaila".

---

## 7. Issues Found

| # | Issue | Severity | Plik / moduł | Dokładne zachowanie | Rekomendacja |
|---|---|---|---|---|---|
| 1 | Evra Fish alias dict miss — sufiks prawny | **HIGH** | `company_aliases.yaml` + `entity_extractor` | LLM ekstrahuje "Evra Fish Sp. z o.o." zamiast "Evra Fish" → alias dict nie ma wariantu z sufiksem → NO_MATCH → BLOCKED_COMPANY_NO_MATCH | (a) Dodaj "Evra Fish Sp. z o.o." do `source_variants` w company_aliases.yaml; (b) dodaj do promptu entity_extractor instrukcję usuwania sufiksów prawnych gdy artykuł ich nie zawiera |
| 2 | ORLEN resolver dopasowuje do spółki córki | **MEDIUM** | `company_resolver.py` + `company_aliases.yaml` | Apollo org search zwraca ORLEN Technologie S.A. (conf 0.50) zamiast ORLEN S.A. / głównej jednostki grupy | Dodaj alias dla "ORLEN" w company_aliases.yaml z domain=orlen.pl i extra_queries wskazującymi na właściwe spółki |
| 3 | Wszystkie PL firmy zwracają 0 emaili z Apollo search | **MEDIUM** | Jakość danych Apollo | 10 kontaktów znalezionych dla ORLEN i Grycan, 0 emaili w wynikach wyszukiwania | Email reveal (`people/match`) jest krytyczny — konieczny live test z prawdziwymi kredytami reveal; bez reveal flow zawsze kończy się BLOCKED_NO_EMAIL |
| 4 | Brak profili procurement dla Grycan | **LOW** | Apollo data coverage | Apollo zwraca Managerów i Brand Managerów dla Grycan, brak Procurement / Category Manager / Zakupy | Oczekiwane dla mniejszych firm FMCG; możliwe rozszerzenie wyszukiwania o associated companies lub ręczne uzupełnienie |
| 5 | Associated company fallback ORLEN uruchomił Pollena Kurowski | **LOW** | `contact_finder.py` (assoc_fallback) | Assoc fallback znalazł 10 kontaktów dla Pollena Kurowski powiązanej z domyślnym kontekstem — mogą to być fałszywe pozytywne | Przegląd logiki assoc_fallback; wymaganie powiązania branżowego, nie tylko Apollo "related org" |

---

## 8. Final Verdict

### Nowy flow — ocena: **POPRAWNY, gotowy do live testu**

Nowy 4-fazowy flow Apollo Email Reveal działa zgodnie z projektem:

1. `validate_contact_found()` poprawnie akceptuje kontakty bez emaila
2. `select_best_contacts()` poprawnie wybiera top-3 by tier bez filtru emaila
3. Generowanie paczek wiadomości dla kontaktów bez emaila — potwierdzone
4. Dry-run `create_news_sequence()` poprawnie raportuje `reveal_would_be_attempted=True`
5. Status `BLOCKED_NO_EMAIL` ustawiany po fazie reveal (nie przed) — kluczowa poprawa semantyczna
6. `blocked_no_email_triggered_before_reveal=False` dla obu przypadków przechodzących — potwierdzone

### Co blokuje pipeline w realu

Żaden z 3 przypadków nie osiągnął `READY_FOR_REVIEW` — co jest oczekiwanym wynikiem dla dry_run przy braku emaili z Apollo search. Pipeline będzie gotowy do READY_FOR_REVIEW dopiero gdy:

1. Reveal (`people/match`) zwróci email dla co najmniej 1 kontaktu — wymaga live test z kredytami
2. LUB Apollo search zwróci kontakty z emailem (rzadkie dla PL firm)

### Priorytety dalszych działań

1. **HIGH** — Naprawić alias bug Evra Fish (`company_aliases.yaml` + prompt entity_extractor)
2. **HIGH** — Live test reveal: 1 artykuł z firmą, dla której Apollo posiada email → weryfikacja end-to-end
3. **MEDIUM** — Dodać alias ORLEN do company_aliases.yaml (główna jednostka, nie spółka córki)
4. **MEDIUM** — Skonfigurować `use_email_reveal: true` i `max_contacts_for_draft: 3` w `campaign_config.yaml`
5. **LOW** — Przegląd logiki assoc_fallback (Pollena Kurowski case)

---

*Raport wygenerowany po wykonaniu `tests/integration_test_three_articles_apollo_reveal.py` w trybie dry_run=True, 2026-04-22.*
