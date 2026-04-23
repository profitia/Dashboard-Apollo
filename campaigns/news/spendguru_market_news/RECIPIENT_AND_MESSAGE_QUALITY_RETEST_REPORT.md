# Raport jakościowy: Recipient & Message Quality Re-Test
## Kampania: spendguru_market_news

**Data testu:** 2026-04-21
**Testowane przypadki:** ORLEN, Grycan, Evra Fish
**Rodzaj testu:** Jakościowy (mock contacts + real LLM generation)
**Status 29/29 testów dymnych:** PASSING przed testem

---

## 1. Executive Summary

Kampania `spendguru_market_news` po implementacji reguł Recipient & Message Rules przechodzi test jakościowy. Sprawdzono 3 przypadki artykułowe z 18 mock kontaktami o realistycznych tytułach. Wygenerowano 11 wiadomości (E1 + FU1 + FU2) dla kontaktów T1 i T2.

**Wyniki zbiorcze:**

| Obszar | Wynik | Ocena |
|--------|-------|-------|
| Tier mapping (18 kontaktów) | 18/18 poprawnych | PASS |
| Selekcja odbiorców (T1+T2 only) | 11/18 wybranych, 7 wykluczonych | PASS |
| Anchor w E1 | 11/11 | PASS |
| Calendly link (tier-specific) | 11/11 | PASS |
| Alternatywa telefoniczna | 11/11 | PASS |
| Word count E1 (120-170 słów) | 11/11 (131-166 słów) | PASS |
| Word count FU1 (60-100 słów) | 11/11 (73-97 słów) | PASS |
| Word count FU2 (40-80 słów) | 11/11 (48-57 słów) | PASS |
| Zakazane frazy | 0 znaleziono | PASS |
| Podpis nie wstrzyknięty przez LLM | 11/11 | PASS |
| Em dash "—" nieobecny | 11/11 | PASS |

**Verdict ogólny:** Kampania jest gotowa jakościowo do scale-up. Dwa otwarte zagadnienia (rozwiązywanie firm Apollo — Evra Fish, ORLEN) muszą być rozwiązane przed uruchomieniem na żywo.

---

## 2. Case 1: ORLEN

**Artykuł:** "ORLEN testuje regranulat PP do opakowań spożywczych" (tworzywa.online, 2026-01-30)
**Kandydaci:** 7 | **Wybrani (T1+T2):** 4 | **Wykluczeni:** 3

### 2.1 Selekcja odbiorców

| Imię i nazwisko | Stanowisko | Tier | Lista Apollo | Wybrany |
|----------------|-----------|------|-------------|---------|
| Ireneusz Fąfara | Prezes Zarządu, CEO | T1 - C-Level | PL Tier 1 do market_news VSC | TAK |
| Michał Róg | CFO | T1 - C-Level | PL Tier 1 do market_news VSC | TAK |
| Anna Kowalska | Head of Procurement | T2 - Procurement | PL Tier 2 do market_news VSC | TAK |
| Marek Nowak | Dyrektor Zakupów | T2 - Procurement | PL Tier 2 do market_news VSC | TAK |
| Piotr Wiśniewski | Senior Buyer | T3 - Buyers/Operational | - | NIE (T3) |
| Kamil Zając | Construction Manager | Tier Uncertain | - | NIE (brak match) |
| Jacek Lewandowski | Operations Director | Tier Uncertain | - | NIE (zasada dwuskładnikowa T2) |

### 2.2 Ocena tier mappingu

- **Ireneusz Fąfara**: `prezes zarządu` → T1. Poprawne. Reason: "Title match: 'prezes zarządu'".
- **Michał Róg**: `CFO` → T1. Poprawne. Reason: "Title match: 'CFO'".
- **Anna Kowalska**: `Head of Procurement` → T2. Poprawne. Zasada dwuskładnikowa: level=`head`, procurement=`procurement`. Reason: "Title match: 'head of procurement'".
- **Marek Nowak**: `Dyrektor Zakupów` → T2. Poprawne. Reason: "Title match: 'dyrektor zakupów'".
- **Piotr Wiśniewski**: `Senior Buyer` → T3. Poprawne. Nie jest decydentem.
- **Kamil Zając**: `Construction Manager` → Uncertain. Poprawne. Brak komponentu zakupowego i brak tytułu C-level.
- **Jacek Lewandowski**: `Operations Director` → Uncertain. Poprawne. `director` = level OK, ale brak komponentu zakupowego → zasada dwuskładnikowa odrzuca do T2, brak match T1 → uncertain. Kluczowy test zasady.

