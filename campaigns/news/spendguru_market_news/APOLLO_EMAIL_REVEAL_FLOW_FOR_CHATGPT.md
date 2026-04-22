# APOLLO EMAIL REVEAL FLOW — FOR CHATGPT

**Cel:** szybki brief na temat przebudowy flow kontaktów i email reveal w pipeline spendguru_market_news.

---

## Kontekst

Pipeline news-triggered: artykuł → qualify → entity → resolution → kontakty → treści → Apollo.

**Problem do rozwiązania:** poprzedni flow kończył się `BLOCKED_NO_EMAIL` zbyt wcześnie — już na etapie wstępnego wyszukiwania kontaktów (`mixed_people/api_search`). Apollo search często nie zwraca emaila w wynikach prospecting — email jest ujawniany dopiero przez osobny krok `people/match` (reveal credit). Pipeline nigdy nie wywoływał tego kroku.

---

## Nowy flow (krok po kroku)

```
1. article qualified
2. company extracted + resolved
3. contacts found (ANY — bez wymagania emaila)
4. validate_contact_found → jeśli 0 kontaktów → BLOCKED_NO_CONTACT
5. select_best_contacts(top 3 wg tier)
6. generate_outreach_pack() dla WSZYSTKICH (bez email filter)
7. create_news_sequence() — wewnętrzne 4 fazy:
   ├─ FAZA 1: add_to_apollo_list + set_stage (dla WSZYSTKICH, bez emaila)
   ├─ FAZA 2: reveal_email → people/match dla kontaktów bez emaila
   ├─ FAZA 3: update_contact_custom_fields (tylko dla kontaktów Z EMAIL po reveal)
   └─ FAZA 4: notyfikacja READY lub BLOCKED
8. if email_available → READY_FOR_REVIEW
   else → BLOCKED_NO_EMAIL (dopiero teraz, po reveal)
```

**Kluczowa zasada:** `BLOCKED_NO_EMAIL` oznacza teraz *brak emaila po próbie reveal*, nie *brak emaila w wynikach search*.

---

## 5 kluczowych wniosków

### 1. Email reveal (people/match) jest teraz integralną częścią flow

`apollo_client.reveal_email()` — nowa metoda. Wywołuje `POST /api/v1/people/match` z `apollo_contact_id`. Zużywa kredyty reveal. Wynik: email lub None. Toggle: `use_email_reveal: true/false` w campaign_config.

### 2. Kontakty są dodawane do list Apollo PRZED reveal

To zgodne z rzeczywistą logiką Apollo: najpierw identyfikujesz osobę (add to list/stage), potem ujawniasz email. Poprzednio add_to_list następował tylko jeśli kontakt już miał email — co było błędem operacyjnym.

### 3. Outreach packs generowane dla WSZYSTKICH kontaktów (nie tylko z emailem)

`generate_outreach_pack()` nie wymaga emaila. W nowym flow treści są generowane dla wszystkich wybranych kontaktów. Trafiają do:
- Kontakty z emailem (READY): custom fields Apollo
- Kontakty bez emaila (BLOCKED): treści w notyfikacji email (do ręcznego review)

### 4. Model statusów NIE został rozszerzony — tylko doprecyzowany

Nie dodano nowych statusów. Zmieniono metadane `BLOCKED_NO_EMAIL`:
- `stage`: `"contact_search"` → `"email_reveal"`
- `description`: aktualizacja o "po próbie email reveal"
Nowe `final_stage` i `final_reason` w state markingu precyzyjnie opisują, kiedy i dlaczego status został nadany.

### 5. BLOCKED_NO_EMAIL notyfikacja nadal zawiera wygenerowane treści

Powiadomienie BLOCKED_NO_EMAIL wysyłane jest z wnętrza `create_news_sequence()` i zawiera pełne wygenerowane treści 3-mailowej sekwencji — nawet bez emaila. Pozwala operatorowi ocenić jakość treści i ręcznie wyszukać/dodać email.

---

## Wpływ na statusy

| Status | Kiedy | Zmiana |
|--------|-------|--------|
| `BLOCKED_NO_CONTACT` | 0 kontaktów w Apollo | Bez zmian |
| `BLOCKED_NO_EMAIL` | Kontakty w listach, reveal = brak emaila | `stage` zmieniony na `email_reveal` |
| `READY_FOR_REVIEW` | Kontakt w liście, email dostępny (oryginalny lub revealed) | Bez zmian |

### Nowe pola w wynikach pipeline'u

```json
{
  "reveal_attempted": true,
  "reveal_count": 0,
  "email_available": false,
  "contacts_added_to_list": 2
}
```

---

## Czy udało się uniknąć bałaganu w modelu stanów?

**Tak.** Zmiany w modelu statusów są minimalne i celowe:
- Żadnych nowych statusów
- Jeden parametr zmieniony w `STATUS_META` (stage `BLOCKED_NO_EMAIL`)
- Spójność z `state_manager.py`, `notifier.py`, `reporting/run_report.py` zachowana
- Smoke tests: 29/29 pass

---

## Co dalej

1. **Dodać do campaign_config.yaml** dwa parametry:
   ```yaml
   use_email_reveal: true        # domyślnie true
   max_contacts_for_draft: 3     # domyślnie 3
   ```

2. **Zweryfikować listy Apollo** przed pierwszym live run: czy listy "PL Tier 1/2/3 do market_news VSC" istnieją w koncie Apollo?

3. **Uruchomić live test** (1 case) z prawdziwą firmą, która ma znany email w Apollo — weryfikacja E2E: kontakt dodany do listy + email reveal + READY_FOR_REVIEW.

4. **Monitorować kredyty reveal** — `people/match` zużywa kredyty. Przy dużej skali można ograniczyć reveal do Tier 1/2 (`use_email_reveal: false` dla Tier 3).

5. **Evra Fish alias dict fix** — nadal aktualny problem niezależny od tej zmiany (LLM dodaje "Sp. z o.o." → alias dict nie dopasowuje → NO_MATCH). Fix: dodać variant do `company_aliases.yaml`.
