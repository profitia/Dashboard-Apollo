#!/usr/bin/env bash
# =============================================================================
# scripts/backup.sh — Backup workspace Kampanie Apollo
#
# Tworzy ZIP backupu, changelog, aktualizuje manifest i opcjonalnie pushuje
# bezpieczne pliki do GitHub.
#
# Użycie:
#   ./scripts/backup.sh              # Tylko backup (ZIP + changelog)
#   ./scripts/backup.sh --push       # Backup + git commit & push safe files
#   ./scripts/backup.sh --push-only  # Tylko git commit & push (bez ZIP)
#
# Backup zapisywany do: ~/Backups/VSC/backup-VSC/
# =============================================================================

set -euo pipefail

# ---- KONFIGURACJA ----
WORKSPACE_NAME="Kampanie Apollo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_BASE_DIR="${HOME}/Backups/VSC/backup-VSC"
STATE_DIR="${PROJECT_DIR}/.backup_state"
DATE_TODAY=$(date +%Y.%m.%d)
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# ---- KOLORY ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---- PARSOWANIE ARGUMENTÓW ----
DO_PUSH=false
PUSH_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --push)      DO_PUSH=true ;;
        --push-only) PUSH_ONLY=true; DO_PUSH=true ;;
        --help|-h)
            echo "Użycie: $0 [--push] [--push-only]"
            echo "  (brak flag)  — tylko backup ZIP + changelog"
            echo "  --push       — backup + git commit & push safe files"
            echo "  --push-only  — tylko git commit & push (bez tworzenia ZIP)"
            exit 0
            ;;
        *)
            log_error "Nieznany argument: $arg"
            exit 1
            ;;
    esac
done

# ---- PRZYGOTOWANIE KATALOGÓW ----
mkdir -p "${BACKUP_BASE_DIR}"
mkdir -p "${STATE_DIR}"

# ---- USTALENIE NUMERU WERSJI ----
get_next_version() {
    local version=1
    while [[ -f "${BACKUP_BASE_DIR}/${DATE_TODAY}_${version}.zip" ]]; do
        ((version++))
    done
    echo "${version}"
}

VERSION=$(get_next_version)
BACKUP_FILENAME="${DATE_TODAY}_${VERSION}"
ZIP_PATH="${BACKUP_BASE_DIR}/${BACKUP_FILENAME}.zip"
CHANGELOG_PATH="${BACKUP_BASE_DIR}/${BACKUP_FILENAME}_CHANGELOG.txt"

log_info "Workspace: ${WORKSPACE_NAME}"
log_info "Data: ${DATE_TODAY}, wersja: ${VERSION}"
log_info "Backup: ${ZIP_PATH}"

# ---- GIT INFO ----
cd "${PROJECT_DIR}"

GIT_BRANCH="(brak repozytorium)"
GIT_LAST_COMMIT="(brak commitów)"
GIT_STATUS="(brak repozytorium)"
GIT_LOG_SINCE_LAST=""

if git rev-parse --is-inside-work-tree &>/dev/null; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "(detached)")
    GIT_LAST_COMMIT=$(git log -1 --format="%H %s" 2>/dev/null || echo "(brak commitów)")
    GIT_STATUS=$(git status --short 2>/dev/null || echo "(brak)")

    # Commity od ostatniego backupu
    if [[ -f "${STATE_DIR}/last_git_commit.txt" ]]; then
        LAST_COMMIT=$(cat "${STATE_DIR}/last_git_commit.txt")
        if git cat-file -t "${LAST_COMMIT}" &>/dev/null; then
            GIT_LOG_SINCE_LAST=$(git log --oneline "${LAST_COMMIT}..HEAD" 2>/dev/null || echo "(brak nowych commitów)")
        else
            GIT_LOG_SINCE_LAST="(nie można ustalić - poprzedni commit nie istnieje)"
        fi
    else
        GIT_LOG_SINCE_LAST="(pierwszy backup - brak punktu odniesienia)"
    fi