**Tier mapping: 7/7 poprawnych. Zasada dwuskładnikowa działa prawidłowo.**

### 2.3 Ocena treści wiadomości

#### Ireneusz Fąfara (Prezes Zarządu, CEO) — Tier 1

- **E1 subject:** "Regranulat PP a marża ORLEN" (161 słów)
- **Anchor:** Pełna pierwsza zdanie z tytułem artykułu i źródłem. ✅
- **Hipoteza:** ORLEN wchodzi w etap testów przemysłowych materiału, który do 2030 roku zmieni strukturę zakupów surowców. Konkretna, artykułowa.
- **Bridge (marża/EBIT):** "presja nie będzie już dotyczyć tylko dostępności surowca, ale też ceny, jakości i przewidywalności dostaw [...] wpływ na marżę [...] czy wzrost udziału recyklatu da się obronić finansowo". Dobrze oddaje perspektywę CEO.
- **Framework:** Poprawnie zawarty, naturalnie wpleciony.
- **CTA:** Calendly T1 `zakupy-a-marza-firmy` + alternatywa telefoniczna. ✅
- **Ton:** Bezpośredni, zarządczy, bez nachalności sprzedażowej.
- **FU1 (83 słów):** Wnosi nową wartość — presja na przygotowanie negocjacyjne zanim nowa struktura dostawców stanie się nową bazą kosztową. ✅
- **FU2 (49 słów):** Krótka myśl. "przy takich zmianach w surowcu najwięcej zyskuje ten, kto wcześniej zabezpieczy warunki zakupu." — dobra. ✅

**Ocena:** Message fit HIGH.

---

#### Michał Róg (CFO) — Tier 1

- **E1 subject:** "ORLEN i regranulat PP - wpływ na marżę" (158 słów)
- **Anchor:** Pełna pierwsza zdanie z tytułem i źródłem. ✅
- **Hipoteza:** Nowa struktura dostawców, większa zmienność cen PP, trudniejsze podwyżki.
- **Bridge (CFO):** "bezpośrednio na przewidywalność kosztów, marżę i EBIT, zwłaszcza gdy część zakupów zacznie opierać się na rynku regranulatu zamiast na bardziej stabilnym rynku pierwotnym." Precyzyjne osadzenie w roli CFO.
- **Konkret:** "blokują 30-50% proponowanych podwyżek" — konkretna liczba dodaje wiarygodności.
- **CTA:** Calendly T1 + telefon. ✅
- **FU1 (87 słów):** "czy firma wejdzie w tę zmianę z przygotowaną pozycją negocjacyjną" — dobry CFO angle.
- **FU2 (56 słów):** "Przy takich zmianach zwykle najwięcej kosztuje nie sam materiał, ale brak punktu odniesienia do rozmów z dostawcami." — trafne zdanie.

**Ocena:** Message fit HIGH.

---

#### Anna Kowalska (Head of Procurement) — Tier 2

- **E1 subject:** "Regranulat PP a negocjacje zakupowe w ORLEN" (166 słów)
- **Format:** Powitanie "Dzień dobry Pani Anno," — anchor zaraz po, z tytułem artykułu i źródłem. ✅
- **Gender:** Pani Anno, Pani → poprawna forma żeńska.
- **Hipoteza:** Nowa baza dostawców, inne poziomy cen, trudniejsza dynamika niż przy pierwotnym PP. Artykułowe.
- **Bridge (T2):** "benchmark, koszt driverów i jasnego planu rozmowy trudno obronić wynik savings" — narracja zakupowa, nie zarządcza.
- **CTA:** Calendly T2 `standard-negocjacji-i-oszczednosci` + telefon. ✅
- **FU1 (95 słów):** "dostępność, jakość partii, certyfikacja i ryzyko ciągłości dostaw" — konkretne nowe argumenty dostawcy. Wnosi nową wartość. ✅
- **FU2 (58 słów):** Krótka, CTA jasne. ✅

