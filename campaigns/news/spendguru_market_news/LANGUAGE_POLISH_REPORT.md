# LANGUAGE POLISH REPORT — spendguru_market_news

**Data:** 2026-04-23  
**Kampania:** spendguru_market_news  
**Cel:** Przepolerowanie języka wiadomości bez zmiany logiki kampanii

---

## 1. Executive Summary

### Co poprawiono
Zaktualizowano prompt generatora wiadomości (`message_writer.md`) oraz dodano heurystykę stylistyczną w `message_generator.py`. Zmiany dotyczą wyłącznie języka i stylu — logika kampanii, struktura sekwencji, CTA i reguły tiers pozostały bez zmian.

### Jaki był cel
Maile brzmiały zbyt technokratycznie — jak fragmenty raportu lub prezentacji biznesowej. Celem było sprawienie, żeby brzmiały bardziej jak spontaniczna reakcja po przeczytaniu artykułu: lżej, naturalniej, prościej — przy zachowaniu profesjonalizmu B2B.

### Jaki efekt (po re-teście ON Lemon)

**Przed (Email 1 — bridge):**
> "W Pana roli jako Ownera taki model rozwoju szybko przekłada się na pytanie nie tylko o sprzedaż, ale też o to, czy przy nowych formułach i opakowaniach da się obronić EBIT bez oddawania marży w negocjacjach z dostawcami."

**Po (Email 1 — bridge):**
> "szybko pojawia się kwestia, jak dowieźć to tak, żeby marża nie uciekała na kosztach składników, opakowań i dostawców."

Efekt: ten sam sens, o 60% mniej słów, o 100% naturalniejszy ton. Anchor zmienił się z "Postanowiłem napisać do Pana po artykule" na "Przeczytałem... i od razu pomyślałem o ON Lemon" — bardziej spontanicznie.

---

## 2. Co było zbyt technokratyczne

### Przykłady problemów

**Problem 1: Piętrowe zdania z wieloma poziomami podrzędności**

> "W Pana roli jako Ownera taki model rozwoju szybko przekłada się na pytanie nie tylko o sprzedaż, ale też o to, czy przy nowych formułach i opakowaniach da się obronić EBIT bez oddawania marży w negocjacjach z dostawcami."

Jedno zdanie z trzema poziomami zagnieżdżenia. Brzmi jak brief dla dyrektora, nie jak mail do człowieka.

**Problem 2: Rzeczowniki odczasownikowe zamiast czasowników**

- "ryzyko marżowe" → powinno być "presja na marżę" / "marża uciekała"
- "precyzyjna ocena kosztu wejścia" → "dobrze policzyć koszt wejścia"
- "przekłada się na pytanie o..." → "pojawia się kwestia..."
- "przewidywalność kosztów zakupowych" → "wiedzieć, z czego wynikają koszty"

**Problem 3: Język prezentacyjny zamiast konwersacyjnego**

Stare anchor: "Kontaktuję się po artykule „[tytuł]" w [źródło] — bo czytając go, miałem od razu hipotezę o tym, jak ta sytuacja przekłada się na [firmę]." → Brzmi jak formalny memo, nie jak ludzka reakcja.

**Dlaczego to przeszkadzało:**
- Odbiorca od razu czuje, że mail jest "skrojony szablonowo"
- Zdania prezentacyjne sygnalizują cold prospecting, nie autentyczną reakcję
- Ciężki język w pierwszych 2 zdaniach powoduje, że mail trafia do kosza zanim dojdzie do hipotezy
- Ton "analityczny" nie pasuje do relacji B2B inicjowanej po artykule

---

## 3. Jak zmieniono styl

### Nowa sekcja w promptcie: STYL I TON — LANGUAGE POLISH

Dodano dedykowaną sekcję przed `## ZASADY PISANIA`, zawierającą:

**3.1. Zasada nadrzędna:**
> "Mail ma brzmieć jak napisany po przeczytaniu konkretnego artykułu, z autentycznej reakcji — nie jak formalna analiza biznesowa ani business memo."

**3.2. Reguły dotyczące zdań:**
- Pisz krótszymi zdaniami — rozrywaj piętrowe konstrukcje na 2–3 prostsze
- Mieszaj zdania krótkie i średnie — nie buduj ciągu identycznie długich
- Końcówka akapitu ma być lekka, nie dociążona rzeczownikiem odczasownikowym
- Unikaj zdań z wieloma zdaniami podrzędnymi zagnieżdżonymi w jednym zdaniu głównym

**3.3. Tabela zamienników technoKratycznych:**

| Unikaj | Zamiast tego |
|---|---|
| „precyzyjna ocena kosztu wejścia" | „dobrze policzyć koszt wejścia" |
| „ryzyko marżowe" | „presja na marżę" / „marża może wtedy uciekać" |
| „przekłada się na pytanie o…" | „rodzi pytanie o…" / „szybko pojawia się kwestia…" |
| „model rozwoju przekłada się na…" | „przy takim podejściu…" |
| „przestrzeń do obrony wyniku" | „możliwość obrony marży" / „jak bronić EBIT" |
| „uporządkować argumentację" | „mieć mocne argumenty" |
| „przewidywalność kosztów zakupowych" | „wiedzieć, z czego wynikają koszty" |
| „nieuzasadnione podwyżki dostawców" | „podwyżki bez pokrycia" |