fi

# ---- DRZEWO KATALOGÓW ----
generate_tree() {
    if command -v tree &>/dev/null; then
        tree -a -I '.git|node_modules|.venv|venv|__pycache__|dist|build|.backup_state|.DS_Store' \
             --charset utf-8 "${PROJECT_DIR}" 2>/dev/null | head -500 || true
    else
        find "${PROJECT_DIR}" \
            -not -path '*/.git/*' \
            -not -path '*/.git' \
            -not -path '*/node_modules/*' \
            -not -path '*/.venv/*' \
            -not -path '*/venv/*' \
            -not -path '*/__pycache__/*' \
            -not -path '*/dist/*' \
            -not -path '*/build/*' \
            -not -path '*/.backup_state/*' \
            -not -name '.DS_Store' \
            | sort | head -500 || true
    fi
}

# ---- PORÓWNANIE Z POPRZEDNIM MANIFESTEM ----
CURRENT_MANIFEST=$(mktemp)
find "${PROJECT_DIR}" \
    -not -path '*/.git/*' \
    -not -path '*/.git' \
    -not -path '*/.venv/*' \
    -not -path '*/venv/*' \
    -not -path '*/node_modules/*' \
    -not -path '*/__pycache__/*' \
    -not -path '*/.backup_state/*' \
    -not -path '*/dist/*' \
    -not -path '*/build/*' \
    -not -name '.DS_Store' \
    -type f \
    | sort > "${CURRENT_MANIFEST}"

DIFF_ADDED=""
DIFF_REMOVED=""
DIFF_SECTION=""

if [[ -f "${STATE_DIR}/last_manifest.txt" ]]; then
    DIFF_ADDED=$(comm -13 "${STATE_DIR}/last_manifest.txt" "${CURRENT_MANIFEST}" 2>/dev/null || true)
    DIFF_REMOVED=$(comm -23 "${STATE_DIR}/last_manifest.txt" "${CURRENT_MANIFEST}" 2>/dev/null || true)

    DIFF_SECTION="=== ZMIANY WZGLĘDEM POPRZEDNIEGO BACKUPU ===

--- Dodane pliki ---
${DIFF_ADDED:-"(brak)"}

--- Usunięte pliki ---
${DIFF_REMOVED:-"(brak)"}

--- Zmodyfikowane pliki (na podstawie git) ---
$(git diff --name-only 2>/dev/null || echo "(nie można ustalić - brak git diff)")
"
else
    DIFF_SECTION="=== ZMIANY WZGLĘDEM POPRZEDNIEGO BACKUPU ===
(Pierwszy backup - brak punktu odniesienia)
"
fi

# ---- SEKRETY — SZYFROWANIE ----
SECRETS_STATUS="NIE wykonano backupu sekretów (brak skonfigurowanego szyfrowania GPG)."
SECRETS_NOTE="Aby zaszyfrować sekrety, zainstaluj GPG i uruchom:
  gpg --symmetric --cipher-algo AES256 -o secrets_${DATE_TODAY}_${VERSION}.gpg <plik>

Pliki .env NIE zostały dołączone do ZIP-a."

