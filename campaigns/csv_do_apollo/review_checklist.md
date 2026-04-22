# Review Checklist — CSV do Apollo

Checklista do wykonania **przed aktywacją sekwencji w Apollo**.

Sprawdź każdy punkt. Jeśli którykolwiek = NIE → zatrzymaj i popraw.

---

## A. Stan sekwencji Apollo

- [ ] Sekwencja jest **inactive** (nie jest aktywna przed review)
- [ ] Sekwencja ma poprawną nazwę zgodną z konwencją `W{week}-{year}-CSVImport-PL[-suffix]`
- [ ] Liczba kroków sekwencji = 3 (Step 1, FU1, FU2)
- [ ] Cadence kroków: Step 1 = D0 (0 min), FU1 = D+2 (2880 min), FU2 = D+2 (2880 min)
- [ ] Każdy krok ma poprawne merge tagi w template (nie hardcoded content)
  - Step 1 subject: `{{sg_email_step_1_subject}}`
  - Step 1 body: `{{sg_email_step_1_body}}{{pl_signature_tu}}`
  - FU1 subject: `{{sg_email_step_2_subject}}`
  - FU1 body: `{{sg_email_step_2_body}}`
  - FU2 subject: `{{sg_email_step_3_subject}}`
  - FU2 body: `{{sg_email_step_3_body}}`

---

## B. Liczba i tożsamość kontaktów

- [ ] Liczba enrolled kontaktów zgadza się z liczbą wierszy w CSV (minus evenuale rejekcje QA)
- [ ] Każdy kontakt ma poprawny email
- [ ] Każdy kontakt ma Apollo `contact_id` (preflight check PASS)
- [ ] Tier 2-specific: kontakty Tier 2 są świadomie dodane lub usunięte w zależności od intent
- [ ] Wyjątki (np. kontakty odrzucone w preflight) są świadomie zaznaczone w raporcie

---

## C. Custom fields — weryfikacja treści

Sprawdź DOCX i/lub readback z Apollo dla każdego kontaktu:

- [ ] `sg_email_step_1_subject` — nie jest pusty, zawiera nazwę firmy lub personalizację
- [ ] `sg_email_step_1_body` — nie jest pusty, treść Step 1 bez podpisu
- [ ] `sg_email_step_2_subject` — format "Re: {temat Step 1}"
- [ ] `sg_email_step_2_body` — treść FU1 z podpisem + thread Step 1
- [ ] `sg_email_step_3_subject` — format "Re: {temat Step 1}"
- [ ] `sg_email_step_3_body` — treść FU2 z podpisem + full thread
- [ ] `pl_signature_tu` — podpis ustawiony i poprawny (HTML, bez błędów)

---

## D. Treść emaili — krytyczne reguły jakości

### Blokujące (STOP jeśli którykolwiek = NIE)

- [ ] **BRAK `@https://`** — w żadnym polu nie ma sekwencji `@https://` (błąd thread email token)
- [ ] **BRAK `[link do Calendly]`** — placeholder zastąpiony prawdziwym linkiem Calendly
- [ ] **BRAK duplikatu CTA** — każdy email ma dokładnie jeden blok CTA
- [ ] **Threading FU1 obecny** — FU1 body zawiera "W dniu" przed separatorem
- [ ] **Threading FU2 obecny** — FU2 body zawiera "W dniu" (full thread Step 1 + FU1)
- [ ] **Podpis Step 1 nie jest embedded** — `sg_email_step_1_body` NIE zawiera podpisu (podpis = `pl_signature_tu`)
- [ ] **Rozmiar custom fields** — żadne pole nie przekracza 5000 znaków

### Ważne (POPRAW przed aktywacją)

- [ ] CTA zawiera **prawidłowy link Calendly Tier 2**: `https://calendly.com/profitia/standard-negocjacji-i-oszczednosci`
- [ ] CTA zawiera **alternatywę telefoniczną** (prośba o numer, słowo "oddzwonię")
- [ ] Formulacja telefoniczna jest naturalna: "Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę śmiało przesłać numer - oddzwonię."
- [ ] **Brak zakazanych sformułowań** z email_style_guide.yaml (np. "porządek danych", "nasza platforma")
- [ ] **Brak generycznych treści** — mail nie jest wysyłalny do 20 osób bez zmian
- [ ] **FU2 wnosi nową wartość** — nie jest tylko przypomnieniem FU1
- [ ] **Powitanie poprawne** — "Dzień dobry Panie Adamie," (małe "p" w następnym akapicie)
- [ ] **Brak em-dash** — wszędzie zwykły myślnik " - " zamiast "—"

---

## E. DOCX do review

- [ ] DOCX jest wygenerowany i dostępny w `outputs/word_campaigns/`
- [ ] DOCX zawiera dane dla WSZYSTKICH kontaktów z kampanii
- [ ] Step 1, FU1, FU2 są czytelne dla każdego kontaktu
- [ ] Podpis NIE jest w Step 1 body w DOCX (podpis jest osobny w Apollo)

---

## F. Mailbox i enrollment

- [ ] Kontakty są rozdzielone round-robin na 5 mailboxów @profitia.pl
- [ ] Żaden mailbox nie dostał nieproporjonalnie dużej liczby kontaktów
- [ ] Enrollment status w Apollo: kontakty mają status "paused" (oczekiwane dla inactive sequence)
- [ ] Po aktywacji sekwencji kontakty zmienią status na "active" automatycznie

---

## G. Aktywacja — OSTATNI KROK

Aktywuj sekwencję dopiero po zaliczeniu wszystkich punktów A-F.

```
Aktywacja wymaga 2 kroków:
1. POST /api/v1/emailer_campaigns/{id}/approve
2. POST /api/v1/emailer_touches/{id}/approve  ← dla KAŻDEGO touch osobno
```

- [ ] Oba kroki wykonane (kampania + touches)
- [ ] Weryfikacja po aktywacji: status sekwencji = "active" w Apollo
- [ ] Weryfikacja: kontakty zmieniły status z "paused" na "active"
- [ ] Pierwsza wysyłka (Step 1) zaplanowana na oczekiwany termin

---

## H. Po kampanii

- [ ] Engagement tracker zaktualizowany (`data/contact_engagement/`)
- [ ] Campaign history zaktualizowany (`data/campaign_history/`)
- [ ] Run report dostępny w `outputs/runs/{timestamp}_{campaign_name}/run_report.md`
- [ ] Backup workspace wykonany (task: "Backup workspace")

---

## Szybkie sprawdzenie regresji (5-minutowa checklista)

```
grep -r "@https://"           outputs/runs/{last_run}/outreach_pack.json
grep -r "[link do Calendly]"  outputs/runs/{last_run}/outreach_pack.json
grep -r "W dniu"              outputs/runs/{last_run}/outreach_pack.json
```

Wszystkie trzy powinny dać wyniki (lub brak dla pierwszych dwóch, obecność dla trzeciego).
