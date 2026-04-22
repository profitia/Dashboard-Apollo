# Apollo Mapping — CSV do Apollo

Kompletny opis integracji tego campaign type z Apollo.io.

---

## 1. Custom Fields — Grupa VSC

Pola zdefiniowane w Apollo w grupie "VSC". Nazwy muszą dokładnie odpowiadać polom w Apollo.

| Pole Apollo | Typ | Zawartość | Merge Tag |
|---|---|---|---|
| `sg_email_step_1_subject` | single-line text | Temat Step 1 | `{{sg_email_step_1_subject}}` |
| `sg_email_step_1_body` | multi-line text | Body Step 1 (HTML, bez podpisu) | `{{sg_email_step_1_body}}` |
| `sg_email_step_2_subject` | single-line text | Temat FU1 | `{{sg_email_step_2_subject}}` |
| `sg_email_step_2_body` | multi-line text | Body FU1 (HTML, z podpisem + thread) | `{{sg_email_step_2_body}}` |
| `sg_email_step_3_subject` | single-line text | Temat FU2 | `{{sg_email_step_3_subject}}` |
| `sg_email_step_3_body` | multi-line text | Body FU2 (HTML, z podpisem + full thread) | `{{sg_email_step_3_body}}` |
| `pl_signature_tu` | multi-line text | HTML podpis (Tomasz Uściński) | `{{pl_signature_tu}}` |

**Źródło konfiguracji:** `source_of_truth/apollo_custom_fields.yaml`

**Limit Apollo:** max 5000 znaków per pole. Typowy rozmiar body:
- sg_email_step_1_body: ~1500-2500 znaków (body + formatowanie HTML)
- sg_email_step_2_body: ~2500-4000 znaków (body + podpis + thread Step 1)
- sg_email_step_3_body: ~3000-4500 znaków (body + podpis + thread Step 1 + FU1)
- pl_signature_tu: ~800-1200 znaków

---

## 2. Dynamiczny content per kontakt — mechanizm

**Model:** 1 sekwencja / wielu kontaktów / unikalne treści per kontakt

**Mechanizm:**
1. Custom fields na każdym kontakcie = unikalne treści
2. Template sekwencji = merge tagi (nie hardcoded content)
3. Apollo resolwuje merge tagi w momencie wysyłki (send time)

**Działająca składnia merge tagów:**
```
{{sg_email_step_1_subject}}   ✓
{{sg_email_step_1_body}}      ✓
{{pl_signature_tu}}            ✓
```

**NIE działają:**
```
{{custom.sg_email_step_1_body}}        ✗
{{custom_field.sg_email_step_1_body}}  ✗
{{field_id}}                           ✗
```

**Weryfikacja API:** Przed wysyłką API zwraca `subject: null` i pusty `body_html` dla scheduled messages z merge tagami — to jest oczekiwane. Weryfikacja contentu możliwa tylko po faktycznym wysłaniu przez `emailer_messages/search`.

**Nieresolwujące tagi:** Apollo owija je w `<span style="background-color:#D54D4A">` (czerwony marker) — widoczne w UI przed wysyłką.

---

## 3. Template sekwencji — merge tagi w Apollo

Jak wyglądają template'y wewnątrz sekwencji Apollo:

| Step | Subject | Body HTML |
|---|---|---|
| Step 1 | `{{sg_email_step_1_subject}}` | `{{sg_email_step_1_body}}{{pl_signature_tu}}` |
| Step 2 (FU1) | `{{sg_email_step_2_subject}}` | `{{sg_email_step_2_body}}` |
| Step 3 (FU2) | `{{sg_email_step_3_subject}}` | `{{sg_email_step_3_body}}` |

**Dlaczego Step 1 ma `{{pl_signature_tu}}` a FU1/FU2 nie?**
- Step 1: podpis jest osobnym custom field (więcej elastyczności, można zmienić jeden raz dla wszystkich)
- FU1/FU2: podpis jest wbudowany bezpośrednio w `sg_email_step_{2,3}_body` — PRZED separatorem HR i thread historyModule: `src/core/weekly_sequence_orchestrator.py` → `MERGE_TAG_TEMPLATES`

---

## 4. Sequence naming convention

**Format:** `W{week}-{year}-{campaign_type}-{market}[-suffix]`

**Przykłady:**
```
W17-2026-CSVImport-PL
W17-2026-CSVImport-PL-Tier2-VSC-2026-04-21
W20-2026-Standard-PL
```

**Parametry:**
- week: numer tygodnia ISO (1-52)
- year: rok 4-cyfrowy
- campaign_type: kod z `campaign_name_builder.py` (CSVImport, Standard, NewsTrig, itd.)
- market: PL / EN / Gen

**Moduł:** `src/core/weekly_sequence_orchestrator.py` → `generate_sequence_name()`

---

## 5. Cadence sekwencji

Standard projektu od 2026-04-19: **D0 / D+2 / D+2**

| Step | Opóźnienie | wait_time (minuty) | Label |
|---|---|---|---|
| Step 1 | D0 | 0 | Email wysyłany natychmiast po aktywacji |
| Step 2 | D+2 | 2880 | FU1 po 2 dniach |
| Step 3 | D+2 | 2880 | FU2 po kolejnych 2 dniach |

**Źródło:** `source_of_truth/apollo_custom_fields.yaml` → `sequence_cadence`
**Override:** per kampania w config YAML pod kluczem `sequence_cadence`

**API note:** Apollo wymaga `wait_mode: "minute"` przy tworzeniu stepów — bez tego 422.

---

## 6. Tworzenie sekwencji — kolejność API calls

