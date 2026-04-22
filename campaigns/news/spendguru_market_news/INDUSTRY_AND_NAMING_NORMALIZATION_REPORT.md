# INDUSTRY AND NAMING NORMALIZATION REPORT — spendguru_market_news

**Data:** 2026-04-22
**Wersja:** v1
**Autor:** AI Copilot / Tomasz Uściński
**Podstawa:** Audit konfiguracji po rozszerzeniu scope branżowego (keywords.yaml v2, 2026-04-22)

---

## 1. Executive Summary

### Co było niespójne

Przed tym etapem w projekcie współistniały cztery niezależne systemy nazewnictwa:

| Kontekst | Przykład niespójności |
|----------|-----------------------|
| Klucze YAML (`keywords.yaml`) | `retail_chains`, `beverages`, `paper_forest` — bez wyraźnego wzorca |
| Etykiety biznesowe (`label:`) | Mieszany PL+EN, np. `"Napoje / Beverages"`, `"Papier / Paper & Forest Products"` |
| Komentarz w `campaign_config.yaml` | `"food & beverages | food production | retail | ..."` — lista w komentarzu, niezwiązana z kluczami |
| Lista `active_industry_scope` | Zawierała `fmcg_trade` i `manufacturing` jako rzekomo canonical, choć są to grupy wspierające |

Dodatkowe problemy:
- `beverages` istniał jako osobna grupa, ale canonical scope wymagał `food & beverages` (połączone z food) — brak mapowania
- `retail_chains` sugerował w nazwie tylko sieci, gdy zakres był szerszy (handel detaliczny ogółem → "retail")
- `paper_forest` nie zawierało `_products` wbrew canonicznej nazwie "paper & forest products"
- Brak formalnego modelu 3-warstwowego (canonical label / technical key / matching terms)

### Przyjęta metoda

Model 3-warstwowy:
```
canonical label  →  technical key         →  terms (w keywords.yaml)
"retail"         →  retail                →  sieć handlowa, supermarket, ...
"food & beverages" → food_beverages       →  napoje, browar, woda mineralna, ...
"paper & forest products" → paper_forest_products → papier, celuloza, ...
```

### Co zmieniono

| Zmiana | Pliki |
|--------|-------|
| Przemianowanie 3 kluczy YAML | `keywords.yaml` |
| Ujednolicenie etykiet na angielski canonical | `keywords.yaml` |
| Oznaczenie grup canonical vs supporting | `keywords.yaml`, `campaign_config.yaml` |
| Aktualizacja `active_industry_scope` | `campaign_config.yaml` |
| Nowa warstwa normalizacji nazw firm | `src/news/utils/company_normalizer.py` |
| `CompanyInfo` — nowe pola | `src/news/entity/entity_extractor.py` |

---

## 2. Industry Naming Normalization

### 2.1 Final Canonical Business Labels (10 branż)

Canonical labels są anglojęzyczne, czytelne, stałe — używane w raportach i dokumentacji:

1. **retail**
2. **food production**
3. **food & beverages**
4. **packaging & containers**
5. **plastics**
6. **chemicals**
7. **pharmaceuticals**
8. **building materials**
9. **cosmetics**
10. **paper & forest products**

### 2.2 Final Technical Keys

Klucze YAML — stabilne, snake_case, odpowiadają 1:1 canonical labels:

| Canonical Label | Technical Key |
|-----------------|---------------|
| retail | `retail` |
| food production | `food_production` |
| food & beverages | `food_beverages` |
| packaging & containers | `packaging_containers` |
| plastics | `plastics` |
| chemicals | `chemicals` |
| pharmaceuticals | `pharmaceuticals` |
| building materials | `building_materials` |
| cosmetics | `cosmetics` |
| paper & forest products | `paper_forest_products` |

**Supporting groups (nie canonical, ale aktywne w scoringu):**

| Technical Key | Rola |
|---------------|------|
| `fmcg_trade` | Wzmacnia scoring dla retail, food_production, food_beverages |
| `manufacturing` | Generic fallback dla ogólnych artykułów produkcyjnych (niższa waga=2) |

### 2.3 Mapping Table: Label → Key → Matching Scope

