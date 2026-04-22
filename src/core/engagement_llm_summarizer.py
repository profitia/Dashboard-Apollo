#!/usr/bin/env python3
"""
Engagement LLM Summarizer — generuje syntetyczny kontekst dla LLM.

Produkuje krótkie, użyteczne streszczenie historii engagement kontaktu,
gotowe do wpięcia w prompt LLM przy generowaniu:
- continuation messages
- re-engagement messages
- follow-upów opartych o historię

Dwie ścieżki:
1. Heurystyczna (domyślna, zawsze dostępna) — template-based summary
2. LLM (opcjonalna, przyszłość) — LLM streszcza surowe dane
"""

import logging
import os

log = logging.getLogger(__name__)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Status labels (PL)
# ============================================================

_STATUS_LABELS = {
    "never_contacted": "Nigdy nie kontaktowany",
    "active_sequence": "Aktywna sekwencja",
    "completed_sequence": "Zakończona sekwencja",
    "opened_no_reply": "Otworzył wiadomości, nie odpowiedział",
    "replied": "Odpowiedział",
    "bounced": "Email nieaktualny (bounce)",
    "paused": "Wstrzymany",
    "do_not_contact": "Nie kontaktować (unsubscribe / opt-out)",
    "reengagement_candidate": "Kandydat do re-engagement",
}


def _get_angle_label(angle_id: str) -> str:
    """Zwraca label_pl angle'a po ID (z cache taxonomy)."""
    try:
        from src.core.angle_tracker import get_angle_info
        info = get_angle_info(angle_id)
        if info:
            return info.get("label_pl", angle_id)
    except ImportError:
        try:
            from core.angle_tracker import get_angle_info
            info = get_angle_info(angle_id)
            if info:
                return info.get("label_pl", angle_id)
        except Exception:
            pass
    except Exception:
        pass
    return angle_id


# ============================================================
# Heuristic summary builder
# ============================================================

def build_llm_context_summary(context: dict) -> str:
    """
    Buduje heurystyczne streszczenie engagement kontaktu dla LLM.

    Krótkie, konkretne, bez śmieci. Gotowe do wpięcia w prompt.

    Args:
        context: pełny obiekt kontekstu z build_engagement_context()

    Returns:
        str — streszczenie kontekstu, np.:
        "Kontakt Jan Kowalski (CPO, Firma Sp. z o.o.) był w 2 kampaniach.
         Otworzył 3 z 6 wiadomości. Nie odpowiedział.
         Główne angles: podwyżki dostawców, savings delivery.
         Obecny status: opened_no_reply.
         Zalecany tryb: soft re-engagement with new angle."
    """
    name = context.get("contact_name", "Nieznany")
    title = context.get("contact_title", "")
    company = context.get("company_name", "")
    status = context.get("current_status", "never_contacted")
    campaigns = context.get("previous_campaigns", [])
    subjects = context.get("previous_subjects", [])
    engagement = context.get("engagement_summary", {})

    # Jeśli nigdy nie kontaktowany
    if status == "never_contacted" or not campaigns:
        return f"Kontakt {name} ({title}, {company}) - brak wcześniejszej komunikacji. Pierwszy kontakt."

    parts = []

    # Linia 1: Kim jest i ile kampanii
    identity = f"Kontakt {name}"
    if title:
        identity += f" ({title}"
        if company:
            identity += f", {company}"
        identity += ")"
    elif company:
        identity += f" ({company})"

    campaign_count = len(campaigns)
    parts.append(f"{identity} byl w {campaign_count} kampanii{'ach' if campaign_count > 1 else 'i'}.")

    # Linia 2: Nazwy kampanii
    campaign_names = [c.get("campaign_name", "?") for c in campaigns]
    if campaign_names:
        parts.append(f"Kampanie: {', '.join(campaign_names)}.")

    # Linia 3: Engagement
    opens = engagement.get("opens_count", 0)
    total_steps = engagement.get("total_steps_sent", 0)
    replied = engagement.get("replied", False)

    if opens > 0 and total_steps > 0:
        parts.append(f"Otworzyl {opens} z {total_steps} wiadomosci.")
    elif total_steps > 0:
        parts.append(f"Wyslano {total_steps} wiadomosci - brak otwarc.")

    if replied:
        parts.append("Odpowiedzial na wiadomosc.")
    elif opens > 0:
        parts.append("Nie odpowiedzial.")

    # Linia 4: Angles
    angle_summary = context.get("angle_summary", {})
    used_angle_labels = angle_summary.get("used_angle_labels", [])
    most_recent_label = angle_summary.get("most_recent_angle_label")
    overused_labels = [
        taxonomy_label
        for a_id in angle_summary.get("overused_angles", [])
        for taxonomy_label in [_get_angle_label(a_id)]
        if taxonomy_label
    ]

    if used_angle_labels:
        parts.append(f"Glowne angles: {', '.join(used_angle_labels)}.")

    if overused_labels:
        parts.append(f"Naduzywane angles (bez odpowiedzi): {', '.join(overused_labels)}.")

    strategy = angle_summary.get("recommended_next_angle_strategy", "")
    if strategy:
        parts.append(f"Strategia angles: {strategy}.")

    # Linia 5: Tematy
    if subjects:
        unique_subjects = list(dict.fromkeys(s.get("subject", "") for s in subjects))[:3]
        parts.append(f"Tematy: {'; '.join(unique_subjects)}.")

    # Linia 5: Status
    status_label = _STATUS_LABELS.get(status, status)
    parts.append(f"Obecny status: {status_label}.")

    # Linia 6: Rekomendacja trybu
    recommendation = _recommend_mode(context)
    if recommendation:
        parts.append(f"Zalecany tryb: {recommendation}.")

    return " ".join(parts)


