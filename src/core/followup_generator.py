#!/usr/bin/env python3
"""
Wspólny generator follow-upów (step 2, step 3) dla wszystkich kampanii.

Używa follow_up_writer.md prompt + LLM, z heurystycznym fallbackiem.
"""

import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from llm_client import generate_json, is_llm_available
except ImportError:
    def generate_json(*args, **kwargs):
        return None
    def is_llm_available():
        return False


# ============================================================
# LLM follow-up generation
# ============================================================

def generate_followup_body(
    step_number: int,
    original_subject: str,
    original_body_clean: str,
    previous_followup_body: str,
    contact: dict,
    message: dict,
    context_files: dict | None = None,
    base_dir: str = "",
    trigger_title: str = "",
    trigger_source: str = "",
) -> str | None:
    """
    Generuje tekst follow-upa przez LLM. Zwraca body_core lub None.

    Args:
        step_number: 2 (follow_up_1) lub 3 (follow_up_2)
        original_subject: Subject z email_1
        original_body_clean: Body email_1 bez podpisu
        previous_followup_body: Body follow_up_1 (tylko jeśli step_number==3)
        contact: Dict z first_name, last_name, title, company, domain
        message: Dict z recipient_gender, first_name_vocative
        context_files: Pliki kontekstowe
        base_dir: Root projektu
        trigger_title: Tytuł triggera (np. artykuł)
        trigger_source: Źródło triggera (np. portal)
    """
    if not is_llm_available():
        return None

    prompt_path = os.path.join(base_dir, "prompts", "shared", "follow_up_writer.md")
    if not os.path.exists(prompt_path):
        return None

    payload = {
        "step_number": step_number,
        "original_subject": original_subject,
        "original_body": original_body_clean,
        "previous_followup_body": previous_followup_body or "",
        "persona_type": "cpo",
        "contact_first_name": contact.get("first_name", ""),
        "contact_title": contact.get("title", contact.get("contact_title", "")),
        "company_name": contact.get("company", contact.get("company_name", "")),
        "recipient_gender": message.get("recipient_gender", message.get("gender", "unknown")),
        "first_name_vocative": message.get("first_name_vocative", ""),
        "trigger_title": trigger_title,
        "trigger_source": trigger_source,
    }

    result = generate_json(
        agent_name=f"FollowUpWriter_step{step_number}",
        prompt_path=prompt_path,
        user_payload=payload,
        context_files=context_files,
        relevant_context_keys=["01_offer", "03_messaging", "05_quality", "icp_tiers", "__icp_tier_active"],
    )

    if result and "body" in result:
        return result["body"], result.get("_llm_model_used", "unknown")
    return None, None


# ============================================================
# Heurystyczny fallback
# ============================================================

def _followup_heuristic(
    step_number: int,
    contact: dict,
    message: dict,
) -> str:
    """Heurystyczny fallback dla follow-upa — prosty tekst."""
    gender = message.get("recipient_gender", message.get("gender", "unknown"))
    vocative = message.get("first_name_vocative", "")
    company = contact.get("company", contact.get("company_name", ""))

    if gender == "female" and vocative:
        greeting = f"Dzień dobry Pani {vocative},"
        pan_form = "Pani"
    elif gender == "male" and vocative:
        greeting = f"Dzień dobry Panie {vocative},"
        pan_form = "Pana"
    else:
        greeting = "Dzień dobry,"
        pan_form = ""

    if step_number == 2:
        if pan_form:
            body = (
                f"{greeting}\n\n"
                f"wracam z krótką myślą w kontekście przygotowania negocjacji z dostawcami "
                f"w {company}.\n\n"
                f"W takich sytuacjach pomagamy ocenić, czy warunki zakupowe są optymalne "
                f"i gdzie jest przestrzeń do obniżki kosztów.\n\n"
                f"Jeśli temat jest dla {pan_form} aktualny, proszę wybrać dogodny termin "
                f"tutaj: [link do Calendly].\n"
                f"Można też po prostu odpisać \u201eTAK\u201d i podać numer telefonu "
                f"\u2014 oddzwonię."
            )
        else:
            body = (
                f"{greeting}\n\n"
                f"wracam z krótką myślą w kontekście przygotowania negocjacji z dostawcami "
                f"w {company}.\n\n"
                f"W takich sytuacjach pomagamy ocenić, czy warunki zakupowe są optymalne "
                f"i gdzie jest przestrzeń do obniżki kosztów.\n\n"
                f"Jeśli temat jest aktualny, proszę wybrać dogodny termin "
                f"tutaj: [link do Calendly].\n"
                f"Można też po prostu odpisać \u201eTAK\u201d i podać numer telefonu "
                f"\u2014 oddzwonię."
            )
    else:  # step_number == 3
        if pan_form:
            body = (
                f"{greeting}\n\n"
                f"wracam ostatni raz w temacie warunków zakupowych w {company}.\n\n"
                f"Pomagamy przełożyć dane rynkowe na konkretną argumentację negocjacyjną "
                f"z dostawcami — tak aby chronić marżę i ograniczać nieuzasadnione podwyżki.\n\n"
                f"Jeśli temat jest dla {pan_form} aktualny, proszę wybrać dogodny termin "
                f"tutaj: [link do Calendly].\n"
                f"Można też po prostu odpisać \u201eTAK\u201d i podać numer telefonu "
                f"\u2014 oddzwonię."
            )
        else:
            body = (
                f"{greeting}\n\n"
                f"wracam ostatni raz w temacie warunków zakupowych w {company}.\n\n"
                f"Pomagamy przełożyć dane rynkowe na konkretną argumentację negocjacyjną "
                f"z dostawcami — tak aby chronić marżę i ograniczać nieuzasadnione podwyżki.\n\n"
                f"Jeśli temat jest aktualny, proszę wybrać dogodny termin "
                f"tutaj: [link do Calendly].\n"
                f"Można też po prostu odpisać \u201eTAK\u201d i podać numer telefonu "
                f"\u2014 oddzwonię."
            )

    return body


def generate_followup(
    step_number: int,
    original_subject: str,
    original_body_clean: str,
    previous_followup_body: str,
    contact: dict,
    message: dict,
    context_files: dict | None = None,
    base_dir: str = "",
    trigger_title: str = "",
    trigger_source: str = "",
) -> dict:
    """
    Generuje follow-up: próbuje LLM, fallback na heurystykę.

    Returns:
        dict z: body (core, bez podpisu), llm_used, fallback_used, _llm_model_used
    """
    body, model_used = generate_followup_body(
        step_number=step_number,
        original_subject=original_subject,
        original_body_clean=original_body_clean,
        previous_followup_body=previous_followup_body,
        contact=contact,
        message=message,
        context_files=context_files,
        base_dir=base_dir,
        trigger_title=trigger_title,
        trigger_source=trigger_source,
    )

    if body:
        return {"body": body, "llm_used": True, "fallback_used": False, "_llm_model_used": model_used}

    # Heurystyczny fallback
    body = _followup_heuristic(step_number, contact, message)
    return {"body": body, "llm_used": False, "fallback_used": True}
