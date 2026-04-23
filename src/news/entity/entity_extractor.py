"""
Entity Extractor — wyodrębnia firmy z artykułu i klasyfikuje je do outreachu.

Używa LLM (gdy dostępny) do precyzyjnej ekstrakcji i klasyfikacji.
Fallback: heurystyczne wzorce + raw_companies z fetcher.

Wynik:
  - primary_company: główna firma do outreachu
  - related_companies: pozostałe firmy wzmiankowane
  - company_type: producer | retailer | distributor | tech_vendor | other
  - campaign_eligible: bool
  - extraction_reason: dlaczego ta firma
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class CompanyInfo:
    name: str
    name_normalized: str        # comparison key: lowercase, bez spacji, bez suffixu prawnego
    company_type: str           # producer | retailer | distributor | tech_vendor | other
    campaign_eligible: bool
    confidence: float           # 0.0-1.0
    reason: str
    related_companies: list[str] = field(default_factory=list)
    extraction_method: str = "llm"  # llm | heuristic | manual
    # Normalizacja nazwy firmy
    source_name: str = ""           # nazwa z artykułu / źródła
    canonical_name: str = ""        # preferowana forma (brand, strona firmowa)
    aliases: list[str] = field(default_factory=list)  # wszystkie znane warianty


def _normalize_company_name(name: str) -> str:
    """Normalizuje nazwę firmy do deduplikacji (comparison key).
    Deleguje do company_normalizer.make_comparison_key.
    """
    try:
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        src_dir = os.path.join(_root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from news.utils.company_normalizer import make_comparison_key
        return make_comparison_key(name)
    except Exception:
        # Fallback inline jeśli import nie działa
        n = name.lower().strip()
        legal = r"\b(sp\.\s*z\s*o\.?\s*o\.?|s\.?a\.?|sp\.?\s*j\.?|sp\.?\s*k\.?|gmbh|ltd\.?|inc\.?)\b"
        n = re.sub(legal, "", n, flags=re.IGNORECASE)
        n = re.sub(r"[^\w\s]", " ", n)
        n = re.sub(r"\s+", "", n).strip()
        return n


def _classify_company_heuristic(company_name: str, article_text: str) -> str:
    """Heurystyczna klasyfikacja typu firmy na podstawie treści."""
    name_lower = company_name.lower()
    text_lower = article_text.lower()

    # Sprawdź kontekst firmy w tekście
    # Znajdź fragmenty tekstu zawierające nazwę firmy
    name_idx = text_lower.find(name_lower[:min(len(name_lower), 10)])
    context = text_lower[max(0, name_idx-100):name_idx+200] if name_idx >= 0 else text_lower[:300]

    producer_signals = ["producent", "produkcja", "wytwarza", "fabryka", "zakład", "przetwórnia", "przetwarza"]
    retailer_signals = ["sieć", "sklep", "supermarket", "hipermarket", "dyskont", "retail", "detaliczny"]
    distributor_signals = ["dystrybutor", "dystrybucja", "hurt", "hurtownia", "importer", "eksporter"]
    tech_signals = ["oprogramowanie", "system", "platforma", "technologia", "software", "it"]

    scores = {
        "producer": sum(1 for s in producer_signals if s in context),
        "retailer": sum(1 for s in retailer_signals if s in context),
        "distributor": sum(1 for s in distributor_signals if s in context),
        "tech_vendor": sum(1 for s in tech_signals if s in context),
    }

    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "other"


def _extract_companies_llm(
    title: str,
    lead: str,
    body: str,
    raw_companies: list[str],
    campaign_config: dict,
) -> CompanyInfo | None:
    """Używa LLM do ekstrakcji i klasyfikacji firmy."""
    try:
        # Lazy import LLM klienta
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        src_dir = os.path.join(_root, "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from llm_client import generate_json, is_llm_available
        if not is_llm_available():
            return None
    except ImportError:
        return None

    # Truncate body dla LLM
    body_excerpt = body[:2000] if body else ""

    excluded = campaign_config.get("excluded_companies", [])
    excluded_str = ", ".join(excluded) if excluded else "brak"

    prompt = f"""Jesteś ekspertem w analizie artykułów branżowych z rynku B2B, FMCG i produkcji żywności.

Artykuł:
TYTUŁ: {title}
LEAD: {lead}
TREŚĆ (fragment): {body_excerpt}

Wstępnie rozpoznane firmy (heurystyka): {', '.join(raw_companies) if raw_companies else 'brak'}

ZADANIE: Zidentyfikuj GŁÓWNĄ firmę, która powinna być celem kampanii outreachowej SpendGuru (narzędzie do negocjacji zakupowych z dostawcami).

SpendGuru jest adresowany do:
- producenci żywności i FMCG (★★★)
- sieci handlowe i retail (★★)
- duże firmy produkcyjne (★★)
- dystrybutorzy (★)

Firmy WYKLUCZONE z outreachu: {excluded_str}

