# Colian Live Pilot Report — NEXT_LIVE_PILOT_REPORT

**Kampania:** spendguru_market_news  
**Pilot:** Colian — wybrany jako lepszy kandydat z porównania Maspex vs Colian  
**Data pilota:** 2026-04-23  
**Plik wyników:** data/test/colian_live_pilot_results.json  
**Skrypt:** tests/colian_live_pilot.py

---

## 1. Executive Summary

Colian został wybrany do live pilota jako zwycięzca porównania Maspex vs Colian. Artykuł EEC 2026 z portalspozywczy.pl zawiera bogate sygnały zakupowe — eksplozja cen kakao, przejęcia zagraniczne, presja kosztów logistycznych — stanowiące silny hook dla SpendGuru w obszarze negocjacji surowcowych.

Pilot przeszedł 4 z 8 etapów: konfiguracja, kwalifikacja (z overridem), ekstrakcja encji, wyszukiwanie kontaktów. Pipeline został zablokowany na etapie doboru odbiorców: **0 kontaktów T1 i T2** spośród 10 znalezionych w Apollo.

**Status końcowy: BLOCKED_NO_CONTACT**

Wynik jest identyczny z pilotem Grycan (poprzednia sesja). To już 3. z rzędu BLOCKED_NO_CONTACT dla prywatnych polskich firm mid-cap z branży żywności/FMCG. Błąd nie leży po stronie pipeline'u — jest to systemowe ograniczenie pokrycia Apollo dla tej klasy firm.

---

## 2. Kwalifikacja

| Parametr | Wartość |
|---|---|
| Artykuł | "Colian chce wejść do top 10 w Europie. Kolański o eksporcie i przejęciach na EEC 2026" |
| URL | portalspozywczy.pl/slodycze-przekaski/wiadomosci/...287905.html |
| Opublikowano | 2026-04-23 |
| Źródło | portalspozywczy.pl (fixture — cookie wall blokuje bezpośredni fetch) |
| Total score (pilot fixture) | 68 |
| Industry score | 9 (próg: 12) — BELOW THRESHOLD |
| Purchase signal score | 35 (próg: 15) |
| Kwalifikacja | NOT QUALIFIED (override zastosowany dla pilota) |

**Dopasowane grupy purchase w fixture:** cost_pressure (ceny surowców, koszty produkcji, presja kosztowa), expansion (fuzja, akwizycja, ekspansja, eksport), supply_chain (zakupy surowców), investment_capacity (nowy zakład)

**Uwaga o scoringu:** W teście bezpośrednim przeprowadzonym wcześniej na bogatszym tekście artykułu scoring wyniósł total=76, industry=14, purchase=40 (kwalifikuje). Rozbieżność wynika ze skróconego tekstu w fixture pilota. Artykuł rzeczywisty kwalifikuje się. Override w pilocie jest prawidłowy.

**Problem strukturalny wykryty:** Słownik `keywords.yaml` -> `food_production` zawiera głównie terminy dotyczące lodów i nabiału (dodane dla Grycan). Słodycze i wyroby cukiernicze (Colian) nie są wystarczająco pokryte. Rekomendacja: dodać `producent słodyczy`, `słodycze`, `wyroby cukiernicze`, `czekolada`, `wafle` do grupy food_production.

---

## 3. Ekstrakcja encji

| Parametr | Wartość |
|---|---|
| Extracted name | Colian |
| Canonical name | Colian |
| Company type | producer |
| Eligible | True |
| Confidence | 0.98 |
| Domain (alias dict) | colian.pl |
| Company resolution | Pominięty (use_company_resolution=false) |

Ekstrakcja przez LLM — pewna identyfikacja bez ambiguity. "Colian" / "Grupa Colian" jednoznacznie wskazują tę samą spółkę.

---

## 4. Wyszukiwanie kontaktów (Apollo — live)

### Strategia wyszukiwania

| Krok | Wariant | Znalezionych | Z emailem |
|---|---|---|---|
| 1 (primary) | name_search "Colian" | 10 | 0 |
| 2 (domain fallback) | domain_search "colian.pl" | 10 | 0 |
| 3 (assoc fallback) | name_search "Grupa Colian" | 0 | 0 |
| Wynik strategii | winning_strategy=none | 10 total | 0 z emailem |

