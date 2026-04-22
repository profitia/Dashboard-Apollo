"""
News Draft Builder — przygotowuje draft kampanii Apollo dla artykułu i kontaktów.

Logika (draft-only, bez auto-enrollmentu):
1. Generuje nazwę sekwencji wg konwencji NEWS-{date}-{company}-{topic}
2. Wyszukuje istniejący kontakt po emailu (search_contact)
3. Jeśli brak — tworzy nowy z run_dedupe=True
4. Dodaje kontakt do właściwej listy Apollo (per tier: PL Tier N do market_news VSC)
5. Ustawia stage: "News pipeline - drafted"
6. Zapisuje custom fields per kontakt (sg_market_news_email_step_N_subject/body)
7. NIE enrolluje do sekwencji wysyłkowej — enrollment ręczny po zatwierdzeniu
8. Wysyła powiadomienie email na adres approval_email_to (Office365)
"""
from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


def _get_apollo_client():
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    integracje_dir = os.path.join(root_dir, "Integracje")
    if integracje_dir not in sys.path:
        sys.path.insert(0, integracje_dir)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(integracje_dir, ".env"))
    except ImportError:
        pass
    from apollo_client import ApolloClient
    return ApolloClient()


def _slugify(text: str, max_len: int = 30) -> str:
    """Konwertuje tekst do slug (lowercase, myślniki)."""
    slug = text.lower()
    slug = re.sub(r"[ąćęłńóśźż]", lambda m: {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l",
        "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"
    }.get(m.group(), m.group()), slug)
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)
    slug = re.sub(r"[\s\-]+", "-", slug).strip("-")
    return slug[:max_len]


def build_sequence_name(
    article_date: str | datetime | None,
    company_name: str,
    article_title: str,
    campaign_config: dict,
) -> str:
    """
    Generuje nazwę sekwencji Apollo.
    Format: NEWS-{YYYY-MM-DD}-{Company}-{Topic}
    """
    prefix = campaign_config.get("sequence_naming", {}).get("prefix", "NEWS")
    max_company = campaign_config.get("sequence_naming", {}).get("max_company_slug_len", 30)
    max_topic = campaign_config.get("sequence_naming", {}).get("max_topic_slug_len", 40)

    if isinstance(article_date, datetime):
        date_str = article_date.strftime("%Y-%m-%d")
    else:
        date_str = (article_date or datetime.now(timezone.utc).isoformat())[:10]
    company_slug = _slugify(company_name, max_company)
    topic_slug = _slugify(article_title, max_topic)

    return f"{prefix}-{date_str}-{company_slug}-{topic_slug}"


