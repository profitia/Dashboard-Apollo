# Maspex vs Colian — Apollo Coverage Comparison Report

**Kampania:** spendguru_market_news  
**Data raportu:** 2026-04-23  
**Autor:** AI Outreach Pipeline  
**Cel:** Wybrać lepszą firmę do live pilota na podstawie dopasowania artykułu i pokrycia Apollo.

---

## 1. Executive Summary

Przeprowadzono porównanie dwóch firm — Maspex i Colian — na podstawie artykułów opublikowanych na EEC 2026 w dniach 22-23 kwietnia 2026. Obie firmy zakwalifikowały się do pilota na poziomie scoringu artykułu. Obie firmy wykazały identyczne ograniczenie w Apollo: 0 kontaktów T1 i T2 niezależnie od użytej nazwy i domeny.

**Wynik:** Colian wygrał porównanie jako kandydat do live pilota ze względu na wyższy łączny scoring artykułu, bogatsze sygnały zakupowe (M&A, presja kosztów kakao, logistyka, ekspansja zagraniczna) i nowszy artykuł (23-04-2026 vs 22-04-2026). Jednak obie firmy natrafiły na ten sam systemowy problem: prywatne polskie spółki mid-cap z branży FMCG nie mają zindeksowanych kontaktów C-level i procurement w Apollo.

---

## 2. Maspex

### 2.1 Dopasowanie artykułu

| Parametr | Wartość |
|---|---|
| Tytuł | "Trzy warunki silnego przemysłu w Polsce i Europie. Prezes Maspex na EEC 2026" |
| URL | portalspozywczy.pl/technologie/wiadomosci/...287852.html |
| Opublikowano | 2026-04-22 |
| Temat | Mowa prezesa Krzysztofa Pawińskiego na EEC 2026 — demografia, energia, regulacje |
| Total score | 63 |
| Industry score | 18 (próg: 12) |
| Purchase signal | 23 (próg: 15) |
| Kwalifikacja | **QUALIFIED** |

**Dopasowane grupy industry:** food_production (producent napojów), manufacturing, food_beverages  
**Dopasowane grupy purchase:** investment_capacity (moce produkcyjne), cost_pressure (koszty energii), supply_chain (zakupy surowców), regulatory (regulacje), expansion (ekspansja)

**Ocena artykułu:** Dobry scoring, ale artykuł ma charakter polityczno-makroekonomiczny (apel o regulacje, kwestia demografii) — sygnały zakupowe są pośrednie i trudniejsze do zaadresowania w outreach niż te z artykułu Colian.

### 2.2 Ekstrakcja encji i resolucja

| Parametr | Wartość |
|---|---|
| Canonical name | Maspex |
| Domain (known) | maspex.com |
| Alias dict | Tak — wpis dla Maspex, Grupa Maspex, Maspex Wadowice, Maspex Group |
| Company resolution | Pominięty (use_company_resolution=false) |

### 2.3 Pokrycie Apollo

**Przeszukane warianty:**

| Wariant (name / domain) | Łącznie | T1 | T2 | T3/Uncertain |
|---|---|---|---|---|
| "Maspex" / maspex.com | 10 | 0 | 0 | 10 |
| "Grupa Maspex" / maspex.com | 10 | 0 | 0 | 10 |
| "Maspex Wadowice" / maspex.com | 0 | 0 | 0 | 0 |
| "Maspex" / grupamaspex.com | 10 | 0 | 0 | 10 |

**Przykładowe kontakty (z name_search "Maspex", 10 wyników):**
- Anett | Senior Brand Manager - Tier 3
- Karin | Brand Manager CZ&SK - Tier 3
- Natalia | Brand Manager - Tier 3
- Oana | Brand Manager - Tier 3
- Lucian | Area Sales Manager - Tier Uncertain

Profil: wyłącznie Brand Managerowie i KAMowie ze środkowej Europy. Brak jakiegokolwiek kontaktu C-level, Dyrektora Zakupów ani Management.

### 2.4 Ocena

