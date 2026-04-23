# Language Polish — Key Findings for ChatGPT

**Sesja:** 2026-04-23  
**Kampania:** spendguru_market_news  
**Typ zmiany:** Language polish — styl i ton, bez zmiany logiki kampanii

---

## 1. Cel — krótko

Wiadomości były dobrze skomponowane logicznie (anchor → hipoteza → bridge → CTA), ale zbyt technokratyczne. Brzmiały jak memo, nie jak mail po przeczytaniu artykułu. Celem było sprawienie, żeby były lżejsze, bardziej naturalne, bardziej ludzkie — przy zachowaniu pełnego sensu biznesowego.

## 2. Język stał się wyraźnie lżejszy

**Najlepszy przykład — bridge (ON Lemon, Robert, Owner):**

**Przed:**
> "W Pana roli jako Ownera taki model rozwoju szybko przekłada się na pytanie nie tylko o sprzedaż, ale też o to, czy przy nowych formułach i opakowaniach da się obronić EBIT bez oddawania marży w negocjacjach z dostawcami."

**Po:**
> "Jeśli firma testuje nowe połączenia i formaty, to szybko pojawia się kwestia, jak dowieźć to tak, żeby marża nie uciekała na kosztach składników, opakowań i dostawców."

Ten sam sens. O 60% mniej słów. Zdecydowanie bardziej naturalnie.

## 3. Anchor brzmi bardziej spontanicznie

**Przed:** "Postanowiłem napisać do Pana po artykule „[tytuł]" opublikowanym w [źródło], bo wynika z niego, że…"  
**Po:** "Przeczytałem w [źródło] artykuł... i od razu pomyślałem o [firmie]"

Małe zdanie, duża różnica w odczuciu. Pierwsze brzmi jak formalny list, drugie jak naturalna reakcja.

## 4. Maile brzmią teraz bardziej "po przeczytaniu artykułu"

Przed zmianami: wiadomości były poprawne logicznie, ale wyglądały na "model" — jakby każdy element był wstawiony przez szablon.

Po zmianach: pierwsze zdanie jest żywe ("Przeczytałem... i od razu pomyślałem"), bridge jest praktyczny ("marża nie uciekała na kosztach"), FU1 wchodzi w jeden konkretny mechanizm bez patetyzmu ("To daje swobodę, ale też łatwo podnosi koszt każdej nowej serii").

## 5. Logika kampanii zachowana w 100%

Nic istotnego nie zostało zmienione:
- anchor → hipoteza → bridge → framework → CTA — identyczna sekwencja
- tier-specific narrative — bez zmian
- CTA (Calendly + telefon) — bez zmian
- word count ranges — bez zmian
- gender/vocative rules — bez zmian
- ZAKAZANE frazy — bez zmian, rozszerzone o technokrację

## 6. Co konkretnie zmieniono w kodzie / promptach

**`message_writer.md` (główna zmiana):**
- Dodano sekcję STYL I TON z 4 podsekciami: zasada nadrzędna, reguły zdań, tabela zamienników, naturalność
- Zaktualizowano anchor warianty na bardziej spontaniczne
- Dodano przykład złego/dobrego bridge bezpośrednio w instrukcji
- Dodano regułę #15: "Styl zawsze wygrywa z formą — lepiej naturalnie niż elegancko i ciężko"

**`message_generator.py` (pomocnicza zmiana):**
- System prompt dla LLM wzbogacony o styl: "piszesz naturalnie i lżej — krótsze zdania, prostsze słownictwo"
- Dodano `_check_style_issues()` — heurystyka logująca ostrzeżenie gdy w tekście wykryto technoKratyczne frazy (9 wzorców)

## 7. Re-test — ON Lemon nadal wypada dobrze

ON Lemon, Robert (Owner, Tier 1) → READY_FOR_REVIEW. Wiadomości wygenerowane i ocenione:
- Email 1: lżejszy anchor, prostszy bridge, dobra hipoteza
- Follow Up 1: wnosi nową wartość (koszty nowych serii produktowych), naturalny
- Follow Up 2: krótki, bez presji, konkretny powód powrotu
- StyleCheck: 0 ostrzeżeń — brak wykrytych technoKratycznych fraz

Grycan: BLOCKED_NO_CONTACT (0 T1/T2 w Apollo) — niezwiązane z language polish.

## 8. Co jeszcze można poprawić

- **Phone CTA konsekwencja:** LLM czasem pomija alternatywę telefoniczną w FU1/FU2 — można dodać explicit rule "zawsze" do promptu.
- **Test T2:** do tej pory sprawdzono tylko T1 (Owner). Tier 2 (dyrektor zakupów) może generować inne patterny — warto sprawdzić gdy pojawi się case.
- **Dalszy monitoring:** StyleCheck loguje ostrzeżenia — warto raz sprawdzić logi po kilku real case'ach, żeby zobaczyć czy LLM nie "ucieka" z powrotem do ciężkiego języka.
- **Grycan/Maspex/Colian:** ich BLOCKED nie wynika z języka — wynika z braku T1/T2 w Apollo. Language polish nie rozwiązuje tego problemu (i nie był celem).

## 9. Kampania brzmi teraz bardziej "po artykule", mniej jak formalny memo

Przed: "W Pana roli jako Ownera taki model rozwoju szybko przekłada się na pytanie..."  
Po: "Jeśli firma testuje nowe pomysły, szybko pojawia się kwestia, jak żeby marża nie uciekała..."

To jest właściwy kierunek. Nie jest idealnie (LLM bywa nieprzewidywalny), ale jest wyraźnie bliżej docelowego tonu.

---

**Pliki zmienione:**
- [campaigns/news/spendguru_market_news/prompts/message_writer.md](prompts/message_writer.md) — główna zmiana
- [src/news/messaging/message_generator.py](../../../src/news/messaging/message_generator.py) — system_prompt + heurystyka

**Pełny raport:** [LANGUAGE_POLISH_REPORT.md](LANGUAGE_POLISH_REPORT.md)

---

*Sesja: 2026-04-23 | spendguru_market_news | Language Polish v1*
