# Audit for ChatGPT — spendguru_market_news

**Kampania:** `campaigns/news/spendguru_market_news`
**Data:** 2026-04-22
**Kontekst:** AI Outreach Pipeline — news-triggered kampania SpendGuru

---

## Main Findings

1. Scorer jest czystym keyword-matchingiem — żadnej warstwy semantycznej ani LLM inference
2. Listy Apollo (`PL Tier 1/2/3 do market_news VSC`) są poprawnie używane jako DESTINATION, nie SOURCE
3. Kontakty są szukane w globalnej bazie Apollo (`mixed_people/api_search`), co jest architekturalnie poprawne
4. Artykuły upstream (dostawcy, materiały, opakowania) są odrzucane przez industry filter, mimo że są pośrednio relevantne zakupowo
5. Artykuł ORLEN/regranulat: purchase_score=20 (PASS), ale industry_score=4 (FAIL) — odrzucony przez zbyt wąski industry filter
6. Artykuł Bio Planet: score=0/0 — odrzucony przez brak keywordów wprost w tekście (możliwy paywall lub brak terminów branżowych)
7. Pipeline nie próbuje firm powiązanych gdy główna firma ma 0 emaili w Apollo
8. Brak fallback search po domenie firmy gdy `q_organization_name` zwraca 0 emaili
9. Dwa różne URL patterns w `apollo_client.py` — `search_people()` ma inny URL niż `_post()` używany w pipeline

---

## Qualification Logic — Biggest Problems

1. **Brak grupy `packaging_materials`** w `industry_keywords` — artykuły o opakowaniach (producenci, materiały, PP, PET, recykling) nie liczą się jako branżowe
2. **Brak grupy `material_innovation`** w `purchase_signals` — testy nowych materiałów, zmiana surowca, innowacja opakowaniowa nie są rozpoznawane jako sygnał zakupowy
3. **Brak grupy `compliance_trigger`** — konkretne daty regulacyjne (EU 2030 recycled content) nie są traktowane jako procurement trigger
4. **`min_industry_score: 15` jest za wysoki** dla artykułów upstream/indirect — artykuły o dostawcach w łańcuchu wartości potrzebują niższego progu branżowego lub osobnej ścieżki
5. **Scoring nie rozumie łańcucha wartości** — artykuł o dostawcy opakowań jest równie relevantny dla kupca w FMCG co artykuł o samej firmie FMCG, ale scorer tego nie widzi
6. **Brak warstwy LLM** — wszystko jest keyword-based. System nie "łączy kropek": "testy materiału = przyszłe zamówienia = trigger zakupowy"
7. **Grupy `food_production` i `retail_chains`** są bardzo dosłowne — brak rozumienia że "producent opakowań" to upstream relevance dla food production
8. **Brak separate scoring** dla: direct procurement relevance vs indirect vs ICP fit vs trigger strength

---

## Apollo Flow — Biggest Problems

1. **Brak domain-based fallback** — gdy `q_organization_name` zwraca kontakty bez emaili, pipeline się zatrzymuje zamiast retry po domenie
2. **Brak multi-company search** — gdy firma główna (np. ORLEN) to `type=other` i ma 0 emaili, pipeline nie próbuje firmy powiązanej (np. Pollena Kurowski) automatycznie
3. **`search_contact` używa `q_keywords: email`** zamiast `email: email` — może zwrócić false positives
4. **Stage lookup nie jest cachowany** — `GET /v1/contact_stages` wykonywany per kontakt, nie per sesja
5. **Brak auto-create listy** — jeśli "PL Tier 1 do market_news VSC" nie istnieje w Apollo (błąd w nazwie), kontakt nie jest przypisany, bez ostrzeżenia blokującego
6. **`search_people()` w apollo_client.py jest martwym kodem** — pipeline używa `_post()` bezpośrednio, `search_people()` ma inny URL i nie jest wywoływana

---

## Most Important Files to Review

- `src/news/relevance/scorer.py` — logika scoringu (keyword-only, brak LLM)
- `campaigns/news/spendguru_market_news/config/keywords.yaml` — grupy keywordów (brakuje: packaging, material_innovation, compliance_trigger)
- `campaigns/news/spendguru_market_news/config/campaign_config.yaml` — progi kwalifikacji (`min_industry_score: 15` → za wysoki)
- `src/news/contacts/contact_finder.py` — wyszukiwanie kontaktów Apollo (`_search_apollo_contacts`)
- `src/news/apollo/sequence_builder.py` — tworzenie draftu w Apollo, przypisanie do list, stage
- `Integracje/apollo_client.py` — klient Apollo, URL patterns, search_people vs _post rozbieżność

---

## Recommended Next Changes

1. **[keywords.yaml]** Dodaj grupy: `packaging_materials`, `material_innovation`, `compliance_trigger` — zero ryzyka, tylko YAML
2. **[campaign_config.yaml]** Zmień `min_industry_score: 15` → `10` (ewentualnie z podwyższonym purchase threshold)
3. **[contact_finder.py]** Dodaj domain-based fallback search gdy 0 emaili
4. **[contact_finder.py lub entity_extractor]** Gdy type=`other` i 0 emaili → sprawdź associated_companies
5. **[scorer.py lub nowy plik]** Opcjonalna warstwa LLM relevance check (toggle w campaign_config.yaml)
6. **[apollo_client.py]** Popraw `search_contact` — użyj `email:` zamiast `q_keywords:`

---

## Overall Conclusion

Kwalifikacja artykułów jest **zbyt literalna i zbyt wąska** — pipeline odrzuca artykuły pośrednio relevantne zakupowo (upstream suppliers, materiały, regulacje branżowe), które powinny triggerować outreach. Naprawienie keyword gaps w `keywords.yaml` i obniżenie `min_industry_score` to pierwsze kroki wymagające tylko zmiany YAML, bez ryzyka. Docelowo konieczna jest warstwa LLM do semantycznej oceny relevance.

Flow Apollo jest **architekturalnie poprawny** — listy Tier 1/2/3 są destinations, nie sources. Wyszukiwanie kontaktów przez `mixed_people/api_search` jest właściwym podejściem. Główne luki to brak fallback strategii gdy główna firma ma 0 emaili oraz kilka drobnych technicznych niedoskonałości (caching, URL pattern, search payload).

---

*Pełny raport: `campaigns/news/spendguru_market_news/RELEVANCE_AND_APOLLO_AUDIT.md`*
