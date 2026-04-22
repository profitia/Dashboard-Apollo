#!/usr/bin/env python3
"""
AI Outreach System — Draft Pipeline
Profitia / SpendGuru

Tryb DRAFT: CSV → scoring → research → hipoteza → wiadomość → QA → output.
Agenty Hypothesis, Message Writer i QA mogą korzystać z LLM API (OpenAI).
Jeśli LLM niedostępny — automatyczny fallback do heurystyk.
Bez integracji z Apollo. Bez wysyłki maili.
"""

import argparse
import csv
import json
import os
import glob
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Dodaj src/ do path żeby zaimportować core
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from core.polish_names import resolve_polish_contact, get_polish_name_data
from core.email_signature import (
    SIGNATURE_PLAIN,
    SIGNATURE_HTML,
    META_BLOCK,
    FONT_BASE as _FONT_BASE,
    FONT_LINK as _FONT_LINK,
    body_to_html as _body_to_html,
    append_signature as _append_signature,
    strip_signature as _strip_signature,
)
from core.email_thread_formatter import build_outreach_pack, build_email_1
from core.followup_generator import generate_followup
from core.icp_tier_resolver import resolve_tier, get_tier_prompt_context
from core.campaign_name_builder import build_campaign_metadata
from core.contact_campaign_history import update_contact_campaign_history, enrich_contact_output
from core.apollo_campaign_sync import build_apollo_sync_payload, sync_outreach_pack_to_apollo
from core.weekly_sequence_orchestrator import run_weekly_sequence, generate_sequence_name
from core.contact_engagement_tracker import record_campaign_batch
from core.apollo_contact_enrichment import enrich_contact_name_fields, build_safe_greeting
from core.tier_alignment import tier_alignment_check
from core.rich_contact_profile import (
    build_rich_profile,
    save_or_merge_rich_profile,
    build_llm_context as build_rich_llm_context,
)

# Backward-compatible aliases (used by send_followup_test.py, simulate_article_sequence.py)
EMAIL_SIGNATURE_PLAIN = SIGNATURE_PLAIN
EMAIL_SIGNATURE_HTML = SIGNATURE_HTML

# --- dotenv ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- YAML loading ---
try:
    import yaml
except ImportError:
    print("BŁĄD: PyYAML nie jest zainstalowany. Uruchom: pip install pyyaml")
    sys.exit(1)

# --- LLM client ---
try:
    from llm_client import generate_json, is_llm_available
except ImportError:
    def generate_json(*args, **kwargs):
        return None
    def is_llm_available():
        return False


# ============================================================
# Helpers
# ============================================================

def load_config(config_path: str) -> dict:
    """Wczytuje YAML config kampanii."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_csv(csv_path: str) -> list[dict]:
    """Wczytuje CSV z danymi wejściowymi."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_context_files(base_dir: str) -> dict[str, str]:
    """Wczytuje pliki kontekstowe *.md z katalogu głównego projektu + source_of_truth."""
    context = {}
    patterns = [
        os.path.join(base_dir, "[0-9][0-9]_*.md"),
        os.path.join(base_dir, "context", "[0-9][0-9]_*.md"),
    ]
    for pattern in patterns:
        for filepath in sorted(glob.glob(pattern)):
            name = os.path.basename(filepath)
            if name not in context:
                with open(filepath, "r", encoding="utf-8") as f:
                    context[name] = f.read()

    # Dołącz icp_tiers.yaml i global_campaign_rules.md
    sot_tiers = os.path.join(base_dir, "source_of_truth", "icp_tiers.yaml")
    if os.path.exists(sot_tiers):
        with open(sot_tiers, "r", encoding="utf-8") as f:
            context["icp_tiers.yaml"] = f.read()

    rules_path = os.path.join(base_dir, "src", "config", "global_campaign_rules.md")
    if os.path.exists(rules_path):
        with open(rules_path, "r", encoding="utf-8") as f:
            context["global_campaign_rules.md"] = f.read()

    policy_path = os.path.join(base_dir, "src", "config", "model_policy.md")
    if os.path.exists(policy_path):
        with open(policy_path, "r", encoding="utf-8") as f:
            context["model_policy.md"] = f.read()

    return context


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


# ============================================================
# Zakazane frazy (z 05_quality_rules.md)
# ============================================================

FORBIDDEN_PHRASES = [
    "innowacyjne rozwiązanie",
    "kompleksowa platforma",
    "synergia",
    "rewolucja w zakupach",
    "transformacja procurement",
    "game changer",
    "w dzisiejszych dynamicznych czasach",
    "zoptymalizujemy państwa procesy",
    "gwarantujemy oszczędności",
    "wiemy, że macie problem",
    "na pewno przepłacacie",
    "chciałbym zaprezentować demo",
    "chciałbym przedstawić naszą ofertę",
    "nasze ai automatyzuje negocjacje",
    "szybkie demo naszej platformy",
    "oferta współpracy",
    "zwiększ oszczędności już dziś",
    "kompleksowe rozwiązanie",
    "innowacyjne podejście",
    "w dynamicznie zmieniającym się otoczeniu",
    "optymalizacja procesów",
]

# ============================================================
# Mapowania person
# ============================================================

TITLE_TO_PERSONA = {
    "dyrektor zakupów": "cpo",
    "head of procurement": "cpo",
    "procurement director": "cpo",
    "purchasing director": "cpo",
    "cpo": "cpo",
    "chief procurement officer": "cpo",
    "kupiec": "buyer",
    "category manager": "buyer",
    "senior buyer": "buyer",
    "sourcing manager": "buyer",
    "procurement manager": "buyer",
    "cfo": "cfo",
    "finance director": "cfo",
    "controlling manager": "cfo",
    "dyrektor finansowy": "cfo",
    "ceo": "ceo",
    "prezes": "ceo",
    "owner": "ceo",
    "właściciel": "ceo",
    "supply chain manager": "supply_chain",
    "supply chain director": "supply_chain",
    "head of supply chain": "supply_chain",
    "vp supply chain": "supply_chain",
    "logistics manager": "supply_chain",
    "operations manager": "supply_chain",
}

PERSONA_VOCATIVES = {
    "cpo": {"M": "Panie Dyrektorze", "K": "Pani Dyrektor"},
    "buyer": {"M": "Panie", "K": "Pani"},
    "cfo": {"M": "Panie Dyrektorze", "K": "Pani Dyrektor"},
    "ceo": {"M": "Panie Prezesie", "K": "Pani Prezes"},
    "supply_chain": {"M": "Panie", "K": "Pani"},
}

