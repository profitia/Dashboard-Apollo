"""
Run Report — zbiorczy raport statusów po każdym uruchomieniu pipeline'u.

Generuje dwa pliki:
  - latest_run_report.md   (Markdown — czytelny operacyjnie)
  - latest_run_report.json (JSON — programistyczne użycie)
  - latest_run_report.html (HTML z kolorami statusów)

Dane źródłowe:
  - run_results: list[dict]  — wyniki bieżącego runu (results[] z orchestratora)
  - state_manager            — ArticleStateManager (dane historyczne ze stanu)
  - campaign_config          — konfiguracja kampanii (campaign_id, tryb)

Użycie z orchestratora:
    from news.reporting.run_report import build_and_save_run_report
    build_and_save_run_report(
        run_results=results,
        state_manager=state,
        campaign_config=campaign_config,
        report_dir=report_dir,
        run_mode="run-daily",
        dry_run=dry_run,
    )
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import datetime, timezone

from news.pipeline_status import PipelineStatus, STATUS_META

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operational groups — podzbiory statusów na sekcje raportu
# ---------------------------------------------------------------------------
GROUP_READY = [PipelineStatus.READY_FOR_REVIEW]

GROUP_ATTENTION = [
    PipelineStatus.BLOCKED_NO_EMAIL,
    PipelineStatus.PENDING_MANUAL_REVIEW,
    PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS,
]

GROUP_REJECTED_SKIPPED = [
    PipelineStatus.REJECTED_QUALIFICATION,
    PipelineStatus.SKIPPED_DUPLICATE,
    PipelineStatus.SKIPPED_COOLDOWN,
    PipelineStatus.SKIPPED_FETCH_FAILED,
    PipelineStatus.REVIEW_ONLY,
]

GROUP_COMPANY_CONTACT = [
    PipelineStatus.BLOCKED_NO_CONTACT,
    PipelineStatus.BLOCKED_COMPANY_NOT_FOUND,
    PipelineStatus.BLOCKED_COMPANY_NO_MATCH,
    PipelineStatus.BLOCKED_COMPANY_EXCLUDED,
    PipelineStatus.BLOCKED_MESSAGE_GENERATION_FAILED,
]

# Detail list statuses — dla których pokazujemy listę artykułów
DETAIL_STATUSES = {
    PipelineStatus.READY_FOR_REVIEW,
    PipelineStatus.BLOCKED_NO_EMAIL,
    PipelineStatus.PENDING_MANUAL_REVIEW,
    PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS,
}

# Emoji per status
STATUS_EMOJI = {
    PipelineStatus.READY_FOR_REVIEW: "🟢",
    PipelineStatus.REJECTED_QUALIFICATION: "⚪",
    PipelineStatus.SKIPPED_FETCH_FAILED: "⚪",
    PipelineStatus.SKIPPED_DUPLICATE: "⚪",
    PipelineStatus.SKIPPED_COOLDOWN: "⚪",
    PipelineStatus.REVIEW_ONLY: "⚪",
    PipelineStatus.BLOCKED_COMPANY_NOT_FOUND: "⚪",
    PipelineStatus.BLOCKED_COMPANY_EXCLUDED: "⚪",
    PipelineStatus.BLOCKED_COMPANY_NO_MATCH: "⚪",
    PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS: "🟡",
    PipelineStatus.BLOCKED_NO_CONTACT: "⚪",
    PipelineStatus.BLOCKED_NO_EMAIL: "🔴",
    PipelineStatus.BLOCKED_MESSAGE_GENERATION_FAILED: "⚪",
    PipelineStatus.PENDING_MANUAL_REVIEW: "🟡",
}

# HTML colors for status banner
STATUS_HTML_COLOR = {
    PipelineStatus.READY_FOR_REVIEW: ("#d4edda", "#28a745"),
    PipelineStatus.BLOCKED_NO_EMAIL: ("#f8d7da", "#dc3545"),
    PipelineStatus.PENDING_MANUAL_REVIEW: ("#fff3cd", "#856404"),
    PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS: ("#fff3cd", "#856404"),
}
DEFAULT_HTML_COLOR = ("#f2f2f2", "#888")


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_run_report(
    run_results: list[dict],
    campaign_config: dict,
    run_mode: str = "run-daily",
    dry_run: bool = False,
    state_articles: dict | None = None,
) -> dict:
    """
    Buduje słownik z danymi raportu.

    Args:
        run_results:      lista wyników bieżącego runu (results[] z orchestratora)
        campaign_config:  konfiguracja kampanii
        run_mode:         tryb runu (run-daily / build-sequence / single-article)
        dry_run:          czy tryb dry-run
        state_articles:   wszystkie artykuły ze state managera (_articles dict)

    Returns:
        dict z kompletnym raportem — używany przez formattery (md, json, html)
    """
    now = datetime.now(timezone.utc)
    campaign_id = campaign_config.get("campaign_id", "unknown")

    # --- Status counts ---
    status_counter: Counter = Counter(r.get("status", "unknown") for r in run_results)
    total = len(run_results)

    # --- Kategorie ---
    n_success = sum(status_counter.get(s, 0) for s in GROUP_READY)
    n_attention = sum(status_counter.get(s, 0) for s in GROUP_ATTENTION)
    n_skipped = sum(status_counter.get(s, 0) for s in GROUP_REJECTED_SKIPPED)
    n_company_contact = sum(status_counter.get(s, 0) for s in GROUP_COMPANY_CONTACT)
    n_review = status_counter.get(PipelineStatus.PENDING_MANUAL_REVIEW, 0)

    # --- Detailed lists per attention status ---
    detail_lists: dict[str, list[dict]] = {s: [] for s in DETAIL_STATUSES}
    for r in run_results:
        s = r.get("status", "")
        if s in detail_lists:
            detail_lists[s].append(r)

    # --- Enrich detail entries from state_articles ---
    if state_articles:
        url_to_state = {v.get("url", k): v for k, v in state_articles.items()}
        url_to_state.update({k: v for k, v in state_articles.items()})  # also by canonical key
        for s, entries in detail_lists.items():
            for entry in entries:
                url = entry.get("url", "")
                st = url_to_state.get(url, {})
                # Merge state fields if not already in results entry
                for field in ("final_stage", "final_reason", "article_title"):
                    if field not in entry and field in st:
                        entry[field] = st[field]

    # --- final_reason aggregation ---
    reason_counter: Counter = Counter()
    for r in run_results:
        reason = r.get("final_reason") or r.get("reason") or ""
        if reason:
            reason_counter[reason] += 1
    # Also pull from state articles that weren't in run_results
    if state_articles:
        result_urls = {r.get("url") for r in run_results}
        for key, art in state_articles.items():
            url = art.get("url", key)
            if url not in result_urls:
                reason = art.get("final_reason") or art.get("reason") or ""
                if reason:
                    reason_counter[reason] += 1

    return {
        "generated_at": now.isoformat(),
        "campaign_id": campaign_id,
        "run_mode": run_mode,
        "dry_run": dry_run,
        "summary": {
            "total_processed": total,
            "success": n_success,
            "requires_attention": n_attention,
            "rejected_skipped": n_skipped,
            "company_contact_blocked": n_company_contact,
            "requires_review": n_review,
        },
        "status_breakdown": [
            {
                "status": status,
                "count": count,
                "pct": round(count / total * 100, 1) if total else 0,
                "description": STATUS_META.get(status, {}).get("description", ""),
                "emoji": STATUS_EMOJI.get(status, "⚪"),
            }
            for status, count in sorted(status_counter.items(), key=lambda x: -x[1])
        ],
        "detail_lists": detail_lists,
        "top_reasons": [
            {"reason": reason, "count": count}
            for reason, count in reason_counter.most_common(10)
        ],
    }


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def _pct_bar(pct: float, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def format_markdown(report: dict) -> str:
    s = report["summary"]
    total = s["total_processed"]
    ts = report["generated_at"][:19].replace("T", " ")
    mode_label = report["run_mode"]
    if report["dry_run"]:
        mode_label += " (dry-run)"

    lines: list[str] = []
    lines.append(f"# Run Report — {report['campaign_id']}")
    lines.append(f"")
    lines.append(f"**Wygenerowany:** {ts} UTC  ")
    lines.append(f"**Tryb:** {mode_label}  ")
    lines.append(f"**Artykułów przetworzonych:** {total}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # --- Summary ---
    lines.append(f"## Podsumowanie")
    lines.append(f"")
    lines.append(f"| Kategoria | Liczba |")
    lines.append(f"|-----------|--------|")
    lines.append(f"| 🟢 Gotowe do review (READY_FOR_REVIEW) | {s['success']} |")
    lines.append(f"| 🔴🟡 Wymagają uwagi (BLOCKED_NO_EMAIL / PENDING) | {s['requires_attention']} |")
    lines.append(f"| ⚪ Odrzucone / pominięte | {s['rejected_skipped']} |")
    lines.append(f"| ⚪ Zablokowane — firma / kontakt | {s['company_contact_blocked']} |")
    lines.append(f"| **SUMA** | **{total}** |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # --- Status breakdown ---
    lines.append(f"## Breakdown per status")
    lines.append(f"")
    lines.append(f"| Status | Liczba | % | Pasek |")
    lines.append(f"|--------|--------|---|-------|")
    for entry in report["status_breakdown"]:
        bar = _pct_bar(entry["pct"])
        emoji = entry["emoji"]
        lines.append(f"| {emoji} `{entry['status']}` | {entry['count']} | {entry['pct']}% | {bar} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # --- Operational groups ---
    lines.append(f"## Grupy operacyjne")
    lines.append(f"")

    def _group_block(title: str, statuses: list[str], breakdown: list[dict]) -> list[str]:
        out = [f"### {title}", ""]
        bd_map = {e["status"]: e for e in breakdown}
        any_entry = False
        for st in statuses:
            e = bd_map.get(st)
            if e and e["count"] > 0:
                out.append(f"- {e['emoji']} **{st}** — {e['count']} przypadków ({e['pct']}%)")
                any_entry = True
        if not any_entry:
            out.append("_Brak w tym runie_")
        out.append("")
        return out

    lines += _group_block("🟢 Gotowe do działania", GROUP_READY, report["status_breakdown"])
    lines += _group_block("🔴🟡 Wymagają uwagi", GROUP_ATTENTION, report["status_breakdown"])
    lines += _group_block("⚪ Odrzucone / pominięte", GROUP_REJECTED_SKIPPED, report["status_breakdown"])
    lines += _group_block("⚪ Problemy z firmą / kontaktem", GROUP_COMPANY_CONTACT, report["status_breakdown"])
    lines.append(f"---")
    lines.append(f"")

    # --- Detail lists ---
    lines.append(f"## Szczegółowe listy artykułów")
    lines.append(f"")

    detail_labels = {
        PipelineStatus.READY_FOR_REVIEW: "🟢 READY_FOR_REVIEW — gotowe do uruchomienia",
        PipelineStatus.BLOCKED_NO_EMAIL: "🔴 BLOCKED_NO_EMAIL — kontakty bez emaila",
        PipelineStatus.PENDING_MANUAL_REVIEW: "🟡 PENDING_MANUAL_REVIEW — czeka na zatwierdzenie",
        PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS: "🟡 BLOCKED_COMPANY_AMBIGUOUS — niejednoznaczna firma",
    }

    for st, label in detail_labels.items():
        entries = report["detail_lists"].get(st, [])
        lines.append(f"### {label}")
        lines.append(f"")
        if not entries:
            lines.append(f"_Brak_")
            lines.append(f"")
            continue
        for e in entries:
            url = e.get("url", "")
            title = e.get("article_title") or e.get("title") or url[:70]
            company = e.get("company", "—")
            stage = e.get("final_stage") or STATUS_META.get(st, {}).get("stage", "—")
            reason = e.get("final_reason") or e.get("reason") or "—"
            lines.append(f"- **{company}**")
            lines.append(f"  - Artykuł: [{title[:70]}]({url})")
            lines.append(f"  - Etap: `{stage}` | Powód: {reason}")
            lines.append(f"")

    lines.append(f"---")
    lines.append(f"")

    # --- Top reasons ---
    lines.append(f"## Najczęstsze powody zatrzymania")
    lines.append(f"")
    if report["top_reasons"]:
        lines.append(f"| Powód | Liczba |")
        lines.append(f"|-------|--------|")
        for r in report["top_reasons"]:
            lines.append(f"| {r['reason'][:100]} | {r['count']} |")
    else:
        lines.append("_Brak danych_")
    lines.append(f"")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML formatter
# ---------------------------------------------------------------------------

def format_html(report: dict) -> str:
    s = report["summary"]
    total = s["total_processed"]
    ts = report["generated_at"][:19].replace("T", " ")
    mode_label = report["run_mode"]
    if report["dry_run"]:
        mode_label += " (dry-run)"

    def _badge(status: str, count: int) -> str:
        bg, border = STATUS_HTML_COLOR.get(status, DEFAULT_HTML_COLOR)
        emoji = STATUS_EMOJI.get(status, "⚪")
        return (
            f'<span style="background:{bg};border:1px solid {border};'
            f'border-radius:4px;padding:2px 8px;font-size:13px;margin:2px;display:inline-block;">'
            f'{emoji} {status}: <strong>{count}</strong></span>'
        )

    # Status breakdown rows
    bd_rows = ""
    for e in report["status_breakdown"]:
        bg, border = STATUS_HTML_COLOR.get(e["status"], DEFAULT_HTML_COLOR)
        bd_rows += (
            f'<tr style="background:{bg}">'
            f'<td>{e["emoji"]} <code>{e["status"]}</code></td>'
            f'<td style="text-align:center">{e["count"]}</td>'
            f'<td style="text-align:center">{e["pct"]}%</td>'
            f'<td style="font-size:12px;color:#555">{e["description"][:80]}</td>'
            f'</tr>\n'
        )

    # Detail lists
    detail_html = ""
    detail_labels = {
        PipelineStatus.READY_FOR_REVIEW: ("🟢 READY_FOR_REVIEW", "#d4edda", "#28a745"),
        PipelineStatus.BLOCKED_NO_EMAIL: ("🔴 BLOCKED_NO_EMAIL", "#f8d7da", "#dc3545"),
        PipelineStatus.PENDING_MANUAL_REVIEW: ("🟡 PENDING_MANUAL_REVIEW", "#fff3cd", "#856404"),
        PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS: ("🟡 BLOCKED_COMPANY_AMBIGUOUS", "#fff3cd", "#856404"),
    }
    for st, (label, bg, border) in detail_labels.items():
        entries = report["detail_lists"].get(st, [])
        detail_html += f'<h3 style="margin-top:24px">{label}</h3>'
        if not entries:
            detail_html += '<p style="color:#888;font-style:italic">Brak w tym runie</p>'
            continue
        detail_html += '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        detail_html += '<tr style="background:#f2f2f2"><th>Firma</th><th>Artykuł</th><th>Etap</th><th>Powód</th></tr>'
        for e in entries:
            url = e.get("url", "")
            title = e.get("article_title") or e.get("title") or url[:60]
            company = e.get("company", "—")
            stage = e.get("final_stage") or STATUS_META.get(st, {}).get("stage", "—")
            reason = e.get("final_reason") or e.get("reason") or "—"
            detail_html += (
                f'<tr style="background:{bg}">'
                f'<td style="padding:4px 8px"><strong>{company}</strong></td>'
                f'<td style="padding:4px 8px"><a href="{url}">{title[:60]}</a></td>'
                f'<td style="padding:4px 8px"><code>{stage}</code></td>'
                f'<td style="padding:4px 8px;font-size:12px">{reason[:100]}</td>'
                f'</tr>\n'
            )
        detail_html += '</table>'

    # Top reasons
    reasons_html = ""
    if report["top_reasons"]:
        reasons_html = '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        reasons_html += '<tr style="background:#f2f2f2"><th>Powód</th><th>Liczba</th></tr>'
        for r in report["top_reasons"]:
            reasons_html += f'<tr><td style="padding:4px 8px">{r["reason"][:120]}</td><td style="padding:4px 8px;text-align:center">{r["count"]}</td></tr>\n'
        reasons_html += '</table>'
    else:
        reasons_html = '<p style="color:#888;font-style:italic">Brak danych</p>'

    summary_badges = "".join(
        _badge(e["status"], e["count"])
        for e in report["status_breakdown"]
        if e["count"] > 0
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Run Report — {report['campaign_id']}</title></head>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#222;max-width:900px;margin:0 auto;padding:24px">
<h1 style="font-size:20px;border-bottom:2px solid #333;padding-bottom:8px">
  Run Report — {report['campaign_id']}
</h1>
<p style="color:#666;font-size:13px">
  Wygenerowany: <strong>{ts} UTC</strong> &nbsp;|&nbsp;
  Tryb: <strong>{mode_label}</strong> &nbsp;|&nbsp;
  Artykułów: <strong>{total}</strong>
</p>

<h2 style="font-size:16px;margin-top:24px">Podsumowanie</h2>
<table style="border-collapse:collapse;font-size:14px;margin-bottom:16px">
<tr><td style="padding:4px 12px">🟢 Gotowe do review</td><td style="padding:4px 12px"><strong>{s['success']}</strong></td></tr>
<tr><td style="padding:4px 12px">🔴🟡 Wymagają uwagi</td><td style="padding:4px 12px"><strong>{s['requires_attention']}</strong></td></tr>
<tr><td style="padding:4px 12px">⚪ Odrzucone / pominięte</td><td style="padding:4px 12px"><strong>{s['rejected_skipped']}</strong></td></tr>
<tr><td style="padding:4px 12px">⚪ Zablokowane (firma/kontakt)</td><td style="padding:4px 12px"><strong>{s['company_contact_blocked']}</strong></td></tr>
<tr style="background:#f2f2f2;font-weight:bold"><td style="padding:4px 12px">SUMA</td><td style="padding:4px 12px">{total}</td></tr>
</table>

<h2 style="font-size:16px;margin-top:24px">Breakdown per status</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="background:#333;color:#fff"><th style="padding:6px 8px;text-align:left">Status</th><th style="padding:6px 8px">Liczba</th><th style="padding:6px 8px">%</th><th style="padding:6px 8px;text-align:left">Opis</th></tr>
{bd_rows}
</table>

<h2 style="font-size:16px;margin-top:32px">Szczegółowe listy artykułów</h2>
{detail_html}

<h2 style="font-size:16px;margin-top:32px">Najczęstsze powody zatrzymania</h2>
{reasons_html}

<p style="font-size:11px;color:#999;margin-top:48px;border-top:1px solid #ddd;padding-top:8px">
  Wygenerowany automatycznie przez AI Outreach Pipeline — {report['campaign_id']}
</p>
</body></html>"""


