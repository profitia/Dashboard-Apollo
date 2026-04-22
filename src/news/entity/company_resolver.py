"""
Company Resolution Layer — dopasowuje firmę z artykułu do właściwej organizacji w Apollo.

Cel: uniknąć sytuacji, w której pipeline szuka kontaktów dla "Evra Fish" gdy firma
w Apollo figuruje jako "EvraFish" lub odwrotnie. Warstwa buduje listę kandydatów
z Apollo, ocenia ich heurystycznie i przez LLM, zwraca resolved company.

Architektura:
    entity_extractor → [company_resolver] → contact_finder

Zasada:
    LLM jako warstwa OCENY nad ustrukturyzowanymi dowodami.
    NIE jako jedyne źródło prawdy.

Statusy rozstrzygnięcia:
    MATCH_CONFIDENT  — pewne dopasowanie (confidence >= confident_threshold)
    MATCH_POSSIBLE   — prawdopodobne dopasowanie (confidence >= min_confidence)
    AMBIGUOUS_HOLD   — kilka kandydatów, brak wyraźnego zwycięzcy → manual review
    NO_MATCH         — brak kandydatów z Apollo

Backward compatibility:
    Jeśli Apollo niedostępny lub resolution layer wyłączony, pipeline działa normalnie.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stałe statusów
# ---------------------------------------------------------------------------
STATUS_CONFIDENT = "MATCH_CONFIDENT"
STATUS_POSSIBLE  = "MATCH_POSSIBLE"
STATUS_AMBIGUOUS = "AMBIGUOUS_HOLD"
STATUS_NO_MATCH  = "NO_MATCH"

# ---------------------------------------------------------------------------
# Wynik resolution
# ---------------------------------------------------------------------------

@dataclass
class ResolutionResult:
    """Wynik warstwy Company Resolution."""
    resolved_company_name: str
    resolved_company_id: str | None
    resolved_domain: str | None
    resolution_confidence: float          # 0.0–1.0
    resolution_status: str                # MATCH_CONFIDENT | MATCH_POSSIBLE | AMBIGUOUS_HOLD | NO_MATCH
    resolution_reason: str
    candidate_summary: list[dict]         # lista kandydatów ze scorami
    requires_manual_review: bool


def _make_no_match_result(reason: str) -> ResolutionResult:
    return ResolutionResult(
        resolved_company_name="",
        resolved_company_id=None,
        resolved_domain=None,
        resolution_confidence=0.0,
        resolution_status=STATUS_NO_MATCH,
        resolution_reason=reason,
        candidate_summary=[],
        requires_manual_review=False,
    )


def _make_ambiguous_result(candidates: list[dict], reason: str) -> ResolutionResult:
    return ResolutionResult(
        resolved_company_name="",
        resolved_company_id=None,
        resolved_domain=None,
        resolution_confidence=0.0,
        resolution_status=STATUS_AMBIGUOUS,
        resolution_reason=reason,
        candidate_summary=candidates,
        requires_manual_review=True,
    )


# ---------------------------------------------------------------------------
# Import pomocniczy — comparison key
# ---------------------------------------------------------------------------

def _get_comparison_key(name: str) -> str:
    """Importuje make_comparison_key z normalizer lub używa inline fallback."""
    try:
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        src_dir = os.path.join(_root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from news.utils.company_normalizer import make_comparison_key
        return make_comparison_key(name)
    except Exception:
        # Inline fallback
        n = name.lower().strip()
        n = re.sub(r"\b(sp\.?\s*z\s*o\.?\s*o\.?|s\.?\s*a\.?|sp\.?\s*j\.?|sp\.?\s*k\.?|gmbh|ltd\.?|inc\.?|llc\.?)\b", "", n, flags=re.IGNORECASE)
        n = re.sub(r"[^\w]", "", n)
        return n


# ---------------------------------------------------------------------------
# Apollo organization search
# ---------------------------------------------------------------------------

def _get_apollo_client():
    """Lazy import ApolloClient z Integracje/."""
    _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    integracje_dir = os.path.join(_root, "Integracje")
    if integracje_dir not in sys.path:
        sys.path.insert(0, integracje_dir)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(integracje_dir, ".env"))
    except ImportError:
        pass
    from apollo_client import ApolloClient
    return ApolloClient()


def _search_apollo_orgs(query_name: str, per_page: int = 10) -> list[dict]:
    """
    Szuka organizacji w Apollo po nazwie.
    Używa POST /v1/mixed_companies/search (search_organizations w apollo_client).

    Returns:
        Lista surowych rekordów organizacji z Apollo lub [] przy błędzie.
    """
    try:
        client = _get_apollo_client()
        orgs, _ = client.search_organizations(q_keywords=query_name, per_page=per_page)
        log.info("[Resolver] Apollo org search '%s' → %d candidates", query_name, len(orgs))
        return orgs
    except Exception as exc:
        log.warning("[Resolver] Apollo org search failed for '%s': %s", query_name, exc)
        return []


def _search_apollo_people_for_orgs(query_name: str, per_page: int = 10) -> list[dict]:
    """
    Fallback: szuka przez people search i wyciąga unikatowe org records.
    Przydatne gdy małe polskie firmy nie są indeksowane w org search,
    ale ich pracownicy figurują w indeksie ludzi (przez LinkedIn scraping).

    Używa POST /v1/mixed_people/api_search z q_organization_name.

    Returns:
        Lista unikatowych rekordów org wyciągniętych z rekordów people.
    """
    try:
        client = _get_apollo_client()
        payload = {
            "q_organization_name": query_name,
            "per_page": per_page,
            "page": 1,
        }
        data = client._post("mixed_people/api_search", payload)
        people = data.get("people", []) or []

        seen_ids: set[str] = set()
        orgs: list[dict] = []
        for person in people:
            # Org może być zagnieżdżona lub jako pola bezpośrednio na person
            org = person.get("organization") or {}
            if not org:
                org_id = person.get("organization_id") or ""
                org_name = person.get("organization_name") or person.get("company_name") or ""
                org_domain = person.get("organization_domain") or ""
                if org_id or org_name:
                    org = {
                        "id": org_id,
                        "name": org_name,
                        "primary_domain": org_domain,
                        "industry": person.get("organization_industry") or "",
                        "keywords": [],
                    }

            org_id = org.get("id") or ""
            org_name = org.get("name") or ""
            if not org_name:
                continue

            dedup = org_id if org_id else _get_comparison_key(org_name)
            if dedup in seen_ids:
                continue
            seen_ids.add(dedup)
            orgs.append(org)

        log.info("[Resolver] Apollo people search '%s' → %d unique orgs", query_name, len(orgs))
        return orgs
    except Exception as exc:
        log.warning("[Resolver] Apollo people search failed for '%s': %s", query_name, exc)
        return []


# ---------------------------------------------------------------------------
# Alias dictionary loader
# ---------------------------------------------------------------------------

def _load_alias_dict(alias_dict_path: str) -> list[dict]:
    """
    Ładuje alias dictionary z pliku YAML.
    Ścieżka może być bezwzględna lub względna do katalogu workspace.

    Returns:
        Lista wpisów alias dict lub [] przy błędzie/braku pliku.
    """
    if not alias_dict_path:
        return []
    try:
        import yaml
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if not os.path.isabs(alias_dict_path):
            alias_dict_path = os.path.join(_root, alias_dict_path)
        if not os.path.exists(alias_dict_path):
            log.debug("[Resolver] Alias dict not found: %s", alias_dict_path)
            return []
        with open(alias_dict_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        entries = data.get("aliases", []) or []
        log.debug("[Resolver] Loaded %d alias entries from %s", len(entries), alias_dict_path)
        return entries
    except Exception as exc:
        log.warning("[Resolver] Alias dict load failed: %s", exc)
        return []


def _apply_alias_lookup(
    source_name: str,
    canonical_name: str,
    alias_entries: list[dict],
) -> dict:
    """
    Szuka dopasowania w alias dictionary.
    Porównuje source_name i canonical_name z każdą listą source_variants.

    Returns:
        Dict z kluczami (wszystkie opcjonalne):
            canonical_name_override: str — nowa canonical_name do szukania
            extra_queries: list[str] — dodatkowe warianty do przeszukania
            domain_hint: str — hint domeny (używany w score_heuristic)
    """
    if not alias_entries:
        return {}

    norm_source = source_name.strip().lower()
    norm_canonical = canonical_name.strip().lower()

    for entry in alias_entries:
        variants = entry.get("source_variants") or []
        norm_variants = [v.strip().lower() for v in variants]
        if norm_source in norm_variants or norm_canonical in norm_variants:
            result: dict = {}
            if entry.get("canonical_name"):
                result["canonical_name_override"] = entry["canonical_name"]
            if entry.get("search_variants"):
                result["extra_queries"] = [v for v in entry["search_variants"] if v.strip()]
            if entry.get("domain"):
                result["domain_hint"] = entry["domain"].strip()
            if result:
                log.info(
                    "[Resolver] Alias match for '%s' → canonical='%s', domain='%s', extra_queries=%s",
                    source_name,
                    result.get("canonical_name_override", canonical_name),
                    result.get("domain_hint", ""),
                    result.get("extra_queries", []),
                )
            return result

    return {}


def _collect_candidates(
    source_company_name: str,
    canonical_name: str,
    comparison_key: str,
    max_per_query: int = 8,
    extra_queries: list[str] | None = None,
) -> list[dict]:
    """
    Zbiera kandydatów organizacyjnych z Apollo dla wszystkich wariantów nazwy.

    Strategia:
    1. Szukaj po canonical_name (primary — branding firmy)
    2. Szukaj po extra_queries (z alias dict — dodatkowe warianty)
    3. Szukaj po source_company_name jeśli różni się od canonical
    4. Jeśli org search = 0 → fallback do people search (wyciąga org info z rekordów osób)
    5. Scalaj wyniki, deduplikuj po apollo_org_id lub comparison_key nazwy

    Returns:
        Lista unikatowych rekordów org z Apollo.
    """
    queries: list[str] = [canonical_name]
    known_lower = {canonical_name.strip().lower()}

    if extra_queries:
        for q in extra_queries:
            if q and q.strip().lower() not in known_lower:
                queries.append(q)
                known_lower.add(q.strip().lower())

    if source_company_name and source_company_name.strip().lower() not in known_lower:
        queries.append(source_company_name)
        known_lower.add(source_company_name.strip().lower())

    seen_ids: set[str] = set()
    candidates: list[dict] = []

    for query in queries:
        orgs = _search_apollo_orgs(query, per_page=max_per_query)
        for org in orgs:
            org_id = org.get("id") or ""
            org_name = org.get("name") or ""
            org_key = _get_comparison_key(org_name) if org_name else ""

            dedup_key = org_id if org_id else org_key
            if not dedup_key or dedup_key in seen_ids:
                continue
            seen_ids.add(dedup_key)
            candidates.append(org)

    # Fallback: people search (gdy org search nie daje wyników)
    if not candidates:
        log.info(
            "[Resolver] Org search returned 0 results for '%s' — trying people search fallback",
            canonical_name,
        )
        fallback_queries = [canonical_name] + (extra_queries or [])
        for query in fallback_queries:
            people_orgs = _search_apollo_people_for_orgs(query, per_page=max_per_query)
            for org in people_orgs:
                org_id = org.get("id") or ""
                org_name = org.get("name") or ""
                org_key = _get_comparison_key(org_name) if org_name else ""
                dedup_key = org_id if org_id else org_key
                if not dedup_key or dedup_key in seen_ids:
                    continue
                seen_ids.add(dedup_key)
                candidates.append(org)
            if candidates:
                break  # znaleziono wyniki — nie szukaj dalej

    return candidates


# ---------------------------------------------------------------------------
# Heuristic scoring per candidate
# ---------------------------------------------------------------------------

def _name_similarity(a: str, b: str) -> float:
    """SequenceMatcher similarity 0.0–1.0."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _domain_contains_key(domain: str, comparison_key: str) -> bool:
    """Sprawdza czy domena zawiera comparison_key (bez TLD)."""
    if not domain or not comparison_key or len(comparison_key) < 3:
        return False
    domain_clean = re.sub(r"\.(com|pl|eu|net|org|io|co\.\w+)$", "", domain.lower())
    domain_clean = re.sub(r"^www\.", "", domain_clean)
    domain_key = re.sub(r"[^\w]", "", domain_clean)
    return comparison_key in domain_key or domain_key in comparison_key


