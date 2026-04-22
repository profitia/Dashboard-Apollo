#!/usr/bin/env python3
"""
Campaign Name Builder — jednolity standard nazewnictwa kampanii.

Format: {CampaignType}_{Tier}_{Segment}_{Angle}_{Market}_{Wxx_Mxx_Rxx}_{vX}
Przykład: LinPost_T2_Prod_Savings_PL_W01_M05_R26_v1

Źródło prawdy: source_of_truth/campaign_naming_rules.yaml
Używany przez: run_campaign.py, run_csv_campaign.py, run_adhoc_linkedin.py i inne flow.
"""

import os
from datetime import date, datetime

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# ============================================================
# Ścieżka do pliku reguł
# ============================================================

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RULES_PATH = os.path.join(_ROOT_DIR, "source_of_truth", "campaign_naming_rules.yaml")

_cached_rules: dict | None = None


def _load_rules() -> dict:
    """Wczytuje campaign_naming_rules.yaml (z cache)."""
    global _cached_rules
    if _cached_rules is not None:
        return _cached_rules
    if yaml is None:
        raise ImportError("PyYAML jest wymagany: pip install pyyaml")
    if not os.path.exists(_RULES_PATH):
        raise FileNotFoundError(f"Brak pliku: {_RULES_PATH}")
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        _cached_rules = yaml.safe_load(f)
    return _cached_rules


def reset_cache():
    """Czyści cache reguł (np. w testach)."""
    global _cached_rules
    _cached_rules = None


# ============================================================
# Timing: week-of-month
# ============================================================

def compute_week_of_month(d: date | datetime | None = None) -> tuple[int, int, int]:
    """
    Oblicza (week, month, year_2digit) na podstawie dnia miesiąca.

    Reguły:
        W01 = dni 1-7
        W02 = dni 8-14
        W03 = dni 15-21
        W04 = dni 22-28
        W05 = dni 29-31

    Returns:
        (week_number, month, year_2digit) np. (1, 5, 26)
    """
    if d is None:
        d = date.today()
    if isinstance(d, datetime):
        d = d.date()

    day = d.day
    if day <= 7:
        week = 1
    elif day <= 14:
        week = 2
    elif day <= 21:
        week = 3
    elif day <= 28:
        week = 4
    else:
        week = 5

    return week, d.month, d.year % 100


def format_timing(d: date | datetime | None = None) -> str:
    """Formatuje timing jako Wxx_Mxx_Rxx."""
    week, month, year2 = compute_week_of_month(d)
    return f"W{week:02d}_M{month:02d}_R{year2:02d}"


# ============================================================
# Detectors
# ============================================================

def detect_campaign_type(
    config: dict | None = None,
    flow_name: str = "",
    trigger: str = "",
) -> tuple[str, str]:
    """
    Rozpoznaje typ kampanii.

    Returns:
        (code, reason) np. ("LinPost", "flow=linkedin_posts")
    """
    rules = _load_rules()
    type_codes = rules.get("campaign_type_codes", {})

    # Zbierz sygnały
    signals = []
    if config:
        ct = config.get("campaign_type", "")
        if ct:
            signals.append(ct.lower())
        source = config.get("source", {})
        if isinstance(source, dict):
            signals.append(source.get("type", "").lower())
    if flow_name:
        signals.append(flow_name.lower())
    if trigger:
        signals.append(trigger.lower())

    combined = " ".join(signals)

    # Szukaj match w triggers
    for code, info in type_codes.items():
        for t in info.get("triggers", []):
            if t in combined:
                return code, f"trigger_match='{t}' in '{combined}'"

    # Heurystyka nazw flow
    flow_map = {
        "run_adhoc_linkedin": "AdHoc",
        "adhoc": "AdHoc",
        "run_csv_campaign": "CSVImport",
        "csv": "CSVImport",
        "simulate_article": "NewsTrig",
        "article": "NewsTrig",
        "linkedin_posts": "LinPost",
        "followup": "FollowUp",
        "no_email": "NoEmail",
    }
    for key, code in flow_map.items():
        if key in combined:
            return code, f"flow_heuristic='{key}'"

    # Config campaign_type - direct match
    if config:
        ct = config.get("campaign_type", "").lower()
        if ct == "outbound":
            return "ApolloList", "config.campaign_type=outbound"

    return "AdHoc", "fallback_default"


