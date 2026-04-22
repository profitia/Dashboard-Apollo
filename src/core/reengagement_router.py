#!/usr/bin/env python3
"""
Re-engagement Router — decyzje o dalszym kontakcie.

Draft / disabled by default. Przygotowany pod przyszłe decyzje:
- send_new_outbound
- send_continuation
- send_reengagement
- do_not_send
- wait
- reply_context_mode

Architektura jest gotowa, ale pełny decision engine uruchomimy
po zebraniu danych engagement z pierwszych kampanii.
"""

import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# Feature flag — włączyć gdy router będzie gotowy do produkcji
ROUTER_ENABLED = False

# Cooldown po zakończonej sekwencji (dni)
DEFAULT_COOLDOWN_DAYS = 30
# Maksymalna liczba kampanii przed eskalacją
MAX_CAMPAIGNS_BEFORE_PAUSE = 3


# ============================================================
# Decyzje
# ============================================================

class EngagementDecision:
    SEND_NEW_OUTBOUND = "send_new_outbound"
    SEND_CONTINUATION = "send_continuation"
    SEND_REENGAGEMENT = "send_reengagement"
    DO_NOT_SEND = "do_not_send"
    WAIT = "wait"
    REPLY_CONTEXT_MODE = "reply_context_mode"


# ============================================================
# Router logic
# ============================================================

def route_contact(context: dict, config: dict | None = None) -> dict:
    """
    Decyduje o trybie dalszego kontaktu na podstawie engagement context.

    Args:
        context: pełny obiekt kontekstu z build_engagement_context()
        config: opcjonalna konfiguracja (cooldown_days, max_campaigns, etc.)

    Returns:
        dict z decyzją:
        {
            "decision": "send_reengagement" | "wait" | ...,
            "reason": "...",
            "recommended_angle": "...",
            "confidence": "high" | "medium" | "low",
            "router_enabled": True/False,
        }
    """
    if not ROUTER_ENABLED:
        return {
            "decision": EngagementDecision.SEND_NEW_OUTBOUND,
            "reason": "Router disabled - default to new outbound",
            "recommended_angle": None,
            "confidence": "low",
            "router_enabled": False,
        }

    config = config or {}
    cooldown_days = config.get("cooldown_days", DEFAULT_COOLDOWN_DAYS)
    max_campaigns = config.get("max_campaigns", MAX_CAMPAIGNS_BEFORE_PAUSE)

    status = context.get("current_status", "never_contacted")
    engagement = context.get("engagement_summary", {})
    campaigns = context.get("previous_campaigns", [])

    # === Hard stops ===
    if status == "do_not_contact":
        return _decision(EngagementDecision.DO_NOT_SEND,
                         "Contact opted out / unsubscribed", confidence="high")

    if status == "bounced":
        return _decision(EngagementDecision.DO_NOT_SEND,
                         "Email bounced - invalid address", confidence="high")

    # === Reply handling ===
    if status == "replied":
        return _decision(EngagementDecision.REPLY_CONTEXT_MODE,
                         "Contact replied - switch to conversation mode",
                         confidence="high")

    # === Never contacted ===
    if status == "never_contacted":
        return _decision(EngagementDecision.SEND_NEW_OUTBOUND,
                         "First contact - standard outbound",
                         confidence="high")

    # === Campaign saturation check ===
    if len(campaigns) >= max_campaigns:
        return _decision(EngagementDecision.DO_NOT_SEND,
                         f"Max campaigns reached ({len(campaigns)}/{max_campaigns})",
                         confidence="medium")

    # === Cooldown check ===
    if campaigns:
        last_campaign = campaigns[-1]
        last_sent = last_campaign.get("sent_at", "")
        if last_sent:
            try:
                last_dt = datetime.fromisoformat(last_sent)
                days_since = (datetime.now() - last_dt).days
                if days_since < cooldown_days:
                    return _decision(EngagementDecision.WAIT,
                                     f"Cooldown: {days_since}d since last campaign "
                                     f"(min {cooldown_days}d)",
                                     confidence="medium")
            except (ValueError, TypeError):
                pass

    # === Engagement-based routing ===
    angle_summary = context.get("angle_summary", {})
    overused = angle_summary.get("overused_angles", [])

    if status == "opened_no_reply":
        opens = engagement.get("opens_count", 0)
        angle_rec = _angle_recommendation(context)

        # Determine continuation mode
        if overused:
            cont_mode = "angle_shift_continuation"
        elif opens >= 3:
            cont_mode = "soft_reengagement"
        else:
            cont_mode = "opened_no_reply_followup"

        if opens >= 3:
            return _decision(EngagementDecision.SEND_REENGAGEMENT,
                             f"High opens ({opens}) but no reply - re-engage with new angle",
                             recommended_angle=angle_rec,
                             continuation_mode=cont_mode,
                             confidence="medium")
        return _decision(EngagementDecision.SEND_REENGAGEMENT,
                         "Opened but no reply - try different approach",
                         recommended_angle=angle_rec,
                         continuation_mode=cont_mode,
                         confidence="medium")

    if status == "completed_sequence":
        angle_rec = _angle_recommendation(context)
        cont_mode = "angle_shift_continuation" if overused else "completed_sequence_reengagement"
        return _decision(EngagementDecision.SEND_REENGAGEMENT,
                         "Sequence completed - re-engagement after cooldown",
                         recommended_angle=angle_rec,
                         continuation_mode=cont_mode,
                         confidence="low")

    if status == "active_sequence":
        return _decision(EngagementDecision.WAIT,
                         "Active sequence in progress - wait for completion",
                         confidence="high")

    # === Default ===
    return _decision(EngagementDecision.SEND_NEW_OUTBOUND,
                     "Default routing - standard outbound",
                     confidence="low")


