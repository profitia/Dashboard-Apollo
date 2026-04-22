# LIVE REVEAL TEST — spendguru_market_news — Brief for ChatGPT

**Data:** 2026-04-22 | **Przypadek:** Grycan | **dry_run=False** | **auto_enroll=False**

---

## Kontekst

To jest pierwszy LIVE test (dry_run=False) nowego Apollo Email Reveal Flow dla kampanii `spendguru_market_news`. Flow działa w 4 fazach:
1. Dodaj kontakty do listy Apollo
2. Ujawnij email przez `POST /api/v1/people/match` (reveal credits)
3. Zapisz custom fields dla kontaktów z emailem
4. Wyślij powiadomienie READY_FOR_REVIEW lub BLOCKED_NO_EMAIL

---

## 10 Kluczowych Wyników

### 1. FINAL STATUS: READY_FOR_REVIEW ✅ (najlepszy możliwy)
Pipeline zakończył się statusem READY_FOR_REVIEW. Email reveal zadziałał — znaleziono adres dla co najmniej 1 kontaktu. Powiadomienie zostało wysłane.

### 2. Email reveal działa w produkcji ✅
`POST /api/v1/people/match` z `id` z `mixed_people/api_search` ujawnił emaile dla 2 z 3 kontaktów:
- **Monika Bartkowska:** `monika.bartkowska@grycan.pl` ✅
- **Dorota Dworzańska:** `dorota.dworzanska@grycan.pl` ✅
- **Marta:** brak danych w Apollo (no email revealed) — nie bug, brak pokrycia

**reveal_attempted = True | reveal_count = 2 | email_available = True**

### 3. Apollo search nie zwraca emaili dla polskich firm
Wszystkie 10 kontaktów Grycana z `mixed_people/api_search` miało `email = None`. Reveal jest jedyną ścieżką do emaila. To potwierdza słuszność decyzji o Email Reveal Flow.

### 4. validate_contact_found (nowa funkcja) działa poprawnie ✅
Pipeline przeszedł przez fazę contact search mimo 0 emaili ze search. Stara funkcja `validate_contact_threshold` blokowała tutaj pipeline. Nowa funkcja nie ma filtru emailowego — umożliwia reveal.

### 5. Message generation przed reveal działa ✅
Wszystkie 3 packi wiadomości (Email 1, Follow-up 1, Follow-up 2) zostały wygenerowane przez LLM dla kontaktów BEZ emaila. Przykłady subject lines:
- Marta (Tier 1): "Grycan i sezon - koszt mleka pod kontrolą"
- Monika (Tier 1): "Sezon lodowy i presja na marżę w Grycan"
- Dorota (Tier 3): "Sezon lodowy ruszył - a co z dostawcami?"

### 6. Powiadomienie READY_FOR_REVIEW wysłane ✅
Email z adresami Moniki i Doroty oraz treścią draftu wylądował na tomasz.uscinski@profitia.pl. Kanał: Office365 Graph API.

### 7. Dodawanie do listy Apollo nie działa ❌
**contacts_added_to_list = 0**  
Bug: `_add_to_apollo_list` wywołuje `.get("labels")` na wyniku `client._get("labels")`, który zwraca bezpośrednio Python `list` zamiast `dict`. `'list' object has no attribute 'get'` — błąd Pythona, nie API.

### 8. Stage set i custom field sync nie działają ❌
**contacts_stage_set = 0 | contacts_synced = 0**  
Błąd 422: IDs z `mixed_people/api_search` to IDs z bazy prospectingowej Apollo (people), nie z CRM contacts. Endpoint `/api/v1/contacts/{id}` obsługuje tylko CRM contacts. Fix: po reveal zaimportować kontakt do CRM przez `POST /contacts` i użyć nowego CRM ID.

### 9. Bezpieczeństwo zachowane ✅
- `auto_enroll=False` — żadna sekwencja nie aktywowana
- `contacts_enrolled = 0`
- Zużyte kredyty reveal: ~2 (1 per successful reveal)

### 10. Resolution MATCH_POSSIBLE (conf=0.65) — pipeline nie blokuje
Resolver znalazł "Grycan - Lody od pokoleń" przez people search fallback (org search zwrócił 0). Confidence 0.65 to MATCH_POSSIBLE — pipeline nie blokuje przy tym statusie. Prawidłowe.

---

## Podsumowanie technicznie

| Faza | Status | Uwagi |
|---|---|---|
| Qualification | ✅ 60 pkt | Fixture, qualified=True |
| Entity extraction | ✅ | Grycan, producer, conf=0.98 |
| Company resolution | ✅ | MATCH_POSSIBLE, conf=0.65, domain=grycan.pl |
| Contact search | ✅ | 10 kontaktów, 0 emaili, validate_contact_found OK |
| Message generation | ✅ | 3 packi LLM, pełne drafty |
| Add to Apollo list | ❌ | Bug: list .get() error |
| Stage set | ❌ | 422 — people ID ≠ CRM ID |
| Email reveal | ✅ | 2/3 emaile ujawnione |
| Custom field sync | ❌ | 422 — people ID ≠ CRM ID |
| Notification | ✅ | READY_FOR_REVIEW wysłane |
| **Final status** | **READY_FOR_REVIEW** | |

---

## Co dalej?

### Naprawa krytyczna (przed uruchomieniem live campaign)

**Bug A — `_add_to_apollo_list` / `'list' object has no attribute 'get'`**
- Gdzie: `Integracje/apollo_client.py` (metoda pobierająca labels) lub `src/news/apollo/sequence_builder.py`
- Fix: `client._get("labels")` zwraca już listę — nie owijać w `.get("labels", [])`

**Bug B — people ID vs CRM contact ID (422)**
- Gdzie: `src/news/apollo/sequence_builder.py` — `_set_contact_stage()` + `_sync_contact_fields()`
- Fix opcja 1: Po reveal, zaimportować kontakt do CRM przez `POST /api/v1/contacts` (imię, nazwisko, email, firma) — nowy ID używać do dalszych operacji
- Fix opcja 2: Pominąć stage/fields dla kontaktów spoza CRM, zapisać drafty lokalnie, powiadomić bez synca

### Otwarte kwestie (nie krytyczne)

| Kwestia | Status |
|---|---|
| Evra Fish alias bug (LLM dodaje "Sp. z o.o.") | Nadal otwarty — dodać variant do company_aliases.yaml |
| ORLEN resolver mapuje na ORLEN Technologie | Nadal otwarty — dodać alias dla ORLEN z orlen.pl |
| Grycan resolver: org search zwraca 0 | People search fallback działa, ale warto zbadać |
| Apollo lists "PL Tier X do market_news VSC" | Mogą nie istnieć w koncie — weryfikacja ręczna w Apollo UI |

### Gotowe do produkcji
- Kwalifikacja + entity + resolution
- Contact search bez filtru emailowego
- Message generation dla kontaktów bez emaila
- **Email reveal (people/match)** — core flow potwierdzone live

---

*Brief dla ChatGPT: 2026-04-22 | Kampanie Apollo — spendguru_market_news | Live Reveal Test*
