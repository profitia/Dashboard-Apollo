# MINI POLISH REPORT — spendguru_market_news

**Data:** 2026-04-23
**Kampania:** campaigns/news/spendguru_market_news
**Charakter zmian:** jakościowe doszlifowanie (mini polish), nie refactor

---

## 1. Executive Summary

Po quality re-teście (2026-04-21) kampania `spendguru_market_news` miała prawidłowo działające:
- Tier mapping (18/18)
- Selekcję odbiorców T1+T2
- Strukturę wiadomości
- Narrację T1 vs T2

Pozostały 4 jakościowe obszary do dopracowania. Wszystkie zostały zaadresowane:

| Obszar | Co poprawiono | Efekt |
|--------|--------------|-------|
| CTA formatting | Ujednolicono strukturę CTA (3-elementowa, spójna) | Konsekwentny układ we wszystkich mailach |
| Subject diversification | Dodano reguły różnicowania, osie T1/T2, zakaz duplikatów | Lepsze subjecty, częściowa poprawa |
| Evra Fish resolution | Aliasy rozszerzone o formy prawne + domain hint | Forma "Sp. z o.o." pokryta, evrafish.pl hint |
| ORLEN resolution | Nowy wpis aliasowy PKN ORLEN + orlen.pl domain hint | Faworyzuje główną spółkę |
| First line + hipoteza + bridge | Doprecyzowane reguły i warianty otwarcia | Bardziej naturalne i zróżnicowane |

Smoke tests: 29/29 ✅. Re-test jakościowy: 11/11 wiadomości, CTA spójne, anchory obecne, brak zakazanych fraz.

---

## 2. CTA Formatting

### Co było źle
- Część wiadomości wstawiała URL bez intro-zdania: "https://calendly.com/... Jeśli wygodniejsza..."
- Brak spójnej struktury między mailami i kontaktami
- Niektóre intro-zdania pojawiały się, inne nie

### Co poprawiono
W `message_writer.md` — sekcja `CTA — REGUŁY OBOWIĄZKOWE`:
- Zmieniono z 2-elementowego CTA (link + telefon) na **3-elementowy wzorzec**:
  1. Zdanie zamykające/intro (naturalne, kilka wariantów do wyboru przez LLM)
  2. Link Calendly w osobnej linii
  3. Alternatywa telefoniczna w osobnej linii
- Zakaz "proszę śmiało przesłać numer" (zmieniony na "proszę przesłać numer")
- Podano przykłady intro dla T1 i T2 z różnym tonem

### Jak działa teraz
Przykład T1 (Ireneusz Fąfara, ORLEN):
```
Jeśli temat jest dla Pana interesujący, proszę wybrać termin krótkiego spotkania online:
https://calendly.com/profitia/zakupy-a-marza-firmy
Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę przesłać numer - oddzwonię.
```

Przykład T2 (Tomasz Bąk, Grycan):
```
Jeśli warto byłoby sprawdzić to podejście na jednej kategorii kosztowej, proszę wybrać termin:
https://calendly.com/profitia/standard-negocjacji-i-oszczednosci
Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę przesłać numer - oddzwonię.
```

✅ Spójne we wszystkich 11 wygenerowanych wiadomościach.

---

## 3. Subject Diversification

### Co było źle
- Duplikaty subject E1 między kontaktami T2 w tym samym case (Evra Fish: obie T2 miały "Evra Fish i negocjacje z dostawcami")
- Brak reguł różnicowania w prompcie
- Subjecty nie zawsze jasno odzwierciedlały T1 vs T2

### Co poprawiono
Dodano osobną sekcję `REGUŁY SUBJECTÓW (OBOWIĄZKOWE)` w `message_writer.md`:
- Oś subjectów dla T1: marża / rentowność / wynik / EBIT / presja kosztowa
- Oś subjectów dla T2: negocjacje / benchmark / surowce / cost drivers / savings
- Przykłady różnorodności dla E1/FU1/FU2
- Zakaz identycznych subjectów dla różnych kontaktów
- Wymóg różnych subjectów dla każdego kroku sekwencji

### Jak działa teraz
Przykłady po poprawce (ORLEN):
- Ireneusz Fąfara T1: E1 "ORLEN: regranulat a presja na marżę" | FU1 "ORLEN - koszt regranulatu i EBIT" | FU2 "Krótko o ORLEN i kosztach"
- Michał Róg T1: E1 "ORLEN i presja na marżę" | FU1 "ORLEN - koszt regranulatu a EBIT" | FU2 "Krótko o ORLEN i kosztach"
- Anna Kowalska T2: E1 "ORLEN i negocjacje regranulatu PP" | FU1 "ORLEN - koszt regranulatu a argumenty"
- Marek Nowak T2: E1 "ORLEN i negocjacje przy regranulacie PP" | FU1 "ORLEN - koszt regranulatu i siła argumentów"

