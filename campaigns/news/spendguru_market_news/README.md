# SpendGuru Market News — News-Triggered Outreach Pipeline

Automatyczny pipeline outreachowy wyzwalany przez artykuły prasowe.  
Codziennie skanuje **wiadomoscihandlowe.pl** (i inne źródła), wyławia artykuły relewantne dla ICP,  
identyfikuje firmę-bohatera artykułu, znajduje kontakty w Apollo i generuje spersonalizowaną  
3-mailową sekwencję (D0 / D+2 / D+2) per tier ICP.

> **Tryb pracy: DRAFT-ONLY.**  
> Pipeline **nie enrolluje** kontaktów do sekwencji wysyłkowej automatycznie.  
> Po zapisaniu draftu wysyłane jest powiadomienie email na **tomasz.uscinski@profitia.pl**.  
> Enrollment wymaga ręcznego zatwierdzenia w Apollo.  
> Wymagana jest aktywna integracja z Office 365 (token cache w `Integracja z Office365/.token_cache.json`).  
> Apollo API: Master API key dla kampanii `spendguru_market_news`.

---

## Architektura — diagram przepływu

```
[sources.yaml]
     │
     ▼
 SCANNER          odkrywa URL artykułów z serwisów newsowych
     │
     ▼
 ARTICLE FETCHER  pobiera i parsuje HTML (respects paywall mode)
     │
     ▼
 RELEVANCE SCORER scoring 0-100 wg keywords.yaml
     │  (min_relevance_score: 40)
     ▼
 ENTITY EXTRACTOR wyodrębnia główną firmę (LLM + heurystyki)
     │
     ▼
 CONTACT FINDER   Apollo people search → mapowanie na tiery ICP
     │
     ▼
 MESSAGE GENERATOR LLM → 3-mailowy OutreachPack per kontakt per tier
     │
     ▼
 DRAFT BUILDER    znajdź/utwórz kontakt w Apollo (search → create run_dedupe=True)
     │            → dodaj do listy per tier (PL Tier N do market_news VSC)
     │            → ustaw stage: "News pipeline - drafted"
     │            → zapisz custom fields sg_market_news_email_step_N_*
     │            → NIE enrolluj do sekwencji (auto_enroll: false)
     │
     ▼
 APPROVAL EMAIL   wyślij powiadomienie na tomasz.uscinski@profitia.pl
     │            (Office365 Graph API)
     ▼
 STATE MANAGER    dedup (30 dni per firma) + log artykułów
     │
     ▼
 NOTIFIER         log / json_report
```

---

## Struktura plików

```
campaigns/news/spendguru_market_news/
├── config/
│   ├── campaign_config.yaml   ← konfiguracja operacyjna
│   ├── sources.yaml           ← serwisy do skanowania
│   ├── keywords.yaml          ← słowa kluczowe do scoringu
│   └── tier_mapping.yaml      ← mapowanie tytułów na tiery ICP
├── prompts/
│   └── message_writer.md      ← prompt LLM do generowania maili
└── README.md

src/news/
├── orchestrator.py            ← główny punkt wejścia / CLI
├── ingestion/
│   ├── scanner.py             ← skanowanie serwisów
│   └── article_fetcher.py     ← pobieranie i parsing artykułów
├── relevance/
│   └── scorer.py              ← scoring relewantności 0-100
├── entity/
│   └── entity_extractor.py   ← ekstrakcja firmy z artykułu
├── contacts/
│   └── contact_finder.py     ← szukanie kontaktów w Apollo
├── messaging/
│   └── message_generator.py  ← generowanie 3-mailowych OutreachPacków
├── apollo/
│   └── sequence_builder.py   ← tworzenie sekwencji Apollo
├── state/
│   └── state_manager.py      ← dedup + śledzenie stanu
└── notifications/
    └── notifier.py           ← powiadomienia (log/json/email/webhook)
```

---

## Szybki start

### 1. Instalacja zależności

```bash
pip install -r requirements.txt
# Dodatkowe zależności wymagane przez ten moduł:
pip install beautifulsoup4
```

### 2. Konfiguracja .env

Skopiuj `.env.example` do `Integracje/.env` (lub uzupełnij istniejący):

```bash
cp .env.example Integracje/.env
# Uzupełnij wszystkie wartości w Integracje/.env
```

### 3. Uruchomienie