def detect_tier(
    tier_info: dict | None = None,
    config: dict | None = None,
) -> tuple[str, str]:
    """
    Mapuje ICP tier na kod kampanijny.

    Args:
        tier_info: wynik z resolve_tier() — dict z kluczem 'tier'
        config: YAML config kampanii

    Returns:
        (code, reason) np. ("T2", "icp_tier=tier_2_procurement_management")
    """
    tier_id = ""
    if tier_info:
        tier_id = tier_info.get("tier", "")
    elif config:
        tier_id = config.get("tier", "")

    rules = _load_rules()
    tier_codes = rules.get("tier_codes", {})

    for code, info in tier_codes.items():
        if info.get("icp_tier_id") == tier_id:
            return code, f"icp_tier={tier_id}"

    # Heurystyka z target_persona
    if config:
        persona = config.get("target_persona", "").lower()
        if persona in ("ceo", "cfo", "owner"):
            return "T1", f"persona_heuristic={persona}"
        if persona in ("cpo", "procurement_director"):
            return "T2", f"persona_heuristic={persona}"
        if persona in ("buyer", "category_manager"):
            return "T3", f"persona_heuristic={persona}"

    return "T0", "tier_uncertain"


def detect_segment(
    industry: str = "",
    config: dict | None = None,
) -> tuple[str, str]:
    """
    Rozpoznaje segment na podstawie branży.

    Returns:
        (code, reason) np. ("Retail", "keyword_match='retail'")
    """
    rules = _load_rules()
    segment_codes = rules.get("segment_codes", {})

    # Zbierz sygnały
    signals = industry.lower()
    if config:
        ti = config.get("target_industry", "")
        if ti:
            signals += " " + ti.lower()
        seg = config.get("segment", "")
        if seg:
            signals += " " + seg.lower()

    for code, info in segment_codes.items():
        for kw in info.get("keywords", []):
            if kw.lower() in signals:
                return code, f"keyword_match='{kw}'"

    # Direct code match
    for code in segment_codes:
        if code.lower() in signals:
            return code, f"direct_code_match='{code}'"

    return "Gen", "fallback_segment_unknown"


def detect_angle(
    brief: str = "",
    config: dict | None = None,
) -> tuple[str, str]:
    """
    Rozpoznaje messaging angle.

    Returns:
        (code, reason) np. ("Savings", "keyword_match='oszczędności'")
    """
    rules = _load_rules()
    angle_codes = rules.get("angle_codes", {})

    signals = brief.lower()
    if config:
        angle = config.get("angle", "")
        if angle:
            signals += " " + angle.lower()
        msg_angle = config.get("messaging_angle", "")
        if msg_angle:
            signals += " " + msg_angle.lower()

    for code, info in angle_codes.items():
        for kw in info.get("keywords", []):
            if kw.lower() in signals:
                return code, f"keyword_match='{kw}'"

    # Direct code match
    for code in angle_codes:
        if code.lower() in signals:
            return code, f"direct_code_match='{code}'"

    return "Gen", "fallback_angle_unknown"


def detect_market(
    language: str = "",
    country: str = "",
    config: dict | None = None,
) -> tuple[str, str]:
    """
    Rozpoznaje rynek.

    Returns:
        (code, reason) np. ("PL", "language_match='pl'")
    """
    rules = _load_rules()
    market_codes = rules.get("market_codes", {})

    lang = language.lower()
    if not lang and config:
        lang = config.get("language_code", "").lower()

    ctry = country.upper()
    if not ctry and config:
        ctry = config.get("country", "").upper()

    # Language match
    for code, info in market_codes.items():
        if lang in [l.lower() for l in info.get("languages", [])]:
            return code, f"language_match='{lang}'"

    # Country match
    for code, info in market_codes.items():
        if ctry in [c.upper() for c in info.get("countries", [])]:
            return code, f"country_match='{ctry}'"

    return "Gen", "fallback_market_unknown"


