"""
Contact Finder — szuka kontaktów dla firmy przez Apollo API.

Używa istniejącego ApolloClient z projektu.
Mapuje stanowiska do tierów wg tier_mapping.yaml.

Zwraca: lista ContactRecord (imię, nazwisko, email, tytuł, tier, źródło)

Extended fallback flow (od 2026-04-22):
    1. Search by name (primary)
    2. Domain fallback — jeśli 0 emaili i domena dostępna
    3. Associated company fallback — jeśli nadal 0 emaili i są firmy powiązane
"""
from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ContactRecord:
    first_name: str
    last_name: str
    full_name: str
    email: str
    job_title: str
    company_name: str
    company_domain: str
    tier: str            # tier_1_c_level | tier_2_procurement_management | tier_3_buyers_operational | tier_uncertain
    tier_label: str
    tier_reason: str
    source: str          # apollo | manual | enrichment
    confidence: float    # 0.0-1.0
    apollo_contact_id: str | None = None
    linkedin_url: str | None = None


@dataclass
class ContactSearchResult:
    """
    Wynik rozszerzonego search flow z obsługą fallbacków.
    Zawiera kontakty + diagnostykę strategii.
    """
    contacts: list[ContactRecord]
    # Strategie
    strategy_used: str              # "name_only" | "name_domain" | "name_domain_assoc" | "name_assoc"
    winning_strategy: str           # "name" | "domain" | "associated:<company_name>" | "none"
    # Name search
    name_search_count: int          # total contacts from name search
    name_search_email_count: int    # contacts with valid email from name search
    # Domain fallback
    domain_fallback_triggered: bool
    domain_searched: str | None     # actual domain searched
    domain_search_count: int
    domain_search_email_count: int
    # Associated company fallback
    assoc_fallback_triggered: bool
    assoc_fallback_company: str | None  # winning associated company
    assoc_search_count: int
    assoc_search_email_count: int
    # Diagnostic log
    search_log: list[str] = field(default_factory=list)


def _get_apollo_client():
    """Lazy import ApolloClient z Integracje/."""
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


def _resolve_tier_from_mapping(title: str, tier_mapping: dict) -> tuple[str, str, str]:
    """
    Mapuje tytuł na tier wg tier_mapping.yaml.

    Returns:
        (tier_id, tier_label, reason)
    """
    if not title:
        return "tier_uncertain", "Tier Uncertain", "No title provided"

    title_lower = title.lower().strip()

    # Sprawdź tier 1 (exact/partial)
    for t in tier_mapping.get("tier_1_titles", {}).get("titles", []):
        if t.lower() in title_lower or title_lower in t.lower():
            return "tier_1_c_level", "Tier 1 - C-Level", f"Title match: '{t}'"

    # Sprawdź tier 2
    for t in tier_mapping.get("tier_2_titles", {}).get("titles", []):
        if t.lower() in title_lower or title_lower in t.lower():
            return "tier_2_procurement_management", "Tier 2 - Procurement", f"Title match: '{t}'"

    # Sprawdź tier 3
    for t in tier_mapping.get("tier_3_titles", {}).get("titles", []):
        if t.lower() in title_lower or title_lower in t.lower():
            return "tier_3_buyers_operational", "Tier 3 - Buyers/Operational", f"Title match: '{t}'"

    # Keyword hints fallback
    hints = tier_mapping.get("tier_keyword_hints", {})
    for kw in hints.get("tier_1_keywords", []):
        if kw.lower() in title_lower:
            return "tier_1_c_level", "Tier 1 - C-Level", f"Keyword hint: '{kw}'"
    for kw in hints.get("tier_2_keywords", []):
        if kw.lower() in title_lower:
            return "tier_2_procurement_management", "Tier 2 - Procurement", f"Keyword hint: '{kw}'"
    for kw in hints.get("tier_3_keywords", []):
        if kw.lower() in title_lower:
            return "tier_3_buyers_operational", "Tier 3 - Buyers/Operational", f"Keyword hint: '{kw}'"

    return "tier_uncertain", "Tier Uncertain", f"No match for: '{title}'"


