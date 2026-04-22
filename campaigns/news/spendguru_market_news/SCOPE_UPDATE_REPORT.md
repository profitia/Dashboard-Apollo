# SCOPE UPDATE REPORT — spendguru_market_news

**Data:** 2026-04-22
**Wersja konfiguracji:** v2 (keyword expansion + explicit thresholds)
**Autor:** AI Copilot / Tomasz Uściński
**Podstawa:** Audit `RELEVANCE_AND_APOLLO_AUDIT.md` + wyniki testu ORLEN Regranulat

---

## 1. Co się zmieniło — pliki

| Plik | Zmiana |
|------|--------|
| `campaigns/news/spendguru_market_news/config/keywords.yaml` | +8 grup branżowych, +2 grupy purchase signals |
| `campaigns/news/spendguru_market_news/config/campaign_config.yaml` | Jawne progi kwalifikacji (min_relevance_score / min_industry_score / min_purchase_signal_score) + pole active_industry_scope |
| `src/news/ingestion/article_fetcher.py` | Fallback og:title dla portali gdzie .entry-title === generic site name (tworzywa.online) |
| `campaigns/news/spendguru_market_news/config/sources.yaml` | +tworzywa_online z poprawnymi selektorami CSS i date extractorem |

---

## 2. Aktywny zakres branżowy po zmianach (10 branż)

| # | Branża | Klucz w keywords.yaml | Waga |
|---|--------|----------------------|------|
| 1 | Produkcja żywności | `food_production` | 4 |
| 2 | Napoje / Beverages | `beverages` | 3 |
| 3 | Sieci handlowe / Retail | `retail_chains` | 3 |
| 4 | FMCG / Handel spożywczy | `fmcg_trade` | 3 |
| 5 | Opakowania / Packaging | `packaging_containers` | 3 |
| 6 | Tworzywa sztuczne / Plastics | `plastics` | 3 |
| 7 | Chemia / Chemicals | `chemicals` | 3 |
| 8 | Farmacja / Pharmaceuticals | `pharmaceuticals` | 3 |
| 9 | Materiały budowlane | `building_materials` | 3 |
| 10 | Kosmetyki | `cosmetics` | 3 |
| 11 | Papier / Forest products | `paper_forest` | 3 |

> Uwaga: `manufacturing` (waga 2) pozostaje jako fallback dla ogólnych artykułów produkcyjnych.

---

## 3. Zmiany w keywords.yaml

### 3.1 Nowe grupy branżowe (industry_keywords) — 8 nowych

Każda dodana po istniejącej grupie `manufacturing`:

| Grupa | Kluczowe termy |
|-------|---------------|
| `beverages` (w3) | napoje, browar, piwowarstwo, woda mineralna, soki, linia rozlewnicza, beverage, brewery |
| `packaging_containers` (w3) | producent opakowań, opakowania spożywcze, folia, laminat, butelka PET, etykieta, packaging, opakowania jednostkowe/zbiorcze |
| `plastics` (w3) | tworzywa sztuczne, polimer, polipropylen, PET, PP, PE, regranulat, recyklat, rPP, rPET, bioplastik, compounding |
| `chemicals` (w3) | branża chemiczna, żywica, klej, farba, detergent, surfaktant, petrochemia, solvent |
| `pharmaceuticals` (w3) | farmacja, producent leków, API, suplementy diety, GMP, biotechnologia, OTC, generyki |
| `building_materials` (w3) | materiały budowlane, cement, beton, stal budowlana, izolacja termiczna, wełna mineralna, styropian |
| `cosmetics` (w3) | kosmetyki, producent kosmetyków, pielęgnacja skóry, perfumy, beauty, personal care, INCI |
| `paper_forest` (w3) | papier, celuloza, pulpa, karton, tektura, drewno, leśnictwo, tissue, makulatura |

### 3.2 Nowe grupy purchase signals — 2 nowe

Dodane po istniejącej grupie `expansion`:

| Grupa | Waga | Kluczowe termy |
|-------|------|---------------|
| `material_innovation` | 4 | nowy materiał, test materiału, zmiana surowca, regranulat, recyklat, bioplastik, innowacja opakowaniowa, nowe opakowanie, surowce wtórne |
| `compliance_trigger` | 5 | wymóg regulacyjny, do 2025/2026/.../2050, PPWR, ESPR, CBAM, dyrektywa opakowaniowa, recycled content, ESG requirement, compliance |

> `compliance_trigger` ma najwyższą wagę (5) — równą `investment_capacity` i `cost_pressure` — bo artykuły o terminach regulacyjnych to najsilniejszy sygnał zakupowy dla SpendGuru.

---

## 4. Zmiany w campaign_config.yaml — progi kwalifikacji

### Stan poprzedni
Progi wynikały wyłącznie z domyślnych wartości w `scorer.py` (`min_total=40, min_industry=15, min_purchase=15`). **Nie były nigdzie zdefiniowane w YAML.**

### Stan po zmianie

```yaml
min_relevance_score: 40        # total score (max ~115)
min_industry_score: 12         # min. branżowe (max 40)
min_purchase_signal_score: 15  # min. zakupowe (max 40)
```

### Uzasadnienie zmiany min_industry_score z 15 na 12