# ============================================================
# Builder
# ============================================================

def build_campaign_name(
    campaign_type: str = "",
    tier: str = "",
    segment: str = "",
    angle: str = "",
    market: str = "",
    campaign_date: date | datetime | None = None,
    version: int = 1,
) -> str:
    """
    Buduje nazwę kampanii według standardu.

    Args:
        campaign_type: kod typu (np. "LinPost")
        tier: kod tieru (np. "T2")
        segment: kod segmentu (np. "Prod")
        angle: kod angle (np. "Savings")
        market: kod rynku (np. "PL")
        campaign_date: data kampanii (domyślnie dziś)
        version: wersja kampanii

    Returns:
        Nazwa kampanii, np. "LinPost_T2_Prod_Savings_PL_W01_M05_R26_v1"
    """
    timing = format_timing(campaign_date)
    return f"{campaign_type}_{tier}_{segment}_{angle}_{market}_{timing}_v{version}"


def build_campaign_metadata(
    config: dict | None = None,
    tier_info: dict | None = None,
    industry: str = "",
    brief: str = "",
    language: str = "",
    country: str = "",
    flow_name: str = "",
    trigger: str = "",
    campaign_date: date | datetime | None = None,
    version: int = 1,
) -> dict:
    """
    Buduje pełne metadane kampanii (nazwa + rozpoznawanie komponentów).

    Returns:
        dict z polami: campaign_name, campaign_type, campaign_type_reason,
        tier, tier_reason, segment, segment_reason, angle, angle_reason,
        market, market_reason, week_of_month, month, year, version
    """
    ct_code, ct_reason = detect_campaign_type(config=config, flow_name=flow_name, trigger=trigger)
    t_code, t_reason = detect_tier(tier_info=tier_info, config=config)
    seg_code, seg_reason = detect_segment(industry=industry, config=config)
    ang_code, ang_reason = detect_angle(brief=brief, config=config)
    mkt_code, mkt_reason = detect_market(language=language, country=country, config=config)

    week, month, year2 = compute_week_of_month(campaign_date)

    name = build_campaign_name(
        campaign_type=ct_code,
        tier=t_code,
        segment=seg_code,
        angle=ang_code,
        market=mkt_code,
        campaign_date=campaign_date,
        version=version,
    )

    return {
        "campaign_name": name,
        "campaign_type": ct_code,
        "campaign_type_reason": ct_reason,
        "tier": t_code,
        "tier_reason": t_reason,
        "segment": seg_code,
        "segment_reason": seg_reason,
        "angle": ang_code,
        "angle_reason": ang_reason,
        "market": mkt_code,
        "market_reason": mkt_reason,
        "week_of_month": week,
        "month": month,
        "year": 2000 + year2,
        "version": version,
        "delivery_type": _resolve_delivery_type(ct_code),
        "apollo_step_type": _resolve_apollo_step_type(ct_code),
        "sequence_template_name": _resolve_sequence_template(ct_code),
        "is_multichannel": _resolve_delivery_type(ct_code) != "email_auto",
        "apollo_delivery_source": "source_of_truth",
    }


def _resolve_delivery_type(campaign_type: str) -> str:
    """Resolve delivery_type z apollo_campaign_types.yaml."""
    try:
        from core.apollo_campaign_sync import resolve_campaign_delivery_type
        dt, _ = resolve_campaign_delivery_type(campaign_type)
        return dt
    except Exception:
        return "email_auto"


def _resolve_apollo_step_type(campaign_type: str) -> str:
    """Resolve Apollo step type z apollo_campaign_types.yaml."""
    try:
        from core.apollo_campaign_sync import resolve_campaign_delivery_type
        _, ast = resolve_campaign_delivery_type(campaign_type)
        return ast
    except Exception:
        return "Automatic email"


def _resolve_sequence_template(campaign_type: str) -> str:
    """Resolve default sequence template dla campaign type."""
    dt = _resolve_delivery_type(campaign_type)
    if dt == "email_auto":
        return "email_only"
    if dt == "task":
        return "no_email_research"
    return "email_only"