Maspex jest największą prywatną polską grupą FMCG (Tymbark, Żubrówka, Tiger, Kubuś, Lubella), ale skala i prywatny charakter firmy oznaczają, że C-level i procurement nie są publicznie zindeksowane w Apollo. Pipeline nie może postępować dalej. Status: **BLOCKED — 0 T1/T2**.

---

## 3. Colian

### 3.1 Dopasowanie artykułu

| Parametr | Wartość |
|---|---|
| Tytuł | "Colian chce wejść do top 10 w Europie. Kolański o eksporcie i przejęciach na EEC 2026" |
| URL | portalspozywczy.pl/slodycze-przekaski/wiadomosci/...287905.html |
| Opublikowano | 2026-04-23 |
| Temat | Jan Kolański (founder/prezes) na EEC 2026 — eksport, przejęcia, kakao, koszty |
| Total score (test bezpośredni) | 76 |
| Total score (pilot fixture) | 68 |
| Industry score | 14 (bezpośredni) / 9 (pilot fixture — poniżej progu 12) |
| Purchase signal | 40 (bezpośredni) / 35 (pilot fixture) |
| Kwalifikacja | QUALIFIED (test bezpośredni) / NOT QUALIFIED + override (pilot) |

> **Uwaga:** rozbieżność scoringu wynika z różnicy w zawartości fixture. Test bezpośredni korzystał z bogatszego tekstu artykułu (pełna treść). Pilot korzystał ze skróconego fixture. Artykuł rzeczywisty kwalifikuje się.

**Dopasowane grupy purchase:** investment_capacity (nowy zakład, moce produkcyjne), cost_pressure (koszty produkcji, presja kosztowa, ceny surowców, wzrost cen kakao), expansion (ekspansja, eksport, fuzja, akwizycja, strategia wzrostu), supply_chain (zakupy surowców, zarządzanie łańcuchem dostaw)

**Ocena artykułu:** Bardzo mocny kontekst zakupowy. Eksplozja cen kakao (z 1300 do 11000 GBP/t) — bezpośrednia presja kosztowa. M&A i przejęcia — jasny sygnał zarządzania kosztami integracji. Ekspansja na 52 rynki — koszty logistyczne i zarządzanie dostawcami. Artykuł bogatszy w actionable procurement triggers niż artykuł Maspex.

### 3.2 Ekstrakcja encji i resolucja

| Parametr | Wartość |
|---|---|
| Extracted name | Colian |
| Canonical name | Colian |
| Confidence | 0.98 |
| Company type | producer |
| Eligible | True |
| Domain (known) | colian.pl |
| Company resolution | Pominięty (use_company_resolution=false) |

Ekstrakcja przez LLM — pewna identyfikacja, brak ambiguity.

### 3.3 Pokrycie Apollo

**Przeszukane warianty:**

| Wariant (name / domain) | Łącznie | T1 | T2 | T3/Uncertain |
|---|---|---|---|---|
| "Colian" / colian.pl | 10 | 0 | 0 | 10 |
| "Colian" / colian.pl (domain fallback) | 10 | 0 | 0 | 10 |
| "Grupa Colian" / colian.pl | 0 | 0 | 0 | 0 |
| "Colian Group" / colian.com | 0 | 0 | 0 | 0 |

**Kontakty znalezione w live pilocie (name_search "Colian", 10 wyników):**

| # | Imię | Stanowisko | Tier |
|---|---|---|---|
| 1 | Sandra | Brand Manager | Tier 3 |
| 2 | Radu | Country Manager Romania & Rep. of Moldova | Tier Uncertain |
| 3 | Jacek | Key Account Manager | Tier Uncertain |
| 4 | Krzysztof | National Key Account Manager | Tier Uncertain |
| 5 | Tomasz | Key Account Manager | Tier Uncertain |
| 6 | Simon | Senior National Account Manager | Tier Uncertain |
| 7 | Magda | Marketing Manager | Tier Uncertain |
| 8 | Zbigniew | Key Account Manager | Tier Uncertain |
| 9 | Wioleta | Key Account Manager | Tier Uncertain |
| 10 | Artur | Senior Key Account Manager | Tier Uncertain |