def _score_candidate_heuristic(
    org: dict,
    source_company_name: str,
    canonical_name: str,
    comparison_key: str,
    article_industry_context: str,
) -> tuple[float, list[str]]:
    """
    Ocenia kandydata heurystycznie.

    Returns:
        (score: float 0.0–1.0, signals: list[str])
    """
    score = 0.0
    signals: list[str] = []

    org_name = org.get("name") or ""
    org_domain = org.get("primary_domain") or org.get("website_url") or ""
    # Wyczyść domain jeśli to URL
    if org_domain.startswith("http"):
        from urllib.parse import urlparse
        org_domain = urlparse(org_domain).netloc or org_domain
    org_industry = org.get("industry") or ""
    org_keywords = " ".join(org.get("keywords") or [])

    org_comparison_key = _get_comparison_key(org_name)

    # --- Sygnał 1: exact comparison_key match (najsilniejszy sygnał) ---
    if org_comparison_key and comparison_key and org_comparison_key == comparison_key:
        score += 0.45
        signals.append(f"comparison_key_exact_match: '{comparison_key}'")
    elif org_comparison_key and comparison_key and (
        org_comparison_key in comparison_key or comparison_key in org_comparison_key
    ) and min(len(org_comparison_key), len(comparison_key)) >= 4:
        score += 0.25
        signals.append(f"comparison_key_partial_match: '{org_comparison_key}' ↔ '{comparison_key}'")

    # --- Sygnał 2: name similarity ---
    sim_canonical = _name_similarity(org_name, canonical_name)
    sim_source = _name_similarity(org_name, source_company_name)
    sim = max(sim_canonical, sim_source)
    if sim >= 0.90:
        score += 0.20
        signals.append(f"name_similarity_high: {sim:.2f}")
    elif sim >= 0.70:
        score += 0.10
        signals.append(f"name_similarity_medium: {sim:.2f}")
    elif sim >= 0.50:
        score += 0.05
        signals.append(f"name_similarity_low: {sim:.2f}")

    # --- Sygnał 3: domain match ---
    if org_domain and _domain_contains_key(org_domain, comparison_key):
        score += 0.20
        signals.append(f"domain_matches_key: '{org_domain}'")
    elif org_domain and _domain_contains_key(org_domain, _get_comparison_key(canonical_name)):
        score += 0.15
        signals.append(f"domain_matches_canonical: '{org_domain}'")

    # --- Sygnał 4: industry alignment ---
    if article_industry_context and org_industry:
        art_lower = article_industry_context.lower()
        org_ind_lower = org_industry.lower()
        # Industry overlap heuristic — sprawdź wspólne słowa
        art_words = set(re.findall(r"\b\w{4,}\b", art_lower))
        org_words = set(re.findall(r"\b\w{4,}\b", org_ind_lower))
        overlap = art_words & org_words
        if overlap:
            score += min(0.10, 0.05 * len(overlap))
            signals.append(f"industry_overlap: {list(overlap)[:3]}")

    # --- Sygnał 5: keywords in org match article context ---
    if article_industry_context and org_keywords:
        art_lower = article_industry_context.lower()
        kw_list = [k.strip().lower() for k in org_keywords.split() if len(k.strip()) >= 4]
        matches = [kw for kw in kw_list if kw in art_lower]
        if matches:
            score += min(0.05, 0.02 * len(matches))
            signals.append(f"keyword_context_overlap: {matches[:3]}")

    return min(score, 1.0), signals


