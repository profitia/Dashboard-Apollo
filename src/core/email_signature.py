#!/usr/bin/env python3
"""
Wspólny podpis e-mail — stałe i utility.

Jedno źródło prawdy dla formatu podpisu używanego we wszystkich kampaniach
(article_triggered, csv_import, linkedin_posts, experimental, przyszłe).
"""

import html as html_mod


# ============================================================
# Font styles
# ============================================================

FONT_BASE = (
    "font-family: Aptos, Calibri, Arial, sans-serif; "
    "font-size: 11pt; color: #000000; line-height: 1.5;"
)

FONT_PARAGRAPH = (
    "font-family: Aptos, Calibri, Arial, sans-serif; "
    "font-size: 11pt; color: #000000; line-height: 1.5; "
    "margin: 0 0 10px 0;"
)

FONT_LINK = (
    "font-family: Aptos, Calibri, Arial, sans-serif; "
    "font-size: 11pt; color: #0000ff; text-decoration: underline;"
)


# ============================================================
# Nadawca — stałe
# ============================================================

SENDER_NAME = "Tomasz Uściński"
SENDER_TITLE = "Senior Client Partner | Procurement Technology"
SENDER_PHONE = "+48 787 417 293"
SENDER_COMPANY = "PROFITIA Management Consultants Mazurowski i Wspólnicy Spółka Jawna"
SENDER_BRAND = "Profitia"
SENDER_TAGLINE = (
    "SpendGuru Data-driven Procurement | Certyfikowany Partner CIPS w Polsce "
    "| Doradztwo | Szkolenia | Analityka zakupowa"
)
SENDER_ADDRESS = "02-715 Warszawa, Villa Metro, ul. Puławska 145, V p."
CONFIDENTIALITY_NOTICE = (
    "Uwaga: Ten e-mail jest poufny i przeznaczony tylko dla adresata (-ów) tej wiadomości. "
    "Jeżeli nie jesteś adresatem niniejszej wiadomości, usuń oryginał wiadomości "
    "wraz z wszelkimi wydrukami (kopiami) i załącznikami."
)


# ============================================================
# Plain text signature
# ============================================================

SIGNATURE_PLAIN = f"""Pozdrawiam serdecznie,

{SENDER_NAME}
{SENDER_TITLE}
{SENDER_PHONE}

{SENDER_COMPANY}
{SENDER_TAGLINE}
{SENDER_ADDRESS}

{CONFIDENTIALITY_NOTICE}"""


# ============================================================
# HTML signature
# ============================================================

FONT_SIGNATURE_CLOSING = (
    "font-family: Aptos, Calibri, Arial, sans-serif; "
    "font-size: 11pt; color: #000000; line-height: 1.5; "
    "margin: 10px 0 2px 0;"
)

SIGNATURE_HTML = f"""<p style="{FONT_SIGNATURE_CLOSING}">Pozdrawiam serdecznie,</p>
<table cellpadding="0" cellspacing="0" border="0" style="{FONT_BASE}">
  <tr><td style="padding-bottom:0;"><strong style="{FONT_BASE} font-weight:bold;">{SENDER_NAME}</strong></td></tr>
  <tr><td style="{FONT_BASE}">{SENDER_TITLE}</td></tr>
  <tr><td style="{FONT_BASE}">+48&#8203; 787&#8203; 417&#8203; 293</td></tr>
  <tr><td style="height:11pt;">&nbsp;</td></tr>
  <tr><td style="{FONT_BASE} font-weight:bold;"><strong>{SENDER_COMPANY}</strong></td></tr>
  <tr><td style="{FONT_BASE}">{SENDER_TAGLINE}</td></tr>
  <tr><td style="{FONT_BASE}">{SENDER_ADDRESS}</td></tr>
  <tr><td style="height:11pt;">&nbsp;</td></tr>
  <tr><td style="font-family: Aptos, Calibri, Arial, sans-serif; font-size: 9pt; color: #949494; line-height: 1.4;">{CONFIDENTIALITY_NOTICE}</td></tr>
</table>"""


# ============================================================
# Standalone signature HTML — osobne pole Apollo (pl_signature_tu)
# ============================================================
# Używane gdy podpis jest w osobnym custom field, a body zawiera
# tylko treść maila. Template: {{sg_email_step_x_body}}{{pl_signature_tu}}
#
# Różnica vs SIGNATURE_HTML:
# - margin-top: 2px (bo body <p> ma margin-bottom: 10px → łączny gap ≈ 12px)
# - brak META_BLOCK (jest w body)
# - brak pustych paragrafów na początku

FONT_SIGNATURE_STANDALONE_CLOSING = (
    "font-family: Aptos, Calibri, Arial, sans-serif; "
    "font-size: 11pt; color: #000000; line-height: 1.5; "
    "margin: 2px 0 2px 0;"
)

