# Campaign Type: CSV do Apollo

## Czym jest ten typ kampanii?

`csv_do_apollo` to pełen flow operacyjny dla kampanii outreachowych prowadzonych na bazie zewnętrznych list kontaktów w formacie CSV.

Flow: **CSV z leadami → generacja spersonalizowanych treści → zapis custom fields w Apollo → tygodniowa sekwencja → enrollment → zapis jako inactive → DOCX do przeglądu → manualna aktywacja**

Jest to **najczęściej uruchamiany typ kampanii** w projekcie Kampanie Apollo — właśnie w nim realizowany jest tygodniowy outreach do list Tier 2 (np. "Tier 2 do VSC").

---

## Czym różni się od innych typów kampanii?

| Cecha | `csv_do_apollo` | `standard` | `news` | `ad_hoc` |
|---|---|---|---|---|
| Źródło leadów | Zewnętrzny CSV (Apollo export / własna lista) | Lista prospectingowa ICP | Trigger artykułowy / rynkowy | Konferencja, LinkedIn, event |
| Trigger maila | Brak twardego triggera (LLM infers weak trigger) | ICP + branża | Artykuł / sygnał rynkowy | Jednorazowy kontekst |
| Generacja treści | Pipeline AI (8 agentów, 3 z LLM) | Pipeline AI | Pipeline AI z triggerem artykułu | Ręcznie lub pipeline |
| Apollo integration | Pełna: custom fields + sekwencja tygodniowa | Sekwencja Apollo | Sekwencja Apollo | Opcjonalna |
| Review przed aktywacją | Zawsze (DOCX + manualna aktywacja) | Zawsze | Zawsze | Zawsze |
| Cadence | D0 / D+2 / D+2 | D0 / D+2 / D+2 | D0 / D+2 / D+2 | D0 / D+2 / D+2 |

---

## Input

- Plik CSV z kontaktami w formacie Apollo export (separator `;`)
- Kolumny: First Name, Last Name, Title, Company Name, Email, Seniority, Industry, Keywords, Person Linkedin Url, Website, itd.
- Lokalizacja: `CSV do kampanii/` (pliki tygodniowe)
- Format imion: może być ALL CAPS lub normalne (normalizer obsługuje oba)

**Lokalizacja CSV w repo:**
```
CSV do kampanii/
  2026-04-21 Tier 2 do VSC.csv
  TEST STRUKTURY 2026-04-21 Tier 2 do VSC.csv   ← walidacja struktury
```

---

## Output

1. **Apollo custom fields** — 6 pól per kontakt: `sg_email_step_{1,2,3}_{subject,body}`
2. **Tygodniowa sekwencja Apollo** — 1 sekwencja / wielu kontaktów / dynamic content via merge tags
3. **Status sekwencji: inactive** — sekwencja NIE jest aktywna do momentu manualnego review
4. **DOCX do przeglądu** — plik Word z Step 1 / FU1 / FU2 dla wszystkich kontaktów
5. **Lokalny engagement tracker** — `data/contact_engagement/{contact_key}.json`
6. **Run report** — `outputs/runs/{timestamp}_{campaign_name}/run_report.md`

---

## Cel operacyjny

Umożliwić tygodniowy, spersonalizowany outreach do listy kilkudziesięciu leadów z jednoczesnym:
- zachowaniem jakości treści (AI + reguły z source_of_truth)
- pełną kontrolą przed wysyłką (manualne review DOCX + aktywacja w Apollo)
- śledzeniem historii kampanii per kontakt
- automatycznym zapisem treści w Apollo (dynamiczny content per kontakt przez merge tagi)

---

## Kluczowe zależności w repo

### Plik wejściowy (pipeline)
- `src/pipelines/run_csv_campaign.py` — główny entry point, CLI: `--config <yaml> --mode draft`

### Agenty
- `src/agents/csv_import/csv_normalizer.py` — normalizacja CSV (gender, vocative, kolumny)
- `src/core/weekly_sequence_orchestrator.py` — tworzenie sekwencji + enrollment + aktywacja
- `src/core/apollo_campaign_sync.py` — sync custom fields do Apollo
- `src/core/email_thread_formatter.py` — budowa Step 1 / FU1 / FU2 z thread simulation
- `src/core/followup_generator.py` — LLM + heuristic generation FU1/FU2
- `src/core/icp_tier_resolver.py` — automatyczne wykrywanie Tier na podstawie stanowiska

### Prompts
- `prompts/csv_import/csv_trigger_inference.md` — hipoteza dla kontaktów bez mocnego triggera
- `prompts/shared/message_writer.md` — główny agent piszący email
- `prompts/shared/follow_up_writer.md` — FU1 i FU2
- `prompts/shared/qa_reviewer.md` — walidacja jakości treści

### Source of truth
- `source_of_truth/apollo_custom_fields.yaml` — nazwy pól Apollo, cadence, mapping
- `source_of_truth/icp_tiers.yaml` — definicje Tier 1/2/3
- `source_of_truth/email_style_guide.yaml` — reguły stylu
- `source_of_truth/spendguru_positioning.yaml` — pozycjonowanie SpendGuru
- `source_of_truth/apollo_campaign_types.yaml` — typy kampanii i delivery types

### Vocative / gender
- `context/Vocative names od VSC.csv` — słownik polskich imion (mianownik → wołacz + płeć)

### Integracja Apollo
- `Integracje/apollo_client.py` — klient Apollo API
- `Integracje/.env` — APOLLO_API_KEY

### Konfiguracje kampanii
- `configs/csv_import/` — YAML pliki konfiguracyjne per kampania

### Outputy
- `outputs/runs/{timestamp}_{campaign_name}/` — wyniki pipeline'u
- `outputs/word_campaigns/` — pliki DOCX do review

---

## Uwaga organizacyjna

> Ten folder (`campaigns/csv_do_apollo/`) jest **niedestrukcyjną warstwą organizacyjną** — nie zastępuje istniejącego runtime ani nie przenosi żadnych plików.
>
> Istniejące pliki produkcyjne (`src/pipelines/run_csv_campaign.py`, `configs/csv_import/`, `source_of_truth/` itd.) działają dokładnie tak jak dotychczas. Ten folder zbiera i opisuje ten typ kampanii, aby był widoczny jako osobna kategoria w strukturze `campaigns/`.

---

## Jak uruchomić kampanię tego typu

```bash
# Standardowy tryb draft (generacja treści, bez push do Apollo):
python src/pipelines/run_csv_campaign.py --config configs/csv_import/<plik>.yaml --mode draft

# Pełny run z push do Apollo i buildowaniem sekwencji:
# Użyj dedykowanego skryptu produkcyjnego (np. tests/run_production_tier2_vsc_2026_04_21.py
# jako wzorzec) lub ustaw apollo.mode: weekly_sequence w config YAML.
```

---

## Historia kampanii tego typu

- **2026-04-20** — pierwszy live test weekly sequence (W17-2026-LiveTest-PL), 3 kontakty Tier 2
- **2026-04-21** — produkcyjna kampania Tier 2 do VSC (plik: `2026-04-21 Tier 2 do VSC.csv`)

---

> **Uwaga — artefakty testowe:**
> Plik `outputs/word_campaigns/csv_do_apollo_test_review.docx` to artefakt **walidacji struktury repo** (test techniczny na kontakcie z syntetycznymi danymi `TEST STRUKTURY...`).
> **Nie jest wzorcem jakości treści.** Wzorce jakościowe kampanii: `outputs/word_campaigns/tier2_real_pilot_review_v2.docx` i inne pliki `_review` / `_sent` z tego folderu.
