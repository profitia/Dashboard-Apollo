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
    email_source: str = "unknown"  # apollo_direct | apollo_reveal | inferred_pattern | unknown


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
            # Zastosuj dwójskładnikową weryfikację dla Tier 2
            if _is_valid_tier2_title(title):
                return "tier_2_procurement_management", "Tier 2 - Procurement", f"Title match: '{t}'"
            # Specjalne wyjątki: CPO i tytuły zakotwiczone (zawierające pełną frazę)
            if t.lower() in ("cpo", "chief procurement officer"):
                return "tier_2_procurement_management", "Tier 2 - Procurement", f"Title match: '{t}' (CPO/Chief Procurement Officer)"
            # Brak składnika procurement w tytule — nie kwalifikuj do Tier 2
            continue

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
            # Dwójskładnikowa weryfikacja: musi mieć poziom + składnik zakupowy
            if _is_valid_tier2_title(title):
                return "tier_2_procurement_management", "Tier 2 - Procurement", f"Keyword hint: '{kw}'"
            # CPO jako akronim — wyjątek (nie można weryfikować dwójskładnikowo)
            if kw.upper() == "CPO" and title_lower.strip() in ("cpo",):
                return "tier_2_procurement_management", "Tier 2 - Procurement", "Keyword hint: 'CPO'"
    for kw in hints.get("tier_3_keywords", []):
        if kw.lower() in title_lower:
            return "tier_3_buyers_operational", "Tier 3 - Buyers/Operational", f"Keyword hint: '{kw}'"

    return "tier_uncertain", "Tier Uncertain", f"No match for: '{title}'"


def _is_valid_tier2_title(title: str) -> bool:
    """
    Weryfikuje dwójskładnikową regułę dla Tier 2:
    - musi mieć komponent poziomu: head | director | chief | dyrektor
    - ORAZ komponent zakupowy: procurement | purchasing | zakup | sourcing

    Zapobiega kwalifikacji ról jak "Operations Director" czy "Brand Director" do Tier 2.
    Przykłady poprawne: "Head of Procurement", "Dyrektor Zakupów", "Chief Procurement Officer"
    """
    if not title:
        return False
    t = title.lower()
    level_kws = ["head", "director", "chief", "dyrektor"]
    procurement_kws = ["procurement", "purchasing", "zakup", "sourcing"]
    has_level = any(kw in t for kw in level_kws)
    has_procurement = any(kw in t for kw in procurement_kws)
    return has_level and has_procurement


def _is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _extract_role_anchored_people(
    article_title: str | None,
    article_lead: str | None,
    article_body: str | None,
    max_people: int = 3,
) -> list[dict[str, str]]:
    """
    Wyciąga osoby decyzyjne wzmiankowane w artykule (imię + nazwisko)
    tylko wtedy, gdy w pobliżu występuje kotwica roli (np. prezes, CEO, dyrektor).

    Zwraca listę dictów: {"full_name": ..., "role_hint": ...}
    """
    chunks = [c for c in [article_title, article_lead, article_body] if c]
    if not chunks:
        return []

    text = "\n".join(chunks)
    role_pattern = re.compile(
        r"(?i)\b(prezes(?:a)?|wiceprezes(?:a)?|ceo|członek zarządu|dyrektor(?:a)?(?:\s+\w+){0,2})\b"
    )
    name_pattern = re.compile(
        r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\-]{2,})\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\-]{2,})\b"
    )

    ignored_tokens = {
        "spółdzielni", "mleczarskiej", "mlekpol", "mlekpolu", "zarządu", "europejskiego",
        "kongresu", "gospodarczego", "polska", "polski", "żywność", "rynku", "globalnym",
        "food", "analiz", "eec",
    }

    def _is_known_first_name(name: str) -> bool:
        try:
            from core.polish_names import get_polish_name_data
            return get_polish_name_data(name) is not None
        except Exception:
            # Gdy helper niedostępny, fallback zachowuje ostrożność.
            return False

    found: list[dict[str, str]] = []
    seen: set[str] = set()

    for role_match in role_pattern.finditer(text):
        role_hint = role_match.group(1).strip().lower()
        tail = text[role_match.end(): min(len(text), role_match.end() + 160)]

        for nm in name_pattern.finditer(tail):
            first = nm.group(1).strip()
            last = nm.group(2).strip()
            f_low = first.lower()
            l_low = last.lower()

            if f_low in ignored_tokens or l_low in ignored_tokens:
                continue
            if not _is_known_first_name(first):
                continue

            full_name = f"{first} {last}"
            name_key = full_name.lower()
            if name_key in seen:
                continue

            seen.add(name_key)
            found.append({"full_name": full_name, "role_hint": role_hint})
            break

        if len(found) >= max_people:
            break

    return found