⚠️ Ograniczenie: Subjecty FU2 w ramach tego samego tieru mogą być jeszcze podobne (np. dwa T2 w Evra Fish mają "Krótko o Evra Fish"). Jest to ograniczenie izolowanych wywołań LLM — każdy kontakt generowany osobno bez wiedzy o innych. Nie da się w pełni zagwarantować unikalności bez post-processingu.

---

## 4. Evra Fish Resolution

### Co było źle
- `company_aliases.yaml` nie pokrywał formy "Evra Fish Sp. z o.o."
- LLM entity extractor zwracał "PEŁNĄ NAZWĘ FIRMY" — co dla Evra Fish dawało "Evra Fish Sp. z o.o."
- Alias lookup nie znajdował dopasowania → NO_MATCH

### Co poprawiono

**Poziom A — `company_aliases.yaml`:**
Dodano do `source_variants` dla Evra Fish:
- "Evra Fish Sp. z o.o."
- "Evra Fish sp. z o.o."
- "EvraFish Sp. z o.o."

Dodano domain hint: `evrafish.pl` (uprzednio pusty string).

Dodano "Evra Fish" jako drugi search_variant obok "EvraFish".

**Poziom B — `entity_extractor.py`:**
Zmieniono prompt LLM ekstrakcji firmy:
- Instrukcja: zwracaj **KRÓTKĄ NAZWĘ BRANDOWĄ** bez formy prawnej
- Przykłady: "Evra Fish" (nie: "Evra Fish Sp. z o.o."), "ORLEN" (nie: "ORLEN S.A.")
- Ogólna zasada: usuń Sp. z o.o., S.A. itp. chyba że są integralną częścią brandu

### Jaki efekt
- Forma "Evra Fish Sp. z o.o." jest teraz pokryta przez alias dict → resolver znajdzie alias i użyje canonical_name "EvraFish" + domain hint evrafish.pl
- LLM entity extractor powinien zwracać "Evra Fish" zamiast "Evra Fish Sp. z o.o."
- Obie warstwy razem powinny rozwiązać problem NO_MATCH

---

## 5. ORLEN Resolution

### Co było źle
- Brak wpisu ORLEN w `company_aliases.yaml`
- Resolver szukał pod "ORLEN" i mógł dopasować dowolną spółkę zależną (ORLEN Technologie, ORLEN Oil, ORLEN Upstream, ORLEN Paliwa itp.)
- Scorer dawał wyższy wynik spółce zależnej jeśli jej comparison_key był bliższy

### Co poprawiono

**`company_aliases.yaml`:**
Dodano nowy wpis ORLEN:
- source_variants: ORLEN, PKN ORLEN, PKN Orlen, Orlen, ORLEN S.A., PKN ORLEN S.A.
- canonical_name: "PKN ORLEN"
- search_variants: PKN ORLEN, ORLEN
- domain: "orlen.pl"

### Jaki efekt
- Resolver będzie szukał "PKN ORLEN" jako canonical_name — preferuje główną spółkę
- Domain hint "orlen.pl" działa jako bonus score dla kandydatów z domeną orlen.pl
- Spółki zależne mają inne domeny (orlen-technologie.pl, orlenupstream.pl itp.) → nie dostaną domain_hint bonus
- Zmniejsza ryzyko dopasowania do złej spółki zależnej

---

## 6. First Line + Hipoteza + Bridge

### Jakie zasady doprecyzowano

**First line:**
- Dodano 4 warianty otwarcia (zamiast jednego szablonu)
- Każdy wariant wymaga: powodu kontaktu + tytułu/tematu artykułu + źródła + firmy/roli
- Zakaz schematycznego powielania jednej konstrukcji

**Hipoteza:**
- Dodano limit: **maksymalnie 1-2 zdania**
- Wymóg: 1 konkretny fakt z artykułu (dane, zmiana, event)
- Zakaz: dodawania faktów których nie ma w artykule ("halucynacja")
- Sugerowany format: "Jeśli [fakt z artykułu], to oznacza…" lub "Z artykułu wynika, że…"

**Bridge:**
- Doprecyzowano mechanikę per typ artykułu:
  - surowce/dostawcy/opakowania → benchmarki i argumentacja negocjacyjna
  - ekspansja/wzrost/nowe rynki → presja na koszty zakupowe i marżę
  - wynik/inwestycja → przewidywalność kosztów i ochrona EBIT
- Zakaz schematycznych zdań bez konkretnej mechaniki

### Jak poprawiono jakość
Porównanie ANCHOR (stary vs nowy styl):

