# APOLLO EMAIL REVEAL FLOW REPORT — spendguru_market_news

**Data implementacji:** 2026-04-22  
**Kampania:** spendguru_market_news  
**Zakres:** przebudowa flow kontaktów i email reveal w pipeline news-triggered  
**Testy po wdrożeniu:** 29/29 smoke tests PASS

---

## 1. Executive Summary

### Co zostało zmienione

Przebudowano logikę kontaktów i emaili w pipeline news-triggered. Poprzedni flow kończył się statusem `BLOCKED_NO_EMAIL` już na etapie wstępnego wyszukiwania kontaktów — jeśli Apollo nie zwracał emaila w wynikach `mixed_people/api_search`, pipeline zatrzymywał się natychmiast. To było błędne — Apollo często nie zwraca emaila w wynikach wyszukiwania prospektów (tylko podstawowe dane), a email jest ujawniany dopiero przez dedykowany krok `people/match` (reveal credit).

Nowy flow rozdziela wyraźnie cztery etapy:
1. **Wyszukanie kontaktów** — bez wymagania emaila
2. **Dodanie do listy Apollo** — dla najlepszych kontaktów po tierze, przed revelaem
3. **Email reveal** — próba ujawnienia emaila przez `people/match`
4. **Decyzja końcowa** — `READY_FOR_REVIEW` lub `BLOCKED_NO_EMAIL` dopiero po reveal

### Dlaczego

`BLOCKED_NO_EMAIL` powinno oznaczać: *brak emaila po właściwym kroku Apollo*, a nie *brak emaila w wynikach prospecting search*. W praktyce Apollo może ujawnić email w reveal nawet gdy wyszukiwanie go nie zwraca.

### Nowy flow (skrót)

```
article qualified
  → company extracted
    → company resolved
      → contacts found (any, no email filter)
        → select best contacts by tier
          → generate outreach packs (for all selected)
            → add to Apollo list (Tier 1/2/3) [NEW]
              → attempt email reveal for contacts without email [NEW]
                → if email available: set custom fields → READY_FOR_REVIEW
                → if no email after reveal: BLOCKED_NO_EMAIL notification
```

---

## 2. Previous vs New Flow

### Poprzedni flow (przed zmianą)

```
contacts = find_contacts_with_fallbacks()         # search Apollo

ok = validate_contact_threshold(contacts)          # ← SPRAWDZA EMAIL

if not ok:
    if contacts_no_email:                          # ← BEZ EMAILA = koniec
        generate packs for notification
        send BLOCKED_NO_EMAIL notification         # ← status nadany zbyt wcześnie
        mark BLOCKED_NO_EMAIL
    else:
        mark BLOCKED_NO_CONTACT
    continue

# Dociera tu tylko jeśli contacts mają email
contacts_with_email = [c for c in contacts if c.email]
contacts_with_packs = [(c, pack) for c in contacts_with_email]

create_news_sequence()                             # add to list + custom fields
mark READY_FOR_REVIEW
```

**Problem:** `validate_contact_threshold()` z `require_email_for_sequence=True` odcinał kontakty bez emaila PRZED krokiem `add_to_list` i PRZED revelaem. Email reveal nigdy nie był wykonywany.

### Nowy flow (po zmianie)

```
contacts = find_contacts_with_fallbacks()          # search Apollo (bez email filter)

ok = validate_contact_found(contacts)              # ← SPRAWDZA TYLKO ISTNIENIE

if not ok:
    mark BLOCKED_NO_CONTACT                        # dopiero teraz brak kontaktu
    continue

best_contacts = select_best_contacts(contacts)     # top 3 wg tier (bez email filter)

contacts_with_packs = [(c, pack) for c in best]   # pack dla WSZYSTKICH (nie tylko z email)

# → create_news_sequence() — 4 fazy WEWNĄTRZ:

  # FAZA 1: Add to list + set stage (ALL contacts, regardless of email)
  for contact in contacts_with_packs:
      contact_id = find_or_create(contact)         # używa apollo_contact_id jeśli brak emaila
      add_to_apollo_list(contact_id, tier_list)    # ← NOWE: przed revelaem
      set_contact_stage(contact_id, stage)         # ← NOWE: przed revelaem

  # FAZA 2: Email reveal (tylko dla kontaktów bez emaila)
  for contact without email:
      email = client.reveal_email(apollo_id=...)   # ← NOWE: people/match z reveal credit
      if email: contact.email = email

  # FAZA 3: Custom fields (tylko dla kontaktów Z EMAILEM po reveal)
  for contact with email:
      client.update_contact_custom_fields(...)     # treści sekwencji

  # FAZA 4: Notyfikacja
  if any(contact.email):
      send READY_FOR_REVIEW notification
      email_available = True
  else:
      send BLOCKED_NO_EMAIL notification
      email_available = False

# Wróć do orchestrator
if email_available:
    mark READY_FOR_REVIEW
    register_sequence()
    notify()
else:
    mark BLOCKED_NO_EMAIL (final_stage="email_reveal")
```

