#!/usr/bin/env python3
"""
Continuation Writer — generuje wiadomości kontynuacyjne / re-engagement.

Wykorzystuje pełny kontekst engagement kontaktu:
- contact profile + engagement context
- angle history + recommended next angle
- LLM context summary
- previous subjects/bodies

Produkuje wiadomość, która brzmi jak naturalna kontynuacja relacji,
nie jak kolejny cold mail.

Feature-flagged: CONTINUATION_MODE_ENABLED = False domyślnie.
"""

import json
import logging
import os
import sys

log = logging.getLogger(__name__)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from llm_client import generate_json, is_llm_available
except ImportError:
    try:
        from src.llm_client import generate_json, is_llm_available
    except ImportError:
        def generate_json(*args, **kwargs):
            return None
        def is_llm_available():
            return False

# Feature flag
CONTINUATION_MODE_ENABLED = False

# Continuation modes
CONTINUATION_MODES = {
    "soft_reengagement": "Lekki re-engagement po otwarciach bez odpowiedzi",
    "opened_no_reply_followup": "Follow-up po otwarciach, kontakt zainteresowany ale nie odpisał",
    "angle_shift_continuation": "Zmiana narracji - inny angle po wyczerpaniu poprzedniego",
    "completed_sequence_reengagement": "Powrót po zakończonej sekwencji bez odpowiedzi",
}


# ============================================================
# Main generation function
# ============================================================

def generate_continuation_message(
    contact: dict,
    engagement_context: dict,
    continuation_mode: str,
    recommended_angle: dict | None = None,
    context_files: dict | None = None,
    config: dict | None = None,
    base_dir: str = "",
) -> dict:
    """
    Generuje wiadomość kontynuacyjną dla kontaktu.

    Args:
        contact: dane kontaktu (first_name, last_name, title, company, gender, vocative)
        engagement_context: pełny engagement context z build_engagement_context()
        continuation_mode: tryb kontynuacji (soft_reengagement, angle_shift_continuation, etc.)
        recommended_angle: sugerowany next angle z angle_tracker
        context_files: pliki kontekstowe *.md
        config: konfiguracja kampanii
        base_dir: root projektu

    Returns:
        dict z wygenerowaną wiadomością:
        {
            "subject": "...",
            "body": "...",
            "continuation_mode": "...",
            "chosen_angle_id": "...",
            "chosen_angle_label": "...",
            "reasoning": "...",
            "word_count": N,
            "language": "pl",
            "llm_used": True/False,
            "fallback_used": True/False,
        }
    """
    config = config or {}
    base_dir = base_dir or _ROOT_DIR

    # Resolve Polish gender/vocative
    gender_data = _resolve_gender(contact)

    # Build LLM payload
    payload = _build_payload(
        contact=contact,
        engagement_context=engagement_context,
        continuation_mode=continuation_mode,
        recommended_angle=recommended_angle,
        gender_data=gender_data,
        config=config,
    )

    # Try LLM generation
    if is_llm_available():
        prompt_path = os.path.join(base_dir, "prompts", "shared", "continuation_writer.md")
        if not os.path.exists(prompt_path):
            prompt_path = os.path.join(base_dir, "prompts", "base", "continuation_writer.md")

        result = generate_json(
            agent_name="ContinuationWriter",
            prompt_path=prompt_path,
            user_payload=payload,
            context_files=context_files,
            relevant_context_keys=[
                "01_offer", "02_personas", "03_messaging",
                "05_quality", "icp_tiers", "__icp_tier_active",
            ],
        )

        if result and "body" in result:
            result["llm_used"] = True
            result["fallback_used"] = False
            result["continuation_mode"] = continuation_mode

            # Override gender/vocative from deterministic source
            result["recipient_gender"] = gender_data["gender"]
            result["first_name_vocative"] = gender_data["first_name_vocative"]
            result["greeting"] = gender_data["greeting"]

            if "word_count" not in result:
                result["word_count"] = len(result["body"].split())
            if "language" not in result:
                result["language"] = config.get("language_code", "pl")
            if "chosen_angle_id" not in result and recommended_angle:
                result["chosen_angle_id"] = recommended_angle.get("angle_id", "")
                result["chosen_angle_label"] = recommended_angle.get("label_pl", "")

            # Append signature
            result = _append_signature(result)

            log.info(
                "Continuation message generated (LLM): mode=%s, angle=%s, words=%d",
                continuation_mode,
                result.get("chosen_angle_id", "?"),
                result.get("word_count", 0),
            )
            return result

    # Heuristic fallback
    log.info("LLM unavailable — using heuristic continuation fallback")
    return _heuristic_continuation(
        contact=contact,
        engagement_context=engagement_context,
        continuation_mode=continuation_mode,
        recommended_angle=recommended_angle,
        gender_data=gender_data,
        config=config,
    )