# ---------------------------------------------------------------------------
# Optional website verification
# ---------------------------------------------------------------------------

def _fetch_website_signals(domain: str, timeout: int = 5) -> dict:
    """
    Pobiera lekkie sygnały ze strony firmowej (title, meta description, h1).
    Nie scrapuje całej strony — tylko nagłówki HTML.

    Returns:
        dict z kluczami: title, description, h1_text lub {} przy błędzie
    """
    if not domain:
        return {}

    url = domain if domain.startswith("http") else f"https://{domain}"
    try:
        import requests
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SpendGuruBot/1.0)"},
            allow_redirects=True,
            stream=True,
        )
        # Pobierz tylko pierwsze 8KB
        content = b""
        for chunk in resp.iter_content(chunk_size=1024):
            content += chunk
            if len(content) >= 8192:
                break
        html = content.decode("utf-8", errors="ignore")

        result = {}

        # Title
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_m:
            result["title"] = re.sub(r"\s+", " ", title_m.group(1)).strip()[:200]

        # Meta description
        desc_m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if desc_m:
            result["description"] = desc_m.group(1).strip()[:300]

        # Pierwszy h1
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_m:
            result["h1_text"] = re.sub(r"<[^>]+>", "", h1_m.group(1)).strip()[:150]

        return result
    except Exception as exc:
        log.debug("[Resolver] Website fetch failed for '%s': %s", domain, exc)
        return {}