# Próba szyfrowania, jeśli gpg jest dostępne
SECRETS_ENCRYPTED=false
if command -v gpg &>/dev/null; then
    SECRETS_TEMP=$(mktemp)
    SECRETS_FOUND=false

    for env_file in "${PROJECT_DIR}/.env" \
                    "${PROJECT_DIR}/Integracja z Office365/.env" \
                    "${PROJECT_DIR}/Integracje/.env"; do
        if [[ -f "${env_file}" ]]; then
            echo "=== ${env_file#${PROJECT_DIR}/} ===" >> "${SECRETS_TEMP}"
            cat "${env_file}" >> "${SECRETS_TEMP}"
            echo "" >> "${SECRETS_TEMP}"
            SECRETS_FOUND=true
        fi
    done

    if [[ "${SECRETS_FOUND}" == true ]]; then
        SECRETS_ENC_PATH="${BACKUP_BASE_DIR}/secrets_${DATE_TODAY}_${VERSION}.gpg"
        log_info "GPG dostępny. Szyfruję sekrety..."
        echo ""
        log_warn "Podaj hasło do zaszyfrowania sekretów (lub Ctrl+C aby pominąć):"
        if gpg --batch --yes --symmetric --cipher-algo AES256 \
               -o "${SECRETS_ENC_PATH}" "${SECRETS_TEMP}" 2>/dev/null; then
            SECRETS_STATUS="Backup sekretów WYKONANY i ZASZYFROWANY: secrets_${DATE_TODAY}_${VERSION}.gpg"
            SECRETS_ENCRYPTED=true
            log_ok "Sekrety zaszyfrowane: ${SECRETS_ENC_PATH}"
        else
            SECRETS_STATUS="Szyfrowanie sekretów NIEUDANE (GPG error lub pominięte). Sekrety NIE zostały dołączone."
            log_warn "Szyfrowanie sekretów pominięte."
        fi
        rm -f "${SECRETS_TEMP}"
    fi
else
    log_warn "GPG niedostępne. Sekrety nie zostaną zaszyfrowane."
    log_warn "Zainstaluj GPG: brew install gnupg"
fi

# ---- TWORZENIE ZIP-a (chyba że --push-only) ----
if [[ "${PUSH_ONLY}" == false ]]; then
    log_info "Tworzę ZIP backupu..."

    cd "${PROJECT_DIR}"
    zip -r "${ZIP_PATH}" . \
        -x ".git/*" \
        -x ".venv/*" \
        -x "venv/*" \
        -x "node_modules/*" \
        -x "__pycache__/*" \
        -x "dist/*" \
        -x "build/*" \
        -x ".backup_state/*" \
        -x ".DS_Store" \
        -x "*.pyc" \
        -x ".env" \
        -x "*/.env" \
        -x ".env.*" \
        -x "*/.env.*" \
        -x "*.key" \
        -x "*.pem" \
        -x "*.p12" \
        -x "*.pfx" \
        -x ".token_cache.json" \
        -x "*/.token_cache.json" \
        -x "credentials.json" \
        -x "*/credentials.json" \
        -x "token*.json" \
        -x "*/token*.json" \
        -x "*secret*" \
        -x "*credential*" \
        -x "outputs/*" \
        > /dev/null 2>&1

    # Dodaj z powrotem pliki .env.example (wykluczone przez .env.*)
    find . -name ".env.example" -print0 2>/dev/null | while IFS= read -r -d '' f; do
        zip "${ZIP_PATH}" "${f}" > /dev/null 2>&1 || true
    done

    ZIP_SIZE=$(du -sh "${ZIP_PATH}" | cut -f1)
    log_ok "ZIP utworzony: ${ZIP_PATH} (${ZIP_SIZE})"

    # ---- GENEROWANIE CHANGELOG ----
    log_info "Generuję changelog..."

    TREE_OUTPUT=$(generate_tree)

    cat > "${CHANGELOG_PATH}" << CHANGELOG_EOF
===============================================================================
CHANGELOG — ${WORKSPACE_NAME}
===============================================================================

Data i godzina backupu:  ${TIMESTAMP}
Numer wersji (dziś):    ${DATE_TODAY}_${VERSION}
Workspace/projekt:       ${WORKSPACE_NAME}
Lokalizacja projektu:    ${PROJECT_DIR}

=== GIT ===
Branch:                  ${GIT_BRANCH}
Ostatni commit:          ${GIT_LAST_COMMIT}

--- Status Git (zmiany niecommitowane) ---
${GIT_STATUS:-"(brak zmian)"}

