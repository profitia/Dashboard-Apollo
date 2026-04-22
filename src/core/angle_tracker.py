#!/usr/bin/env python3
"""
Angle Tracker — rozpoznawanie, zapis i rekomendacja angles kampanijnych.

Odpowiada za:
- Rozpoznawanie primary + secondary angle kampanii
- Zapis angle history per kontakt
- Analiza częstotliwości użycia angle'i
- Rekomendacja next angle (heurystyka)
- Tłumaczenie naming_code ↔ angle_id

Źródło taksonomii: source_of_truth/campaign_angles.yaml
"""

import logging
import os
from collections import Counter

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

log = logging.getLogger(__name__)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ANGLES_PATH = os.path.join(_ROOT_DIR, "source_of_truth", "campaign_angles.yaml")

_cached_angles: dict | None = None


# ============================================================
# Load taxonomy
# ============================================================

def _load_angles() -> dict:
    """Wczytuje taksonomię angles z YAML (z cache)."""
    global _cached_angles
    if _cached_angles is not None:
        return _cached_angles
    if yaml is None:
        raise ImportError("PyYAML jest wymagany: pip install pyyaml")
    if not os.path.exists(_ANGLES_PATH):
        raise FileNotFoundError(f"Brak pliku: {_ANGLES_PATH}")
    with open(_ANGLES_PATH, "r", encoding="utf-8") as f:
        _cached_angles = yaml.safe_load(f)
    return _cached_angles


def reset_cache():
    """Czyści cache (np. w testach)."""
    global _cached_angles
    _cached_angles = None


def get_angle_taxonomy() -> dict:
    """Zwraca pełną taksonomię angles."""
    data = _load_angles()
    return data.get("angles", {})


def get_angle_info(angle_id: str) -> dict | None:
    """Zwraca info o angle po angle_id."""
    return get_angle_taxonomy().get(angle_id)


def get_naming_code_mapping() -> dict:
    """Zwraca mapowanie naming_code → default angle_id."""
    data = _load_angles()
    return data.get("naming_code_to_default_angle", {})


# ============================================================
# Resolve angle — ustal primary + secondary z danych pipeline
# ============================================================

