"""
Manual Mode — walidacja i konwersja kontaktów podanych przez operatora.

Zasady:
- email podany przez operatora = source of truth (bez nadpisywania)
- tier podany przez operatora = source of truth (bez nadpisywania)
- pipeline tylko sprawdza czy dane techniczne są poprawne (nie puste, właściwy format)
- zero "inteligentnego poprawiania" danych operatora

Wymagane pola na kontakt:
  - email      (niepusty, zawiera @)
  - tier       (jeden z VALID_TIERS)

Pola opcjonalne:
  - full_name, first_name, last_name
  - job_title
  - company_name
  - company_domain (zwykle pomijane — pipeline nie robi domain lookupów w manual mode)
"""
from __future__ import annotations

import re
import sys
import os
from dataclasses import dataclass, field

# Dozwolone wartości tier (per ContactRecord)
VALID_TIERS = frozenset({
    "tier_1_c_level",
    "tier_2_procurement_management",
    "tier_3_buyers_operational",
    "tier_uncertain",
})

TIER_LABELS = {
    "tier_1_c_level": "Tier 1 — C-Level / Zarząd",
    "tier_2_procurement_management": "Tier 2 — Procurement Management",
    "tier_3_buyers_operational": "Tier 3 — Buyers / Operacyjni",
    "tier_uncertain": "Tier nieustalony",
}


@dataclass
class ManualContactValidationError:
    index: int              # 0-based index w liście
    field: str              # nazwa pola z błędem
    message: str            # opis błędu po polsku


@dataclass
class ManualContactValidationResult:
    valid: bool
    errors: list[ManualContactValidationError] = field(default_factory=list)


def _is_valid_email(email: str) -> bool:
    """Minimalna walidacja email — sprawdza obecność @ i domeny."""
    if not email or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local) and bool(domain) and "." in domain


def validate_contacts(contacts_raw: list[dict]) -> ManualContactValidationResult:
    """
    Waliduje listę surowych kontaktów.

    Returns:
        ManualContactValidationResult — valid=True jeśli zero błędów.
    """
    errors: list[ManualContactValidationError] = []

    if not contacts_raw:
        errors.append(ManualContactValidationError(
            index=-1, field="contacts",
            message="Lista kontaktów jest pusta — wymagany co najmniej 1 kontakt."
        ))
        return ManualContactValidationResult(valid=False, errors=errors)

    for i, c in enumerate(contacts_raw):
        # email — wymagane
        email = (c.get("email") or "").strip()
        if not email:
            errors.append(ManualContactValidationError(
                index=i, field="email",
                message=f"Kontakt [{i}]: brak pola 'email'."
            ))
        elif not _is_valid_email(email):
            errors.append(ManualContactValidationError(
                index=i, field="email",
                message=f"Kontakt [{i}]: nieprawidłowy format email: '{email}'."
            ))

        # tier — wymagane
        tier = (c.get("tier") or "").strip()
        if not tier:
            errors.append(ManualContactValidationError(
                index=i, field="tier",
                message=f"Kontakt [{i}]: brak pola 'tier'."
            ))
        elif tier not in VALID_TIERS:
            valid_str = ", ".join(sorted(VALID_TIERS))
            errors.append(ManualContactValidationError(
                index=i, field="tier",
                message=(
                    f"Kontakt [{i}]: nieprawidłowa wartość tier='{tier}'. "
                    f"Dozwolone: {valid_str}."
                )
            ))

    return ManualContactValidationResult(valid=(len(errors) == 0), errors=errors)


def contacts_to_records(contacts_raw: list[dict]) -> list:
    """
    Konwertuje surowe dykty wejściowe operatora na ContactRecord.

    Zakłada, że contacts_raw preszedł już validate_contacts() bez błędów.

    Pola:
      - email         → email (source of truth)
      - tier          → tier (source of truth)
      - full_name     → full_name (fallback: first_name + last_name)
      - first_name    → first_name
      - last_name     → last_name
      - job_title     → job_title (domyślnie: "")
      - company_name  → company_name (domyślnie: "")

    email_source = "operator_provided"
    source = "manual"
    confidence = 1.0  (operator = source of truth)
    """
    # Lazy import ContactRecord (z news.contacts.contact_finder)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from news.contacts.contact_finder import ContactRecord

    records = []
    for c in contacts_raw:
        email = (c.get("email") or "").strip()
        tier = (c.get("tier") or "tier_uncertain").strip()
        first_name = (c.get("first_name") or "").strip()
        last_name = (c.get("last_name") or "").strip()
        full_name = (c.get("full_name") or f"{first_name} {last_name}").strip()

        # Uzupełnij first/last jeśli podano tylko full_name
        if full_name and not first_name and not last_name:
            parts = full_name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        tier_label = TIER_LABELS.get(tier, tier)

        records.append(ContactRecord(
            first_name=first_name,
            last_name=last_name,
            full_name=full_name or email,
            email=email,
            job_title=(c.get("job_title") or "").strip(),
            company_name=(c.get("company_name") or "").strip(),
            company_domain=(c.get("company_domain") or "").strip(),
            tier=tier,
            tier_label=tier_label,
            tier_reason="operator_provided",
            source="manual",
            confidence=1.0,
            apollo_contact_id=None,
            linkedin_url=c.get("linkedin_url") or None,
            email_source="operator_provided",
        ))

    return records