Żaden z kontaktów nie pełni roli C-level, Dyrektora Zakupów ani Management odpowiedzialnego za procurement. "Country Manager Romania" i "Senior KAM" to role sprzedażowe, nie procurement/management w rozumieniu kampanii. Brak emaili dla wszystkich 10 kontaktów.

### 3.4 Ocena

Colian jest prywatną polską spółką (słodycze, 70% eksport, ~50 rynków) z bardzo silnym artykułem zakupowym, ale C-level (Jan Kolański) i procurement nie są zindeksowane w Apollo. Status: **BLOCKED — 0 T1/T2**.

---

## 4. Tabela porównawcza

| Kryterium | Maspex | Colian |
|---|---|---|
| Data artykułu | 22-04-2026 | 23-04-2026 (nowszy) |
| Total score | 63 | 76 (bezpośredni test) |
| Industry score | 18 | 14 (bezpośredni test) |
| Purchase signal score | 23 | 40 (bezpośredni test) |
| Kwalifikacja | QUALIFIED | QUALIFIED (bezpośredni test) |
| Procurement triggers | Pośrednie (koszty energii, regulacje) | Bezpośrednie (kakao, M&A, logistyka, eksport) |
| Ekstrakcja encji | n/a | Colian — confidence 0.98, eligible=True |
| Company resolution | Pominięty | Pominięty |
| Apollo: T1 | 0 | 0 |
| Apollo: T2 | 0 | 0 |
| Apollo: T3/Uncertain | 10 (Brand Managers, Area Sales) | 10 (Brand Manager, KAMs, Country Manager, Senior KAM) |
| Emaile w Apollo | 0 | 0 |
| Warianty próbowane | 4 (Maspex, Grupa Maspex, Maspex Wadowice, grupamaspex.com) | 4 (Colian, Colian Group, Grupa Colian, colian.com) |
| Najlepszy znaleziony kontakt | Area Sales Manager (Lucian) — Tier Uncertain | Country Manager Romania (Radu) — Tier Uncertain |
| Status pipeline | BLOCKED_NO_CONTACT | BLOCKED_NO_CONTACT |
| **Overall fit** | Dobry artykuł, słabe pokrycie | **Lepszy artykuł, identyczne słabe pokrycie** |

---

## 5. Werdykt: Colian wygrywa

**Wybrana firma: Colian**

**Powody:**
1. **Lepszy artykuł** — total score 76 vs 63. Sygnały zakupowe (purchase=40 vs 23) są bardziej konkretne i actionable: eksplozja cen kakao, M&A, integracja kosztowa, ekspansja na 52 rynki.
2. **Nowszy artykuł** — opublikowany 23-04-2026 (dziś), Maspex 22-04-2026. Świeżość kontekstu ma znaczenie dla personalizacji outreach.
3. **Lepszy pretext** — Kolański mówi o aktywnym zarządzaniu ryzykiem cenowym i kosztami przejęć. To bezpośredni hook dla SpendGuru w negocjacjach surowcowych. Maspex mówi o makroekonomii i polityce przemysłowej.
4. **Równy coverage** — obie firmy mają 0 T1/T2 w Apollo. Colian nie jest gorszy pod tym względem.

**Ograniczenie systemowe:** Obie firmy — oraz Grycan w poprzednim pilocie — wykazują ten sam problem. Prywatne polskie firmy mid-cap z branży FMCG nie mają zindeksowanego C-level ani procurement w Apollo. To 3. z rzędu BLOCKED_NO_CONTACT. Jest to znalezisko systemowe, nie błąd pipeline'u.

**Rekomendacja:** Patrz sekcja 9 raportu pilota Colian (NEXT_LIVE_PILOT_REPORT.md).

---

*Raport wygenerowany przez AI Outreach Pipeline - spendguru_market_news*  
*Data: 2026-04-23*
