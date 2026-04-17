# Migration Report — Kampanie Apollo

**Data migracji**: 2026-04-17
**Cel**: Przebudowa struktury katalogów projektu — izolacja kampanii, wspólne Source of Truth.

---

## 1. Co zostało utworzone

### source_of_truth/
| Plik | Opis |
|------|------|
| `icp.yaml` | Ideal Customer Profile — 17 ról decyzyjnych w 4 kategoriach |
| `target_industries.yaml` | 5 branż docelowych z keywords |
| `messaging_framework.yaml` | 4 filary komunikacji + logika wiadomości |
| `spendguru_positioning.yaml` | Zasady pozycjonowania SpendGuru / Profitia |
| `qualification_rules.yaml` | Reguły kwalifikacji, scoring, wagi jakości |
| `rejection_rules.yaml` | Reguły odrzucania (hard + soft reject) |
| `email_style_guide.yaml` | Styl, ton, typografia, CTA, personalizacja |
| `statuses.yaml` | Statusy kontaktów i wiadomości |
| `compliance_rules.yaml` | Reguły compliance, review, izolacja kampanii |

### campaigns/
| Ścieżka | Typ | Status |
|----------|-----|--------|
| `campaigns/ad_hoc/linkedin_posts_retail_summit_2026/` | ad_hoc | active |
| `campaigns/news/spendguru_market_news/` | news | draft |
| `campaigns/standard/default_standard_campaign/` | standard | draft |

Każda kampania zawiera: `input/`, `output/`, `review/`, `prompts/`, `logs/`, `campaign_config.yaml`.

### prompts/ (nowa struktura)
| Ścieżka | Zawartość |
|----------|-----------|
| `prompts/base/` | 9 bazowych promptów agentów (z prompts/shared/) |
| `prompts/campaign_types/ad_hoc/` | adhoc_email_writer.md |
| `prompts/campaign_types/news/` | (pusty, gotowy na przyszłe prompty) |
| `prompts/campaign_types/standard/` | csv_normalizer.md, csv_trigger_inference.md |

---

## 2. Co zostało przeniesione (skopiowane)

| Źródło | Cel |
|--------|-----|
| `AdHoc/configs/retail_summit_2026.yaml` | `campaigns/ad_hoc/.../configs/retail_summit_2026.yaml` |
| `AdHoc/data/posts_analysis.json` | `campaigns/ad_hoc/.../input/posts_analysis.json` |
| `AdHoc/prompts/adhoc_email_writer.md` | `campaigns/ad_hoc/.../prompts/adhoc_email_writer.md` |
| `AdHoc/src/*.py` (5 plików) | `campaigns/ad_hoc/.../src/` |
| `AdHoc/outputs/*` | `campaigns/ad_hoc/.../output/` |
| `prompts/shared/*.md` (9 plików) | `prompts/base/` |
| `prompts/csv_import/*.md` (2 pliki) | `prompts/campaign_types/standard/` |

**Uwaga**: Oryginalne pliki w `AdHoc/`, `prompts/shared/` i `prompts/csv_import/` NIE zostały usunięte. Plik `AdHoc/README_MIGRATED.md` informuje o migracji.

---

## 3. Jakie ścieżki zostały zaktualizowane

### campaigns/ad_hoc/.../src/run_adhoc_linkedin.py
- `_PROJECT_ROOT`: zmieniony z `os.path.dirname(_ADHOC_ROOT)` na `os.path.dirname(os.path.dirname(os.path.dirname(_ADHOC_ROOT)))` (3 poziomy wyżej zamiast 1)
- Docstring usage: `python AdHoc/src/...` → `python campaigns/ad_hoc/.../src/...`
- Output path: `_ADHOC_ROOT, "outputs"` → `_ADHOC_ROOT, "output"`

### campaigns/ad_hoc/.../src/generate_word_docs.py
- `_PROJECT_ROOT`: identyczna zmiana jak wyżej
- Output path: `_ADHOC_ROOT, "outputs"` → `_ADHOC_ROOT, "output"`

### campaigns/ad_hoc/.../src/generate_no_email_contacts.py
- `_PROJECT_ROOT`: identyczna zmiana jak wyżej
- Output path: `_ADHOC_ROOT, "outputs"` → `_ADHOC_ROOT, "output"`

### campaigns/ad_hoc/.../configs/retail_summit_2026.yaml
- `posts_analysis`: `AdHoc/data/posts_analysis.json` → `campaigns/ad_hoc/.../input/posts_analysis.json`

### README.md
- Sekcja "Struktura projektu" zaktualizowana o `source_of_truth/`, `campaigns/`, nową strukturę `prompts/`

---

## 4. Pliki wymagające ręcznego review