def _angle_recommendation(context: dict) -> str | None:
    """Zwraca angle recommendation na podstawie angle_summary w kontekście."""
    angle_summary = context.get("angle_summary", {})
    overused = angle_summary.get("overused_angles", [])
    strategy = angle_summary.get("recommended_next_angle_strategy", "")

    if overused:
        # Spróbuj zasugerować konkretny angle z angle_tracker
        try:
            from src.core.angle_tracker import suggest_next_angles
        except ImportError:
            from core.angle_tracker import suggest_next_angles
        try:
            # ale możemy zbudować minimalny z angle_history
            fake_profile = {
                "outreach_history": [],
                "angle_history": angle_summary.get("angle_history", []),
                "engagement_snapshot": {
                    "replied": context.get("engagement_summary", {}).get("replied", False),
                },
                "current_status": context.get("current_status", ""),
            }
            suggestions = suggest_next_angles(fake_profile, max_suggestions=1)
            if suggestions:
                return suggestions[0].get("angle_id")
        except Exception:
            pass
        return "new_angle_required"

    if strategy:
        return strategy

    return None


def _decision(
    decision: str,
    reason: str,
    recommended_angle: str | None = None,
    continuation_mode: str | None = None,
    confidence: str = "medium",
) -> dict:
    return {
        "decision": decision,
        "reason": reason,
        "recommended_angle": recommended_angle,
        "continuation_mode": continuation_mode,
        "confidence": confidence,
        "router_enabled": ROUTER_ENABLED,
        "decided_at": datetime.now().isoformat(),
    }


# ============================================================
# Batch routing
# ============================================================

def route_contacts_batch(contexts: list[dict], config: dict | None = None) -> list[dict]:
    """
    Routuje batch kontaktów.

    Returns:
        Lista par (context, decision).
    """
    results = []
    for ctx in contexts:
        decision = route_contact(ctx, config)
        results.append({
            "contact_email": ctx.get("contact_email", ""),
            "contact_name": ctx.get("contact_name", ""),
            "current_status": ctx.get("current_status", ""),
            "decision": decision,
        })
    return results


# ============================================================
# Filter: contacts eligible for outreach
# ============================================================

def filter_eligible_for_outreach(
    contexts: list[dict],
    config: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Filtruje kontakty: eligible vs. excluded.

    Returns:
        (eligible, excluded) — dwie listy kontekstów.
    """
    eligible = []
    excluded = []

    for ctx in contexts:
        decision = route_contact(ctx, config)
        if decision["decision"] in (
            EngagementDecision.SEND_NEW_OUTBOUND,
            EngagementDecision.SEND_CONTINUATION,
            EngagementDecision.SEND_REENGAGEMENT,
        ):
            ctx["_routing_decision"] = decision
            eligible.append(ctx)
        else:
            ctx["_routing_decision"] = decision
            excluded.append(ctx)

    log.info("Routing: %d eligible, %d excluded", len(eligible), len(excluded))
    return eligible, excluded