def resolve_angles(
    pipeline_result: dict | None = None,
    campaign_metadata: dict | None = None,
    hypothesis_text: str = "",
    message_body: str = "",
    message_subject: str = "",
) -> dict:
    """
    Rozpoznaje primary i secondary angles na podstawie danych pipeline.

    Hierarchia rozpoznawania primary angle:
    1. Explicit angle_id w campaign_metadata lub pipeline_result
    2. naming_code z campaign_metadata.angle → tłumaczenie na angle_id
    3. messaging_angle z icp_tier → keyword match
    4. hypothesis text → keyword match
    5. message subject + body → keyword match
    6. Fallback: "general"

    Returns:
        {
            "primary_angle_id": "savings_delivery",
            "primary_angle_label": "savings delivery",
            "secondary_angle_ids": ["supplier_price_increases"],
            "secondary_angle_labels": ["podwyżki dostawców"],
            "resolution_method": "naming_code_mapping",
        }
    """
    taxonomy = get_angle_taxonomy()
    nc_map = get_naming_code_mapping()

    primary_id = None
    resolution_method = "fallback"

    # 1. Explicit angle_id
    if pipeline_result:
        explicit = pipeline_result.get("angle_id", "")
        if explicit and explicit in taxonomy:
            primary_id = explicit
            resolution_method = "explicit_angle_id"

    # 2. naming_code z campaign_metadata.angle
    if not primary_id and campaign_metadata:
        naming_code = campaign_metadata.get("angle", "")
        if naming_code and naming_code in nc_map:
            primary_id = nc_map[naming_code]
            resolution_method = "naming_code_mapping"

    # 3. messaging_angle z icp_tier
    if not primary_id and pipeline_result:
        tier_info = pipeline_result.get("icp_tier", {})
        messaging_angle = tier_info.get("messaging_angle", "")
        if messaging_angle:
            matched = _keyword_match(messaging_angle, taxonomy)
            if matched:
                primary_id = matched
                resolution_method = "messaging_angle_keyword"

    # 4. hypothesis text
    if not primary_id and hypothesis_text:
        matched = _keyword_match(hypothesis_text, taxonomy)
        if matched:
            primary_id = matched
            resolution_method = "hypothesis_keyword"
    if not primary_id and pipeline_result:
        hyp = pipeline_result.get("hypothesis", {})
        hyp_text = hyp.get("hypothesis", "")
        if hyp_text:
            matched = _keyword_match(hyp_text, taxonomy)
            if matched:
                primary_id = matched
                resolution_method = "hypothesis_keyword"

    # 5. message subject + body
    if not primary_id:
        combined = f"{message_subject} {message_body}"
        if not combined.strip() and pipeline_result:
            msg = pipeline_result.get("message", {})
            combined = f"{msg.get('subject', '')} {msg.get('body', '')}"
        if combined.strip():
            matched = _keyword_match(combined, taxonomy)
            if matched:
                primary_id = matched
                resolution_method = "message_content_keyword"

    # 6. Fallback
    if not primary_id:
        primary_id = "general"
        resolution_method = "fallback"

    # Secondary angles: szukaj dodatkowych angle'i w treści
    secondary_ids = _find_secondary_angles(
        primary_id,
        hypothesis_text or (pipeline_result or {}).get("hypothesis", {}).get("hypothesis", ""),
        message_subject or (pipeline_result or {}).get("message", {}).get("subject", ""),
        message_body or (pipeline_result or {}).get("message", {}).get("body", ""),
        taxonomy,
    )

    # Buduj wynik
    primary_info = taxonomy.get(primary_id, {})
    result = {
        "primary_angle_id": primary_id,
        "primary_angle_label": primary_info.get("label_pl", primary_id),
        "secondary_angle_ids": secondary_ids,
        "secondary_angle_labels": [
            taxonomy.get(a, {}).get("label_pl", a) for a in secondary_ids
        ],
        "resolution_method": resolution_method,
    }

    return result


def _keyword_match(text: str, taxonomy: dict) -> str | None:
    """Szuka najlepszego keyword match w tekście. Zwraca angle_id lub None."""
    text_lower = text.lower()
    best_match = None
    best_count = 0

    for angle_id, info in taxonomy.items():
        if angle_id == "general":
            continue
        keywords = info.get("keywords", [])
        count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if count > best_count:
            best_count = count
            best_match = angle_id

    return best_match


def _find_secondary_angles(
    primary_id: str,
    hypothesis: str,
    subject: str,
    body: str,
    taxonomy: dict,
) -> list[str]:
    """Szuka secondary angles w treści (max 3, bez primary)."""
    combined = f"{hypothesis} {subject} {body}".lower()
    if not combined.strip():
        return []

    candidates = []
    for angle_id, info in taxonomy.items():
        if angle_id == primary_id or angle_id == "general":
            continue
        keywords = info.get("keywords", [])
        hits = sum(1 for kw in keywords if kw.lower() in combined)
        if hits > 0:
            candidates.append((angle_id, hits))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidates[:3]]


# ============================================================
# Angle history analysis
# ============================================================