# ============================================================
# Build LLM payload
# ============================================================

def _build_payload(
    contact: dict,
    engagement_context: dict,
    continuation_mode: str,
    recommended_angle: dict | None,
    gender_data: dict,
    config: dict,
) -> dict:
    """Buduje payload dla LLM continuation writer."""
    angle_summary = engagement_context.get("angle_summary", {})
    eng_summary = engagement_context.get("engagement_summary", {})

    # Previous angle (most recent)
    previous_angle = {}
    angle_hist = angle_summary.get("angle_history", [])
    if angle_hist:
        last = angle_hist[-1]
        previous_angle = {
            "primary_angle_id": last.get("primary_angle_id", ""),
            "primary_angle_label": last.get("primary_angle_label", ""),
        }

    # Previous subjects summary (last 3)
    prev_subjects = [
        s.get("subject", "")
        for s in engagement_context.get("previous_subjects", [])
    ][-3:]

    # Previous bodies summary (first email only, truncated)
    prev_bodies = engagement_context.get("previous_bodies", [])
    bodies_summary = ""
    if prev_bodies:
        first_body = prev_bodies[0].get("body", "")
        if len(first_body) > 300:
            first_body = first_body[:300] + "..."
        bodies_summary = first_body

    payload = {
        "continuation_mode": continuation_mode,
        "contact_first_name": contact.get("first_name", contact.get("contact_first_name", "")),
        "contact_title": contact.get("title", contact.get("contact_title", "")),
        "company_name": contact.get("company", contact.get("company_name", "")),
        "industry": contact.get("industry", ""),
        "gender": gender_data["gender"],
        "first_name_vocative": gender_data["first_name_vocative"],
        "greeting": gender_data["greeting"],
        "current_status": engagement_context.get("current_status", ""),
        "engagement_summary": {
            "opens_count": eng_summary.get("opens_count", 0),
            "replied": eng_summary.get("replied", False),
            "total_campaigns": eng_summary.get("total_campaigns", 0),
            "total_steps_sent": eng_summary.get("total_steps_sent", 0),
        },
        "previous_angle": previous_angle,
        "recommended_next_angle": recommended_angle or {},
        "used_angles": angle_summary.get("used_angle_labels", []),
        "overused_angles": [
            _angle_label(a) for a in angle_summary.get("overused_angles", [])
        ],
        "previous_subjects": prev_subjects,
        "previous_bodies_summary": bodies_summary,
        "llm_context_summary": engagement_context.get("llm_context_summary", ""),
        "tier": contact.get("tier", "tier_2"),
        "language": config.get("language_code", "pl"),
        "max_words": config.get("message", {}).get("max_words", 100),
        "style": config.get("message", {}).get("style", "concise_consultative"),
    }
    return payload


# ============================================================
# Heuristic fallback
# ============================================================

_HEURISTIC_TEMPLATES = {
    "soft_reengagement": {
        "subject_prefix": "Pytanie - ",
        "opener": "wracam z jednym krótkim pytaniem.",
        "bridge": "Ostatnio pisałem w kontekście {prev_angle}. Pomyślałem, że może warto spojrzeć na to z innej strony - {next_angle_label}.",
        "cta": "Czy ma sens krótka rozmowa na ten temat? Telefon albo Teams - jak wygodniej.",
    },
    "opened_no_reply_followup": {
        "subject_prefix": "Inna perspektywa - ",
        "opener": "wracam do tematu, ale z trochę innej strony.",
        "bridge": "Zamiast wracać do {prev_angle}, chciałem zapytać o {next_angle_label} w kontekście {company}.",
        "cta": "Jeśli to bardziej trafiony temat - proszę dać znać, kiedy wygodnie porozmawiać.",
    },
    "angle_shift_continuation": {
        "subject_prefix": "Inny kąt - ",
        "opener": "pomyślałem, że może warto podejść do tematu z zupełnie innej strony.",
        "bridge": "W kontekście {company}, temat {next_angle_label} może być ciekawszy niż to, o czym pisałem wcześniej.",
        "cta": "Czy to bliższe temu, z czym mierzy się Pan/Pani na co dzień? Krótki telefon wystarczy.",
    },
    "completed_sequence_reengagement": {
        "subject_prefix": "Powrót do tematu - ",
        "opener": "wracam po jakimś czasie z jednym pytaniem.",
        "bridge": "Od ostatniego kontaktu sporo się zmieniło na rynku. W kontekście {next_angle_label} - zastanawiam się, czy temat jest teraz bardziej aktualny dla {company}.",
        "cta": "Jeśli tak - proszę o krótki sygnał, chętnie opowiem więcej. Telefon albo Teams.",
    },
}


