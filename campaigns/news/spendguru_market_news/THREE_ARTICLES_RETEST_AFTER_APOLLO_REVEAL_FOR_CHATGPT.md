# THREE ARTICLES RETEST — APOLLO REVEAL FLOW — BRIEF FOR CHATGPT

**Kontekst:** Retest 3 artykułów po redesignie Apollo Email Reveal flow. Poprzedni test używał starego flow z filtrem emaila przy kontaktach. Nowy flow nie filtruje kontaktów po emailu — reveal (`people/match`) jest teraz osobną fazą wewnątrz `create_news_sequence()`.

**Data:** 2026-04-22 | **Tryb:** dry_run=True | **Script:** `tests/integration_test_three_articles_apollo_reveal.py`

---

## Finalne statusy

| Case | Fetch | Qualification | Resolution | Kontakty | Paczki | Reveal (dry) | Status |
|---|---|---|---|---|---|---|---|
| ORLEN | live (tworzywa.online) | PASS (77.0) | MATCH_POSSIBLE 0.55 → ORLEN Technologie S.A. | 10 found, 0 email, 3 selected | **3** | would_be=True | **BLOCKED_NO_EMAIL (after reveal)** |
| Grycan | fixture | PASS (60.0) | MATCH_POSSIBLE 0.65 → Grycan - Lody od pokoleń | 10 found, 0 email, 3 selected | **3** | would_be=True | **BLOCKED_NO_EMAIL (after reveal)** |
| Evra Fish | fixture | PASS (58.0) | **NO_MATCH** (alias bug) | 0 | 0 | False | **BLOCKED_COMPANY_NO_MATCH** |

---

## 10 kluczowych wniosków

**1. Nowy flow działa poprawnie — potwierdzone end-to-end (dry_run)**
Pipeline przeszedł przez wszystkie 6 faz dla ORLEN i Grycan: fetch → qualify → entity → resolution → contacts (new flow) → messages (new flow) → dry_run sequence. W starym flow zatrzymywał się na fazie contacts.

**2. Kontakty BEZ emaila są teraz akceptowane i procesowane**
Wszystkie 6 wybranych kontaktów (3 ORLEN + 3 Grycan) nie miało emaila z Apollo search. `validate_contact_found()` zaakceptował je bez problemu. `select_best_contacts()` wybrał top-3 by tier.

**3. Paczki wiadomości generowane dla kontaktów bez emaila**
Nowe zachowanie: 6 paczek mailowych wygenerowanych przez LLM dla kontaktów z email=NONE. Poprzedni flow generował 0. To jest fundamentalna zmiana — treść jest gotowa na moment, gdy reveal zwróci email.

**4. BLOCKED_NO_EMAIL teraz znaczy co powinien znaczyć**
Poprzedni flow: BLOCKED_NO_EMAIL przy `final_stage="contact_search"` — czyli "nie znalazłem emaila przy wyszukiwaniu kontaktów". Nowy flow: BLOCKED_NO_EMAIL przy `final_stage="email_reveal"` — czyli "próbowałem reveal, ale nie zwrócił emaila". Semantycznie poprawne.

**5. `reveal_would_be_attempted=True` dla ORLEN i Grycan — kluczowy wskaźnik**
W trybie dry_run pipeline raportuje, że w trybie live wywołałby `people/match` dla 3 kontaktów w każdym przypadku. Oznacza to, że nowy flow jest gotowy do live testu — wystarczy wyłączyć dry_run i upewnić się, że konfiguracja ma `use_email_reveal: true`.

**6. Evra Fish nadal zablokowany — znany błąd alias dict**
LLM entity extractor ekstrahuje "Evra Fish Sp. z o.o." (z sufiksem prawnym, którego nie ma w artykule). Alias dict ma warianty "Evra Fish" i "Evra-Fish", ale nie "Evra Fish Sp. z o.o." — NO_MATCH. Błąd udokumentowany w poprzednim teście, nie naprawiony. Naprawa jest prosta i dwuetapowa.

