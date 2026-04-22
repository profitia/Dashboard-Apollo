# LIVE REVEAL TEST REPORT — spendguru_market_news

**Data testu:** 2026-04-22  
**Przypadek:** Grycan (Grycan - Lody od pokoleń, grycan.pl)  
**Test ID:** live_reveal_grycan  
**Plik wyników:** `data/test/live_reveal_test_results.json`  
**Czas trwania:** 20:27:39 – 20:28:55 UTC (ok. 76 sekund)

---

## 1. Executive Summary

Pierwszy LIVE test (dry_run=False) przepływu Apollo Email Reveal zakończył się wynikiem **READY_FOR_REVIEW** — najlepszym możliwym. Email reveal zadziałał w produkcji: Apollo `people/match` ujawnił adresy e-mail dla **2 z 3 kontaktów** (Monika Bartkowska i Dorota Dworzańska z grycan.pl). Powiadomienie READY_FOR_REVIEW zostało wysłane na tomasz.uscinski@profitia.pl.

Odkryto **3 błędy infrastrukturalne** niezwiązane z samym reveal:
1. Dodawanie do listy Apollo nie działa (błąd `'list' object has no attribute 'get'` w `_add_to_apollo_list`)
2. Ustawianie stage kontaktu zwraca 422 (IDs z `mixed_people/api_search` to IDs z bazy people, nie CRM contacts)
3. Sync custom fields zwraca 422 (ten sam powód co wyżej)

Rdzeń flow - reveal → powiadomienie - **działa poprawnie**.

---

## 2. Test Setup

| Parametr | Wartość |
|---|---|
| `dry_run` | `False` (LIVE) |
| `auto_enroll` | `False` (enforced) |
| `use_email_reveal` | `True` (forced in test) |
| `send_approval_email` | `True` |
| `approval_email_to` | `tomasz.uscinski@profitia.pl` |
| `send_blocked_email_notification` | `True` |
| `contact_stage_draft` | `News pipeline - drafted` |
| Apollo list Tier 1 | `PL Tier 1 do market_news VSC` |
| Apollo list Tier 2 | `PL Tier 2 do market_news VSC` |
| Apollo list Tier 3 | `PL Tier 3 do market_news VSC` |
| Artykuł | Fixture (portalspozywczy.pl blokuje scrapera) |
| Script | `tests/integration_test_live_reveal.py` |

### Precondition: weryfikacja list Apollo

```
[PRECOND] Could not fetch Apollo labels: 'list' object has no attribute 'get'
[PRECOND] Apollo list 'PL Tier 1 do market_news VSC': MISSING
[PRECOND] Apollo list 'PL Tier 2 do market_news VSC': MISSING
[PRECOND] Apollo list 'PL Tier 3 do market_news VSC': MISSING
```

`client._get("labels")` zwraca bezpośrednio listę, a kod próbuje wywołać `.get("labels")` na tym wyniku - błąd Pythona, nie API. Listy mogą faktycznie istnieć w Apollo; precondition check był wadliwy (ten sam bug co w `_add_to_apollo_list`).

---

## 3. Qualification

| Pole | Wartość |
|---|---|
| Źródło danych | Fixture (artykuł 2026-04-15) |
| Tytuł | Przyspieszony start sezonu lodowego. Grycan: początek sezonu przynosi pozytywne sygnały |
| Total score | 60.0 |
| Industry score | 35.0 |
| Purchase signal score | 25.0 |
| Qualified | **True** |
| Disqualification reason | None |

**Scoring details:**
- `[Industry/food_production]`: producent lody, produkcja
- `[Industry/food_beverages]`: żywność
- `[Signal/supply_chain]`: surowce mleczne, dostawcy
- `[Signal/investment_capacity]`: zakupy surowców

---

## 4. Entity + Resolution

### Entity Extraction