```bash
# Pełny workflow dzienny (zalecane do CRON / zadania zaplanowanego)
python src/news/orchestrator.py run-daily

# Dry-run — nie zapisuje do Apollo
python src/news/orchestrator.py run-daily --dry-run

# Tylko skanowanie
python src/news/orchestrator.py scan

# Tylko scoring/kwalifikacja
python src/news/orchestrator.py qualify

# Kwalifikacja + sekwencja dla jednego artykułu
python src/news/orchestrator.py build-sequence \
  --single-article-url https://www.wiadomoscihandlowe.pl/artykul/xxx

# Verbose
python src/news/orchestrator.py run-daily --verbose
```

---

## Tryby CLI

| Tryb | Opis |
|---|---|
| `scan` | Skanuje serwisy, zapisuje URL-e kandydatów do `outputs/news/{campaign}/` |
| `qualify` | Pobiera artykuły, ocenia scoring, zwraca zakwalifikowane |
| `build-sequence` | Dla zakwalifikowanych: ekstrakcja firmy → kontakty → treści → Apollo |
| `run-daily` | scan + qualify + build-sequence (pełny workflow) |

### Flagi

| Flaga | Opis |
|---|---|
| `--dry-run` | Symulacja — nie zapisuje do Apollo |
| `--no-apollo-write` | Alias dla `--dry-run` |
| `--review-only` | Generuje treści, ale nie tworzy sekwencji |
| `--single-article-url URL` | Uruchom tylko dla jednego URL |
| `--campaign ID` | ID kampanii (domyślnie: `spendguru_market_news`) |
| `--verbose` | Debug logging |

---

## Konfiguracja

### `campaign_config.yaml`

Główny plik sterujący. Kluczowe parametry:

| Parametr | Domyślnie | Opis |
|---|---|---|
| `lookback_days` | 5 | Max. wiek artykułu (dni) |
| `min_relevance_score` | 40 | Min. wynik ogólny (0-100) |
| `min_industry_score` | 15 | Min. wynik branżowy |
| `min_purchase_signal_score` | 15 | Min. sygnał zakupowy |
| `dedup_window_days` | 30 | Cooldown na tę samą firmę (dni) |
| `human_review_gate` | false | Pauza przed tworzeniem sekwencji |
| `activate_automatically` | false | NIE włączaj sekwencji automatycznie |

### `sources.yaml`

Definiuje serwisy do skanowania. Każde źródło ma:

- `id` — unikalny identyfikator
- `scan_urls[]` — lista URL-i do skanowania (strona główna, tagi, kategorie)
- `article_list_selectors` — CSS selektory linków do artykułów
- `article_selectors` — CSS selektory treści artykułu
- `paywall.mode` — `partial_content` | `full_access` | `logged_in`

#### Dodawanie nowego źródła

1. Otwórz `config/sources.yaml`
2. Skopiuj blok z komentarzem `## TEMPLATE: Add new source here`
3. Wypełnij `id`, `base_url`, `scan_urls`, selektory i konfigurację paywalla
4. Ustaw `enabled: true`

### `keywords.yaml`

Słowa kluczowe do scoringu relewantności.  
Grupy: `industry_keywords`, `purchase_signals`, `amplifier_signals`, `procurement_vocabulary`.  
Każda grupa: `weight` + `terms[]`.

### `tier_mapping.yaml`

Mapowanie tytułów stanowisk na tiery ICP:
- **Tier 1** (C-Level): Prezes, Wiceprezes, CEO, CFO, COO, Dyrektor Generalny
- **Tier 2** (Procurement Management): Dyrektor Zakupów, Head of Procurement, Purchasing Manager
- **Tier 3** (Buyers Operational): Kupiec, Category Manager, Buyer

---

## Integracja Apollo

### Custom fields (merge tags w sekwencji)

Pipeline zapisuje treści maili do custom fields kontaktu w Apollo (prefix: `sg_market_news`):

| Custom field | Zawartość |
|---|---|
| `sg_market_news_email_step_1_subject` | Temat emaila 1 |
| `sg_market_news_email_step_1_body` | Treść emaila 1 (HTML, bez podpisu) |
| `sg_market_news_email_step_2_subject` | Temat emaila 2 |
| `sg_market_news_email_step_2_body` | Treść emaila 2 |
| `sg_market_news_email_step_3_subject` | Temat emaila 3 |
| `sg_market_news_email_step_3_body` | Treść emaila 3 |