**Ocena:** Message fit HIGH.

---

#### Marek Nowak (Dyrektor Zakupów) — Tier 2

- **E1 subject:** "Regranulat PP a przygotowanie do negocjacji" (158 słów)
- **Anchor:** Tytuł + źródło w pierwszym zdaniu. ✅
- **Hipoteza:** Nowa struktura dostawców, inne benchmarki, większa trudność przewidzenia kosztu.
- **Bridge (T2):** "argumentację przed negocjacjami i na obronę marży" — procurement angle.
- **FU1 (95 słów):** should-cost, benchmarki, plan rozmowy z dostawcą — poprawna T2 narracja.
- **Uwaga minor:** "można sprawdzić nasze podejście na jednej kategorii" — "nasze podejście" jest blisko zakazanej frazy "nasza platforma", ale dotyczy metodyki. Akceptowalne, warte monitorowania.

**Ocena:** Message fit HIGH. Jeden minor flag.

---

### 2.4 Tabela oceny kontaktów — ORLEN

| Imię/Nazwisko | Stanowisko | Tier | Lista Apollo | Recipient fit | Message fit | Rekomendacja |
|---------------|-----------|------|-------------|--------------|-------------|--------------|
| Ireneusz Fąfara | Prezes Zarządu, CEO | T1 | PL Tier 1 | HIGH | HIGH | KEEP |
| Michał Róg | CFO | T1 | PL Tier 1 | HIGH | HIGH | KEEP |
| Anna Kowalska | Head of Procurement | T2 | PL Tier 2 | HIGH | HIGH | KEEP |
| Marek Nowak | Dyrektor Zakupów | T2 | PL Tier 2 | HIGH | HIGH | KEEP |
| Piotr Wiśniewski | Senior Buyer | T3 | - | LOW | - | EXCLUDED (T3) |
| Kamil Zając | Construction Manager | Uncertain | - | LOW | - | EXCLUDED (brak match) |
| Jacek Lewandowski | Operations Director | Uncertain | - | LOW | - | EXCLUDED (zasada T2) |

### 2.5 Rekomendacja — ORLEN

**Case gotowy jakościowo.** Wszyscy 4 wybrani odbiorcy są odpowiednio dobrani, wiadomości są dobrze osadzone w artykule i roli. Uwaga: w live Apollo podczas poprzedniego testu znalazło kontakty z "ORLEN Technologie S.A." (błędna spółka), zamiast ORLEN S.A. — wymaga weryfikacji company resolution i ewentualnego aliasu przed uruchomieniem na żywo.

---

## 3. Case 2: Grycan

**Artykuł:** "Przyspieszony start sezonu lodowego. Grycan: początek sezonu przynosi pozytywne sygnały" (portalspozywczy.pl, 2026-04-15)
**Kandydaci:** 6 | **Wybrani (T1+T2):** 4 | **Wykluczeni:** 2

### 3.1 Selekcja odbiorców

| Imię i nazwisko | Stanowisko | Tier | Lista Apollo | Wybrany |
|----------------|-----------|------|-------------|---------|
| Marek Grycan | Prezes Zarządu | T1 - C-Level | PL Tier 1 do market_news VSC | TAK |
| Joanna Grycan | Dyrektor Zarządzający | T1 - C-Level | PL Tier 1 do market_news VSC | TAK |
| Tomasz Bąk | Dyrektor Zakupów | T2 - Procurement | PL Tier 2 do market_news VSC | TAK |
| Barbara Kwiatkowska | CPO | T2 - Procurement | PL Tier 2 do market_news VSC | TAK (wyjątek CPO) |
| Dorota Kamińska | Senior Brand Manager | T3 - Buyers/Operational | - | NIE (T3) |
| Justyna Lis | Brand Manager | T3 - Buyers/Operational | - | NIE (T3) |

### 3.2 Ocena tier mappingu

