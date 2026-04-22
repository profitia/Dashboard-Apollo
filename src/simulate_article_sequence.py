#!/usr/bin/env python3
"""
Symulacja pełnej sekwencji 3-krokowej na podstawie artykułu.
Artykuł → identyfikacja odbiorcy → step 1 (LLM) → follow-up 2 → follow-up 3 → wysyłka.
"""

import json
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
OFFICE365_DIR = os.path.join(BASE_DIR, "Integracja z Office365")

sys.path.insert(0, SRC_DIR)
sys.path.insert(0, OFFICE365_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(OFFICE365_DIR, ".env"))

from llm_client import generate_json, is_llm_available
from send_mail import acquire_token, send_mail
from run_campaign import (
    EMAIL_SIGNATURE_PLAIN, EMAIL_SIGNATURE_HTML,
    _body_to_html, _FONT_BASE, load_context_files,
)
from send_followup_test import (
    build_step2, build_step3, generate_followup_body, _strip_signature,
)
from core.icp_tier_resolver import resolve_tier, get_tier_prompt_context
from core.tier_alignment import tier_alignment_check

try:
    from core.campaign_name_builder import build_campaign_metadata
except ImportError:
    build_campaign_metadata = None

try:
    from core.apollo_contact_enrichment import enrich_contact_name_fields
except ImportError:
    enrich_contact_name_fields = None

# ============================================================
# Dane symulacji — artykuł + fikcyjny odbiorca
# ============================================================

ARTICLE_TRIGGER = {
    "url": "https://www.portalspozywczy.pl/mieso/wiadomosci/gigant-miesny-zderzyl-sie-z-rynkiem-sytuacja-w-trzodzie-ciazy-wynikom,287106.html",
    "title": "Gigant mięsny zderzył się z rynkiem. Sytuacja w trzodzie ciąży wynikom",
    "date": "2026-03-31",
    "source": "PortalSpożywczy.pl",
    "summary": (
        "Artykuł o Grupie Gobarto — przychody wzrosły do 3,83 mld zł w 2025, "
        "ale druga połowa roku przyniosła wyraźne pogorszenie warunków rynkowych. "
        "W H1 2025 ceny trzody w UE rosły, od lipca zaczęły wyraźnie spadać. "
        "Spadek cen żywca wieprzowego + presja kosztowa = słabsza koniunktura w sektorze. "
        "Eksport wieprzowiny z Polski wzrósł wolumenowo, ale w GK Gobarto spadły "
        "przychody eksportowe i ich udział w sprzedaży. Na wyniki segmentu mięsa i wędlin "
        "wpłynęły wyższe wolumeny uboju oraz rozwój własnych kanałów dystrybucji. "
        "Kluczowe wyzwanie: zmienność cen surowca (żywca) vs. presja cenowa ze strony "
        "sieci handlowych i kanałów dystrybucji."
    ),
}

SIMULATED_CONTACT = {
    "first_name": "Karol",
    "last_name": "Ludwiński",
    "title": "Prezes Zarządu",
    "company": "Gobarto",
    "domain": "gobarto.pl",
    "industry": "Przetwórstwo mięsne",
    "country": "PL",
}

# ============================================================
# Step 1 — generowanie maila głównego przez LLM
# ============================================================

