#!/usr/bin/env python3
"""
Contact Engagement Tracker — Layer 1: Collect & Store.

Zbiera i utrwala per-contact historię outreachu + engagement.
Działa od razu jako recorder, nawet bez pełnego AI follow-up mode.

Odpowiada za:
- Zapis pełnej historii wysyłek (subjects, bodies, steps, timestamps)
- Pobieranie engagement z Apollo (opens, replies, status)
- Aktualizację engagement snapshots
- Trwałe przechowywanie w data/contact_engagement/

Storage: JSON per contact, klucz = email lub first_last_company.
"""

import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENGAGEMENT_DIR = os.path.join(_ROOT_DIR, "data", "contact_engagement")


def _ensure_dir():
    os.makedirs(_ENGAGEMENT_DIR, exist_ok=True)


def contact_key(contact: dict) -> str:
    """Generuje unikalny klucz kontaktu (email lub first+last+company)."""
    email = contact.get("email", "").strip().lower()
    if email:
        return email
    first = contact.get("first_name", contact.get("contact_first_name", "")).strip().lower()
    last = contact.get("last_name", contact.get("contact_last_name", "")).strip().lower()
    company = contact.get("company", contact.get("company_name", "")).strip().lower()
    return f"{first}_{last}_{company}"


def _safe_filename(key: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in key)


def _engagement_path(key: str) -> str:
    return os.path.join(_ENGAGEMENT_DIR, f"{_safe_filename(key)}.json")


# ============================================================
# Empty profile template
# ============================================================

