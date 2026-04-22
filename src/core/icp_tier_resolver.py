#!/usr/bin/env python3
"""
ICP Tier Resolver — automatyczne przypisywanie Tieru na podstawie stanowiska.

Źródło prawdy: source_of_truth/icp_tiers.yaml
Używany przez: run_campaign.py, run_csv_campaign.py, test pipeline, QA.
"""

import os
import re

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


# ============================================================
# Ścieżka do pliku tiers
# ============================================================

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TIERS_PATH = os.path.join(_ROOT_DIR, "source_of_truth", "icp_tiers.yaml")

_cached_tiers: dict | None = None


def _load_tiers() -> dict:
    """Wczytuje icp_tiers.yaml (z cache)."""
    global _cached_tiers
    if _cached_tiers is not None:
        return _cached_tiers
    if yaml is None:
        raise ImportError("PyYAML jest wymagany: pip install pyyaml")
    if not os.path.exists(_TIERS_PATH):
        raise FileNotFoundError(f"Brak pliku: {_TIERS_PATH}")
    with open(_TIERS_PATH, "r", encoding="utf-8") as f:
        _cached_tiers = yaml.safe_load(f)
    return _cached_tiers


def reset_cache():
    """Czyści cache tiers (np. w testach)."""
    global _cached_tiers
    _cached_tiers = None


# ============================================================
# Tier detection
# ============================================================

# Keywords sugerujące management (Tier 2) dla ról warunkowych
_TIER2_KEYWORDS = re.compile(
    r"head|director|lead|team|manager\s+of|department|regional|group|vp|vice\s+president",
    re.IGNORECASE,
)

TIER_IDS = ("tier_1_c_level", "tier_2_procurement_management", "tier_3_buyers_operational")


def resolve_tier(title: str, context: str = "") -> dict:
    """
    Przypisuje Tier na podstawie stanowiska.

    Args:
        title: stanowisko kontaktu (np. "CEO", "Procurement Manager")
        context: opcjonalny dodatkowy kontekst (opis roli, odpowiedzialności)

    Returns:
        dict z polami: tier, tier_label, tier_reason, savings_accountability,
        messaging_angle, auto_detected
    """
    tiers = _load_tiers()
    mapping = tiers.get("role_to_tier_mapping", {})

    title_clean = title.strip()
    title_lower = title_clean.lower()

    # 1. Exact match w mapping
    for role_key, tier_id in mapping.items():
        if role_key.lower() == title_lower:
            if tier_id == "conditional_tier_2_or_3":
                return _resolve_conditional(title_clean, context, tiers)
            return _build_result(tier_id, tiers, f"Rola '{title_clean}' mapowana na {tier_id}")

    # 2. Partial match — szukaj w mapie
    for role_key, tier_id in mapping.items():
        if role_key.lower() in title_lower or title_lower in role_key.lower():
            if tier_id == "conditional_tier_2_or_3":
                return _resolve_conditional(title_clean, context, tiers)
            return _build_result(tier_id, tiers, f"Rola '{title_clean}' częściowo pasuje do '{role_key}'")

    # 3. Heurystyka — sprawdź keyword patterns
    if any(kw in title_lower for kw in ("ceo", "cfo", "coo", "owner", "prezes", "zarząd", "board")):
        return _build_result("tier_1_c_level", tiers, f"Heurystyka: '{title_clean}' zawiera keyword C-Level")

    if any(kw in title_lower for kw in ("director", "dyrektor", "head of", "vp ")):
        return _build_result("tier_2_procurement_management", tiers, f"Heurystyka: '{title_clean}' zawiera keyword management")

    if any(kw in title_lower for kw in ("buyer", "kupiec", "category", "sourcing", "analyst", "specialist")):
        return _build_result("tier_3_buyers_operational", tiers, f"Heurystyka: '{title_clean}' zawiera keyword operacyjny")

    # 4. Fallback — tier_uncertain
    return {
        "tier": "tier_uncertain",
        "tier_label": "Tier nierozstrzygnięty",
        "tier_reason": f"Nie udało się jednoznacznie przypisać Tieru dla '{title_clean}'",
        "savings_accountability": "",
        "messaging_angle": "",
        "auto_detected": True,
        "suggested_tier": "tier_2_procurement_management",
        "suggested_reason": "Domyślnie sugerowany Tier 2 jako najbardziej uniwersalny",
    }


