# Execution Flow — CSV do Apollo

Kompletny, krok po kroku opis flow kampanii typu `csv_do_apollo`.

---

## Diagram przepływu

```
CSV (semicolon-delimited)
    ↓
[1] Wczytanie i normalizacja (csv_normalizer / rich_contact_profile)
    ↓
[2] ICP Tier detection (icp_tier_resolver)
    ↓
[3] Pipeline agentów (lead scoring → research → persona → hypothesis → message → QA)
    ↓
[4] Generacja FU1 + FU2 (followup_generator + follow_up_writer)
    ↓
[5] Budowa outreach_pack (email_thread_formatter)
         Step 1 (intro)
         FU1 (nowa wartość + thread Step 1)
         FU2 (krótki + thread Step 1 + FU1)
    ↓
[6] Apollo custom fields sync (apollo_campaign_sync)
         sg_email_step_1_subject / sg_email_step_1_body
         sg_email_step_2_subject / sg_email_step_2_body
         sg_email_step_3_subject / sg_email_step_3_body
    ↓
[7] Budowa tygodniowej sekwencji (weekly_sequence_orchestrator)
         Tworzenie sekwencji → create steps (D0/D+2/D+2) →
         Update templates (merge tags) → set schedule
    ↓
[8] Enrollment kontaktów (round-robin multi-mailbox)
    ↓
[9] Sekwencja zapisywana jako INACTIVE
    ↓
[10] Generacja DOCX do review (python-docx)
    ↓
[11] Manual review → manualna aktywacja w Apollo UI
         (POST /approve + approve touches)
```

---

## Szczegółowy opis kroków

### Krok 1 — Import i normalizacja CSV

**Moduł:** `src/agents/csv_import/csv_normalizer.py`
**Tryb:** `normalize_contacts_rich()` — rozszerzony profil z 6 sekcjami

Co się dzieje:
- Wczytanie CSV z separatorem `;` (utf-8-sig encoding)
- Mapowanie kolumn (case-insensitive, 100+ aliasów — `src/core/rich_contact_profile.py`)
- Wykrycie płci (słownik `context/Vocative names od VSC.csv` → `polish_names.py`)
- Budowa wołacza (formy grzecznościowe: "Panie Adamie", "Pani Anno")
- Budowa powitania: "Dzień dobry Panie Adamie," / "Dzień dobry Pani Anno," / "Dzień dobry,"
- Ekstrakcja keywords, URL-ów, lokalizacji, seniority
- Persystencja rich profile: `data/contact_engagement/{key}_rich_profile.json`

**Fallback:** gender="unknown", vocative=None, greeting="Dzień dobry,"

---

### Krok 2 — ICP Tier Detection

**Moduł:** `src/core/icp_tier_resolver.py`
**Źródło:** `source_of_truth/icp_tiers.yaml`

Tiers:
- **Tier 1** (`tier_1_c_level`) — CEO, CFO, Prezes, Właściciel → perspektywa strategiczna
- **Tier 2** (`tier_2_procurement_management`) — CPO, Dyrektor Zakupów, Head of Procurement → kontrola taktyczna
- **Tier 3** (`tier_3_buyers_operational`) — Buyer, Category Manager, Kupiec → execution
- **Tier Uncertain** (`tier_uncertain`) — fallback → suggest Tier 2

Wynik tier jest dodawany do kontekstu LLM jako `__icp_tier_active`.

---

### Krok 3 — Pipeline agentów

Kolejność: lead_scoring → account_research → persona_selection → hypothesis → message → qa

**Lead scoring** (heurystyka)
- Input: dane firmy + branża + kontakt
- Output: lead_score (0-100), decision (deep/standard/light/reject)

**Account research** (heurystyka)
- Input: dane firmy
- Output: company_summary, business_signals, potential_trigger

**Persona selection** (heurystyka)
- Input: job title → TITLE_TO_PERSONA map
- Output: persona_type (cpo / buyer / cfo / ceo / supply_chain / unknown)

**CSVTriggerInference** (LLM lub fallback)
- Prompt: `prompts/csv_import/csv_trigger_inference.md`
- Input: persona, job title, firma, branża, keywords, notes
- Output: hypothesis + trigger_type (weak_inferred / generic)
- Fallback: agent_hypothesis() z zamockowanym row

**MessageWriter_CSV** (LLM lub fallback)
- Prompt: `prompts/shared/message_writer.md`
- Input: hypothesis + contact (z gender/vocative/greeting już wyliczonymi!)
- Output: subject + body (bez podpisu) + word_count
- Fallback: `_csv_message_heuristic()` w run_csv_campaign.py
- WAŻNE: LLM NIE zgaduje płci ani wołacza — dostaje je gotowe z normalizatora

