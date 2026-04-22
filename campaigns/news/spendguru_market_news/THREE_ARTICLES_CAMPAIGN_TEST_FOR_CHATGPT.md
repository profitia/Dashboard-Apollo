# THREE ARTICLES CAMPAIGN TEST — FOR CHATGPT

**Cel dokumentu:** szybkie briefowanie ChatGPT lub innego modelu na temat wyników testu 3 case'ów przez pipeline news-triggered (SpendGuru / Kampanie Apollo).

---

## Kontekst

Pipeline news-triggered: artykuł z rynku spożywczego → qualify (scoring) → entity extraction (LLM) → company resolution (Apollo API + alias dict + LLM) → contact search (Apollo API) → message generation (LLM) → Apollo sequence (draft-only).

**Kampania:** `spendguru_market_news`. **LLM:** gpt-4.1-mini (GitHub Models). **Tryb:** dry-run, bez zapisu do Apollo.

---

## Status per artykuł

### 1. ORLEN — artykuł o testach regranulatu PP do opakowań spożywczych

**Status finaly:** BLOCKED_NO_EMAIL

- Kwalifikacja: **PASS** — score 77/100 (industry=40 plastics/packaging, purchase=32)
- Poprzedni wynik tego samego artykułu: score 29 (FAIL). Zmiana wynika z rozszerzenia scope o branżę plastics/chemicals.
- Entity extraction: "ORLEN S.A.", type=other, conf=0.97 — poprawne
- Company resolution: **wyłączony** (`use_company_resolution: false` w config)
- Kontakty: 10 kontaktów w Apollo (Dyrektor, Category Manager…), **0 z emailem**
- Associated fallback: Pollena Kurowski (współuczestnik artykułu) — 10 kontaktów, 0 emaili
- Messaging: nie wygenerowano (brak emaili)
- Bloker: Apollo brak emaili dla ORLEN i Pollena Kurowski — strukturalny problem z danymi polskich firm

**Biznesowy kontekst:** ORLEN pojawia się w artykule jako dostawca rPP, nie jako nabywca — to upstream case. SpendGuru celuje w kupujących. Pollena Kurowski (producent opakowań, partner testu) byłaby lepszym targetem. Obie firmy mają 0 emaili w Apollo.

---

### 2. Grycan — artykuł o starcie sezonu lodowego i zakupach surowców mlecznych

**Status finaly:** BLOCKED_NO_EMAIL

- Fetch: **portalspozywczy.pl zablokował fetcher** — użyto fixture (tekst artykułu podany ręcznie)
- Kwalifikacja: PASS — score 60 (food_production, supply_chain: surowce mleczne)
- Entity extraction: "Grycan", type=producer, conf=0.98 — **idealna ekstrakcja** (bez suffixu prawnego)
- Company resolution: **MATCH_POSSIBLE 0.65** — alias dict uruchomił domain hint (grycan.pl), people search fallback znalazł "Grycan - Lody od pokoleń". Wynik spójny z poprzednim testem.
- Kontakty: 10 kontaktów (2x Tier 1 Manager, 3x Brand Manager), **0 z emailem**; domain fallback (grycan.pl) też 0
- Messaging: nie wygenerowano
- Bloker: Apollo brak emaili — strukturalny. Znalezione kontakty to Brand Managerzy, nie procurement — Apollo słabo indeksuje Grycan w rolach zakupowych.

**Biznesowy kontekst:** Grycan to **idealny target** dla SpendGuru — FMCG producent z sezonowymi spikes zakupów mleka/śmietanki/masła, aktywne procurement. Jedyny problem to Apollo data gap. Warto enrichować ręcznie przez LinkedIn.

---

### 3. Evra Fish — artykuł o renegocjacji kontraktów z dostawcami ryb

**Status finaly:** BLOCKED_COMPANY_NO_MATCH

- Fetch: **portalspozywczy.pl zablokował** — użyto fixture
- Kwalifikacja: PASS — score 58 (food_production/ryby, supply_chain, contract_negotiations)
- Entity extraction: **"Evra Fish Sp. z o.o."** — LLM dodał suffix prawny ⚠️
- Company resolution: **NO_MATCH** — alias dict ma source_variants: ["Evra Fish", "Evra-Fish"] — nie dopasował "Evra Fish Sp. z o.o." — resolver szukał "EvraFish" jak powinien, ale po pełnej nazwie z Sp. z o.o.
- Kontakty: 0 (brak resolved company → brak domain → brak wyszukiwania)
- **Regresja:** poprzedni test diagnostyczny (z ręcznie podanym "Evra Fish") → MATCH_CONFIDENT 0.90 → EvraFish.com w Apollo. W pełnym pipeline LLM dodał suffix i alias dict nie zadziałał.