| Pole | Wartość |
|---|---|
| Metoda | LLM |
| Wyekstrahowana nazwa | Grycan |
| Source name | Grycan |
| Canonical name | Grycan |
| Company type | producer |
| Campaign eligible | **True** |
| Confidence | 0.98 |

Uzasadnienie LLM: "Grycan jest producentem lodów i firmą FMCG, która intensywnie kupuje surowce mleczne oraz zarządza łańcuchem dostaw. Wzrost popytu i planowana ekspansja zwiększają potrzebę optymalizacji zakupów i negocjacji z dostawcami."

### Company Resolution

| Pole | Wartość |
|---|---|
| Status | `MATCH_POSSIBLE` |
| Confidence | 0.65 |
| Resolved name | **Grycan - Lody od pokoleń** |
| Resolved domain | **grycan.pl** |
| Liczba kandydatów | 1 |
| Candidate score (Apollo) | 0.45 |

Ścieżka resolvera:
1. Alias match: `Grycan` → canonical=`Grycan`, domain=`grycan.pl`
2. Apollo org search: `Grycan` → 0 wyników, `Grycan lody` → 0, `Grycan ice cream` → 0
3. Fallback people search: `Grycan` → 1 unikalny org → `Grycan - Lody od pokoleń`
4. LLM scorer: conf=0.65, status=MATCH_POSSIBLE → pipeline nie blokuje

**Uwaga:** conf=0.65 oznacza MATCH_POSSIBLE, nie MATCH_CONFIRMED. Resolver przetworzył poprawnie, ale org search nie zwraca wyników dla tej firmy — only people search fallback działał.

---

## 5. Contact Flow

### Apollo Search

| Metryka | Wartość |
|---|---|
| Search method | name_search + domain_fallback |
| Resolved name used | Grycan - Lody od pokoleń |
| Resolved domain used | grycan.pl |
| Contacts found (name_search) | 10 |
| Contacts found (domain_fallback) | 10 |
| With email from search | **0** |
| Without email from search | **10** |
| Winning strategy | none (email_contacts=0) |
| Validation function | `validate_contact_found` (NEW — no email filter) |
| Validate OK | **True** (10 contacts found) |

### Selected Contacts (top 3 by tier)

| # | Imię | Stanowisko | Tier | Apollo ID | E-mail ze search |
|---|---|---|---|---|---|
| 1 | Marta | Manager | tier_1_c_level | `66a86b99b597f900014170fa` | brak |
| 2 | Monika | Manager | tier_1_c_level | `636e672cd87c6e0001c842f4` | brak |
| 3 | Dorota | Senior Brand Manager | tier_3_buyers_operational | `6093a4f841f145000168d48d` | brak |

Apollo `mixed_people/api_search` nie zwraca emaili dla polskich firm — wszystkie 10 kontaktów bez emaila. Dzięki nowej funkcji `validate_contact_found` (brak filtru emailowego) pipeline przeszedł do fazy message generation i email reveal.

---

## 6. Email Reveal

### Wynik reveal

| Kontakt | Apollo ID | Wynik reveal | E-mail ujawniony |
|---|---|---|---|
| Marta | `66a86b99b597f900014170fa` | BRAK | — |
| Monika | `636e672cd87c6e0001c842f4` | **SUKCES** | `monika.bartkowska@grycan.pl` |
| Dorota | `6093a4f841f145000168d48d` | **SUKCES** | `dorota.dworzanska@grycan.pl` |

| Metryka | Wartość |
|---|---|
| `reveal_attempted` | **True** |
| `reveal_count` | **2** (z 3 prób) |
| `email_available` | **True** |
| API endpoint | `POST /api/v1/people/match` |
| Pole użyte | `id` (apollo_contact_id z search) |
| Kredyty reveal zużyte | ~2 (1 per successful reveal) |

**To jest kluczowy wynik testu.** `client.reveal_email()` działa w produkcji. Apollo `people/match` z parametrem `id` z `mixed_people/api_search` ujawnia emaile dla polskich firm.

---

## 7. Apollo Write Result

