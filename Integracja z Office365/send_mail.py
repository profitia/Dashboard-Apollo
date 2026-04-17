import os
import sys
import csv
import json
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", "http://localhost:3000/auth/callback")
MAIL_FROM = os.getenv("MAIL_FROM")
SCOPES = os.getenv("MAIL_SCOPES", "Mail.Send,User.Read").split(",")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
TOKEN_CACHE_FILE = ".token_cache.json"


def get_msal_app():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )
    return app, cache


def save_cache(cache):
    if cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def acquire_token():
    app, cache = get_msal_app()

    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            save_cache(cache)
            return result["access_token"]

    print("Logowanie przez przeglądarkę...")
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print(f"Błąd inicjalizacji device flow: {json.dumps(flow, indent=2)}")
        sys.exit(1)

    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        save_cache(cache)
        return result["access_token"]
    else:
        print(f"Błąd logowania: {json.dumps(result, indent=2)}")
        sys.exit(1)


def send_mail(access_token, to_email, subject, body_html):
    url = f"{GRAPH_ENDPOINT}/me/sendMail"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body_html,
            },
            "toRecipients": [
                {"emailAddress": {"address": to_email}}
            ],
            "from": {
                "emailAddress": {"address": MAIL_FROM}
            },
        },
        "saveToSentItems": True,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 202:
        print(f"  ✓ Wysłano do: {to_email}")
        return True
    else:
        print(f"  ✗ Błąd wysyłki do {to_email}: {response.status_code} - {response.text}")
        return False


def send_single(to_email, subject, body_html):
    token = acquire_token()
    send_mail(token, to_email, subject, body_html)


def send_bulk_from_csv(csv_path, subject, body_html):
    token = acquire_token()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sent = 0
        failed = 0
        for row in reader:
            email = row.get("email", "").strip()
            if email:
                ok = send_mail(token, email, subject, body_html)
                if ok:
                    sent += 1
                else:
                    failed += 1

    print(f"\nPodsumowanie: wysłano {sent}, błędów {failed}")


def test_connection():
    token = acquire_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{GRAPH_ENDPOINT}/me", headers=headers, timeout=30)
    if response.status_code == 200:
        user = response.json()
        print(f"Zalogowano jako: {user.get('displayName')} ({user.get('mail')})")
        return True
    else:
        print(f"Błąd połączenia: {response.status_code} - {response.text}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie:")
        print("  python send_mail.py test                          - test połączenia")
        print('  python send_mail.py send <email> <temat> <treść>  - wyślij jednego maila')
        print('  python send_mail.py bulk <csv> <temat> <treść>    - wyślij masowo z CSV')
        sys.exit(0)

    command = sys.argv[1]

    if command == "test":
        test_connection()

    elif command == "send":
        if len(sys.argv) < 5:
            print('Użycie: python send_mail.py send <email> "<temat>" "<treść HTML>"')
            sys.exit(1)
        send_single(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "bulk":
        if len(sys.argv) < 5:
            print('Użycie: python send_mail.py bulk <plik.csv> "<temat>" "<treść HTML>"')
            sys.exit(1)
        send_bulk_from_csv(sys.argv[2], sys.argv[3], sys.argv[4])

    else:
        print(f"Nieznana komenda: {command}")
        sys.exit(1)
