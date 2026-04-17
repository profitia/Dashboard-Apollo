"""
sync_messages.py — synchronizacja wiadomości outreach z Apollo do PostgreSQL (apollo.outreach_messages).

Pobiera wiadomości z Apollo API (GET /emailer_messages/search),
zapisuje/aktualizuje je w tabeli apollo.outreach_messages (UPSERT po apollo_message_id).

Nie filtruje po statusie sekwencji - pobiera wszystkie wiadomości.
Status sekwencji (active/inactive/archived) jest w apollo.sequences
i łączony przez JOIN po apollo_sequence_id.
"""

import json
import logging
import os
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

APOLLO_API_URL = "https://api.apollo.io/api/v1/emailer_messages/search"
PER_PAGE = 100
MAX_PAGES = 500  # limit Apollo API: 50 000 rekordów (100 * 500)

POSITIVE_REPLY_TYPES = frozenset({
    "willing_to_meet",
    "follow_up_question",
    "interested",
    "positive",
})

STATUS_BOOLEAN_MAP = {
    "delivered":    "is_delivered",
    "opened":       "is_opened",
    "not_opened":   "is_delivered",  # dostarczono, ale nie otworzono
    "clicked":      "is_clicked",
    "unsubscribed": "is_unsubscribed",
    "bounced":      "is_bounced",
    "spam_blocked": "is_spam_blocked",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        log.error("Brak wymaganej zmiennej środowiskowej: %s", name)
        sys.exit(1)
    return value


def is_positive_reply(reply_type: str | None) -> bool | None:
    """Zwraca True jeśli reply_type wskazuje pozytywną odpowiedź, False jeśli inny typ, None jeśli brak."""
    if reply_type is None:
        return None
    return reply_type.lower() in POSITIVE_REPLY_TYPES


def normalize_message_status(message: dict) -> str | None:
    """Wyciąga znormalizowany status wiadomości z obiektu Apollo.

    Priorytet: pole `status`, potem heurystyka z flag.
    """
    status = message.get("status")
    if status:
        return status.lower().strip()

    # Fallback: heurystyka z pól boolowskich
    if message.get("bounce"):
        return "bounced"
    if message.get("spam_blocked"):
        return "spam_blocked"
    if message.get("replied"):
        return "replied"
    if message.get("completed_at"):
        return "delivered"

    return None


def extract_message_fields(message: dict) -> dict:
    """Mapuje surowy obiekt wiadomości z Apollo API na dict kolumn tabeli apollo.outreach_messages.

    Obsługuje alternatywne nazwy pól, bezpiecznie przez .get().
    """
    status = normalize_message_status(message)

    reply_type = (
        message.get("reply_class")
        or message.get("reply_type")
    )

    # Boolean flags - najpierw z bezpośrednich pól Apollo, potem z heurystyki statusu
    bool_from_status = {}
    if status and status in STATUS_BOOLEAN_MAP:
        bool_from_status[STATUS_BOOLEAN_MAP[status]] = True

    is_replied_val = True if message.get("replied") else None
    if reply_type is not None:
        is_replied_val = True

    # sent_at: completed_at (faktyczna wysyłka) > due_at (zaplanowana) > created_at
    sent_at = (
        message.get("completed_at")
        or message.get("sent_at")
        or message.get("due_at")
    )

    # step_number: campaign_position (1-based step index w sekwencji)
    step_number = (
        message.get("campaign_position")
        or message.get("step_number")
        or message.get("step")
    )

    # mailbox_user: email_account_id (Apollo nie zwraca adresu email wprost w tym endpoincie)
    mailbox_user = (
        message.get("from_email")
        or message.get("user_email")
        or message.get("owner_email")
        or message.get("mailbox")
        or message.get("email_account_id")
    )

    return {
        "apollo_message_id": message["id"],
        "apollo_sequence_id": (
            message.get("emailer_campaign_id")
            or message.get("campaign_id")
            or message.get("sequence_id")
        ),
        "apollo_contact_id": (
            message.get("contact_id")
            or message.get("person_id")
        ),
        "mailbox_user": mailbox_user,
        "subject": message.get("subject"),
        "step_number": int(step_number) if step_number is not None else None,
        "sent_at": sent_at,
        "status": status,
        "reply_type": reply_type,
        "is_delivered": bool_from_status.get("is_delivered", None),
        "is_opened": bool_from_status.get("is_opened", None),
        "is_clicked": bool_from_status.get("is_clicked", None),
        "is_replied": is_replied_val,
        "is_positive_reply": is_positive_reply(reply_type),
        "is_unsubscribed": bool_from_status.get("is_unsubscribed", None),
        "is_bounced": True if message.get("bounce") else bool_from_status.get("is_bounced", None),
        "is_spam_blocked": True if message.get("spam_blocked") else bool_from_status.get("is_spam_blocked", None),
        "raw_payload": message,
    }


# ---------------------------------------------------------------------------
# Apollo API
# ---------------------------------------------------------------------------

def fetch_messages(api_key: str) -> list[dict]:
    """Pobiera wszystkie wiadomości outreach z Apollo API (z paginacją GET)."""
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }

    all_messages: list[dict] = []
    page = 1

    while page <= MAX_PAGES:
        log.info("Pobieram stronę %d wiadomości z Apollo API...", page)
        try:
            resp = requests.get(
                APOLLO_API_URL,
                params={"per_page": PER_PAGE, "page": page},
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

        try:
            data = resp.json()
        except ValueError:
            log.error("Nieoczekiwany format odpowiedzi z Apollo API (nie JSON).")
            raise

        if not isinstance(data, dict):
            log.error("Nieoczekiwany format odpowiedzi z Apollo API: oczekiwano obiektu JSON.")
            break

        messages = data.get("emailer_messages", [])

        if not messages:
            if page == 1:
                log.warning("Apollo API zwróciło pustą listę wiadomości.")
            break

        all_messages.extend(messages)

        pagination = data.get("pagination", {})
        total_entries = pagination.get("total_entries", "?")
        total_pages = pagination.get("total_pages", page)
        log.info(
            "Strona %d/%s - pobrano %d wiadomości (łącznie: %d / %s)",
            page, total_pages, len(messages), len(all_messages), total_entries,
        )

        if page >= total_pages:
            break
        page += 1

    return all_messages


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

UPSERT_SQL = text("""
    INSERT INTO apollo.outreach_messages (
        apollo_message_id,
        apollo_sequence_id,
        apollo_contact_id,
        mailbox_user,
        subject,
        step_number,
        sent_at,
        status,
        reply_type,
        is_delivered,
        is_opened,
        is_clicked,
        is_replied,
        is_positive_reply,
        is_unsubscribed,
        is_bounced,
        is_spam_blocked,
        raw_payload,
        inserted_at,
        updated_at
    ) VALUES (
        :apollo_message_id,
        :apollo_sequence_id,
        :apollo_contact_id,
        :mailbox_user,
        :subject,
        :step_number,
        :sent_at,
        :status,
        :reply_type,
        :is_delivered,
        :is_opened,
        :is_clicked,
        :is_replied,
        :is_positive_reply,
        :is_unsubscribed,
        :is_bounced,
        :is_spam_blocked,
        :raw_payload,
        now(),
        now()
    )
    ON CONFLICT (apollo_message_id) DO UPDATE SET
        apollo_sequence_id = EXCLUDED.apollo_sequence_id,
        apollo_contact_id  = EXCLUDED.apollo_contact_id,
        mailbox_user       = EXCLUDED.mailbox_user,
        subject            = EXCLUDED.subject,
        step_number        = EXCLUDED.step_number,
        sent_at            = EXCLUDED.sent_at,
        status             = EXCLUDED.status,
        reply_type         = EXCLUDED.reply_type,
        is_delivered       = EXCLUDED.is_delivered,
        is_opened          = EXCLUDED.is_opened,
        is_clicked         = EXCLUDED.is_clicked,
        is_replied         = EXCLUDED.is_replied,
        is_positive_reply  = EXCLUDED.is_positive_reply,
        is_unsubscribed    = EXCLUDED.is_unsubscribed,
        is_bounced         = EXCLUDED.is_bounced,
        is_spam_blocked    = EXCLUDED.is_spam_blocked,
        raw_payload        = EXCLUDED.raw_payload,
        updated_at         = now()
""")


def upsert_messages(engine, messages: list[dict]) -> int:
    """Zapisuje wiadomości do apollo.outreach_messages (UPSERT). Zwraca liczbę zapisanych wierszy."""
    rows = [extract_message_fields(m) for m in messages]
    count = 0
    with engine.begin() as conn:
        for row in rows:
            try:
                row_copy = dict(row)
                row_copy["raw_payload"] = json.dumps(row_copy["raw_payload"], default=str)
                conn.execute(UPSERT_SQL, row_copy)
                count += 1
            except Exception:
                log.exception(
                    "Błąd zapisu wiadomości apollo_message_id=%s",
                    row.get("apollo_message_id", "?"),
                )
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = _require_env("APOLLO_API_KEY")
    db_url = _require_env("DATABASE_URL")

    engine = create_engine(db_url, pool_pre_ping=True)

    log.info("Start synchronizacji wiadomości outreach Apollo -> PostgreSQL")

    messages = fetch_messages(api_key)
    log.info("Pobrano łącznie %d wiadomości z Apollo API.", len(messages))

    if not messages:
        log.info("Brak wiadomości do zapisania. Koniec.")
        return

    count = upsert_messages(engine, messages)
    log.info("Zapisano/zaktualizowano %d/%d wiadomości w apollo.outreach_messages.", count, len(messages))
    if count < len(messages):
        log.warning("Nie udało się zapisać %d wiadomości (szczegóły powyżej).", len(messages) - count)
    log.info("Synchronizacja zakończona.")


if __name__ == "__main__":
    main()
