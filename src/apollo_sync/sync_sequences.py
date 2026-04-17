"""
sync_sequences.py — synchronizacja sekwencji z Apollo do PostgreSQL (apollo.sequences).

Pobiera sekwencje z Apollo API (POST /emailer_campaigns/search),
zapisuje/aktualizuje je w tabeli apollo.sequences (UPSERT po apollo_sequence_id).
"""

import logging
import os
import re
import sys

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

APOLLO_API_URL = "https://api.apollo.io/api/v1/emailer_campaigns/search"
PER_PAGE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        log.error("Brak wymaganej zmiennej środowiskowej: %s", name)
        sys.exit(1)
    return value


def _parse_sequence_name(name: str) -> dict:
    """Próbuje wyciągnąć campaign_slug, campaign_type, persona, industry z nazwy sekwencji.

    Konwencja nazewnictwa (przykład):
        „standard_retail_cpo_pl" -> campaign_type=standard, industry=retail, persona=cpo
    Jeśli nazwa nie pasuje - zwraca NULL-e.
    """
    result = {
        "campaign_slug": None,
        "campaign_type": None,
        "persona": None,
        "industry": None,
    }
    if not name:
        return result

    slug = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    result["campaign_slug"] = slug

    known_types = ("standard", "csv_import", "article_triggered", "ad_hoc", "linkedin_posts")
    for t in known_types:
        if t in slug:
            result["campaign_type"] = t
            break

    known_personas = ("cpo", "cfo", "ceo", "gm", "commercial_director", "procurement", "category_manager")
    for p in known_personas:
        if p in slug:
            result["persona"] = p
            break

    known_industries = ("retail", "fmcg", "manufacturing", "logistics", "pharma", "automotive")
    for ind in known_industries:
        if ind in slug:
            result["industry"] = ind
            break

    return result


# ---------------------------------------------------------------------------
# Apollo API
# ---------------------------------------------------------------------------

def fetch_sequences(api_key: str) -> list[dict]:
    """Pobiera wszystkie sekwencje z Apollo API (z paginacją)."""
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }

    all_sequences: list[dict] = []
    page = 1

    while True:
        log.info("Pobieram stronę %d sekwencji z Apollo API...", page)
        try:
            resp = requests.post(
                APOLLO_API_URL,
                json={"per_page": PER_PAGE, "page": page},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            log.error("Błąd HTTP z Apollo API: %s", exc.response.status_code)
            raise
        except requests.RequestException as exc:
            log.error("Błąd połączenia z Apollo API: %s", exc)
            raise

        data = resp.json()
        campaigns = data.get("emailer_campaigns", [])

        if not campaigns:
            if page == 1:
                log.warning("Apollo API zwróciło pustą listę sekwencji.")
            break

        all_sequences.extend(campaigns)

        pagination = data.get("pagination", {})
        total_pages = pagination.get("total_pages", 1)
        log.info(
            "Strona %d/%d - pobrano %d sekwencji (łącznie: %d)",
            page, total_pages, len(campaigns), len(all_sequences),
        )

        if page >= total_pages:
            break
        page += 1

    return all_sequences


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

UPSERT_SQL = text("""
    INSERT INTO apollo.sequences (
        apollo_sequence_id,
        sequence_name,
        campaign_slug,
        campaign_type,
        persona,
        industry,
        owner_email,
        status,
        created_at,
        updated_at,
        inserted_at
    ) VALUES (
        :apollo_sequence_id,
        :sequence_name,
        :campaign_slug,
        :campaign_type,
        :persona,
        :industry,
        :owner_email,
        :status,
        :created_at,
        :updated_at,
        now()
    )
    ON CONFLICT (apollo_sequence_id) DO UPDATE SET
        sequence_name  = EXCLUDED.sequence_name,
        campaign_slug  = EXCLUDED.campaign_slug,
        campaign_type  = EXCLUDED.campaign_type,
        persona        = EXCLUDED.persona,
        industry       = EXCLUDED.industry,
        owner_email    = EXCLUDED.owner_email,
        status         = EXCLUDED.status,
        created_at     = EXCLUDED.created_at,
        updated_at     = EXCLUDED.updated_at
""")


def _map_sequence(raw: dict) -> dict:
    """Mapuje surowy obiekt z Apollo API na wiersz tabeli."""
    parsed = _parse_sequence_name(raw.get("name", ""))

    active = raw.get("active")
    archived = raw.get("archived", False)
    if archived:
        status = "archived"
    elif active is True:
        status = "active"
    elif active is False:
        status = "inactive"
    else:
        status = "unknown"

    return {
        "apollo_sequence_id": raw["id"],
        "sequence_name": raw.get("name", ""),
        "campaign_slug": parsed["campaign_slug"],
        "campaign_type": parsed["campaign_type"],
        "persona": parsed["persona"],
        "industry": parsed["industry"],
        "owner_email": None,  # brak w odpowiedzi API - do uzupełnienia przez join z users
        "status": status,
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("last_used_at"),
    }


def upsert_sequences(engine, sequences: list[dict]) -> int:
    """Zapisuje sekwencje do apollo.sequences (UPSERT). Zwraca liczbę zapisanych wierszy."""
    rows = [_map_sequence(s) for s in sequences]
    with engine.begin() as conn:
        for row in rows:
            conn.execute(UPSERT_SQL, row)
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = _require_env("APOLLO_API_KEY")
    db_url = _require_env("DATABASE_URL")

    engine = create_engine(db_url, pool_pre_ping=True)

    log.info("Start synchronizacji sekwencji Apollo -> PostgreSQL")

    sequences = fetch_sequences(api_key)
    log.info("Pobrano %d sekwencji z Apollo API.", len(sequences))

    if not sequences:
        log.info("Brak sekwencji do zapisania. Koniec.")
        return

    count = upsert_sequences(engine, sequences)
    log.info("Zapisano/zaktualizowano %d sekwencji w apollo.sequences.", count)
    log.info("Synchronizacja zakończona.")


if __name__ == "__main__":
    main()