ZASADA NAZEWNICTWA (krytyczna):
W polu "name" podaj KRÓTKĄ NAZWĘ BRANDOWĄ firmy (taką, jak używa jej rynek i media), NIE pełną nazwę prawną.
- Poprawnie: "Evra Fish" (nie: "Evra Fish Sp. z o.o.")
- Poprawnie: "ORLEN" lub "PKN ORLEN" (nie: "ORLEN S.A." ani "PKN ORLEN S.A.")
- Poprawnie: "Grycan" (nie: "Grycan - Lody od pokoleń Sp. z o.o.")
- Ogólnie: usuń formy prawne (Sp. z o.o., S.A., sp.j., Ltd., GmbH itp.) z nazwy, chyba że są integralną częścią brandu.

Odpowiedz w JSON (nic poza JSON):
{{
  "primary_company": {{
    "name": "KRÓTKA NAZWA BRANDOWA FIRMY (bez formy prawnej)",
    "company_type": "producer|retailer|distributor|tech_vendor|other",
    "campaign_eligible": true/false,
    "eligibility_reason": "krótkie uzasadnienie (max 2 zdania)",
    "confidence": 0.0-1.0
  }},
  "related_companies": ["Firma A", "Firma B"],
  "article_summary": "1-2 zdania o czym jest artykuł",
  "outreach_trigger": "1 zdanie: jaki jest biznesowy trigger dla outreachu SpendGuru"
}}

Jeśli artykuł nie dotyczy żadnej firmy wartej outreachu, ustaw campaign_eligible: false."""

    result = generate_json(
        prompt=prompt,
        system_prompt="Jesteś ekspertem w analizie firm B2B. Odpowiadasz WYŁĄCZNIE w JSON, bez komentarzy.",
        temperature=0.2,
        max_tokens=800,
    )

    if not result or "primary_company" not in result:
        return None

    pc = result["primary_company"]
    name = pc.get("name", "").strip()
    if not name:
        return None

    related = result.get("related_companies", [])

    return CompanyInfo(
        name=name,
        name_normalized=_normalize_company_name(name),
        company_type=pc.get("company_type", "other"),
        campaign_eligible=pc.get("campaign_eligible", False),
        confidence=float(pc.get("confidence", 0.5)),
        reason=pc.get("eligibility_reason", ""),
        related_companies=[r for r in related if r != name],
        extraction_method="llm",
        source_name=name,
        canonical_name=name,
        aliases=[name],
    )


def _extract_companies_heuristic(
    title: str,
    lead: str,
    body: str,
    raw_companies: list[str],
    campaign_config: dict,
) -> CompanyInfo | None:
    """Heurystyczna ekstrakcja — fallback gdy LLM niedostępny."""
    if not raw_companies:
        # Brak rozpoznanych firm
        return None

    full_text = f"{title} {lead} {body}"
    excluded = [c.lower() for c in campaign_config.get("excluded_companies", [])]

    # Wybierz pierwszą pasującą firmę (wyłącz wykluczone)
    candidates = [c for c in raw_companies if _normalize_company_name(c) not in excluded]
    if not candidates:
        return None

    # Wybierz tę, która pojawia się najczęściej w tekście
    def count_mentions(company: str) -> int:
        term = company.lower()[:min(len(company), 15)]
        return full_text.lower().count(term)

    candidates.sort(key=count_mentions, reverse=True)
    primary = candidates[0]
    related = candidates[1:5]

    company_type = _classify_company_heuristic(primary, full_text)
    eligible = company_type in ("producer", "retailer", "distributor")

    return CompanyInfo(
        name=primary,
        name_normalized=_normalize_company_name(primary),
        company_type=company_type,
        campaign_eligible=eligible,
        confidence=0.4,
        reason=f"Heuristic: most mentioned company in article (type: {company_type})",
        related_companies=related,
        extraction_method="heuristic",
        source_name=primary,
        canonical_name=primary,
        aliases=[primary],
    )


def extract_primary_company(
    title: str,
    lead: str,
    body: str,
    raw_companies: list[str],
    campaign_config: dict,
) -> CompanyInfo | None:
    """
    Wyodrębnia główną firmę z artykułu.
    Najpierw próbuje LLM, fallback do heurystyki.

    Returns:
        CompanyInfo lub None jeśli artykuł nie ma kandydatów
    """
    # LLM first
    result = _extract_companies_llm(title, lead, body, raw_companies, campaign_config)
    if result:
        log.info("Company extracted via LLM: %s (type=%s, eligible=%s)",
                 result.name, result.company_type, result.campaign_eligible)
        return result

    # Fallback
    result = _extract_companies_heuristic(title, lead, body, raw_companies, campaign_config)
    if result:
        log.info("Company extracted via heuristic: %s (type=%s, eligible=%s)",
                 result.name, result.company_type, result.campaign_eligible)
    else:
        log.info("No company could be extracted from article: %s", title[:60])

    return result
