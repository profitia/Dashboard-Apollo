"""
Relevance Scorer — ocenia artykuł pod kątem relewantności branżowej i zakupowej.

Scoring 0-100:
  - Industry relevance (A): max 40 pkt
  - Purchase signal (B): max 40 pkt
  - Freshness bonus: max 20 pkt

Artykuł jest kwalifikowany gdy:
  - total_score >= min_relevance_score (z campaign_config.yaml)
  - industry_score >= min_industry_score
  - purchase_signal_score >= min_purchase_signal_score
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class RelevanceResult:
    qualified: bool
    total_score: float
    industry_score: float
    purchase_signal_score: float
    freshness_bonus: float
    matched_industry_terms: dict[str, list[str]]   # group → [terms]
    matched_purchase_terms: dict[str, list[str]]   # group → [terms]
    matched_amplifiers: list[str]
    article_age_days: int | None
    disqualification_reason: str | None
    explanation: str


def _normalize(text: str) -> str:
    """Lowercase + usuń nadmiarowe spacje."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _count_hits(text: str, terms: list[str]) -> list[str]:
    """Zwraca listę termów, które wystąpiły w tekście."""
    norm = _normalize(text)
    hits = []
    for term in terms:
        if _normalize(term) in norm:
            hits.append(term)
    return hits


def _get_article_age_days(published_at: str | datetime | None) -> int | None:
    """Oblicza wiek artykułu w dniach. None jeśli brak daty."""
    if not published_at:
        return None
    try:
        if isinstance(published_at, datetime):
            pub_dt = published_at
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - pub_dt
            return max(0, delta.days)
        # Handle various string formats
        for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
            try:
                pub_dt = datetime.strptime(published_at[:19], fmt[:len(published_at[:19])])
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - pub_dt
                return max(0, delta.days)
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _freshness_bonus(age_days: int | None, freshness_config: dict) -> float:
    if age_days is None:
        return 5  # brak daty → mały bonus zamiast 0
    if age_days <= 1:
        return freshness_config.get("age_0_1_days", 20)
    if age_days <= 3:
        return freshness_config.get("age_1_3_days", 15)
    if age_days <= 7:
        return freshness_config.get("age_3_7_days", 10)
    if age_days <= 14:
        return freshness_config.get("age_7_14_days", 5)
    return freshness_config.get("age_14_plus_days", 0)


