"""
News Campaign Orchestrator — główny punkt wejścia do pipelinu.

Tryby uruchomienia:
  scan            — skanuj serwisy, zapisz kandydatów artykułów
  qualify         — oceń artykuły i wybierz relewantne
  build-sequence  — dla artykułu/firmy: kontakty + treści + sekwencja Apollo
  run-daily       — pełny workflow dzienny end-to-end
  
Flagi:
  --dry-run            — nie pisz do Apollo
  --no-apollo-write    — aliased --dry-run
  --review-only        — generuj tylko treści, nie twórz sekwencji
  --single-article-url — uruchom dla jednego URL artykułu
  --campaign            — ID kampanii (domyślnie: spendguru_market_news)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Dodaj src/ do path
_DIR = os.path.dirname(os.path.abspath(__file__))  # src/news/
_SRC_DIR = os.path.dirname(os.path.dirname(_DIR))  # workspace root (Kampanie Apollo/)
_ROOT_DIR = _SRC_DIR                               # alias: workspace root used for file paths

for p in [os.path.dirname(_DIR), _SRC_DIR]:        # src/ and workspace root
    if p not in sys.path:
        sys.path.insert(0, p)

from news.pipeline_status import PipelineStatus
from news.reporting.run_report import build_and_save_run_report

try:
    import yaml
except ImportError:
    print("BŁĄD: PyYAML nie jest zainstalowany. Uruchom: pip install pyyaml")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT_DIR, "Integracje", ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("news.orchestrator")


def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _campaign_dir(campaign_id: str) -> str:
    return os.path.join(_ROOT_DIR, "campaigns", "news", campaign_id)


def _load_campaign_configs(campaign_id: str) -> tuple[dict, dict, dict]:
    """Ładuje campaign_config, sources, keywords."""
    cdir = _campaign_dir(campaign_id)
    campaign_config = _load_yaml(os.path.join(cdir, "config", "campaign_config.yaml"))
    sources_config = _load_yaml(os.path.join(cdir, "config", "sources.yaml"))
    keywords_config = _load_yaml(os.path.join(cdir, "config", "keywords.yaml"))
    tier_mapping = _load_yaml(os.path.join(cdir, "config", "tier_mapping.yaml"))
    return campaign_config, sources_config, keywords_config, tier_mapping


# ============================================================
# MODE: SCAN
# ============================================================
def run_scan(campaign_id: str, **kwargs) -> list[dict]:
    """Skanuje serwisy i zapisuje kandydatów artykułów."""
    from news.ingestion.scanner import scan_all_sources

    campaign_config, sources_config, _, _ = _load_campaign_configs(campaign_id)
    sources = sources_config.get("sources", [])
    log.info("[SCAN] Starting scan for campaign: %s (%d sources)", campaign_id, len(sources))

    articles = scan_all_sources(sources)
    log.info("[SCAN] Done. %d article URLs discovered.", len(articles))

    # Zapisz do pliku kandydatów
    out_dir = os.path.join(_ROOT_DIR, "outputs", "news", campaign_id)
    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(out_dir, f"{timestamp}_scan_candidates.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    log.info("[SCAN] Saved %d candidates to %s", len(articles), out_file)
    return articles


# ============================================================
# MODE: QUALIFY
# ============================================================
def run_qualify(
    campaign_id: str,
    candidates: list[dict] | None = None,
    single_url: str | None = None,
    **kwargs,
) -> list[dict]:
    """Pobiera artykuły, ocenia relewantność i zwraca listę zakwalifikowanych."""
    from news.ingestion.article_fetcher import fetch_article
    from news.relevance.scorer import score_article
    from news.state.state_manager import ArticleStateManager

    campaign_config, sources_config, keywords_config, _ = _load_campaign_configs(campaign_id)
    sources_by_id = {s["id"]: s for s in sources_config.get("sources", [])}
    lookback_days = campaign_config.get("lookback_days", 5)

    # State manager
    state_file = os.path.join(_ROOT_DIR, campaign_config.get("state_file", "data/processed_articles.json"))
    sequences_file = os.path.join(_ROOT_DIR, campaign_config.get("sequences_log_file", "data/sequences_created.json"))
    state = ArticleStateManager(state_file, sequences_file)

    # Prepare candidates list
    if single_url:
        source_id = next(
            (s["id"] for s in sources_config.get("sources", []) if single_url.startswith(s["base_url"])),
            "wiadomosci_handlowe"
        )
        candidates = [{"url": single_url, "source_id": source_id, "source_label": source_id, "discovered_at": datetime.now(timezone.utc).isoformat()}]
    elif not candidates:
        # Załaduj ostatni plik kandidatów
        out_dir = os.path.join(_ROOT_DIR, "outputs", "news", campaign_id)
        import glob
        files = sorted(glob.glob(os.path.join(out_dir, "*_scan_candidates.json")), reverse=True)
        if files:
            with open(files[0], encoding="utf-8") as f:
                candidates = json.load(f)
            log.info("[QUALIFY] Loaded %d candidates from %s", len(candidates), files[0])
        else:
            log.warning("[QUALIFY] No candidates file found. Run scan first.")
            return []

    qualified = []
    scrape_options = {"request_delay_ms": 1500, "timeout_s": 15, "user_agent": "Mozilla/5.0"}

    for i, candidate in enumerate(candidates):
        url = candidate["url"]
        source_id = candidate.get("source_id", "unknown")

        # Sprawdź dedup
        if state.is_article_processed(url):
            log.debug("[QUALIFY] Already processed: %s", url)
            continue

        # Pobierz artykuł
        source_config = sources_by_id.get(source_id, {"id": source_id, "scrape_options": scrape_options, "article_selectors": {}, "paywall": {"mode": "partial_content", "paywall_indicators": []}})
        log.info("[QUALIFY] %d/%d Fetching: %s", i + 1, len(candidates), url[:80])
        article = fetch_article(url, source_config)

        if article.fetch_error or not article.is_usable:
            log.debug("[QUALIFY] Unusable: %s (error: %s)", url, article.fetch_error)
            state.mark_article(url, article.article_hash, PipelineStatus.SKIPPED_FETCH_FAILED, {
                "error": article.fetch_error,
                "final_stage": "fetch",
                "final_reason": article.fetch_error or "Article unusable",
            })
            continue

        # Score
        score_result = score_article(
            full_text=article.full_text,
            tags=article.tags,
            title=article.title,
            published_at=article.published_at,
            keywords_config=keywords_config,
            campaign_config=campaign_config,
        )

        if not score_result.qualified:
            log.info("[QUALIFY] NOT qualified (score=%.0f): %s — %s",
                     score_result.total_score, url[:60], score_result.disqualification_reason)
            state.mark_article(url, article.article_hash, PipelineStatus.REJECTED_QUALIFICATION, {
                "score": score_result.total_score,
                "reason": score_result.disqualification_reason,
                "final_stage": "qualification",
                "final_reason": score_result.disqualification_reason,
            })
            continue

        log.info("[QUALIFY] QUALIFIED (score=%.0f, industry=%.0f, purchase=%.0f): %s",
                 score_result.total_score, score_result.industry_score,
                 score_result.purchase_signal_score, article.title[:60])

        qualified.append({
            "article": article,
            "score_result": score_result,
            "candidate": candidate,
        })

    log.info("[QUALIFY] Qualified: %d / %d candidates", len(qualified), len(candidates))
    return qualified


# ============================================================
# MODE: BUILD-SEQUENCE
# ============================================================
def run_build_sequence(
    campaign_id: str,
    qualified_articles: list[dict] | None = None,
    single_url: str | None = None,
    dry_run: bool = False,
    review_only: bool = False,
    **kwargs,
) -> list[dict]:
    """Dla każdego zakwalifikowanego artykułu: kontakty + treści + sekwencja Apollo."""
    from news.entity.entity_extractor import extract_primary_company
    from news.entity.company_resolver import resolve_company, STATUS_NO_MATCH, STATUS_AMBIGUOUS
    from news.contacts.contact_finder import (
        find_contacts_for_company, find_contacts_with_fallbacks,
        validate_contact_found, select_best_contacts,
    )
    from news.messaging.message_generator import generate_outreach_pack
    from news.apollo.sequence_builder import build_sequence_name, create_news_sequence, send_blocked_no_email_notification
    from news.state.state_manager import ArticleStateManager
    from news.notifications.notifier import notify

    campaign_config, _, _, tier_mapping = _load_campaign_configs(campaign_id)
    cdir = _campaign_dir(campaign_id)
    dedup_window = campaign_config.get("dedup_window_days", 30)

    state_file = os.path.join(_ROOT_DIR, campaign_config.get("state_file", "data/processed_articles.json"))
    sequences_file = os.path.join(_ROOT_DIR, campaign_config.get("sequences_log_file", "data/sequences_created.json"))
    state = ArticleStateManager(state_file, sequences_file)

    if single_url:
        qualified_articles = run_qualify(campaign_id, single_url=single_url)

    if not qualified_articles:
        log.warning("[BUILD] No qualified articles to process.")
        return []

    results = []

    for item in qualified_articles:
        article = item["article"]
        score_result = item["score_result"]
        log.info("[BUILD] Processing: %s", article.title[:70])

        # --- Ekstrakcja firmy ---
        company = extract_primary_company(
            title=article.title,
            lead=article.lead,
            body=article.body,
            raw_companies=article.companies_mentioned_raw,
            campaign_config=campaign_config,
        )

        if not company:
            log.warning("[BUILD] No company extracted: %s", article.url)
            state.mark_article(article.url, article.article_hash, PipelineStatus.BLOCKED_COMPANY_NOT_FOUND, {
                "final_stage": "entity_extraction",
                "final_reason": "No company extracted from article",
            })
            results.append({"url": article.url, "status": PipelineStatus.BLOCKED_COMPANY_NOT_FOUND})
            continue

        if not company.campaign_eligible:
            log.info("[BUILD] Company not eligible for outreach: %s (%s)",
                     company.name, company.company_type)
            state.mark_article(article.url, article.article_hash, PipelineStatus.BLOCKED_COMPANY_EXCLUDED, {
                "company": company.name,
                "reason": company.reason,
                "final_stage": "entity_extraction",
                "final_reason": company.reason or f"Company type '{company.company_type}' excluded",
            })
            results.append({"url": article.url, "status": PipelineStatus.BLOCKED_COMPANY_EXCLUDED, "company": company.name})
            continue

        # Sprawdź cooldown firmy
        if state.is_company_in_cooldown(company.name_normalized, dedup_window):
            log.info("[BUILD] Company in cooldown: %s", company.name)
            state.mark_article(article.url, article.article_hash, PipelineStatus.SKIPPED_COOLDOWN, {
                "company": company.name,
                "final_stage": "dedup",
                "final_reason": f"Company '{company.name}' in cooldown window ({dedup_window}d)",
            })
            results.append({"url": article.url, "status": PipelineStatus.SKIPPED_COOLDOWN, "company": company.name})
            continue

        # --- Company Resolution Layer ---
        # Opcjonalna warstwa między entity_extractor a contact_finder.
        # Dopasowuje firmę z artykułu do właściwej organizacji w Apollo.
        # Toggle: use_company_resolution w campaign_config.yaml
        resolved_company_name = company.canonical_name or company.name
        resolved_domain = None
        resolution_status_logged = None

        if campaign_config.get("use_company_resolution", False):
            # Buduj kontekst branżowy dla resolvera z wyników scorera
            industry_terms = " ".join(
                term
                for terms_list in score_result.matched_industry_terms.values()
                for term in terms_list
            )
            purchase_terms = " ".join(
                term
                for terms_list in score_result.matched_purchase_terms.values()
                for term in terms_list
            )
            article_industry_ctx = f"{industry_terms} {purchase_terms}".strip() or article.lead[:200]

            try:
                resolution = resolve_company(
                    source_company_name=company.source_name or company.name,
                    canonical_name=company.canonical_name or company.name,
                    comparison_key=company.name_normalized,
                    article_title=article.title,
                    article_lead=article.lead or "",
                    article_body_excerpt=(article.body or "")[:600],
                    article_industry_context=article_industry_ctx,
                    article_purchase_context=purchase_terms,
                    campaign_config=campaign_config,
                )
                resolution_status_logged = resolution.resolution_status
                log.info(
                    "[BUILD] Resolution: status=%s confidence=%.2f name='%s' → '%s'",
                    resolution.resolution_status,
                    resolution.resolution_confidence,
                    company.name,
                    resolution.resolved_company_name or "(none)",
                )

                if resolution.resolution_status == STATUS_NO_MATCH:
                    log.info("[BUILD] Resolution NO_MATCH for '%s' — skipping. Reason: %s",
                             company.name, resolution.resolution_reason)
                    state.mark_article(article.url, article.article_hash,
                                       PipelineStatus.BLOCKED_COMPANY_NO_MATCH, {
                                           "company": company.name,
                                           "reason": resolution.resolution_reason,
                                           "final_stage": "company_resolution",
                                           "final_reason": resolution.resolution_reason,
                                       })
                    results.append({
                        "url": article.url,
                        "status": PipelineStatus.BLOCKED_COMPANY_NO_MATCH,
                        "company": company.name,
                        "resolution": resolution.resolution_reason,
                    })
                    continue

                if resolution.resolution_status == STATUS_AMBIGUOUS:
                    log.info("[BUILD] Resolution AMBIGUOUS for '%s' → manual review. Reason: %s",
                             company.name, resolution.resolution_reason)
                    state.mark_article(article.url, article.article_hash,
                                       PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS, {
                                           "company": company.name,
                                           "reason": resolution.resolution_reason,
                                           "final_stage": "company_resolution",
                                           "final_reason": resolution.resolution_reason,
                                       })
                    results.append({
                        "url": article.url,
                        "status": PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS,
                        "company": company.name,
                        "resolution": resolution.resolution_reason,
                        "requires_manual_review": True,
                    })
                    continue

                # MATCH_CONFIDENT lub MATCH_POSSIBLE — zaktualizuj resolved name
                if resolution.resolved_company_name:
                    resolved_company_name = resolution.resolved_company_name
                resolved_domain = resolution.resolved_domain

            except Exception as exc:
                # Błąd resolution layer nie blokuje pipeline'u
                log.warning("[BUILD] Resolution layer error for '%s': %s — falling back to original name",
                             company.name, exc)

        # --- Kontakty (z fallback flow) ---
        # Zbierz firmy powiązane: z entity_extractor + z resolution candidates (jeśli dostępne)
        associated_companies: list[str] = list(company.related_companies or [])
        if resolution_status_logged and campaign_config.get("use_company_resolution", False):
            try:
                # Dodaj runner-up candidates z resolution jako potencjalne firmy powiązane
                if "resolution" in dir() and resolution.candidate_summary:
                    for cand in resolution.candidate_summary[1:3]:  # max 2 runner-ups
                        cand_name = cand.get("name", "")
                        if cand_name and cand_name not in associated_companies:
                            associated_companies.append(cand_name)
            except Exception:
                pass

        search_result = find_contacts_with_fallbacks(
            company_name=resolved_company_name,
            company_domain=resolved_domain,
            tier_mapping=tier_mapping,
            campaign_config=campaign_config,
            associated_companies=associated_companies or None,
        )
        contacts = search_result.contacts

        # Log search strategy
        log.info(
            "[BUILD] Contact search: strategy=%s winning=%s name_email=%d domain_fb=%s assoc_fb=%s",
            search_result.strategy_used,
            search_result.winning_strategy,
            search_result.name_search_email_count,
            f"{search_result.domain_searched}({search_result.domain_search_email_count}e)" if search_result.domain_fallback_triggered else "off",
            f"{search_result.assoc_fallback_company}({search_result.assoc_search_email_count}e)" if search_result.assoc_fallback_triggered else "off",
        )
        for line in search_result.search_log:
            log.debug("[BUILD] %s", line)

        ok, threshold_reason = validate_contact_found(contacts)
        if not ok:
            log.info("[BUILD] No contacts found for %s: %s", company.name, threshold_reason)
            state.mark_article(article.url, article.article_hash, PipelineStatus.BLOCKED_NO_CONTACT, {
                "company": company.name,
                "reason": threshold_reason,
                "final_stage": "contact_search",
                "final_reason": "No contacts found in Apollo for this company",
            })
            results.append({
                "url": article.url,
                "status": PipelineStatus.BLOCKED_NO_CONTACT,
                "company": company.name,
                "reason": threshold_reason,
            })
            continue

        # --- Wybierz najlepsze kontakty wg tier (bez filtrowania po emailu) ---
        # Email reveal jest wykonywany dopiero w create_news_sequence (Faza 2).
        max_contacts = campaign_config.get("max_contacts_for_draft", 3)
        best_contacts = select_best_contacts(contacts, max_contacts=max_contacts)
        log.info("[BUILD] Selected %d best contact(s) for %s (from %d total)",
                 len(best_contacts), company.name, len(contacts))

        # --- Treści wiadomości dla WSZYSTKICH wybranych kontaktów ---
        # Packs nie wymagają emaila — personalizacja oparta na roli i firmie.
        # Używane zarówno dla READY (custom fields) jak i BLOCKED (notyfikacja).
        article_key_facts = score_result.explanation
        contacts_with_packs = []
        tier_breakdown = {"tier_1": 0, "tier_2": 0, "tier_3": 0, "other": 0}

        for contact in best_contacts:
            try:
                pack = generate_outreach_pack(
                    contact=contact,
                    article=article,
                    campaign_dir=cdir,
                    article_key_facts=article_key_facts,
                )
                contacts_with_packs.append({"contact": contact, "pack": pack})
                tier_key = {
                    "tier_1_c_level": "tier_1",
                    "tier_2_procurement_management": "tier_2",
                    "tier_3_buyers_operational": "tier_3",
                }.get(contact.tier, "other")
                tier_breakdown[tier_key] += 1
            except Exception as exc:
                log.warning("[BUILD] Pack generation failed for %s: %s", contact.full_name, exc)

        if not contacts_with_packs:
            log.warning("[BUILD] No outreach packs generated for %s — all failed", company.name)
            state.mark_article(article.url, article.article_hash, PipelineStatus.BLOCKED_MESSAGE_GENERATION_FAILED, {
                "company": company.name,
                "final_stage": "message_generation",
                "final_reason": "All outreach pack generation attempts failed",
            })
            results.append({"url": article.url, "status": PipelineStatus.BLOCKED_MESSAGE_GENERATION_FAILED, "company": company.name})
            continue
        # --- Human review gate ---
        if campaign_config.get("human_review_gate", False) and not review_only:
            log.info("[BUILD] Human review gate active — marking for review: %s", company.name)
            state.mark_article(article.url, article.article_hash, PipelineStatus.PENDING_MANUAL_REVIEW, {
                "company": company.name,
                "contacts_count": len(contacts_with_packs),
                "final_stage": "review_gate",
                "final_reason": "human_review_gate active in campaign config",
            })
            results.append({"url": article.url, "status": PipelineStatus.PENDING_MANUAL_REVIEW, "company": company.name})
            continue

        if review_only:
            log.info("[BUILD][REVIEW ONLY] Sequence would be created for %s (%d contacts)",
                     company.name, len(contacts_with_packs))
            results.append({
                "url": article.url, "status": PipelineStatus.REVIEW_ONLY,
                "company": company.name,
                "contacts_count": len(contacts_with_packs),
                "tier_breakdown": tier_breakdown,
            })
            continue

        # --- Sekwencja Apollo (list + reveal + custom fields + notyfikacja) ---
        sequence_name = build_sequence_name(
            article_date=article.published_at,
            company_name=company.name,
            article_title=article.title,
            campaign_config=campaign_config,
        )

        seq_result = create_news_sequence(
            sequence_name=sequence_name,
            contacts_with_packs=contacts_with_packs,
            campaign_config=campaign_config,
            dry_run=dry_run,
            article_title=article.title,
            article_url=article.canonical_url or article.url,
            company_name=company.name,
        )

        # --- Finalny status na podstawie dostępności emaila po reveal ---
        email_available = seq_result.get("email_available", False)

        if email_available:
            final_status = PipelineStatus.READY_FOR_REVIEW
            final_stage = "apollo_write"
            final_reason = "Flow complete — contact added to list, email available, sequence ready for review"
        else:
            final_status = PipelineStatus.BLOCKED_NO_EMAIL
            final_stage = "email_reveal"
            final_reason = (
                "Contacts identified and added to Apollo list — "
                "email reveal attempted but no email address available"
            )

        state.mark_article(article.url, article.article_hash, final_status, {
            "company": company.name,
            "sequence_name": sequence_name,
            "sequence_id": seq_result.get("sequence_id"),
            "final_stage": final_stage,
            "final_reason": final_reason,
            "reveal_attempted": seq_result.get("reveal_attempted", False),
            "reveal_count": seq_result.get("reveal_count", 0),
        })

        if email_available:
            state.register_sequence(
                sequence_name=sequence_name,
                sequence_id=seq_result.get("sequence_id"),
                article_url=article.url,
                article_title=article.title,
                company_name=company.name,
                company_normalized=company.name_normalized,
                contacts_count=len(contacts_with_packs),
                tier_breakdown=tier_breakdown,
            )

            # Powiadomienie (log + JSON raport) — email już wysłany w create_news_sequence
            build_meta = {
                "article_title": article.title,
                "article_url": article.canonical_url,
                "company_name": company.name,
                "tier_breakdown": tier_breakdown,
                "enrichment_status": f"{seq_result.get('contacts_synced', 0)} contacts synced",
            }
            notify(
                sequence_result=seq_result,
                build_result=build_meta,
                campaign_config=campaign_config,
                report_dir=os.path.join(_ROOT_DIR, "outputs", "news", campaign_id),
            )

        log.info("[BUILD] %s → %s (reveal=%s/%s, list=%d, email_available=%s, dry_run=%s)",
                 company.name, final_status,
                 seq_result.get("reveal_count", 0),
                 "attempted" if seq_result.get("reveal_attempted") else "skipped",
                 seq_result.get("contacts_added_to_list", 0),
                 email_available, dry_run)

        results.append({
            "url": article.url,
            "status": final_status,
            "company": company.name,
            "sequence_name": sequence_name,
            "sequence_id": seq_result.get("sequence_id"),
            "contacts_added_to_list": seq_result.get("contacts_added_to_list", 0),
            "reveal_attempted": seq_result.get("reveal_attempted", False),
            "reveal_count": seq_result.get("reveal_count", 0),
            "email_available": email_available,
            "tier_breakdown": tier_breakdown,
            "dry_run": dry_run,
        })

    # --- Zbiorczy raport runu ---
    if results:
        try:
            report_dir = os.path.join(
                _campaign_dir(campaign_id), "output"
            )
            run_mode = "single-article" if single_url else "build-sequence"
            if review_only:
                run_mode = "review-only"
            build_and_save_run_report(
                run_results=results,
                campaign_config=campaign_config,
                report_dir=report_dir,
                run_mode=run_mode,
                dry_run=dry_run,
                state_manager=state,
            )
            log.info("[REPORT] Run report saved to %s", report_dir)
        except Exception as exc:
            log.warning("[REPORT] Could not generate run report: %s", exc)

    return results


# ============================================================
# MODE: RUN-DAILY
# ============================================================
def run_daily(campaign_id: str, dry_run: bool = False, **kwargs) -> list[dict]:
    """Pełny workflow dzienny: scan → qualify → build."""
    log.info("[DAILY] Starting daily run for campaign: %s (dry_run=%s)", campaign_id, dry_run)
    candidates = run_scan(campaign_id)
    qualified = run_qualify(campaign_id, candidates=candidates)
    results = run_build_sequence(campaign_id, qualified_articles=qualified, dry_run=dry_run)
    log.info("[DAILY] Done. %d results.", len(results))
    return results


# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="SpendGuru Market News — News Campaign Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tryby:
  scan              Skanuj serwisy i zapisz kandydatów artykułów
  qualify           Oceniaj artykuły i wybierz relewantne
  build-sequence    Dla zakwalifikowanych artykułów: kontakty + treści + sekwencja Apollo
  run-daily         Pełny workflow end-to-end (scan + qualify + build)
  report            Generuj raport z ostatniego runu (z pliku stanu)

Przykłady:
  python orchestrator.py run-daily
  python orchestrator.py run-daily --dry-run
  python orchestrator.py build-sequence --single-article-url https://...
  python orchestrator.py qualify --single-article-url https://...
  python orchestrator.py scan
  python orchestrator.py report
"""
    )
    parser.add_argument("mode", choices=["scan", "qualify", "build-sequence", "run-daily", "report"],
                        help="Tryb uruchomienia")
    parser.add_argument("--campaign", default="spendguru_market_news",
                        help="ID kampanii (domyślnie: spendguru_market_news)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nie pisz do Apollo — symulacja")
    parser.add_argument("--no-apollo-write", action="store_true",
                        help="Alias dla --dry-run")
    parser.add_argument("--review-only", action="store_true",
                        help="Generuj tylko treści, nie twórz sekwencji")
    parser.add_argument("--single-article-url",
                        help="Uruchom tylko dla jednego URL artykułu")
    parser.add_argument("--verbose", action="store_true",
                        help="Tryb debug — więcej logów")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    dry_run = args.dry_run or args.no_apollo_write

    mode = args.mode
    campaign_id = args.campaign
    single_url = args.single_article_url

    if mode == "scan":
        run_scan(campaign_id)
    elif mode == "qualify":
        run_qualify(campaign_id, single_url=single_url)
    elif mode == "build-sequence":
        results = run_build_sequence(
            campaign_id,
            single_url=single_url,
            dry_run=dry_run,
            review_only=args.review_only,
        )
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    elif mode == "run-daily":
        results = run_daily(campaign_id, dry_run=dry_run)
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    elif mode == "report":
        # Generuj raport na podstawie pliku stanu (bez uruchamiania runu)
        from news.state.state_manager import ArticleStateManager
        campaign_config, _, _, _ = _load_campaign_configs(campaign_id)
        state_file = os.path.join(_ROOT_DIR, campaign_config.get("state_file", "data/processed_articles.json"))
        sequences_file = os.path.join(_ROOT_DIR, campaign_config.get("sequences_log_file", "data/sequences_created.json"))
        state = ArticleStateManager(state_file, sequences_file)
        # Build synthetic results from state
        synthetic_results = [
            {"url": art.get("url", url), "status": art.get("status", "unknown"),
             "company": art.get("company", ""), "final_stage": art.get("final_stage", ""),
             "final_reason": art.get("final_reason", ""), "article_title": art.get("article_title", "")}
            for url, art in state._articles.items()
        ]
        report_dir = os.path.join(_campaign_dir(campaign_id), "output")
        paths = build_and_save_run_report(
            run_results=synthetic_results,
            campaign_config=campaign_config,
            report_dir=report_dir,
            run_mode="report",
            dry_run=False,
            state_manager=state,
        )
        for fmt, path in paths.items():
            print(f"[REPORT] {fmt.upper()}: {path}")


if __name__ == "__main__":
    main()
