#!/usr/bin/env python3
"""
AI Outreach System — CSV Import Pipeline
Profitia / SpendGuru

Tryb DRAFT: CSV → normalizacja → scoring → research → hipoteza → wiadomość → QA → output.
Wykorzystuje wspólne agenty z run_campaign.py + dedykowany csv_normalizer.
Bez integracji z Apollo. Bez wysyłki maili.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- Ścieżki ---
PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(PIPELINE_DIR)
BASE_DIR = os.path.dirname(SRC_DIR)

sys.path.insert(0, SRC_DIR)
sys.path.insert(0, BASE_DIR)

# --- dotenv ---
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

# --- YAML ---
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

# --- CSV normalizer ---
from agents.csv_import.csv_normalizer import normalize_contacts

# --- Wspólne agenty z run_campaign ---
from run_campaign import (
    load_config,
    load_csv,
    load_context_files,
    ensure_dir,
    write_json,
    write_csv_rows,
    agent_lead_scoring,
    agent_account_research,
    agent_persona_selection,
    agent_hypothesis,
    agent_message_writer,
    agent_qa_reviewer,
    agent_apollo_fields,
    agent_sequence_router,
    TITLE_TO_PERSONA,
    FORBIDDEN_PHRASES,
    is_llm_available,
    _append_signature,
)
from core.email_signature import strip_signature as _strip_signature
from core.email_thread_formatter import build_outreach_pack
from core.followup_generator import generate_followup


# ============================================================
# Weak trigger inference (dla CSV bez mocnego triggera)
# ============================================================

def agent_csv_trigger_inference(contact: dict, persona: dict,
                                context_files: dict | None = None,
                                base_dir: str = "") -> dict:
    """
    Buduje hipotezę dla kontaktów z CSV.
    Próbuje LLM z dedykowanym promptem, fallback na wspólny agent_hypothesis.
    """
    notes = contact.get("notes", "")
    industry = contact.get("industry", "")
    persona_type = persona.get("persona_type", "cpo")

    # Spróbuj LLM z dedykowanym promptem csv_trigger_inference
    if is_llm_available():
        prompt_path = os.path.join(base_dir, "prompts", "csv_import", "csv_trigger_inference.md")
        if os.path.exists(prompt_path):
            payload = {
                "persona_type": persona_type,
                "job_title": contact.get("job_title", ""),
                "company_name": contact.get("company_name", ""),
                "industry": industry,
                "country": contact.get("country", ""),
                "notes": notes,
                "language": "pl",
            }
            result = generate_json(
                agent_name="CSVTriggerInference",
                prompt_path=prompt_path,
                user_payload=payload,
                context_files=context_files,
                relevant_context_keys=["01_offer", "02_personas", "03_messaging"],
            )
            if result and "hypothesis" in result:
                result["llm_used"] = True
                result["fallback_used"] = False
                result.setdefault("trigger_type", "weak_inferred")
                return result

    # Fallback: użyj wspólnego agent_hypothesis z zamockowanym row
    mock_row = {
        "company_name": contact.get("company_name", ""),
        "industry": industry,
        "country": contact.get("country", ""),
        "notes": notes,
        "contact_title": contact.get("job_title", ""),
    }
    mock_research = {
        "company_summary": f"{contact.get('company_name', 'Firma')} — branża {industry.lower()}.",
        "business_signals": [notes] if notes else ["Brak dodatkowych sygnałów — dane z CSV."],
        "potential_trigger": notes if notes else "brak twardego triggera",
    }
    result = agent_hypothesis(mock_research, persona, mock_row,
                              context_files=context_files, base_dir=base_dir)
    result["trigger_type"] = "weak_inferred" if notes else "generic"
    return result


# ============================================================
# Adapter: normalized contact → internal row format
# ============================================================

def contact_to_pipeline_row(contact: dict) -> dict:
    """
    Konwertuje znormalizowany kontakt na format row oczekiwany przez
    wspólne agenty (lead_scoring, persona_selection, message_writer itd.).
    """
    return {
        "company_name": contact.get("company_name", ""),
        "company_domain": contact.get("company_domain", ""),
        "country": contact.get("country", ""),
        "industry": contact.get("industry", ""),
        "contact_first_name": contact.get("first_name", ""),
        "contact_last_name": contact.get("last_name", ""),
        "contact_title": contact.get("job_title", ""),
        "notes": contact.get("notes", ""),
    }


# ============================================================
# Rozszerzony message_writer payload (z normalizacją)
# ============================================================

def agent_csv_message_writer(contact: dict, research: dict, persona: dict,
                             hypothesis: dict, config: dict,
                             context_files: dict | None = None,
                             base_dir: str = "") -> dict:
    """
    Generuje wiadomość. Przekazuje do message_writer dane już znormalizowane:
    gender, first_name_vocative, greeting.
    """
    row = contact_to_pipeline_row(contact)

    if is_llm_available():
        prompt_path = os.path.join(base_dir, "prompts", "shared", "message_writer.md")
        payload = {
            "persona_type": persona.get("persona_type", "cpo"),
            "hypothesis": hypothesis.get("hypothesis", ""),
            "trigger": hypothesis.get("trigger_used", ""),
            "trigger_type": hypothesis.get("trigger_type", "generic"),
            "account_research": research,
            "contact_first_name": contact.get("first_name", ""),
            "contact_title": contact.get("job_title", ""),
            "company_name": contact.get("company_name", ""),
            "industry": contact.get("industry", ""),
            "notes": contact.get("notes", ""),
            "language": config.get("language_code", "pl"),
            "max_words": config.get("message", {}).get("max_words", 120),
            "style": config.get("message", {}).get("style", "concise_consultative"),
            # Dane znormalizowane — LLM nie musi zgadywać
            "gender": contact.get("gender", "unknown"),
            "first_name_vocative": contact.get("first_name_vocative"),
            "greeting": contact.get("greeting", "Dzień dobry,"),
        }

        result = generate_json(
            agent_name="MessageWriter_CSV",
            prompt_path=prompt_path,
            user_payload=payload,
            context_files=context_files,
            relevant_context_keys=["01_offer", "02_personas", "03_messaging", "05_quality"],
            max_tokens=2500,
        )
        if result and "body" in result:
            result["llm_used"] = True
            result["fallback_used"] = False
            if "word_count" not in result:
                result["word_count"] = len(result["body"].split())
            if "language" not in result:
                result["language"] = config.get("language_code", "pl")
            # Nadpisz greeting i gender z normalizacji (bardziej wiarygodne)
            result["recipient_gender"] = contact.get("gender", "unknown")
            result["first_name_vocative"] = contact.get("first_name_vocative")
            result["greeting"] = contact.get("greeting", "Dzień dobry,")
            # Dodaj firmę do subject
            company_name = contact.get("company_name", "")
            if company_name and company_name not in result.get("subject", ""):
                result["subject"] = f"{result['subject']} — {company_name}"
            return _append_signature(result)

    # Heurystyczny fallback
    return _append_signature(_csv_message_heuristic(contact, research, persona, hypothesis, config))


# ============================================================
# Heurystyczny fallback message writer dla CSV
# ============================================================

_CTA_TEMPLATES = {
    "cpo": "Czy ma sens krótka rozmowa o tym, jak wygląda przygotowanie negocjacji w jednej wybranej kategorii?",
    "buyer": "Czy warto porozmawiać o jednej kategorii, w której warto sprawdzić zasadność obecnych warunków?",
    "cfo": "Czy ma sens krótka rozmowa o wpływie zakupów na przewidywalność kosztów?",
    "ceo": "Czy warto poświęcić 15 minut na rozmowę o kontroli kosztów zakupowych?",
    "supply_chain": "Czy ma sens krótka rozmowa o jednym elemencie łańcucha dostaw, który warto zweryfikować?",
}

_PROOF_TEMPLATES = {
    "cpo": "W podobnych projektach zwykle zaczynamy od jednej kategorii — żeby zobaczyć, czy dane potwierdzają hipotezę.",
    "buyer": "W praktyce często wystarczy spojrzeć na jedną ofertę dostawcy, żeby ocenić, czy warunki są fair.",
    "cfo": "W firmach o podobnej skali często okazuje się, że nawet kilka kategorii zakupowych ma istotny wpływ na wynik.",
    "ceo": "W firmach o podobnym profilu często widzimy, że przegląd kilku kluczowych kategorii daje szybki obraz sytuacji.",
    "supply_chain": "W praktyce warto zacząć od jednego elementu łańcucha, żeby zobaczyć, gdzie jest największy potencjał.",
}


def _csv_message_heuristic(contact: dict, research: dict, persona: dict,
                           hypothesis: dict, config: dict) -> dict:
    """Heurystyczny fallback dla CSV message writera — z pełną obsługą gender/vocative."""
    persona_type = persona.get("persona_type", "cpo")
    gender = contact.get("gender", "unknown")
    greeting = contact.get("greeting", "Dzień dobry,")
    notes = contact.get("notes", "")

    opener = "piszę z krótką hipotezą dotyczącą przygotowania negocjacji z dostawcami w firmach o podobnej skali."

    hyp_text = hypothesis.get("hypothesis", "")
    proof = _PROOF_TEMPLATES.get(persona_type, _PROOF_TEMPLATES["cpo"])

    # CTA z formami grzecznościowymi dopasowanymi do płci
    if gender == "female":
        cta = (
            "Je\u015bli temat jest dla Pani aktualny, prosz\u0119 wybra\u0107 dogodny termin tutaj: [link do Calendly].\n"
            "Mo\u017ce Pani te\u017c po prostu odpisa\u0107 \u201eTAK\u201d i poda\u0107 numer telefonu \u2014 oddzwoni\u0119."
        )
    elif gender == "male":
        cta = (
            "Je\u015bli temat jest dla Pana aktualny, prosz\u0119 wybra\u0107 dogodny termin tutaj: [link do Calendly].\n"
            "Mo\u017ce Pan te\u017c po prostu odpisa\u0107 \u201eTAK\u201d i poda\u0107 numer telefonu \u2014 oddzwoni\u0119."
        )
    else:
        cta = (
            "Je\u015bli temat jest aktualny, prosz\u0119 wybra\u0107 dogodny termin tutaj: [link do Calendly].\n"
            "Mo\u017cna te\u017c po prostu odpisa\u0107 \u201eTAK\u201d i poda\u0107 numer telefonu \u2014 oddzwoni\u0119."
        )

    subject = "Pytanie o przygotowanie negocjacji z dostawcami"
    company_name = contact.get("company_name", "")
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
        "first_name_vocative": contact.get("first_name_vocative"),
        "greeting": greeting,
        "word_count": word_count,
        "language": config.get("language_code", "pl"),
        "llm_used": False,
        "fallback_used": True,
    }


# ============================================================
# Pipeline
# ============================================================

def run_csv_pipeline(contact: dict, config: dict, context_files: dict | None = None,
                     base_dir: str = "") -> dict:
    """Uruchamia pełny pipeline dla jednego znormalizowanego kontaktu CSV, w tym follow-upy."""
    row = contact_to_pipeline_row(contact)

    scoring = agent_lead_scoring(row, config)
    research = agent_account_research(row)
    persona = agent_persona_selection(row)

    # Hypothesis: dedykowany CSV trigger inference
    hypothesis = agent_csv_trigger_inference(contact, persona,
                                            context_files=context_files,
                                            base_dir=base_dir)

    # Message writer: z normalizacją gender/vocative
    message = agent_csv_message_writer(contact, research, persona, hypothesis, config,
                                       context_files=context_files, base_dir=base_dir)

    qa = agent_qa_reviewer(message, persona, hypothesis, config,
                           context_files=context_files, base_dir=base_dir)
    fields = agent_apollo_fields(row, message, persona, hypothesis, scoring, qa, config)
    routing = agent_sequence_router(persona, config)

    contact_dict = {
        "first_name": contact.get("first_name", ""),
        "last_name": contact.get("last_name", ""),
        "title": contact.get("job_title", ""),
        "company": contact.get("company_name", ""),
        "domain": contact.get("company_domain", ""),
        "gender": contact.get("gender", "unknown"),
        "vocative": contact.get("first_name_vocative"),
    }

    # --- Follow-upy + outreach pack ---
    email_1_body_core = _strip_signature(message.get("body", ""))
    email_1_subject = message.get("subject", "")
    trigger_title = hypothesis.get("trigger_used", "")
    trigger_source = contact.get("notes", "")

    fu1_result = generate_followup(
        step_number=2,
        original_subject=email_1_subject,
        original_body_clean=email_1_body_core,
        previous_followup_body="",
        contact=contact_dict,
        message=message,
        context_files=context_files,
        base_dir=base_dir,
        trigger_title=trigger_title,
        trigger_source=trigger_source,
    )

    fu2_result = generate_followup(
        step_number=3,
        original_subject=email_1_subject,
        original_body_clean=email_1_body_core,
        previous_followup_body=fu1_result["body"],
        contact=contact_dict,
        message=message,
        context_files=context_files,
        base_dir=base_dir,
        trigger_title=trigger_title,
        trigger_source=trigger_source,
    )

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

    return {
        "normalized_contact": contact,
        "contact": contact_dict,
        "lead_scoring": scoring,
        "account_research": research,
        "persona_selection": persona,
        "hypothesis": hypothesis,
        "message": message,
        "qa": qa,
        "apollo_fields": fields,
        "routing": routing,
        "outreach_pack": outreach_pack,
        "followup_meta": {
            "follow_up_1_llm_used": fu1_result["llm_used"],
            "follow_up_2_llm_used": fu2_result["llm_used"],
            "follow_up_1_model": fu1_result.get("_llm_model_used", "heuristic"),
            "follow_up_2_model": fu2_result.get("_llm_model_used", "heuristic"),
        },
    }


# ============================================================
# Report generator
# ============================================================

def generate_csv_run_report(config: dict, results: list[dict], normalized: list[dict],
                            context_files: dict, run_dir: str) -> str:
    """Generuje raport kampanii CSV import."""
    total = len(results)
    approved = [r for r in results if r["qa"]["decision"] == "approve"]
    rewrite = [r for r in results if r["qa"]["decision"] == "rewrite"]
    manual = [r for r in results if r["qa"]["decision"] == "manual_review"]
    rejected = [r for r in results if r["qa"]["decision"] == "reject"]

    avg_lead = sum(r["lead_scoring"]["lead_score"] for r in results) / total if total else 0
    avg_qa = sum(r["qa"]["qa_score"] for r in results) / total if total else 0

    # Normalization warnings
    all_warnings = []
    for n in normalized:
        all_warnings.extend(n.get("normalization_warnings", []))

    # Gender stats
    genders = [n.get("gender", "unknown") for n in normalized]
    g_female = genders.count("female")
    g_male = genders.count("male")
    g_unknown = genders.count("unknown")

    # Issues
    all_issues = []
    for r in results:
        all_issues.extend(r["qa"].get("issues", []))

    ctx_status = "Załadowano" if context_files else "BRAK"
    ctx_list = ", ".join(sorted(context_files.keys())) if context_files else "brak"

    report = f"""# Run Report — CSV Import