| Plik | Powód |
|------|-------|
| `AdHoc/` (cały folder) | Oryginalne pliki zostały skopiowane, nie przeniesione. Po weryfikacji migracji możesz usunąć stary folder. |
| `prompts/shared/` | Oryginalne prompty skopiowane do `prompts/base/`. Stary folder zachowany dla kompatybilności wstecznej. |
| `prompts/csv_import/` | Skopiowane do `prompts/campaign_types/standard/`. Stary folder zachowany. |
| `configs/article_triggered/` | Pusty folder — zdecyduj, czy przenieść do `campaigns/news/` czy usunąć. |
| `configs/linkedin_posts/` | Pusty folder — zdecyduj, czy przenieść do `campaigns/ad_hoc/` czy usunąć. |
| `configs/experimental/` | Pusty folder — zdecyduj, czy zachować czy usunąć. |
| `outputs/runs/` | Istniejące wyniki runów standardowych kampanii. Przyszłe runy powinny trafiać do `campaigns/{typ}/{nazwa}/output/`. |
| `src/run_campaign.py` | Główny pipeline nadal zapisuje wyniki do `outputs/runs/`. Może wymagać aktualizacji, aby używać `campaigns/standard/.../output/`. |
| `src/pipelines/run_csv_campaign.py` | Jak wyżej — output path może wymagać aktualizacji. |
| `.vscode/tasks.json` | Taski nadal odwołują się do standardowych ścieżek (src/run_campaign.py, configs/). To jest OK, ale warto rozważyć dodanie taskóow dla campaign-specific pipeline'ów. |

---

## 5. Konflikty nazw

**Brak konfliktów.** Wszystkie pliki zostały skopiowane do nowych lokalizacji bez nadpisywania.

---

## 6. Stare referencje do AdHoc/

| Lokalizacja | Referencja | Status |
|-------------|-----------|--------|
| `AdHoc/src/run_adhoc_linkedin.py` | Wiele referencji (docstring, _ADHOC_ROOT, _PROJECT_ROOT) | Zachowane w oryginalnym pliku (archiwum) |
| `AdHoc/src/generate_word_docs.py` | _ADHOC_ROOT, _PROJECT_ROOT | Zachowane w oryginalnym pliku (archiwum) |
| `AdHoc/src/generate_no_email_contacts.py` | _ADHOC_ROOT, _PROJECT_ROOT | Zachowane w oryginalnym pliku (archiwum) |
| `AdHoc/configs/retail_summit_2026.yaml` | `AdHoc/data/posts_analysis.json` | Zachowane w oryginalnym pliku (archiwum) |
| `campaigns/ad_hoc/.../src/run_adhoc_linkedin.py` | Zaktualizowane ścieżki | **OK** |
| `campaigns/ad_hoc/.../src/generate_word_docs.py` | Zaktualizowane ścieżki | **OK** |
| `campaigns/ad_hoc/.../src/generate_no_email_contacts.py` | Zaktualizowane ścieżki | **OK** |
| `campaigns/ad_hoc/.../configs/retail_summit_2026.yaml` | Zaktualizowana ścieżka | **OK** |

---

## 7. Rekomendacje następnych kroków

1. **Weryfikacja migracji**: Uruchom kampanię ad-hoc z nowej lokalizacji (`campaigns/ad_hoc/.../`) i sprawdź, czy ścieżki działają poprawnie.

2. **Usunięcie starych folderów**: Po weryfikacji usuń:
   - `AdHoc/` (oryginał — zachowany jako archiwum)
   - `prompts/shared/` (jeśli `prompts/base/` działa)
   - `prompts/csv_import/` (jeśli `prompts/campaign_types/standard/` działa)

3. **Aktualizacja pipeline'ów standardowych**: `src/run_campaign.py` i `src/pipelines/run_csv_campaign.py` nadal zapisują do `outputs/runs/`. Rozważ aktualizację, aby nowe runy trafiały do `campaigns/standard/.../output/`.

4. **Konfiguracja kampanii newsowych**: Folder `campaigns/news/spendguru_market_news/` jest gotowy — uzupełnij `campaign_config.yaml` i dodaj prompty, gdy będziesz gotowy.

5. **Integracja source_of_truth z pipeline'ami**: Dodaj logikę ładowania plików z `source_of_truth/` w agentach (lead scoring, persona selection, QA) zamiast hardkodowania reguł.

6. **Puste katalogi konfiguracyjne**: Zdecyduj, co zrobić z `configs/article_triggered/`, `configs/linkedin_posts/`, `configs/experimental/`.

7. **VS Code tasks**: Rozważ dodanie tasków dla pipeline'ów kampanijnych (np. `AI Outreach: Draft AdHoc Retail Summit`).