def _is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _search_apollo_contacts(
    company_name: str,
    campaign_config: dict,
) -> list[dict]:
    """
    Szuka kontaktów w Apollo dla danej firmy po nazwie.
    Używa mixed_people/api_search z q_organization_name.
    """
    try:
        client = _get_apollo_client()
    except Exception as exc:
        log.warning("Apollo client unavailable: %s", exc)
        return []

    seniority_list = campaign_config.get(
        "apollo_search_seniority",
        ["director", "vp", "c_suite", "owner", "founder", "manager"]
    )
    max_contacts = campaign_config.get("apollo_contacts_per_company", 10)

    try:
        result = client._post("mixed_people/api_search", {
            "q_organization_name": company_name,
            "person_seniorities": seniority_list,
            "per_page": max_contacts,
            "page": 1,
        })
        people = result.get("people", []) if isinstance(result, dict) else []
        log.info("[Apollo] name_search '%s' → %d contacts", company_name, len(people))
        return people
    except Exception as exc:
        resp_body = ""
        if hasattr(exc, "response") and exc.response is not None:
            try:
                resp_body = exc.response.text[:500]
            except Exception:
                pass
        log.warning("[Apollo] Search failed for '%s': %s%s",
                    company_name, exc,
                    f" — response: {resp_body}" if resp_body else "")
        return []


def _search_apollo_contacts_by_domain(
    domain: str,
    campaign_config: dict,
) -> list[dict]:
    """
    Domain fallback: szuka kontaktów przez domenę firmy.
    Używa mixed_people/api_search z q_organization_domains_list.

    To bardziej precyzyjne niż search po nazwie — domain jest unikalnym identyfikatorem.
    """
    try:
        client = _get_apollo_client()
    except Exception as exc:
        log.warning("[Apollo] Domain fallback — client unavailable: %s", exc)
        return []

    seniority_list = campaign_config.get(
        "apollo_search_seniority",
        ["director", "vp", "c_suite", "owner", "founder", "manager"]
    )
    max_contacts = campaign_config.get("apollo_contacts_per_company", 10)

    # Wyczyść domenę (usuń protokół i ścieżkę)
    clean_domain = re.sub(r"^https?://", "", domain).strip().rstrip("/")
    clean_domain = clean_domain.split("/")[0]  # usuń ścieżkę

    try:
        result = client._post("mixed_people/api_search", {
            "q_organization_domains_list": [clean_domain],
            "person_seniorities": seniority_list,
            "per_page": max_contacts,
            "page": 1,
        })
        people = result.get("people", []) if isinstance(result, dict) else []
        log.info("[Apollo] domain_search '%s' → %d contacts", clean_domain, len(people))
        return people
    except Exception as exc:
        resp_body = ""
        if hasattr(exc, "response") and exc.response is not None:
            try:
                resp_body = exc.response.text[:500]
            except Exception:
                pass
        log.warning("[Apollo] Domain search failed for '%s': %s%s",
                    clean_domain, exc,
                    f" — response: {resp_body}" if resp_body else "")
        return []


def _map_raw_contacts(
    raw_contacts: list[dict],
    company_name: str,
    company_domain: str | None,
    tier_mapping: dict,
) -> list[ContactRecord]:
    """
    Mapuje surowe rekordy Apollo na ContactRecord.
    Wspólna logika dla name search i domain fallback.
    """
    records: list[ContactRecord] = []
    seen_emails: set[str] = set()

    tier_priority = {
        "tier_1_c_level": 0,
        "tier_2_procurement_management": 1,
        "tier_3_buyers_operational": 2,
        "tier_uncertain": 3,
    }

    for person in raw_contacts:
        email = person.get("email", "") or ""
        first_name = person.get("first_name", "") or ""
        last_name = person.get("last_name", "") or ""
        full_name = person.get("name", f"{first_name} {last_name}").strip()
        title = person.get("title", "") or ""
        org = person.get("organization", {}) or {}
        comp_name = org.get("name", company_name)
        comp_domain = org.get("primary_domain", company_domain or "")
        contact_id = person.get("id")
        linkedin = person.get("linkedin_url")

        if email and email in seen_emails:
            continue
        if email:
            seen_emails.add(email)

        tier_id, tier_label, tier_reason = _resolve_tier_from_mapping(title, tier_mapping)
        confidence = 0.7 if _is_valid_email(email) else 0.3

        records.append(ContactRecord(
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            email=email,
            job_title=title,
            company_name=comp_name,
            company_domain=comp_domain,
            tier=tier_id,
            tier_label=tier_label,
            tier_reason=tier_reason,
            source="apollo",
            confidence=confidence,
            apollo_contact_id=contact_id,
            linkedin_url=linkedin,
        ))

    records.sort(key=lambda r: (tier_priority.get(r.tier, 9), -r.confidence))
    return records


def _count_email_contacts(records: list[ContactRecord]) -> int:
    """Liczy rekordy z walidowanym emailem."""
    return sum(1 for r in records if _is_valid_email(r.email))


def find_contacts_for_company(
    company_name: str,
    company_domain: str | None,
    tier_mapping: dict,
    campaign_config: dict,
) -> list[ContactRecord]:
    """
    Główna funkcja: wyszukuje i mapuje kontakty dla firmy po nazwie.
    Backward-compatible — nie zmienia zachowania.

    Returns:
        Lista ContactRecord posortowana wg priority tier (1 → 2 → 3 → uncertain)
    """
    raw_contacts = _search_apollo_contacts(company_name, campaign_config)
    return _map_raw_contacts(raw_contacts, company_name, company_domain, tier_mapping)


