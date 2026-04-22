#!/usr/bin/env python3
"""
Contact Engagement Context — buduje syntetyczny kontekst kontaktu.

Łączy dane z:
- lokalnej historii outreach (contact_engagement_tracker)
- Apollo engagement data
- campaign history (contact_campaign_history)

Produkuje ustrukturyzowany obiekt JSON gotowy do:
- podania do LLM jako kontekst
- zapisu per contact
- użycia w decyzjach re-engagement
"""

import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Build full engagement context
# ============================================================

def build_engagement_context(contact: dict, profile: dict | None = None) -> dict:
    """
    Buduje pełny syntetyczny kontekst engagement kontaktu.

    Args:
        contact: dane kontaktu (email, first_name, last_name, company, title)
        profile: opcjonalny profil z contact_engagement_tracker
                 (jeśli None, wczytuje z dysku)

    Returns:
        dict — pełny obiekt kontekstu:
        {
            "contact_id": ...,
            "contact_email": ...,
            "contact_name": ...,
            "current_status": ...,
            "previous_campaigns": [...],
            "previous_subjects": [...],
            "previous_bodies": [...],
            "engagement_summary": {...},
            "contact_extended": {...},
            "llm_context_summary": "...",
            "built_at": "..."
        }
    """
    if profile is None:
        from src.core.contact_engagement_tracker import load_engagement_profile
        profile = load_engagement_profile(contact)

    context = {
        "contact_id": profile.get("apollo_contact_id"),
        "contact_email": profile.get("contact_email", ""),
        "contact_name": profile.get("contact_name", ""),
        "contact_title": profile.get("contact_title", ""),
        "company_name": profile.get("company_name", ""),
        "current_status": profile.get("current_status", "never_contacted"),
        "previous_campaigns": _extract_campaigns(profile),
        "previous_subjects": _extract_subjects(profile),
        "previous_bodies": _extract_bodies(profile),
        "engagement_summary": _build_engagement_summary(profile),
        "angle_history": _extract_angle_history(profile),
        "angle_summary": _build_angle_summary(profile),
        "contact_extended": _extract_extended_context(contact, profile),
        "llm_context_summary": "",  # Wypełniane przez engagement_llm_summarizer
        "built_at": datetime.now().isoformat(),
    }

    return context


def _extract_campaigns(profile: dict) -> list[dict]:
    """Wyciąga listę kampanii z historii outreach."""
    campaigns = []
    for entry in profile.get("outreach_history", []):
        campaigns.append({
            "campaign_name": entry.get("campaign_name", ""),
            "campaign_type": entry.get("campaign_type", ""),
            "apollo_sequence_name": entry.get("apollo_sequence_name"),
            "apollo_sequence_id": entry.get("apollo_sequence_id"),
            "sent_at": entry.get("sent_at", ""),
            "sent_date": entry.get("sent_date", ""),
            "steps_count": entry.get("steps_count", 0),
            "mailbox_used": entry.get("mailbox_used"),
            "metadata": entry.get("metadata", {}),
        })
    return campaigns


def _extract_subjects(profile: dict) -> list[dict]:
    """Wyciąga listę tematów z historii outreach."""
    subjects = []
    for entry in profile.get("outreach_history", []):
        campaign_name = entry.get("campaign_name", "")
        for step in entry.get("steps", []):
            subject = step.get("subject", "")
            if subject:
                subjects.append({
                    "step_number": step.get("step_number", 0),
                    "subject": subject,
                    "sent_at": entry.get("sent_at", ""),
                    "campaign_name": campaign_name,
                })
    return subjects


def _extract_bodies(profile: dict) -> list[dict]:
    """Wyciąga listę treści z historii outreach."""
    bodies = []
    for entry in profile.get("outreach_history", []):
        campaign_name = entry.get("campaign_name", "")
        for step in entry.get("steps", []):
            body = step.get("body", "")
            if body:
                bodies.append({
                    "step_number": step.get("step_number", 0),
                    "body": body,
                    "sent_at": entry.get("sent_at", ""),
                    "campaign_name": campaign_name,
                })
    return bodies


def _build_engagement_summary(profile: dict) -> dict:
    """Buduje podsumowanie engagement z profilu."""
    snap = profile.get("engagement_snapshot", {})

    return {
        "opens_count": snap.get("total_opens", 0),
        "unique_opens": snap.get("unique_opens", 0),
        "last_open_at": snap.get("last_open_at"),
        "replied": snap.get("replied", False),
        "total_replies": snap.get("total_replies", 0),
        "last_reply_at": snap.get("last_reply_at"),
        "bounced": snap.get("bounced", False),
        "unsubscribed": snap.get("unsubscribed", False),
        "last_checked_at": snap.get("last_checked_at"),
        "total_campaigns": len(profile.get("outreach_history", [])),
        "total_steps_sent": sum(
            e.get("steps_count", 0) for e in profile.get("outreach_history", [])
        ),
    }


