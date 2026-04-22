#!/usr/bin/env python3
"""
Wspólny formatter emaili w formacie thread / reply chain.

Buduje trzy-mailowy outreach pack (email_1, follow_up_1, follow_up_2)
ze spójnym formatowaniem, podpisem i historią wątku.

Używany przez wszystkie kampanie: article_triggered, csv_import,
linkedin_posts, experimental i przyszłe.
"""

import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from core.email_signature import (
    SIGNATURE_PLAIN,
    SIGNATURE_HTML,
    SIGNATURE_STANDALONE_HTML,
    META_BLOCK,
    FONT_BASE,
    SENDER_NAME,
    SENDER_BRAND,
    body_to_html,
    strip_llm_signature,
    strip_signature,
)


# ============================================================
# Syntetyczny email kontaktu
# ============================================================

_PL_TRANSLITERATE = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def make_contact_email(contact: dict) -> str:
    """Generuje syntetyczny email z imienia/nazwiska/domeny kontaktu."""
    first = contact.get("first_name", "kontakt").lower().translate(_PL_TRANSLITERATE)
    last = contact.get("last_name", "").lower().translate(_PL_TRANSLITERATE)
    domain = str(contact.get("domain", contact.get("company_domain", "example.com"))).strip()
    domain = domain.removeprefix("https://").removeprefix("http://").lstrip("/")
    return f"{first}.{last}@{domain}"


# ============================================================
# Nagłówki separatora (Outlook-style)
# ============================================================

def _separator_plain(date_str: str, contact: dict, subject: str) -> str:
    """Nagłówek Outlook-style (plain text) nad cytowanym mailem."""
    contact_email = make_contact_email(contact)
    first = contact.get("first_name", "")
    last = contact.get("last_name", "")
    return (
        f"\n\n--------------------------------------------------------------\n"
        f"W dniu {date_str} {SENDER_NAME} napisał:\n"
        f"Do: {first} {last} | {contact_email}\n"
        f"Od: {SENDER_NAME} | {SENDER_BRAND}\n"
        f"Temat: {subject}\n\n"
    )


def _separator_html(date_str: str, contact: dict, subject: str) -> str:
    """Nagłówek Outlook-style (HTML) nad cytowanym mailem."""
    contact_email = make_contact_email(contact)
    first = contact.get("first_name", "")
    last = contact.get("last_name", "")
    style_header = (
        "font-family: Aptos, Calibri, Arial, sans-serif; font-size: 11pt; "
        "color: #000000; line-height: 1.5;"
    )
    style_line = (
        "border: none; border-top: 1px solid #b5b5b5; margin: 20px 0 10px 0;"
    )
    return (
        f'<hr style="{style_line}">'
        f'<div style="{style_header} margin-bottom: 12px;">'
        f'<b>W dniu {date_str} {SENDER_NAME} napisał:</b><br>'
        f'Do: {first} {last} | {contact_email}<br>'
        f'Od: {SENDER_NAME} | {SENDER_BRAND}<br>'
        f'Temat: {subject}'
        f'</div>'
    )


def _strip_meta_tags(html_content: str) -> str:
    """Usuwa META_BLOCK (metatagi + style) z cytowanego HTML (żeby nie duplikować)."""
    for tag in [
        '<meta name="format-detection" content="telephone=no">',
        '<meta name="x-apple-disable-message-reformatting">',
        ('<style>a[x-apple-data-detectors]'
         '{color:inherit !important;text-decoration:none !important;}</style>'),
    ]:
        html_content = html_content.replace(tag, "")
    return html_content.strip()


# ============================================================
# Budowanie email_1 (pierwszy mail)
# ============================================================

def build_email_1(body_core: str, subject: str) -> dict:
    """
    Buduje finalny email_1 z body_core + podpis.

    Returns:
        dict z: subject, body_core, body (full plain), body_html (full HTML),
                body_html_nosig (HTML bez podpisu — do osobnego pola Apollo)
    """
    clean = strip_llm_signature(body_core).rstrip()

    body_full = clean + "\n\n" + SIGNATURE_PLAIN
    body_html_nosig = META_BLOCK + body_to_html(clean)
    html_full = body_html_nosig + SIGNATURE_HTML

    return {
        "subject": subject,
        "body_core": clean,
        "body": body_full,
        "body_html": html_full,
        "body_html_nosig": body_html_nosig,
    }


# ============================================================
# Budowanie follow_up_1 (thread z historią email_1)
# ============================================================