---

## 3. New Apollo Contact/Email Flow

### Krok po kroku

| Krok | Etap | Moduł | Wymaganie emaila |
|------|------|-------|-----------------|
| 1 | `find_contacts_with_fallbacks()` | `contact_finder.py` | ❌ Nie |
| 2 | `validate_contact_found()` | `contact_finder.py` | ❌ Nie |
| 3 | `select_best_contacts()` | `contact_finder.py` | ❌ Nie |
| 4 | `generate_outreach_pack()` | `message_generator.py` | ❌ Nie |
| 5 | `_find_or_create_apollo_contact()` | `sequence_builder.py` | ❌ Używa `apollo_contact_id` |
| **6** | **`_add_to_apollo_list()`** | `sequence_builder.py` | ❌ **Nowe — bez emaila** |
| **7** | **`_set_contact_stage()`** | `sequence_builder.py` | ❌ **Nowe — bez emaila** |
| **8** | **`client.reveal_email()`** | `apollo_client.py` | ➡️ **Nowy krok reveal** |
| 9 | `update_contact_custom_fields()` | `sequence_builder.py` | ✅ Tylko z emailem |
| 10 | `_send_draft_approval_email()` | `sequence_builder.py` | Zależy od emaila |

### Gdzie następuje add_to_list

**`create_news_sequence()` — Faza 1**, przed próbą reveal. Kontakt jest dodawany do właściwej listy Apollo (PL Tier 1/2/3 do market_news VSC) na podstawie przypisanego tieru — niezależnie od tego, czy ma email.

Listy Apollo:
- `PL Tier 1 do market_news VSC` — tier_1_c_level
- `PL Tier 2 do market_news VSC` — tier_2_procurement_management
- `PL Tier 3 do market_news VSC` — tier_3_buyers_operational

### Gdzie następuje email reveal

**`create_news_sequence()` — Faza 2**, po dodaniu do listy i ustawieniu stage'u. Endpoint: `POST /api/v1/people/match` z parametrem `id` (apollo_contact_id). Zużywa kredyty reveal Apollo.

Implementacja w `apollo_client.reveal_email()`:
- Preferuje `apollo_id` — najdokładniejszy identyfikator
- Fallback: `first_name + last_name + domain / organization_name`
- Obsługuje błędy API gracefully (zwraca None)
- Toggle: `use_email_reveal: true/false` w campaign_config.yaml

### Kiedy zapada decyzja READY vs BLOCKED_NO_EMAIL

**`create_news_sequence()` — Faza 4**, po przetworzeniu wszystkich kontaktów. Decyzja:
- `email_available = any(contact.email for contact in contacts_with_packs after reveal)`
- Jeśli `True` → `READY_FOR_REVIEW` notification, wrócony `email_available=True`
- Jeśli `False` → `BLOCKED_NO_EMAIL` notification (z wygenerowanymi treściami), `email_available=False`

Orchestrator używa `seq_result["email_available"]` do nadania finalnego statusu w state manager.

---

## 4. Status Model Impact

### Zmiany w statusach

Nie dodano nowych statusów. Doprecyzowano istniejący `BLOCKED_NO_EMAIL`:

| Parametr | Poprzednia wartość | Nowa wartość |
|---------|-------------------|-------------|
| `description` | "Kontakty znalezione, brak adresu email — powiadomienie BLOCKED wysłane" | "Kontakty znalezione i dodane do listy Apollo — próba email reveal nieudana — powiadomienie BLOCKED wysłane" |
| `stage` | `"contact_search"` | `"email_reveal"` |

### Zmiana znaczenia statusów w state markingu

| Status | Poprzedni `final_stage` | Nowy `final_stage` |
|--------|------------------------|-------------------|
| `BLOCKED_NO_CONTACT` | `"contact_search"` | `"contact_search"` (bez zmian) |
| `BLOCKED_NO_EMAIL` | `"contact_search"` | `"email_reveal"` |
| `READY_FOR_REVIEW` | `"apollo_write"` | `"apollo_write"` (bez zmian) |

### Nowe pola w state marking dla BLOCKED_NO_EMAIL

```python
{
    "company": "...",
    "final_stage": "email_reveal",          # nowe (było: contact_search)
    "final_reason": "Contacts identified and added to Apollo list — email reveal attempted but no email address available",
    "reveal_attempted": True,               # nowe
    "reveal_count": 0,                      # nowe
}
```

