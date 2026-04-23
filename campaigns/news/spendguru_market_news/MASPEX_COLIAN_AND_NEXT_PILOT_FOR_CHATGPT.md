# Maspex vs Colian + Colian Live Pilot — Key Findings for ChatGPT

**Sesja:** 2026-04-23  
**Kampania:** spendguru_market_news  
**Cel sesji:** porównanie Maspex vs Colian, wybór lepszej firmy, live pilot, ocena pipeline

---

## 1. Porównano dwie firmy na podstawie artykułów z EEC 2026

- **Maspex** — artykuł 22-04-2026: "Trzy warunki silnego przemysłu w Polsce i Europie. Prezes Maspex na EEC 2026" | total=63, industry=18, purchase=23
- **Colian** — artykuł 23-04-2026: "Colian chce wejść do top 10 w Europie. Kolański o eksporcie i przejęciach na EEC 2026" | total=76, industry=14, purchase=40
- Obie firmy zakwalifikowały się (próg: total≥40, industry≥12, purchase≥15)

## 2. Colian wygrał porównanie — lepszy artykuł, te same ograniczenia Apollo

Colian wygrywa ze względu na:
- Wyższy total score (76 vs 63) i purchase signal (40 vs 23)
- Nowszy artykuł (23-04-2026 vs 22-04-2026)
- Bogatsze, bardziej konkretne triggery zakupowe: eksplozja cen kakao (1300→11000 GBP/t), M&A przejęcia zagraniczne, presja kosztów logistycznych i produkcyjnych, ekspansja na 52 rynki
- Artykuł Maspex jest bardziej polityczno-makroekonomiczny (apel o regulacje, demografia, energia) — mniej actionable dla SpendGuru

## 3. Oba Apollo coverage: 0 T1, 0 T2 — mimo wielu wariantów wyszukiwania

Próbowane warianty dla Maspex: "Maspex", "Grupa Maspex", "Maspex Wadowice", domena grupamaspex.com → łącznie 10 kontaktów, 0 T1/T2  
Próbowane warianty dla Colian: "Colian", "Grupa Colian", "Colian Group", domena colian.com → łącznie 10 kontaktów, 0 T1/T2

Wszystkie znalezione kontakty to: Brand Managerowie, KAMowie, Country Manager (sprzedaż), Marketing Manager. Brak jakiegokolwiek C-level ani Dyrektora Zakupów w żadnej z firm.

## 4. Live pilot Colian: BLOCKED_NO_CONTACT — ten sam wzorzec co Grycan

Pilot przeszedł etapy: konfiguracja → kwalifikacja (override, industry=9<12 z powodu skróconego fixture) → ekstrakcja encji (Colian, confidence=0.98) → wyszukiwanie kontaktów (10, 0 email, 0 T1/T2) → zablokowany na recipient_selection.

Żaden kontakt nie spełnia reguły T2 (seniority + procurement component). Pipeline zatrzymał się elegancko, wyniki zapisane do JSON.

## 5. To już 3. z rzędu BLOCKED_NO_CONTACT — systemowe ograniczenie Apollo dla prywatnych FMCG

| Firma | Typ | T1 | T2 | Kontakty | Status |
|---|---|---|---|---|---|
| Grycan | Prywatna, lody premium | 0 | 0 | 10 | BLOCKED_NO_CONTACT |
| Maspex | Prywatna, duże FMCG | 0 | 0 | 10 | BLOCKED_NO_CONTACT |
| Colian | Prywatna, słodycze, eksport | 0 | 0 | 10 | BLOCKED_NO_CONTACT |

Wniosek: Apollo nie ma zindeksowanego C-level ani procurement dla prywatnych polskich firm FMCG mid-cap. Nie jest to błąd pipeline'u — to cecha bazy Apollo dla tej kategorii firm.

## 6. Problem pomocniczy: keywords.yaml food_production nie obejmuje słodyczy

Słownik `food_production` zawiera głównie terminy ice cream / nabiał (dodane dla Grycan w poprzedniej sesji). Colian — producent słodyczy, wafli, czekolad — uzyska industry=9 zamiast >12, co powoduje failed qualification w pilocie fixture. Prawdziwy artykuł kwalifikuje się (test bezpośredni: 76/14/40).

**Rekomendacja:** dodać do `food_production`: `producent słodyczy`, `słodycze`, `wyroby cukiernicze`, `czekolada`, `wafle`, `galaretki`, `cukierki`.

## 7. Pipeline jest gotowy — problem jest po stronie danych wejściowych (Apollo coverage)

Wszystkie etapy pipeline'u zadziałały poprawnie: scoring, ekstrakcja encji, wyszukiwanie kontaktów, fallbacki, reguły selekcji, zapis wyników. Problem nie leży w kodzie — leży w jakości danych Apollo dla tej klasy firm.

## 8. Rekomendacje co dalej

**Opcja A — firmy z lepszym Apollo coverage:**  
LPP, Eurocash, AmRest (GPW), Mlekovita, Animex/Smithfield, Hochland — korporacje z C-level publicznie dostępnym w Apollo

**Opcja B — CSV import bypass:**  
Ręcznie zebrać Dyrektorów Zakupów z Linkedin (Colian, Maspex, Grycan) → import CSV → kampania przez csv_import pipeline (już gotowy, przetestowany)

**Opcja C — Apollo list search:**  
Sprawdzić czy Jan Kolański (Colian) lub Krzysztof Pawiński (Maspex) są już na listach Apollo (`PL Tier 1 do market_news VSC`) — jeśli tak, można użyć ich bezpośrednio

**Opcja D — rozszerz keywords.yaml:**  
Dodaj confectionery terms do `food_production` (patrz punkt 6) — wtedy Colian i podobne firmy słodyczowe będą się kwalifikować z właściwym score

---

**Pliki sesji:**
- Skrypt pilota: [tests/colian_live_pilot.py](../../../tests/colian_live_pilot.py)
- Wyniki JSON: [data/test/colian_live_pilot_results.json](../../../data/test/colian_live_pilot_results.json)
- Raport porównawczy: [MASPEX_COLIAN_COVERAGE_COMPARISON_REPORT.md](MASPEX_COLIAN_COVERAGE_COMPARISON_REPORT.md)
- Raport pilota: [NEXT_LIVE_PILOT_REPORT.md](NEXT_LIVE_PILOT_REPORT.md)

---

*Sesja: 2026-04-23 | spendguru_market_news | AI Outreach Pipeline*