def validate_contact_found(contacts: list[ContactRecord]) -> tuple[bool, str]:
    """
    Sprawdza czy znaleziono jakiekolwiek kontakty (bez sprawdzania emaila).
    Poprzedza etap email reveal — nie wymaga dostępności emaila.

    Returns:
        (ok: bool, reason: str)
    """
    if not contacts:
        return False, "No contacts found in Apollo for this company"
    return True, f"Found {len(contacts)} contact(s) in Apollo"


def select_best_contacts(
    contacts: list[ContactRecord],
    max_contacts: int = 3,
) -> list[ContactRecord]:
    """
    Zwraca top N kontaktów posortowanych wg tier + confidence.
    Nie filtruje po emailu — wybiera kandydatów przed etapem email reveal.
    Kontakty są już posortowane przez _map_raw_contacts (tier_priority ascending).

    Args:
        contacts:     posortowana lista ContactRecord (tier_1 → tier_uncertain)
        max_contacts: maksymalna liczba kontaktów do wybrania

    Returns:
        Lista top N ContactRecord
    """
    return contacts[:max_contacts]


def validate_contact_threshold(
    contacts: list[ContactRecord],
    campaign_config: dict,
) -> tuple[bool, str]:
    """
    Sprawdza czy lista kontaktów spełnia minimalny próg do stworzenia sekwencji.
    Używany po etapie email reveal (sprawdza email).

    Returns:
        (ok: bool, reason: str)
    """
    require_email = campaign_config.get("require_email_for_sequence", True)
    min_contacts = campaign_config.get("min_contacts_to_create_sequence", 1)

    # Filtruj kontakty z poprawnym emailem (jeśli wymagany)
    valid = contacts if not require_email else [
        c for c in contacts if _is_valid_email(c.email)
    ]

    if len(valid) < min_contacts:
        return False, f"Not enough valid contacts: {len(valid)} (min {min_contacts})"

    # Sprawdź czy jest Tier 1 lub Tier 2
    has_tier1_or_2 = any(
        c.tier in ("tier_1_c_level", "tier_2_procurement_management")
        for c in valid
    )
    if not has_tier1_or_2:
        return False, "No Tier 1 or Tier 2 contacts found with valid email"

    return True, f"OK: {len(valid)} valid contacts (Tier breakdown: " + \
        f"T1={sum(1 for c in valid if c.tier=='tier_1_c_level')}, " + \
        f"T2={sum(1 for c in valid if c.tier=='tier_2_procurement_management')}, " + \
        f"T3={sum(1 for c in valid if c.tier=='tier_3_buyers_operational')})"


# ---------------------------------------------------------------------------
# Extended search flow with domain + associated company fallbacks
# ---------------------------------------------------------------------------