### Nowe pola w state marking dla READY_FOR_REVIEW

```python
{
    "final_stage": "apollo_write",
    "final_reason": "Flow complete — contact added to list, email available, sequence ready for review",
    "reveal_attempted": ...,                # nowe
    "reveal_count": ...,                    # nowe
}
```

### Spójność z innymi modułami

- `state_manager.py` — nie zmieniony. Statusy są aliasami PipelineStatus — spójność zachowana.
- `notifier.py` — nie zmieniony. Notyfikacje logowane przez `notify()` tylko dla READY_FOR_REVIEW.
- `sequence_builder.py` — notyfikacje email (READY i BLOCKED) wysyłane wewnętrznie z `create_news_sequence()`.
- Reporting (`run_report.py`) — nie zmieniony. Korzysta ze statusów z PipelineStatus — spójność zachowana.

---

## 5. Files Changed

| Plik | Typ zmiany | Po co |
|------|-----------|-------|
| `Integracje/apollo_client.py` | ADD: `reveal_email()` | Nowy endpoint do ujawniania emaila przez `people/match` |
| `src/news/contacts/contact_finder.py` | ADD: `validate_contact_found()`, `select_best_contacts()` | Oddzielenie walidacji (kontakt istnieje) od walidacji (email dostępny) |
| `src/news/pipeline_status.py` | MODIFY: `BLOCKED_NO_EMAIL` metadata | Aktualizacja opisu i stage'u (email_reveal zamiast contact_search) |
| `src/news/apollo/sequence_builder.py` | REFACTOR: `create_news_sequence()` | 4-fazowy flow: add_to_list → reveal → custom_fields → notification |
| `src/news/orchestrator.py` | MODIFY: `run_build_sequence()` | Nowy flow: `validate_contact_found` + `select_best_contacts` + generate packs bez email filter + finalny status z `seq_result["email_available"]` |

### Szczegółowe zmiany w orchestrator.py

- Zmieniony import: `validate_contact_threshold` → `validate_contact_found, select_best_contacts`
- Usunięto: blok BLOCKED_NO_EMAIL przed `create_news_sequence()` (z osobnym `send_blocked_no_email_notification()`)
- Usunięto: filtrowanie `if not contact.email: continue` przy generowaniu packów
- Dodano: `select_best_contacts(contacts, max_contacts=3)` po `validate_contact_found()`
- Dodano: obsługę błędu `BLOCKED_MESSAGE_GENERATION_FAILED` gdy wszystkie packi failują
- Zmieniono: finalny status na podstawie `seq_result["email_available"]`
- Zmieniono: `state.register_sequence()` + `notify()` wywołane tylko gdy `email_available=True`

### Szczegółowe zmiany w sequence_builder.py

- Zmieniono: docstring `create_news_sequence()` — opisuje nowy 4-fazowy flow
- Dodano: `use_email_reveal`, `reveal_attempted`, `reveal_count`, `email_available` do result dict
- Dodano: `dry_run` teraz raportuje `email_available` i `reveal_attempted` (nawet bez API calls)
- Zmieniono: per-contact loop podzielony na Fazy 1–4
- Zmieniono: error message używa `contact.full_name` zamiast `contact.email` (email może być None)
- Zmieniono: custom fields ustawiane tylko dla kontaktów z emailem
- Zmieniono: notification READY lub BLOCKED decyduje `email_available`

---

## 6. Validation

### Smoke tests

**Wynik:** 29/29 PASS po wszystkich zmianach.

```
python -m pytest tests/test_news_pipeline_smoke.py -v
29 passed in 1.49s
```

### Logiczna weryfikacja flow

| Scenariusz | Poprzedni status | Nowy status | Poprawność |
|-----------|-----------------|-------------|-----------|
| 0 kontaktów w Apollo | BLOCKED_NO_CONTACT | BLOCKED_NO_CONTACT | ✅ Bez zmian |
| Kontakty z emailem (z search) | READY_FOR_REVIEW | READY_FOR_REVIEW | ✅ Bez zmian |
| Kontakty bez emaila, reveal = email | ❌ BLOCKED_NO_EMAIL (zbyt wcześnie) | ✅ READY_FOR_REVIEW | ✅ POPRAWIONE |
| Kontakty bez emaila, reveal = None | BLOCKED_NO_EMAIL | BLOCKED_NO_EMAIL | ✅ Poprawnie |
| Kontakty bez emaila, reveal wyłączony | BLOCKED_NO_EMAIL | BLOCKED_NO_EMAIL | ✅ Spójnie |

### Weryfikacja notyfikacji