def _website_signal_score(
    website_data: dict,
    canonical_name: str,
    comparison_key: str,
    article_industry_context: str,
) -> tuple[float, str]:
    """
    Ocenia dopasowanie strony www do firmy i kontekstu artykułu.

    Returns:
        (bonus_score: float, reason: str)
    """
    if not website_data:
        return 0.0, ""

    all_text = " ".join([
        website_data.get("title", ""),
        website_data.get("description", ""),
        website_data.get("h1_text", ""),
    ]).lower()

    signals = []

    # Czy nazwa firmy pojawia się na stronie
    if comparison_key and len(comparison_key) >= 3:
        if comparison_key in re.sub(r"\s+", "", all_text):
            signals.append("company_key_in_website")

    # Canonical name na stronie
    if canonical_name and len(canonical_name) >= 4:
        if canonical_name.lower() in all_text:
            signals.append("canonical_name_in_website")

    # Industry context overlap
    if article_industry_context:
        art_words = set(re.findall(r"\b\w{4,}\b", article_industry_context.lower()))
        web_words = set(re.findall(r"\b\w{4,}\b", all_text))
        overlap = art_words & web_words
        if len(overlap) >= 2:
            signals.append(f"industry_context_in_website({len(overlap)} words)")

    if not signals:
        return 0.0, ""

    score = min(0.10, 0.04 * len(signals))
    reason = "website_verification: " + ", ".join(signals)
    return score, reason


