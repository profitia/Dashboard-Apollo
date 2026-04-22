"""
Notifier — wysyła powiadomienia o nowych sekwencjach.

Adaptery: log | json_report | email | webhook
Skonfiguruj w campaign_config.yaml (notification_channels).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


def _format_notification(sequence_result: dict, build_result: dict) -> str:
    """Formatuje powiadomienie jako czytelny tekst."""
    seq_name = sequence_result.get("sequence_name", "")
    seq_id = sequence_result.get("sequence_id", "N/A")
    article_title = build_result.get("article_title", "")
    article_url = build_result.get("article_url", "")
    company = build_result.get("company_name", "")
    contacts_count = sequence_result.get("contacts_enrolled", 0)
    tier_breakdown = build_result.get("tier_breakdown", {})
    enrichment_status = build_result.get("enrichment_status", "")
    warnings = sequence_result.get("errors", [])
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "=" * 60,
        "NOWA SEKWENCJA — spendguru_market_news",
        "=" * 60,
        f"Sekwencja:     {seq_name}",
        f"Apollo ID:     {seq_id}",
        f"Artykuł:       {article_title}",
        f"URL:           {article_url}",
        f"Firma:         {company}",
        f"Kontaktów:     {contacts_count}",
        f"Tier 1:        {tier_breakdown.get('tier_1', 0)}",
        f"Tier 2:        {tier_breakdown.get('tier_2', 0)}",
        f"Tier 3:        {tier_breakdown.get('tier_3', 0)}",
        f"Enrichment:    {enrichment_status}",
        f"Wygenerowano:  {created_at}",
    ]
    if warnings:
        lines.append("")
        lines.append(f"Ostrzeżenia ({len(warnings)}):")
        for w in warnings[:5]:
            lines.append(f"  - {w}")
    lines.append("=" * 60)
    return "\n".join(lines)


def notify(
    sequence_result: dict,
    build_result: dict,
    campaign_config: dict,
    report_dir: str = "outputs/news",
):
    """
    Wysyła powiadomienie przez skonfigurowane kanały.

    Args:
        sequence_result: wynik create_news_sequence()
        build_result: dodatkowe metadane (article_title, url, firma, tiery)
        campaign_config: konfiguracja kampanii
        report_dir: katalog na raporty JSON
    """
    channels = campaign_config.get("notification_channels", ["log"])
    message = _format_notification(sequence_result, build_result)

    for channel in channels:
        if channel == "log":
            _notify_log(message)
        elif channel == "json_report":
            _notify_json_report(sequence_result, build_result, report_dir)
        elif channel == "email":
            _notify_email(message, campaign_config)
        elif channel == "webhook":
            _notify_webhook(sequence_result, build_result, campaign_config)
        else:
            log.warning("Unknown notification channel: %s", channel)


def _notify_log(message: str):
    for line in message.split("\n"):
        log.info(line)


def _notify_json_report(sequence_result: dict, build_result: dict, report_dir: str):
    os.makedirs(report_dir, exist_ok=True)
    seq_name = sequence_result.get("sequence_name", "unknown").replace("/", "-")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{seq_name[:50]}.json"
    path = os.path.join(report_dir, filename)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence_result,
        "build_context": build_result,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log.info("JSON report saved: %s", path)


def _notify_email(message: str, campaign_config: dict):
    """Wysyła e-mail powiadomienie przez Office365."""
    to_email = campaign_config.get("notification_email_to", "")
    if not to_email:
        log.warning("notification_email_to not configured — skipping email notification")
        return
    try:
        import subprocess, sys
        mail_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
            "Integracja z Office365", "send_mail.py"
        )
        subject = f"[SpendGuru News] Nowa sekwencja: {campaign_config.get('campaign_id', '')}"
        if os.path.exists(mail_script):
            subprocess.run(
                [sys.executable, mail_script, "send", to_email, subject, message],
                timeout=30, capture_output=True
            )
            log.info("Email notification sent to %s", to_email)
        else:
            log.warning("send_mail.py not found — skipping email notification")
    except Exception as exc:
        log.warning("Email notification failed: %s", exc)


def _notify_webhook(sequence_result: dict, build_result: dict, campaign_config: dict):
    """Wysyła JSON webhook."""
    webhook_url = campaign_config.get("notification_webhook_url", "")
    if not webhook_url:
        log.warning("notification_webhook_url not configured — skipping webhook")
        return
    try:
        import requests
        payload = {
            "event": "sequence_created",
            "campaign": campaign_config.get("campaign_id"),
            "sequence_name": sequence_result.get("sequence_name"),
            "sequence_id": sequence_result.get("sequence_id"),
            "article_title": build_result.get("article_title"),
            "article_url": build_result.get("article_url"),
            "company": build_result.get("company_name"),
            "contacts_enrolled": sequence_result.get("contacts_enrolled"),
            "tier_breakdown": build_result.get("tier_breakdown"),
        }
        resp = requests.post(webhook_url, json=payload, timeout=10)
        log.info("Webhook sent: status %d", resp.status_code)
    except Exception as exc:
        log.warning("Webhook notification failed: %s", exc)