**QA Reviewer** (LLM lub fallback)
- Prompt: `prompts/shared/qa_reviewer.md`
- Output: qa_score (0-100), decision (approve/rewrite/manual_review/reject), issues[]

---

### Krok 4 — Generacja FU1 i FU2

**Moduł:** `src/core/followup_generator.py`
**Prompt:** `prompts/shared/follow_up_writer.md`

FU1 (step_number=2):
- Wnosi nową wartość (nie jest tylko przypomnieniem!)
- Kontynuuje wątek hipotezy Step 1
- Pokazuje 1 konkretny mechanizm / konsekwencję

FU2 (step_number=3):
- Krótki, bez presji
- Jasne, łatwe CTA
- Nie wysyła się bez odpowiedzi FU1

**Fallback:** heurystyki z predefiniowanymi szablonami per persona

---

### Krok 5 — Budowa outreach_pack

**Moduł:** `src/core/email_thread_formatter.py`
**Funkcja:** `build_outreach_pack()`

Buduje 3 kompletne emaile:

**email_1** (`build_email_1()`):
- body_core: treść Step 1 bez podpisu
- body: treść + podpis plain
- body_html: HTML z podpisem (pełny, ze stopką)
- body_html_nosig: HTML bez podpisu ← używany do sg_email_step_1_body

**follow_up_1** (`build_follow_up_1()`):
- body_core: treść FU1 bez podpisu i bez thread
- body_html_nosig: HTML z podpisem + separator HR + zacytowany Step 1 ← do sg_email_step_2_body
- Thread header: "W dniu {data}, {imię} {nazwisko} <{email}> napisał(a):"

**follow_up_2** (`build_follow_up_2()`):
- body_core: treść FU2 bez podpisu i bez thread
- body_html_nosig: HTML z podpisem + separator HR + zacytowany Step 1 + FU1 ← do sg_email_step_3_body
- Thread header: obejmuje cały wątek (Step 1 + FU1)

---

### Krok 6 — Apollo Custom Fields Sync

**Moduł:** `src/core/apollo_campaign_sync.py`
**Klient:** `Integracje/apollo_client.py`

Mapowanie (z `source_of_truth/apollo_custom_fields.yaml`):
```
outreach_pack.email_1.subject         → sg_email_step_1_subject
outreach_pack.email_1.body_html_nosig → sg_email_step_1_body
outreach_pack.follow_up_1.subject     → sg_email_step_2_subject
outreach_pack.follow_up_1.body_html_nosig → sg_email_step_2_body
outreach_pack.follow_up_2.subject     → sg_email_step_3_subject
outreach_pack.follow_up_2.body_html_nosig → sg_email_step_3_body
```

Osobny krok (poza outreach pack): ustawienie `pl_signature_tu` na każdym kontakcie.

**Limit Apollo:** max 5000 znaków per pole — body_html_nosig typowo ~3000-3300 znaków.

---

### Krok 7 — Budowa tygodniowej sekwencji

**Moduł:** `src/core/weekly_sequence_orchestrator.py`

1. **Naming:** `generate_sequence_name()` → format `W{week}-{year}-CSVImport-PL[-suffix]`
2. **Tworzenie:** `POST /v1/emailer_campaigns` z `{name, active: false}`
3. **Steps:** `POST /v1/emailer_steps` × 3 z cadence D0/D+2/D+2
4. **Templates:** `PUT /api/v1/emailer_templates/{id}` — ustawienie merge tagów
   - Step 1: subject=`{{sg_email_step_1_subject}}`, body=`{{sg_email_step_1_body}}{{pl_signature_tu}}`
   - Step 2: subject=`{{sg_email_step_2_subject}}`, body=`{{sg_email_step_2_body}}`
   - Step 3: subject=`{{sg_email_step_3_subject}}`, body=`{{sg_email_step_3_body}}`
5. **Schedule:** `PUT /api/v1/emailer_campaigns/{id}` z `{emailer_schedule_id}`

**Ważne:** Apollo auto-tworzy 1 empty touch + 1 template per step. NIE dodawaj dodatkowych touches — duplikaty blokują aktywację.

---

### Krok 8 — Enrollment kontaktów

**Moduł:** `src/core/weekly_sequence_orchestrator.py` → `enroll_batch()`
**Metoda:** Round-robin multi-mailbox (5 mailboxów @profitia.pl)

Przed enrollmentem: `preflight_batch()` — sprawdza czy kontakt ma Apollo contact_id i czy email jest ważny.

Enrollment API: `POST /api/v1/emailer_campaigns/{id}/add_contact_ids` z `send_email_from_email_account_id`.