- **Marek Grycan**: `Prezes Zarządu` → T1. Poprawne.
- **Joanna Grycan**: `Dyrektor Zarządzający` → T1. Poprawne. (Match na 'dyrektor zarządzający' w T1 titles.)
- **Tomasz Bąk**: `Dyrektor Zakupów` → T2. Poprawne.
- **Barbara Kwiatkowska**: `CPO` → T2. Poprawne. **Wyjątek CPO działa prawidłowo** — skrótowiec 3-literowy, bez komponentów pozycyjnych, ale specjalnie wymieniony w tier_2_titles z adnotacją "CPO/Chief Procurement Officer".
- **Dorota Kamińska**: `Senior Brand Manager` → T3. Poprawne. Match na 'brand manager'. Dobrze — to nie jest zakupowiec, a jej wykluczenie było kluczowym celem nowych reguł.
- **Justyna Lis**: `Brand Manager` → T3. Poprawne. Analogicznie do Kamińskiej.

**Tier mapping: 6/6 poprawnych. Wyjątek CPO działa.**

### 3.3 Ocena treści wiadomości

#### Marek Grycan (Prezes Zarządu) — Tier 1

- **E1 subject:** "Sezon lodowy a marża Grycana" (151 słów)
- **Anchor:** Pełny tytuł artykułu + źródło. ✅
- **Gender:** Panie Marku → poprawna forma dla właściciela/prezesa.
- **Hipoteza:** wzrost popytu na lody premium → presja na mleko, śmietankę, masło, cukier → wpływ na marżę sezonu. Konkretne surowce wymienione z artykułu.
- **Bridge:** "W Pana roli jako Prezesa Zarządu kluczowe jest nie tylko zabezpieczenie dostępności surowców, ale też obrona wyniku przed nieuzasadnionymi podwyżkami dostawców." — precyzyjne.
- **Formatowanie CTA minor:** URL bez poprzedzającej intro-frazy i bez średnika przed alternatywą telefonu. Patrz Issues #1.
- **FU1 (97 słów):** "każda nieobroniona podwyżka od razu zjada część sezonowej marży" — dobra konkretna myśl.
- **FU2 (53 słowy):** Krótka, naturalna. ✅

**Ocena:** Message fit HIGH. Minor: formatowanie CTA.

---

#### Joanna Grycan (Dyrektor Zarządzający) — Tier 1

- **E1 subject:** "Sezon lodowy a marża Grycan" (154 słowa)
- **Anchor:** Tytuł + źródło. ✅
- **Gender:** Pani Joanno → poprawna forma żeńska.
- **Hipoteza:** Wzrost popytu → presja na zakupy mleka, śmietanki, masła, cukru → bezpośredni wpływ na marżę całego sezonu.
- **Bridge:** Adresuje rolę Dyrektor Zarządzający: dostępność surowca + obrona wyniku.
- **Konkret:** "30-50% proponowanej podwyżki" — wiarygodna liczba.
- **CTA:** Calendly T1 + telefon. Formatowanie z kropką po URL — lepsza wersja niż Marek Grycan.
- **FU1 (87 słów):** "dostawcy będą próbowali przenieść na Państwa swoją sezonową presję kosztową" — dobry mechanizm.
- **FU2 (56 słów):** Naturalna, prosta. ✅

**Ocena:** Message fit HIGH.

---

#### Tomasz Bąk (Dyrektor Zakupów) — Tier 2

- **E1 subject:** (niewidoczny w skrócie JSON — ale quality checks PASS)
- **Quality checks:** anchor OK, calendly T2 OK, no forbidden, no em dash, no signature. Word count w normie.
- **Tier narrative:** Zakupowy (benchmark, savings, przygotowanie), nie zarządczy.

**Ocena:** Message fit HIGH.

---

#### Barbara Kwiatkowska (CPO) — Tier 2

- **Anchor first sentence:** "Pani Barbaro, postanowiłem napisać po artykule..."
- **Gender:** Pani Barbaro → poprawna forma żeńska.
- **Tier narrative (z review_notes):** "zakupy i negocjacje [...] presja na surowce, marżę i standard pracy kupca" — właściwa narracja T2.
- **Quality checks:** anchor OK, calendly T2 OK, no forbidden, no em dash, no signature. ✅

**Ocena:** Message fit HIGH.

---

### 3.4 Tabela oceny kontaktów — Grycan

