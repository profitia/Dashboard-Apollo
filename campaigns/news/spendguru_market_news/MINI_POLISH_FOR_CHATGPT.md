# MINI POLISH — Summary for ChatGPT

**Data:** 2026-04-23
**Kampania:** spendguru_market_news
**Pipeline:** artykuł → entity extractor → company resolver → contact finder → message writer → QA

---

## Co zostało poprawione (5 obszarów)

### 1. CTA — ujednolicona struktura
**Problem:** Nierówna struktura CTA między mailami — część miała intro-zdanie przed linkiem Calendly, część nie.

**Fix:** Zmieniono prompt `message_writer.md` na obowiązkowy 3-element wzorzec:
1. Zdanie zamykające (np. "Jeśli temat jest dla Pana interesujący, proszę wybrać termin:")
2. Link Calendly (osobna linia)
3. "Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę przesłać numer - oddzwonię." (osobna linia)

**Status:** ✅ Działa. Wszystkie 11 wiadomości w re-teście mają spójną 3-elementową strukturę CTA.

---

### 2. Subject diversification
**Problem:** Duplikaty subjectów dla różnych kontaktów tego samego tieru (np. Evra Fish T2: obie kontakt miały "Evra Fish i negocjacje z dostawcami").

**Fix:** Dodano sekcję `REGUŁY SUBJECTÓW` w prompcie:
- Oś T1: marża / rentowność / EBIT / presja kosztowa
- Oś T2: negocjacje / benchmark / surowce / cost drivers
- Zakaz identycznych subjectów, wymóg różnych subjectów E1/FU1/FU2

**Status:** ⚠️ Częściowa poprawa. Subjecty są bardziej zróżnicowane i kontekstowe, ale mogą być jeszcze podobne gdy dwa kontakty tego samego tieru trafiają na analogiczną hipotezę. Pełna unikalność wymaga post-processingu (poza zakresem).

---

### 3. Evra Fish resolution
**Problem:** Resolver zwracał NO_MATCH. Powód: LLM entity extractor zwracał "Evra Fish Sp. z o.o." (forma prawna), co nie trafiało na alias lookup (mający tylko "Evra Fish" i "Evra-Fish").

**Fix dwa-warstwowy:**
- **Warstwa A (alias dict):** Dodano "Evra Fish Sp. z o.o.", "Evra Fish sp. z o.o.", "EvraFish Sp. z o.o." do source_variants. Dodano domain hint `evrafish.pl`. Dodano "Evra Fish" jako search_variant.
- **Warstwa B (entity extractor prompt):** Zmieniono instrukcję LLM — ma zwracać KRÓTKĄ NAZWĘ BRANDOWĄ (bez formy prawnej), z przykładami: "Evra Fish" (dobrze) vs "Evra Fish Sp. z o.o." (źle).

**Status:** ✅ Obie warstwy naprawione. Live test z artykułem Evra Fish pokaże efekt.

---

### 4. ORLEN resolution
**Problem:** Brak wpisu w alias dict → resolver mógł dopasować dowolną spółkę zależną ORLEN (Technologie, Oil, Upstream, Paliwa).

**Fix:** Nowy wpis ORLEN w `company_aliases.yaml`:
- canonical_name: "PKN ORLEN"
- domain hint: "orlen.pl"
- Pokrywa warianty: ORLEN, PKN ORLEN, PKN Orlen, ORLEN S.A. itd.

**Status:** ✅ Dodane. Domain hint "orlen.pl" faworyzuje główną spółkę w scorerze (spółki zależne mają inne domeny).

---

### 5. First line + hipoteza + bridge
**Problem:** Zbyt schematyczne otwarcia first line, zbyt ogólna hipoteza (brak limitu zdań, ryzyko halucynacji), bridge mało article-specific.

**Fix:**
- 4 warianty otwarcia (Postanowiłem napisać / Zwrócił moją uwagę / Po lekturze / Kontaktuję się)
- Hipoteza: max 1-2 zdania, 1 fakt z artykułu, zakaz dodawania faktów spoza artykułu
- Bridge: różna mechanika zależna od typu artykułu (surowce → negocjacje; ekspansja → presja marży; wyniki → EBIT)

**Status:** ✅ Różnorodność otwarcia widoczna w nowych wiadomościach.

---

## Wyniki re-testu

| Metryka | Wynik |
|---------|-------|
| Smoke tests | 29/29 ✅ |
| Tier mapping | 18/18 ✅ |
| Wiadomości wygenerowane | 11/11 ✅ |
| CTA 3-elementowe | 11/11 ✅ |
| Anchor present | 11/11 ✅ |
| Zakazane frazy | 0 ✅ |
| Em dash | 0 ✅ |
| E1 word count OK | 10/11 (1x 172w) |
| FU1 word count OK | 7/11 (4x 101-118w) |

---

## Co nadal warto poprawić (poza zakresem mini-polish)

1. **Word count FU1** — kilka przekracza 100w. Można dodać post-processing trimmer.
2. **Subject uniqueness** — pełna gwarancja wymaga batch-generation albo post-processing deduplication.
3. **Live test Evra Fish / ORLEN** — testy tylko na mockach. Live Apollo pokaże rzeczywisty efekt resolution.

---

## Pliki zmienione

| Plik | Zmiana |
|------|--------|
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | CTA 3-el, warianty first line, hipoteza limit, bridge guidance, REGUŁY SUBJECTÓW |
| `campaigns/news/spendguru_market_news/data/company_aliases.yaml` | Evra Fish formy prawne + domain; nowy ORLEN z PKN ORLEN + orlen.pl |
| `src/news/entity/entity_extractor.py` | Prompt LLM: preferuj krótką nazwę brandową bez formy prawnej |

---

## Rekomendacja dalszych kroków

1. **Pilotaż live — Grycan** → Artykuł z portalspozywczy.pl o Grycan, draft mode, weryfikacja ręczna, send do 1-2 kontaktów. Grycan ma najlepiej rozwiązaną resolution (domena grycan.pl, Apollo org widoczny).
2. **Live test — Evra Fish** → Sprawdź czy entity extractor zwraca "Evra Fish" (nie formę prawną) i czy resolver trafia na alias.
3. **Live test — ORLEN** → Sprawdź która spółka zwracana. Jeśli zależna — przejrzyj log scorera i dostosuj.