Dodatkowe warianty próbowane wcześniej (poza pipeline'm, manualnie):
- "Colian Group" / colian.com → 0 kontaktów

**10 znalezionych kontaktów (z live pilota):**

| # | Imię | Stanowisko | Tier |
|---|---|---|---|
| 1 | Sandra | Brand Manager | Tier 3 - Buyers/Operational |
| 2 | Radu | Country Manager Romania & Rep. of Moldova | Tier Uncertain |
| 3 | Jacek | Key Account Manager | Tier Uncertain |
| 4 | Krzysztof | National Key Account Manager | Tier Uncertain |
| 5 | Tomasz | Key Account Manager | Tier Uncertain |
| 6 | Simon | Senior National Account Manager | Tier Uncertain |
| 7 | Magda | Marketing Manager | Tier Uncertain |
| 8 | Zbigniew | Key Account Manager | Tier Uncertain |
| 9 | Wioleta | Key Account Manager | Tier Uncertain |
| 10 | Artur | Senior Key Account Manager | Tier Uncertain |

Profil kontaktów: wyłącznie KAMowie, Brand Managerowie, Country Manager ds. sprzedaży (Rumunia). Brak jakiegokolwiek C-level, Dyrektora, CPO ani innej roli T1/T2. Żaden kontakt nie ma emaila w Apollo.

---

## 5. Dobór odbiorców (recipient selection)

| Parametr | Wartość |
|---|---|
| Pilot max contacts | 3 |
| Kontakty wybrane (T1) | 0 |
| Kontakty wybrane (T2) | 0 |
| Łącznie wybrane | 0 |
| Łącznie wykluczone | 10 |
| Powód wykluczenia | Tier 3 lub Tier Uncertain — nie spełniają reguły kampanii |

Wszyscy 10 kontaktów odrzuceni. Pilot zablokowany na tym etapie.

**Dlaczego te role nie kwalifikują się:**
- Brand Manager → Tier 3 (operacyjny, bez odpowiedzialności za zakupy surowców)
- Key Account Manager → Tier Uncertain (sprzedaż, nie zakupy)
- Country Manager Romania → Tier Uncertain (sprzedaż/operations, bez "procurement component")
- Senior KAM → Tier Uncertain (sprzedaż)
- Marketing Manager → Tier Uncertain (marketing)

Reguła T2 wymaga: seniority (Director/Head/VP) + procurement component (Zakupy/CPO/Procurement). Żaden z 10 kontaktów nie spełnia obu warunków jednocześnie.

---

## 6. Generowanie wiadomości

Etap pominięty — pipeline zablokowany na recipient_selection przed generowaniem wiadomości.

| Parametr | Wartość |
|---|---|
| Wiadomości wygenerowane | 0 |
| Wiadomości nieudane | 0 |
| Powód | Brak odbiorców T1/T2 |

Kontekst zakupowy artykułu (kakao, M&A, logistyka) byłby silnym materiałem dla email_1. Nie doszło jednak do generowania.

---

## 7. Apollo operational flow

Etap nieosiągnięty — pipeline zablokowany wcześniej.

| Parametr | Wartość |
|---|---|
| Kontakty dodane do listy | 0 |
| Stage custom field | 0 |
| Custom fields synced | 0 |
| Email reveal | 0 (nie próbowany) |
| Auto-enroll | False (wymuszone w pilocie) |

Żadne operacje API Apollo nie zostały wykonane poza wyszukiwaniem kontaktów (read-only).

---

## 8. Notyfikacja

Nie wysłana — pipeline zablokowany przed etapem notyfikacji.

---

## 9. Werdykt

**Status: BLOCKED_NO_CONTACT**  
**Etap blokady:** recipient_selection  
**Powód:** 0 kontaktów Tier 1 (C-level) i Tier 2 (Procurement/Management) dla Colian w Apollo

**Co zadziałało poprawnie:**
- Ekstrakcja encji (Colian, confidence=0.98) - LLM działa ✓
- Wyszukiwanie kontaktów — 10 znalezionych, wszystkie warianty próbowane ✓
- Company aliases — colian.pl zarejestrowany, assoc fallback "Grupa Colian" próbowany ✓
- Pipeline zatrzymał się elegancko, wyniki zapisane do JSON ✓

**Co nie zadziałało:**
- Apollo nie ma zindeksowanego C-level ani procurement dla Colian
- Żaden z 10 kontaktów nie ma emaila w bazie
- industry score 9 (poniżej progu 12) — fixture za skrótowy, keywords.yaml za wąski dla słodyczy

**Wzorzec:** 3. z rzędu BLOCKED_NO_CONTACT dla prywatnych polskich firm FMCG:
1. Grycan (lody, producent premium) — 10 kontaktów, 0 T1/T2
2. Maspex (Tymbark, Żubrówka, Kubuś — prywatna, duża) — 10 kontaktów, 0 T1/T2
3. Colian (słodycze, eksport, Jan Kolański) — 10 kontaktów, 0 T1/T2

Jest to ograniczenie Apollo, nie ograniczenie pipeline'u.

---

## 10. Rekomendacje

### Krótkoterminowe

**A. Spróbuj firm z lepszym pokryciem Apollo:**
- Firmy notowane na GPW (LPP, Eurocash, AmRest, CCC) — C-level publicznie dostępny
- Firmy z silną obecnością korporacyjną w Europie (Mlekovita, Animex/Smithfield, Hochland)
- ORLEN, PKN ORLEN — duże korporacje z procurement działem

**B. Import CSV kontaktów (bypass Apollo search):**
- Użyj istniejącego pipeline'u CSV Import (`configs/csv_import/csv_import_pl_test.yaml`)
- Ręczne przygotowanie listy Dyrektorów Zakupów z Linkedin
- Kontakty z Colian / Maspex / Grycan znalezione ręcznie → import do Apollo → kampania

**C. Apollo list search:**
- Przeszukaj istniejące listy Apollo (`PL Tier 1 do market_news VSC`, `PL Tier 2 do market_news VSC`)
- Jeśli Jan Kolański lub Krzysztof Pawiński są już w systemie — użyj ich bezpośrednio

**D. Rozszerz keywords.yaml o confectionery:**
- Dodaj do `food_production`: `producent słodyczy`, `słodycze`, `wyroby cukiernicze`, `czekolada`, `wafle`, `cukierki`, `galaretki`
- Colian wówczas uzyska wystarczający industry score (>12) z prawdziwego artykułu

### Strategiczne

Pipeline market_news działa poprawnie dla firm z dobrym pokryciem Apollo. Testuj na firmach korporacyjnych (GPW, spółki z działami zakupów wymienionymi w raportach rocznych) zanim wrócisz do firm prywatnych.

---

*Raport wygenerowany przez AI Outreach Pipeline - spendguru_market_news*  
*Data pilota: 2026-04-23*  
*Skrypt: tests/colian_live_pilot.py*  
*Wyniki: data/test/colian_live_pilot_results.json*