def build_follow_up_1(
    body_core: str,
    email_1: dict,
    contact: dict,
    date_email_1: str,
) -> dict:
    """
    Buduje follow_up_1 z nową treścią + podpis + historia email_1.

    Args:
        body_core: Nowa treść follow-upu (bez podpisu)
        email_1: Dict zwrócony przez build_email_1
        contact: Dict kontaktu (first_name, last_name, domain)
        date_email_1: Data email_1 w formacie DD.MM.RRRR

    Returns:
        dict z: subject, body_core, body (full plain), body_html (full HTML),
                body_html_nosig (HTML bez podpisu — do osobnego pola Apollo)
    """
    clean = strip_llm_signature(body_core).rstrip()
    subject = f"RE: {email_1['subject']}"

    # === body_html_nosig (nowa treść + podpis + historia wątku — do Apollo custom field) ===
    # Podpis jest embedded PRZED thread, bo w FU template nie ma {{pl_signature_tu}}.
    # Thread: separator + cytowany Email 1 (bez meta, bez podpisu)
    quoted_e1 = _strip_meta_tags(email_1["body_html_nosig"])
    body_html_nosig = (
        META_BLOCK
        + body_to_html(clean)
        + SIGNATURE_STANDALONE_HTML
        + _separator_html(date_email_1, contact, email_1["subject"])
        + quoted_e1
    )

    # === PLAIN ===
    plain = clean + "\n\n" + SIGNATURE_PLAIN
    plain += _separator_plain(date_email_1, contact, email_1["subject"])
    plain += email_1["body"]

    # === HTML ===
    html = META_BLOCK
    html += body_to_html(clean)
    html += SIGNATURE_HTML
    html += _separator_html(date_email_1, contact, email_1["subject"]) + "\n"
    html += f'<div style="padding-left: 0;">{email_1["body_html"]}</div>'

    return {
        "subject": subject,
        "body_core": clean,
        "body": plain,
        "body_html": html,
        "body_html_nosig": body_html_nosig,
    }


# ============================================================
# Budowanie follow_up_2 (thread z historią follow_up_1 + email_1)
# ============================================================

def build_follow_up_2(
    body_core: str,
    follow_up_1: dict,
    email_1: dict,
    contact: dict,
    date_follow_up_1: str,
) -> dict:
    """
    Buduje follow_up_2 z nową treścią + podpis + zagnieżdżona historia.

    Args:
        body_core: Nowa treść follow-upu (bez podpisu)
        follow_up_1: Dict zwrócony przez build_follow_up_1
        email_1: Dict zwrócony przez build_email_1
        contact: Dict kontaktu (first_name, last_name, domain)
        date_follow_up_1: Data follow_up_1 w formacie DD.MM.RRRR

    Returns:
        dict z: subject, body_core, body (full plain), body_html (full HTML),
                body_html_nosig (HTML bez podpisu — do osobnego pola Apollo)
    """
    clean = strip_llm_signature(body_core).rstrip()
    subject = f"RE: {email_1['subject']}"

    # === body_html_nosig (nowa treść + podpis + historia wątku — do Apollo custom field) ===
    # Podpis jest embedded PRZED thread, bo w FU template nie ma {{pl_signature_tu}}.
    # Thread: separator + cytowany FU1 (z zagnieżdżonym Email 1)
    # Każda wiadomość w threadzie ma własny podpis — E1 na dole też.
    quoted_fu1 = _strip_meta_tags(follow_up_1["body_html_nosig"])
    body_html_nosig = (
        META_BLOCK
        + body_to_html(clean)
        + SIGNATURE_STANDALONE_HTML
        + _separator_html(date_follow_up_1, contact, follow_up_1["subject"])
        + quoted_fu1
        + SIGNATURE_STANDALONE_HTML
    )

    # === PLAIN ===
    plain = clean + "\n\n" + SIGNATURE_PLAIN
    plain += _separator_plain(date_follow_up_1, contact, follow_up_1["subject"])
    # Cytujemy PEŁNY follow_up_1 (tekst + podpis + separator + email_1)
    plain += follow_up_1["body"]

    # === HTML ===
    html = META_BLOCK
    html += body_to_html(clean)
    html += SIGNATURE_HTML
    html += _separator_html(date_follow_up_1, contact, follow_up_1["subject"]) + "\n"
    # Cytujemy PEŁNY follow_up_1 HTML (bez meta tagów)
    fu1_html = _strip_meta_tags(follow_up_1["body_html"])
    html += f'<div style="padding-left: 0;">{fu1_html}</div>'

    return {
        "subject": subject,
        "body_core": clean,
        "body": plain,
        "body_html": html,
        "body_html_nosig": body_html_nosig,
    }


# ============================================================
# Budowanie pełnego outreach pack (3 maile)
# ============================================================

def build_outreach_pack(
    email_1_subject: str,
    email_1_body_core: str,
    follow_up_1_body_core: str,
    follow_up_2_body_core: str,
    contact: dict,
    date_email_1: str,
    date_follow_up_1: str,
    date_follow_up_2: str,
) -> dict:
    """
    Buduje kompletny outreach pack (3 maile) w formacie thread.

    Args:
        email_1_subject: Temat emaila 1
        email_1_body_core: Treść emaila 1 (bez podpisu)
        follow_up_1_body_core: Treść follow-upu 1 (bez podpisu)
        follow_up_2_body_core: Treść follow-upu 2 (bez podpisu)
        contact: Dict z first_name, last_name, domain
        date_email_1: Data emaila 1 (DD.MM.RRRR)
        date_follow_up_1: Data follow-upu 1 (DD.MM.RRRR)
        date_follow_up_2: Data follow-upu 2 (DD.MM.RRRR)

    Returns:
        dict z kluczami: email_1, follow_up_1, follow_up_2
        Każdy zawiera: subject, body_core, body, body_html
    """
    e1 = build_email_1(email_1_body_core, email_1_subject)
    fu1 = build_follow_up_1(follow_up_1_body_core, e1, contact, date_email_1)
    fu2 = build_follow_up_2(follow_up_2_body_core, fu1, e1, contact, date_follow_up_1)

    return {
        "email_1": e1,
        "follow_up_1": fu1,
        "follow_up_2": fu2,
    }