### Phase 1 — Dodawanie do listy Apollo

| Metryka | Wartość |
|---|---|
| `contacts_added_to_list` | **0** |
| Błąd | `'list' object has no attribute 'get'` |
| Źródło błędu | `_add_to_apollo_list` (lub pomocniczy `_get_list_id`) |

**Root cause:** `client._get("labels")` zwraca bezpośrednio listę obiektów (Python `list`), a kod po stronie `_add_to_apollo_list` wywołuje `.get(...)` na tym rezultacie traktując go jak dict. Błąd Pythona, nie błąd API. Listy Apollo mogą istnieć — weryfikacja precondition jest też dotknięta tym samym bugiem.

**Działanie:** błąd jest łapany jako wyjątek, pipeline kontynuuje.

### Phase 1 — Ustawianie stage kontaktu

| Metryka | Wartość |
|---|---|
| `contacts_stage_set` | **0** |
| Błąd | `422 Client Error: Unprocessable Entity` |
| Endpoint | `PUT /api/v1/contacts/{apollo_contact_id}` |

**Root cause:** IDs zwrócone przez `mixed_people/api_search` to IDs z bazy prospectingowej Apollo (`people`). Endpoint `/contacts/{id}` obsługuje wyłącznie kontakty z CRM (`contacts`). Te same IDs mogą nie istnieć w CRM lub mieć inne ID po imporcie. Próba aktualizacji osoby z bazy people przez endpoint contacts zwraca 422.

**Działanie:** błąd jest łapany, pipeline kontynuuje.

### Phase 2 — Email reveal

Patrz sekcja 6. Reveal się udał.

### Phase 3 — Custom field sync

| Metryka | Wartość |
|---|---|
| `contacts_synced` | **0** |
| Błąd Moniki | `422 Client Error: Unprocessable Entity` (`/contacts/636e672cd87c6e0001c842f4`) |
| Błąd Doroty | `422 Client Error: Unprocessable Entity` (`/contacts/6093a4f841f145000168d48d`) |

**Root cause:** Identyczny jak przy stage set — IDs z people search nie są CRM contact IDs. Custom fields mogą być ustawiane tylko na obiektach typu Contact w CRM.

**Działanie:** błąd jest łapany, pipeline przechodzi do fazy powiadomienia.

### Phase 4 — Notification

Patrz sekcja 8.

---

## 8. Notification

| Metryka | Wartość |
|---|---|
| Typ powiadomienia | **READY_FOR_REVIEW** |
| Wysłano do | `tomasz.uscinski@profitia.pl` |
| Status | ✓ Wysłano |
| Kanał | Office365 Graph API |

Powiadomienie READY_FOR_REVIEW zostało wysłane prawidłowo. Email zawiera:
- Nazwę firmy: Grycan
- Sequence name: `NEWS-2026-04-15-grycan-przyspieszony-start-sezonu-lodowego-gryc`
- Kontakty z ujawnionymi emailami: Monika (monika.bartkowska@grycan.pl), Dorota (dorota.dworzanska@grycan.pl)
- Treść wiadomości (drafty) dla każdego kontaktu do ręcznej weryfikacji

---

## 9. Final Pipeline Status

| Pole | Wartość |
|---|---|
| `final_status` | **READY_FOR_REVIEW** |
| `final_stage` | `email_reveal` |
| `final_reason` | Email revealed for 2 contact(s) — content synced to Apollo |
| `contacts_processed` | 3 |
| `contacts_added_to_list` | 0 |
| `contacts_stage_set` | 0 |
| `contacts_synced` | 0 |
| `contacts_enrolled` | 0 |
| `reveal_attempted` | True |
| `reveal_count` | 2 |
| `email_available` | True |
| Test czas start | 2026-04-22T18:27:39 UTC |
| Test czas koniec | 2026-04-22T18:28:55 UTC |

### Podsumowanie błędów