- **READY_FOR_REVIEW:** email wysyłany wewnątrz `create_news_sequence()` Faza 4. Zawiera kontakty z emailami + treści sekwencji.
- **BLOCKED_NO_EMAIL:** email wysyłany wewnątrz `create_news_sequence()` Faza 4. Zawiera kontakty bez emaila + wygenerowane treści (do przeglądu i ew. manualnego uzupełnienia).
- Treści (packs) generowane dla **wszystkich** wybranych kontaktów (nie tylko z emailem) — dostępne w obu notyfikacjach.

### Weryfikacja `state_manager`

- `state.mark_article()` wywołany raz per case (z prawidłowym statusem).
- `state.register_sequence()` wywołany tylko gdy `email_available=True`.
- Model stanów pozostał spójny — żadne nowe statusy nie zostały dodane.

---

## 7. Risks / Limitations

### Email reveal zużywa kredyty Apollo

Każde wywołanie `client.reveal_email()` (endpoint `people/match`) zużywa kredyty reveal. Przy dużej liczbie artykułów może prowadzić do wyczerpania kredytów. Mitigation: toggle `use_email_reveal: false` w campaign_config.yaml wyłącza reveal.

### Reveal może nie znaleźć emaila

Apollo `people/match` może zwrócić profil bez emaila nawet dla prawdziwej osoby (email chroniony lub niedostępny w bazie). W takim przypadku status to `BLOCKED_NO_EMAIL` — poprawne zachowanie.

### `_find_or_create_apollo_contact()` wymaga emaila do tworzenia NOWEGO kontaktu

Kontakty zwrócone przez `mixed_people/api_search` mają `apollo_contact_id` — są już w Apollo i nie wymagają tworzenia. Problem pojawia się tylko jeśli kontakt NIE istnieje w Apollo i NIE ma emaila — wtedy `_find_or_create_apollo_contact()` zwraca `contact.apollo_contact_id` (który może być None). Ten przypadek jest obsługiwany: brak `contact_id` → kontakt pomijany z ostrzeżeniem w logach.

### use_email_reveal nie jest jeszcze w campaign_config.yaml

Toggle `use_email_reveal` jest sprawdzany w kodzie, ale nie jest domyślnie dodany do `campaign_config.yaml` kampanii spendguru_market_news. Domyślna wartość: `True`. Można dodać ręcznie jako `use_email_reveal: false` żeby wyłączyć reveal (np. w trybie testowym).

### max_contacts_for_draft nie jest w campaign_config.yaml

Nowy parametr `max_contacts_for_draft` (domyślnie: 3) steruje ile najlepszych kontaktów jest wybieranych przez `select_best_contacts()`. Analogicznie — można dodać do config, domyślnie działa.

### BLOCKED_NO_EMAIL nie rejestruje sekwencji (register_sequence nie wywoływany)

To celowe zachowanie — firma w cooldown jest sprawdzana na początku pipeline'u. BLOCKED_NO_EMAIL nie rejestruje sekwencji, więc ta sama firma może być przetworzona ponownie przy następnym artykule.

---

## 8. Final Recommendation

### Czy nowy flow jest lepiej dopasowany do Apollo?

**Tak.** Nowy flow odwzorowuje rzeczywistą dwuetapową logikę Apollo:
1. Prospecting search (`mixed_people/api_search`) — bez emaila, do identyfikacji osób
2. Reveal (`people/match`) — ujawnienie emaila z credential credit

Poprzedni flow pomijał krok 2 i traktował brak emaila w kroku 1 jako koniec.

### Czy jest gotowy do dalszych testów live?

**Tak, z zastrzeżeniami:**
1. **Reveal będzie zużywać kredyty** — pierwsze testy live powinny być małe (1–2 case'y)
2. **Kontakty bez emaila są teraz dodawane do list Apollo** — to jest oczekiwane, ale warto zweryfikować, że listy (PL Tier 1/2/3 do market_news VSC) istnieją w Apollo przed pierwszym live run
3. **Stage "News pipeline - drafted"** — warto zweryfikować, że stage o tej nazwie istnieje w Apollo (lub jest tworzony automatycznie)

### Dodatkowe rekomendacje

- Dodać `use_email_reveal: true` (lub `false`) jawnie do `campaign_config.yaml`
- Dodać `max_contacts_for_draft: 3` do `campaign_config.yaml`
- Uruchomić `integration_test_three_articles.py` ponownie po tej zmianie — zobaczymy że flow teraz:
  - Próbuje reveal dla ORLEN, Grycan, Evra Fish
  - Jeśli kredyty = 0 lub brak emaila → BLOCKED_NO_EMAIL (ale kontakty są w listach)
  - Jeśli reveal zwróci email → READY_FOR_REVIEW
- Rozważyć dodanie do state markingu informacji, które listy Apollo były użyte (audit trail)