# ---------------------------------------------------------------------------
# Save to files
# ---------------------------------------------------------------------------

def save_run_report(report: dict, report_dir: str) -> dict[str, str]:
    """Zapisuje raport w formatach: json, md, html. Zwraca ścieżki plików."""
    os.makedirs(report_dir, exist_ok=True)

    paths = {}

    # JSON
    json_path = os.path.join(report_dir, "latest_run_report.json")
    # JSON-serializable: convert detail_lists values (they may have non-serializable objects)
    json_report = dict(report)
    json_report["detail_lists"] = {
        status: [
            {k: v for k, v in entry.items() if isinstance(v, (str, int, float, bool, type(None)))}
            for entry in entries
        ]
        for status, entries in report["detail_lists"].items()
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    paths["json"] = json_path
    log.info("[REPORT] JSON saved: %s", json_path)

    # Markdown
    md_path = os.path.join(report_dir, "latest_run_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(format_markdown(report))
    paths["md"] = md_path
    log.info("[REPORT] Markdown saved: %s", md_path)

    # HTML
    html_path = os.path.join(report_dir, "latest_run_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(format_html(report))
    paths["html"] = html_path
    log.info("[REPORT] HTML saved: %s", html_path)

    return paths


# ---------------------------------------------------------------------------
# Public API — called from orchestrator
# ---------------------------------------------------------------------------

def build_and_save_run_report(
    run_results: list[dict],
    campaign_config: dict,
    report_dir: str,
    run_mode: str = "run-daily",
    dry_run: bool = False,
    state_manager=None,
) -> dict[str, str]:
    """
    Buduje i zapisuje zbiorczy raport runu.

    Args:
        run_results:    wyniki orchestratora (results[] z run_build_sequence / run_qualify)
        campaign_config: konfiguracja kampanii
        report_dir:     katalog zapisu raportów
        run_mode:       tryb runu (run-daily / build-sequence / single-article)
        dry_run:        czy dry-run
        state_manager:  opcjonalnie ArticleStateManager — wzbogaca dane

    Returns:
        dict {"json": path, "md": path, "html": path}
    """
    state_articles = None
    if state_manager is not None:
        try:
            state_articles = state_manager._articles
        except AttributeError:
            pass

    report = build_run_report(
        run_results=run_results,
        campaign_config=campaign_config,
        run_mode=run_mode,
        dry_run=dry_run,
        state_articles=state_articles,
    )

    try:
        return save_run_report(report, report_dir)
    except Exception as exc:
        log.warning("[REPORT] Failed to save run report: %s", exc)
        return {}
