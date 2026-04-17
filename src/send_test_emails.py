#!/usr/bin/env python3
"""
Wysyła wygenerowane wiadomości z ostatniego runu na podany adres email (test).
Używa Office365 Graph API z send_mail.py.
"""

import json
import os
import sys
import glob

# Dodaj ścieżkę do send_mail.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICE365_DIR = os.path.join(BASE_DIR, "Integracja z Office365")
sys.path.insert(0, OFFICE365_DIR)

# Załaduj .env z Office365
from dotenv import load_dotenv
load_dotenv(os.path.join(OFFICE365_DIR, ".env"))

from send_mail import acquire_token, send_mail


def find_latest_run():
    """Znajdź najnowszy folder runu."""
    runs_dir = os.path.join(BASE_DIR, "outputs", "runs")
    run_dirs = sorted(glob.glob(os.path.join(runs_dir, "*")))
    if not run_dirs:
        print("BŁĄD: Brak runów w outputs/runs/")
        sys.exit(1)
    return run_dirs[-1]


def plain_to_html(body_text: str) -> str:
    """Konwertuje plain text body na prosty HTML (zachowując paragrafy)."""
    import html as html_mod
    escaped = html_mod.escape(body_text)
    paragraphs = escaped.split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.replace("\n", "<br>")
        html_parts.append(f"<p>{p}</p>")
    return "\n".join(html_parts)


def main():
    to_email = sys.argv[1] if len(sys.argv) > 1 else "tomasz.uscinski@profitia.pl"

    # Znajdź ostatni run
    run_dir = find_latest_run()
    messages_path = os.path.join(run_dir, "generated_messages.json")

    if not os.path.exists(messages_path):
        print(f"BŁĄD: Brak pliku {messages_path}")
        sys.exit(1)

    with open(messages_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    print(f"Run: {os.path.basename(run_dir)}")
    print(f"Wiadomości: {len(messages)}")
    print(f"Odbiorca testowy: {to_email}")
    print()

    # Uzyskaj token
    token = acquire_token()

    sent = 0
    failed = 0

    for i, msg in enumerate(messages, 1):
        contact = msg["contact"]
        message = msg["message"]
        subject = f"[TEST] {message['subject']}"

        # Użyj body_html jeśli dostępny, inaczej konwertuj plain text
        if "body_html" in message:
            body_html = message["body_html"]
        else:
            body_html = plain_to_html(message["body"])

        # Dodaj nagłówek testowy
        test_header = (
            f'<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 10px; '
            f'margin-bottom: 15px; border-radius: 4px; font-size: 0.9em;">'
            f'⚠️ <strong>TEST</strong> — ten mail byłby wysłany do: '
            f'{contact["first_name"]} {contact["last_name"]} ({contact["company"]})'
            f'</div>'
        )
        body_html = test_header + body_html

        print(f"  [{i}/{len(messages)}] {contact['company']} — {subject}")
        ok = send_mail(token, to_email, subject, body_html)
        if ok:
            sent += 1
        else:
            failed += 1

    print()
    print(f"Wysłano: {sent}, Błędów: {failed}")


if __name__ == "__main__":
    main()