def _extract_angle_history(profile: dict) -> list[dict]:
    """Wyciąga historię angles z profilu."""
    try:
        from src.core.angle_tracker import build_angle_history
        return build_angle_history(profile)
    except ImportError:
        try:
            from core.angle_tracker import build_angle_history
            return build_angle_history(profile)
        except Exception:
            return profile.get("angle_history", [])
    except Exception:
        return profile.get("angle_history", [])


def _build_angle_summary(profile: dict) -> dict:
    """Buduje podsumowanie angles z profilu."""
    try:
        from src.core.angle_tracker import build_angle_summary
        return build_angle_summary(profile)
    except ImportError:
        try:
            from core.angle_tracker import build_angle_summary
            return build_angle_summary(profile)
        except Exception:
            pass
    except Exception:
        pass
    # Fallback: minimalne podsumowanie
    angle_hist = profile.get("angle_history", [])
    if not angle_hist:
        return {
            "used_angles": [],
            "most_recent_angle": None,
            "total_campaigns_with_angles": 0,
            "overused_angles": [],
        }
    ids = [h.get("primary_angle_id", "general") for h in angle_hist]
    return {
        "used_angles": list(dict.fromkeys(ids)),
        "most_recent_angle": ids[-1] if ids else None,
        "total_campaigns_with_angles": len(angle_hist),
        "overused_angles": [],
    }


def _extract_extended_context(contact: dict, profile: dict) -> dict:
    """
    Wyciąga rozszerzony kontekst kontaktu z rich profile (jeśli dostępny).

    Dane używane w downstream logic (hypothesis, angle selection, re-engagement),
    ale NIE dumpowane w całości do LLM prompt.
    """
    extended = {}

    # 1. From engagement profile (contact_extended saved during load)
    profile_ext = profile.get("contact_extended", {})
    if profile_ext:
        extended.update({k: v for k, v in profile_ext.items() if v})

    # 2. From contact dict (normalized contact with rich_profile)
    rich = contact.get("rich_profile")
    if rich:
        org = rich.get("org_context", {})
        urls = rich.get("urls", {})
        loc = rich.get("location", {})
        cm = rich.get("company_metadata", {})

        # Merge — enrich, don't overwrite
        for key, val in {
            "industry": org.get("industry"),
            "keywords_raw": org.get("keywords_raw"),
            "keywords_list": org.get("keywords_list"),
            "seniority": rich.get("core_identity", {}).get("seniority"),
            "departments": org.get("departments"),
            "person_linkedin_url": urls.get("person_linkedin_url"),
            "website": urls.get("website") or urls.get("company_domain"),
            "company_linkedin_url": urls.get("company_linkedin_url"),
            "city": loc.get("city"),
            "country": loc.get("country"),
            "company_city": loc.get("company_city"),
            "company_country": loc.get("company_country"),
            "company_phone": cm.get("company_phone"),
            "employees_count": cm.get("employees_count"),
        }.items():
            if val and key not in extended:
                extended[key] = val

    # 3. Try loading from rich_contact_profile storage
    if not extended:
        try:
            from core.rich_contact_profile import load_rich_profile_by_contact
            stored = load_rich_profile_by_contact(contact)
            if stored:
                org = stored.get("org_context", {})
                urls = stored.get("urls", {})
                extended = {
                    "industry": org.get("industry"),
                    "keywords_raw": org.get("keywords_raw"),
                    "person_linkedin_url": urls.get("person_linkedin_url"),
                    "website": urls.get("website"),
                }
                extended = {k: v for k, v in extended.items() if v}
        except Exception:
            pass

    return extended


# ============================================================
# Save / Load context
# ============================================================

_CONTEXT_DIR = os.path.join(_ROOT_DIR, "data", "contact_engagement")


def save_engagement_context(context: dict):
    """Zapisuje syntetyczny kontekst kontaktu."""
    os.makedirs(_CONTEXT_DIR, exist_ok=True)
    email = context.get("contact_email", "unknown")
    safe_key = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in email)
    path = os.path.join(_CONTEXT_DIR, f"{safe_key}_context.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)
    log.info("Engagement context saved: %s", path)
    return path


def load_engagement_context(contact_email: str) -> dict | None:
    """Wczytuje zapisany kontekst engagement kontaktu."""
    safe_key = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in contact_email.lower())
    path = os.path.join(_CONTEXT_DIR, f"{safe_key}_context.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ============================================================
# Batch context building
# ============================================================

def build_batch_contexts(
    profiles: list[dict],
) -> list[dict]:
    """
    Buduje konteksty engagement dla listy profili.

    Returns:
        Lista kontekstów.
    """
    contexts = []
    for profile in profiles:
        contact = {
            "email": profile.get("contact_email", ""),
            "first_name": profile.get("contact_name", "").split()[0] if profile.get("contact_name") else "",
            "last_name": " ".join(profile.get("contact_name", "").split()[1:]) if profile.get("contact_name") else "",
            "company": profile.get("company_name", ""),
            "title": profile.get("contact_title", ""),
        }
        ctx = build_engagement_context(contact, profile)
        contexts.append(ctx)
    return contexts