## Campaign
- **Nazwa**: {config.get('campaign_name', 'unknown')}
- **Typ**: csv_import
- **Język**: {config.get('language_code', 'pl')}
- **Persona docelowa**: {config.get('target_persona', 'unknown')}
- **Tryb**: {config.get('mode', 'draft')}
- **Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Plik źródłowy**: {config.get('source', {}).get('file', 'unknown')}

## Pliki kontekstowe
- **Status**: {ctx_status}
- **Pliki**: {ctx_list}

## Normalizacja
- Rekordów wejściowych: {total}
- Gender — female: {g_female}, male: {g_male}, unknown: {g_unknown}
- Warnings normalizacji: {len(all_warnings)}
"""
    if all_warnings:
        report += "\n### Normalization Warnings\n"
        for w in all_warnings:
            report += f"- {w}\n"

    report += f"""
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

    # LLM usage
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
| CSVTriggerInference | {llm_hyp} | {fb_hyp} |
| MessageWriter_CSV | {llm_msg} | {fb_msg} |
| QA Reviewer | {llm_qa} | {fb_qa} |
"""

    # Model usage per contact
    report += "\n## LLM Model Usage (per contact)\n"
    report += "| Kontakt | Hypothesis | Message | QA | FU1 | FU2 |\n"
    report += "|---|---|---|---|---|---|\n"
    for r in results:
        name = f"{r['contact']['first_name']} {r['contact']['last_name']}"
        hyp_model = r["hypothesis"].get("_llm_model_used", "heuristic")
        msg_model = r["message"].get("_llm_model_used", "heuristic")
        qa_model = r["qa"].get("_llm_model_used", "heuristic")
        fu1_model = r.get("followup_meta", {}).get("follow_up_1_model", "heuristic")
        fu2_model = r.get("followup_meta", {}).get("follow_up_2_model", "heuristic")
        hyp_fb = " (fb)" if r["hypothesis"].get("_llm_fallback") else ""
        msg_fb = " (fb)" if r["message"].get("_llm_fallback") else ""
        qa_fb = " (fb)" if r["qa"].get("_llm_fallback") else ""
        report += f"| {name} | {hyp_model}{hyp_fb} | {msg_model}{msg_fb} | {qa_model}{qa_fb} | {fu1_model} | {fu2_model} |\n"

    report += f"""