# WAŻNE: Cały HTML w jednej linii — Apollo konwertuje \n na <br /> w merge tagach.
# BEZ <table> — lekki podpis tekstowy dla lepszej deliverability i naturalnego wyglądu.
SIGNATURE_STANDALONE_HTML = (
    f'<p style="{FONT_SIGNATURE_STANDALONE_CLOSING}">Pozdrawiam serdecznie,</p>'
    f'<p style="{FONT_BASE} margin: 0 0 0 0;">'
    f'<strong>{SENDER_NAME}</strong><br>'
    f'{SENDER_TITLE}<br>'
    f'+48&#8203; 787&#8203; 417&#8203; 293'
    f'</p>'
    f'<p style="{FONT_BASE} margin: 8px 0 0 0;">'
    f'<strong>{SENDER_COMPANY}</strong><br>'
    f'{SENDER_TAGLINE}<br>'
    f'{SENDER_ADDRESS}'
    f'</p>'
    f'<p style="font-family: Aptos, Calibri, Arial, sans-serif; font-size: 9pt; color: #949494; line-height: 1.4; margin: 8px 0 0 0;">'
    f'{CONFIDENTIALITY_NOTICE}'
    f'</p>'
)


# ============================================================
# HTML meta block (anti-autodetection)
# ============================================================

META_BLOCK = (
    '<meta name="format-detection" content="telephone=no">'
    '<meta name="x-apple-disable-message-reformatting">'
    '<style>a[x-apple-data-detectors]'
    '{color:inherit !important;text-decoration:none !important;}</style>'
)


# ============================================================
# Utility functions
# ============================================================

def body_to_html(body_text: str) -> str:
    """Konwertuje plain text body na HTML ze stylem Aptos 11pt #000000.

    Używa FONT_PARAGRAPH z kontrolowanym marginem (margin: 0 0 10px 0)
    zamiast domyślnego marginu <p> (~1em), który tworzy zbyt duże odstępy.

    WAŻNE: Elementy łączone BEZ \n — Apollo konwertuje \n w merge tagach
    na <br />, co tworzy niechciane odstępy między paragrafami.
    """
    escaped = html_mod.escape(body_text)
    paragraphs = escaped.split("\n\n")
    parts = [
        f'<p style="{FONT_PARAGRAPH}">{p.replace(chr(10), "<br>")}</p>'
        for p in paragraphs
    ]
    return "".join(parts)


# Placeholdery, które LLM może dodać zamiast podpisu
_SIGNATURE_PLACEHOLDERS = [
    "[Twoje Imi\u0119]",
    "[Imi\u0119 i Nazwisko]",
    "[Podpis]",
    "Pozdrawiam,\n\n[Twoje Imi\u0119]",
    "Pozdrawiam,",
    "Pozdrawiam serdecznie,",
]

# Frazy zakończeniowe, które LLM może dopisać na końcu body
_SIGNOFF_PATTERNS = [
    "Pozdrawiam serdecznie,",
    "Pozdrawiam serdecznie",
    "Pozdrawiam,",
    "Pozdrawiam",
    "Z poważaniem,",
    "Z poważaniem",
    "Serdecznie pozdrawiam,",
    "Serdecznie pozdrawiam",
    "Z pozdrowieniami,",
    "Z pozdrowieniami",
]

# Imię/nazwisko nadawcy, które LLM może dodać po sign-off
_SENDER_NAMES = [
    "Tomasz Uściński",
    "Tomasz",
]


def strip_llm_signature(body: str) -> str:
    """Usuwa sign-off / podpis dodany przez LLM z końca body.

    Obsługuje:
    - placeholdery typu [Twoje Imię]
    - sign-offy: Pozdrawiam, Z poważaniem itp.
    - imię/nazwisko nadawcy po sign-off
    - kombinacje: "Pozdrawiam,\\nTomasz Uściński"
    """
    import re

    text = body.rstrip()

    # 1. Stare placeholdery (kompatybilność wsteczna)
    for placeholder in _SIGNATURE_PLACEHOLDERS:
        if text.endswith(placeholder):
            return text[:-len(placeholder)].rstrip()

    # 2. Usuń trailing sender name (może być po sign-off lub samodzielnie)
    changed = True
    while changed:
        changed = False
        stripped = text.rstrip()
        for name in _SENDER_NAMES:
            if stripped.endswith(name):
                stripped = stripped[:-len(name)].rstrip()
                # Usuń ewentualny separator (myślnik, przecinek, newline) przed imieniem
                stripped = re.sub(r'[\s,\-—–]+$', '', stripped)
                text = stripped
                changed = True
                break

    # 3. Usuń trailing sign-off
    stripped = text.rstrip()
    for signoff in _SIGNOFF_PATTERNS:
        if stripped.endswith(signoff):
            text = stripped[:-len(signoff)].rstrip()
            break

    return text


def strip_signature(body_with_sig: str) -> str:
    """Usuwa podpis z body — szuka 'Pozdrawiam serdecznie,' jako markera."""
    marker = "Pozdrawiam serdecznie,"
    idx = body_with_sig.find(marker)
    if idx > 0:
        return body_with_sig[:idx].rstrip()
    return body_with_sig


def append_signature(message: dict) -> dict:
    """
    Dodaje podpis do wiadomości (plain + HTML).
    Modyfikuje dict in-place i zwraca go.
    """
    body = strip_llm_signature(message.get("body", ""))

    message["body"] = body.rstrip() + "\n\n" + SIGNATURE_PLAIN
    message["body_html"] = (
        META_BLOCK + "\n"
        + body_to_html(body.rstrip()) + "\n"
        + SIGNATURE_HTML
    )
    message["word_count"] = len(body.split())  # bez podpisu
    return message