# Proste dopasowanie płci na podstawie imienia — legacy fallback
FEMALE_ENDINGS = ("a",)  # w polskim — uproszczenie


def guess_gender(first_name: str) -> str:
    """
    Płeć kontaktu. Priorytet: CSV (context/Vocative names od VSC.csv),
    fallback: heurystyka końcówki.
    Zwraca 'K' (kobieta) lub 'M' (mężczyzna) — format wewnętrzny article_triggered.
    """
    data = get_polish_name_data(first_name)
    if data:
        return "K" if data["gender"] == "female" else "M"
    # Legacy fallback
    if first_name and first_name.strip().lower().endswith(FEMALE_ENDINGS):
        return "K"
    return "M"


# ============================================================
# Agent 1: Lead Scoring (heurystyka)
# ============================================================

def agent_lead_scoring(row: dict, config: dict) -> dict:
    """Heurystyczny scoring leada na podstawie danych z CSV."""
    score = 0
    details = {}

    # ICP fit (20) — PL + industry known
    icp = 0
    if row.get("country", "").upper() == "PL":
        icp += 10
    if row.get("industry", "").strip():
        icp += 10
    details["icp_fit"] = icp
    score += icp

    # Persona fit (20)
    title_lower = row.get("contact_title", "").lower().strip()
    target = config.get("target_persona", "cpo")
    matched_persona = TITLE_TO_PERSONA.get(title_lower)
    persona_score = 20 if matched_persona == target else (10 if matched_persona else 0)
    details["persona_fit"] = persona_score
    score += persona_score

    # Seniority (15)
    senior_keywords = ["director", "dyrektor", "head", "cpo", "cfo", "ceo", "vp", "prezes"]
    seniority = 15 if any(kw in title_lower for kw in senior_keywords) else 8
    details["seniority"] = seniority
    score += seniority

    # Trigger strength (15) — notes present?
    trigger = 15 if row.get("notes", "").strip() else 5
    details["trigger_strength"] = trigger
    score += trigger

    # Business case potential (10)
    biz = 8 if row.get("notes", "").strip() else 4
    details["business_case_potential"] = biz
    score += biz

    # Data quality (10) — email placeholder? name present?
    dq = 0
    if row.get("contact_first_name", "").strip():
        dq += 5
    if row.get("contact_last_name", "").strip():
        dq += 5
    details["data_quality"] = dq
    score += dq

    # Industry fit (5)
    ind = 5 if row.get("industry", "").strip() else 0
    details["industry_fit"] = ind
    score += ind

    # Context availability (5)
    ctx = 5 if row.get("notes", "").strip() else 0
    details["context_availability"] = ctx
    score += ctx

    # Decision
    if score >= 85:
        decision = "deep_personalization"
    elif score >= 70:
        decision = "standard_personalization"
    elif score >= 50:
        decision = "light_personalization"
    else:
        decision = "reject"

    return {
        "lead_score": score,
        "scoring_details": details,
        "decision": decision,
    }


# ============================================================
# Agent 2: Account Research (heurystyka z CSV)
# ============================================================

def agent_account_research(row: dict) -> dict:
    """Generuje krótki research brief na podstawie danych z CSV."""
    company = row.get("company_name", "Nieznana firma")
    industry = row.get("industry", "nieokreślona")
    country = row.get("country", "")
    notes = row.get("notes", "")

    summary = f"{company} — firma z branży {industry.lower()}"
    if country:
        summary += f", {country}"
    summary += "."

    signals = []
    facts = []
    hypotheses = []

    if notes:
        signals.append(notes)
        facts.append(f"Notatka: {notes}")
        hypotheses.append(
            f"Sytuacja opisana w notatkach ({notes.lower()}) może mieć wpływ "
            f"na przygotowanie negocjacji zakupowych."
        )

    trigger = notes if notes else "brak twardego triggera"

    return {
        "company_summary": summary,
        "business_signals": signals if signals else ["Brak dodatkowych sygnałów — dane ograniczone do CSV."],
        "potential_trigger": trigger,
        "procurement_implications": (
            f"W firmie z branży {industry.lower()} mogą istnieć kategorie zakupowe, "
            "w których warto zweryfikować warunki dostawców."
        ),
        "confidence_level": "low" if not notes else "medium",
        "facts_vs_hypotheses": {
            "facts": facts if facts else ["Brak potwierdzonych faktów poza danymi z CSV."],
            "hypotheses": hypotheses if hypotheses else ["Brak wystarczających danych do hipotezy."],
        },
    }


# ============================================================
# Agent 3: Persona Selection (heurystyka)
# ============================================================

def agent_persona_selection(row: dict) -> dict:
    """Przypisuje persona_type na podstawie contact_title."""
    title_lower = row.get("contact_title", "").lower().strip()
    persona = TITLE_TO_PERSONA.get(title_lower)

    if persona:
        return {
            "persona_type": persona,
            "confidence": "high",
            "reasoning": f"Tytuł '{row.get('contact_title', '')}' odpowiada personie {persona}.",
            "fallback_persona": None,
        }

    # Partial match
    for key, val in TITLE_TO_PERSONA.items():
        if key in title_lower or title_lower in key:
            return {
                "persona_type": val,
                "confidence": "medium",
                "reasoning": f"Częściowe dopasowanie tytułu '{row.get('contact_title', '')}' → {val}.",
                "fallback_persona": None,
            }

    return {
        "persona_type": "unknown",
        "confidence": "low",
        "reasoning": f"Tytuł '{row.get('contact_title', '')}' nie pasuje do żadnej znanej persony.",
        "fallback_persona": "cpo",
    }


# ============================================================
# Agent 4: Hypothesis (heurystyka)
# ============================================================

HYPOTHESIS_TEMPLATES = {
    "cpo": (
        "Przy rosnącej liczbie kategorii i dostawców może pojawić się pytanie, "
        "czy każdy kupiec przygotowuje negocjacje według spójnej logiki "
        "i na podstawie porównywalnych danych."
    ),
    "buyer": (
        "Przy kolejnych rundach negocjacji z dostawcami warto sprawdzić, "
        "czy obecne warunki nadal odzwierciedlają aktualne realia kosztowe "
        "i czy argumentacja opiera się na twardych danych."
    ),
    "cfo": (
        "Przy rosnącej presji kosztowej może być dobry moment, "
        "żeby zweryfikować, na ile zakupy realnie chronią marżę "
        "i czy podwyżki dostawców są zasadne."
    ),
    "ceo": (
        "W firmach o podobnej skali często pojawia się pytanie, "
        "czy koszty zakupowe są pod wystarczającą kontrolą "
        "i czy podwyżki dostawców mają uzasadnienie."
    ),
    "supply_chain": (
        "Przy złożonym łańcuchu dostaw warto sprawdzić, "
        "czy decyzje zakupowe uwzględniają pełny koszt posiadania "
        "i timing kontraktów."
    ),
}