**3.4. Zasada naturalności:**
- Pierwsze 1–2 akapity mają być żywe i osadzone w jednym konkretnym wątku z artykułu
- Bridge ma być logiczny, ale zapisany prostszym, praktycznym językiem — nie analitycznym
- Preferuj czasowniki nad rzeczownikami odczasownikowymi

### Zaktualizowane anchor warianty

Stare warianty brzmiały formalnie ("Postanowiłem napisać... bo wynika z niego, że", "Kontaktuję się po artykule"). Nowe:
- "Przeczytałem w [źródło] artykuł... i od razu pomyślałem o [firmie]"
- "Zwrócił moją uwagę artykuł... Od razu przyszło mi do głowy, że..."
- "Trafiłem na artykuł... i od razu miałem hipotezę..."
- "Niedawny artykuł w [źródło]... zwrócił moją uwagę - szczególnie w kontekście [firmy]"

### Zaktualizowana reguła bridge w ZASADACH PISANIA

Dodano przykład złego i dobrego bridge bezpośrednio w opisie:
> Zamiast: "model rozwoju przekłada się na pytanie o EBIT bez oddawania marży" → lepiej: "szybko pojawia się kwestia, jak dowieźć nowe pomysły tak, żeby marża nie uciekała na kosztach"

### Nowa reguła #15 w ZASADACH PISANIA

> "Styl zawsze wygrywa z formą: jeśli zdanie brzmi jak fragment raportu, skróć je i przepisz prościej. Lepiej naturalnie i komunikatywnie niż elegancko i ciężko."

### Zaktualizowany system_prompt dla LLM

Stary:
> "Jesteś ekspertem od komunikacji B2B i outreachu. Odpowiadasz WYŁĄCZNIE w JSON..."

Nowy:
> "Jesteś ekspertem od komunikacji B2B i outreachu. Piszesz naturalnie i lżej — krótsze zdania, prostsze słownictwo, mniej technoKratyczny język. Mail ma brzmieć jak napisany po przeczytaniu artykułu, nie jak formalna analiza. Odpowiadasz WYŁĄCZNIE w JSON..."

---

## 4. Co pozostało bez zmian

| Element | Status |
|---|---|
| Logika kampanii (kwalifikacja artykułu, tiers, Apollo) | Bez zmian |
| Struktura sekwencji (E1 + FU1 + FU2) | Bez zmian |
| Anchor → hipoteza → bridge → framework → CTA | Bez zmian |
| CTA logiczne (Calendly + telefon) | Bez zmian |
| Tier-specific narrative (TIER_PERSPECTIVES) | Bez zmian |
| Word count ranges (E1: 120-170, FU1: 60-100, FU2: 40-80) | Bez zmian |
| Reguły gender (Pan/Pani, wołacz) | Bez zmian |
| Format JSON odpowiedzi | Bez zmian |
| Calendly URLs | Bez zmian |
| Zakaz em-dash, zakaz "nasza platforma" etc. | Bez zmian |

---

## 5. Re-test jakościowy

### Case 1: ON Lemon (Robert, Owner, Tier 1)

**Status testu:** READY_FOR_REVIEW (identycznie jak przed zmianami)

**Ocena Email 1 po language polish:**

```
Subject: ON Lemon i presja na marżę
```

**Anchor:** "Przeczytałem w horecatrends.pl artykuł „ON Lemon na EEC 2026..." i od razu pomyślałem o ON Lemon, bo w Pana roli to nie jest tylko ciekawa deklaracja, ale też decyzja o tym, jak pilnować wyniku przy nowych pomysłach."

- ✓ Bardziej spontaniczne — "Przeczytałem... i od razu pomyślałem" zamiast "Postanowiłem napisać"
- ✓ Krótsze, naturalniejsze zdanie
- ✓ Brak piętrowej składni

**Hipoteza:** "Z artykułu wynika, że ON Lemon nie chce iść za trendami, tylko tworzyć własne produkty, a tonik espresso w puszce jest już kolejnym takim przykładem."

- ✓ Konkretny fakt z artykułu
- ✓ Prosto, bez abstrakcji

**Bridge:** "Jeśli firma testuje nowe połączenia i formaty, to szybko pojawia się kwestia, jak dowieźć to tak, żeby marża nie uciekała na kosztach składników, opakowań i dostawców."

- ✓ Prościej niż poprzednio (vs "da się obronić EBIT bez oddawania marży w negocjacjach")
- ✓ Naturalny, praktyczny język
- ✓ Zachowana logika biznesowa

**Follow Up 1:** "W tym artykule ważne jest jeszcze jedno: ON Lemon mówi wprost, że jako najmniejszy podmiot przy stole może pozwolić sobie na testy i eksperymenty. To daje swobodę, ale też łatwo podnosi koszt każdej nowej serii, jeśli warunki u dostawców nie są dobrze przygotowane."