| Błąd | Typ | Moduł | Priorytet naprawy |
|---|---|---|---|
| `_add_to_apollo_list` — `'list' object has no attribute 'get'` | Bug Python (typ odpowiedzi API) | `apollo_client._get("labels")` lub `_get_list_id()` | WYSOKI — listy nie działają |
| Stage set 422 | API — people ID ≠ CRM contact ID | `sequence_builder._set_contact_stage()` | WYSOKI — stage nie jest ustawiany |
| Custom field sync 422 | API — people ID ≠ CRM contact ID | `sequence_builder._sync_contact_fields()` | WYSOKI — custom fields nie są pisane |
| Reveal brak dla Marty | Brak danych w Apollo | `apollo_client.reveal_email()` | LOW — expected, nie bug |

---

## 10. Verdict

### Co działa ✅

- **Email reveal działa w produkcji.** `POST /api/v1/people/match` z `id` z `mixed_people/api_search` ujawnia emaile. 2/3 kontaktów Grycana ma email w Apollo.
- **Powiadomienie READY_FOR_REVIEW wysłane prawidłowo.** Tomasz dostał email z adresami i treścią draftu.
- **Kwalifikacja, entity extraction i resolution** działają bez błędów.
- **Message generation** dla kontaktów bez emaila — wszystkie 3 packi wygenerowane przez LLM przed reveal.
- **`validate_contact_found`** (nowa funkcja bez filtru emailowego) działa — pipeline nie blokuje się przed reveal.
- **Bezpieczeństwo zachowane.** `auto_enroll=False`, żadna sekwencja nie została aktywowana.

### Co wymaga naprawy ❌

#### Bug 1 — `_add_to_apollo_list`: `'list' object has no attribute 'get'`

**Lokalizacja:** `Integracje/apollo_client.py` — metoda pomocnicza wyszukująca listę po nazwie (prawdopodobnie `_get_list_id` lub podobna) lub `sequence_builder._add_to_apollo_list`.

**Problem:** `client._get("labels")` zwraca `list`, a kod traktuje ją jak `dict` i wywołuje `.get("labels", [])`.

**Fix:** Sprawdzić typ odpowiedzi — jeśli wynik `_get("labels")` to już lista, użyć bezpośrednio; jeśli dict, wyciągnąć klucz.

#### Bug 2 — Stage set i custom fields: 422 na IDs z people search

**Lokalizacja:** `src/news/apollo/sequence_builder.py` — `_set_contact_stage()` i `_sync_contact_fields()`.

**Problem:** IDs zwracane przez `mixed_people/api_search` są to IDs z bazy people (prospecting), nie z CRM. Endpoint `/contacts/{id}` obsługuje tylko CRM contacts. Próba zapisu na people ID zwraca 422.

**Fix (opcja A — preferowana):** Przed zapisem custom fields/stage, zaimportować kontakt do CRM przez `POST /api/v1/contacts` z danymi z reveal (email, imię, nazwisko, firma). Nowy ID z CRM użyć do dalszych operacji.

**Fix (opcja B — szybka):** Pominąć stage set i custom field sync dla kontaktów, których ID pochodzi z people search (dopóki nie są w CRM). Zapisać drafty tylko lokalnie, wysłać powiadomienie z pełną treścią.

### Następne kroki

1. **[KRYTYCZNE]** Naprawić `_add_to_apollo_list` — bug z typem odpowiedzi `_get("labels")`
2. **[KRYTYCZNE]** Rozwiązać kwestię people ID vs CRM contact ID — zaimplementować tworzenie CRM contact po reveal lub pominąć sync dla people IDs
3. **[OPCJONALNE]** Rozważyć `POST /contacts` po reveal, żeby zapisać kontakt do CRM z ujawnionym emailem
4. **[GOTOWE DO PRODUKCJI]** Reveal + notification flow nie wymaga zmian — działa

---

*Raport wygenerowany: 2026-04-22 | Autor: GitHub Copilot | Workspace: Kampanie Apollo*
