"""
Export Apollo analytics views to a static JSON file for the GitHub Pages dashboard.

Usage:
    python src/apollo_sync/export_dashboard_data.py

Output:
    docs/data/apollo_dashboard.json
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

VIEWS = {
    "sequence_performance": "apollo.v_sequence_performance",
    "message_status_summary": "apollo.v_message_status_summary",
    "reply_type_summary": "apollo.v_reply_type_summary",
    "sequence_status_summary": "apollo.v_sequence_status_summary",
}

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "docs" / "data" / "apollo_dashboard.json"


def _json_serializer(obj):
    """Handle Decimal, datetime, date for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _fetch_view(conn, view_name: str) -> list[dict]:
    """Fetch all rows from a view and return as list of dicts."""
    result = conn.execute(text(f"SELECT * FROM {view_name}"))  # noqa: S608 — view names are hardcoded constants
    columns = list(result.keys())
    rows = []
    for row in result:
        rows.append(dict(zip(columns, row)))
    return rows


def main():
    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        log.error("DATABASE_URL not set. Add it to .env and retry.")
        sys.exit(1)

    log.info("Starting Apollo dashboard data export...")

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
    except Exception as exc:
        log.error("Failed to create database engine: %s", exc)
        sys.exit(1)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with engine.connect() as conn:
            for key, view in VIEWS.items():
                try:
                    rows = _fetch_view(conn, view)
                    payload[key] = rows
                    log.info("  %-30s → %d records", view, len(rows))
                except Exception as exc:
                    log.error("Failed to query view %s: %s", view, exc)
                    payload[key] = []
    except Exception as exc:
        log.error("Database connection failed: %s", exc)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, default=_json_serializer, ensure_ascii=False, indent=2)
        log.info("Dashboard JSON written → %s", OUTPUT_PATH)
    except Exception as exc:
        log.error("Failed to write JSON file: %s", exc)
        sys.exit(1)

    log.info("Export complete.")


if __name__ == "__main__":
    main()