def find_contacts_with_fallbacks(
    company_name: str,
    company_domain: str | None,
    tier_mapping: dict,
    campaign_config: dict,
    associated_companies: list[str] | None = None,
) -> ContactSearchResult:
    """
    Rozszerzony search flow z fallbackami.

    Kolejność:
    1. Search po nazwie firmy (primary)
    2. Domain fallback — jeśli 0 emaili i domena dostępna
    3. Associated company fallback — jeśli nadal 0 emaili i są firmy powiązane

    Args:
        company_name:         resolved company name (z resolwera lub entity_extractor)
        company_domain:       domena firmy (z resolwera, alias dict lub Apollo)
        tier_mapping:         mapowanie stanowisk na tiery
        campaign_config:      config kampanii z togglesami
        associated_companies: opcjonalne firmy powiązane z artykułem

    Returns:
        ContactSearchResult z kontaktami i pełną diagnostyką
    """
    use_domain_fb = campaign_config.get("use_domain_fallback", True)
    use_assoc_fb = campaign_config.get("use_associated_company_fallback", True)
    max_assoc = campaign_config.get("max_associated_company_candidates", 2)

    search_log: list[str] = []

    # --- Krok 1: Search po nazwie firmy ---
    raw_name = _search_apollo_contacts(company_name, campaign_config)
    name_contacts = _map_raw_contacts(raw_name, company_name, company_domain, tier_mapping)
    name_email_count = _count_email_contacts(name_contacts)
    search_log.append(
        f"[1] name_search: '{company_name}' → {len(name_contacts)} contacts, {name_email_count} with email"
    )
    log.info("[ContactFinder] name_search '%s' → %d total, %d with email",
             company_name, len(name_contacts), name_email_count)

    if name_email_count > 0:
        return ContactSearchResult(
            contacts=name_contacts,
            strategy_used="name_only",
            winning_strategy="name",
            name_search_count=len(name_contacts),
            name_search_email_count=name_email_count,
            domain_fallback_triggered=False,
            domain_searched=None,
            domain_search_count=0,
            domain_search_email_count=0,
            assoc_fallback_triggered=False,
            assoc_fallback_company=None,
            assoc_search_count=0,
            assoc_search_email_count=0,
            search_log=search_log,
        )

    # --- Krok 2: Domain fallback ---
    domain_contacts: list[ContactRecord] = []
    domain_email_count = 0
    domain_triggered = False
    clean_domain: str | None = None

    if use_domain_fb and company_domain:
        domain_triggered = True
        clean_domain = re.sub(r"^https?://", "", company_domain).strip().rstrip("/").split("/")[0]
        raw_domain = _search_apollo_contacts_by_domain(clean_domain, campaign_config)
        domain_contacts = _map_raw_contacts(raw_domain, company_name, clean_domain, tier_mapping)
        domain_email_count = _count_email_contacts(domain_contacts)
        search_log.append(
            f"[2] domain_fallback: '{clean_domain}' → {len(domain_contacts)} contacts, {domain_email_count} with email"
        )
        log.info("[ContactFinder] domain_fallback '%s' → %d total, %d with email",
                 clean_domain, len(domain_contacts), domain_email_count)

        if domain_email_count > 0:
            return ContactSearchResult(
                contacts=domain_contacts,
                strategy_used="name_domain",
                winning_strategy="domain",
                name_search_count=len(name_contacts),
                name_search_email_count=name_email_count,
                domain_fallback_triggered=True,
                domain_searched=clean_domain,
                domain_search_count=len(domain_contacts),
                domain_search_email_count=domain_email_count,
                assoc_fallback_triggered=False,
                assoc_fallback_company=None,
                assoc_search_count=0,
                assoc_search_email_count=0,
                search_log=search_log,
            )
    elif use_domain_fb and not company_domain:
        search_log.append("[2] domain_fallback: skipped — no domain available")

    # --- Krok 3: Associated company fallback ---
    assoc_contacts: list[ContactRecord] = []
    assoc_email_count = 0
    assoc_triggered = False
    assoc_winner: str | None = None

    if use_assoc_fb and associated_companies:
        assoc_triggered = True
        candidates = [c for c in associated_companies if c and c.strip() and c.strip().lower() != company_name.strip().lower()][:max_assoc]

        for assoc_name in candidates:
            raw_assoc = _search_apollo_contacts(assoc_name, campaign_config)
            recs = _map_raw_contacts(raw_assoc, assoc_name, None, tier_mapping)
            count_email = _count_email_contacts(recs)
            search_log.append(
                f"[3] assoc_fallback: '{assoc_name}' → {len(recs)} contacts, {count_email} with email"
            )
            log.info("[ContactFinder] assoc_fallback '%s' → %d total, %d with email",
                     assoc_name, len(recs), count_email)

            if count_email > 0:
                assoc_contacts = recs
                assoc_email_count = count_email
                assoc_winner = assoc_name
                break
    elif use_assoc_fb and not associated_companies:
        search_log.append("[3] assoc_fallback: skipped — no associated companies provided")

    # Wybierz najlepszy wynik: preferuj assoc jeśli ma emaile, inaczej domain, inaczej name
    if assoc_email_count > 0:
        best_contacts = assoc_contacts
        winning = f"associated:{assoc_winner}"
        strategy = "name_domain_assoc" if domain_triggered else "name_assoc"
    elif domain_email_count > 0:
        best_contacts = domain_contacts
        winning = "domain"
        strategy = "name_domain"
    else:
        # Żaden fallback nie dał emaili — zwróć name_contacts (może być puste)
        best_contacts = name_contacts
        winning = "none"
        strategy = "name_only"
        search_log.append("[RESULT] All strategies failed — 0 contacts with email")

    log.info("[ContactFinder] Final: strategy=%s winning=%s email_contacts=%d",
             strategy, winning, _count_email_contacts(best_contacts))

    return ContactSearchResult(
        contacts=best_contacts,
        strategy_used=strategy,
        winning_strategy=winning,
        name_search_count=len(name_contacts),
        name_search_email_count=name_email_count,
        domain_fallback_triggered=domain_triggered,
        domain_searched=clean_domain,
        domain_search_count=len(domain_contacts),
        domain_search_email_count=domain_email_count,
        assoc_fallback_triggered=assoc_triggered,
        assoc_fallback_company=assoc_winner,
        assoc_search_count=len(assoc_contacts),
        assoc_search_email_count=assoc_email_count,
        search_log=search_log,
    )
