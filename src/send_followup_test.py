#!/usr/bin/env python3
"""
Wysyła testowe follow-upy z ostatniego runu.

1. Jeśli istnieje outreach_pack.json — używa gotowych maili.
2. Jeśli nie — generuje follow-upy przez LLM + buduje thread (fallback).

Struktura:
- Step 2: nowy tekst + podpis + separator + header Outlook + cytowany step 1 (z podpisem)
- Step 3: nowy tekst + podpis + separator + header Outlook + cytowany step 2 PEŁNY
"""

import json
import os
import sys
import glob
from datetime import datetime, timedelta

# Ścieżki
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
OFFICE365_DIR = os.path.join(BASE_DIR, "Integracja z Office365")

sys.path.insert(0, SRC_DIR)
sys.path.insert(0, OFFICE365_DIR)

# dotenv
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(OFFICE365_DIR, ".env"))

from llm_client import generate_json, is_llm_available
from send_mail import acquire_token, send_mail
from run_campaign import load_context_files
from core.email_signature import (
    SIGNATURE_PLAIN, SIGNATURE_HTML, strip_signature,
    body_to_html, FONT_BASE,
)
from core.email_thread_formatter import (
    build_email_1, build_follow_up_1, build_follow_up_2,
)
from core.followup_generator import generate_followup


# ============================================================
# Main
# ============================================================

def main():
    to_email = sys.argv[1] if len(sys.argv) > 1 else "tomasz.uscinski@profitia.pl"

    # Znajdź ostatni run
    runs_dir = os.path.join(BASE_DIR, "outputs", "runs")
    run_dirs = sorted(glob.glob(os.path.join(runs_dir, "*")))
    if not run_dirs:
        print("BŁĄD: Brak runów w outputs/runs/")
        sys.exit(1)
    run_dir = run_dirs[-1]
    print(f"Run: {os.path.basename(run_dir)}")

    # --- Tryb 1: outreach_pack.json istnieje ---
    pack_path = os.path.join(run_dir, "outreach_pack.json")
    if os.path.exists(pack_path):
        print("Znaleziono outreach_pack.json — używam gotowych maili.")
        with open(pack_path, "r", encoding="utf-8") as f:
            packs = json.load(f)

        pack = packs[0]
        contact = pack["contact"]
        op = pack["outreach_pack"]

        step2_mail = op["follow_up_1"]
        step3_mail = op["follow_up_2"]

        print(f"Kontakt: {contact['first_name']} {contact['last_name']} ({contact['company']})")
        print(f"Subject: {op['email_1']['subject']}")
        print(f"Odbiorca testowy: {to_email}")
        print()

    else:
        # --- Tryb 2: fallback — generuj follow-upy z LLM ---
        print("Brak outreach_pack.json — generuję follow-upy z LLM...")
        messages_path = os.path.join(run_dir, "generated_messages.json")
        with open(messages_path, "r", encoding="utf-8") as f:
            messages = json.load(f)

        msg = messages[0]
        contact = msg["contact"]
        message = msg["message"]
        step1_subject = message["subject"]
        step1_body_clean = strip_signature(message.get("body", ""))

        print(f"Kontakt: {contact['first_name']} {contact['last_name']} ({contact['company']})")
        print(f"Subject step 1: {step1_subject}")
        print(f"Odbiorca testowy: {to_email}")
        print()

        today = datetime.now()
        date_step1 = today.strftime("%d.%m.%Y")
        date_step2 = (today + timedelta(days=2)).strftime("%d.%m.%Y")

        context_files = load_context_files(BASE_DIR)

        print("[1/3] Generuję follow-up 1 (LLM)...")
        fu1_result = generate_followup(
            step_number=2,
            original_subject=step1_subject,
            original_body_clean=step1_body_clean,
            previous_followup_body="",
            contact=contact,
            message=message,
            context_files=context_files,
            base_dir=BASE_DIR,
        )
        print(f"       OK — {len(fu1_result['body'].split())} słów [{'LLM' if fu1_result['llm_used'] else 'heuristic'}]")

        print("[2/3] Generuję follow-up 2 (LLM)...")
        fu2_result = generate_followup(
            step_number=3,
            original_subject=step1_subject,
            original_body_clean=step1_body_clean,
            previous_followup_body=fu1_result["body"],
            contact=contact,
            message=message,
            context_files=context_files,
            base_dir=BASE_DIR,
        )
        print(f"       OK — {len(fu2_result['body'].split())} słów [{'LLM' if fu2_result['llm_used'] else 'heuristic'}]")

        print("[3/3] Buduję struktury maili z thread simulation...")
        email_1 = build_email_1(step1_body_clean, step1_subject)
        step2_mail = build_follow_up_1(fu1_result["body"], email_1, contact, date_step1)
        step3_mail = build_follow_up_2(fu2_result["body"], step2_mail, email_1, contact, date_step2)
        print("       OK")

    # --- Wysyłka ---
    print(f"\nWysyłam 2 maile testowe do {to_email}...")
    token = acquire_token()

    test_banner = (
        f'<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 10px; '
        f'margin-bottom: 15px; border-radius: 4px; font-size: 0.9em;">'
        f'⚠️ <strong>TEST</strong> — follow-up dla: '
        f'{contact["first_name"]} {contact["last_name"]} ({contact["company"]})'
        f'</div>'
    )

    # Step 2 (follow_up_1)
    subj2 = f"[TEST Step 2/3] {step2_mail['subject']}"
    html2 = test_banner + step2_mail["body_html"]
    print(f"  Wysyłam step 2: {subj2}")
    send_mail(token, to_email, subj2, html2)

    # Step 3 (follow_up_2)
    subj3 = f"[TEST Step 3/3] {step3_mail['subject']}"
    html3 = test_banner + step3_mail["body_html"]
    print(f"  Wysyłam step 3: {subj3}")
    send_mail(token, to_email, subj3, html3)

    print()
    print("DONE — sprawdź skrzynkę.")

    # Zapisz follow-upy do pliku
    output = {
        "contact": contact,
        "step2": {
            "body_core": step2_mail.get("body_core", ""),
            "subject": step2_mail["subject"],
        },
        "step3": {
            "body_core": step3_mail.get("body_core", ""),
            "subject": step3_mail["subject"],
        },
    }
    out_path = os.path.join(run_dir, "followup_test.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Zapisano: {out_path}")


if __name__ == "__main__":
    main()
