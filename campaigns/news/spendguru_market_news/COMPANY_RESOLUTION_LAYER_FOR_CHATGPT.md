# COMPANY RESOLUTION LAYER — For ChatGPT

**Data:** 2026-04-22 | **Kampania:** spendguru_market_news | **Status:** WDROŻONE (domyślnie wyłączone)

---

## 5 najważniejszych wniosków

1. **Nowa warstwa między entity_extractor a contact_finder** — rozwiązuje problem niedopasowania nazwy firmy z artykułu do jej formy w Apollo (Evra Fish → EvraFish, brand vs pełna nazwa prawna, spacja vs brak spacji).

2. **LLM jako warstwa OCENY, nie jedyne źródło prawdy** — pipeline buduje pakiet kandydatów + dowodów (comparison_key, name similarity, domain, industry), a LLM tylko koryguje heurystyczny wynik (max ±0.20). Heurystyka dominuje.

3. **Evra Fish → EvraFish jest w pełni wspierane** — comparison_key("Evra Fish") == comparison_key("EvraFish") == "evrafish" to najsilniejszy sygnał (+0.45). Razem z domain match (+0.20) i name similarity (+0.10) → total ≥ 0.75 → MATCH_CONFIDENT.

4. **Backward compatible i bezpieczne** — toggle `use_company_resolution: false` domyślnie. Jeśli warstwa rzuci wyjątek, pipeline wraca do oryginalnego flow. Smoke tests: 29/29 PASS po integracji.

5. **Cztery statusy decyzji z jasnymi konsekwencjami:**
   - `MATCH_CONFIDENT` (score ≥ 0.72) → przekaż resolved_company_name do contact_finder
   - `MATCH_POSSIBLE` (score ≥ 0.45) → przekaż (niższe confidence)
   - `AMBIGUOUS_HOLD` → manual review, brak automatycznej sekwencji
   - `NO_MATCH` → pomiń artykuł

---

## Finalna metoda — jak to działa

```
Artykuł → entity_extractor (source_name, canonical_name, comparison_key)
             ↓
         resolve_company()
           1. Apollo org search (canonical + source, max 16 kandydatów)
           2. Heuristic scoring per candidate (comparison_key, similarity, domain, industry)
           3. Opcjonalnie: website verification (8KB HTML, title+meta+h1)
           4. LLM evaluates top-5 candidates with evidence package
           5. Final confidence = heuristic_score + llm_adjustment (capped 0.0–1.0)
           6. Decision: MATCH_CONFIDENT | MATCH_POSSIBLE | AMBIGUOUS_HOLD | NO_MATCH
             ↓
         contact_finder(company_name=resolved_company_name)
```

---

## Ocena reguły kanonicznej dla firm

**Działa sensownie.** Reguła comparison_key jest deterministyczna i symetryczna:

| Input | comparison_key |
|-------|----------------|
| "Evra Fish" | "evrafish" |
| "EvraFish" | "evrafish" |
| "Evra Fish Sp. z o.o." | "evrafish" |
| "Grycan" | "grycan" |
| "Grycan - Lody od pokoleń Sp. z o.o." | **"grycanlodyodpokole"** (różny klucz!) |

Dla Grycan: comparison_key różny, ale partial_overlap + domain match + name_similarity + LLM → MATCH_POSSIBLE lub MATCH_CONFIDENT. Działa, choć mniej pewnie niż Evra Fish.

---

## Najważniejsze zmiany

| Plik | Opis |
|------|------|
| **`src/news/entity/company_resolver.py`** | Nowy moduł — 620 linii. Dataclass `ResolutionResult`, `resolve_company()`, `_collect_candidates()`, `_score_candidate_heuristic()`, `_fetch_website_signals()`, `_llm_evaluate_candidates()` |
| **`src/news/orchestrator.py`** | Integracja w `run_build_sequence()`: import resolvera, blok po cooldown check, obsługa 4 statusów, fallback na błąd |
| **`campaigns/news/.../config/campaign_config.yaml`** | 4 nowe toggles: `use_company_resolution: false`, `company_resolution_use_website_check: false`, `company_resolution_min_confidence: 0.45`, `company_resolution_confident_threshold: 0.72` |

---

## Czy wymagany kolejny etap?

**Nie natychmiast.** Warstwa jest gotowa do testu w dry-run. Po kilku tygodniach monitoringu warto dodać:
- Cache kandydatów Apollo (optymalizacja)
- Słownik aliasów YAML (dla powtarzających się firm z niestandardowym brandingiem)
- Liczniki statusów w run report (statystyki CONFIDENT/POSSIBLE/AMBIGUOUS/NO_MATCH)