def _heuristic_continuation(
    contact: dict,
    engagement_context: dict,
    continuation_mode: str,
    recommended_angle: dict | None,
    gender_data: dict,
    config: dict,
) -> dict:
    """Generuje heurystyczną wiadomość kontynuacyjną (fallback bez LLM)."""
    template = _HEURISTIC_TEMPLATES.get(
        continuation_mode,
        _HEURISTIC_TEMPLATES["soft_reengagement"],
    )

    company = contact.get("company", contact.get("company_name", "Firma"))
    next_angle_label = (recommended_angle or {}).get("label_pl", "koszty zakupowe")
    next_angle_id = (recommended_angle or {}).get("angle_id", "general")

    # Previous angle label
    angle_summary = engagement_context.get("angle_summary", {})
    prev_angle_label = "poprzedni temat"
    angle_hist = angle_summary.get("angle_history", [])
    if angle_hist:
        prev_angle_label = angle_hist[-1].get("primary_angle_label", prev_angle_label)

    greeting = gender_data["greeting"]

    # Build subject
    subject = template["subject_prefix"] + f"{next_angle_label} w {company}"

    # Build body
    opener = template["opener"]
    bridge = template["bridge"].format(
        prev_angle=prev_angle_label,
        next_angle_label=next_angle_label,
        company=company,
    )
    cta = template["cta"]

    body = f"{greeting}\n\n{opener}\n\n{bridge}\n\n{cta}"

    result = {
        "subject": subject,
        "body": body,
        "continuation_mode": continuation_mode,
        "chosen_angle_id": next_angle_id,
        "chosen_angle_label": next_angle_label,
        "reasoning": f"Heuristic fallback: mode={continuation_mode}, prev_angle={prev_angle_label}, next_angle={next_angle_label}",
        "word_count": len(body.split()),
        "language": config.get("language_code", "pl"),
        "llm_used": False,
        "fallback_used": True,
        "recipient_gender": gender_data["gender"],
        "first_name_vocative": gender_data["first_name_vocative"],
        "greeting": greeting,
    }

    result = _append_signature(result)
    return result


# ============================================================
# Batch continuation
# ============================================================

def generate_continuation_batch(
    contacts_with_context: list[dict],
    context_files: dict | None = None,
    config: dict | None = None,
    base_dir: str = "",
) -> list[dict]:
    """
    Generuje continuation messages dla batcha kontaktów.

    Args:
        contacts_with_context: lista dict z kluczami:
            - contact: dane kontaktu
            - engagement_context: pełny kontekst engagement
            - continuation_mode: tryb kontynuacji
            - recommended_angle: sugerowany angle (opcjonalny)

    Returns:
        Lista wyników generowania.
    """
    results = []
    for item in contacts_with_context:
        try:
            result = generate_continuation_message(
                contact=item["contact"],
                engagement_context=item["engagement_context"],
                continuation_mode=item["continuation_mode"],
                recommended_angle=item.get("recommended_angle"),
                context_files=context_files,
                config=config,
                base_dir=base_dir,
            )
            result["contact_email"] = item["contact"].get(
                "email", item["contact"].get("contact_email", "")
            )
            results.append(result)
        except Exception as exc:
            log.warning("Continuation generation failed for %s: %s",
                        item.get("contact", {}).get("email", "?"), exc)
            results.append({
                "contact_email": item.get("contact", {}).get("email", "?"),
                "error": str(exc),
                "continuation_mode": item.get("continuation_mode", ""),
            })
    return results


# ============================================================
# Helpers
# ============================================================

def _resolve_gender(contact: dict) -> dict:
    """Resolve Polish gender/vocative for contact."""
    try:
        from core.polish_names import resolve_polish_contact
    except ImportError:
        try:
            from src.core.polish_names import resolve_polish_contact
        except ImportError:
            # Minimal fallback
            first = contact.get("first_name", contact.get("contact_first_name", ""))
            return {
                "gender": "unknown",
                "first_name_vocative": first,
                "greeting": f"Dzień dobry,",
            }

    first_name = contact.get("first_name", contact.get("contact_first_name", "")).strip()
    return resolve_polish_contact(first_name)


def _append_signature(result: dict) -> dict:
    """Append email signature to body."""
    try:
        from core.email_signature import append_signature
    except ImportError:
        try:
            from src.core.email_signature import append_signature
        except ImportError:
            return result
    return append_signature(result)


def _angle_label(angle_id: str) -> str:
    """Get Polish label for angle ID."""
    try:
        from core.angle_tracker import get_angle_info
    except ImportError:
        try:
            from src.core.angle_tracker import get_angle_info
        except ImportError:
            return angle_id
    info = get_angle_info(angle_id)
    return info.get("label_pl", angle_id) if info else angle_id
