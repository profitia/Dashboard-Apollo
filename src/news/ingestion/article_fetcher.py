"""
Article Fetcher — pobiera i parsuje treść artykułu.

Tryby:
  public          — treść publicznie dostępna
  partial_content — parsuj to co dostępne (paywall)
  logged_in       — użyj sesji z logowaniem (przyszłość)

Zwraca ArticleContent (dataclass).
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger(__name__)


@dataclass
class ArticleContent:
    url: str
    canonical_url: str
    source_id: str
    title: str = ""
    lead: str = ""
    body: str = ""
    body_truncated: bool = False   # True jeśli paywall uciął treść
    tags: list[str] = field(default_factory=list)
    published_at: str | None = None  # ISO8601
    author: str = ""
    companies_mentioned_raw: list[str] = field(default_factory=list)
    article_hash: str = ""
    fetch_mode: str = "public"
    fetch_error: str | None = None
    fetched_at: str = ""

    @property
    def full_text(self) -> str:
        """Łączy tytuł + lead + body do scoringu."""
        parts = [self.title, self.lead, self.body]
        return " ".join(p for p in parts if p).lower()

    @property
    def is_usable(self) -> bool:
        """True jeśli artykuł ma wystarczająco treści do kwalifikacji."""
        return bool(self.title and (self.lead or len(self.body) > 100))


def _get_requests():
    import requests
    return requests


def _get_bs4():
    from bs4 import BeautifulSoup
    return BeautifulSoup


def _build_headers(user_agent: str) -> dict:
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    }


def _extract_date(soup, selectors: dict) -> str | None:
    """Wyodrębnia datę publikacji z meta lub elementów HTML."""
    # Meta OG/Article
    for meta_name in ["article:published_time", "og:published_time", "datePublished"]:
        m = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
        if m and m.get("content"):
            return m.get("content")

    # time[datetime]
    t = soup.find("time")
    if t and t.get("datetime"):
        return t.get("datetime")

    # CSS selector fallback
    date_sel = selectors.get("date", "")
    if date_sel:
        el = soup.select_one(date_sel)
        if el:
            return el.get("datetime") or el.get_text(strip=True)

    return None


def _detect_paywall(html: str, soup, paywall_indicators: list[str]) -> bool:
    for indicator in paywall_indicators:
        if indicator.startswith(".") or indicator.startswith("#"):
            if soup.select_one(indicator):
                return True
        elif indicator.lower() in html.lower():
            return True
    return False


def _extract_canonical(soup, current_url: str) -> str:
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return link["href"]
    return current_url


def _extract_companies_raw(text: str) -> list[str]:
    """
    Heurystyczna ekstrakcja nazw firm z tekstu.
    Szuka słów/fraz zaczynających się wielką literą po typowych prefiksach.
    Nie jest to NER — wyniki będą oczyszczone przez entity_extractor.
    """
    # Proste wzorce: Sp. z o.o., S.A., sp.j., itp.
    legal_forms = r"(?:Sp\.?\s*z\s*o\.?\s*o\.?|S\.?A\.?|sp\.?\s*j\.?|sp\.?\s*k\.?|Sp\.?\s*zoo|GmbH|Ltd\.?|Inc\.?|Corp\.?|B\.?V\.?)"
    pattern = re.compile(
        r'\b([A-ZŁŚĆŻŹĘÓĄŃ][A-Za-złśćżźęóąń\s\-]{1,40})\s+' + legal_forms,
        re.IGNORECASE
    )
    companies = set()
    for m in pattern.finditer(text):
        companies.add(m.group(0).strip())
    return list(companies)[:20]


def fetch_article(
    url: str,
    source_config: dict,
    delay_ms: int = 0,
) -> ArticleContent:
    """
    Pobiera i parsuje artykuł ze wskazanego URL.

    Args:
        url: URL artykułu
        source_config: konfiguracja serwisu (z sources.yaml)
        delay_ms: dodatkowe opóźnienie przed requestem

    Returns:
        ArticleContent
    """
    source_id = source_config.get("id", "unknown")
    selectors = source_config.get("article_selectors", {})
    scrape_options = source_config.get("scrape_options", {})
    paywall_config = source_config.get("paywall", {})
    paywall_mode = paywall_config.get("mode", "public")
    paywall_indicators = paywall_config.get("paywall_indicators", [])

    user_agent = scrape_options.get("user_agent", "Mozilla/5.0")
    timeout_s = scrape_options.get("timeout_s", 15)

    if delay_ms > 0:
        time.sleep(delay_ms / 1000)

    art = ArticleContent(
        url=url,
        canonical_url=url,
        source_id=source_id,
        fetch_mode=paywall_mode,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )

    requests = _get_requests()
    BeautifulSoup = _get_bs4()

    try:
        headers = _build_headers(user_agent)
        resp = requests.get(url, headers=headers, timeout=timeout_s, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        art.fetch_error = str(exc)
        log.warning("[%s] Fetch error for %s: %s", source_id, url, exc)
        return art

    try:
        soup = BeautifulSoup(html, "html.parser")

        art.canonical_url = _extract_canonical(soup, url)

        # Title
        title_sel = selectors.get("title", "h1")
        title_el = soup.select_one(title_sel)
        art.title = title_el.get_text(strip=True) if title_el else ""

        # Fallback: if extracted title matches the generic <title> tag (site name), try og:title
        _page_title_tag = soup.find("title")
        _page_title_text = _page_title_tag.get_text(strip=True) if _page_title_tag else ""
        if art.title and _page_title_text and art.title in _page_title_text:
            # Title looks like generic site name — prefer og:title
            og_title_el = soup.find("meta", property="og:title")
            if og_title_el and og_title_el.get("content"):
                og_title = og_title_el["content"].split(" - ")[0].split(" | ")[0].strip()
                if og_title and og_title != art.title:
                    art.title = og_title

        # Lead
        lead_sel = selectors.get("lead", ".lead, .excerpt")
        lead_el = soup.select_one(lead_sel)
        art.lead = lead_el.get_text(strip=True) if lead_el else ""

        # Body
        body_sel = selectors.get("body", "article")
        body_el = soup.select_one(body_sel)
        if body_el:
            art.body = body_el.get_text(separator=" ", strip=True)
        else:
            # Fallback: wszystkie akapity w main/article
            paragraphs = soup.select("article p, main p, .content p")
            art.body = " ".join(p.get_text(strip=True) for p in paragraphs)

        # Tags
        tags_sel = selectors.get("tags", ".tags a")
        art.tags = [t.get_text(strip=True) for t in soup.select(tags_sel) if t.get_text(strip=True)]

        # Date
        art.published_at = _extract_date(soup, selectors)

        # Paywall detection
        if paywall_mode == "partial_content":
            art.body_truncated = _detect_paywall(html, soup, paywall_indicators)

        # Companies raw
        full_text = f"{art.title} {art.lead} {art.body}"
        art.companies_mentioned_raw = _extract_companies_raw(full_text)

        # Article hash (oparty o canonical URL)
        art.article_hash = hashlib.sha256(art.canonical_url.encode()).hexdigest()[:16]

    except Exception as exc:
        art.fetch_error = f"Parse error: {exc}"
        log.exception("[%s] Parse error for %s", source_id, url)

    return art