def _resolve_conditional(title: str, context: str, tiers: dict) -> dict:
    """Rozstrzyga role warunkowe (procurement/purchasing manager)."""
    combined = f"{title} {context}".lower()

    if _TIER2_KEYWORDS.search(combined):
        return _build_result(
            "tier_2_procurement_management", tiers,
            f"Rola warunkowa '{title}' → Tier 2 (kontekst wskazuje na odpowiedzialność za zespół/funkcję)"
        )

    # Default conditional → Tier 3
    return _build_result(
        "tier_3_buyers_operational", tiers,
        f"Rola warunkowa '{title}' → Tier 3 (brak kontekstu wskazującego na management)"
    )


def _build_result(tier_id: str, tiers: dict, reason: str) -> dict:
    """Buduje wynikowy dict z pełnym kontekstem Tieru."""
    tier_data = tiers.get(tier_id, {})

    label = tier_data.get("label", tier_id)
    savings = tier_data.get("savings_accountability", "")
    if isinstance(savings, str):
        savings = savings.strip()

    vp = tier_data.get("value_proposition", {})
    if isinstance(vp, dict):
        angle = vp.get("one_liner", vp.get("primary", ""))
    elif isinstance(vp, str):
        angle = vp
    else:
        angle = ""
    if isinstance(angle, str):
        angle = angle.strip()

    return {
        "tier": tier_id,
        "tier_label": label,
        "tier_reason": reason,
        "savings_accountability": savings,
        "messaging_angle": angle,
        "auto_detected": True,
    }


# ============================================================
# Pobranie pełnego kontekstu Tieru (do promptu LLM)
# ============================================================

def get_tier_context(tier_id: str) -> dict:
    """Zwraca pełny kontekst Tieru z icp_tiers.yaml."""
    tiers = _load_tiers()
    return tiers.get(tier_id, {})


def get_tier_prompt_context(tier_id: str) -> str:
    """Zwraca kontekst Tieru sformatowany jako tekst do promptu LLM."""
    ctx = get_tier_context(tier_id)
    if not ctx:
        return ""

    lines = [
        f"## ICP Tier: {ctx.get('label', tier_id)}",
        "",
        f"**Perspektywa odbiorcy:** {ctx.get('perspective', '')}",
        "",
        f"**Savings accountability:** {ctx.get('savings_accountability', '')}",
        "",
        "**Główne pain points:**",
    ]
    for pp in ctx.get("pain_points", []):
        lines.append(f"- {pp}")

    lines.append("")
    lines.append("**Potrzeby:**")
    for n in ctx.get("needs", []):
        lines.append(f"- {n}")

    vp = ctx.get("value_proposition", {})
    if isinstance(vp, dict):
        lines.append("")
        lines.append(f"**Value proposition:** {vp.get('primary', '')}")
        lines.append(f"**One-liner:** {vp.get('one_liner', '')}")

    tone = ctx.get("messaging_tone", {})
    if isinstance(tone, dict):
        lines.append("")
        lines.append("**Jak pisać:**")
        for h in tone.get("how_to_write", []):
            lines.append(f"- {h}")
        lines.append("")
        lines.append("**Czego unikać:**")
        for a in tone.get("avoid", []):
            lines.append(f"- {a}")

    lines.append("")
    lines.append(f"**Typowe pytanie:** {ctx.get('typical_question', '')}")

    return "\n".join(lines)


def get_all_tier_ids() -> list[str]:
    """Zwraca listę wszystkich tier_id."""
    return list(TIER_IDS)


def load_tiers_yaml_text() -> str:
    """Zwraca surowy tekst icp_tiers.yaml (do dołączenia do kontekstu LLM)."""
    if not os.path.exists(_TIERS_PATH):
        return ""
    with open(_TIERS_PATH, "r", encoding="utf-8") as f:
        return f.read()
