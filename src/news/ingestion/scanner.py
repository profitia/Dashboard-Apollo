"""
News Scanner — pobiera linki artykułów ze skonfigurowanych serwisów.

Obsługuje:
- article_index (strona z listą artykułów)
- tag_page (strona tagu)
- search results (przyszłość)

Zwraca: lista {"url": str, "source_id": str, "discovered_at": ISO8601}
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

log = logging.getLogger(__name__)


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


def _fetch_html(url: str, options: dict) -> str | None:
    requests = _get_requests()
    headers = _build_headers(options.get("user_agent", "Mozilla/5.0"))
    delay_ms = options.get("request_delay_ms", 1000)
    timeout_s = options.get("timeout_s", 15)
    follow = options.get("follow_redirects", True)
    try:
        resp = requests.get(url, headers=headers, timeout=timeout_s, allow_redirects=follow)
        resp.raise_for_status()
        time.sleep(delay_ms / 1000)
        return resp.text
    except Exception as exc:
        log.warning("Fetch failed for %s: %s", url, exc)
        return None


def _extract_article_links(html: str, base_url: str, selectors: dict) -> list[str]:
    BeautifulSoup = _get_bs4()
    soup = BeautifulSoup(html, "html.parser")
    link_sel = selectors.get("article_link", "a[href]")
    links = set()
    for a in soup.select(link_sel):
        href = a.get("href", "")
        if not href:
            continue
        # Resolve relative
        full_url = urljoin(base_url, href)
        # Keep only same-domain article URLs
        parsed = urlparse(full_url)
        base_parsed = urlparse(base_url)
        if parsed.netloc == base_parsed.netloc and parsed.scheme in ("http", "https"):
            # Filter obvious non-article paths
            path = parsed.path.lower()
            if any(skip in path for skip in ["/kontakt", "/regulamin", "/polityka", "/reklama", "/login", "/rejestracja"]):
                continue
            links.add(full_url)
    return list(links)


def scan_source(source_config: dict) -> list[dict]:
    """
    Skanuje jeden serwis i zwraca listę linków artykułów.

    Args:
        source_config: jeden wpis z sources.yaml

    Returns:
        Lista {"url", "source_id", "source_label", "discovered_at"}
    """
    if not source_config.get("enabled", True):
        log.info("Source %s disabled — skipping", source_config.get("id"))
        return []

    source_id = source_config["id"]
    source_label = source_config.get("label", source_id)
    base_url = source_config["base_url"]
    scan_urls = source_config.get("scan_urls", [])
    list_selectors = source_config.get("article_list_selectors", {})
    scrape_options = source_config.get("scrape_options", {})
    max_articles = scrape_options.get("max_articles_per_scan", 50)

    discovered: dict[str, dict] = {}

    for scan_entry in scan_urls:
        url = scan_entry.get("url") if isinstance(scan_entry, dict) else scan_entry
        label = scan_entry.get("label", url) if isinstance(scan_entry, dict) else url
        log.info("[%s] Scanning: %s", source_id, url)

        html = _fetch_html(url, scrape_options)
        if not html:
            continue

        links = _extract_article_links(html, base_url, list_selectors)
        log.info("[%s] Found %d article links at %s", source_id, len(links), label)

        now_iso = datetime.now(timezone.utc).isoformat()
        for link in links:
            if link not in discovered:
                discovered[link] = {
                    "url": link,
                    "url_hash": hashlib.sha256(link.encode()).hexdigest()[:16],
                    "source_id": source_id,
                    "source_label": source_label,
                    "discovered_at": now_iso,
                }

        if len(discovered) >= max_articles:
            log.info("[%s] Reached max_articles_per_scan (%d) — stopping scan", source_id, max_articles)
            break

    return list(discovered.values())[:max_articles]


def scan_all_sources(sources_config: list[dict]) -> list[dict]:
    """
    Skanuje wszystkie aktywne serwisy.

    Returns:
        Zdeduplikowana lista odkrytych artykułów.
    """
    all_articles: dict[str, dict] = {}
    for source in sources_config:
        articles = scan_source(source)
        for art in articles:
            url = art["url"]
            if url not in all_articles:
                all_articles[url] = art
    log.info("Total unique article URLs discovered: %d", len(all_articles))
    return list(all_articles.values())