def _hypothesis_heuristic(research: dict, persona: dict, row: dict) -> dict:
    """Heurystyczny fallback dla hipotezy."""
    persona_type = persona.get("persona_type", "cpo")
    notes = row.get("notes", "")

    base = HYPOTHESIS_TEMPLATES.get(persona_type, HYPOTHESIS_TEMPLATES["cpo"])

    if notes:
        hypothesis = (
            f"W kontekście: {notes.lower()} — {base[0].lower()}{base[1:]}"
        )
        trigger_used = "notes_context"
    else:
        hypothesis = base
        trigger_used = "generic_persona"

    return {
        "hypothesis": hypothesis,
        "trigger_used": trigger_used,
        "hypothesis_type": "observation",
        "confidence": "medium" if notes else "low",
        "risk_level": "low",
        "llm_used": False,
        "fallback_used": True,
    }


def agent_hypothesis(research: dict, persona: dict, row: dict,
                     context_files: dict | None = None, base_dir: str = "") -> dict:
    """Buduje ostrożną hipotezę biznesową. Próbuje LLM, fallback na heurystykę."""
    if is_llm_available():
        prompt_path = os.path.join(base_dir, "prompts", "shared", "hypothesis.md")
        payload = {
            "account_research": research,
            "persona_type": persona.get("persona_type", "cpo"),
            "industry": row.get("industry", ""),
            "notes": row.get("notes", ""),
            "company_name": row.get("company_name", ""),
        }
        result = generate_json(
            agent_name="Hypothesis",
            prompt_path=prompt_path,
            user_payload=payload,
            context_files=context_files,
            relevant_context_keys=["01_offer", "02_personas", "03_messaging", "icp_tiers", "__icp_tier_active"],
        )
        if result and "hypothesis" in result:
            result["llm_used"] = True
            result["fallback_used"] = False
            return result

    return _hypothesis_heuristic(research, persona, row)


# ============================================================
# Email signature — delegated to src/core/email_signature.py
# Backward-compatible exports defined in imports above.
# ============================================================


# ============================================================
# Agent 5: Message Writer (heurystyka / szablony)
# ============================================================

CTA_TEMPLATES = {
    "cpo": "Czy ma sens krótka rozmowa o tym, jak wygląda przygotowanie negocjacji w jednej wybranej kategorii?",
    "buyer": "Czy warto porozmawiać o jednej kategorii, w której chciałby Pan/Pani sprawdzić zasadność obecnych warunków?",
    "cfo": "Czy ma sens krótka rozmowa o wpływie zakupów na przewidywalność kosztów?",
    "ceo": "Czy warto poświęcić 15 minut na rozmowę o kontroli kosztów zakupowych?",
    "supply_chain": "Czy ma sens krótka rozmowa o jednym elemencie łańcucha dostaw, który warto zweryfikować?",
}

PROOF_TEMPLATES = {
    "cpo": "W podobnych projektach zwykle zaczynamy od jednej kategorii — żeby zobaczyć, czy dane potwierdzają hipotezę.",
    "buyer": "W praktyce często wystarczy spojrzeć na jedną ofertę dostawcy, żeby ocenić, czy warunki są fair.",
    "cfo": "W firmach o podobnej skali często okazuje się, że nawet kilka kategorii zakupowych ma istotny wpływ na wynik.",
    "ceo": "W firmach o podobnym profilu często widzimy, że przegląd kilku kluczowych kategorii daje szybki obraz sytuacji.",
    "supply_chain": "W praktyce warto zacząć od jednego elementu łańcucha, żeby zobaczyć, gdzie jest największy potencjał.",
}


def _message_writer_heuristic(
    row: dict, research: dict, persona: dict, hypothesis: dict, config: dict
) -> dict:
    """Heurystyczny fallback dla message writera."""
    persona_type = persona.get("persona_type", "cpo")
    first_name = row.get("contact_first_name", "").strip()
    notes = row.get("notes", "")
    max_words = config.get("message", {}).get("max_words", 120)

    # Resolve gender/vocative z CSV
    pl = resolve_polish_contact(first_name)
    gender = pl["gender"]
    vocative = pl["first_name_vocative"]
    greeting = pl["greeting"]

    if notes:
        opener = f"Widziałem informację o: {notes.lower()} — "
    else:
        opener = "Piszę z krótką hipotezą dotyczącą przygotowania negocjacji zakupowych w firmach o podobnej skali. "

    hyp_text = hypothesis.get("hypothesis", "")
    proof = PROOF_TEMPLATES.get(persona_type, PROOF_TEMPLATES["cpo"])
    cta = CTA_TEMPLATES.get(persona_type, CTA_TEMPLATES["cpo"])

    subject = "Pytanie o przygotowanie negocjacji"
    company_name = row.get("company_name", "")
    if persona_type == "buyer":
        subject = "Jedna kategoria / jeden dostawca"
    elif persona_type == "cfo":
        subject = "Pytanie o przewidywalność kosztów zakupowych"
    elif persona_type == "ceo":
        subject = "Pytanie o kontrolę kosztów zakupowych"
    if company_name:
        subject = f"{subject} — {company_name}"

    body_parts = [
        greeting,
        "",
        opener.strip(),
        "",
        hyp_text,
        "",
        proof,
        "",
        cta,
    ]
    body = "\n".join(body_parts)
    word_count = len(body.split())

    return {
        "subject": subject,
        "body": body,
        "recipient_gender": gender,
        "first_name_vocative": vocative,
        "greeting": greeting,
        "word_count": word_count,
        "language": config.get("language_code", "pl"),
        "llm_used": False,
        "fallback_used": True,
    }