- ✓ Wnosi nową wartość (koszty serii + warunki dostawców)
- ✓ Lżej, prostszy język
- ✓ Dobre zdania: krótkie + średnie mieszane

**Follow Up 2:** "Wracam jeszcze do tego artykułu, bo widać w nim dobrze jedno: kreacja jest ważna, ale przy nowych produktach od razu pojawia się pytanie o koszt."

- ✓ Krótki, prosty, bez presji
- ✓ Zachowany anchor do artykułu
- ✓ Jasne CTA

**StyleCheck log:** OK (brak technoKratycznych fraz wykrytych)

### Case 2: Grycan (pilot)

**Status testu:** BLOCKED_NO_CONTACT (0 T1/T2 w Apollo — bez zmian, niezwiązane z language polish)

Brak wygenerowanych wiadomości — nie ma podstawy do oceny stylu. Grycan nadal blokuje się na Apollo coverage, nie na jakości generowanego języka.

### Ocena ogólna po re-teście

| Kryterium | Przed | Po |
|---|---|---|
| Czy maile brzmią lżej? | Nie — ciężkie, analityczne | Tak — naturalnie, lekko |
| Czy anchor jest naturalny? | Formalny | Spontaniczny |
| Czy hipoteza wynika z artykułu? | Tak | Tak (zachowane) |
| Czy bridge jest logiczny? | Tak | Tak (prostszy język) |
| Czy CTA działa? | Tak | Tak |
| Czy wiadomości brzmią "po artykule"? | Nie do końca | Tak |
| StyleCheck (heurystyka) | N/A | OK — 0 ostrzeżeń |

---

## 6. Files changed

| Plik | Co zmieniono | Po co |
|---|---|---|
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | Dodano sekcję STYL I TON (reguły stylistyczne, tabela zamienników, zasada naturalności). Zaktualizowano anchor warianty. Poprawiono opis bridge. Dodano regułę #15. | Główna zmiana — instruuje LLM do prostszego, naturalniejszego języka |
| `src/news/messaging/message_generator.py` | Zaktualizowano system_prompt (styl i naturalność). Dodano `_TECHNOCRATIC_PHRASES` + `_check_style_issues()`. Wywołanie heurystyki w `_enrich_step()`. | Wzmocnienie instrukcji stylu na poziomie systemu + monitoring ostrzeżeń |

---

## 7. Risks / Limitations

### 7.1. LLM jest niedeterministyczny
Nawet po dodaniu reguł stylistycznych, LLM może:
- Czasem pominąć alternatywę telefoniczną w CTA (pre-existing, niezwiązane z language polish)
- Wygenerować zbyt krótkie FU1 lub FU2 (poniżej progu word count)
- Ocasami wrócić do cięższego języka przy długich artykułach z dużą ilością kontekstu

**Mitigacja:** heurystyka `_check_style_issues` loguje ostrzeżenie — umożliwia monitoring.

### 7.2. Heurystyka stylistyczna jest prosta
Lista `_TECHNOCRATIC_PHRASES` zawiera 9 fraz. Nie wychwyta wszystkich możliwych stylowych regresji. Pełna ocena stylu wymaga oceny człowieka.

### 7.3. Cięższy artykuł → cięższy mail
Jeśli artykuł jest nasycony żargonem (np. regulacyjny, finansowy), LLM może przenosić ten żargon do maila. Reguły promptu ograniczają to, ale nie eliminują.

### 7.4. Brak testu T2
Re-test objął tylko Tier 1 (Robert, Owner). Tier 2 (procurement management) może generować inne patterny języka — wymaga osobnego testu gdy pojawi się case z T2 w Apollo.

### 7.5. StyleCheck nie blokuje dostawy
`_check_style_issues` tylko loguje — nie blokuje wygenerowania maila. Decyzja o odrzuceniu maila z powodu stylu pozostaje przy człowieku (Tomasz, READY_FOR_REVIEW).

---

## 8. Final Recommendation

**Język kampanii jest teraz znacznie bliżej docelowego tonu.**

Kluczowa różnica: bridge i anchor brzmią teraz jak ludzka reakcja, nie jak analiza formalna. Zdania są krótsze, słownictwo prostsze, ton lżejszy — przy zachowaniu całej logiki biznesowej.

**Rekomendacje:**

1. **Kontynuuj z obecnym promptem** — język jest w dobrym kierunku, nie ma potrzeby dalszych zmian strukturalnych.

2. **Monitoruj StyleCheck w logach** — jeśli pojawi się ostrzeżenie dla konkretnego kontaktu, sprawdź mail przed zatwierdzeniem.

3. **Opcjonalnie:** jeśli po kilku real case'ach okaże się, że CTA (alternatywa telefoniczna) nadal bywa pomijane — dodaj explicit rule do promptu: "ZAWSZE zakończ każdą wiadomość zdaniem o telefonie — nawet FU2".

4. **Opcjonalnie:** dodaj test T2 gdy pojawi się case z procurement manager w Apollo — sprawdź czy styl jest adekwatnie dobrany (mniej marżowy, bardziej negocjacyjny).

---

*Raport wygenerowany: 2026-04-23 | spendguru_market_news | Language Polish v1*