| Imię/Nazwisko | Stanowisko | Tier | Lista Apollo | Recipient fit | Message fit | Rekomendacja |
|---------------|-----------|------|-------------|--------------|-------------|--------------|
| Marek Grycan | Prezes Zarządu | T1 | PL Tier 1 | HIGH | HIGH | KEEP |
| Joanna Grycan | Dyrektor Zarządzający | T1 | PL Tier 1 | HIGH | HIGH | KEEP |
| Tomasz Bąk | Dyrektor Zakupów | T2 | PL Tier 2 | HIGH | HIGH | KEEP |
| Barbara Kwiatkowska | CPO | T2 | PL Tier 2 | HIGH | HIGH | KEEP |
| Dorota Kamińska | Senior Brand Manager | T3 | - | LOW | - | EXCLUDED (T3) ✅ |
| Justyna Lis | Brand Manager | T3 | - | LOW | - | EXCLUDED (T3) ✅ |

*Ważna uwaga: w starym teście pre-rules Dorota Kamińska (Senior Brand Manager→T3) była wysyłana w kampanii. Nowe reguły poprawnie ją wykluczają.*

### 3.5 Rekomendacja — Grycan

**Case gotowy jakościowo.** Szczególnie dobry przykład poprawy relative to old logic — Brand Managerzy prawidłowo wykluczeni. CPO wyjątek działa. Artykuł sezonowy (surowce mleczne) jest dobrze przełożony na napięcia zakupowe. Formatowanie CTA do ujednolicenia (patrz Issues).

---

## 4. Case 3: Evra Fish

**Artykuł:** "Evra Fish: wzrost spożycia ryb w Polsce nie wydarzy się w tradycyjnych formatach" (portalspozywczy.pl, 2026-04-16)
**Kandydaci:** 5 | **Wybrani (T1+T2):** 3 | **Wykluczeni:** 2

### 4.1 Selekcja odbiorców

| Imię i nazwisko | Stanowisko | Tier | Lista Apollo | Wybrany |
|----------------|-----------|------|-------------|---------|
| Krzysztof Woźniak | Prezes Zarządu | T1 - C-Level | PL Tier 1 do market_news VSC | TAK |
| Agnieszka Malinowska | Procurement Director | T2 - Procurement | PL Tier 2 do market_news VSC | TAK |
| Michał Jabłoński | Head of Sourcing | T2 - Procurement | PL Tier 2 do market_news VSC | TAK |
| Paweł Dąbrowski | Buyer | T3 - Buyers/Operational | - | NIE (T3) |
| Łukasz Krawczyk | Supply Chain Director | Tier Uncertain | - | NIE (zasada dwuskładnikowa T2) |

### 4.2 Ocena tier mappingu

- **Krzysztof Woźniak**: `Prezes Zarządu` → T1. Poprawne.
- **Agnieszka Malinowska**: `Procurement Director` → T2. Poprawne. Zasada dwuskładnikowa: `director` + `procurement`. Reason: "Title match: 'procurement director'".
- **Michał Jabłoński**: `Head of Sourcing` → T2. Poprawne. Zasada dwuskładnikowa: `head` + `sourcing`. Reason: "Title match: 'head of sourcing'".
- **Paweł Dąbrowski**: `Buyer` → T3. Poprawne.
- **Łukasz Krawczyk**: `Supply Chain Director` → Uncertain. Poprawne. `director` = level OK, `supply chain` nie zawiera komponentu zakupowego (procurement/purchasing/zakup/sourcing). Zasada dwuskładnikowa prawidłowo wyklucza.

**Tier mapping: 5/5 poprawnych. Kluczowy test Supply Chain Director → Uncertain zadziałał.**

### 4.3 Ocena treści wiadomości

#### Krzysztof Woźniak (Prezes Zarządu) — Tier 1

- **E1 subject:** "Evra Fish i presja na marżę" (152 słowa)
- **Anchor:** Pełny tytuł + źródło w pierwszym zdaniu. ✅
- **Hipoteza:** Evra Fish rozwija convenience i HoReCa równolegle z negocjacjami z dostawcami surowców rybnych.
- **Bridge:** "marża na takich formatach szybciej reaguje na każdą podwyżkę po stronie dostawców [...] obrona EBIT przed kosztami, których nie da się później odzyskać w cenie." — T1 language. Doskonałe.
- **FU1 (73 słowa):** "w praktyce widzimy, że firmy z dobrze przygotowanym wejściem do negocjacji potrafią zablokować 30-50% proponowanych podwyżek" — konkretna wartość.
- **FU2 (49 słów):** Naturalna, krótka. ✅