def score_article(
    full_text: str,
    tags: list[str],
    title: str,
    published_at: str | None,
    keywords_config: dict,
    campaign_config: dict,
) -> RelevanceResult:
    """
    Ocenia relewantność artykułu.

    Args:
        full_text: połączony tytuł + lead + body (lowercase OK)
        tags: tagi artykułu
        title: tytuł artykułu (dla osobnego ważenia)
        published_at: data publikacji ISO8601
        keywords_config: zawartość keywords.yaml
        campaign_config: zawartość campaign_config.yaml

    Returns:
        RelevanceResult
    """
    min_total = campaign_config.get("min_relevance_score", 40)
    min_industry = campaign_config.get("min_industry_score", 15)
    min_purchase = campaign_config.get("min_purchase_signal_score", 15)
    max_article_age = campaign_config.get("max_article_age_days", 14)

    # --- Industry scoring (A) ---
    industry_kw = keywords_config.get("industry_keywords", {})
    industry_score = 0.0
    matched_industry: dict[str, list[str]] = {}

    # Tags bonus: tagi mają podwójną wagę (precyzyjny sygnał)
    tags_text = " ".join(tags)
    search_text = full_text + " " + tags_text + " " + title

    for group_id, group in industry_kw.items():
        weight = group.get("weight", 1)
        terms = group.get("terms", [])
        hits = _count_hits(search_text, terms)
        # Bonus × 2 jeśli hit w tytule
        title_hits = _count_hits(title, terms)
        score_contribution = (len(hits) * weight) + (len(title_hits) * weight)
        if hits:
            matched_industry[group_id] = hits
            industry_score += score_contribution

    # Normalize to max 40
    industry_score = min(40.0, industry_score)

    # --- Purchase signal scoring (B) ---
    purchase_kw = keywords_config.get("purchase_signals", {})
    purchase_score = 0.0
    matched_purchase: dict[str, list[str]] = {}

    for group_id, group in purchase_kw.items():
        weight = group.get("weight", 1)
        terms = group.get("terms", [])
        hits = _count_hits(search_text, terms)
        title_hits = _count_hits(title, terms)
        score_contribution = (len(hits) * weight) + (len(title_hits) * weight)
        if hits:
            matched_purchase[group_id] = hits
            purchase_score += score_contribution

    purchase_score = min(40.0, purchase_score)

    # --- Amplifiers ---
    amplifier_config = keywords_config.get("amplifier_signals", {})
    amp_terms = amplifier_config.get("terms", [])
    amp_weight = amplifier_config.get("weight", 2)
    amp_hits = _count_hits(search_text, amp_terms)
    amp_bonus = min(10.0, len(amp_hits) * amp_weight)

    # --- Procurement vocabulary ---
    proc_config = keywords_config.get("procurement_vocabulary", {})
    proc_terms = proc_config.get("terms", [])
    proc_weight = proc_config.get("weight", 2)
    proc_hits = _count_hits(search_text, proc_terms)
    proc_bonus = min(5.0, len(proc_hits) * proc_weight)

    # --- Freshness ---
    freshness_config = keywords_config.get("freshness_scoring", {})
    age_days = _get_article_age_days(published_at)
    fresh_bonus = _freshness_bonus(age_days, freshness_config)

    total = industry_score + purchase_score + fresh_bonus + amp_bonus + proc_bonus
    total = min(100.0, total)

    # --- Kwalifikacja ---
    disqualification_reason = None

    # Sprawdzenie freshness (wiek)
    if age_days is not None and age_days > max_article_age:
        disqualification_reason = f"Article too old: {age_days} days (max {max_article_age})"

    # Minimalne progi
    if not disqualification_reason and industry_score < min_industry:
        disqualification_reason = (
            f"Industry score too low: {industry_score:.1f} (min {min_industry}). "
            f"Matched groups: {list(matched_industry.keys()) or 'none'}"
        )
    if not disqualification_reason and purchase_score < min_purchase:
        disqualification_reason = (
            f"Purchase signal score too low: {purchase_score:.1f} (min {min_purchase}). "
            f"Matched groups: {list(matched_purchase.keys()) or 'none'}"
        )
    if not disqualification_reason and total < min_total:
        disqualification_reason = f"Total score too low: {total:.1f} (min {min_total})"

    qualified = disqualification_reason is None

    # --- Explanation ---
    parts = []
    if matched_industry:
        for gid, terms in matched_industry.items():
            parts.append(f"[Industry/{gid}]: {', '.join(terms[:5])}")
    if matched_purchase:
        for gid, terms in matched_purchase.items():
            parts.append(f"[Signal/{gid}]: {', '.join(terms[:5])}")
    if amp_hits:
        parts.append(f"[Amplifiers]: {', '.join(amp_hits[:3])}")
    if age_days is not None:
        parts.append(f"[Age]: {age_days} days")

    explanation = "; ".join(parts) if parts else "No significant matches found."

    return RelevanceResult(
        qualified=qualified,
        total_score=round(total, 1),
        industry_score=round(industry_score, 1),
        purchase_signal_score=round(purchase_score, 1),
        freshness_bonus=round(fresh_bonus, 1),
        matched_industry_terms=matched_industry,
        matched_purchase_terms=matched_purchase,
        matched_amplifiers=amp_hits,
        article_age_days=age_days,
        disqualification_reason=disqualification_reason,
        explanation=explanation,
    )