## Uwagi
- Tryb: **DRAFT** — żadne dane nie zostały zapisane do Apollo.
- Normalizacja (gender, vocative, mapowanie kolumn) wykonana deterministycznie.
- Wyniki służą do walidacji pipeline'u csv_import, nie do wysyłki.

## Output
- Folder: `{run_dir}`
"""
    return report


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AI Outreach System — CSV Import Pipeline")
    parser.add_argument("--config", required=True, help="Ścieżka do YAML config kampanii")
    parser.add_argument("--mode", default="draft", choices=["draft"],
                        help="Tryb uruchomienia (CSV import: tylko draft)")
    args = parser.parse_args()

    # Ścieżki
    config_path = os.path.join(BASE_DIR, args.config)

    # Wczytaj config
    print(f"[1/9] Wczytuję config: {args.config}")
    config = load_config(config_path)
    config["mode"] = args.mode

    # CSV source path
    source_file = config.get("source", {}).get("file", "")
    csv_path = os.path.join(BASE_DIR, source_file)

    # Wczytaj CSV
    print(f"[2/9] Wczytuję dane: {source_file}")
    if not os.path.exists(csv_path):
        print(f"BŁĄD: Plik {csv_path} nie istnieje.")
        sys.exit(1)
    raw_rows = load_csv(csv_path)
    print(f"       Załadowano {len(raw_rows)} rekordów.")

    # Normalizacja
    print("[3/9] Normalizuję dane kontaktowe...")
    normalized = normalize_contacts(raw_rows)
    warnings_total = sum(len(c.get("normalization_warnings", [])) for c in normalized)
    genders = [c.get("gender", "unknown") for c in normalized]
    print(f"       Gender: female={genders.count('female')}, male={genders.count('male')}, unknown={genders.count('unknown')}")
    if warnings_total:
        print(f"       Warnings: {warnings_total}")
        for c in normalized:
            for w in c.get("normalization_warnings", []):
                print(f"         - [{c.get('full_name', '?')}] {w}")

    # Wczytaj context
    print("[4/9] Wczytuję pliki kontekstowe...")
    context_files = load_context_files(BASE_DIR)
    if context_files:
        print(f"       Załadowano {len(context_files)} plików: {', '.join(sorted(context_files.keys()))}")
    else:
        print("       UWAGA: Nie znaleziono plików kontekstowych.")

    # LLM status
    print("[5/9] Sprawdzam dostępność LLM...")
    if is_llm_available():
        llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        print(f"       LLM AKTYWNY: model={llm_model}")
        print("       Agenty z LLM: CSVTriggerInference, MessageWriter_CSV, QA Reviewer")
    else:
        print("       LLM NIEAKTYWNY — pipeline użyje heurystyk (fallback).")

    # Run pipeline
    print(f"[6/10] Uruchamiam pipeline dla {len(normalized)} kontaktów...")
    results = []
    for i, contact in enumerate(normalized, 1):
        result = run_csv_pipeline(contact, config, context_files=context_files, base_dir=BASE_DIR)
        results.append(result)
        company = contact.get("company_name", "?")
        score = result["qa"]["qa_score"]
        decision = result["qa"]["decision"]
        gender = contact.get("gender", "?")
        vocative = contact.get("first_name_vocative", "-")
        llm_tag = "LLM" if result["message"].get("llm_used") else "heuristic"
        fu_tag = "LLM" if result["followup_meta"]["follow_up_1_llm_used"] else "heur"
        print(f"       [{i}/{len(normalized)}] {company} ({gender}/{vocative}) → QA: {score} ({decision}) [msg:{llm_tag}, fu:{fu_tag}]")

    # Prepare output dir
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    campaign_name = config.get("campaign_name", "unknown")
    run_dir_name = f"{timestamp}_{campaign_name}"
    run_dir = os.path.join(BASE_DIR, "outputs", "runs", run_dir_name)
    ensure_dir(run_dir)

    # Write outputs
    print(f"[7/10] Zapisuję wyniki do: outputs/runs/{run_dir_name}/")

    # normalized_contacts.json
    write_json(os.path.join(run_dir, "normalized_contacts.json"), normalized)

    # generated_messages.json
    messages = [
        {
            "contact": r["contact"],
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
            "qa": r["qa"],
            "lead_score": r["lead_scoring"]["lead_score"],
        }
        for r in results
    ]
    write_json(os.path.join(run_dir, "qa_results.json"), qa_results)

    # outreach_pack.json — 3-email pack per contact
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
            "gender": r["contact"]["gender"],
            "vocative": r["contact"]["vocative"],
            "persona": r["persona_selection"]["persona_type"],
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
    report = generate_csv_run_report(config, results, normalized, context_files,
                                     f"outputs/runs/{run_dir_name}")
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
    print("DONE — CSV Import pipeline zakończony pomyślnie.")
    llm_count = sum(1 for r in results if r["message"].get("llm_used"))
    fb_count = sum(1 for r in results if r["message"].get("fallback_used", True))
    print(f"LLM: {llm_count} kontaktów | Fallback: {fb_count} kontaktów")
    print(f"Outreach pack: {len(outreach_packs)} × 3 emaile (email_1 + follow_up_1 + follow_up_2)")
    print(f"Output: outputs/runs/{run_dir_name}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