def generate_step1(contact: dict, article: dict, context_files: dict) -> dict:
    """Generuje mail 1 (opening) na podstawie artykułu jako triggera."""
    prompt_path = os.path.join(BASE_DIR, "prompts", "shared", "message_writer.md")

    # ICP Tier detection
    tier_info = resolve_tier(contact.get("title", ""))

    # Wzbogać kontekst o aktywny tier
    enriched_context = dict(context_files) if context_files else {}
    tier_prompt = get_tier_prompt_context(tier_info["tier"])
    if tier_prompt:
        enriched_context["__icp_tier_active"] = tier_prompt

    payload = {
        "persona_type": "cpo",
        "hypothesis": "",  # LLM sam zbuduje na podstawie triggera
        "trigger": article["summary"],
        "trigger_url": article["url"],
        "trigger_title": article["title"],
        "account_research": {
            "company_summary": (
                f"{contact['company']} — Grupa Gobarto, jeden z największych polskich "
                "producentów mięsa i wędlin. Przychody 3,83 mld zł w 2025. Duży wolumen "
                "uboju trzody, przetwórstwo, eksport, własne kanały dystrybucji. "
                "Zmienność cen żywca wieprzowego bezpośrednio wpływa na marże "
                "i pozycję negocjacyjną wobec dostawców żywca i odbiorców (sieci handlowe)."
            ),
            "business_signals": [
                "Branża przetwórstwa mięsnego — wrażliwa na zmienność cen żywca",
                "H2 2025: spadek cen trzody w UE osłabił wyniki Gobarto",
                "Presja cenowa ze strony sieci handlowych vs. zmienność kosztów surowca",
                "Spadek przychodów eksportowych mimo wzrostu wolumenów",
                "Rozwój własnych kanałów dystrybucji — zmiana struktury sprzedaży",
            ],
            "potential_trigger": article["summary"],
        },
        "contact_first_name": contact["first_name"],
        "contact_title": contact["title"],
        "company_name": contact["company"],
        "industry": contact["industry"],
        "notes": (
            f"Artykuł z {article['source']} ({article['date']}): {article['title']}. "
            "Artykuł opisuje wyniki właśnie tej firmy — Gobarto. Przychody 3,83 mld zł, "
            "ale H2 2025 przyniosło pogorszenie — spadek cen żywca wieprzowego + presja "
            "kosztowa. Kluczowe wyzwanie Prezesa: zmienność cen surowca (żywca), "
            "presja sieci handlowych na ceny, spadek przychodów eksportowych. "
            "Temat istotny z perspektywy zarządzania — jak bronić marży w warunkach "
            "spadających cen żywca, negocjować lepsze warunki z dostawcami żywca "
            "i optymalizować kanały dystrybucji."
        ),
        "language": "pl",
        "max_words": 140,
        "style": "concise_consultative",
    }

    result = generate_json(
        agent_name="MessageWriter_Simulation",
        prompt_path=prompt_path,
        user_payload=payload,
        context_files=enriched_context,
        relevant_context_keys=["01_offer", "02_personas", "03_messaging", "05_quality", "icp_tiers", "__icp_tier_active"],
    )

    if result and "body" in result:
        result["llm_used"] = True
        result["icp_tier"] = tier_info
        # Dodaj firmę do subject jeśli brak
        if contact["company"] not in result.get("subject", ""):
            result["subject"] = f"{result['subject']} — {contact['company']}"
        return result

    return None


def append_signature(message: dict) -> dict:
    """Dodaje podpis do wiadomości."""
    body = message.get("body", "")
    # Usuń ewentualny placeholder
    for placeholder in ["[Twoje Imię]", "[Imię i Nazwisko]", "[Podpis]",
                        "Pozdrawiam,\n\n[Twoje Imię]",
                        "Pozdrawiam,", "Pozdrawiam serdecznie,"]:
        if body.rstrip().endswith(placeholder):
            body = body.rstrip()[:-len(placeholder)].rstrip()
            break
    message["body"] = body.rstrip() + "\n\n" + EMAIL_SIGNATURE_PLAIN

    meta_block = (
        '<meta name="format-detection" content="telephone=no">'
        '<meta name="x-apple-disable-message-reformatting">'
    )
    message["body_html"] = (
        meta_block + "\n"
        + _body_to_html(body.rstrip()) + "\n"
        + EMAIL_SIGNATURE_HTML
    )
    return message


# ============================================================
# Main
# ============================================================