def agent_message_writer(
    row: dict, research: dict, persona: dict, hypothesis: dict, config: dict,
    context_files: dict | None = None, base_dir: str = ""
) -> dict:
    """Generuje pierwszy email. Próbuje LLM, fallback na heurystykę."""
    # Resolve gender/vocative z CSV dla payloadu LLM
    first_name = row.get("contact_first_name", "").strip()
    pl = resolve_polish_contact(first_name)

    if is_llm_available():
        prompt_path = os.path.join(base_dir, "prompts", "shared", "message_writer.md")
        payload = {
            "persona_type": persona.get("persona_type", "cpo"),
            "hypothesis": hypothesis.get("hypothesis", ""),
            "trigger": hypothesis.get("trigger_used", ""),
            "account_research": research,
            "contact_first_name": row.get("contact_first_name", ""),
            "contact_title": row.get("contact_title", ""),
            "company_name": row.get("company_name", ""),
            "industry": row.get("industry", ""),
            "notes": row.get("notes", ""),
            "language": config.get("language_code", "pl"),
            "max_words": config.get("message", {}).get("max_words", 120),
            "style": config.get("message", {}).get("style", "concise_consultative"),
            # Dane znormalizowane z CSV — LLM nie musi zgadywać
            "gender": pl["gender"],
            "first_name_vocative": pl["first_name_vocative"],
            "greeting": pl["greeting"],
        }
        result = generate_json(
            agent_name="MessageWriter",
            prompt_path=prompt_path,
            user_payload=payload,
            context_files=context_files,
            relevant_context_keys=["01_offer", "02_personas", "03_messaging", "05_quality", "icp_tiers", "__icp_tier_active"],
        )
        if result and "body" in result:
            result["llm_used"] = True
            result["fallback_used"] = False
            if "word_count" not in result:
                result["word_count"] = len(result["body"].split())
            if "language" not in result:
                result["language"] = config.get("language_code", "pl")
            # Nadpisz gender/vocative z CSV (bardziej wiarygodne niż LLM)
            result["recipient_gender"] = pl["gender"]
            result["first_name_vocative"] = pl["first_name_vocative"]
            result["greeting"] = pl["greeting"]
            # Dodaj nazwę firmy do subject jeśli brak
            company_name = row.get("company_name", "")
            if company_name and company_name not in result.get("subject", ""):
                result["subject"] = f"{result['subject']} — {company_name}"
            return _append_signature(result)

    return _append_signature(_message_writer_heuristic(row, research, persona, hypothesis, config))


# ============================================================
# Agent 6: QA Reviewer (heurystyka)
# ============================================================

def _qa_reviewer_heuristic(message: dict, persona: dict, hypothesis: dict, config: dict) -> dict:
    """Heurystyczny fallback QA — ocenia jakość wiadomości."""
    score = 0
    strengths = []
    issues = []
    required_changes = []

    body = message.get("body", "")
    body_lower = body.lower()
    word_count = message.get("word_count", 0)
    max_words = config.get("message", {}).get("max_words", 120)
    persona_type = persona.get("persona_type", "unknown")

    # Persona fit (15)
    if persona_type != "unknown":
        score += 15
        strengths.append("Persona przypisana")
    else:
        issues.append("Brak dopasowanej persony")

    # Trigger / powód kontaktu (15)
    if hypothesis.get("trigger_used") != "generic_persona":
        score += 15
        strengths.append("Trigger obecny")
    else:
        score += 8
        issues.append("Brak twardego triggera — użyty neutralny opener")

    # Hypothesis quality (15)
    if hypothesis.get("hypothesis"):
        score += 13
        strengths.append("Hipoteza obecna")
    else:
        issues.append("Brak hipotezy")

    # Naturalność — brak zakazanych fraz (15)
    forbidden_found = [p for p in FORBIDDEN_PHRASES if p in body_lower]
    if not forbidden_found:
        score += 15
        strengths.append("Brak zakazanych fraz")
    else:
        score += 5
        issues.append(f"Zakazane frazy: {', '.join(forbidden_found)}")
        required_changes.append("Usuń zakazane frazy")

    # Zwięzłość (10)
    if word_count <= max_words:
        score += 10
        strengths.append(f"Dobra długość ({word_count} słów)")
    elif word_count <= max_words * 1.25:
        score += 6
        issues.append(f"Lekko za długa ({word_count} słów, max {max_words})")
        required_changes.append("Skróć wiadomość")
    else:
        score += 2
        issues.append(f"Za długa ({word_count} słów, max {max_words})")
        required_changes.append("Znacznie skróć wiadomość")

    # CTA (10)
    cta_phrases = ["rozmow", "porozmawiać", "sprawdzić", "sens", "warto",
                    "calendly", "termin", "odpisać", "oddzwonię", "oddzwoni"]
    if any(p in body_lower for p in cta_phrases):
        score += 10
        strengths.append("CTA obecne")
    else:
        score += 3
        issues.append("Brak wyraźnego CTA")
        required_changes.append("Dodaj CTA")

    # Wiarygodność (10) — brak podejrzanych twierdzeń
    score += 10
    strengths.append("Brak halucynacji (heurystyka)")

    # Brak generycznego języka (5)
    generic_phrases = ["dynamicznie", "innowacyjn", "kompleksow", "synergi"]
    if not any(p in body_lower for p in generic_phrases):
        score += 5
    else:
        issues.append("Generyczny język")

    # Brak pitchowania (5)
    first_line = body.split("\n")[2] if len(body.split("\n")) > 2 else ""
    product_words = ["spendguru", "profitia", "platforma", "demo", "moduł"]
    if not any(pw in first_line.lower() for pw in product_words):
        score += 5
    else:
        issues.append("Produkt pojawia się za wcześnie")
        required_changes.append("Przenieś produkt dalej w wiadomości")

    # Decision
    if score >= 85:
        decision = "approve"
        recommendation = "approved_for_sequence"
    elif score >= 70:
        decision = "rewrite"
        recommendation = "rewrite_before_sequence"
    elif score >= 50:
        decision = "manual_review"
        recommendation = "needs_manual_review"
    else:
        decision = "reject"
        recommendation = "do_not_send"

    # Risk
    risk = "low"
    if decision == "reject":
        risk = "high"
    elif decision in ("rewrite", "manual_review"):
        risk = "medium"

    return {
        "qa_score": score,
        "decision": decision,
        "risk_level": risk,
        "strengths": strengths,
        "issues": issues,
        "required_changes": required_changes,
        "final_recommendation": recommendation,
        "llm_used": False,
        "fallback_used": True,
    }