def build_angle_history(profile: dict) -> list[dict]:
    """
    Buduje historię angles z profilu engagement.

    Przegląda outreach_history i wyciąga angle data z metadata.

    Returns:
        Lista dict z polami:
        - campaign_name, sent_date
        - primary_angle_id, primary_angle_label
        - secondary_angle_ids, secondary_angle_labels
    """
    taxonomy = get_angle_taxonomy()
    nc_map = get_naming_code_mapping()
    history = []

    for entry in profile.get("outreach_history", []):
        meta = entry.get("metadata", {})
        angle_data = entry.get("angle_data", {})

        if angle_data:
            # Nowe wpisy mają angle_data bezpośrednio
            history.append({
                "campaign_name": entry.get("campaign_name", ""),
                "sent_date": entry.get("sent_date", ""),
                "primary_angle_id": angle_data.get("primary_angle_id", "general"),
                "primary_angle_label": angle_data.get("primary_angle_label", ""),
                "secondary_angle_ids": angle_data.get("secondary_angle_ids", []),
                "secondary_angle_labels": angle_data.get("secondary_angle_labels", []),
            })
        elif meta:
            # Stare wpisy: próbuj odtworzyć angle z metadata
            angle_code = meta.get("angle", "")
            angle_id = "general"
            if angle_code and angle_code in nc_map:
                angle_id = nc_map[angle_code]
            elif angle_code:
                # Próbuj direct match do taxonomy
                if angle_code.lower() in taxonomy:
                    angle_id = angle_code.lower()

            info = taxonomy.get(angle_id, {})
            history.append({
                "campaign_name": entry.get("campaign_name", ""),
                "sent_date": entry.get("sent_date", ""),
                "primary_angle_id": angle_id,
                "primary_angle_label": info.get("label_pl", angle_id),
                "secondary_angle_ids": [],
                "secondary_angle_labels": [],
            })

    return history


def build_angle_summary(profile: dict) -> dict:
    """
    Buduje podsumowanie historii angles kontaktu.

    Returns:
        {
            "angle_history": [...],
            "used_angles": ["savings_delivery", "supplier_price_increases"],
            "used_angle_labels": ["savings delivery", "podwyżki dostawców"],
            "most_recent_angle": "savings_delivery",
            "most_recent_angle_label": "savings delivery",
            "angle_frequency": {"savings_delivery": 2, ...},
            "total_campaigns_with_angles": 2,
            "overused_angles": ["savings_delivery"],
            "recommended_next_angle_strategy": "...",
        }
    """
    taxonomy = get_angle_taxonomy()
    angle_hist = build_angle_history(profile)

    if not angle_hist:
        return {
            "angle_history": [],
            "used_angles": [],
            "used_angle_labels": [],
            "most_recent_angle": None,
            "most_recent_angle_label": None,
            "angle_frequency": {},
            "total_campaigns_with_angles": 0,
            "overused_angles": [],
            "recommended_next_angle_strategy": "first_outbound - any angle appropriate",
        }

    # Zlicz użycia
    primary_ids = [h["primary_angle_id"] for h in angle_hist]
    freq = dict(Counter(primary_ids))

    used_ids = list(dict.fromkeys(primary_ids))  # preserves order, unique
    used_labels = [
        taxonomy.get(a, {}).get("label_pl", a) for a in used_ids
    ]

    most_recent = angle_hist[-1]["primary_angle_id"]
    most_recent_label = angle_hist[-1]["primary_angle_label"]

    # Sprawdź overused (>= threshold bez reply)
    overused = []
    for angle_id, count in freq.items():
        info = taxonomy.get(angle_id, {})
        threshold = info.get("avoid_repeat_threshold", 2)
        if count >= threshold and angle_id != "general":
            overused.append(angle_id)

    # Rekomendacja
    strategy = _recommend_next_angle_strategy(
        angle_hist, freq, overused, most_recent, taxonomy, profile
    )

    return {
        "angle_history": angle_hist,
        "used_angles": used_ids,
        "used_angle_labels": used_labels,
        "most_recent_angle": most_recent,
        "most_recent_angle_label": most_recent_label,
        "angle_frequency": freq,
        "total_campaigns_with_angles": len(angle_hist),
        "overused_angles": overused,
        "recommended_next_angle_strategy": strategy,
    }


# ============================================================
# Next angle recommendation (heurystyka)
# ============================================================