def _search_apollo_contacts_by_person(
    company_name: str,
    person_full_name: str,
    campaign_config: dict,
) -> list[dict]:
    """
    Szuka osoby wzmiankowanej w artykule w kontekście organizacji.

    Używa mixed_people/api_search z kombinacją:
      - q_organization_name (firma)
      - q_keywords (pełne imię i nazwisko)
    """
    try:
        client = _get_apollo_client()
    except Exception as exc:
        log.warning("[Apollo] Person fallback — client unavailable: %s", exc)
        return []

    per_page = campaign_config.get("apollo_person_fallback_per_page", 15)

    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    company_token = _norm(company_name)
    name_parts = [p for p in person_full_name.split() if p.strip()]
    first = name_parts[0] if name_parts else ""
    last = name_parts[-1] if len(name_parts) > 1 else ""

    keyword_variants = [person_full_name]
    if last and last not in keyword_variants:
        keyword_variants.append(last)

    org_variants = [company_name]
    if company_name and " " not in company_name.strip():
        upper = company_name.strip().upper()
        org_variants.extend([
            upper,
            f"Spółdzielnia Mleczarska {upper}",
            f"SM {upper}",
        ])
    org_variants = list(dict.fromkeys(v for v in org_variants if v and v.strip()))

    payloads: list[dict] = []
    for kw in keyword_variants:
        for org in org_variants:
            payloads.append({
                "q_organization_name": org,
                "q_keywords": kw,
                "per_page": per_page,
                "page": 1,
            })
        payloads.append({
            "q_keywords": kw,
            "per_page": per_page,
            "page": 1,
        })

    merged: list[dict] = []
    seen_ids: set[str] = set()

    for payload in payloads:
        try:
            result = client._post("mixed_people/api_search", payload)
            people = result.get("people", []) if isinstance(result, dict) else []
        except Exception as exc:
            resp_body = ""
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    resp_body = exc.response.text[:500]
                except Exception:
                    pass
            log.warning("[Apollo] Person fallback failed for '%s' payload=%s: %s%s",
                        person_full_name, payload, exc,
                        f" — response: {resp_body}" if resp_body else "")
            continue

        for p in people:
            pid = p.get("id") or ""
            if not pid or pid in seen_ids:
                continue

            org = p.get("organization") or {}
            org_name = org.get("name") or p.get("organization_name") or p.get("company_name") or ""
            org_key = _norm(org_name)

            # W person fallback zachowaj tylko rekordy faktycznie związane z firmą.
            if company_token and company_token not in org_key:
                continue

            p_first = (p.get("first_name") or "").strip().lower()
            if first and p_first and p_first != first.lower():
                continue

            seen_ids.add(pid)
            merged.append(p)

    # --- CRM fallback: contacts/search ---
    # Jeśli prospecting DB nie zwróciło wyników → sprawdź CRM.
    # contacts/search przeszukuje zarządzane kontakty (z emailem) wg q_keywords.
    if not merged:
        crm_keywords = [person_full_name]
        if last and last != person_full_name:
            crm_keywords.append(last)

        for kw in crm_keywords:
            try:
                result = client._post("contacts/search", {
                    "q_keywords": kw,
                    "page": 1,
                    "per_page": per_page,
                })
                crm_contacts = result.get("contacts", []) if isinstance(result, dict) else []
            except Exception as exc:
                log.warning("[Apollo] CRM contacts/search failed for '%s': %s", kw, exc)
                continue

            for p in crm_contacts:
                pid = p.get("id") or ""
                if not pid or pid in seen_ids:
                    continue

                org = p.get("organization") or {}
                org_name = (
                    org.get("name")
                    or p.get("organization_name")
                    or p.get("account_name")
                    or p.get("company_name")
                    or ""
                )
                org_key = _norm(org_name)

                # Zachowaj tylko rekordy z tej organizacji.
                if company_token and company_token not in org_key:
                    continue

                p_first = (p.get("first_name") or "").strip().lower()
                if first and p_first and p_first != first.lower():
                    continue

                seen_ids.add(pid)
                merged.append(p)

            if merged:
                log.info("[Apollo] person_fallback CRM '%s' @ '%s' → %d contacts",
                         kw, company_name, len(merged))
                break

    log.info("[Apollo] person_fallback '%s' @ '%s' → %d contacts total",
             person_full_name, company_name, len(merged))
    return merged