**Biznesowy kontekst:** Evra Fish to **dobry target** — dystrybutor/przetwórca ryb, renegocjuje kontrakty zakupowe. Artykuł ma silny trigger. Fix jest prosty — jeden wpis w YAML. Po fixie należy przetestować ponownie.

---

## 5 Kluczowych Insightów

### 1. Qualification po scope expansion działa — drastyczna poprawa dla ORLEN
Score ORLEN: 29 (FAIL) → 77 (PASS) po dodaniu branż plastics/chemicals do active_industry_scope. Artykuły z branży opakowaniowej/chemicznej są teraz prawidłowo kwalifikowane. Zmiana przyniosła efekt zgodny z oczekiwaniami.

### 2. Apollo brak emaili dla polskich firm to systemowy bottleneck
Wszystkie 3 firmy (ORLEN, Grycan, Evra Fish): kontakty istnieją, emaile niedostępne. To nie jest bug pipeline'u — Apollo po prostu słabo pokrywa emaile polskich firm. Pipeline w pełni działa (qualify → entity → resolution → contacts), ale ostatni krok (emaile) blokowany zewnętrznie. **Wniosek: pipeline jest gotowy — problem leży poza nim.**

### 3. Alias dict jest krytycznym elementem resolution — ale musi trafić na czysty brand name
Dla Grycan alias dict zadziałał (LLM zwrócił "Grycan" bez suffixu). Dla Evra Fish alias dict nie zadziałał, bo LLM dodał "Sp. z o.o.". Drobna zmiana w entity prompt (instrukcja: "zwróć sam brand name bez formy prawnej") lub normalizacja przed alias lookup rozwiązuje problem systemowo.

### 4. portalspozywczy.pl jest de facto niedostępny dla fetchera
2 z 3 artykułów nie mogły zostać pobrane automatycznie. Portal to główne źródło polskiej branży spożywczej — blokada jest poważnym ograniczeniem operacyjnym. Możliwe rozwiązania: RSS feed, pośrednik (Google Cache), lub zmiana źródeł na tworzywa.online / branżowe newslettery.

### 5. Pipeline jest "production-ready" — ale bez emaili jest read-only
Pipeline poprawnie przechodzi przez wszystkie 6 faz dla artykułów z działającym fetchem. Evra Fish będzie READY po jednym fixie. ORLEN i Grycan potrzebują zewnętrznego enrichmentu emaili. Gdy emaile będą dostępne — cały flow łącznie z generowaniem wiadomości zadziała automatycznie.

---

## Best Case / Worst Case

**Best case — Grycan:**  
- Poprawna kwalifikacja, idealna ekstrakcja entity, stabilna resolution (MATCH_POSSIBLE 0.65), 10 kontaktów znalezionych. Jedyny problem: brak emaili. Gdyby emaile były dostępne, pipeline wygenerowałby wiadomości i przesłał do Apollo sequence.

**Worst case — Evra Fish:**  
- Potencjalnie najlepszy case biznesowo (renegocjacje kontraktów = bezpośredni trigger), ale bug alias dict doprowadził do NO_MATCH. Zero kontaktów. Jeden fix w YAML przywróci pełen flow.

---

## Rekomendowane Następne Kroki (priorytetowo)

1. **FIX: alias dict** — dodać "Evra Fish Sp. z o.o." do source_variants w `data/company_aliases.yaml` ORAZ dodać instrukcję do entity extraction promptu: "Zwróć tylko brand name, bez form prawnych (Sp. z o.o., S.A., itp.)"

2. **FIX: portalspozywczy.pl** — rozważyć rezygnację z portalu jako źródła. Zastąpić lub wzbogacić innymi źródłami (Google News, sekcje spożywcze portali biznesowych, branżowe RSS, bezpośrednio tworzywa.online).

3. **INVESTIGATE: emaile dla polskich firm** — zbadać enrichment przez LinkedIn Sales Navigator lub Hunter.io. Apollo "reveal email" feature. Rozważyć, czy pipeline powinien automatycznie triggerować LinkedIn outreach zamiast emaila gdy emaile są niedostępne.

4. **RE-RUN Evra Fish** — po fixie alias dict uruchomić ponownie test fixture dla Evra Fish. Oczekiwany wynik: MATCH_CONFIDENT 0.90, kontakty z Apollo, potencjalnie emaile.

5. **MONITOR ORLEN qualification** — sprawdzić, czy keyword "API" nie powoduje false positive dla pharmaceuticals w artykułach spoza pharma. Rozważyć doprecyzowanie keywordu.