def _outreach_pack_to_custom_fields(outreach_pack) -> dict[str, str]:
    """Mapuje OutreachPack → dict pól custom Apollo (prefix: sg_market_news)."""
    try:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        src_dir = os.path.join(root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from core.email_signature import body_to_html
    except ImportError:
        def body_to_html(b): return f"<p>{b}</p>"

    def _nosig_html(step: dict) -> str:
        """HTML bez podpisu (podpis w osobnym polu Apollo)."""
        body_core = step.get("body_core") or step.get("body", "")
        sig_marker = "Z poważaniem,"
        if sig_marker in body_core:
            body_core = body_core[:body_core.index(sig_marker)].rstrip()
        return body_to_html(body_core)

    fields = {
        "sg_market_news_email_step_1_subject": outreach_pack.email_1.get("subject", ""),
        "sg_market_news_email_step_1_body": _nosig_html(outreach_pack.email_1),
        "sg_market_news_email_step_2_subject": outreach_pack.follow_up_1.get("subject", ""),
        "sg_market_news_email_step_2_body": _nosig_html(outreach_pack.follow_up_1),
        "sg_market_news_email_step_3_subject": outreach_pack.follow_up_2.get("subject", ""),
        "sg_market_news_email_step_3_body": _nosig_html(outreach_pack.follow_up_2),
    }
    for k, v in fields.items():
        if len(v) > 4900:
            fields[k] = v[:4900]
    return fields


def _find_or_create_apollo_contact(client, contact) -> str | None:
    """
    Szuka CRM kontaktu w Apollo po emailu. Jeśli nie istnieje — tworzy z run_dedupe=True.

    WAŻNE: Wymaga contact.email. Kontakt bez emaila nie może być importowany do CRM.
    Zwraca CRM contact ID (nie people/prospecting ID) lub None.

    people_id (z mixed_people/api_search) NIE jest tym samym co CRM contact ID.
    Tylko CRM contact ID może być używane do operacji CRM (lista, stage, custom fields).
    """
    if not contact.email:
        # Brak emaila — nie można znaleźć ani stworzyć CRM contact
        return None

    # 1. Szukaj po emailu w CRM (contacts/search zwraca CRM contacts, nie people)
    try:
        existing = client.search_contact(contact.email)
        if existing:
            found_id = existing.get("id")
            log.debug("[CRM] Contact found by email: %s → crm_id=%s", contact.email, found_id)
            return found_id
    except Exception as exc:
        log.debug("[CRM] Contact search failed for %s: %s", contact.email, exc)

    # 2. Utwórz nowy CRM kontakt z run_dedupe=True
    try:
        payload = {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "title": contact.job_title,
            "organization_name": contact.company_name,
            "run_dedupe": True,
        }
        if contact.linkedin_url:
            payload["linkedin_url"] = contact.linkedin_url

        resp = client._post("contacts", payload)
        contact_data = resp.get("contact", {}) if isinstance(resp, dict) else {}
        crm_id = contact_data.get("id")
        log.info("[CRM] Contact created: %s → crm_id=%s", contact.email, crm_id)
        return crm_id
    except Exception as exc:
        log.warning("[CRM] Failed to create CRM contact for %s: %s", contact.email, exc)
        return None


def _add_to_apollo_list(client, contact_id: str, list_name: str) -> bool:
    """Dodaje CRM kontakt do listy Apollo (wymaga CRM contact ID, nie people/prospecting ID).

    Używa dwóch metod:
    1. POST /api/v1/labels/{label_id}/add_contact_ids (właściwy endpoint Apollo)
    2. Fallback: PATCH /api/v1/contacts/{contact_id} z label_ids=[label_id]
    """
    import requests as _req

    all_labels: list = []
    try:
        labels_raw = client._get("labels") or []
        # Apollo GET /labels zwraca bezpośrednio listę, nie słownik
        if isinstance(labels_raw, list):
            all_labels = labels_raw
        elif isinstance(labels_raw, dict):
            all_labels = labels_raw.get("labels", [])
        else:
            all_labels = []
        label_id = next((l["id"] for l in all_labels if l.get("name") == list_name), None)
    except Exception as exc:
        log.warning("[LIST] Failed to fetch Apollo labels: %s", exc)
        return False

    if not label_id:
        log.warning("[LIST] Apollo list not found: '%s' (searched %d labels)",
                    list_name, len(all_labels))
        return False

    # Primary: POST /api/v1/labels/{label_id}/add_contact_ids
    # NOTE: Must use /api/v1/ path — /v1/ returns 404 for this endpoint
    try:
        api_base = "https://api.apollo.io/api/v1"
        resp = _req.post(
            f"{api_base}/labels/{label_id}/add_contact_ids",
            json={"contact_ids": [contact_id]},
            headers=client.headers,
        )
        resp.raise_for_status()
        log.debug("[LIST] Added CRM contact %s to list '%s' (label_id=%s)",
                  contact_id, list_name, label_id)
        return True
    except Exception as exc:
        log.warning("[LIST] Primary add_contact_ids failed for contact %s list '%s': %s — trying fallback",
                    contact_id, list_name, exc)

    # Fallback: PATCH /api/v1/contacts/{contact_id} with label_ids
    # NOTE: This APPENDS label; Apollo merges label_ids on PATCH
    try:
        client.update_contact(contact_id, label_ids=[label_id])
        log.debug("[LIST] Fallback label_ids PATCH succeeded for %s → list '%s'",
                  contact_id, list_name)
        return True
    except Exception as exc2:
        log.warning("[LIST] Fallback label_ids PATCH also failed for contact %s list '%s': %s",
                    contact_id, list_name, exc2)
        return False


def _set_contact_stage(client, contact_id: str, stage_name: str) -> bool:
    """
    Ustawia stage kontaktu w Apollo (wyszukuje ID stage'u po nazwie).
    Wymaga live API test — Apollo musi mieć zdefiniowany stage o tej nazwie.
    """
    try:
        data = client._get("contact_stages") or {}
        stages = data.get("contact_stages", [])
        stage_id = next((s["id"] for s in stages if s.get("name") == stage_name), None)
        if not stage_id:
            log.warning("Apollo contact stage not found: '%s' — skipping stage update", stage_name)
            return False
        client.update_contact(contact_id, contact_stage_id=stage_id)
        log.debug("Stage '%s' set for contact_id=%s", stage_name, contact_id)
        return True
    except Exception as exc:
        log.warning("Failed to set stage '%s' for contact %s: %s", stage_name, contact_id, exc)
        return False


def _body_to_html(text: str) -> str:
    """Konwertuje plain text body na HTML (escape + newlines → <br>)."""
    import html as _html
    return _html.escape(text or "").replace("\n", "<br>")


_STATUS_META = {
    "READY_FOR_REVIEW": {
        "banner_bg":    "#d4edda",
        "banner_border": "#28a745",
        "banner_text":  "#155724",
        "emoji":        "🟢",
        "headline":     "FLOW GOTOWY DO REVIEW I URUCHOMIENIA W APOLLO",
        "subline":      "Artykuł zakwalifikowany · Firma rozpoznana · Kontakt znaleziony · Email dostępny · Treści gotowe",
        "label":        "Gotowy do review",
        "email_label":  None,  # show email as-is
    },
    "BLOCKED_NO_EMAIL": {
        "banner_bg":    "#f8d7da",
        "banner_border": "#dc3545",
        "banner_text":  "#721c24",
        "emoji":        "🔴",
        "headline":     "FLOW ZATRZYMANY — BRAK ADRESU EMAIL",
        "subline":      "Artykuł zakwalifikowany · Firma rozpoznana · Osoba rozpoznana · Treści gotowe · <b>Brak adresu email — sekwencja nie jest gotowa do uruchomienia w Apollo</b>",
        "label":        "Zatrzymany — brak emaila",
        "email_label":  "brak adresu email",
    },
}


def _build_status_notification_html(
    status: str,
    article_title: str,
    article_url: str,
    company_name: str,
    contact_blocks: list[dict],
    campaign_name: str = "spendguru_market_news",
    contact_stage: str = "News pipeline - drafted",
) -> str:
    """
    Buduje HTML body powiadomienia o statusie flow.

    status: "READY_FOR_REVIEW" | "BLOCKED_NO_EMAIL"

    contact_blocks: lista dict z kluczami:
        first_name, last_name, email, tier, tier_label, list_name
        step_1_subject, step_1_body,
        step_2_subject, step_2_body,
        step_3_subject, step_3_body  (opcjonalne — "" jeśli brak)
    """
    import html as _html

    meta = _STATUS_META.get(status, _STATUS_META["READY_FOR_REVIEW"])
    blocked = (status == "BLOCKED_NO_EMAIL")
    stage_display = "—" if blocked else contact_stage

    # --- Banner ---
    banner = f"""
<div style="background:{meta['banner_bg']};border:2px solid {meta['banner_border']};border-radius:8px;padding:16px 20px;margin-bottom:24px">
  <h2 style="color:{meta['banner_text']};margin:0;font-size:18px;font-weight:bold">
    {meta['emoji']} {meta['headline']}
  </h2>
  <p style="color:{meta['banner_text']};margin:8px 0 0 0;font-size:13px">{meta['subline']}</p>
</div>"""

    # --- Blocked reason box ---
    reason_box = ""
    if blocked:
        reason_box = """
<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:12px 16px;margin-bottom:20px;font-size:14px">
  <b>⚠ Powód zatrzymania:</b> Brak adresu email — kontakt rozpoznany w Apollo, ale adres e-mail nie jest dostępny.<br>
  <span style="color:#555">Flow nie jest gotowy do uruchomienia w Apollo. Wymaga ręcznego uzupełnienia emaila lub enrichmentu.</span>
</div>"""

    # --- Article section ---
    article_url_safe = _html.escape(article_url or "")
    article_title_safe = _html.escape(article_title or "")
    company_name_safe = _html.escape(company_name or "")

    def _row(label, value, bg="#fff"):
        return f'<tr style="background:{bg}"><td style="padding:6px 12px;color:#666;width:160px;white-space:nowrap">{label}</td><td style="padding:6px 12px">{value}</td></tr>'

    article_rows = (
        _row("Kampania:", _html.escape(campaign_name), "#f8f9fa") +
        _row("Status:", f'<b style="color:{meta["banner_text"]}">{meta["label"]}</b>') +
        _row("Artykuł:", article_title_safe, "#f8f9fa") +
        _row("Link:", f'<a href="{article_url_safe}" style="color:#0056b3">{article_url_safe}</a>') +
        _row("Firma:", f"<b>{company_name_safe}</b>", "#f8f9fa")
    )

    article_section = f"""
<table style="border-collapse:collapse;width:100%;margin-bottom:24px;font-size:14px;border:1px solid #dee2e6;border-radius:4px">
  <tr style="background:#343a40">
    <td colspan="2" style="padding:8px 12px;font-weight:bold;color:#fff;font-size:13px;letter-spacing:.05em">ARTYKUŁ I FIRMA</td>
  </tr>
  {article_rows}
</table>"""

    # --- Contact blocks ---
    contact_html_parts = []
    for i, cb in enumerate(contact_blocks, 1):
        email_val = cb.get("email", "")
        if blocked or not email_val:
            email_display = '<span style="color:#dc3545;font-weight:bold">brak adresu email</span>'
        else:
            email_display = _html.escape(email_val)

        list_name = _html.escape(cb.get("list_name") or "—")
        contact_rows = (
            _row("Tier:", _html.escape(cb.get("tier_label") or cb.get("tier") or ""), "#f8f9fa") +
            _row("Imię i nazwisko:", _html.escape(f"{cb.get('first_name', '')} {cb.get('last_name', '')}".strip())) +
            _row("Email:", email_display, "#f8f9fa") +
            _row("Lista Apollo:", list_name) +
            _row("Stage Apollo:", _html.escape(stage_display), "#f8f9fa")
        )
        if blocked:
            contact_rows += _row(
                "Powód zatrzymania:",
                '<b style="color:#dc3545">Brak adresu email</b>',
            )

        # --- Sequence steps ---
        steps_html = ""
        for step_n, step_key_prefix in [(1, "step_1"), (2, "step_2"), (3, "step_3")]:
            subj = cb.get(f"{step_key_prefix}_subject", "")
            body = cb.get(f"{step_key_prefix}_body", "")
            if not subj and not body:
                continue
            step_color = {"step_1": "#0062cc", "step_2": "#6f42c1", "step_3": "#20c997"}.get(step_key_prefix, "#333")
            body_html_content = _body_to_html(body)
            steps_html += f"""
<div style="margin:12px 0;padding:12px 16px;border-left:4px solid {step_color};background:#f8f9fa">
  <div style="font-weight:bold;color:{step_color};font-size:13px;margin-bottom:6px">Step {step_n}</div>
  <div style="margin-bottom:4px"><b>Temat:</b> {_html.escape(subj)}</div>
  <div style="margin-top:8px;padding:10px;background:#fff;border:1px solid #dee2e6;border-radius:4px;font-size:13px;line-height:1.6">{body_html_content}</div>
</div>"""

        contact_section_header = f'<div style="font-weight:bold;color:#fff;font-size:13px;letter-spacing:.05em">KONTAKT {i}</div>'
        contact_html_parts.append(f"""
<table style="border-collapse:collapse;width:100%;margin-bottom:16px;font-size:14px;border:1px solid #dee2e6">
  <tr style="background:#495057">
    <td colspan="2" style="padding:8px 12px">{contact_section_header}</td>
  </tr>
  {contact_rows}
</table>
{"" if not steps_html else f'<div style="margin-bottom:24px"><div style="font-weight:bold;color:#333;font-size:13px;margin-bottom:8px;padding:4px 0;border-bottom:1px solid #dee2e6">SEKWENCJA MAILOWA (Step 1–3)</div>{steps_html}</div>'}""")

    contacts_block = "".join(contact_html_parts) or '<p style="color:#888">Brak kontaktów.</p>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:820px;margin:0 auto;padding:16px">
{banner}
{reason_box}
{article_section}
{contacts_block}
<hr style="margin:24px 0;border:none;border-top:1px solid #dee2e6">
<p style="color:#888;font-size:12px">Wiadomość wygenerowana automatycznie przez AI Outreach Pipeline — {campaign_name}.</p>
</body></html>"""


def _send_draft_approval_email(
    article_title: str,
    article_url: str,
    company_name: str,
    contact_blocks: list[dict],
    campaign_config: dict,
    status: str = "READY_FOR_REVIEW",
) -> bool:
    """
    Wysyła powiadomienie email przez Office365.

    status: "READY_FOR_REVIEW" | "BLOCKED_NO_EMAIL"
    Temat jest zawsze taki sam (wymaganie biznesowe):
        "Kampania spendguru_market_news czeka na zatwierdzenie"
    """
    to_email = campaign_config.get("approval_email_to", "")
    if not to_email:
        log.warning("approval_email_to not configured — skipping approval email")
        return False

    campaign_name = campaign_config.get("campaign_id", "spendguru_market_news")
    contact_stage = campaign_config.get("contact_stage_draft", "News pipeline - drafted")

    # Temat stały dla obu statusów — wymaganie biznesowe
    subject = f"Kampania {campaign_name} czeka na zatwierdzenie"

    body_html = _build_status_notification_html(
        status=status,
        article_title=article_title,
        article_url=article_url,
        company_name=company_name,
        contact_blocks=contact_blocks,
        campaign_name=campaign_name,
        contact_stage=contact_stage,
    )

    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        mail_dir = os.path.join(root_dir, "Integracja z Office365")
        if mail_dir not in sys.path:
            sys.path.insert(0, mail_dir)
        import importlib.util
        spec = importlib.util.spec_from_file_location("send_mail", os.path.join(mail_dir, "send_mail.py"))
        send_mail_mod = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(send_mail_mod)  # type: ignore
        send_mail_mod.send_single(to_email, subject, body_html)
        log.info("[Notifier] %s email sent to %s — company: %s", status, to_email, company_name)
        return True
    except Exception as exc:
        log.warning("[Notifier] Failed to send %s email: %s", status, exc)
        return False


def send_blocked_no_email_notification(
    article_title: str,
    article_url: str,
    company_name: str,
    contacts_with_packs: list[dict],  # [{contact: ContactRecord, pack: OutreachPack}]
    campaign_config: dict,
) -> bool:
    """
    Wysyła powiadomienie BLOCKED_NO_EMAIL po przetworzeniu artykułu,
    gdy kontakty zostały znalezione, treści wygenerowane, ale brak adresu email.

    Używany przez orchestrator gdy validate_contact_threshold zwraca False
    z powodu braku emaili, ale contacts nie jest puste.
    """
    if not campaign_config.get("send_blocked_email_notification", True):
        log.info("[Notifier] send_blocked_email_notification=false — skipping BLOCKED_NO_EMAIL notification")
        return False

    to_email = campaign_config.get("approval_email_to", "")
    if not to_email:
        log.warning("[Notifier] approval_email_to not configured — skipping BLOCKED_NO_EMAIL notification")
        return False

    contact_blocks: list[dict] = []
    for item in contacts_with_packs:
        contact = item["contact"]
        pack = item.get("pack")
        block: dict = {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email or "",
            "tier": contact.tier,
            "tier_label": contact.tier_label,
            "list_name": "",  # nie dodany do listy Apollo
            "step_1_subject": "",
            "step_1_body": "",
            "step_2_subject": "",
            "step_2_body": "",
            "step_3_subject": "",
            "step_3_body": "",
        }
        if pack is not None:
            try:
                block["step_1_subject"] = pack.email_1.get("subject", "")
                block["step_1_body"] = pack.email_1.get("body_core") or pack.email_1.get("body", "")
                block["step_2_subject"] = pack.follow_up_1.get("subject", "")
                block["step_2_body"] = pack.follow_up_1.get("body_core") or pack.follow_up_1.get("body", "")
                block["step_3_subject"] = pack.follow_up_2.get("subject", "")
                block["step_3_body"] = pack.follow_up_2.get("body_core") or pack.follow_up_2.get("body", "")
            except Exception as exc:
                log.warning("[Notifier] Failed to extract pack steps for %s: %s", contact.full_name, exc)
        contact_blocks.append(block)

    if not contact_blocks:
        log.warning("[Notifier] No contact blocks for BLOCKED_NO_EMAIL notification — skipping")
        return False

    return _send_draft_approval_email(
        article_title=article_title,
        article_url=article_url,
        company_name=company_name,
        contact_blocks=contact_blocks,
        campaign_config=campaign_config,
        status="BLOCKED_NO_EMAIL",
    )


def create_news_sequence(
    sequence_name: str,
    contacts_with_packs: list[dict],  # [{contact: ContactRecord, pack: OutreachPack}]
    campaign_config: dict,
    dry_run: bool = False,
    article_title: str = "",
    article_url: str = "",
    company_name: str = "",
) -> dict[str, Any]:
    """
    Przetwarza kontakty dla artykułu w trybie draft-only (bez auto-enrollmentu).

    Nowy 4-fazowy flow:
    1. LISTA + STAGE:  Dla WSZYSTKICH kontaktów — dodaj do listy Apollo, ustaw stage.
                       Nie wymaga emaila — kontakty z Apollo search mają apollo_contact_id.
    2. EMAIL REVEAL:   Dla kontaktów bez emaila — próba ujawnienia emaila przez people/match.
    3. CUSTOM FIELDS:  Tylko dla kontaktów Z EMAILEM (po reveal) — zapisz treści sekwencji.
    4. NOTYFIKACJA:    READY_FOR_REVIEW jeśli email dostępny, BLOCKED_NO_EMAIL jeśli nie.

    Brak emaila na etapie search NIE jest jeszcze statusem końcowym —
    dopiero nieudany reveal powoduje BLOCKED_NO_EMAIL.

    Args:
        sequence_name: nazwa draftu (z build_sequence_name)
        contacts_with_packs: lista {contact, pack} — kontakty mogą być bez emaila
        campaign_config: konfiguracja kampanii
        dry_run: jeśli True, nie zapisuje do Apollo
        article_title: tytuł artykułu (do powiadomienia)
        article_url: URL artykułu (do powiadomienia)
        company_name: nazwa firmy (do powiadomienia)

    Returns:
        dict z wynikami operacji, w tym email_available i reveal_attempted
    """
    apollo_lists = campaign_config.get("apollo_lists", {})
    tier_list_map = {
        "tier_1_c_level": apollo_lists.get("tier_1", "PL Tier 1 do market_news VSC"),
        "tier_2_procurement_management": apollo_lists.get("tier_2", "PL Tier 2 do market_news VSC"),
        "tier_3_buyers_operational": apollo_lists.get("tier_3", "PL Tier 3 do market_news VSC"),
    }
    contact_stage = campaign_config.get("contact_stage_draft", "News pipeline - drafted")
    auto_enroll = campaign_config.get("auto_enroll", False)
    send_approval = campaign_config.get("send_approval_email", True)
    use_email_reveal = campaign_config.get("use_email_reveal", True)

    result = {
        "sequence_name": sequence_name,
        "sequence_id": None,        # brak auto-tworzenia sekwencji w tym trybie
        "dry_run": dry_run,
        "auto_enroll": auto_enroll,
        "contacts_processed": 0,
        "contacts_added_to_list": 0,
        "contacts_stage_set": 0,
        "contacts_synced": 0,       # kontakty z zapisanymi custom fields (mają email)
        "contacts_enrolled": 0,     # zawsze 0 w trybie draft-only
        "reveal_attempted": False,
        "reveal_count": 0,          # liczba kontaktów z ujawnionym emailem
        "email_available": False,   # True jeśli ≥1 kontakt ma email po reveal
        "errors": [],
        "contact_results": [],
    }

    # --- DRY RUN: bez API calls ---
    if dry_run:
        contacts_with_email = sum(1 for cp in contacts_with_packs if cp["contact"].email)
        log.info("[DRY RUN] Would draft %d contacts for: %s (%d already have email)",
                 len(contacts_with_packs), sequence_name, contacts_with_email)
        result["contacts_processed"] = len(contacts_with_packs)
        result["email_available"] = contacts_with_email > 0
        result["reveal_attempted"] = (
            use_email_reveal and any(not cp["contact"].email for cp in contacts_with_packs)
        )
        return result

    try:
        client = _get_apollo_client()
    except Exception as exc:
        result["errors"].append(f"Apollo client init failed: {exc}")
        return result

    # ----------------------------------------------------------------
    # FAZA 1: CRM contact import + lista + stage dla kontaktów Z EMAILEM.
    # Kontakty bez emaila: zapisz tylko people_id (z Apollo search) na potrzeby reveal.
    #
    # KLUCZOWE ROZRÓŻNIENIE:
    #   people_id  — ID z mixed_people/api_search (prospecting DB) → tylko do reveal
    #   crm_id     — ID z /contacts (CRM) → do list, stage, custom fields
    # ----------------------------------------------------------------
    people_ids_by_item: dict[int, str | None] = {}  # Apollo prospecting ID — wyłącznie do reveal
    crm_ids_by_item: dict[int, str | None] = {}     # Apollo CRM contact ID — do operacji CRM
    list_names_by_item: dict[int, str] = {}

    for idx, item in enumerate(contacts_with_packs):
        contact = item["contact"]
        result["contacts_processed"] += 1

        # people_id pochodzi z mixed_people/api_search
        people_ids_by_item[idx] = contact.apollo_contact_id
        list_name = tier_list_map.get(contact.tier, "")
        list_names_by_item[idx] = list_name

        if contact.email:
            # Ma email → znajdź lub utwórz CRM contact, dodaj do listy, ustaw stage
            crm_id = _find_or_create_apollo_contact(client, contact)
            crm_ids_by_item[idx] = crm_id

            if not crm_id:
                log.warning("[BUILD] No CRM ID for %s despite email — skipping Phase 1 CRM ops",
                            contact.full_name)
                result["errors"].append(f"No CRM contact_id for {contact.full_name}")
                continue

            if list_name:
                added = _add_to_apollo_list(client, crm_id, list_name)
                if added:
                    result["contacts_added_to_list"] += 1
                    log.info("[BUILD] Added to list '%s': %s (crm_id=%s)",
                             list_name, contact.full_name, crm_id)

            stage_ok = _set_contact_stage(client, crm_id, contact_stage)
            if stage_ok:
                result["contacts_stage_set"] += 1
        else:
            # Brak emaila → brak CRM contact w tej fazie; reveal w Fazie 2
            crm_ids_by_item[idx] = None
            log.info("[BUILD] No email for %s — Phase 1 CRM ops skipped, will attempt reveal",
                     contact.full_name)

        # Brak enrollmentu — auto_enroll=False jest wymuszony w tym workflow
        if auto_enroll:
            log.warning("auto_enroll=True in config but enrollment is disabled in this workflow — skipping")

    # ----------------------------------------------------------------
    # FAZA 2: Email reveal dla kontaktów bez emaila
    # Używa people_id (z Apollo search) — jedyne miejsce gdzie people_id ma zastosowanie.
    # Po udanym reveal: importuj kontakt do CRM, dodaj do listy, ustaw stage.
    # ----------------------------------------------------------------
    contacts_needing_reveal = [
        (idx, item) for idx, item in enumerate(contacts_with_packs)
        if not item["contact"].email and people_ids_by_item.get(idx)
    ]

    if use_email_reveal and contacts_needing_reveal:
        result["reveal_attempted"] = True
        log.info("[Reveal] Attempting email reveal for %d contact(s) without email",
                 len(contacts_needing_reveal))
        for idx, item in contacts_needing_reveal:
            contact = item["contact"]
            people_id = people_ids_by_item[idx]
            try:
                email = client.reveal_email(
                    apollo_id=people_id,
                    first_name=contact.first_name or None,
                    last_name=contact.last_name or None,
                    domain=contact.company_domain or None,
                    organization_name=contact.company_name or None,
                )
                if email:
                    contact.email = email
                    result["reveal_count"] += 1
                    log.info("[Reveal] Email revealed for %s: %s", contact.full_name, email)

                    # Po reveal: importuj do CRM i wykonaj Phase 1 CRM ops
                    crm_id = _find_or_create_apollo_contact(client, contact)
                    crm_ids_by_item[idx] = crm_id

                    if crm_id:
                        log.info("[CRM] CRM contact for %s (post-reveal): crm_id=%s",
                                 contact.full_name, crm_id)
                        list_name = list_names_by_item.get(idx, "")
                        if list_name:
                            added = _add_to_apollo_list(client, crm_id, list_name)
                            if added:
                                result["contacts_added_to_list"] += 1
                                log.info("[BUILD] Added to list '%s': %s (post-reveal, crm_id=%s)",
                                         list_name, contact.full_name, crm_id)
                        stage_ok = _set_contact_stage(client, crm_id, contact_stage)
                        if stage_ok:
                            result["contacts_stage_set"] += 1
                    else:
                        log.warning("[CRM] Could not get CRM ID for %s after reveal (%s)",
                                    contact.full_name, email)
                        result["errors"].append(
                            f"No CRM ID after reveal for {contact.full_name} ({email})"
                        )
                else:
                    log.info("[Reveal] No email revealed for %s (people_id=%s)",
                             contact.full_name, people_id)
            except Exception as exc:
                log.warning("[Reveal] Reveal failed for %s: %s", contact.full_name, exc)
    elif not use_email_reveal:
        log.info("[Reveal] use_email_reveal=false — reveal skipped")

    # ----------------------------------------------------------------
    # FAZA 3: Custom fields tylko dla kontaktów Z EMAILEM i CRM ID (po reveal)
    # Używa crm_id — nigdy people_id.
    # ----------------------------------------------------------------
    approval_contact_blocks: list[dict] = []
    revealed_idxs = {i for i, _ in contacts_needing_reveal}

    for idx, item in enumerate(contacts_with_packs):
        contact = item["contact"]
        pack = item["pack"]
        crm_id = crm_ids_by_item.get(idx)
        list_name = list_names_by_item.get(idx, "")

        contact_entry: dict = {
            "full_name": contact.full_name,
            "email": contact.email or "(no email)",
            "tier": contact.tier,
            "tier_label": contact.tier_label,
            "apollo_person_id": people_ids_by_item.get(idx),    # prospecting ID (reveal only)
            "apollo_crm_contact_id": crm_id,                    # CRM ID (list/stage/fields)
            "list_name": list_name,
            "stage": contact_stage,
            "status": "drafted",
            "email_revealed": idx in revealed_idxs and bool(contact.email),
        }

        if contact.email and crm_id:
            # Kontakt ma email i CRM ID — zapisz custom fields
            custom_fields = _outreach_pack_to_custom_fields(pack)
            try:
                client.update_contact_custom_fields(crm_id, custom_fields)
                result["contacts_synced"] += 1
                log.info("[BUILD] Custom fields synced for %s (%s) crm_id=%s",
                         contact.full_name, contact.email, crm_id)
                contact_entry["status"] = "drafted_with_email"
            except Exception as exc:
                log.warning("[BUILD] Custom field sync failed for %s: %s", contact.full_name, exc)
                result["errors"].append(f"Custom field sync failed: {contact.full_name}: {exc}")

            _step_1_body = pack.email_1.get("body_core") or pack.email_1.get("body", "")
            _step_2_body = pack.follow_up_1.get("body_core") or pack.follow_up_1.get("body", "")
            _step_3_body = pack.follow_up_2.get("body_core") or pack.follow_up_2.get("body", "")

            approval_contact_blocks.append({
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "tier": contact.tier,
                "tier_label": contact.tier_label,
                "list_name": list_name,
                "step_1_subject": pack.email_1.get("subject", ""),
                "step_1_body": _step_1_body,
                "step_2_subject": pack.follow_up_1.get("subject", ""),
                "step_2_body": _step_2_body,
                "step_3_subject": pack.follow_up_2.get("subject", ""),
                "step_3_body": _step_3_body,
            })

        elif contact.email and not crm_id:
            # Ma email, ale tworzenie CRM contact failed
            contact_entry["status"] = "email_available_no_crm"
            log.warning("[BUILD] %s has email but no CRM ID — custom fields not synced",
                        contact.full_name)
        else:
            # Kontakt bez emaila po reveal — zbierz do BLOCKED notyfikacji
            _step_1_body = pack.email_1.get("body_core") or pack.email_1.get("body", "")
            _step_2_body = pack.follow_up_1.get("body_core") or pack.follow_up_1.get("body", "")
            _step_3_body = pack.follow_up_2.get("body_core") or pack.follow_up_2.get("body", "")

            contact_entry["blocked_notification_block"] = {
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": "",
                "tier": contact.tier,
                "tier_label": contact.tier_label,
                "list_name": list_name,
                "step_1_subject": pack.email_1.get("subject", ""),
                "step_1_body": _step_1_body,
                "step_2_subject": pack.follow_up_1.get("subject", ""),
                "step_2_body": _step_2_body,
                "step_3_subject": pack.follow_up_2.get("subject", ""),
                "step_3_body": _step_3_body,
            }

        result["contact_results"].append(contact_entry)

    # ----------------------------------------------------------------
    # FAZA 4: Notyfikacja — READY_FOR_REVIEW lub BLOCKED_NO_EMAIL
    # ----------------------------------------------------------------
    result["email_available"] = bool(approval_contact_blocks)

    if send_approval:
        if approval_contact_blocks:
            # READY_FOR_REVIEW — przynajmniej 1 kontakt z emailem
            _send_draft_approval_email(
                article_title=article_title,
                article_url=article_url,
                company_name=company_name,
                contact_blocks=approval_contact_blocks,
                campaign_config=campaign_config,
                status="READY_FOR_REVIEW",
            )
        else:
            # BLOCKED_NO_EMAIL — żaden kontakt nie ma emaila po reveal
            blocked_blocks = [
                cr["blocked_notification_block"]
                for cr in result["contact_results"]
                if cr.get("blocked_notification_block")
            ]
            if blocked_blocks and campaign_config.get("send_blocked_email_notification", True):
                _send_draft_approval_email(
                    article_title=article_title,
                    article_url=article_url,
                    company_name=company_name,
                    contact_blocks=blocked_blocks,
                    campaign_config=campaign_config,
                    status="BLOCKED_NO_EMAIL",
                )
                log.info("[BUILD] BLOCKED_NO_EMAIL notification sent — %d contacts added to list, reveal failed",
                         result["contacts_added_to_list"])

    log.info(
        "Draft complete: %s — listed=%d, stage=%d, synced=%d, reveal=%d/%s, email_available=%s",
        sequence_name,
        result["contacts_added_to_list"],
        result["contacts_stage_set"],
        result["contacts_synced"],
        result["reveal_count"],
        "attempted" if result["reveal_attempted"] else "skipped",
        result["email_available"],
    )
    return result

