#!/usr/bin/env python3
"""
Lightweight ICP Tier alignment check — heuristic validation.

Nie blokuje flow. Oznacza rekord jako requires_review jeśli walidacja nie przejdzie.
Używany przez flow bez pełnego QA agenta:
  - run_adhoc_linkedin.py
  - generate_no_email_contacts.py
  - simulate_article_sequence.py
"""

import re

# ── Tier keyword maps ──────────────────────────────────────────

_TIER_1_KEYWORDS = [
    r"wynik\w*", r"marż\w*", r"budżet\w*", r"cash\s*flow", r"strategi\w*",
    r"ryzyk\w*", r"rentowno\w*", r"ebitda", r"przychod\w*", r"zyskown\w*",
    r"wzrost\w*", r"decyzj\w* strategiczn\w*", r"portfel\w*", r"inwestycj\w*",
    r"wartość firmy", r"pozycj\w* negocjacyjn\w*", r"konkurencyjno\w*",
]

_TIER_2_KEYWORDS = [
    r"savings?\b", r"oszcz[eę]dno\w*", r"zespo[lł]\w*", r"standar\w* negocjacj\w*",
    r"unikni[eę]\w* podwyż\w*", r"raport\w* do zarządu", r"proces\w* zakupow\w*",
    r"efektywno\w* zakup\w*", r"polityk\w* zakupow\w*", r"optymalizacj\w*",
    r"kategori\w* zakupow\w*", r"konsolidacj\w*", r"podwyżk\w* cenow\w*",
    r"avoided\s*cost", r"cost\s*avoidance",
]

_TIER_3_KEYWORDS = [
    r"kategori\w*", r"dostaw\w*", r"benchmark\w*", r"argumentacj\w*",
    r"savings w kategori\w*", r"avoided\s*cost", r"negocjacj\w* z dostaw\w*",
    r"cennik\w*", r"warun\w* handlow\w*", r"analiz\w* kosztow\w*",
    r"porównan\w* ofert", r"scoring\w* dostaw\w*", r"tender\w*",
    r"renegocjacj\w*", r"indeksacj\w*",
]

# Cross-tier mismatch patterns
_TIER_1_WRONG = [
    r"kupiec operacyjn\w*", r"buyer\b", r"analiz\w* kategori\w*",
    r"scoring dostaw\w*", r"obsług\w* zamówień",
]

_TIER_3_WRONG = [
    r"zarząd\w*", r"(?:strategi\w* firmy)", r"portfel\w* biznesow\w*",
    r"c-level", r"board\b", r"(?:decyzj\w* strategiczn\w* firmy)",
]

_TIER_2_MUST_HAVE = [
    r"savings?\b", r"oszcz[eę]dno\w*", r"zespo[lł]\w*", r"efektywno\w*",
]

_CTA_PATTERNS = [
    r"rozmow\w*", r"telefon\w*", r"teams\b", r"spotkani\w*",
    r"termin\w*", r"wygodni\w*", r"porozmawiać", r"calendly",
    r"zaprasz\w*", r"kontakt\w*", r"informacj\w*.*wygodni\w*",
]


def _count_matches(text: str, patterns: list[str]) -> int:
    count = 0
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            count += 1
    return count


def _has_any(text: str, patterns: list[str]) -> bool:
    return _count_matches(text, patterns) > 0


def tier_alignment_check(
    tier_info: dict | None,
    email_bodies: list[str],
) -> dict:
    """
    Lightweight heuristic check for ICP Tier alignment.

    Args:
        tier_info: dict from resolve_tier() (tier, tier_label, ...)
        email_bodies: list of email body strings to check

    Returns:
        dict with: pass, tier_detected, tier_label, savings_context_present,
                   wrong_tier_language_detected, cta_present, comments, requires_review
    """
    result = {
        "pass": False,
        "tier_detected": None,
        "tier_label": None,
        "savings_context_present": False,
        "wrong_tier_language_detected": False,
        "cta_present": False,
        "comments": [],
        "requires_review": False,
    }

    # 1. Check tier_info exists
    if not tier_info or not isinstance(tier_info, dict):
        result["comments"].append("Brak icp_tier w output")
        result["requires_review"] = True
        return result

    tier_id = tier_info.get("tier", "")
    tier_label = tier_info.get("tier_label", "")

    # 2. Check tier_label exists
    if not tier_label:
        result["comments"].append("Brak tier_label")
        result["requires_review"] = True
        return result

    result["tier_detected"] = tier_id
    result["tier_label"] = tier_label

    # Combine all email bodies for analysis
    combined = "\n".join(b for b in email_bodies if b).lower()

    if not combined.strip():
        result["comments"].append("Puste treści maili - nie można zwalidować")
        result["requires_review"] = True
        return result

    # 3-5. Check tier-specific keywords
    if tier_id == "tier_1_c_level":
        hits = _count_matches(combined, _TIER_1_KEYWORDS)
        if hits >= 2:
            result["savings_context_present"] = True
        else:
            result["comments"].append(
                f"Tier 1 (C-level): za mało kontekstu biznesowego "
                f"(wynik/marża/budżet/strategia/ryzyko) — znaleziono {hits} trafień"
            )
            result["requires_review"] = True

    elif tier_id == "tier_2_procurement_management":
        hits = _count_matches(combined, _TIER_2_KEYWORDS)
        if hits >= 2:
            result["savings_context_present"] = True
        else:
            result["comments"].append(
                f"Tier 2 (Procurement Mgmt): za mało kontekstu savings/zespół/standard "
                f"— znaleziono {hits} trafień"
            )
            result["requires_review"] = True

    elif tier_id == "tier_3_buyers_operational":
        hits = _count_matches(combined, _TIER_3_KEYWORDS)
        if hits >= 2:
            result["savings_context_present"] = True
        else:
            result["comments"].append(
                f"Tier 3 (Buyers): za mało kontekstu kategoria/dostawca/benchmark "
                f"— znaleziono {hits} trafień"
            )
            result["requires_review"] = True

    elif tier_id == "tier_uncertain":
        result["comments"].append("Tier nierozstrzygnięty — wymaga ręcznego review")
        result["requires_review"] = True

    # 6. Cross-tier mismatch detection
    wrong_language = False

    if tier_id == "tier_1_c_level" and _has_any(combined, _TIER_1_WRONG):
        wrong_language = True
        result["comments"].append("Tier 1 traktowany jak kupiec operacyjny")

    if tier_id == "tier_3_buyers_operational" and _has_any(combined, _TIER_3_WRONG):
        wrong_language = True
        result["comments"].append("Tier 3 traktowany jak zarząd")

    if tier_id == "tier_2_procurement_management" and not _has_any(combined, _TIER_2_MUST_HAVE):
        wrong_language = True
        result["comments"].append("Tier 2 bez wątku savings lub zespołu")

    result["wrong_tier_language_detected"] = wrong_language
    if wrong_language:
        result["requires_review"] = True

    # 7. CTA check
    result["cta_present"] = _has_any(combined, _CTA_PATTERNS)
    if not result["cta_present"]:
        result["comments"].append("Brak praktycznego CTA w treści")
        result["requires_review"] = True

    # Final pass/fail
    result["pass"] = not result["requires_review"]

    if not result["comments"]:
        result["comments"].append("OK — tier alignment poprawny")

    return result