**Uwaga:** Enrollment do inactive sequence powoduje status "paused" dla kontaktu. To jest oczekiwane — kontakty startują po aktywacji.

---

### Krok 9 — Sekwencja pozostaje INACTIVE

Sekwencja jest zapisywana bez aktywacji. To celowe — wymagany jest manual review DOCX przed aktywacją.

---

### Krok 10 — Generacja DOCX

Biblioteka: `python-docx`
Output: `outputs/word_campaigns/{kampania_review}.docx`

Plik zawiera dla każdego kontaktu:
- Nagłówek: imię, nazwisko, stanowisko, firma, email
- Step 1: subject + body (plain text)
- FU1: subject + body
- FU2: subject + body

---

### Krok 11 — Manual review i aktywacja

Sprawdź DOCX zgodnie z `review_checklist.md`.

Aktywacja sekwencji (dwa obowiązkowe kroki):
1. `POST /api/v1/emailer_campaigns/{id}/approve` — aktywacja sekwencji
2. `POST /api/v1/emailer_touches/{id}/approve` — zatwierdzenie każdego touch osobno

**Tylko przez API lub VSC skrypt.** PUT z `active: true` NIE aktywuje sekwencji.

---

## Co jest krytyczne dla jakości

1. **Wołacz i płeć** — muszą pochodzić z normalizatora (słownik), nie z LLM. Błędy tu propagują się do każdego maila.
2. **CTA z prawdziwym linkiem Calendly** — placeholder `[link do Calendly]` musi być zastąpiony przed zapisem do Apollo.
3. **Threading FU1/FU2** — FU1 musi zawierać thread Step 1, FU2 musi zawierać thread Step 1 + FU1. Sprawdź separator HR + header "W dniu..."
4. **Podpis** — `pl_signature_tu` jest osobnym polem, nie embedded w body Step 1. FU1/FU2 mają podpis embedded w body_html_nosig.
5. **Rozmiar custom fields** — max 5000 znaków. Nie wstawiaj META_BLOCK ani pełnego thread history do custom fields.
6. **Aktywacja sekwencji** — tylko przez /approve, nie przez PUT.

---

## Co najczęściej się psuło (historia regresji)

| Problem | Opis | Gdzie sprawdzić |
|---|---|---|
| `@https://` w body | Błędny token w thread email reference (zamiast `from@domain.com` wchodziło `@https://...`) | `validate_outreach_pack()` — sprawdź body FU1/FU2 |
| Zdublowane CTA | Dwa bloki CTA w jednym mailu (raz z LLM, raz z postprocessingu) | Sprawdź body każdego emaila |
| Brak thread header | FU1/FU2 bez "W dniu... napisał(a)" — Apollo nie pokazuje wątku | Sprawdź `body_html_nosig` FU1/FU2 |
| Podpis w body Step 1 | `pl_signature_tu` wchodzi do body Step 1, a potem template dodaje go znowu | Sprawdź body_html_nosig Step 1 |
| Placeholder Calendly | `[link do Calendly]` zostaje w treści, zamiast prawdziwego URL | Grep na `[link do Calendly]` w outreach_pack |
| Nie ma "numer telefonu" | Brakuje alternatywy telefonicznej w CTA | Sprawdź body Step 1 |
| Activation via PUT | PUT z `active: true` nie aktywuje — trzeba POST /approve | Zawsze używaj `activate_sequence()` |
| Enrollment paused | Kontakt enrolled do inactive sequence → paused zamiast active | Oczekiwane — aktywacja po review rozwiązuje |
| Merge tag syntax | `{{custom.field_name}}` zamiast `{{field_name}}` — nie działa | Weryfikuj template bodies przed aktywacją |
| Gender unknown dla rzadkich imion | Imię nieznane w słowniku → gender=unknown → neutralna forma "Dzień dobry," | Sprawdź warnings normalizatora |

---

## Jakie regresje kontrolować przy każdym runie

1. `@https://` w body FU1/FU2 — BLOKUJĄCE
2. Placeholder `[link do Calendly]` — BLOKUJĄCE
3. Brak thread header "W dniu" w FU1/FU2 — BLOKUJĄCE
4. Zdublowane CTA — BLOKUJĄCE
5. Zbyt długi custom field (>5000 znaków) — BLOKUJĄCE (Apollo odrzuci)
6. Podpis w body Step 1 — BLOKUJĄCE (pojawi się dwukrotnie)
7. Brak alternatywy telefonicznej — MIĘKKIE
8. Merge tags nieresolwujące (czerwone w Apollo) — OSTRZEŻENIE (sprawdź nazwy pól)