# ---------------------------------------------------------------------------
# LLM evaluation
# ---------------------------------------------------------------------------

def _llm_evaluate_candidates(
    source_company_name: str,
    canonical_name: str,
    article_title: str,
    article_lead: str,
    article_body_excerpt: str,
    article_industry_context: str,
    candidates_with_scores: list[dict],
) -> dict | None:
    """
    Używa LLM do oceny kandydatów organizacyjnych.
    System zbiera dowody i pakiet porównawczy → LLM ocenia, nie zgaduje.

    Returns:
        Dict z kluczami: best_candidate_index (int), rationale (str), confidence_adjustment (float -0.2..+0.2)
        lub None jeśli LLM niedostępny.
    """
    try:
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        src_dir = os.path.join(_root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from llm_client import generate_json, is_llm_available
        if not is_llm_available():
            return None
    except ImportError:
        return None

    # Ogranicz ilość kandydatów przekazywanych do LLM
    top_candidates = candidates_with_scores[:5]

    candidates_text = ""
    for i, c in enumerate(top_candidates):
        candidates_text += (
            f"\nKandydat {i+1}:\n"
            f"  Nazwa: {c.get('apollo_org_name', '')}\n"
            f"  Domena: {c.get('apollo_domain', '')}\n"
            f"  Branża (Apollo): {c.get('apollo_industry', '')}\n"
            f"  Słowa kluczowe: {c.get('apollo_keywords', '')}\n"
            f"  Wynik heurystyczny: {c.get('heuristic_score', 0.0):.2f}\n"
            f"  Sygnały: {', '.join(c.get('signals', []))}\n"
        )

    prompt = f"""Jesteś ekspertem dopasowywania firm. Twoim zadaniem jest ocenić, który z poniższych kandydatów organizacyjnych (z bazy Apollo) najlepiej odpowiada firmie wspomnianej w artykule.

FIRMA Z ARTYKUŁU:
  Nazwa z artykułu: {source_company_name}
  Preferowana forma: {canonical_name}
  Kontekst branżowy: {article_industry_context}

ARTYKUŁ:
  Tytuł: {article_title}
  Lead: {article_lead[:300]}
  Fragment: {article_body_excerpt[:500]}

KANDYDACI Z APOLLO:{candidates_text}

ZADANIE:
Oceń, który kandydat (jeśli którykolwiek) odpowiada firmie z artykułu.
Bierz pod uwagę:
- zgodność nazwy (comparison key, warianty nazw)
- domenę firmy
- branżę / słowa kluczowe Apollo vs kontekst artykułu
- ogólny sens biznesowy

Odpowiedz w JSON (nic poza JSON):
{{
  "best_candidate_index": <numer kandydata 1-N lub 0 jeśli żaden nie pasuje>,
  "confidence_adjustment": <liczba od -0.20 do +0.20 — korekta confidence względem heurystyki>,
  "rationale": "<max 2 zdania uzasadnienia wyboru lub braku wyboru>"
}}

Jeśli nie jesteś pewny — lepiej ustaw confidence_adjustment ujemny lub zerowy."""

    result = None
    try:
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
            _future = _pool.submit(
                generate_json,
                prompt=prompt,
                system_prompt="Jesteś ekspertem dopasowywania firm. Odpowiadasz WYŁĄCZNIE w JSON.",
                temperature=0.15,
                max_tokens=400,
            )
            try:
                result = _future.result(timeout=45)
            except _cf.TimeoutError:
                log.warning("[Resolver] LLM evaluation timed out after 45s — skipping LLM step")
                return None
    except Exception as exc:
        log.warning("[Resolver] LLM evaluation error: %s", exc)
        return None

    if not result:
        return None

    # Walidacja
    idx = result.get("best_candidate_index")
    if not isinstance(idx, int) or idx < 0 or idx > len(top_candidates):
        return None

    adj = result.get("confidence_adjustment", 0.0)
    if not isinstance(adj, (int, float)):
        adj = 0.0
    adj = max(-0.20, min(0.20, float(adj)))

    return {
        "best_candidate_index": idx,
        "confidence_adjustment": adj,
        "rationale": str(result.get("rationale", ""))[:500],
    }


# ---------------------------------------------------------------------------
# Główna funkcja resolution
# ---------------------------------------------------------------------------

def resolve_company(
    source_company_name: str,
    canonical_name: str,
    comparison_key: str,
    article_title: str,
    article_lead: str,
    article_body_excerpt: str,
    article_industry_context: str,
    article_purchase_context: str,
    campaign_config: dict,
    associated_companies: list[str] | None = None,
) -> ResolutionResult:
    """
    Główna funkcja warstwy Company Resolution.

    Kroki:
    1. Zbierz kandydatów z Apollo (search_organizations)
    2. Ocen każdego heurystycznie (comparison_key, similarity, domain, industry)
    3. Opcjonalne: weryfikacja strony www
    4. LLM ocenia pakiet kandydatów z dowodami
    5. Decyzja: MATCH_CONFIDENT / MATCH_POSSIBLE / AMBIGUOUS_HOLD / NO_MATCH

    Returns:
        ResolutionResult
    """
    confident_threshold = campaign_config.get("company_resolution_confident_threshold", 0.72)
    min_confidence = campaign_config.get("company_resolution_min_confidence", 0.45)
    use_website_check = campaign_config.get("company_resolution_use_website_check", False)

    # --- Alias dictionary lookup (pre-search enrichment) ---
    alias_entries = _load_alias_dict(campaign_config.get("company_resolution_alias_dict", ""))
    alias_hints = _apply_alias_lookup(source_company_name, canonical_name, alias_entries)

    if alias_hints.get("canonical_name_override"):
        canonical_name = alias_hints["canonical_name_override"]
        comparison_key = _get_comparison_key(canonical_name)

    extra_queries = alias_hints.get("extra_queries", [])
    domain_hint = alias_hints.get("domain_hint", "")

    # --- Krok 1: Zbierz kandydatów ---
    raw_candidates = _collect_candidates(
        source_company_name=source_company_name,
        canonical_name=canonical_name,
        comparison_key=comparison_key,
        max_per_query=8,
        extra_queries=extra_queries if extra_queries else None,
    )

    if not raw_candidates:
        log.info("[Resolver] No Apollo candidates found for: '%s'", canonical_name)
        return _make_no_match_result(f"No Apollo organizations found for: '{canonical_name}'")

    # --- Krok 2: Score heurystycznie każdego kandydata ---
    scored: list[dict] = []
    for org in raw_candidates:
        org_name = org.get("name") or ""
        org_id = org.get("id") or None
        org_domain = org.get("primary_domain") or org.get("website_url") or ""
        if org_domain.startswith("http"):
            from urllib.parse import urlparse
            org_domain = urlparse(org_domain).netloc or org_domain
        # Jeśli org nie ma domeny w Apollo, a alias dict podał domain_hint, użyj go
        if not org_domain and domain_hint:
            org_domain = domain_hint
        org_industry = org.get("industry") or ""
        kw_list = org.get("keywords") or []
        org_keywords = ", ".join(kw_list[:10]) if kw_list else ""

        # Przekaż org z domain_hint żeby heurystyka miała dostęp do domeny
        org_for_scoring = dict(org)
        if not org_for_scoring.get("primary_domain") and domain_hint:
            org_for_scoring["primary_domain"] = domain_hint

        h_score, h_signals = _score_candidate_heuristic(
            org=org_for_scoring,
            source_company_name=source_company_name,
            canonical_name=canonical_name,
            comparison_key=comparison_key,
            article_industry_context=article_industry_context,
        )

        # Opcjonalne: weryfikacja strony www
        website_bonus = 0.0
        website_reason = ""
        if use_website_check and org_domain and h_score >= 0.25:
            web_data = _fetch_website_signals(org_domain)
            website_bonus, website_reason = _website_signal_score(
                website_data=web_data,
                canonical_name=canonical_name,
                comparison_key=comparison_key,
                article_industry_context=article_industry_context,
            )
            if website_reason:
                h_signals.append(website_reason)

        total_heuristic = min(h_score + website_bonus, 1.0)

        scored.append({
            "apollo_org_name": org_name,
            "apollo_org_id": org_id,
            "apollo_domain": org_domain,
            "apollo_industry": org_industry,
            "apollo_keywords": org_keywords,
            "heuristic_score": total_heuristic,
            "signals": h_signals,
            "final_score": total_heuristic,  # aktualizowane po LLM
            "llm_rationale": "",
        })

    # Sort by heuristic score descending
    scored.sort(key=lambda c: c["heuristic_score"], reverse=True)

    log.info("[Resolver] Top candidates for '%s': %s",
             canonical_name,
             [(c["apollo_org_name"], f"{c['heuristic_score']:.2f}") for c in scored[:3]])

    # --- Krok 3: LLM evaluation ---
    llm_result = _llm_evaluate_candidates(
        source_company_name=source_company_name,
        canonical_name=canonical_name,
        article_title=article_title,
        article_lead=article_lead,
        article_body_excerpt=article_body_excerpt,
        article_industry_context=article_industry_context,
        candidates_with_scores=scored,
    )

    llm_preferred_index = None  # 0-based index do scored[]
    llm_rationale = ""
    llm_adjustment = 0.0

    if llm_result:
        idx_1based = llm_result["best_candidate_index"]
        llm_adjustment = llm_result["confidence_adjustment"]
        llm_rationale = llm_result["rationale"]
        if idx_1based > 0:
            llm_preferred_index = idx_1based - 1  # convert to 0-based

    # --- Krok 4: Finalna decyzja ---
    best = scored[0]
    best_score = best["heuristic_score"]

    # Jeśli LLM wybrał innego kandydata niż top heurystyczny — zweryfikuj
    if llm_preferred_index is not None and llm_preferred_index != 0:
        llm_pick = scored[llm_preferred_index]
        llm_score = llm_pick["heuristic_score"] + llm_adjustment
        # Akceptuj LLM wybór tylko jeśli jego wynik jest zbliżony do topu (nie drastycznie gorszy)
        if llm_score >= best_score * 0.70:
            best = llm_pick
            best_score = llm_pick["heuristic_score"]
            log.info("[Resolver] LLM overrode heuristic top choice → '%s'", best["apollo_org_name"])

    # Zastosuj korektę LLM do finalnego score
    if llm_preferred_index is not None and best == scored[0] or (
        llm_preferred_index is not None and scored[llm_preferred_index] == best
    ):
        best_score = min(1.0, max(0.0, best_score + llm_adjustment))

    best["final_score"] = best_score
    if llm_rationale:
        best["llm_rationale"] = llm_rationale

    # Sprawdź czy wynik jest dwuznaczny (drugi kandydat też wysoki)
    is_ambiguous = False
    if len(scored) >= 2:
        second_score = scored[1]["heuristic_score"]
        # Ambiguous jeśli różnica między top a drugim jest mała i obaj powyżej min_confidence
        if (
            second_score >= min_confidence
            and best_score - second_score < 0.15
            and best_score < confident_threshold
        ):
            is_ambiguous = True

    # Candidate summary (do zwrócenia w wyniku)
    candidate_summary = [
        {
            "rank": i + 1,
            "name": c["apollo_org_name"],
            "domain": c["apollo_domain"],
            "industry": c["apollo_industry"],
            "heuristic_score": round(c["heuristic_score"], 3),
            "final_score": round(c.get("final_score", c["heuristic_score"]), 3),
            "signals": c["signals"],
            "llm_rationale": c.get("llm_rationale", ""),
        }
        for i, c in enumerate(scored[:5])
    ]

    # Finalne statusy
    if is_ambiguous:
        reason = (
            f"Ambiguous: top='{scored[0]['apollo_org_name']}'({scored[0]['heuristic_score']:.2f}) "
            f"vs second='{scored[1]['apollo_org_name']}'({scored[1]['heuristic_score']:.2f}). "
            f"Manual review required."
        )
        return _make_ambiguous_result(candidate_summary, reason)

    if best_score >= confident_threshold:
        status = STATUS_CONFIDENT
        requires_review = False
    elif best_score >= min_confidence:
        status = STATUS_POSSIBLE
        requires_review = False
    else:
        # Score poniżej min_confidence — treat as no match
        reason = (
            f"Best candidate '{best['apollo_org_name']}' score {best_score:.2f} "
            f"below min_confidence={min_confidence:.2f}"
        )
        return _make_no_match_result(reason)

    signals_str = "; ".join(best["signals"]) if best["signals"] else "no strong signals"
    reason_parts = [
        f"Best match: '{best['apollo_org_name']}' (score={best_score:.2f}, status={status})",
        f"Signals: {signals_str}",
    ]
    if best.get("llm_rationale"):
        reason_parts.append(f"LLM: {best['llm_rationale']}")

    return ResolutionResult(
        resolved_company_name=best["apollo_org_name"],
        resolved_company_id=best["apollo_org_id"],
        resolved_domain=best["apollo_domain"] or None,
        resolution_confidence=round(best_score, 3),
        resolution_status=status,
        resolution_reason=" | ".join(reason_parts),
        candidate_summary=candidate_summary,
        requires_manual_review=requires_review,
    )
