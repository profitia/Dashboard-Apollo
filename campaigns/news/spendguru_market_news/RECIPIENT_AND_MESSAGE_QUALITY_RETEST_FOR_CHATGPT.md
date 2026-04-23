# Quality Re-Test Summary — spendguru_market_news
## For AI assistant / ChatGPT context

**Data:** 2026-04-21
**Kampania:** campaigns/news/spendguru_market_news
**Test:** jakościowy (mock contacts + real LLM), 3 przypadki, 18 kontaktów, 11 wygenerowanych wiadomości

---

## Kluczowe ustalenia

### 1. Tier mapping działa prawidłowo (18/18)
- Zasada dwuskładnikowa T2 odrzuca `Operations Director` i `Supply Chain Director` → Uncertain ✅
- `CPO` (bez komponentów) trafia do T2 jako wyjątek ✅
- `Brand Manager`, `Senior Brand Manager` → T3, wykluczeni z kampanii ✅
- `Head of Sourcing`, `Procurement Director`, `Dyrektor Zakupów`, `Head of Procurement` → T2 ✅
- `CEO`, `CFO`, `Prezes Zarządu`, `Dyrektor Zarządzający` → T1 ✅

### 2. Selekcja odbiorców: T1 + T2 only — działa
- ORLEN: 7 kandydatów → 4 wybrani (2 T1 + 2 T2), 3 wykluczone
- Grycan: 6 kandydatów → 4 wybrani (2 T1 + 2 T2), 2 wykluczone (Brand Managerzy — były błędem w old logic)
- Evra Fish: 5 kandydatów → 3 wybrani (1 T1 + 2 T2), 2 wykluczone

### 3. Jakość wiadomości E1 — HIGH we wszystkich przypadkach
Każdy mail spełnia:
- Anchor (tytuł artykułu + źródło w pierwszym zdaniu)
- Konkretna hipoteza z artykułu
- Bridge do biznesowego napięcia (T1: marża/EBIT, T2: savings/benchmark)
- Framework Profitii wpleciony naturalnie
- CTA: Calendly tier-specific + alternatywa telefoniczna
- Word count: E1 131-166 słów (spec 120-170), FU1 73-97 (spec 60-100), FU2 48-57 (spec 40-80)

### 4. Narracje T1 vs T2 wyraźnie różne
- **T1:** marża, EBIT, przewidywalność kosztów, kontrola ryzyka, obrona wyniku finansowego
- **T2:** benchmark, cost drivers, should-cost, argumentacja negocjacyjna, savings delivery

### 5. Gender poprawny, zakazane frazy nieobecne, brak podpisów LLM, brak em dash
Wszystkie 11 maili przechodzi wszystkie checklist.

---

## Co jeszcze wymaga poprawy

| # | Priorytet | Problem | Gdzie |
|---|-----------|---------|-------|
| 1 | HIGH | Evra Fish NO_MATCH w live Apollo (company resolution) | contact_finder.py / aliasy |
| 2 | MEDIUM | ORLEN zła spółka zależna w live Apollo | company resolution |
| 3 | LOW | Niespójne formatowanie CTA (URL bez intro-zdania w niektórych mailach) | message_writer.md |
| 4 | LOW | Duplikaty subject E1 dla T2 w tym samym case (Evra Fish) | prompt / message_generator |

---

## Następny krok

**Pilotaż live z Grycan (najlepiej rozwiązane company resolution w Apollo) — 1 artykuł, 2-4 kontakty, tryb draft → weryfikacja ręczna → send.**

ORLEN i Evra Fish wymagają naprawy company resolution zanim trafią na żywo.
