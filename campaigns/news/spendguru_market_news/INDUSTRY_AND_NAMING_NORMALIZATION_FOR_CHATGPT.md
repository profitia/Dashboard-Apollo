# INDUSTRY AND NAMING NORMALIZATION — FOR CHATGPT
# spendguru_market_news | 2026-04-22

---

## 5 kluczowych wniosków

1. **Branże miały niespójne nazwy w 3 różnych kontekstach** — klucze YAML, etykiety, komentarze w configu nie były ze sobą zsynchronizowane. Przykład: klucz `retail_chains`, etykieta `"Retail / Sieci handlowe"`, komentarz w config `"retail"` — trzy formy dla tej samej branży.

2. **Wprowadzono model 3-warstwowy** — każda branża ma teraz: (a) canonical label (EN, do raportów), (b) technical key (snake_case YAML), (c) matching terms (lista słów). Nie mieszamy tych trzech warstw.

3. **3 klucze zostały przemianowane** — `retail_chains→retail`, `beverages→food_beverages`, `paper_forest→paper_forest_products`. Grupy `fmcg_trade` i `manufacturing` zostały oznaczone jako supporting (nie canonical).

4. **Dodano `CompanyRecord` do pipeline** — lekka dataclass z polami: `source_name` (z artykułu), `canonical_name` (preferowana), `comparison_key` (do dedup), `aliases` (warianty). Backward-compatible: istniejące pola w `CompanyInfo` nie zostały usunięte.

5. **Smoke tests: 29/29 PASS** — żadna zmiana nie zepsuła istniejącej logiki. Scorer działa dynamicznie po kluczach YAML — rename kluczy nie wymagał zmian w kodzie scorera.

---

## Finalna rekomendowana metoda

### Branże — model 3-warstwowy

```
canonical label       technical key          matching terms
─────────────────     ───────────────        ─────────────────────────────
retail                retail                 sieć handlowa, supermarket, dyskont...
food production       food_production        produkcja żywności, przetwórstwo...
food & beverages      food_beverages         napoje, browar, woda mineralna...
packaging & containers  packaging_containers producent opakowań, folia, butelka PET...
plastics              plastics               tworzywa sztuczne, PP, PET, regranulat...
chemicals             chemicals              branża chemiczna, żywica, klej, farba...
pharmaceuticals       pharmaceuticals        farmacja, GMP, API, producent leków...
building materials    building_materials     cement, beton, wełna mineralna, styropian...
cosmetics             cosmetics              kosmetyki, beauty, INCI, personal care...
paper & forest products  paper_forest_products  papier, celuloza, karton, tektura...
```

Supporting (nie canonical):
- `fmcg_trade` — wzmacnia food/retail, weight 3
- `manufacturing` — generic fallback, weight 2

### Firmy — comparison_key

```python
make_comparison_key("Evra Fish Sp. z o.o.")  # → "evrafish"
make_comparison_key("EvraFish")              # → "evrafish"
make_comparison_key("ORLEN S.A.")            # → "orlen"
make_comparison_key("Bio Planet Sp. z o.o.") # → "bioplanet"
make_comparison_key("Grycan")                # → "grycan"
```

Reguła: **canonical_name** = forma firmowa (brand/strona); **source_name** = forma z artykułu; **comparison_key** = do deduplikacji.

---

## Lista ważnych zmian

| Plik | Zmiana |
|------|--------|
| `keywords.yaml` | Rename: retail_chains→retail, beverages→food_beverages, paper_forest→paper_forest_products. Etykiety EN. Znaczniki [CANONICAL]/[SUPPORTING]. |
| `campaign_config.yaml` | Nowe klucze w `active_industry_scope`. Nowe pole `active_supporting_groups`. |
| `src/news/utils/company_normalizer.py` | NOWY — `CompanyRecord`, `make_comparison_key()`, `make_company_record()` |
| `src/news/utils/__init__.py` | NOWY — moduł utils |
| `src/news/entity/entity_extractor.py` | +3 pola w `CompanyInfo`: `source_name`, `canonical_name`, `aliases`. `_normalize_company_name` deleguje do `make_comparison_key`. |

---

## Ocena reguły Evra Fish → EvraFish

**TAK, reguła jest sensowna i wdrożona.**

- comparison_key jest identyczny: "evrafish" dla obu form → dedup działa
- canonical_name = "EvraFish" (forma firmowa) → Apollo search lepiej trafi
- source_name = "Evra Fish" → zachowany jako ślad audit (skąd nazwa pochodzi)
- aliases = ["Evra Fish", "EvraFish"] → oba warianty dostępne

Ograniczenie: pipeline nie wie automatycznie, że "Evra Fish" → "EvraFish". LLM ekstrahuje formę z artykułu (source). Enrichment do canonical wymaga słownika aliasów (Phase 3).

Na tym etapie: comparison_key "evrafish" jest wystarczający do dedup i szukania w Apollo. Canonical enrichment można dodać później bez refactoru architektury.

---

## Stan po zmianach

- Branże spójne: **TAK** — 10 canonical labels, 10 technical keys, model 3-warstwowy
- Firmy mają canonicalization rule: **TAK** — `company_normalizer.py`, `CompanyRecord`
- Reguła Evra Fish → EvraFish: **TAK** — wzorzec wdrożony i przetestowany
- Smoke tests: **29/29 PASS**