**Limit**: max 4900 znaków per pole (limit Apollo: 5000).

### Listy Apollo

Kontakty są dodawane do list zależnie od tieru:

| Tier | Lista Apollo |
|---|---|
| Tier 1 (C-Level) | `PL Tier 1 do market_news VSC` |
| Tier 2 (Procurement Management) | `PL Tier 2 do market_news VSC` |
| Tier 3 (Buyers Operational) | `PL Tier 3 do market_news VSC` |

Listy muszą istnieć w Apollo przed pierwszym live runem.

### Stage kontaktu

Po zapisaniu draftu każdy kontakt otrzymuje stage: **`News pipeline - drafted`**  
Stage musi istnieć w Apollo (Contact Stages) przed pierwszym live runem.

Kolejne stage'e (ustawiane ręcznie):
- `News pipeline - approved` — po ręcznym zatwierdzeniu
- `News pipeline - enrolled` — po ręcznym enrollmencie do sekwencji

### Nazewnictwo draftu (sequence_name)

Format: `NEWS-YYYY-MM-DD-{company-slug}-{topic-slug}`  
Przykład: `NEWS-2026-04-21-biedronka-sa-inwestycja-w-magazyny`

Nazwa używana jako identyfikator draftu i w logach. Sekwencja wysyłkowa w Apollo  
**nie jest tworzona automatycznie** — należy ją stworzyć ręcznie po zatwierdzeniu.

---

## Workflow ręcznego zatwierdzenia

Po wygenerowaniu draftu:

1. **Email powiadomienie** trafia na `tomasz.uscinski@profitia.pl` z listą kontaktów
2. Weryfikacja treści maili w Apollo custom fields (`sg_market_news_email_step_*`)
3. Ręczne zatwierdzenie: zmiana stage na `News pipeline - approved`
4. Ręczne dodanie do sekwencji wysyłkowej w Apollo (Enrollment)
5. Aktywacja sekwencji w Apollo → **Activate sequence** → **Approve touch** per krok

---

## Stan i deduplicja

Stan przechowywany w `data/processed_articles.json` i `data/sequences_created.json`.

Logika dedup:
- Artykuł przetworzony (dowolny status poza `pending_review`) → pomijany
- Firma w cooldown (30 dni od ostatniej sekwencji) → pomijana
- Cooldown sprawdzany po `company_normalized` (lowercase, bez znaków specjalnych)

---

## Powiadomienia

Kanały konfigurowane w `config/campaign_config.yaml → notification_channels`:

| Kanał | Opis |
|---|---|
| `log` | Tylko logi konsoli |
| `json_report` | Zapis JSON do `outputs/news/{campaign}/` |

### Approval email (Office365)

Wysyłany automatycznie po zapisaniu każdego draftu.  
Adresat: `tomasz.uscinski@profitia.pl`  
Temat: `[spendguru_market_news] Draft czeka na zatwierdzenie - {firma}`

**Wymagania**:
- Aktywna integracja Office365 (`Integracja z Office365/.env` z `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`, `MAIL_FROM`)
- Ważny token cache w `Integracja z Office365/.token_cache.json`  
  (token generowany przy pierwszym uruchomieniu `send_mail.py` — device flow)
- Master API key Apollo skonfigurowany w `Integracje/.env`

---

## Zależności

```
requests
python-dotenv
pyyaml
openai
beautifulsoup4  ← wymagane przez article_fetcher.py
msal            ← wymagane do wysyłki approval email (Office365)
```

---

## Ograniczenia i otwarte decyzje

- **Paywall wiadomoscihandlowe.pl**: tryb `partial_content` — scoring na tytule + leadzie + widocznych fragmentach. Logowanie (`logged_in`) wymaga ustawienia `WH_USERNAME` / `WH_PASSWORD` w .env.
- **LLM**: entity extraction i message generation wymagają `GITHUB_TOKEN` lub `OPENAI_API_KEY`. Fallback heurystyczny dostępny dla entity extraction.
- **Apollo contact search**: zwraca kontakty z Apollo bazy — nie gwarantuje aktualności. Zweryfikuj e-maile przed wysyłką.
- **Cadence**: [D0, D+2, D+2] ustawione w `sequence_cadence` w `campaign_config.yaml`. Zmień wartości (minuty) według potrzeb.
- **Integracja Opoint**: rozważana jako alternatywne źródło artykułów — wymaga sprawdzenia API access.