Zweryfikowany flow (E2E test PASS):

```
1. POST /v1/emailer_campaigns           → create sequence (active: false)
2. POST /v1/emailer_steps × 3          → create steps (z wait_mode: "minute")
3. GET  /api/v1/emailer_campaigns/{id} → pobierz auto-created templates
4. PUT  /api/v1/emailer_templates/{id} × 3 → ustaw merge tagi
5. PUT  /api/v1/emailer_campaigns/{id} → ustaw schedule (emailer_schedule_id)
```

**Krytyczna uwaga:** Apollo auto-tworzy 1 empty touch + 1 template per step. NIE twórz dodatkowych touches — duplikaty blokują aktywację i powodują podwójne maile.

---

## 7. Enrollment kontaktów

**Endpoint:** `POST /api/v1/emailer_campaigns/{id}/add_contact_ids`

**Payload:**
```json
{
  "contact_ids": ["id1", "id2"],
  "send_email_from_email_account_id": "mailbox_id",
  "sequence_active_in_other_campaigns": true
}
```

**Multi-mailbox model:** 5 mailboxów @profitia.pl, round-robin distribution
- tomasz@profitia.pl
- uscinski@profitia.pl
- t.uscinski@profitia.pl
- tomasz-uscinski@profitia.pl
- tuscinski@profitia.pl

**Endpoint do pobierania mailboxów:** `GET /api/v1/email_accounts` (wymaga master key)

**Weryfikacja:** `POST /v1/contacts/search` z `emailer_campaign_ids` → `contact_campaign_statuses.send_email_from_email_account_id`

---

## 8. Aktywacja sekwencji

**WAŻNE:** PUT z `active: true` NIE aktywuje sekwencji.

Wymagane dwa kroki:
```
1. POST /api/v1/emailer_campaigns/{id}/approve     → aktywacja sekwencji
2. POST /api/v1/emailer_touches/{id}/approve × N  → zatwierdzenie każdego touch
```

Oba kroki są wymagane. Bez approve touches, emaile się nie schedulują.

**Deaktywacja:** `POST /api/v1/emailer_campaigns/{id}/deactivate`

**Moduł:** `Integracje/apollo_client.py` → `activate_sequence(seq_id)`

---

## 9. Threading FU1 / FU2

**Moduł:** `src/core/email_thread_formatter.py`

**Format separatora:**
```html
<hr style="border: none; border-top: 1px solid #b5b5b5; margin: 20px 0;">
```

**Format thread header:**
```
W dniu {dd.mm.YYYY}, {Imię} {Nazwisko} <{email}> napisał(a):
```

**FU1 body (body_html_nosig) = content + podpis + HR separator + zacytowany Step 1**
**FU2 body (body_html_nosig) = content + podpis + HR separator + zacytowany Step 1 + FU1**

**Weryfikacja:** Sprawdź czy `"W dniu"` jest w body FU1 i FU2.

---

## 10. Podpis — model osobnego pola

**Custom field:** `pl_signature_tu` (TU = Tomasz Uściński)
**Typ:** multi-line text / textarea
**Zawartość:** HTML z podpisem + szara stopka (dane kontaktowe, profitia.pl)

**Dlaczego osobne pole:**
- Jeden update pola zmienia podpis dla wszystkich kontaktów i wszystkich kampanii jednocześnie
- Większa elastyczność (można zmienić podpis bez regeneracji treści)
- Unikamy duplikacji ~1000 znaków HTML per kontakt per pole

**Uwaga:** Podpis jest EMBEDDED w FU1/FU2 (w body_html_nosig), bo FU1/FU2 mają thread history po podpisie. W Step 1 jest OSOBNO (merge tag w template).

---

## 11. Typowe blokady Apollo (known gotchas)

### contacts_finished_in_other_campaigns
Kontakty zakończone w poprzednich sekwencjach Apollo są domyślnie blokowane.
- **Rozwiązanie A:** W Apollo UI: "Add Anyway" przy enrollmencie
- **Rozwiązanie B:** Settings > Sequences > odznacz blokadę "contacts_finished_in_other_campaigns"
- **Przez API:** nie da się obejść tej blokady programatycznie

### Archived sequences z enrolled contacts
Archiwizacja sekwencji z aktywnymi kontaktami powoduje corrupted state.
- Zawsze twórz nową sekwencję dla nowej kampanii
- Nie używaj archived sequences do enrollmentu

### `remove_contact_ids` na archived sequence
- Endpoint `remove_contact_ids` zwraca 404 na archived sequence
- Trzeba: unarchive → remove → re-archive (ale nawet to nie czyści finished status)

### Enrollment do inactive sequence
- Kontakty enrolled do inactive sequence mają status "paused" — to jest oczekiwane
- Po aktywacji sekwencji przechodzą do active i startują od Step 1

### API readback merge tags
- API pokazuje `subject: null` i pusty `body_html` dla scheduled messages z merge tagami
- To jest normalne — Apollo resolwuje tagi w momencie wysyłki
- Weryfikacja możliwa tylko przez `emailer_messages/search` po faktycznym wysłaniu

---

## 12. Apollo Contact ID — prerequisite

Każdy kontakt musi istnieć w Apollo (mieć `contact_id`) przed enrollmentem.

Jeśli kontakt nie istnieje:
1. `apollo_client.create_contact(email, first_name, last_name, title, company)`
2. Poczekaj chwilę (Apollo może potrzebować czasu na propagację)
3. `apollo_client.find_contact_by_email(email)` → pobierz contact_id

**Preflight check:** `src/core/enrollment_preflight.py` → `preflight_batch()` waliduje czy contact_id istnieje.