def _recommend_next_angle_strategy(
    angle_hist: list[dict],
    freq: dict,
    overused: list[str],
    most_recent: str,
    taxonomy: dict,
    profile: dict,
) -> str:
    """Heurystyczna rekomendacja strategii następnego angle."""
    status = profile.get("current_status", "never_contacted")
    replied = profile.get("engagement_snapshot", {}).get("replied", False)

    if not angle_hist:
        return "first_outbound - any angle appropriate"

    if replied:
        return (
            f"Contact replied (most recent angle: {most_recent}). "
            f"Continue with the angle that worked or deepen it."
        )

    if overused:
        overused_labels = [taxonomy.get(a, {}).get("label_pl", a) for a in overused]
        related = _get_unused_related_angles(overused, freq, taxonomy)
        if related:
            related_labels = [taxonomy.get(a, {}).get("label_pl", a) for a in related[:3]]
            return (
                f"Overused angles: {', '.join(overused_labels)}. "
                f"Change narrative. Suggested: {', '.join(related_labels)}."
            )
        return (
            f"Overused angles: {', '.join(overused_labels)}. "
            f"Change narrative completely - fresh angle needed."
        )

    if len(angle_hist) == 1:
        recent_info = taxonomy.get(most_recent, {})
        related = recent_info.get("related_angles", [])
        unused_related = [a for a in related if a not in freq]
        if unused_related:
            labels = [taxonomy.get(a, {}).get("label_pl", a) for a in unused_related[:2]]
            return (
                f"One campaign sent (angle: {taxonomy.get(most_recent, {}).get('label_pl', most_recent)}). "
                f"Consider related: {', '.join(labels)}."
            )
        return (
            f"One campaign sent (angle: {taxonomy.get(most_recent, {}).get('label_pl', most_recent)}). "
            f"Same angle can be retried with different framing, or switch to new angle."
        )

    # Multiple campaigns, no overuse yet
    recent_label = taxonomy.get(most_recent, {}).get("label_pl", most_recent)
    return (
        f"Last angle: {recent_label}. "
        f"{len(angle_hist)} campaigns sent. "
        f"Consider new angle or continuation with different framing."
    )


def _get_unused_related_angles(
    overused: list[str],
    freq: dict,
    taxonomy: dict,
) -> list[str]:
    """Zwraca related angles, które nie były jeszcze używane."""
    candidates = set()
    for angle_id in overused:
        info = taxonomy.get(angle_id, {})
        for related in info.get("related_angles", []):
            if related not in freq and related != "general":
                candidates.add(related)
    return sorted(candidates)


# ============================================================
# Suggest specific next angles
# ============================================================

def suggest_next_angles(profile: dict, max_suggestions: int = 3) -> list[dict]:
    """
    Sugeruje konkretne next angles na podstawie historii kontaktu.

    Returns:
        Lista dict:
        [
            {"angle_id": "negotiation_preparation", "label_pl": "przygotowanie negocjacji",
             "reason": "related to savings_delivery, not yet used"},
            ...
        ]
    """
    taxonomy = get_angle_taxonomy()
    summary = build_angle_summary(profile)
    freq = summary["angle_frequency"]
    used = set(summary["used_angles"])

    # Zbierz kandydatów: related angles z użytych, ale jeszcze nieużyte
    candidates = []
    for used_id in summary["used_angles"]:
        info = taxonomy.get(used_id, {})
        for related_id in info.get("related_angles", []):
            if related_id not in used and related_id != "general":
                candidates.append({
                    "angle_id": related_id,
                    "label_pl": taxonomy.get(related_id, {}).get("label_pl", related_id),
                    "reason": f"related to {info.get('label_pl', used_id)}, not yet used",
                })

    # Deduplikuj
    seen = set()
    unique = []
    for c in candidates:
        if c["angle_id"] not in seen:
            seen.add(c["angle_id"])
            unique.append(c)

    # Jeśli mało kandydatów, dodaj losowe niewykorzystane
    if len(unique) < max_suggestions:
        for angle_id, info in taxonomy.items():
            if angle_id not in used and angle_id != "general" and angle_id not in seen:
                unique.append({
                    "angle_id": angle_id,
                    "label_pl": info.get("label_pl", angle_id),
                    "reason": "not yet used with this contact",
                })
                seen.add(angle_id)

    return unique[:max_suggestions]