| Canonical Label | Technical Key | Przykłady terms |
|-----------------|---------------|-----------------|
| retail | `retail` | sieć handlowa, supermarket, dyskont, handel detaliczny, Biedronka, Lidl, Dino |
| food production | `food_production` | produkcja żywności, przetwórstwo spożywcze, branża spożywcza, food manufacturer |
| food & beverages | `food_beverages` | napoje, browar, woda mineralna, soki, piwowarstwo, linia rozlewnicza, beverage |
| packaging & containers | `packaging_containers` | producent opakowań, folia, butelka PET, etykieta, packaging, opakowania spożywcze |
| plastics | `plastics` | tworzywa sztuczne, polipropylen, PET, PP, regranulat, recyklat, bioplastik |
| chemicals | `chemicals` | branża chemiczna, żywica, klej, farba, detergent, petrochemia, surfaktant |
| pharmaceuticals | `pharmaceuticals` | farmacja, producent leków, API, suplementy diety, GMP, biotechnologia |
| building materials | `building_materials` | materiały budowlane, cement, beton, wełna mineralna, styropian |
| cosmetics | `cosmetics` | kosmetyki, producent kosmetyków, beauty, personal care, INCI |
| paper & forest products | `paper_forest_products` | papier, celuloza, pulpa, karton, tektura, drewno, tissue, makulatura |

### 2.4 Files Changed

| Plik | Zmiana |
|------|--------|
| `campaigns/news/spendguru_market_news/config/keywords.yaml` | Przemianowano klucze: `retail_chains→retail`, `beverages→food_beverages`, `paper_forest→paper_forest_products`. Ujednolicono etykiety (EN). Dodano znaczniki `[CANONICAL]` / `[SUPPORTING]`. |
| `campaigns/news/spendguru_market_news/config/campaign_config.yaml` | Zaktualizowano `active_industry_scope` (nowe klucze). Dodano `active_supporting_groups`. Zaktualizowano komentarz z canonical labels. |

---

## 3. Company Naming Normalization

### 3.1 Proposed Normalization Method

Lekka, deterministyczna 3-elementowa struktura na firmę:

```
source_name     — nazwa firmy z artykułu (oryginalna, niezmieniana)
canonical_name  — preferowana forma (branding firmy, strona, stopka)
comparison_key  — klucz do deduplikacji / porównań
                  (lowercase, bez spacji, bez form prawnych, bez znaków spec)
aliases         — lista wszystkich znanych wariantów (source + canonical + inne)
```

### 3.2 Canonical Company Name Rules

**Hierarchia preferencji dla canonical_name:**

1. Forma używana przez firmę na oficjalnej stronie / stopce / brandingu
2. Forma zgodna z domeną (evrafish.com → EvraFish)
3. Forma najczęściej pojawiająca się w wiarygodnych źródłach
4. Forma prawna (Sp. z o.o., S.A.) może być przechowywana oddzielnie lub jako alias — **nie jest canonical**

**Reguły ogólne:**
- Jeśli artykuł i firma używają tej samej nazwy → source = canonical
- Jeśli artykuł pisze wariant z błędem spacji / casingiem → canonical = forma firmowa
- Forma prawna NIE jest canonical — stanowi osobny alias lub jest pomijana przy porównaniu

### 3.3 Alias Handling

Aliases zawierają **wszystkie znane formy nazwy**, w tym:
- source_name (z artykułu)
- canonical_name (preferowana)
- dodatkowe warianty przekazane przy tworzeniu rekordu

Deduplication: po dokładnym stringu (nie po comparison_key) — dzięki temu "Evra Fish" i "EvraFish" są osobnymi aliasami mimo tego samego comparison_key.

### 3.4 Example: Evra Fish → EvraFish

```python
make_company_record(
    source_name="Evra Fish",
    canonical_name="EvraFish",
)
```

Wynik:
```
source_name     : "Evra Fish"
canonical_name  : "EvraFish"
comparison_key  : "evrafish"
aliases         : ["Evra Fish", "EvraFish"]
```

Uzasadnienie:
- artykuł na portalspozywczy.pl pisze "Evra Fish" (z spacją)
- firma sama używa "EvraFish" w brandingu i domenie evrafish.com
- oba warianty mają ten sam `comparison_key = "evrafish"` → dedup działa poprawnie
- `canonical_name = "EvraFish"` używane przy wyszukiwaniu w Apollo i raportach

Ten sam wzorzec zastosować dla:
- "Bio Planet" vs "BioFresh" (gdyby firma użyła rebrandingu)
- "Stella Pack" vs "StellaPack"
- "Grupa Azoty" vs "Azoty" (artykuły skracają)

### 3.5 Example: Grycan

```python
make_company_record(
    source_name="Grycan",
    canonical_name="Grycan",
    aliases=["Grycan - Lody od pokoleń Sp. z o.o."],
)
```

Wynik:
```
source_name     : "Grycan"
canonical_name  : "Grycan"
comparison_key  : "grycan"
aliases         : ["Grycan", "Grycan - Lody od pokoleń Sp. z o.o."]
```

Uzasadnienie:
- Firma popularnie znana jako "Grycan"
- Pełna forma prawna "Grycan - Lody od pokoleń Sp. z o.o." to alias
- comparison_key "grycan" — forma prawa usunięta, bez spacji
- W Apollo szukamy po "Grycan" (canonical) — najlepszy match

