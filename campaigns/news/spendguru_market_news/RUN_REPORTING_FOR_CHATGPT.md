# RUN REPORTING — PODSUMOWANIE DLA CHATGPT

## Co zostało wdrożone

Po każdym przebiegu pipeline'u news (`run_build_sequence` lub `run-daily`) generowany jest automatycznie zbiorczy raport runu w trzech formatach: JSON, Markdown, HTML. Pliki lądują w `campaigns/news/spendguru_market_news/output/latest_run_report.*`.

Dodatkowo dostępny jest nowy tryb CLI: `python src/news/orchestrator.py report` — generuje raport z aktualnego pliku stanu bez uruchamiania pipeline'u.

---

## 10 kluczowych wniosków

**1. Raport daje natychmiastowy przegląd operacyjny bez przeglądania logów.**  
Po runie otwierasz `latest_run_report.md` lub `.html` i widzisz: ile artykułów przetworzono, ile trafiło do Apollo, ile wymaga uwagi.

**2. Statusy są pogrupowane operacyjnie, nie technicznie.**  
Zamiast 14 kodów statusów masz 4 grupy: READY / REQUIRES ATTENTION / REJECTED-SKIPPED / COMPANY-CONTACT BLOCKED. Każda grupo ma swoją sekcję z listą artykułów.

**3. REQUIRES ATTENTION to najważniejsza sekcja operacyjna.**  
Zawiera: `BLOCKED_NO_EMAIL` (artykuł ważny, firma w Apollo, ale brak emaila), `PENDING_MANUAL_REVIEW` (czeka na decyzję człowieka), `BLOCKED_COMPANY_AMBIGUOUS` (resolver nie mógł rozstrzygnąć). Te artykuły można uratować ręcznie.

**4. TOP REASONS pokazuje gdzie leży systemowy problem.**  
Jeśli 60% artykułów odpada z tym samym powodem (`Industry score too low`, `No company extracted`), to sygnał do kalibracji scorera lub entity_extractora.

**5. Raport poprawnie odzwierciedla unified status model.**  
Wszystkie 14 konstantów z `PipelineStatus` jest obsługiwanych. Raport nie "gubi" żadnego statusu.

**6. Raport jest bezpieczny — nie blokuje pipeline'u.**  
Cała generacja raportu jest opakowana w `try/except`. Błąd w raporcie = log warning, pipeline zwraca wyniki normalnie.

**7. Dane dla raportu czerpie z `run_results` (bieżący run) i `state_manager._articles` (historia).**  
Dzięki temu detail listy mogą pokazać pełne metadane artykułu (tytuł, URL), nie tylko kod statusu.

**8. Tryb `report` CLI pozwala wygenerować raport z historii bez uruchamiania runu.**  
Przydatne gdy chcesz zobaczyć aktualny stan po przerwie albo sprawdzić, co zostało przetworzone wcześniej.

**9. Paski postępu (█░) w Markdown dają szybką wizualizację struktury statusów.**  
Proporcje widoczne na pierwszy rzut oka bez otwierania HTML.

**10. Następnym naturalnym krokiem jest archiwizacja raportów z timestampem.**  
Aktualnie `latest_run_report.*` jest zawsze nadpisywany. Historia runów wymaga dodania timestampa do nazwy pliku — to jednolinijkowa zmiana w `save_run_report()`.

---

## Jak to pomaga operacyjnie

| Zadanie | Bez raportu | Z raportem |
|---------|-------------|------------|
| Sprawdzenie co zrobił run | Przeglądanie logów (setki linii) | Otwarcie latest_run_report.md (30 sekund) |
| Znalezienie artykułów do ręcznej interwencji | Grep po logach | Sekcja REQUIRES ATTENTION (gotowa lista) |
| Identyfikacja systemowego problemu | Analiza kodów w state.json | Tabela TOP REASONS |
| Potwierdzenie że pipeline nie zgubił artykułu | Trudne | Status breakdown z procentami |
| Raport po run-daily dla stakeholdera | Manualny opis | Skopiowanie sekcji SUMMARY z MD |

---

## Czy unified status model dobrze się wykorzystuje w praktyce?

**Tak.** Raport jest bezpośrednim dowodem że model działa:
- Każdy z 14 statusów jest zmapowany na grupę operacyjną
- `STATUS_META` (z `pipeline_status.py`) dostarcza opis i emoji do raportu — nie ma żadnych hard-kodowanych stringów w `run_report.py`
- Grupy operacyjne są spójne z tym, co pipeline faktycznie robi (kiedy wysyłamy notyfikację, kiedy blokujemy, kiedy odrzucamy)

Jedyne ograniczenie: raport nie pokazuje skumulowanych trendów między runami — każdy run to osobny snapshot. Dla trendów potrzebna byłaby baza danych lub archiwizacja raportów.