def agent_qa_reviewer(message: dict, persona: dict, hypothesis: dict, config: dict,
                      context_files: dict | None = None, base_dir: str = "") -> dict:
    """QA wiadomości. Próbuje LLM, fallback na heurystykę."""
    if is_llm_available():
        prompt_path = os.path.join(base_dir, "prompts", "shared", "qa_reviewer.md")
        payload = {
            "subject": message.get("subject", ""),
            "body": message.get("body", ""),
            "word_count": message.get("word_count", 0),
            "persona_type": persona.get("persona_type", "unknown"),
            "hypothesis": hypothesis.get("hypothesis", ""),
            "max_words": config.get("message", {}).get("max_words", 120),
            "language": config.get("language_code", "pl"),
        }
        result = generate_json(
            agent_name="QAReviewer",
            prompt_path=prompt_path,
            user_payload=payload,
            context_files=context_files,
            relevant_context_keys=["03_messaging", "05_quality", "icp_tiers", "__icp_tier_active"],
        )
        if result and "qa_score" in result and "decision" in result:
            result["llm_used"] = True
            result["fallback_used"] = False
            # Upewnij się, że wymagane pola istnieją
            result.setdefault("risk_level", "low")
            result.setdefault("strengths", [])
            result.setdefault("issues", [])
            result.setdefault("required_changes", [])
            result.setdefault("final_recommendation", result["decision"])
            return result

    return _qa_reviewer_heuristic(message, persona, hypothesis, config)


# ============================================================
# Agent 7: Apollo Fields (heurystyka)
# ============================================================

def agent_apollo_fields(
    row: dict, message: dict, persona: dict, hypothesis: dict,
    scoring: dict, qa: dict, config: dict
) -> dict:
    """Przygotowuje custom fields gotowe do Apollo."""
    body = message.get("body", "")
    lines = [l.strip() for l in body.split("\n") if l.strip()]

    # Wyciągnij fragmenty wiadomości
    opener = lines[1] if len(lines) > 1 else ""
    hyp = hypothesis.get("hypothesis", "")
    persona_type = persona.get("persona_type", "cpo")

    cta_text = ""
    for line in lines:
        if any(w in line.lower() for w in ["sens", "rozmow", "warto", "sprawdzić"]):
            cta_text = line
            break

    proof_text = ""
    for line in lines:
        if any(w in line.lower() for w in ["zwykle", "praktyce", "często", "okazuje"]):
            proof_text = line
            break

    return {
        "custom_subject_1": message.get("subject", ""),
        "custom_opener_1": opener,
        "custom_problem_hypothesis_1": hyp,
        "custom_proof_1": proof_text,
        "custom_cta_1": cta_text,
        "persona_type": persona_type,
        "trigger_type": hypothesis.get("trigger_used", ""),
        "trigger_summary": row.get("notes", ""),
        "campaign_name": config.get("campaign_name", ""),
        "language_code": config.get("language_code", "pl"),
        "sequence_recommendation": config.get("routing", {}).get("default_sequence", ""),
        "mailbox_group": config.get("routing", {}).get("default_mailbox_group", ""),
        "lead_score": scoring.get("lead_score", 0),
        "qa_score": qa.get("qa_score", 0),
        "risk_level": qa.get("risk_level", "low"),
    }


# ============================================================
# Agent 8: Sequence Router (heurystyka)
# ============================================================

SEQUENCE_TABLE = {
    ("cpo", "pl", "standard"): "PL_CPO_MEETING_STD",
    ("buyer", "pl", "standard"): "PL_BUYER_MEETING_STD",
    ("cpo", "pl", "strategic"): "PL_NAMED_ACCOUNT_SOFT",
    ("cpo", "en", "standard"): "EN_CPO_MEETING_STD",
    ("cfo", "pl", "standard"): "PL_EXEC_MARGIN_MEETING",
    ("ceo", "pl", "standard"): "PL_EXEC_MARGIN_MEETING",
    ("supply_chain", "pl", "standard"): "PL_SUPPLY_CHAIN_TCO",
}

MAILBOX_TABLE = {
    "PL_CPO_MEETING_STD": "pl_sales_primary",
    "PL_BUYER_MEETING_STD": "pl_sales_primary",
    "PL_NAMED_ACCOUNT_SOFT": "named_accounts",
    "EN_CPO_MEETING_STD": "en_sales",
    "PL_EXEC_MARGIN_MEETING": "pl_sales_primary",
    "PL_SUPPLY_CHAIN_TCO": "pl_sales_primary",
}


def agent_sequence_router(persona: dict, config: dict) -> dict:
    """Przypisuje sekwencję i mailbox."""
    persona_type = persona.get("persona_type", "cpo")
    lang = config.get("language_code", "pl")
    priority = "standard"  # MVP — zawsze standard

    key = (persona_type, lang, priority)
    sequence = SEQUENCE_TABLE.get(key, config.get("routing", {}).get("default_sequence", "PL_CPO_MEETING_STD"))
    mailbox = MAILBOX_TABLE.get(sequence, config.get("routing", {}).get("default_mailbox_group", "pl_sales_primary"))
    manual = priority == "strategic"

    return {
        "sequence_recommendation": sequence,
        "mailbox_group": mailbox,
        "manual_review_required": manual or config.get("quality", {}).get("manual_review_required", False),
        "reasoning": f"{persona_type} + {lang} + {priority} → {sequence}",
    }


# ============================================================
# Pipeline
# ============================================================