### 3.6 Files Changed

| Plik | Zmiana |
|------|--------|
| `src/news/utils/company_normalizer.py` | NOWY plik — `CompanyRecord`, `make_comparison_key()`, `make_company_record()` |
| `src/news/utils/__init__.py` | NOWY plik — moduł utils (plik pomocniczy) |
| `src/news/entity/entity_extractor.py` | Dodano pola `source_name`, `canonical_name`, `aliases` do `CompanyInfo`. Zaktualizowano `_normalize_company_name` (deleguje do `make_comparison_key`). |

---

## 4. Recommended Implementation Pattern

### Kiedy używać którego pola:

| Kontekst | Użyj |
|----------|------|
| Wyświetlanie w raporcie / approval email | `canonical_name` |
| Szukanie w Apollo (`q_organization_name`) | `canonical_name` |
| Deduplication / cooldown check | `comparison_key` |
| Logowanie (co artykuł napisał) | `source_name` |
| Fuzzy matching / aliasy | `aliases` |
| Porównanie dwóch firm | `comparison_key == comparison_key` |

### Pattern dla pipeline flow:

```python
# 1. Artykuł zwraca source_name (z LLM lub heurystyki)
company = extract_primary_company(...)
# company.source_name = "Evra Fish"    (z artykułu)
# company.canonical_name = "Evra Fish" (na razie = source, LLM nie zna brandingu)
# company.comparison_key = "evrafish"

# 2. (opcjonalnie, przyszłość) Wzbogacenie o canonical przez lookup
# company.canonical_name = enrich_canonical("evrafish")  # → "EvraFish"

# 3. Apollo search używa canonical_name
contacts = find_contacts(company_name=company.canonical_name, ...)

# 4. Dedup używa comparison_key
if state.is_company_in_cooldown(company.name_normalized):  # name_normalized = comparison_key
    skip()
```

---

## 5. Risks and Limitations

### Czego ta metoda nie rozwiązuje:

| Ryzyko | Opis | Mitygacja |
|--------|------|-----------|
| Dynamiczne aliasy | Pipeline nie zna `canonical_name` automatycznie — LLM zwraca formę z artykułu | Przyszłość: lookup tabela lub enrichment step |
| Firmy z identycznym comparison_key | "Orlen" i "Orlen S.A." → "orlen" — OK. Ale "Pol-Mak" i "PolMak" → "polmak" mogą być różnymi firmami | Akceptowalne ryzyko na tym etapie |
| Nieznane warianty brandingu | Evra Fish → EvraFish wymaga wiedzy o firmie — pipeline jej nie ma bez lookupa | Ewentualny słownik aliasów w YAML |
| Firmy wieloczłonowe | "Zakłady Mleczarskie w Pile S.A." → "zakadymleczarskiewpile" — porównanie trudne | Akceptowalne — artykuły i tak używają krótkich form |
| Rebrandingi | Firma zmienia nazwę, stare artykuły mają starą → dedup może nie zadziałać | Akceptowalne; rzadkie |
| Portal 403 / paywall | Artykuły z portalspozywczy.pl mogą być niedostępne automatycznie | Testy manualne lub obejście User-Agent |

### Przypadki wymagające ręcznej weryfikacji:

- Firmy z bardzo krótką nazwą (np. "ABC") — collision risk
- Firmy z nazwą zawierającą liczby (np. "Zakład nr 3")
- Grupy kapitałowe z wieloma spółkami zależnymi (ORLEN → PKN ORLEN, ORLEN Polyolefins, Orlen Południe)

---

## 6. Final Recommendation

### Czy obecna metoda jest wystarczająca na tym etapie?

**TAK** — dla bieżącego etapu projektu.

Uzasadnienie:
- Pipeline działa w trybie draft + human review → błędna canonical_name jest korygowana manualnie przed wysyłką
- comparison_key jest wystarczający do deduplikacji (cooldown window chroni przed duplikatami)
- Nowe pola `source_name` / `canonical_name` / `aliases` są opcjonalne i backward-compatible
- Smoke tests: 29/29 PASS po wszystkich zmianach

### Co zrobić później (Phase 3):

1. **Alias dictionary** — plik YAML `data/reference/company_aliases.yaml` z ręcznie zweryfikowanymi mapowaniami (Evra Fish → EvraFish, itp.)
2. **Canonical enrichment step** — przed Apollo search: lookup alias dictionary i aktualizacja `canonical_name`
3. **Artykuły testowe** — Evra Fish + Grycan: pobrać ręcznie lub przez User-Agent trick, uruchomić integration test z `--url`

---

*Raport wygenerowany po implementacji etapu normalizacji nazewnictwa. Zmiany są backward-compatible — orchestrator i scorer nie wymagają modyfikacji.*