def _empty_profile(key: str) -> dict:
    """Tworzy pusty profil engagement kontaktu."""
    return {
        "contact_key": key,
        "contact_email": "",
        "contact_name": "",
        "contact_title": "",
        "company_name": "",
        "apollo_contact_id": None,
        "current_status": "never_contacted",
        "rich_profile_ref": None,
        "outreach_history": [],
        "angle_history": [],
        "engagement_snapshot": {
            "total_opens": 0,
            "unique_opens": 0,
            "last_open_at": None,
            "total_replies": 0,
            "last_reply_at": None,
            "replied": False,
            "bounced": False,
            "unsubscribed": False,
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


# ============================================================
# Load / Save
# ============================================================

def load_engagement_profile(contact: dict) -> dict:
    """Wczytuje profil engagement kontaktu z dysku."""
    _ensure_dir()
    key = contact_key(contact)
    path = _engagement_path(key)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    profile = _empty_profile(key)
    # Wypełnij dane kontaktu
    profile["contact_email"] = contact.get("email", "").strip().lower()
    first = contact.get("first_name", contact.get("contact_first_name", ""))
    last = contact.get("last_name", contact.get("contact_last_name", ""))
    profile["contact_name"] = f"{first} {last}".strip()
    profile["contact_title"] = contact.get("title", contact.get("contact_title", contact.get("job_title", "")))
    profile["company_name"] = contact.get("company", contact.get("company_name", ""))

    # Rich profile reference — link to rich_contact_profile storage
    rich_profile = contact.get("rich_profile")
    if rich_profile:
        profile["rich_profile_ref"] = contact_key(contact)
        # Store extended contact metadata from rich profile
        org_ctx = rich_profile.get("org_context", {})
        urls = rich_profile.get("urls", {})
        loc = rich_profile.get("location", {})
        profile["contact_extended"] = {
            "industry": org_ctx.get("industry"),
            "keywords_raw": org_ctx.get("keywords_raw"),
            "seniority": rich_profile.get("core_identity", {}).get("seniority"),
            "person_linkedin_url": urls.get("person_linkedin_url"),
            "website": urls.get("website"),
            "company_linkedin_url": urls.get("company_linkedin_url"),
            "city": loc.get("city"),
            "country": loc.get("country"),
            "company_city": loc.get("company_city"),
            "company_country": loc.get("company_country"),
        }

    return profile


def save_engagement_profile(profile: dict):
    """Zapisuje profil engagement kontaktu na dysk."""
    _ensure_dir()
    profile["updated_at"] = datetime.now().isoformat()
    key = profile.get("contact_key", "unknown")
    path = _engagement_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    log.info("Engagement profile saved: %s", key)


def load_all_profiles() -> list[dict]:
    """Wczytuje wszystkie profile engagement z dysku."""
    _ensure_dir()
    profiles = []
    for fname in os.listdir(_ENGAGEMENT_DIR):
        if fname.endswith(".json"):
            path = os.path.join(_ENGAGEMENT_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                profiles.append(json.load(f))
    return profiles


# ============================================================
# Record outreach — zapis wysyłki do historii
# ============================================================

def record_outreach(
    contact: dict,
    campaign_name: str,
    campaign_type: str,
    outreach_pack: dict,
    apollo_sequence_name: str | None = None,
    apollo_sequence_id: str | None = None,
    mailbox_used: str | None = None,
    extra_metadata: dict | None = None,
    angle_data: dict | None = None,
) -> dict:
    """
    Zapisuje wysyłkę do historii engagement kontaktu.

    Rejestruje per-step: subject, body, step_id, timestamps.
    Chroni przed duplikatami (campaign_name + sent_at date).

    Args:
        contact: dane kontaktu
        campaign_name: nazwa kampanii
        campaign_type: typ kampanii (outbound, csv_import, etc.)
        outreach_pack: dict z email_1, follow_up_1, follow_up_2
        apollo_sequence_name: nazwa sekwencji Apollo
        apollo_sequence_id: ID sekwencji Apollo
        mailbox_used: skrzynka użyta do wysyłki
        extra_metadata: dodatkowe metadane (tier, segment, angle, etc.)

    Returns:
        Zaktualizowany profil engagement.
    """
    profile = load_engagement_profile(contact)
    now = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    # Sprawdź duplikat (ta sama kampania tego samego dnia)
    for entry in profile.get("outreach_history", []):
        if (entry.get("campaign_name") == campaign_name
                and entry.get("sent_date") == today):
            log.info("Duplikat outreach '%s' dla '%s' w dniu %s - pomijam",
                     campaign_name, profile["contact_key"], today)
            entry["last_seen_at"] = now
            save_engagement_profile(profile)
            return profile

    # Buduj listę steps z outreach_pack
    steps = []
    step_map = {
        "email_1": {"step_number": 1, "step_type": "initial"},
        "follow_up_1": {"step_number": 2, "step_type": "follow_up"},
        "follow_up_2": {"step_number": 3, "step_type": "follow_up"},
    }
    for pack_key, step_meta in step_map.items():
        step_data = outreach_pack.get(pack_key)
        if step_data:
            steps.append({
                "step_number": step_meta["step_number"],
                "step_type": step_meta["step_type"],
                "subject": step_data.get("subject", ""),
                "body": step_data.get("body", ""),
                "body_html": step_data.get("body_html", ""),
            })

    # Nowy wpis outreach
    outreach_entry = {
        "campaign_name": campaign_name,
        "campaign_type": campaign_type,
        "apollo_sequence_name": apollo_sequence_name,
        "apollo_sequence_id": apollo_sequence_id,
        "mailbox_used": mailbox_used,
        "sent_at": now,
        "sent_date": today,
        "steps": steps,
        "steps_count": len(steps),
    }
    if extra_metadata:
        outreach_entry["metadata"] = extra_metadata
    if angle_data:
        outreach_entry["angle_data"] = angle_data

    profile["outreach_history"].append(outreach_entry)

    # Aktualizuj angle_history
    if angle_data:
        if "angle_history" not in profile:
            profile["angle_history"] = []
        profile["angle_history"].append({
            "campaign_name": campaign_name,
            "sent_date": today,
            "primary_angle_id": angle_data.get("primary_angle_id", "general"),
            "primary_angle_label": angle_data.get("primary_angle_label", ""),
            "secondary_angle_ids": angle_data.get("secondary_angle_ids", []),
            "secondary_angle_labels": angle_data.get("secondary_angle_labels", []),
        })

    # Aktualizuj status
    if profile["current_status"] == "never_contacted":
        profile["current_status"] = "active_sequence"

    save_engagement_profile(profile)
    log.info("Outreach recorded: '%s' for '%s' (%d steps)",
             campaign_name, profile["contact_key"], len(steps))
    return profile


# ============================================================
# Update engagement from Apollo
# ============================================================

def update_engagement_from_apollo(
    contact: dict,
    apollo_data: dict,
) -> dict:
    """
    Aktualizuje engagement snapshot kontaktu danymi z Apollo.

    Args:
        contact: dane kontaktu
        apollo_data: dane z Apollo API (emailer_touches, contact details, etc.)

    Returns:
        Zaktualizowany profil engagement.
    """
    profile = load_engagement_profile(contact)
    now = datetime.now().isoformat()

    snapshot = profile.get("engagement_snapshot", {})

    # Otworzenia
    opens = apollo_data.get("opens", [])
    if opens:
        snapshot["total_opens"] = len(opens)
        snapshot["unique_opens"] = len(set(o.get("message_id", i) for i, o in enumerate(opens)))
        last_open = max(opens, key=lambda o: o.get("opened_at", ""), default=None)
        if last_open:
            snapshot["last_open_at"] = last_open.get("opened_at")

    # Odpowiedzi
    replies = apollo_data.get("replies", [])
    if replies:
        snapshot["total_replies"] = len(replies)
        snapshot["replied"] = True
        last_reply = max(replies, key=lambda r: r.get("replied_at", ""), default=None)
        if last_reply:
            snapshot["last_reply_at"] = last_reply.get("replied_at")

    # Flagi statusu z Apollo
    if apollo_data.get("bounced"):
        snapshot["bounced"] = True
    if apollo_data.get("unsubscribed"):
        snapshot["unsubscribed"] = True

    # Proste metryki z Apollo contact
    if "emailer_touches" in apollo_data:
        touches = apollo_data["emailer_touches"]
        if isinstance(touches, list):
            open_count = sum(1 for t in touches if t.get("opened_at"))
            reply_count = sum(1 for t in touches if t.get("replied_at"))
            if open_count > snapshot.get("total_opens", 0):
                snapshot["total_opens"] = open_count
                snapshot["unique_opens"] = open_count
            if reply_count > snapshot.get("total_replies", 0):
                snapshot["total_replies"] = reply_count
                snapshot["replied"] = reply_count > 0
            # Ostatnie otwarcie/odpowiedź
            opens_at = [t["opened_at"] for t in touches if t.get("opened_at")]
            if opens_at:
                snapshot["last_open_at"] = max(opens_at)
            replies_at = [t["replied_at"] for t in touches if t.get("replied_at")]
            if replies_at:
                snapshot["last_reply_at"] = max(replies_at)
                snapshot["replied"] = True

    # Apollo contact ID
    if apollo_data.get("contact_id"):
        profile["apollo_contact_id"] = apollo_data["contact_id"]

    # Sequence status z Apollo
    if "sequence_status" in apollo_data:
        seq_status = apollo_data["sequence_status"]
        # active / paused / finished / bounced
        if seq_status == "finished":
            profile["current_status"] = "completed_sequence"
        elif seq_status == "active":
            profile["current_status"] = "active_sequence"
        elif seq_status == "bounced":
            profile["current_status"] = "bounced"

    snapshot["last_checked_at"] = now
    profile["engagement_snapshot"] = snapshot

    # Ustal current_status na podstawie engagement
    _resolve_status(profile)

    save_engagement_profile(profile)
    log.info("Engagement updated from Apollo for '%s'", profile["contact_key"])
    return profile


def _resolve_status(profile: dict):
    """Ustala current_status na podstawie engagement snapshot."""
    snap = profile.get("engagement_snapshot", {})

    if snap.get("bounced"):
        profile["current_status"] = "bounced"
        return
    if snap.get("unsubscribed"):
        profile["current_status"] = "do_not_contact"
        return
    if snap.get("replied"):
        profile["current_status"] = "replied"
        return
    if snap.get("total_opens", 0) > 0 and not snap.get("replied"):
        profile["current_status"] = "opened_no_reply"
        return

    # Jeśli ma historię outreach ale brak engagement
    if profile.get("outreach_history"):
        last_outreach = profile["outreach_history"][-1]
        sent_at = last_outreach.get("sent_at", "")
        if sent_at:
            # Nie zmieniaj jeśli aktywna sekwencja
            if profile["current_status"] in ("active_sequence", "completed_sequence"):
                return
        profile["current_status"] = "completed_sequence"


# ============================================================
# Fetch engagement z Apollo API
# ============================================================

def fetch_apollo_engagement(contact: dict) -> dict | None:
    """
    Pobiera dane engagement z Apollo dla kontaktu.

    Szuka kontaktu w Apollo po email, pobiera:
    - emailer_touches (otwarcia, odpowiedzi per step)
    - emailer_campaigns (sekwencje, statusy)
    - contact status flags

    Returns:
        dict z danymi Apollo lub None jeśli niedostępny.
    """
    client = _get_apollo_client()
    if client is None:
        log.warning("Apollo client niedostępny - nie mogę pobrać engagement")
        return None

    email = contact.get("email", "").strip()
    if not email:
        log.warning("Brak emaila kontaktu - nie mogę pobrać engagement z Apollo")
        return None

    try:
        apollo_contact = client.search_contact(email)
        if not apollo_contact:
            log.info("Kontakt '%s' nie znaleziony w Apollo", email)
            return None

        contact_id = apollo_contact.get("id")
        result = {
            "contact_id": contact_id,
            "email": email,
            "fetched_at": datetime.now().isoformat(),
        }

        # Pobierz szczegóły kontaktu (zawiera emailer_touches)
        try:
            details = client.get_contact_details(contact_id)
            contact_detail = details.get("contact", details)

            # Emailer touches - historia aktywności emailowej
            touches = contact_detail.get("emailer_touches", [])
            if touches:
                result["emailer_touches"] = touches

            # Emailer campaigns kontaktu
            campaigns = contact_detail.get("emailer_campaigns", [])
            if campaigns:
                result["emailer_campaigns"] = campaigns

            # Statusy kontaktu
            result["bounced"] = contact_detail.get("email_status") == "bounced"
            result["unsubscribed"] = contact_detail.get("email_unsubscribed", False)

            # Aktywne sekwencje
            active_campaigns = [
                c for c in campaigns
                if c.get("emailer_campaign_id") and c.get("status") in ("active", "paused")
            ]
            if active_campaigns:
                result["active_sequences"] = active_campaigns
                result["sequence_status"] = "active"
            elif campaigns:
                result["sequence_status"] = "finished"

        except Exception as exc:
            log.warning("Nie udało się pobrać szczegółów kontaktu %s: %s", contact_id, exc)

        return result

    except Exception as exc:
        log.warning("Błąd pobierania engagement z Apollo dla '%s': %s", email, exc)
        return None


# ============================================================
# Full refresh — local + Apollo
# ============================================================

def refresh_contact_engagement(contact: dict) -> dict:
    """
    Pełny refresh engagement kontaktu: local profile + Apollo data.

    1. Wczytuje lokalny profil
    2. Pobiera engagement z Apollo
    3. Aktualizuje profil
    4. Zapisuje

    Returns:
        Zaktualizowany profil engagement.
    """
    profile = load_engagement_profile(contact)

    apollo_data = fetch_apollo_engagement(contact)
    if apollo_data:
        profile = update_engagement_from_apollo(contact, apollo_data)

    return profile


# ============================================================
# Batch operations
# ============================================================

def record_campaign_batch(
    contacts_results: list[dict],
    campaign_name: str,
    campaign_type: str,
    apollo_sequence_name: str | None = None,
    apollo_sequence_id: str | None = None,
) -> list[dict]:
    """
    Zapisuje outreach dla batch kontaktów po zakończeniu kampanii.

    Args:
        contacts_results: lista wyników pipeline (z contact, outreach_pack, routing)
        campaign_name: nazwa kampanii
        campaign_type: typ kampanii
        apollo_sequence_name: nazwa sekwencji Apollo
        apollo_sequence_id: ID sekwencji Apollo

    Returns:
        Lista zaktualizowanych profili.
    """
    profiles = []
    for result in contacts_results:
        contact = result.get("contact", {})
        outreach_pack = result.get("outreach_pack", {})
        routing = result.get("routing", {})

        if not outreach_pack:
            continue

        extra = {
            "tier": result.get("icp_tier", {}).get("tier", ""),
            "persona": result.get("persona_selection", {}).get("persona_type", ""),
            "lead_score": result.get("lead_scoring", {}).get("lead_score", 0),
            "qa_score": result.get("qa", {}).get("qa_score", 0),
            "qa_decision": result.get("qa", {}).get("decision", ""),
            "angle": result.get("hypothesis", {}).get("trigger_used", ""),
        }

        # Resolve angle via angle_tracker
        angle_data = None
        try:
            from src.core.angle_tracker import resolve_angles
            campaign_meta = result.get("campaign_metadata", {})
            angle_data = resolve_angles(
                pipeline_result=result,
                campaign_metadata=campaign_meta,
                hypothesis_text=result.get("hypothesis", {}).get("hypothesis", ""),
            )
        except ImportError:
            try:
                from core.angle_tracker import resolve_angles
                campaign_meta = result.get("campaign_metadata", {})
                angle_data = resolve_angles(
                    pipeline_result=result,
                    campaign_metadata=campaign_meta,
                    hypothesis_text=result.get("hypothesis", {}).get("hypothesis", ""),
                )
            except Exception as exc:
                log.warning("Angle resolution failed: %s", exc)
        except Exception as exc:
            log.warning("Angle resolution failed: %s", exc)

        profile = record_outreach(
            contact=contact,
            campaign_name=campaign_name,
            campaign_type=campaign_type,
            outreach_pack=outreach_pack,
            apollo_sequence_name=apollo_sequence_name or routing.get("sequence_recommendation"),
            apollo_sequence_id=apollo_sequence_id,
            mailbox_used=routing.get("mailbox_group"),
            extra_metadata=extra,
            angle_data=angle_data,
        )
        profiles.append(profile)

    log.info("Batch recorded: %d contacts for campaign '%s'", len(profiles), campaign_name)
    return profiles


# ============================================================
# Apollo client — lazy import (re-use pattern from apollo_campaign_sync)
# ============================================================

_apollo_client = None


def _get_apollo_client():
    """Lazy init ApolloClient. Zwraca None jeśli niedostępny."""
    global _apollo_client
    if _apollo_client is not None:
        return _apollo_client

    try:
        import sys
        integracje_dir = os.path.join(_ROOT_DIR, "Integracje")
        if integracje_dir not in sys.path:
            sys.path.insert(0, integracje_dir)
        from dotenv import load_dotenv
        load_dotenv(os.path.join(integracje_dir, ".env"))
        from apollo_client import ApolloClient
        _apollo_client = ApolloClient()
        return _apollo_client
    except Exception as exc:
        log.warning("Apollo client niedostępny: %s", exc)
        return None