def _recommend_mode(context: dict) -> str:
    """Heurystyczna rekomendacja trybu dalszego kontaktu."""
    status = context.get("current_status", "never_contacted")
    engagement = context.get("engagement_summary", {})
    campaigns = context.get("previous_campaigns", [])
    angle_summary = context.get("angle_summary", {})
    overused = angle_summary.get("overused_angles", [])

    if status == "never_contacted":
        return "first outbound"

    if status == "bounced":
        return "skip - email bounce"

    if status == "do_not_contact":
        return "do not send"

    if status == "replied":
        return "reply context mode - kontynuacja rozmowy"

    if status == "opened_no_reply":
        opens = engagement.get("opens_count", 0)
        if overused:
            return "soft re-engagement with NEW angle (current angle overused)"
        if opens >= 3:
            return "soft re-engagement with new angle"
        return "re-engagement - zmiana narracji"

    if status == "completed_sequence":
        campaign_count = len(campaigns)
        if overused:
            return "new angle required (previous angle exhausted)"
        if campaign_count >= 2:
            return "wait or new angle (multiple campaigns exhausted)"
        return "re-engagement after cooldown"

    if status == "active_sequence":
        return "wait - active sequence in progress"

    return "standard outbound"


# ============================================================
# LLM-based summary (przygotowane, disabled by default)
# ============================================================

# Feature flag — włączyć gdy LLM summary będzie gotowy do produkcji
LLM_SUMMARY_ENABLED = False


def build_llm_context_summary_via_llm(context: dict) -> str | None:
    """
    Generuje streszczenie przez LLM (draft, disabled by default).

    Gdy włączone, LLM dostaje surowy kontekst i produkuje zwięzłe streszczenie
    optymalne do wpięcia w prompt generujący wiadomość.

    Returns:
        str streszczenie lub None jeśli niedostępne / disabled.
    """
    if not LLM_SUMMARY_ENABLED:
        return None

    try:
        from llm_client import generate_json, is_llm_available
        if not is_llm_available():
            return None

        prompt_path = os.path.join(_ROOT_DIR, "prompts", "shared", "engagement_summarizer.md")
        if not os.path.exists(prompt_path):
            log.warning("Brak promptu engagement_summarizer.md - fallback do heurystyki")
            return None

        payload = {
            "contact_name": context.get("contact_name", ""),
            "contact_title": context.get("contact_title", ""),
            "company_name": context.get("company_name", ""),
            "current_status": context.get("current_status", ""),
            "campaigns_count": len(context.get("previous_campaigns", [])),
            "campaign_names": [c.get("campaign_name") for c in context.get("previous_campaigns", [])],
            "subjects": [s.get("subject") for s in context.get("previous_subjects", [])],
            "engagement": context.get("engagement_summary", {}),
        }

        result = generate_json(
            agent_name="EngagementSummarizer",
            prompt_path=prompt_path,
            user_payload=payload,
        )

        if result and "summary" in result:
            return result["summary"]

    except Exception as exc:
        log.warning("LLM summary failed: %s", exc)

    return None


# ============================================================
# Main entry point
# ============================================================

def generate_context_summary(context: dict) -> str:
    """
    Generuje streszczenie kontekstu: LLM jeśli włączone, inaczej heurystyka.

    Returns:
        str — streszczenie gotowe do wpięcia w prompt.
    """
    if LLM_SUMMARY_ENABLED:
        llm_summary = build_llm_context_summary_via_llm(context)
        if llm_summary:
            return llm_summary

    return build_llm_context_summary(context)