def _apply_article_role_hint(record: ContactRecord, role_hint: str) -> None:
    """
    Gdy Apollo zwraca słabe/niepełne title, użyj roli z artykułu jako hintu tieru.
    Dotyczy wyłącznie rekordów tier_uncertain.
    """
    if record.tier != "tier_uncertain":
        return

    hint = role_hint.lower()
    if any(k in hint for k in ["prezes", "wiceprezes", "ceo", "członek zarządu"]):
        record.tier = "tier_1_c_level"
        record.tier_label = "Tier 1 - C-Level"
        record.tier_reason = f"Article role hint: '{role_hint}'"
        record.confidence = max(record.confidence, 0.75)
        return

    if "dyrektor" in hint and any(k in hint for k in ["zakup", "sourcing", "procurement", "purchasing"]):
        record.tier = "tier_2_procurement_management"
        record.tier_label = "Tier 2 - Procurement"
        record.tier_reason = f"Article role hint: '{role_hint}'"
        record.confidence = max(record.confidence, 0.7)


def _merge_contacts_prefer_tier(contacts: list[ContactRecord]) -> list[ContactRecord]:
    """Deduplikuje listę kontaktów i sortuje wg priorytetu tier/confidence."""
    if not contacts:
        return []

    tier_priority = {
        "tier_1_c_level": 0,
        "tier_2_procurement_management": 1,
        "tier_3_buyers_operational": 2,
        "tier_uncertain": 3,
    }

    best_by_key: dict[str, ContactRecord] = {}
    for rec in contacts:
        key = rec.apollo_contact_id or (rec.full_name.lower() if rec.full_name else "")
        if not key:
            continue
        cur = best_by_key.get(key)
        if not cur:
            best_by_key[key] = rec
            continue

        cur_rank = (tier_priority.get(cur.tier, 9), -cur.confidence)
        new_rank = (tier_priority.get(rec.tier, 9), -rec.confidence)
        if new_rank < cur_rank:
            best_by_key[key] = rec

    merged = list(best_by_key.values())
    merged.sort(key=lambda r: (tier_priority.get(r.tier, 9), -r.confidence))
    return merged


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
            email_source="apollo_direct" if _is_valid_email(email) else "unknown",
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