def main():
    to_email = sys.argv[1] if len(sys.argv) > 1 else "tomasz.uscinski@profitia.pl"
    contact = SIMULATED_CONTACT
    article = ARTICLE_TRIGGER

    print("=" * 60)
    print("SYMULACJA SEKWENCJI 3-KROKOWEJ")
    print("=" * 60)
    print(f"Artykuł: {article['title']}")
    print(f"Odbiorca: {contact['first_name']} {contact['last_name']}, {contact['title']}")
    print(f"Firma: {contact['company']} ({contact['industry']})")
    print(f"Email testowy: {to_email}")
    print()

    # Context files
    context_files = load_context_files(BASE_DIR)

    # --- Step 1 ---
    print("[1/5] Generuję mail 1 (opening) przez LLM...")
    step1_msg = generate_step1(contact, article, context_files)
    if not step1_msg:
        print("BŁĄD: LLM nie wygenerował maila 1.")
        sys.exit(1)
    step1_msg = append_signature(step1_msg)
    step1_subject = step1_msg["subject"]
    step1_body_with_sig = step1_msg["body"]
    step1_body_html = step1_msg["body_html"]
    step1_body_clean = _strip_signature(step1_body_with_sig)
    print(f"       OK — subject: {step1_subject}")
    print(f"       {len(step1_body_clean.split())} słów")

    # Lightweight tier alignment check (step1 only — followups nie mają jeszcze body)
    tier_info = step1_msg.get("icp_tier", {})
    alignment = tier_alignment_check(tier_info, [step1_body_clean])
    align_tag = "PASS" if alignment.get("pass") else "REVIEW"
    print(f"       Tier alignment: {align_tag}")
    if alignment.get("comments"):
        for c in alignment["comments"]:
            print(f"         - {c}")

    # Daty
    today = datetime.now()
    date_step1 = today.strftime("%d.%m.%Y")
    date_step2 = (today + timedelta(days=2)).strftime("%d.%m.%Y")

    # --- Step 2 ---
    print("[2/5] Generuję follow-up 2 (LLM)...")
    followup2_body = generate_followup_body(
        step_number=2,
        original_subject=step1_subject,
        original_body_clean=step1_body_clean,
        previous_followup_body="",
        contact=contact,
        message=step1_msg,
        context_files=context_files,
        trigger_title=article["title"],
        trigger_source=article["source"],
    )
    if not followup2_body:
        print("BŁĄD: LLM nie wygenerował follow-upa 2.")
        sys.exit(1)
    print(f"       OK — {len(followup2_body.split())} słów")

    # --- Step 3 ---
    print("[3/5] Generuję follow-up 3 (LLM)...")
    followup3_body = generate_followup_body(
        step_number=3,
        original_subject=step1_subject,
        original_body_clean=step1_body_clean,
        previous_followup_body=followup2_body,
        contact=contact,
        message=step1_msg,
        context_files=context_files,
        trigger_title=article["title"],
        trigger_source=article["source"],
    )
    if not followup3_body:
        print("BŁĄD: LLM nie wygenerował follow-upa 3.")
        sys.exit(1)
    print(f"       OK — {len(followup3_body.split())} słów")

    # --- Build thread simulation ---
    print("[4/5] Buduję struktury maili z thread simulation...")

    step2_mail = build_step2(
        followup2_body=followup2_body,
        step1_body_with_sig=step1_body_with_sig,
        step1_body_html=step1_body_html,
        step1_subject=step1_subject,
        contact=contact,
        date_step1=date_step1,
    )

    step3_mail = build_step3(
        followup3_body=followup3_body,
        step2_full=step2_mail,
        step1_subject=step1_subject,
        contact=contact,
        date_step1=date_step1,
        date_step2=date_step2,
    )
    print("       OK")

    # --- Wysyłka ---
    print(f"[5/5] Wysyłam 3 maile na {to_email}...")
    token = acquire_token()

    test_banner = (
        f'<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 10px; '
        f'margin-bottom: 15px; border-radius: 4px; font-size: 0.9em;">'
        f'⚠️ <strong>SYMULACJA</strong> — sekwencja dla: '
        f'{contact["first_name"]} {contact["last_name"]}, {contact["title"]} @ {contact["company"]}<br>'
        f'Trigger: <a href="{article["url"]}">{article["title"]}</a>'
        f'</div>'
    )

    # Step 1
    subj1 = f"[Step 1/3] {step1_subject}"
    html1 = test_banner + step1_body_html
    print(f"  Step 1: {subj1}")
    send_mail(token, to_email, subj1, html1)

    # Step 2
    subj2 = f"[Step 2/3] {step2_mail['subject']}"
    html2 = test_banner + step2_mail["body_html"]
    print(f"  Step 2: {subj2}")
    send_mail(token, to_email, subj2, html2)

    # Step 3
    subj3 = f"[Step 3/3] {step3_mail['subject']}"
    html3 = test_banner + step3_mail["body_html"]
    print(f"  Step 3: {subj3}")
    send_mail(token, to_email, subj3, html3)

    print()
    print("DONE — 3 maile wysłane. Sprawdź skrzynkę.")

    # Zapisz dane symulacji
    # Re-run alignment on all 3 bodies combined
    all_bodies = [step1_body_clean, followup2_body, followup3_body]
    final_alignment = tier_alignment_check(step1_msg.get("icp_tier", {}), all_bodies)

    output = {
        "simulation": {
            "article": article,
            "contact": contact,
        },
        "campaign_metadata": build_campaign_metadata(
            config={"campaign_type": "article_triggered", "market": "PL"},
            flow_name="simulate_article_sequence",
            trigger="article",
        ) if build_campaign_metadata else None,
        "icp_tier": step1_msg.get("icp_tier", {}),
        "tier_alignment": final_alignment,
        "name_enrichment": enrich_contact_name_fields(
            contact, write_to_apollo=False,
        ) if enrich_contact_name_fields else None,
        "step1": {
            "subject": step1_subject,
            "body_clean": step1_body_clean,
            "recipient_gender": step1_msg.get("recipient_gender"),
            "first_name_vocative": step1_msg.get("first_name_vocative"),
        },
        "step2": {
            "subject": step2_mail["subject"],
            "body_new": followup2_body,
        },
        "step3": {
            "subject": step3_mail["subject"],
            "body_new": followup3_body,
        },
    }
    out_path = os.path.join(BASE_DIR, "outputs", "simulation_article_sequence.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Zapisano: {out_path}")


if __name__ == "__main__":
    main()
