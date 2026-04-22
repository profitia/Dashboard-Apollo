# Company Resolution Layer — Podsumowanie testów (dla ChatGPT)
*Test: Evra Fish + Grycan | Data: 2026-04-21*

---

## Status testu

✅ Oba przypadki rozwiązane poprawnie.

| Case | Status | Confidence | Źródło |
|------|--------|------------|--------|
| Evra Fish | MATCH_CONFIDENT | 0.90 | Org search (via alias "EvraFish") |
| Grycan | MATCH_POSSIBLE | 0.65 | People search fallback |

---

## Kluczowe wnioski

1. **Alias dict krytyczny dla Evra Fish.** Media piszą "Evra Fish" ze spacją, Apollo ma firmę jako "Evrafish" (jedno słowo). Bez alias dict: 0 wyników → NO_MATCH. Z alias dict: exact comparison_key match → score 0.90.

2. **People search fallback krytyczny dla Grycan.** Org search (`mixed_companies/search`) zwrócił 0 wyników dla obu firm. Grycan znaleziony przez `mixed_people/api_search` — pracownicy firmy figurują w indeksie LinkedIn mimo braku org record. Ten fallback wdrożono właśnie w tej sesji.

3. **Domain hint z alias dict istotny dla Grycan.** Apollo nie miał domeny dla "Grycan - Lody od pokoleń". Bez domain_hint heurystyczny score = 0.25 (poniżej progu min_confidence 0.45). Z domain_hint `grycan.pl` → +0.20 → score 0.45 → LLM +0.20 → finalne 0.65.

4. **LLM działa poprawnie, ale miał timeout 825 sekund dla Evra Fish.** Przyczyna: OpenAI SDK bez skonfigurowanego timeoutu, GitHub Models provider może retryować długo. Naprawiono przez `concurrent.futures` timeout 45s — po przekroczeniu resolver kontynuuje bez LLM (heurystyka wystarczy).

5. **Portalspozywczy.pl — body JS-rendered.** Real fetch HTTP 200, ale treść artykułu = "Reklama". Resolver używa title + lead z og:description — te fetchują poprawnie. Brak wpływu na resolution.

6. **Alias dictionary jest uzasadniony.** Prosty YAML, 2 wpisy, wnosi realną wartość dla obu testowanych przypadków. Nie jest "ciężkim MDM" — jest ręczną korekcją nazwy dla konkretnych rozbieżności media vs Apollo. Strategia: dodawaj reaktywnie gdy NO_MATCH dla znanych firm.

7. **Trzy komponenty działają razem jako system:** alias dict (search variants) + people search fallback + domain hint. Każdy rozwiązuje inny gap Apollo coverage dla małych polskich firm.

---

## Co wdrożono w tej sesji

- `_search_apollo_people_for_orgs()` — people search fallback gdy org search = 0
- `_load_alias_dict()` + `_apply_alias_lookup()` — alias dictionary pre-search enrichment
- `_collect_candidates()` — rozszerzone o `extra_queries` i fallback do people search
- `resolve_company()` — zintegrowane alias dict + domain_hint dla heurystyki
- Timeout 45s dla LLM evaluation (concurrent.futures)
- `company_aliases.yaml` — wpisy dla Evra Fish + Grycan
- `campaign_config.yaml` — dodano klucz `company_resolution_alias_dict`
- Smoke tests: 29/29 PASS po wszystkich zmianach

---

## Co do zrobienia przed włączeniem na live

1. Ustaw `use_company_resolution: true` w `campaign_config.yaml`
2. Przetestuj kilka artykułów z realnego feedu Opoint
3. Monitoruj logi `[Resolver]` — szczególnie: ile razy people search fallback się odpala, jakie statusy dominują
4. Dodawaj wpisy do `company_aliases.yaml` reaktywnie gdy NO_MATCH dla znanych firm
