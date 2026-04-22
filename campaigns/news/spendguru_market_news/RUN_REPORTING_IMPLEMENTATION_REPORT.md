# RUN REPORTING — IMPLEMENTATION REPORT
**Kampania:** spendguru_market_news  
**Data:** 2026-04-22  
**Status:** ✅ Wdrożone, przetestowane (29/29 smoke tests)

---

## 1. Executive Summary

Wdrożono zbiorczy raport runu ("run report") generowany automatycznie po każdym przebiegu pipeline'u news. Raport powstaje w trzech formatach: JSON (dane maszynowe), Markdown (czytelny tekst), HTML (widok w przeglądarce). Zapisywany jest do katalogu `campaigns/news/spendguru_market_news/output/` jako pliki `latest_run_report.*`.

Cel: operator ma natychmiastowy wgląd w to, co pipeline zrobił z każdym artykułem — bez przeglądania logów.

---

## 2. Struktura raportu

### JSON (`latest_run_report.json`)
```json
{
  "generated_at": "2026-04-22T19:20:00Z",
  "campaign_id": "spendguru_market_news",
  "run_mode": "run-daily",
  "dry_run": false,
  "summary": {
    "total_processed": 8,
    "success": 1,
    "requires_attention": 3,
    "rejected_skipped": 3,
    "company_contact_blocked": 1,
    "requires_review": 1
  },
  "status_breakdown": [...],
  "detail_lists": { "READY_FOR_REVIEW": [...], "BLOCKED_NO_EMAIL": [...], ... },
  "top_reasons": [...]
}
```

### Markdown (`latest_run_report.md`)
Zawiera:
- Nagłówek z datą, kampanią, trybem, flagą dry_run
- Tabela SUMMARY: 6 kluczowych wskaźników
- Tabela STATUS BREAKDOWN: każdy status z liczbą, procentem, graficznym paskiem (█░)
- 4 sekcje operacyjne: Ready, Wymaga uwagi, Odrzucone/pominięte, Zablokowane firma/kontakt
- Szczegółowe listy artykułów dla 4 kluczowych statusów: `READY_FOR_REVIEW`, `BLOCKED_NO_EMAIL`, `PENDING_MANUAL_REVIEW`, `BLOCKED_COMPANY_AMBIGUOUS`
- Tabela TOP REASONS: najczęstsze przyczyny nieprocesowalności

### HTML (`latest_run_report.html`)
Pełny widok HTML z kolorowymi bannerami per kategoria statusu. Otwieralny bezpośrednio w przeglądarce.

### Grupowanie statusów w raporcie
| Grupa | Statusy |
|-------|---------|
| READY | `READY_FOR_REVIEW` |
| REQUIRES ATTENTION | `BLOCKED_NO_EMAIL`, `PENDING_MANUAL_REVIEW`, `BLOCKED_COMPANY_AMBIGUOUS` |
| REJECTED / SKIPPED | `REJECTED_QUALIFICATION`, `SKIPPED_DUPLICATE`, `SKIPPED_COOLDOWN`, `SKIPPED_FETCH_FAILED`, `REVIEW_ONLY` |
| COMPANY / CONTACT BLOCKED | `BLOCKED_NO_CONTACT`, `BLOCKED_COMPANY_NOT_FOUND`, `BLOCKED_COMPANY_NO_MATCH`, `BLOCKED_COMPANY_EXCLUDED`, `BLOCKED_MESSAGE_GENERATION_FAILED` |

---

## 3. Źródła danych

Raport pobiera dane z dwóch miejsc:

**1. `run_results` (lista wyników runu)**  
Każdy element to słownik z polami: `url`, `status`, `company`, `final_stage`, `final_reason`.  
Produkowany przez `run_build_sequence()` w locie — jeden wpis per artykuł.

**2. `state_manager._articles` (stan trwały)**  
JSON na dysku: `data/processed_articles.json`. Zawiera historię wszystkich artykułów z pełnymi metadanymi. Używany do liczenia unikalnych firm i kompletowania metadanych artykułów w detail listach.

Raport korzysta z `PipelineStatus` (unified status model, `src/news/pipeline_status.py`) — wszystkie 14 konstantów jest obsługiwanych.

---

## 4. Zmienione pliki

| Plik | Zmiana |
|------|--------|
| `src/news/reporting/run_report.py` | **NOWY** — moduł generujący raport (JSON/MD/HTML) |
| `src/news/reporting/__init__.py` | **NOWY** — package marker |
| `src/news/orchestrator.py` | **Zmodyfikowany** — import `build_and_save_run_report`, wywołanie po `run_build_sequence`, nowy tryb CLI `report`, poprawka sys.path |

---

## 5. Walidacja

| Test | Wynik |
|------|-------|
| `python -m pytest tests/test_news_pipeline_smoke.py -q` | **29/29 PASS** |
| Generacja raportu z syntetycznymi danymi (8 artykułów, mixed statuses) | **OK** — JSON 3.3 KB, MD 2.9 KB, HTML 6.8 KB |
| CLI `python src/news/orchestrator.py report` | **OK** — pliki zapisane do `campaigns/news/spendguru_market_news/output/` |
| Brak raportu gdy `results=[]` | **OK** — guard `if results:` w orchestratorze |
| Wyjątek w generacji raportu nie blokuje pipeline'u | **OK** — `try/except` z `log.warning` |

---

## 6. Ryzyka i ograniczenia

- **Raport nadpisuje się przy każdym runie** — pliki `latest_run_report.*` są zawsze nadpisywane. Brak historii per-run. Jeśli potrzebna historia: dodać timestamp do nazwy pliku.
- **Raport CLI (`report` mode) nie jest "live"** — czerpie dane z pliku stanu `data/processed_articles.json`, który może zawierać artykuły z poprzednich runów.
- **Brak raportowania dla `run_qualify()`** — raport jest generowany tylko w `run_build_sequence()`. Artykuły odrzucone na etapie `qualify` (bez pełnego pipeline'u) nie są w `run_results`.
- **HTML nie jest responsywny** — zaprojektowany do przeglądania na desktopie w przeglądarce.
- **Top reasons** bazują na `final_reason` — jeśli pipeline nie ustawia `final_reason` (stare ścieżki kodu), wyświetli się "No reason".

---

## 7. Rekomendacja końcowa

Moduł raportowania jest gotowy do produkcji. Następne możliwe ulepszenia (nie priorytet):
- Archiwizacja raportów z timestampem (historia runów)
- Integracja z emailem (wysyłka raportu Markdown po każdym run-daily)
- Dashboard zbiorczy (agregacja wielu runów)
