"""
Apollo Enrollment Preflight — obowiązkowa walidacja przed enrollmentem.

Sprawdza dla każdego kontaktu:
1. Czy 6 custom fields (sg_email_step_*) jest ustawione i niepuste
2. Czy subject/body nie zawierają nierozwiązanych placeholderów
3. Czy link Calendly jest poprawny (jeśli używany)
4. Czy kontakt nie jest zablokowany przez inną kampanię Apollo

Jeśli warunek nie jest spełniony — kontakt NIE jest enrollowany,
a problem jest jasno opisany w raporcie preflight.
"""

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

# 6 wymaganych pól custom fields w kolejności stepów
REQUIRED_CUSTOM_FIELDS = [
    "sg_email_step_1_subject",
    "sg_email_step_1_body",
    "sg_email_step_2_subject",
    "sg_email_step_2_body",
    "sg_email_step_3_subject",
    "sg_email_step_3_body",
]

# Wzorce placeholderów, które NIE powinny być w treści
UNRESOLVED_PLACEHOLDER_PATTERNS = [
    r"\{\{[^}]+\}\}",                          # {{cokolwiek}}
    r"\[link do Calendly\]",                    # [link do Calendly]
    r"\[imię\]",                                # [imię]
    r"\[stanowisko\]",                          # [stanowisko]
    r"\[firma\]",                                # [firma]
    r"\[BRAK[^\]]*\]",                          # [BRAK ...]
    r"\[TODO[^\]]*\]",                          # [TODO ...]
]

CALENDLY_URL_PATTERN = re.compile(
    r"https://calendly\.com/profitia/[a-z0-9\-]+"
)