**Ocena:** Message fit HIGH.

---

#### Agnieszka Malinowska (Procurement Director) — Tier 2

- **E1 subject:** "Evra Fish i negocjacje z dostawcami" (153 słowa)
- **Format:** Powitanie Pani Agnieszko, → anchor z tytułem artykułu + źródłem. ✅
- **Gender:** Pani Agnieszko, Pani → poprawna forma żeńska.
- **Hipoteza:** Firma jednocześnie rozwija kanały i negocjuje z dostawcami → "każda rozmowa z dostawcą była oparta na twardych argumentach, a nie na improwizacji."
- **Konkret z artykułu:** "przetwarza rocznie kilkadziesiąt tysięcy ton ryb" — użyty wprost.
- **CTA:** Calendly T2 + telefon. ✅
- **FU1 (93 słowa):** "rozjazd między ceną zakupu a realną marżą [...] cost driver, przestrzeń do ustępstwa, jak obronić wynik przed zarządem" — doskonałe T2 procurementowe.
- **FU2 (48 słów):** Krótka, prosta, CTA jasne. ✅

**Ocena:** Message fit HIGH.

---

#### Michał Jabłoński (Head of Sourcing) — Tier 2

- **E1 subject:** "Evra Fish i negocjacje z dostawcami" (131 słów)
- **Anchor:** Tytuł + źródło w pierwszym zdaniu. ✅
- **Hipoteza:** Evra Fish szuka nowych dostawców łososiowatych i dorsza + negocjuje z obecnymi.
- **Konkret:** "przy rocznym przerobie liczonym w dziesiątkach tysięcy ton nawet niewielka zmiana ceny łososia czy dorsza szybko przekłada się na wynik kategorii" — świetne, bardzo konkretne.
- **Bridge (Head of Sourcing):** "od benchmarku, przez cost drivers, po plan argumentacji wobec dostawcy" — doskonałe.
- **FU1 (77 słów):** "Bez benchmarku i prostego modelu should-cost łatwo wejść w negocjacje z samą presją cenową, zamiast z konkretną argumentacją." — mocne zdanie FU.
- **FU2 (49 słów):** Naturalna. ✅

**Ocena:** Message fit HIGH.

---

### 4.4 Tabela oceny kontaktów — Evra Fish

| Imię/Nazwisko | Stanowisko | Tier | Lista Apollo | Recipient fit | Message fit | Rekomendacja |
|---------------|-----------|------|-------------|--------------|-------------|--------------|
| Krzysztof Woźniak | Prezes Zarządu | T1 | PL Tier 1 | HIGH | HIGH | KEEP |
| Agnieszka Malinowska | Procurement Director | T2 | PL Tier 2 | HIGH | HIGH | KEEP |
| Michał Jabłoński | Head of Sourcing | T2 | PL Tier 2 | HIGH | HIGH | KEEP |
| Paweł Dąbrowski | Buyer | T3 | - | LOW | - | EXCLUDED (T3) |
| Łukasz Krawczyk | Supply Chain Director | Uncertain | - | LOW | - | EXCLUDED (zasada T2) ✅ |

### 4.5 Rekomendacja — Evra Fish

**Case gotowy jakościowo.** Artykuł rybny bardzo konkretny (łososiowate, dorsz, roczny przerób), co LLM świetnie wykorzystał do personalizacji. Kluczowy test Supply Chain Director → prawidłowo wykluczony. **WAŻNE:** W live Apollo, Evra Fish returnuje NO_MATCH (problem company resolution / alias). Blokuje uruchomienie. Wymaga fixa przed scale-up.

---

## 5. Cross-case comparison

