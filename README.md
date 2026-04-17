# AI Outreach System — Profitia / SpendGuru

Lokalny MVP systemu do personalizowanego outreachu B2B.

## Co robi projekt

System czyta dane kontaktów z CSV, przepuszcza je przez pipeline 8 agentów i generuje:

- spersonalizowane wiadomości email,
- scoring leadów,
- ocenę jakości (QA),
- payloady pod Apollo custom fields,
- raport kampanii.

Tryb **DRAFT** — nic nie jest wysyłane, nic nie trafia do Apollo.

## Jak uruchomić

### Wymagania

```bash
pip install -r requirements.txt
```

### Konfiguracja LLM (opcjonalna)

Skopiuj `.env.example` do `.env` i wklej klucz API:

```bash
cp .env.example .env
# Edytuj .env i wklej OPENAI_API_KEY
```

Jeśli klucz API nie jest ustawiony, pipeline automatycznie przechodzi na **heurystyki (fallback)** — dane wyjściowe są generowane z szablonów, nie z modelu.

| Zmienna | Opis | Domyślnie |
|---|---|---|
| `LLM_PROVIDER` | Provider LLM | `openai` |
| `LLM_MODEL` | Model do użycia | `gpt-4o-mini` |
| `OPENAI_API_KEY` | Klucz API OpenAI | (brak) |

### Z terminala

```bash
# Pipeline oryginalny (article-triggered / generic)
python src/run_campaign.py --config configs/cpo_pl_test.yaml --mode draft

# Pipeline CSV Import
python src/pipelines/run_csv_campaign.py --config configs/csv_import/csv_import_pl_test.yaml --mode draft
```

### Z VS Code (Task)

1. `Cmd+Shift+P` → `Tasks: Run Task`
2. Wybierz **AI Outreach: Draft CPO PL** lub **AI Outreach: Draft CSV Import PL**

## Tryb draft

- Wczytuje dane z `data/input_accounts.csv`.
- Wczytuje pliki kontekstowe z `context/` (`00_master_context.md` – `06_sequences_and_apollo.md`).
- Dla każdego kontaktu uruchamia pipeline: scoring → research → persona → hipoteza → wiadomość → QA → Apollo fields → routing.
- Agenty **Hypothesis**, **Message Writer** i **QA Reviewer** mogą korzystać z OpenAI LLM (jeśli `.env` jest skonfigurowany).
- Jeśli LLM jest niedostępny → automatyczny **fallback na heurystyki**.
- Zapisuje wyniki do `outputs/runs/YYYY-MM-DD_HH-MM-SS_campaign_name/`.
- **Nie** wysyła maili, **nie** łączy się z Apollo API.

## Pliki wejściowe

| Plik | Opis |
|---|---|
| `configs/cpo_pl_test.yaml` | Konfiguracja kampanii (persona, język, progi jakości, routing) |
| `data/input_accounts.csv` | Dane kontaktów (5 fikcyjnych rekordów testowych) |
| `context/00_master_context.md` – `context/06_*.md` | Pliki kontekstowe systemu (pozycjonowanie, persony, zasady) |
| `prompts/shared/*.md` | Prompty agentów (system prompts dla LLM) |
| `.env` | Konfiguracja LLM (klucz API, model) — nie commitować! |

## Outputy

Każdy run tworzy folder w `outputs/runs/` z plikami:

| Plik | Opis |
|---|---|
| `generated_messages.json` | Wygenerowane wiadomości (email_1) |
| `outreach_pack.json` | Pełny 3-mailowy pack per kontakt (email_1 + follow_up_1 + follow_up_2) |
| `qa_results.json` | Wyniki oceny jakości |
| `apollo_payloads.json` | Payloady gotowe pod Apollo custom fields |
| `approved.csv` | Kontakty zatwierdzone do wysyłki |
| `rejected.csv` | Kontakty odrzucone |
| `manual_review.csv` | Kontakty wymagające ręcznego przeglądu |
| `run_report.md` | Raport kampanii |

## Outreach Pack — 3-mailowy format thread

Każda kampania generuje `outreach_pack.json` z trzema mailami per kontakt:

| Email | Opis | Subject |
|---|---|---|
| `email_1` | Główny email outreachowy | Oryginalny subject |
| `follow_up_1` | Follow-up po 2 dniach | `RE: {subject}` |
| `follow_up_2` | Ostatni follow-up po 5 dniach | `RE: {subject}` |

Każdy email zawiera:
- `body_core` — czysta treść (bez podpisu, bez historii)
- `body` — pełny plain text (treść + podpis + separator Outlook + historia wątku)
- `body_html` — pełny HTML (Aptos 11pt, podpis z linkami, separator `<hr>`, historia)