def run_pipeline(row: dict, config: dict, context_files: dict | None = None,
                 base_dir: str = "") -> dict:
    """Uruchamia pełny pipeline dla jednego kontaktu, w tym follow-upy i outreach pack."""
    scoring = agent_lead_scoring(row, config)
    research = agent_account_research(row)
    persona = agent_persona_selection(row)

    # ICP Tier detection (przed hipotezą i message writerem)
    contact_title = row.get("contact_title", "")
    tier_info = resolve_tier(contact_title)

    # Dodaj tier prompt context do context_files (tymczasowa kopia)
    enriched_context = dict(context_files) if context_files else {}
    tier_prompt = get_tier_prompt_context(tier_info["tier"])
    if tier_prompt:
        enriched_context["__icp_tier_active"] = tier_prompt

    hypothesis = agent_hypothesis(research, persona, row,
                                  context_files=enriched_context, base_dir=base_dir)
    message = agent_message_writer(row, research, persona, hypothesis, config,
                                   context_files=enriched_context, base_dir=base_dir)
    qa = agent_qa_reviewer(message, persona, hypothesis, config,
                           context_files=enriched_context, base_dir=base_dir)

    # Dodaj tier alignment info do QA report
    qa["tier_detected"] = tier_info["tier"]
    qa["tier_label"] = tier_info["tier_label"]

    fields = agent_apollo_fields(row, message, persona, hypothesis, scoring, qa, config)
    routing = agent_sequence_router(persona, config)

    # Resolve gender/vocative z CSV
    first_name = row.get("contact_first_name", "").strip()
    pl = resolve_polish_contact(first_name)

    contact_dict = {
        "first_name": row.get("contact_first_name", ""),
        "last_name": row.get("contact_last_name", ""),
        "title": row.get("contact_title", ""),
        "company": row.get("company_name", ""),
        "domain": row.get("company_domain", ""),
        "gender": pl["gender"],
        "vocative": pl["first_name_vocative"],
        "email": row.get("email", row.get("contact_email", "")),
        "job_title": row.get("contact_title", ""),
        "company_name": row.get("company_name", ""),
    }

    # Build and persist rich profile from row data
    try:
        rich = build_rich_profile(row)
        save_or_merge_rich_profile(rich)
        contact_dict["rich_profile"] = rich
    except Exception:
        pass

    # --- Name enrichment (deterministyczny, z source of truth) ---
    name_enrichment = enrich_contact_name_fields(
        contact_dict, write_to_apollo=False,
    )

    # --- Follow-upy + outreach pack ---
    email_1_body_core = _strip_signature(message.get("body", ""))
    email_1_subject = message.get("subject", "")
    trigger_title = hypothesis.get("trigger_used", "")
    trigger_source = row.get("notes", "")

    # Follow-up 1
    fu1_result = generate_followup(
        step_number=2,
        original_subject=email_1_subject,
        original_body_clean=email_1_body_core,
        previous_followup_body="",
        contact=contact_dict,
        message=message,
        context_files=enriched_context,
        base_dir=base_dir,
        trigger_title=trigger_title,
        trigger_source=trigger_source,
    )

    # Follow-up 2
    fu2_result = generate_followup(
        step_number=3,
        original_subject=email_1_subject,
        original_body_clean=email_1_body_core,
        previous_followup_body=fu1_result["body"],
        contact=contact_dict,
        message=message,
        context_files=enriched_context,
        base_dir=base_dir,
        trigger_title=trigger_title,
        trigger_source=trigger_source,
    )

    # Buduj outreach pack (thread-style formatting)
    today = datetime.now()
    outreach_pack = build_outreach_pack(
        email_1_subject=email_1_subject,
        email_1_body_core=email_1_body_core,
        follow_up_1_body_core=fu1_result["body"],
        follow_up_2_body_core=fu2_result["body"],
        contact=contact_dict,
        date_email_1=today.strftime("%d.%m.%Y"),
        date_follow_up_1=(today + timedelta(days=2)).strftime("%d.%m.%Y"),
        date_follow_up_2=(today + timedelta(days=5)).strftime("%d.%m.%Y"),
    )

    # Tier alignment check (heuristic, non-blocking)
    tier_alignment = tier_alignment_check(
        tier_info,
        [email_1_body_core, fu1_result["body"], fu2_result["body"]],
    )
    if tier_alignment.get("requires_review"):
        qa.setdefault("requires_review", False)
        qa["requires_review"] = True
        qa.setdefault("tier_alignment_comments", [])
        qa["tier_alignment_comments"] = tier_alignment["comments"]

    return {
        "contact": contact_dict,
        "lead_scoring": scoring,
        "account_research": research,
        "persona_selection": persona,
        "icp_tier": tier_info,
        "hypothesis": hypothesis,
        "message": message,
        "qa": qa,
        "apollo_fields": fields,
        "routing": routing,
        "outreach_pack": outreach_pack,
        "name_enrichment": name_enrichment,
        "tier_alignment": tier_alignment,
        "followup_meta": {
            "follow_up_1_llm_used": fu1_result["llm_used"],
            "follow_up_2_llm_used": fu2_result["llm_used"],
        },
    }


# ============================================================
# Output writers
# ============================================================

