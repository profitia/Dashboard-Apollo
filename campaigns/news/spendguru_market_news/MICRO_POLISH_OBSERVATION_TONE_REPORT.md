# MICRO POLISH OBSERVATION TONE REPORT — spendguru_market_news

**Data:** 2026-04-23  
**Kampania:** spendguru_market_news  
**Typ zmiany:** Mikro-polish tonu obserwacji — bez zmiany architektury wiadomości

---

## 1. Executive Summary

### Co poprawiono
Wprowadzono zmianę tonu hipotezy i pierwszych akapitów: od stylu referującego artykuł ("Z artykułu wynika, że...") do stylu osobistej obserwacji po lekturze ("Zwróciłem uwagę w tym artykule na to, że...").

### Po co
Po pierwszym language polish wiadomości brzmiały już lżej i naturalniej. Pozostał jednak jeden wzorzec językowy, który sygnalizował "automat": hipoteza zapisana jak wniosek z dokumentu, nie jak myśl człowieka, który przeczytał artykuł. To drobna różnica w sformułowaniu, ale duża w odczuciu.

### Jaki efekt

**Email 1 — hipoteza przed:**
> "Z artykułu wynika, że ON Lemon nie chce iść za trendami, tylko tworzyć własne produkty, a tonik espresso w puszce jest już kolejnym takim przykładem."

**Email 1 — hipoteza po:**
> "Zwróciłem uwagę w tym artykule na to, że ON Lemon stawia na kreowanie, a nie podążanie za trendem, i że cztery lata temu powstał u Was tonik espresso w puszce."

Ten sam fakt. Ta sama informacja. Całkowicie inny ton — bardziej ludzki, bardziej "po przeczytaniu".

---

## 2. Problem przed zmianą

### Gdzie język był zbyt raportowy

**Email 1 — hipoteza:**

Formuła "Z artykułu wynika, że..." sygnalizuje: ktoś to przeanalizował, nie ktoś to zauważył. To ton referatu, nie obserwacji. W kontekście cold maila (nawet eleganckiego) brzmi jak wklejona analiza, nie jak autentyczna reakcja.

**Follow Up 1 — nawiązanie:**

Stara logika FU1 nie miała reguły dotyczącej tonu nawiązania do artykułu — domyślnie LLM wracał do konstrukji "Artykuł wskazuje też, że..." lub podobnych.

**Follow Up 2 — nawiązanie:**

Podobnie — brak reguły powodował powrót do formalnych nawiązań do "materiału".

### Przykłady problematycznych fraz (przed zmianą)

| Fraz | Typ problemu |
|---|---|
| „Z artykułu wynika, że…" | Raportowy wniosek, nie ludzka obserwacja |
| „Artykuł pokazuje, że…" | Analiza dokumentu, nie refleksja po lekturze |
| „W artykule opisano…" | Formalne referowanie, bezosobowe |
| „Z tekstu wynika…" | Jak z raportu analitycznego |
| „Materiał wskazuje na…" | Akademickie, nie B2B outreach |

### Dlaczego to przeszkadzało

Odbiorca na poziomie wyczucia — nawet bez analizy — identyfikuje styl raportowania jako sygnał masowego, automatycznego mailingu. Osobista obserwacja ("zwróciłem uwagę") buduje wrażenie autentyczności i konkretnego impulsu do kontaktu.

---

## 3. Jak zmieniono prompt / generator

### 3.1. message_writer.md — hipoteza (Email 1)

**Zmieniono:** opis dopuszczalnej formy hipotezy.

**Stara reguła:**
> Forma: "Jeśli [fakt z artykułu], to oznacza to, że…" lub "Z artykułu wynika, że…"

