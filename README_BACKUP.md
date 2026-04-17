# README_BACKUP.md — Odtworzenie środowiska Kampanie Apollo

## 1. Klonowanie repozytorium

```bash
git clone https://github.com/profitia/backup-VSC.git "Kampanie Apollo"
cd "Kampanie Apollo"
```

## 2. Odtworzenie środowiska Python

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## 3. Odtworzenie plików .env

Repozytorium zawiera pliki `.env.example` z nazwami wymaganych zmiennych (bez wartości).
Skopiuj je i uzupełnij swoimi kluczami:

```bash
cp .env.example .env
cp "Integracja z Office365/.env.example" "Integracja z Office365/.env"
cp "Integracje/.env.example" "Integracje/.env"
```

Wymagane zmienne:

| Plik | Zmienne |
|------|---------|
| `.env` | `LLM_PROVIDER`, `LLM_MODEL`, `GITHUB_TOKEN`, `OPENAI_API_KEY` |
| `Integracja z Office365/.env` | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SECRET_ID`, `AZURE_OBJECT_ID`, `AZURE_REDIRECT_URI`, `MAIL_FROM`, `MAIL_SCOPES` |
| `Integracje/.env` | `APOLLO_API_KEY`, `PIPEDRIVE_API_TOKEN`, `PIPEDRIVE_PIPELINE_ID`, `PIPEDRIVE_STAGE_ID` |

## 4. Odszyfrowywanie backupu sekretów (jeśli istnieje)

Jeśli masz plik `secrets_YYYY.MM.DD_N.gpg`:

```bash
gpg --decrypt secrets_2026.04.17_1.gpg > secrets_decrypted.txt
```

Następnie skopiuj zawartość do odpowiednich plików `.env`.

> **Uwaga:** Plik `.gpg` wymaga hasła podanego podczas szyfrowania.

## 5. Rozszerzenia VS Code

Zalecane rozszerzenia do pracy z tym projektem:

- **Python** (`ms-python.python`)
- **Pylance** (`ms-python.vscode-pylance`)
- **YAML** (`redhat.vscode-yaml`)
- **GitHub Copilot** (`GitHub.copilot`)
- **GitHub Copilot Chat** (`GitHub.copilot-chat`)

Instalacja z terminala:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension redhat.vscode-yaml
code --install-extension GitHub.copilot
code --install-extension GitHub.copilot-chat
```

## 6. Uruchamianie flows

### Kampania CPO PL (draft)
```bash
python src/run_campaign.py --config configs/cpo_pl_test.yaml --mode draft
```

### Kampania CSV Import PL (draft)
```bash
python src/pipelines/run_csv_campaign.py --config configs/csv_import/csv_import_pl_test.yaml --mode draft
```

Lub przez VS Code: **Terminal → Run Task → AI Outreach: Draft CPO PL** / **AI Outreach: Draft CSV Import PL**

## 7. Backup — uruchomienie ręczne z terminala

```bash
# Tylko backup (ZIP + changelog)
bash scripts/backup.sh

# Backup + git commit & push bezpiecznych plików
bash scripts/backup.sh --push

# Tylko git commit & push (bez tworzenia ZIP)
bash scripts/backup.sh --push-only
```

Backupy zapisywane do: `~/Backups/VSC/backup-VSC/`

## 8. Backup — uruchomienie z VS Code

**Terminal → Run Task**, a następnie:

| Task | Opis |
|------|------|
| **Backup workspace** | Tworzy ZIP + changelog |
| **Git push safe files** | Commit + push bezpiecznych plików do GitHub |
| **Backup workspace + Git push** | Backup ZIP + changelog + commit + push |

## 9. Odtwarzanie z ZIP-a

Jeśli odtwarzasz z ZIP-a (np. po formatowaniu dysku):

```bash
mkdir "Kampanie Apollo"
cd "Kampanie Apollo"
unzip ~/Backups/VSC/backup-VSC/2026.04.17_1.zip -d .
```

Potem wykonaj kroki 2-5 powyżej.

## 10. Struktura backupu

```
~/Backups/VSC/backup-VSC/
├── 2026.04.17_1.zip                  # ZIP backupu
├── 2026.04.17_1_CHANGELOG.txt        # Changelog
├── secrets_2026.04.17_1.gpg          # Zaszyfrowane sekrety (opcjonalnie)
├── 2026.04.17_2.zip                  # Kolejny backup tego dnia
├── 2026.04.17_2_CHANGELOG.txt
└── ...
```

## 11. Co jest commitowane do GitHub

- Kod źródłowy (src/, scripts/, configs/, prompts/, campaigns/, context/, data/, source_of_truth/, AdHoc/)
- Konfiguracje (.gitignore, .vscode/tasks.json, requirements.txt)
- Dokumentacja (README.md, README_BACKUP.md, migration_report.md)
- Pliki .env.example (szablony bez wartości)

## 12. Co NIE jest commitowane do GitHub

- `.env` (sekrety)
- `.venv/` (środowisko Python)
- `outputs/` (wygenerowane pliki)
- `.backup_state/` (metadane backupów)
- `*.zip` (archiwa backupów)
- `*.key`, `*.pem`, `*.p12` (certyfikaty)
- `*.enc`, `*.gpg` (zaszyfrowane pliki)