def write_json(filepath: str, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv_rows(filepath: str, rows: list[dict]):
    if not rows:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("")
        return
    fieldnames = rows[0].keys()
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_run_report(
    config: dict, results: list[dict], context_files: dict, run_dir: str
) -> str:
    """Generuje raport kampanii w formacie Markdown."""
    total = len(results)
    approved = [r for r in results if r["qa"]["decision"] == "approve"]
    rewrite = [r for r in results if r["qa"]["decision"] == "rewrite"]
    manual = [r for r in results if r["qa"]["decision"] == "manual_review"]
    rejected = [r for r in results if r["qa"]["decision"] == "reject"]

    avg_lead = sum(r["lead_scoring"]["lead_score"] for r in results) / total if total else 0
    avg_qa = sum(r["qa"]["qa_score"] for r in results) / total if total else 0

    # Zbierz powody odrzuceń
    all_issues = []
    for r in results:
        all_issues.extend(r["qa"]["issues"])

    # Kontekst
    ctx_status = "Załadowano" if context_files else "BRAK — pliki kontekstowe nie zostały znalezione"
    ctx_list = ", ".join(sorted(context_files.keys())) if context_files else "brak"

    report = f"""# Run Report

## Campaign
- **Nazwa**: {config.get('campaign_name', 'unknown')}
- **Campaign Name (standard)**: {campaign_metadata.get('campaign_name', '')}
- **Język**: {config.get('language_code', 'pl')}
- **Persona**: {config.get('target_persona', 'unknown')}
- **Tryb**: {config.get('mode', 'draft')}
- **Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Campaign Metadata
- **Type**: {campaign_metadata.get('campaign_type', '')} ({campaign_metadata.get('campaign_type_reason', '')})
- **Tier**: {campaign_metadata.get('tier', '')} ({campaign_metadata.get('tier_reason', '')})
- **Segment**: {campaign_metadata.get('segment', '')} ({campaign_metadata.get('segment_reason', '')})
- **Angle**: {campaign_metadata.get('angle', '')} ({campaign_metadata.get('angle_reason', '')})
- **Market**: {campaign_metadata.get('market', '')} ({campaign_metadata.get('market_reason', '')})

## Pliki kontekstowe
- **Status**: {ctx_status}
- **Pliki**: {ctx_list}

## Input
- Liczba rekordów: {total}

## Results
| Status | Liczba |
|---|---:|
| Approved | {len(approved)} |
| Rewrite | {len(rewrite)} |
| Manual review | {len(manual)} |
| Rejected | {len(rejected)} |

## QA Summary
- Średni lead score: {avg_lead:.1f}
- Średni QA score: {avg_qa:.1f}

## Sequence Routing
"""
    # Policz routing
    seq_counts: dict[str, int] = {}
    for r in results:
        seq = r["routing"]["sequence_recommendation"]
        seq_counts[seq] = seq_counts.get(seq, 0) + 1
    for seq, count in sorted(seq_counts.items()):
        report += f"- {seq}: {count}\n"

    if all_issues:
        report += "\n## Issues\n"
        from collections import Counter
        for issue, cnt in Counter(all_issues).most_common(10):
            report += f"- {issue} ({cnt}x)\n"

    # LLM usage stats
    llm_hyp = sum(1 for r in results if r["hypothesis"].get("llm_used", False))
    llm_msg = sum(1 for r in results if r["message"].get("llm_used", False))
    llm_qa = sum(1 for r in results if r["qa"].get("llm_used", False))
    fb_hyp = sum(1 for r in results if r["hypothesis"].get("fallback_used", True))
    fb_msg = sum(1 for r in results if r["message"].get("fallback_used", True))
    fb_qa = sum(1 for r in results if r["qa"].get("fallback_used", True))

    report += f"""
## LLM Usage
| Agent | LLM | Fallback |
|---|---:|---:|
| Hypothesis | {llm_hyp} | {fb_hyp} |
| Message Writer | {llm_msg} | {fb_msg} |
| QA Reviewer | {llm_qa} | {fb_qa} |
"""

    if fb_hyp or fb_msg or fb_qa:
        report += "\n> **UWAGA**: Część agentów użyła fallback (heurystyki). "
        if not is_llm_available():
            report += "LLM nie był dostępny (brak klucza API lub brak konfiguracji w .env).\n"
        else:
            report += "LLM zwrócił błąd lub niepoprawny JSON dla niektórych kontaktów.\n"

    report += f"""
## Uwagi
- Tryb: **DRAFT** — żadne dane nie zostały zapisane do Apollo.
- Wyniki służą do walidacji pipeline'u, nie do wysyłki.

## Output
- Folder: `{run_dir}`
"""
    return report


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AI Outreach System — Draft Pipeline")
    parser.add_argument("--config", required=True, help="Ścieżka do YAML config kampanii")
    parser.add_argument("--mode", default="draft", choices=["draft", "prepare", "launch"],
                        help="Tryb uruchomienia (MVP: tylko draft)")
    args = parser.parse_args()

    # Walidacja trybu
    if args.mode != "draft":
        print(f"UWAGA: Tryb '{args.mode}' nie jest jeszcze zaimplementowany. Używam 'draft'.")
        args.mode = "draft"

    # Ścieżki
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, args.config)
    csv_path = os.path.join(base_dir, "data", "input_accounts.csv")

    # Wczytaj config
    print(f"[1/8] Wczytuję config: {args.config}")
    config = load_config(config_path)
    config["mode"] = args.mode

    # Wczytaj CSV
    print(f"[2/8] Wczytuję dane: data/input_accounts.csv")
    if not os.path.exists(csv_path):
        print(f"BŁĄD: Plik {csv_path} nie istnieje.")
        sys.exit(1)
    accounts = load_csv(csv_path)
    print(f"       Załadowano {len(accounts)} rekordów.")

    # Wczytaj context
    print("[3/8] Wczytuję pliki kontekstowe...")
    context_files = load_context_files(base_dir)
    if context_files:
        print(f"       Załadowano {len(context_files)} plików: {', '.join(sorted(context_files.keys()))}")
    else:
        print("       UWAGA: Nie znaleziono plików kontekstowych (*.md). Pipeline działa dalej.")

    # LLM status
    print("[4/8] Sprawdzam dostępność LLM...")
    if is_llm_available():
        from src.config.openai_client import get_config_summary
        _cfg = get_config_summary()
        print(f"       LLM AKTYWNY: provider={_cfg['provider']}, primary={_cfg['primary_model']}, fallback={_cfg['fallback_model']}, cheap={_cfg['cheap_model']}")
        print("       Agenty z LLM: Hypothesis, Message Writer, QA Reviewer")
    else:
        print("       LLM NIEAKTYWNY — pipeline użyje heurystyk (fallback).")
        provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        if provider == "github" and not os.getenv("GITHUB_TOKEN", "").strip():
            print("       Powód: brak GITHUB_TOKEN w .env")
        elif provider == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
            print("       Powód: brak OPENAI_API_KEY w .env")
        else:
            print("       Powód: brak LLM_PROVIDER w .env (ustaw 'openai' lub 'github')")

    # Campaign naming
    print("[5/10] Generuję campaign_name...")
    campaign_metadata = build_campaign_metadata(
        config=config,
        flow_name="run_campaign",
    )
    auto_campaign_name = campaign_metadata["campaign_name"]
    print(f"       campaign_name: {auto_campaign_name}")
    print(f"       type={campaign_metadata['campaign_type']} tier={campaign_metadata['tier']} "
          f"segment={campaign_metadata['segment']} angle={campaign_metadata['angle']} "
          f"market={campaign_metadata['market']}")

    # Apollo sync payload
    apollo_sync = build_apollo_sync_payload(campaign_metadata)

    # Run pipeline
    print(f"[6/10] Uruchamiam pipeline dla {len(accounts)} kontaktów...")
    results = []
    for i, row in enumerate(accounts, 1):
        result = run_pipeline(row, config, context_files=context_files, base_dir=base_dir)
        results.append(result)
        company = row.get("company_name", "?")
        gender_tag = result["contact"].get("gender", "?")
        vocative_tag = result["contact"].get("vocative") or "–"
        score = result["qa"]["qa_score"]
        decision = result["qa"]["decision"]
        llm_tag = "LLM" if result["message"].get("llm_used") else "heuristic"
        fu_tag = "LLM" if result["followup_meta"]["follow_up_1_llm_used"] else "heur"
        tier_tag = result["icp_tier"]["tier_label"]
        print(f"       [{i}/{len(accounts)}] {company} ({gender_tag}/{vocative_tag}) → Tier: {tier_tag} | QA: {score} ({decision}) [msg:{llm_tag}, fu:{fu_tag}]")

    # Flagowanie kontaktów — campaign history
    for r in results:
        update_contact_campaign_history(
            contact=r["contact"],
            campaign_metadata=campaign_metadata,
            apollo_metadata=apollo_sync,
        )

    # Engagement tracking — zapis historii outreach per kontakt
    try:
        engagement_profiles = record_campaign_batch(
            contacts_results=results,
            campaign_name=auto_campaign_name,
            campaign_type=config.get("campaign_type", "outbound"),
            apollo_sequence_name=apollo_sync.get("apollo_sequence_name"),
            apollo_sequence_id=apollo_sync.get("apollo_sequence_id"),
        )
        print(f"       Engagement tracker: {len(engagement_profiles)} profili zapisanych")
    except Exception as exc:
        print(f"       [WARN] Engagement tracker error: {exc}")

    # Prepare output dir
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir_name = f"{timestamp}_{auto_campaign_name}"
    run_dir = os.path.join(base_dir, "outputs", "runs", run_dir_name)
    ensure_dir(run_dir)

    # Write outputs
    print(f"[7/10] Zapisuję wyniki do: outputs/runs/{run_dir_name}/")

    # campaign_metadata.json
    write_json(os.path.join(run_dir, "campaign_metadata.json"), {
        "campaign_metadata": campaign_metadata,
        "apollo_sync": apollo_sync,
    })

    # generated_messages.json
    messages = [
        {
            "contact": r["contact"],
            "icp_tier": r["icp_tier"],
            "message": r["message"],
            "persona": r["persona_selection"]["persona_type"],
            "hypothesis": r["hypothesis"]["hypothesis"],
        }
        for r in results
    ]
    write_json(os.path.join(run_dir, "generated_messages.json"), messages)

    # qa_results.json
    qa_results = [
        {
            "contact": r["contact"],
            "icp_tier": r["icp_tier"]["tier"],
            "qa": r["qa"],
            "lead_score": r["lead_scoring"]["lead_score"],
        }
        for r in results
    ]
    write_json(os.path.join(run_dir, "qa_results.json"), qa_results)

    # outreach_pack.json — 3-email pack per contact (email_1 + follow_up_1 + follow_up_2)
    outreach_packs = [
        {
            "contact": r["contact"],
            "outreach_pack": r["outreach_pack"],
            "followup_meta": r["followup_meta"],
        }
        for r in results
    ]
    write_json(os.path.join(run_dir, "outreach_pack.json"), outreach_packs)
    print(f"       outreach_pack.json — {len(outreach_packs)} kontaktów × 3 emaile")

    # Apollo weekly sequence — nowy model: 1 sekwencja / wielu kontaktów / dynamic content
    apollo_mode = config.get("apollo", {}).get("mode", "sync_fields")
    if apollo_mode == "weekly_sequence":
        contacts_with_packs = [
            {"email": r["contact"].get("email", ""), "outreach_pack": r["outreach_pack"]}
            for r in results if r["contact"].get("email") and r.get("outreach_pack")
        ]
        seq_name = config.get("apollo", {}).get("sequence_name") or generate_sequence_name(
            campaign_type=campaign_metadata.get("campaign_type", "Standard"),
            market=campaign_metadata.get("market", "PL"),
        )
        weekly_result = run_weekly_sequence(
            contacts_with_packs=contacts_with_packs,
            sequence_name=seq_name,
            campaign_type=campaign_metadata.get("campaign_type", "Standard"),
            market=campaign_metadata.get("market", "PL"),
            dry_run=config.get("apollo", {}).get("dry_run", True),
        )
        write_json(os.path.join(run_dir, "apollo_weekly_sequence.json"), weekly_result)
        summary = weekly_result.get("summary", {})
        print(f"       apollo_weekly_sequence.json — {summary.get('verdict', '?')}: "
              f"{summary.get('enrolled', 0)}/{summary.get('contacts_input', 0)} enrolled, "
              f"sequence={summary.get('sequence_name', '?')}")
    else:
        # Fallback: stary model per-contact sync (backward compatible)
        apollo_sync_results = []
        for r in results:
            email = r["contact"].get("email", "")
            if email and r.get("outreach_pack"):
                sync_result = sync_outreach_pack_to_apollo(email, r["outreach_pack"])
                apollo_sync_results.append({"contact_email": email, **sync_result})
        if apollo_sync_results:
            write_json(os.path.join(run_dir, "apollo_custom_fields_sync.json"), apollo_sync_results)
            ok = sum(1 for s in apollo_sync_results if s.get("status") == "success")
            print(f"       apollo_custom_fields_sync.json — {ok}/{len(apollo_sync_results)} kontaktów zsynchronizowanych")

    # apollo_payloads.json
    payloads = [
        {
            "contact": r["contact"],
            "routing": r["routing"],
            "quality": {
                "lead_score": r["lead_scoring"]["lead_score"],
                "qa_score": r["qa"]["qa_score"],
                "risk_level": r["qa"]["risk_level"],
                "manual_review_required": r["routing"]["manual_review_required"],
            },
            "custom_fields": r["apollo_fields"],
        }
        for r in results
    ]
    write_json(os.path.join(run_dir, "apollo_payloads.json"), payloads)

    # CSV splits
    def contact_row(r):
        return {
            "company": r["contact"]["company"],
            "first_name": r["contact"]["first_name"],
            "last_name": r["contact"]["last_name"],
            "title": r["contact"]["title"],
            "persona": r["persona_selection"]["persona_type"],
            "tier": r["icp_tier"]["tier"],
            "tier_label": r["icp_tier"]["tier_label"],
            "lead_score": r["lead_scoring"]["lead_score"],
            "qa_score": r["qa"]["qa_score"],
            "decision": r["qa"]["decision"],
            "sequence": r["routing"]["sequence_recommendation"],
        }

    approved = [contact_row(r) for r in results if r["qa"]["decision"] == "approve"]
    rejected = [contact_row(r) for r in results if r["qa"]["decision"] == "reject"]
    manual_review = [contact_row(r) for r in results if r["qa"]["decision"] in ("manual_review", "rewrite")]

    print(f"[8/10] Approved: {len(approved)}, Rejected: {len(rejected)}, Manual review: {len(manual_review)}")

    write_csv_rows(os.path.join(run_dir, "approved.csv"), approved)
    write_csv_rows(os.path.join(run_dir, "rejected.csv"), rejected)
    write_csv_rows(os.path.join(run_dir, "manual_review.csv"), manual_review)

    # Run report
    report = generate_run_report(config, results, context_files, f"outputs/runs/{run_dir_name}")
    report_path = os.path.join(run_dir, "run_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[9/10] Raport zapisany: {report_path}")

    # Outreach pack summary
    fu1_llm = sum(1 for r in results if r["followup_meta"]["follow_up_1_llm_used"])
    fu2_llm = sum(1 for r in results if r["followup_meta"]["follow_up_2_llm_used"])
    print(f"[10/10] Follow-upy: FU1 LLM={fu1_llm}/{len(results)}, FU2 LLM={fu2_llm}/{len(results)}")
    print()
    print("=" * 60)
    print("DONE — Draft pipeline zakończony pomyślnie.")
    llm_count = sum(1 for r in results if r["message"].get("llm_used"))
    fb_count = sum(1 for r in results if r["message"].get("fallback_used", True))
    print(f"LLM: {llm_count} kontaktów | Fallback: {fb_count} kontaktów")
    print(f"Outreach pack: {len(outreach_packs)} × 3 emaile (email_1 + follow_up_1 + follow_up_2)")
    print(f"Output: outputs/runs/{run_dir_name}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