def select_campaign_contacts(
    contacts: list[ContactRecord],
    campaign_config: dict | None = None,
    max_contacts: int | None = None,
) -> list[ContactRecord]:
    """
    Wybiera kontakty dla kampanii news wg reguł kampanii:
    - TYLKO Tier 1 i Tier 2 (Tier 3 i Uncertain są wykluczone)
    - Wszyscy znalezieni z T1/T2 (nie ograniczaj do 1 per tier)
    - Posortowane: Tier 1 → Tier 2 → confidence malejąco

    Logika cytowanej osoby (spray-and-pray do właściwych ról):
    - Jeśli są osoby T1/T2 → wyślij do wszystkich T1/T2
    - Brak T3/uncertain w tej kampanii

    Args:
        contacts:        lista ContactRecord (może zawierać wszystkie tiery)
        campaign_config: opcjonalny config (dla max_contacts_for_draft)
        max_contacts:    hard limit (override config)

    Returns:
        Lista ContactRecord wyłącznie Tier 1 i Tier 2, posortowana
    """
    eligible_tiers = {"tier_1_c_level", "tier_2_procurement_management"}
    selected = [c for c in contacts if c.tier in eligible_tiers]

    # Sortuj: Tier 1 przed Tier 2, potem confidence malejąco
    tier_priority = {"tier_1_c_level": 0, "tier_2_procurement_management": 1}
    selected.sort(key=lambda r: (tier_priority.get(r.tier, 9), -r.confidence))

    # Hard cap (opcjonalny)
    cap = max_contacts
    if cap is None and campaign_config:
        cap = campaign_config.get("max_contacts_for_draft")
    if cap is not None:
        selected = selected[:cap]

    tier1_count = sum(1 for c in selected if c.tier == "tier_1_c_level")
    tier2_count = sum(1 for c in selected if c.tier == "tier_2_procurement_management")
    excluded = sum(1 for c in contacts if c.tier not in eligible_tiers)
    log.info(
        "[ContactFinder] select_campaign_contacts: %d total → T1=%d, T2=%d selected, %d excluded (T3/uncertain)",
        len(contacts), tier1_count, tier2_count, excluded,
    )
    return selected


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
    article_title: str | None = None,
    article_lead: str | None = None,
    article_body: str | None = None,
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
    use_person_fb = campaign_config.get("use_article_person_fallback", True)
    max_person_candidates = campaign_config.get("max_article_person_candidates", 3)

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

    # --- Krok 4: Article person fallback (osoba wskazana w artykule) ---
    # Używamy tylko gdy dotychczasowy best nie zawiera T1/T2.
    has_t1_t2 = any(c.tier in {"tier_1_c_level", "tier_2_procurement_management"} for c in best_contacts)
    if use_person_fb and not has_t1_t2:
        candidates = _extract_role_anchored_people(
            article_title=article_title,
            article_lead=article_lead,
            article_body=article_body,
            max_people=max_person_candidates,
        )

        if candidates:
            person_contacts: list[ContactRecord] = []
            for cand in candidates:
                full_name = cand.get("full_name", "").strip()
                role_hint = cand.get("role_hint", "").strip()
                if not full_name:
                    continue

                raw_people = _search_apollo_contacts_by_person(
                    company_name=company_name,
                    person_full_name=full_name,
                    campaign_config=campaign_config,
                )
                recs = _map_raw_contacts(raw_people, company_name, company_domain, tier_mapping)
                for r in recs:
                    _apply_article_role_hint(r, role_hint)
                person_contacts.extend(recs)
                search_log.append(
                    f"[4] article_person: '{full_name}' ({role_hint}) → {len(recs)} contacts"
                )

            merged = _merge_contacts_prefer_tier(best_contacts + person_contacts)
            merged_has_t1_t2 = any(c.tier in {"tier_1_c_level", "tier_2_procurement_management"} for c in merged)
            if merged and merged_has_t1_t2:
                best_contacts = merged
                winning = "article_person"
                strategy = f"{strategy}_person"
                search_log.append("[RESULT] article_person fallback upgraded contacts to include T1/T2")
        else:
            search_log.append("[4] article_person: skipped — no role-anchored names in article")

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