**Nowa reguła:**
- Ton osobistej obserwacji, NIE raportowy
- ZAKAZANE: „Z artykułu wynika, że…", „Artykuł pokazuje, że…", „W artykule opisano…", „Z tekstu wynika…"
- PREFEROWANE: „Zwróciłem uwagę w tym artykule na to, że…", „Uderzyło mnie to, że…", „Czytając ten materiał, zwróciłem uwagę, że…", „Pomyślałem od razu, że jeśli [fakt], to…"
- Cel: hipoteza ma brzmieć jak myśl nadawcy po lekturze, nie jak wniosek z analizy dokumentu

### 3.2. message_writer.md — STYL I TON (nowa podsekcja)

Dodano nową podsekcję: **„Ton obserwacji — NIE raportowania (KLUCZOWA ZASADA)"**

Zawiera:
- Listę ZAKAZANYCH form referujących (5 wzorców)
- Listę PREFEROWANYCH form obserwacyjnych (6 przykładów)
- Ograniczenia tonu (nie: "zainspirowało mnie", nie: zbyt wiele "ja", nie: mail o nadawcy)

### 3.3. message_writer.md — Follow Up 1

Dodano tone guidance dla nawiązania do artykułu:
- ZAKAZANE: „Z artykułu wynika również…", „Artykuł wskazuje też, że…"
- PREFEROWANE: „W tym artykule ważne jest jeszcze jedno:", „Wracając do tego artykułu — zwróciłem uwagę jeszcze na jeden wątek:", „Jeden konkretny wątek z tego artykułu, który mnie uderzył:"

### 3.4. message_generator.py — _TECHNOCRATIC_PHRASES

Rozszerzono listę monitorowanych fraz o 5 wzorców raportowych:
```python
"z artykułu wynika, że",
"artykuł pokazuje, że",
"w artykule opisano",
"z tekstu wynika",
"materiał wskazuje na",
```

### 3.5. message_generator.py — system_prompt

Zaktualizowano system_prompt LLM o explicit zakaz i preferowane formy:

> "KLUCZOWE: hipoteza i pierwsze akapity mają brzmieć jak osobista obserwacja po lekturze — NIE jak raport. ZAKAZANE: 'Z artykułu wynika, że', 'Artykuł pokazuje, że', 'Z tekstu wynika', 'W artykule opisano'. PREFEROWANE: 'Zwróciłem uwagę na to, że', 'Uderzyło mnie, że', 'Czytając ten artykuł, zwróciłem uwagę, że'."

---

## 4. Jaki jest efekt po zmianie

### Czy ton jest bardziej osobisty?

**Tak.** Wszystkie 3 wiadomości w re-teście (ON Lemon, Robert, Owner) mają ton obserwacyjny:

- Email 1: "Zwróciłem uwagę w tym artykule na to, że..." ✓
- Follow Up 1: "Wracając do tego artykułu - zwróciłem uwagę jeszcze na jeden wątek:" ✓
- Follow Up 2: "Jeden wątek z tego artykułu od razu zwrócił moją uwagę:" ✓

### Czy nadal jest profesjonalny?

**Tak.** Ton obserwacyjny nie przekroczył granicy w stronę potoczności ani emocjonalności. Nie pojawiło się "zainspirowało mnie", "zafascynowało mnie". Mail nadal jest elegancki i biznesowy.

### Czy wiadomość nadal jest logiczna?

**Tak.** Anchor → hipoteza → bridge → framework → CTA zachowane bez zmian. Logika biznesowa (kreacja → koszt → marża) nie naruszona.

### StyleCheck

**0 ostrzeżeń** — żadna z monitorowanych fraz (technokratycznych ani raportowych) nie pojawiła się w wygenerowanych wiadomościach.

---

## 5. Mikro re-test

### ON Lemon — Robert (Owner, Tier 1)

**Status:** READY_FOR_REVIEW (bez zmian)

**Pełne wiadomości po micro-polish:**

**Email 1 — "ON Lemon i presja na marżę"** (porównanie przed/po kluczowych fragmentów)