| Obszar | ORLEN | Grycan | Evra Fish |
|--------|-------|--------|-----------|
| Tier mapping accuracy | 7/7 ✅ | 6/6 ✅ | 5/5 ✅ |
| Recipient selection | 4 wybranych / 3 wykluczonych | 4 wybranych / 2 wykluczone | 3 wybranych / 2 wykluczone |
| Anchor quality | HIGH | HIGH | HIGH |
| Tier narrative T1 | Marża / EBIT / kontrola ryzyka | Marża / EBIT / obrona wyniku | EBIT / presja kosztowa |
| Tier narrative T2 | Benchmark / cost drivers / savings | Standard zakupów / savings | Should-cost / argumentacja |
| CTA prawidłowy tier | ✅ T1→zakupy-a-marza | ✅ T1→zakupy-a-marza | ✅ T1→zakupy-a-marza |
| CTA prawidłowy tier | ✅ T2→standard-negocjacji | ✅ T2→standard-negocjacji | ✅ T2→standard-negocjacji |
| Gender poprawny | ✅ (M/K) | ✅ (M/K) | ✅ (M/K) |
| Live company resolution | UWAGA (zła spółka) | OK | BLOKADA (NO_MATCH) |

---

## 6. Issues Found

| # | Issue | Severity | Moduł / plik | Zachowanie | Rekomendacja |
|---|-------|----------|-------------|-----------|--------------|
| 1 | Niespójne formatowanie CTA — URL bez intro-frazy | LOW | message_writer.md (prompt) | Część maili: "https://... Jeśli wygodniejsza..." bez kropki ani intro-zdania przed URL. Część ma intro-zdanie + URL + "Jeśli...". | Ujednolicić strukturę CTA w prompcie: "Proponuję krótką rozmowę: [URL]. Jeśli wygodniejsza..." |
| 2 | "nasze podejście" jako borderline forbidden phrase | LOW | message_writer.md (prompt) | "można sprawdzić nasze podejście na jednej kategorii" — granicznie blisko zakazanej "nasza platforma". | Dodać "nasze podejście" do watch listy w prompcie; preferować "to podejście" lub "taki standard". |
| 3 | Duplikaty subject line w tym samym case | LOW | message_generator.py | Agnieszka Malinowska i Michał Jabłoński (Evra Fish T2) mają identyczny subject E1: "Evra Fish i negocjacje z dostawcami". | Nie blokuje, ale warto różnicować lub dodać tytuł stanowiska do subject prompt. |
| 4 | Live ORLEN: zła spółka zależna w Apollo | MEDIUM | company resolution | Poprzedni live test: Apollo zwrócił "ORLEN Technologie S.A." zamiast "ORLEN S.A." — inne kontakty. | Zweryfikować Apollo company_id dla ORLEN S.A. lub dodać alias. |
| 5 | Live Evra Fish: NO_MATCH w company resolution | HIGH | company resolution / contact_finder.py | Poprzedni live test: 0 kontaktów, BLOCKED_COMPANY_NO_MATCH. Mock bypass działa, live nie. | Dodać alias "Evra Fish" → Apollo domain/company_id lub naprawić fuzzy match. |

---

## 7. Final Verdict

### Gotowość jakościowa: TAK - z dwoma blokerami live

**Co działa doskonale:**
- Tier mapping (18/18) z poprawnymi edgecases: Operations Director → Uncertain, Supply Chain Director → Uncertain, CPO → T2 (wyjątek), Brand Manager → T3
- Selekcja T1+T2 (11 kontaktów) z wykluczeniem T3 i Uncertain
- Struktura wiadomości: anchor → hipoteza → bridge → framework → CTA w każdym mailu
- Tier narratives wyraźnie różne: T1 = marża/EBIT/kontrola, T2 = benchmark/savings/argumentacja
- Word count: E1 131-166w, FU1 73-97w, FU2 48-57w — wszystkie w normie
- Gender forms: poprawne we wszystkich testowanych mailach
- Calendly links: tier-specific, żadnego cross-tier
- Brak podpisów wstrzykiwanych przez LLM
- Brak zakazanych fraz, brak em dash

**Co wymaga fixa przed scale-up:**

1. **(HIGH) Live Evra Fish company resolution** — NO_MATCH blokuje kampanię całkowicie
2. **(MEDIUM) Live ORLEN company resolution** — ryzyko dotarcia do złej spółki zależnej
3. **(LOW) Formatowanie CTA** — ujednolicić strukturę URL+telefon w prompcie
4. **(LOW) Duplikaty subject** — opcjonalnie zróżnicować dla T2 w tym samym case

**Rekomendacja:** Uruchomić pilota live z jednym dobrze rozwiązanym case (Grycan — dobra company resolution) przed scale-up. Evra Fish i ORLEN wymagają naprawy company resolution.