Follow-upy używają **thread simulation** — każdy mail cytuje pełną historię poprzednich wiadomości z Outlook-style separatorem (`W dniu DD.MM.RRRR Tomasz Uściński napisał:`).

### Generowanie follow-upów

Follow-upy generowane przez `src/core/followup_generator.py`:
1. Próba LLM z promptem `prompts/shared/follow_up_writer.md`
2. Heurystyczny fallback z szablonami per gender/persona

### Wspólne moduły email

| Moduł | Odpowiedzialność |
|---|---|
| `src/core/email_signature.py` | Podpis (PLAIN + HTML), formatowanie body, strip signature |
| `src/core/email_thread_formatter.py` | Separator Outlook, budowanie thread chain, outreach pack |
| `src/core/followup_generator.py` | LLM + heurystyczny fallback follow-upów |

## LLM — jak to działa

3 agenty korzystają z LLM (OpenAI) z heurystycznym fallbackiem:

| Agent | LLM → generuje | Fallback → szablon |
|---|---|---|
| Hypothesis | Hipotezę biznesową z kontekstu | Generyczny szablon per persona |
| Message Writer | Pełny email z promptu | Szablon z openerem + hipotezą |
| QA Reviewer | Ocenę jakości i rekomendację | Heurystyczny scoring |

W outputach (`generated_messages.json`, `qa_results.json`) i w `run_report.md` widoczne flagi:
- `"llm_used": true/false` — czy użyto LLM
- `"fallback_used": true/false` — czy użyto heurystyki

## Czego system jeszcze NIE robi

- **Nie** integruje się z Apollo API — payloady są lokalne.
- **Nie** wysyła maili automatycznie (wysyłka testowa: `src/send_followup_test.py`).
- **Nie** robi enrichmentu danych (email, phone, company data).
- **Nie** obsługuje trybu `prepare` ani `launch`.
- **Nie** analizuje odpowiedzi.
- **Nie** integruje się z CRM.

## Typ kampanii: csv_import

Kampania `csv_import` umożliwia import kontaktów z pliku CSV z dowolnym układem kolumn.

### Przepływ

```
CSV → csv_normalizer → lead_scoring → persona_selection → hypothesis (weak trigger inference) → message_writer → qa_reviewer → apollo_fields → sequence_router → outputs
```

### Normalizacja CSV (csv_normalizer)

Przed przekazaniem danych do agentów LLM, każdy rekord CSV jest normalizowany deterministycznie:

| Kolumna CSV | Pole wewnętrzne |
|---|---|
| `Name` | `full_name` → rozdzielone na `first_name` + `last_name` |
| `Company` | `company_name` |
| `Domain` | `company_domain` |
| `Country` | `country` |
| `Industry` | `industry` |
| `Job role` | `job_title` |
| `Notes` | `notes` |

### Rozdzielanie Name

- Pierwsza część = imię (`first_name`)
- Reszta = nazwisko (`last_name`)
- Jeśli nie da się bezpiecznie rozdzielić, oba pola = null + warning

### Płeć i wołacz — wspólne źródło prawdy (wszystkie kampanie)

**Źródło**: `context/Vocative names od VSC.csv` (~25 000 imion)
**Helper**: `src/core/polish_names.py` — wspólny moduł dla article_triggered, csv_import i przyszłych kampanii.

Logika:
1. Imię kontaktu → lookup w pliku CSV (case-insensitive)
2. Jeśli znalezione → `gender` + `first_name_vocative` z CSV
3. Jeśli brak dopasowania → `gender = "unknown"`, `first_name_vocative = null`, powitanie `Dzień dobry,`

Żadne heurystyki (końcówka `-a`) ani zgadywanie przez LLM nie są używane jako primary source.

### Formy grzecznościowe w wiadomościach

| Gender | Powitanie | Formy w treści |
|---|---|---|
| female | Dzień dobry Pani {vocative}, | dla Pani, czy byłaby Pani otwarta, czy widzi Pani sens |
| male | Dzień dobry Panie {vocative}, | dla Pana, czy byłby Pan otwarty, czy widzi Pan sens |
| unknown | Dzień dobry, | formy neutralne, bez Pan/Pani |

Wszystkie formy grzecznościowe (Pan, Pani, Pana, Panią, Panu, Państwa) pisane wielką literą.

### Outputy csv_import

Każdy run tworzy folder w `outputs/runs/` z plikami:

| Plik | Opis |
|---|---|
| `normalized_contacts.json` | Kontakty po normalizacji (gender, vocative, mapowanie) |
| `generated_messages.json` | Wygenerowane wiadomości (email_1) |
| `outreach_pack.json` | Pełny 3-mailowy pack per kontakt |
| `qa_results.json` | Wyniki oceny jakości |
| `apollo_payloads.json` | Payloady gotowe pod Apollo custom fields |
| `approved.csv` | Kontakty zatwierdzone do wysyłki |
| `rejected.csv` | Kontakty odrzucone |
| `manual_review.csv` | Kontakty wymagające ręcznego przeglądu |
| `run_report.md` | Raport kampanii |