def preflight_contact(
    contact_email: str,
    custom_field_values: dict[str, str],
    apollo_contact: dict | None = None,
    target_sequence_id: str | None = None,
) -> dict[str, Any]:
    """
    Przeprowadza preflight check dla jednego kontaktu.

    Args:
        contact_email: email kontaktu
        custom_field_values: dict {field_name: value} z 6 polami sg_email_step_*
        apollo_contact: (opcjonalny) pełny obiekt kontaktu z Apollo API
        target_sequence_id: (opcjonalny) ID sekwencji docelowej

    Returns:
        dict z wynikiem:
        {
            "email": str,
            "passed": bool,
            "errors": list[str],         # blokujące — kontakt NIE może być enrollowany
            "warnings": list[str],       # niekrytyczne — kontakt może być enrollowany
            "checks": dict,              # szczegóły każdego checku
        }
    """
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    # ── CHECK 1: Czy 6 custom fields jest ustawione i niepuste ──
    missing_fields = []
    empty_fields = []
    for field_name in REQUIRED_CUSTOM_FIELDS:
        value = custom_field_values.get(field_name)
        if value is None:
            missing_fields.append(field_name)
        elif not str(value).strip():
            empty_fields.append(field_name)

    if missing_fields:
        errors.append(f"Brakujące custom fields: {', '.join(missing_fields)}")
    if empty_fields:
        errors.append(f"Puste custom fields: {', '.join(empty_fields)}")

    checks["custom_fields_present"] = len(missing_fields) == 0
    checks["custom_fields_nonempty"] = len(empty_fields) == 0
    checks["missing_fields"] = missing_fields
    checks["empty_fields"] = empty_fields

    # ── CHECK 2: Brak nierozwiązanych placeholderów ──
    unresolved_found = []
    for field_name, value in custom_field_values.items():
        if not value:
            continue
        for pattern in UNRESOLVED_PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, str(value), re.IGNORECASE)
            for match in matches:
                unresolved_found.append({"field": field_name, "placeholder": match})

    if unresolved_found:
        errors.append(
            f"Nierozwiązane placeholdery ({len(unresolved_found)}): "
            + "; ".join(f"{u['field']}→{u['placeholder']}" for u in unresolved_found[:5])
        )

    checks["no_unresolved_placeholders"] = len(unresolved_found) == 0
    checks["unresolved_placeholders"] = unresolved_found

    # ── CHECK 3: Calendly link poprawny (jeśli występuje) ──
    calendly_ok = True
    calendly_issues = []
    for field_name, value in custom_field_values.items():
        if not value:
            continue
        # Szukaj jakiegokolwiek calendly.com linku
        calendly_refs = re.findall(r"https?://calendly\.com/\S+", str(value))
        for ref in calendly_refs:
            if not CALENDLY_URL_PATTERN.match(ref):
                calendly_ok = False
                calendly_issues.append({"field": field_name, "url": ref})

        # Szukaj niekompletnych placeholderów Calendly
        if "[link do calendly]" in str(value).lower() or "[calendly]" in str(value).lower():
            calendly_ok = False
            calendly_issues.append({"field": field_name, "url": "[placeholder]"})

    if not calendly_ok:
        errors.append(
            f"Niepoprawny Calendly link: "
            + "; ".join(f"{c['field']}→{c['url']}" for c in calendly_issues[:3])
        )

    checks["calendly_links_valid"] = calendly_ok
    checks["calendly_issues"] = calendly_issues

    # ── CHECK 4: Kontakt nie jest zablokowany przez inną kampanię ──
    campaign_block = None
    if apollo_contact:
        campaign_ids = apollo_contact.get("emailer_campaign_ids", [])
        campaign_statuses = apollo_contact.get("contact_campaign_statuses", [])

        active_campaigns = [
            cs for cs in campaign_statuses
            if cs.get("status") in ("active", "paused")
            and cs.get("emailer_campaign_id") != target_sequence_id
        ]

        if active_campaigns:
            campaign_block = "contacts_active_in_other_campaigns"
            campaign_names = [cs.get("emailer_campaign_id", "?") for cs in active_campaigns]
            warnings.append(
                f"Kontakt aktywny w {len(active_campaigns)} innych kampaniach: "
                + ", ".join(campaign_names[:3])
            )

        finished_campaigns = [
            cs for cs in campaign_statuses
            if cs.get("status") == "finished"
        ]
        if finished_campaigns:
            campaign_block = campaign_block or "contacts_finished_in_other_campaigns"
            warnings.append(
                f"Kontakt zakończył {len(finished_campaigns)} kampanii "
                "(może wymagać bypass flag)"
            )

    checks["no_campaign_block"] = campaign_block is None
    checks["campaign_block_reason"] = campaign_block

    # ── Podsumowanie ──
    passed = len(errors) == 0

    if not passed:
        log.warning("Preflight FAIL dla %s: %s", contact_email, "; ".join(errors))
    else:
        log.info("Preflight PASS dla %s", contact_email)

    return {
        "email": contact_email,
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def preflight_batch(
    contacts: list[dict],
    target_sequence_id: str | None = None,
) -> dict[str, Any]:
    """
    Preflight check dla batcha kontaktów.

    Args:
        contacts: lista dict-ów, każdy z:
            - email: str
            - custom_field_values: dict {field_name: value}
            - apollo_contact: (opcjonalny) obiekt z Apollo
        target_sequence_id: ID docelowej sekwencji

    Returns:
        dict z:
        - total: int
        - passed: int
        - failed: int
        - results: list[dict] — wynik per kontakt
        - enrollable_emails: list[str] — emaile, które przeszły preflight
        - blocked_emails: list[str] — emaile, które nie przeszły
    """
    results = []
    enrollable = []
    blocked = []

    for contact in contacts:
        email = contact.get("email", "")
        cf_values = contact.get("custom_field_values", {})
        apollo_contact = contact.get("apollo_contact")

        result = preflight_contact(
            contact_email=email,
            custom_field_values=cf_values,
            apollo_contact=apollo_contact,
            target_sequence_id=target_sequence_id,
        )
        results.append(result)

        if result["passed"]:
            enrollable.append(email)
        else:
            blocked.append(email)

    passed_count = len(enrollable)
    failed_count = len(blocked)
    total = len(contacts)

    log.info(
        "Preflight batch: %d/%d passed, %d blocked",
        passed_count, total, failed_count,
    )

    return {
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "results": results,
        "enrollable_emails": enrollable,
        "blocked_emails": blocked,
    }