| Element | Przed micro-polish | Po micro-polish |
|---|---|---|
| Anchor | "Przeczytałem w horecatrends.pl artykuł..." | "Postanowiłem napisać do Pana po artykule... - od razu pomyślałem o ON Lemon..." |
| Hipoteza | "Z artykułu wynika, że ON Lemon nie chce iść za trendami..." | "Zwróciłem uwagę w tym artykule na to, że ON Lemon stawia na kreowanie..." |
| Bridge | "szybko pojawia się kwestia, jak dowieźć to tak, żeby marża nie uciekała..." | "łatwo o sytuację, w której dobry pomysł zaczyna przegrywać z kosztem surowców..." |
| Ocena | Dobry, ale hipoteza raportowa | Dobry, hipoteza obserwacyjna ✓ |

**Follow Up 1 — "ON Lemon - koszt pomysłu i marża"**

> "Wracając do tego artykułu - zwróciłem uwagę jeszcze na jeden wątek: skoro ON Lemon daje sobie przestrzeń na testy i eksperymenty, to rośnie znaczenie tego, jak szybko widać koszt takiego pomysłu po stronie zakupów."

- ✓ Obserwacyjny ton ("zwróciłem uwagę jeszcze na jeden wątek")
- ✓ Nowa wartość (koszt testów i eksperymentów)
- ✓ Naturalne

**Follow Up 2 — "Krótko o ON Lemon"**

> "Jeden wątek z tego artykułu od razu zwrócił moją uwagę: u Was chodzi o kreowanie, nie o bieganie za trendem. W praktyce przy zakupach oznacza to jedno - dobrze mieć z góry policzone, gdzie marża może uciekać."

- ✓ Obserwacyjny ("od razu zwrócił moją uwagę")
- ✓ Krótki, prosty, bez presji
- ✓ Dobry one-liner na zamknięcie

### Ocena porównawcza: 3 iteracje language polish

| Iteracja | Co zmieniano | Efekt |
|---|---|---|
| v0 (przed polish) | — | Ciężki, technokratyczny, raportowy |
| v1 (Language Polish) | Krótsze zdania, prostsze słownictwo, lżejszy bridge | Dużo lepiej — lżej, naturalniej |
| v2 (Micro Polish — obserwacja) | Hipoteza obserwacyjna, zakazane formy raportowe | Jeszcze bardziej ludzko — "czytałem i zwróciłem uwagę" |

---

## 6. Files changed

| Plik | Co zmieniono | Po co |
|---|---|---|
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | Zaktualizowano hipotezę (zakazane/preferowane formy). Dodano podsekcję STYL I TON → „Ton obserwacji". Dodano tone guidance dla FU1. | Instruuje LLM, by używał tonu obserwacyjnego, nie raportowego |
| `src/news/messaging/message_generator.py` | Rozszerzono `_TECHNOCRATIC_PHRASES` o 5 wzorców raportowych. Zaktualizowano system_prompt o explicit zakaz i preferowane formy. | Wzmocnienie na poziomie systemu + monitoring ostrzeżeń |

---

## 7. Final Recommendation

**Tak — to jest bliżej docelowego tonu.**

Wszystkie 3 wiadomości w re-teście (Email 1, FU1, FU2) mają teraz ton osobistej obserwacji po lekturze artykułu. Nie ma już "Z artykułu wynika". Nie ma "Artykuł pokazuje". Jest: "Zwróciłem uwagę", "Jeden wątek od razu zwrócił moją uwagę", "Wracając do tego artykułu".

To właśnie jest docelowy ton: odbiorca czuje, że ktoś przeczytał konkretny artykuł i pomyślał o jego sytuacji — nie że dostał wygenerowany mail na podstawie słów kluczowych.

**Kampania po obu iteracjach language polish jest gotowa do live use** — jeśli pojawi się artykuł z dobrym purchase signal dla firmy z T1/T2 coverage w Apollo.

---

*Raport wygenerowany: 2026-04-23 | spendguru_market_news | Micro Polish Observation Tone v1*