## Kolejne kroki

1. ~~**LLM API**~~ ✅ Podłączone (Hypothesis, Message Writer, QA) z fallbackiem.
2. **Apollo Search / Enrichment** — wyszukiwanie firm i osób przez API, weryfikacja emaili.
3. **Prepare mode** — zapis kontaktów i custom fields do Apollo bez dodawania do sekwencji.
4. **Launch mode** — automatyczne dodawanie do sekwencji Apollo.
5. ~~**Follow-up generation**~~ ✅ 3-mailowy outreach pack (email_1 + follow_up_1 + follow_up_2) z thread simulation.
6. **Response classification** — klasyfikacja odpowiedzi i dalsze kroki.
7. **CRM integration** — automatyczne notatki w Pipedrive.
8. **Feedback loop** — analiza wyników kampanii i optymalizacja.

## Struktura projektu

```
├── source_of_truth/                   # Wspólne Source of Truth dla wszystkich kampanii
│   ├── icp.yaml                       # Ideal Customer Profile (role decyzyjne)
│   ├── target_industries.yaml         # Branże docelowe
│   ├── messaging_framework.yaml       # Framework komunikacji (4 filary)
│   ├── spendguru_positioning.yaml     # Pozycjonowanie SpendGuru / Profitia
│   ├── qualification_rules.yaml       # Reguły kwalifikacji leadów
│   ├── rejection_rules.yaml           # Reguły odrzucania kontaktów
│   ├── email_style_guide.yaml         # Styl i ton komunikacji
│   ├── statuses.yaml                  # Statusy kontaktów i wiadomości
│   └── compliance_rules.yaml          # Reguły compliance
│
├── campaigns/                         # Wszystkie kampanie (izolowane)
│   ├── ad_hoc/                        # Kampanie jednorazowe (konferencje, LinkedIn)
│   │   └── linkedin_posts_retail_summit_2026/
│   ├── news/                          # Kampanie newsowe (artykuły, triggery rynkowe)
│   │   └── spendguru_market_news/
│   └── standard/                      # Kampanie prospectingowe (ICP, listy firm)
│       └── default_standard_campaign/
│
├── context/                           # Pliki kontekstowe (00-06 .md + materiały referencyjne)
├── configs/                           # Konfiguracje kampanii (YAML)
│   ├── csv_import/                    # Kampanie z importu CSV
│   ├── article_triggered/             # Kampanie triggered artykułami
│   ├── linkedin_posts/                # Kampanie z LinkedIn
│   └── experimental/                  # Kampanie eksperymentalne
├── data/                              # Dane wejściowe
│   ├── inputs/csv_import/             # CSV-e do importu
│   ├── reference/                     # Dane referencyjne (słownik imion, reguły)
│   └── test/                          # Dane testowe
├── outputs/runs/                      # Wyniki runów (archiwalne / zbiorcze)
├── prompts/                           # Prompty agentów
│   ├── base/                          # Prompty bazowe (wszystkie agenty)
│   ├── shared/                        # (legacy) Wspólne prompty
│   ├── csv_import/                    # (legacy) Prompty dedykowane csv_import
│   └── campaign_types/                # Prompty per typ kampanii
│       ├── ad_hoc/
│       ├── news/
│       └── standard/
├── src/
│   ├── run_campaign.py                # Oryginalny pipeline (article-triggered / generic)
│   ├── llm_client.py                  # Klient LLM (OpenAI) z fallbackiem
│   ├── send_followup_test.py          # Wysyłka testowych follow-upów (Office365)
│   ├── core/                          # Wspólne moduły
│   │   ├── polish_names.py            # Gender + vocative z CSV (25K imion)
│   │   ├── email_signature.py         # Podpis email (PLAIN + HTML)
│   │   ├── email_thread_formatter.py  # Thread builder (separator, outreach pack)
│   │   └── followup_generator.py      # Follow-up generator (LLM + heuristic)
│   ├── agents/csv_import/             # Agenty dedykowane csv_import (csv_normalizer)
│   └── pipelines/                     # Pipeline'y kampanii
│       └── run_csv_campaign.py        # Pipeline CSV Import
├── Integracje/                        # Integracje z Apollo, Pipedrive
├── Integracja z Office365/            # Wysyłka maili (Graph API)
├── .vscode/tasks.json                 # VS Code tasks
├── .env.example                       # Szablon konfiguracji LLM
├── requirements.txt                   # Zależności Python
└── README.md
```