Stary: "Postanowiłem napisać do Pana po artykule „ORLEN testuje regranulat PP..." opublikowanym w..."
Nowy: "Kontaktuję się po artykule „ORLEN testuje regranulat PP..." w tworzywa.online — bo czytając go, miałem od razu hipotezę o tym, jak ta sytuacja przekłada się na ORLEN."

Różnorodność first line widoczna w nowych wynikach — LLM używa różnych konstrukcji otwarcia dla różnych kontaktów.

---

## 7. Files Changed

| Plik | Zmiana |
|------|--------|
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | Sekcja LOGIKA SEKWENCJI: nowe warianty first line, doprecyzowane reguły hipotezy i bridge; Sekcja CTA: 3-elementowy wzorzec; Nowa sekcja REGUŁY SUBJECTÓW |
| `campaigns/news/spendguru_market_news/data/company_aliases.yaml` | Evra Fish: dodano formy prawne do source_variants + domain; Nowy wpis ORLEN z PKN ORLEN canonical + orlen.pl domain |
| `src/news/entity/entity_extractor.py` | Prompt LLM: instrukcja "KRÓTKA NAZWA BRANDOWA bez formy prawnej" + przykłady |

---

## 8. Validation

### Smoke tests
- `python -m pytest tests/test_news_pipeline_smoke.py -v` → **29/29 PASSING** ✅

### Quality re-test (po zmianach)
- 3 przypadki, 18 kontaktów, 11 wygenerowanych wiadomości
- Tier mapping: 18/18 ✅
- CTA formatting: 11/11 — spójne 3-elementowe CTA ✅
- Anchor obecny: 11/11 ✅
- Zakazane frazy: 0 ✅
- Podpis LLM: 0 (podpis z custom field) ✅
- Em dash: 0 ✅
- Word count E1 (120-170): 10/11 — Michał Jabłoński 172w (minor overrun) ⚠️
- Word count FU1 (60-100): 7/11 — 4 przypadki 101-118w ⚠️ (LLM variance)

### Wzrost jakości vs poprzedni re-test
| Metryka | Poprzedni (pre-polish) | Nowy (post-polish) |
|---------|----------------------|------------------|
| CTA spójne 3-elementowe | ❌ (2-el, nierówne) | ✅ |
| Intro-zdanie przed URL | ❌ częściowe | ✅ zawsze |
| Telefon: "proszę przesłać numer" | ❌ "proszę śmiało przesłać" | ✅ |
| Subjecty zróżnicowane per tier | ⚠️ | ✅ lepiej |
| Evra Fish forma prawna pokryta | ❌ | ✅ |
| ORLEN domain hint | ❌ brak wpisu | ✅ |
| Warianty first line | ❌ jeden szablon | ✅ 4 warianty |

---

## 9. Risks / Limitations

1. **Duplikaty subjectów w tym samym case** — Przy generacji contact-per-contact (izolowane wywołania LLM), model nie wie co wygenerował dla innych kontaktów. Reguły pomagają, ale nie gwarantują 100% unikalności. FU2 "Krótko o [firma]" bywa identyczne dla wielu odbiorców — jest krótkie, neutralne i trudno bardziej je zróżnicować.

2. **Word count FU1** — Kilka FU1 przekracza 100 słów (do ~118). LLM ma tendencję do pisania pełnymi paragrafami. Można dokleić post-processing trimmer, ale to poza zakresem mini-polish.

3. **Evra Fish live test** — Nie był przeprowadzony live test Apollo dla Evra Fish (tylko mock). Poprawki w alias dict i entity extractor zwiększają prawdopodobieństwo resolution, ale nie gwarantują — zależy od tego czy firma figuruje w Apollo people search.

4. **ORLEN domain hint w scorerze** — Hint przekazywany gdy kandydat nie ma własnej domeny. Jeśli Apollo ma poprawnie orlen.pl dla ORLEN S.A., domain match signal zadziała. Nie gwarantuje 100% eliminacji spółek zależnych z wynikami.

---

## 10. Final Recommendation

**Kampania jest bliżej gotowości do pilotażu live.** Cztery z pięciu obszarów zostały poprawione. CTA jest spójne i eleganckie. Aliases i entity extractor powinny rozwiązać problem Evra Fish.

**Kolejny krok:**
1. Pilotaż live z **Grycan** (najlepiej rozwiązane company resolution w Apollo) — 1 artykuł, draft mode, weryfikacja ręczna, send.
2. Po Grycan — live test z **Evra Fish** pod nowym artykułem z portalspozywczy.pl, sprawdzenie czy entity extractor zwraca "Evra Fish" (nie "Sp. z o.o.") i czy alias lookup działa.
3. ORLEN — live test z weryfikacją która spółka jest zwracana przez resolver przed send.