- **Przed:** Artykuły o plastics/packaging/chemicals musiały zdobyć 15 pkt branżowych z 4 dostępnych grup (retail, fmcg, food, manufacturing). Plastics-only artykuł miał industry=4 (1 trafienie w `food_production`) → FAIL.
- **Po:** Te same artykuły trafiają teraz w dedykowane grupy `plastics`, `packaging_containers`, `chemicals` (waga 3 każda) → łatwo osiągalne 9-18+ pkt za kilka trafień.
- Jednak dla artykułów z pogranicza (np. o recyklingu w kontekście regulacyjnym, bez słów "producent/manufacturer") industria=12 daje margines bezpieczeństwa bez otwierania na false positives.
- `min_purchase_signal_score: 15` pozostaje bez zmiany — każdy artykuł wartościowy dla SpendGuru musi zawierać sygnał zakupowy.

---

## 5. Oczekiwany wpływ na kwalifikację artykułów

### Co przechodzi teraz, a poprzednio nie:
- Artykuły o tworzywach sztucznych (PP, PET, regranulat, recyklat)
- Artykuły o producentach opakowań i innowacjach opakowaniowych
- Artykuły o chemii przemysłowej (żywice, kleje, środki czystości)
- Artykuły o terminach regulacyjnych (PPWR, ESPR, recycled content do 2030)
- Artykuły farmaceutyczne z sygnałem inwestycyjnym
- Artykuły kosmetyczne z sygnałem zakupowym
- Artykuły paperowe/celulozowe z sygnałem przetargowym

### Co nadal jest odrzucane (poprawnie):
- Artykuły czysto polityczne / makroekonomiczne bez branżowego kontekstu
- Artykuły zbyt stare (> 14 dni) — freshness check niezależny od keyword expansion
- Artykuły z industry score < 12 AND purchase score < 15 jednocześnie
- Artykuły o branżach poza aktywnym zakresem (np. motoryzacja, obronność, IT)

---

## 6. Walidacja

### 6.1 Smoke tests
```
python -m pytest tests/test_news_pipeline_smoke.py -q
29 passed in 17.33s
```
**PASS — 29/29** (potwierdzone po obu zmianach: keywords.yaml + campaign_config.yaml)

### 6.2 ORLEN Regranulat — scoring przed/po

| Metryka | PRZED (v1) | PO (v2) | Zmiana |
|---------|-----------|---------|--------|
| Industry score | 4.0 | 40.0 | +900% |
| Purchase score | 20.0 | 40.0 | +100% |
| Total score | 29.0 | 85.0 | +193% |
| Qualified | **FALSE** | **TRUE** | ✓ |
| Industry groups matched | food_production | manufacturing, packaging_containers, plastics, cosmetics, paper_forest | |
| Purchase groups matched | supply_chain, regulatory | investment_capacity, supply_chain, energy_packaging, regulatory, material_innovation, compliance_trigger | |

> Uwaga: W teście integracyjnym (real URL) wynik wciąż pokazuje v1 scores, bo artykuł z 2026-01-30 jest starszy niż 14 dni i zostałby odrzucony przez `max_article_age_days` przed scoring dla bieżącego skanowania. Powyższe v2 scores zostały zmierzone bezpośrednio przez `score_article()` z zachowanym tekstem artykułu.

### 6.3 Bio Planet — scoring po zmianach

| Metryka | PO (v2) |
|---------|---------|
| Industry score | 11.0 (poniżej progu 12) |
| Purchase score | 12.0 (poniżej progu 15) |
| Qualified | FALSE |

Bio Planet nadal nie przechodzi — artykuł był blokowany przez paywall i zawierał bardzo mało tekstu. Przy pełnym dostępie do treści i obecności sygnałów zakupowych (inwestycja, ekspansja) powinien przejść jako retail/fmcg. Problem jest na poziomie dostępności treści, nie konfiguracji.

---

## 7. Otwarte ryzyka i kolejna faza

### Ryzyko 1: False positives w nowych branżach
- Artykuły o chemii/tworzywach mogą trafić na firmy bez działu zakupów SpendGuru scope.
- Mitygacja: `min_purchase_signal_score: 15` jest barierą — artykuł branżowy bez sygnału zakupowego nie przechodzi.

### Ryzyko 2: Bio Planet + paywalle
- Wiele artykułów z cennych portali branżowych jest obciętych do leadu (< 200 znaków).
- Lead-only text nie zawiera wystarczającej liczby keyword matches.
- Kolejna faza (Phase 2): LLM relevance layer — klasyfikacja nawet z krótkim tekstem.

### Ryzyko 3: Apollo — brak emaili
- ORLEN S.A. i Pollena Kurowski: 10 kontaktów każdy, email=0.
- Problem niezależny od keyword expansion — dotyczy Apollo data coverage dla PL rynku.
- Kolejna faza: domain-based email enrichment (np. Hunter.io, Clearbit).

### Ryzyko 4: Artykuły z 2026-01-30 vs max_article_age_days: 14
- ORLEN artykuł (82 dni) jest poprawnie odrzucany przez age check przy live scan.
- Nie jest to błąd — age check chroni przed wysyłaniem outdated trigger messages.

### Kolejna faza (Phase 2) — rekomendacje
1. LLM relevance layer (krótki prompt, ~100 tokenów) dla artykułów z industry=10-14 — borderline cases
2. Apollo email enrichment via domain lookup
3. Rozszerzenie `sources.yaml` o portale: plasticstoday.com, packagingnews.co.uk, chemicalwatch.com, pharmamanufacturing.com
4. Testy na żywych artykułach z nowych branż (Stella Pack, Grupa Azoty, PKN ORLEN Polyolefins)

---

*Raport wygenerowany po implementacji zakresu zdefiniowanego w RELEVANCE_AND_APOLLO_AUDIT.md, sekcja "Rekomendacje Phase 1".*