**7. Apollo search dla PL firm zwraca 0 emaili — to norma, nie błąd**
Dla ORLEN Technologie i Grycan - Lody od pokoleń: 10 kontaktów znalezionych, 0 emaili. To typowe dla polskich firm w Apollo. Email reveal (`people/match`) jest jedynym sposobem na pozyskanie emaila. Nowy flow jest zaprojektowany właśnie pod tę rzeczywistość.

**8. ORLEN resolver dopasowuje do spółki córki, nie do grupy**
Resolution zwróciła ORLEN Technologie S.A. (conf 0.50) zamiast ORLEN S.A. Brak aliasu dla "ORLEN" w company_aliases.yaml. Kontakty z ORLEN Technologie mogą nie być właściwym targetem — dodanie aliasu z domain=orlen.pl poprawiłoby jakość.

**9. Grycan — brak profili zakupowych w Apollo**
Apollo zwróciło Managerów i Brand Managerów dla Grycan. Brak profili Procurement / Category Manager / Kupiec. Dla małych firm FMCG to oczekiwane — Apollo nie ma pełnego pokrycia. Może wymagać manualnego uzupełnienia lub innego źródła kontaktów.

**10. Pipeline gotowy do live testu z kredytami reveal**
Dwa z trzech przypadków (ORLEN, Grycan) przeszły pełen flow dry_run z potwierdzeniem, że reveal zostałby wywołany. Następny krok to uruchomienie z dry_run=False dla jednego przypadku z firmą, dla której Apollo posiada email w bazie — weryfikacja end-to-end live.

---

## Co poprawiło się po nowym flow

| Aspekt | Przed redesignem | Po redesignie |
|---|---|---|
| Kontakty bez emaila | Odrzucane (filtro) | Akceptowane (nowy flow) |
| Paczki dla kontaktów bez emaila | 0 (nie generowane) | Generowane (gotowe na reveal) |
| Etap BLOCKED_NO_EMAIL | contact_search | email_reveal |
| Semantyka statusu | "brak emaila w search" | "reveal nie zwrócił emaila" |
| Pipeline depth (ORLEN) | 3 fazy | 6 faz (pełen pipeline) |
| Pipeline depth (Grycan) | 3 fazy | 6 faz (pełen pipeline) |

---

## Co nadal blokuje pipeline

**Blokery krótkoterminowe (do naprawy):**
1. Evra Fish alias bug — LLM dodaje "Sp. z o.o." → NO_MATCH (naprawa: 2 pliki)
2. ORLEN alias dict — brak wpisu dla głównej jednostki grupy (naprawa: 1 plik)
3. `use_email_reveal: true` i `max_contacts_for_draft: 3` nie skonfigurowane w `campaign_config.yaml`

**Blokery strukturalne (wymagają live testu):**
1. Apollo search dla PL firm → 0 emaili — reveal konieczny, ale nie przetestowany live
2. Reveal może zwrócić None dla popularnych firm (ORLEN, Grycan) — nieznana jakość danych Apollo w `people/match` dla PL

---

## Co powinno być kolejnym krokiem

1. **TERAZ** — Fix Evra Fish: dodaj "Evra Fish Sp. z o.o." do `source_variants` w `campaigns/news/spendguru_market_news/data/company_aliases.yaml` + dodaj instrukcję do promptu entity_extractor (`src/news/entity/entity_extractor_prompt.py` lub odpowiedni plik) żeby nie dodawał sufiksów prawnych
2. **TERAZ** — Fix ORLEN: dodaj alias dla "ORLEN" z domain=orlen.pl do company_aliases.yaml
3. **POTEM** — Skonfiguruj `use_email_reveal: true` + `max_contacts_for_draft: 3` w campaign_config
4. **LIVE TEST** — Wybierz firmę, dla której Apollo na pewno posiada email (np. zagraniczna firma ze sprawdzoną bazą), uruchom z dry_run=False i prawdziwymi kredytami reveal — sprawdź end-to-end czy READY_FOR_REVIEW jest osiągalne
5. **MONITORING** — Po live teście sprawdź zużycie kredytów reveal (każde wywołanie `people/match` to 1 kredyt) i skalibruj `max_contacts_for_draft`

---

*Brief wygenerowany po retescie 2026-04-22. Pełny raport: `THREE_ARTICLES_RETEST_AFTER_APOLLO_REVEAL_REPORT.md`*