--- Commity od poprzedniego backupu ---
${GIT_LOG_SINCE_LAST:-"(brak)"}

=== DRZEWO KATALOGÓW ===
${TREE_OUTPUT}

${DIFF_SECTION}

=== SEKRETY ===
${SECRETS_STATUS}
${SECRETS_NOTE}

=== PLIK BACKUPU ===
ZIP:       ${ZIP_PATH}
Rozmiar:   ${ZIP_SIZE}
Changelog: ${CHANGELOG_PATH}

===============================================================================
Koniec CHANGELOG — ${BACKUP_FILENAME}
===============================================================================
CHANGELOG_EOF

    log_ok "Changelog zapisany: ${CHANGELOG_PATH}"

    # ---- AKTUALIZACJA MANIFESTU I STANU ----
    cp "${CURRENT_MANIFEST}" "${STATE_DIR}/last_manifest.txt"

    if git rev-parse HEAD &>/dev/null 2>&1; then
        git rev-parse HEAD > "${STATE_DIR}/last_git_commit.txt"
    fi

    log_ok "Manifest zaktualizowany: ${STATE_DIR}/last_manifest.txt"
fi

rm -f "${CURRENT_MANIFEST}"

# ---- GIT PUSH (opcjonalnie) ----
if [[ "${DO_PUSH}" == true ]]; then
    log_info "Przygotowuję commit i push bezpiecznych plików..."

    cd "${PROJECT_DIR}"

    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        log_error "To nie jest repozytorium Git. Uruchom najpierw: git init"
        exit 1
    fi

    # Sprawdź remote
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ -z "${REMOTE_URL}" ]]; then
        log_error "Brak remote 'origin'. Skonfiguruj: git remote add origin <URL>"
        exit 1
    fi

    # Dodaj TYLKO bezpieczne pliki (nie sekrety, nie ZIPy, nie outputy)
    git add \
        .gitignore \
        .env.example \
        "Integracja z Office365/.env.example" \
        "Integracje/.env.example" \
        README.md \
        README_BACKUP.md \
        requirements.txt \
        migration_report.md \
        scripts/ \
        src/ \
        configs/ \
        prompts/ \
        context/ \
        campaigns/ \
        data/ \
        source_of_truth/ \
        AdHoc/ \
        .vscode/tasks.json \
        2>/dev/null || true

    # Sprawdź, czy jest coś do commitowania
    if git diff --cached --quiet 2>/dev/null; then
        log_warn "Brak zmian do commitowania."
    else
        COMMIT_MSG="backup ${DATE_TODAY}_${VERSION}"
        git commit -m "${COMMIT_MSG}"
        log_ok "Commit: ${COMMIT_MSG}"

        if git push -u origin main 2>&1; then
            log_ok "Push do GitHub zakończony sukcesem."
        else
            log_error "Push nieudany. Sprawdź autoryzację i połączenie."
            exit 1
        fi
    fi

    # Aktualizuj last_git_commit po pushu
    if git rev-parse HEAD &>/dev/null 2>&1; then
        git rev-parse HEAD > "${STATE_DIR}/last_git_commit.txt"
    fi
fi

# ---- PODSUMOWANIE ----
echo ""
echo "============================================="
echo "  BACKUP ZAKOŃCZONY"
echo "============================================="
if [[ "${PUSH_ONLY}" == false ]]; then
    echo "  ZIP:       ${ZIP_PATH}"
    echo "  Changelog: ${CHANGELOG_PATH}"
fi
if [[ "${DO_PUSH}" == true ]]; then
    echo "  Git push:  TAK"
fi
if [[ "${SECRETS_ENCRYPTED}" == true ]]; then
    echo "  Sekrety:   ZASZYFROWANE (${SECRETS_ENC_PATH})"
else
    echo "  Sekrety:   NIE zaszyfrowano (brak GPG lub pominięte)"
fi
echo "============================================="
echo ""
