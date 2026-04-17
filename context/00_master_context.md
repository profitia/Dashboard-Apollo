# 00_master_context.md  
# Master Context: AI Outreach System

## 1. Cel systemu

Celem systemu jest wspieranie personalizowanego outreachu B2B, którego głównym zadaniem jest dotarcie do właściwych osób z jakościowym, trafnym i wiarygodnym przekazem oraz umówienie pierwszego spotkania.

System ma wspierać sprzedaż consultative / POC-led, a nie masową wysyłkę generycznych wiadomości.

Najważniejszy cel komunikacji:

> Dotarcie do właściwej osoby z wiadomością opartą na realnym kontekście firmy, triggerze biznesowym, hipotezie problemu i prostym CTA do rozmowy.

---

## 2. Zasada nadrzędna

Agenci AI nie mają „pisać ładnych maili".

Agenci mają budować komunikację opartą na:

- realnym triggerze,
- kontekście firmy,
- personie odbiorcy,
- hipotezie problemu biznesowego,
- właściwym proof point,
- krótkim i naturalnym CTA.

Każda wiadomość powinna sprawiać wrażenie ręcznie przygotowanej po researchu, a nie wygenerowanej masowo.

---

## 3. Kontekst biznesowy

Outreach dotyczy oferty SpendGuru / Profitia.

SpendGuru powinien być komunikowany przede wszystkim jako wsparcie skuteczniejszych negocjacji zakupowych, a nie jako zwykła platforma analityczna lub dashboard.

Główna logika komunikacji:

> Pomagamy zespołom zakupowym lepiej przygotować negocjacje z dostawcami dzięki połączeniu danych, benchmarków, prognoz, analizy dostawców, informacji rynkowych i doświadczenia ekspertów Profitii.

W komunikacji należy unikać zaczynania od produktu, modułów lub technologii. Najpierw należy mówić o problemie biznesowym, jakości przygotowania negocjacji, kontroli nad kosztami, ochronie marży i przewidywalności wyniku.

---

## 4. Główna propozycja wartości

SpendGuru i Profitia pomagają organizacjom przejść od negocjacji prowadzonych intuicyjnie do powtarzalnego standardu przygotowania negocjacji opartego na danych.

Najważniejsze wartości:

- lepsze przygotowanie do rozmów z dostawcami,
- większa kontrola nad jakością negocjacji,
- silniejsza argumentacja oparta na faktach,
- lepsza ocena zasadności podwyżek,
- większa przewidywalność kosztów,
- ochrona marży i budżetu,
- możliwość skalowania standardu pracy na kolejne kategorie i dostawców.

---

## 5. Jak nie pozycjonować SpendGuru

Nie komunikować SpendGuru głównie jako:

- kolejnego software'u,
- dashboardu,
- systemu raportowego,
- narzędzia AI,
- listy modułów,
- technologii samej w sobie.

W komunikacji nie zaczynać od:

- „mamy platformę",
- „nasze narzędzie pozwala…",
- „oferujemy moduły Cost Scan, X-Ray, Crystal Ball…",
- „chciałbym pokazać demo".

Najpierw problem, potem hipoteza, następnie wartość, dopiero na końcu rozwiązanie.

---

## 6. Jak pozycjonować SpendGuru

Komunikować SpendGuru jako:

- sposób na lepsze przygotowanie negocjacji,
- standard pracy negocjacyjnej oparty na danych,
- wsparcie w obronie przed nieuzasadnionymi podwyżkami,
- narzędzie do budowania argumentacji zakupowej,
- połączenie danych, technologii i doświadczenia doradczego,
- wsparcie realnych rozmów z dostawcami.

Przykładowe kierunki komunikacji:

- „lepsze przygotowanie negocjacji",
- „powtarzalny standard negocjacji zakupowych",
- „argumentacja oparta na danych",
- „ocena zasadności podwyżek",
- „ochrona marży i budżetu zakupowego",
- „przejście od intuicji do faktów".

---

## 7. Główne persony

System powinien rozróżniać komunikację do różnych person.

### 7.1. Dyrektor zakupów / CPO / Head of Procurement

Najważniejsze tematy:

- kontrola nad jakością pracy zespołu,
- powtarzalny standard przygotowania negocjacji,
- wpływ zakupów na wynik finansowy,
- przewidywalność efektów negocjacji,
- ochrona marży,
- lepsze zarządzanie kategoriami i dostawcami.

Język:

- zarządczy,
- strategiczny,
- biznesowy,
- oparty na wyniku i kontroli.

### 7.2. Kupiec / Category Manager / Senior Buyer

Najważniejsze tematy:

- lepsze przygotowanie do rozmowy z dostawcą,
- mocniejsze argumenty,
- szybszy dostęp do danych,
- mniejsza improwizacja,
- łatwiejsza ocena oferty,
- pewność w rozmowie negocjacyjnej.

Język:

- praktyczny,
- konkretny,
- operacyjny,
- bliski codziennej pracy.

### 7.3. CFO / Controlling / Finanse

Najważniejsze tematy:

- wpływ zakupów na marżę,
- budżetowanie,
- cash flow,
- zasadność podwyżek,
- przewidywalność kosztów,
- ryzyko dostawców.

Język:

- finansowy,
- rzeczowy,
- nastawiony na wynik, ryzyko i kontrolę.

### 7.4. Zarząd / właściciel / CEO

Najważniejsze tematy:

- ochrona wyniku firmy,
- marża,
- przewaga negocjacyjna,
- lepsza decyzyjność,
- ryzyko kosztowe,
- profesjonalizacja funkcji zakupowej.

Język:

- bardzo krótki,
- biznesowy,
- strategiczny,
- bez nadmiernych szczegółów operacyjnych.

---

## 8. Model pipeline'u

Docelowy pipeline systemu:

1. Lead scoring  
2. Research konta  
3. Wybór persony  
4. Budowa hipotezy problemu  
5. Dobór proof pointu  
6. Przygotowanie wiadomości  
7. QA / Anti-LLM review  
8. Zapis personalizacji do pól kontaktu  
9. Dodanie kontaktu do właściwej sekwencji w Apollo  
10. Follow-upy  
11. Call prep po odpowiedzi  
12. Notatka CRM i feedback loop

Skrót:

> Score leada → research → hipoteza → proof → message → QA → Apollo sequence → call prep.

---

## 9. Rola Apollo

Apollo odpowiada za:

- wyszukiwanie firm,
- wyszukiwanie osób,
- enrichment,
- adresy email,
- zapis kontaktów,
- sekwencje,
- wysyłkę maili,
- obsługę skrzynek pocztowych.

Apollo jest warstwą danych kontaktowych i wykonania kampanii.

Agenci AI nie powinni samodzielnie „zgadywać" adresów email ani scrapować ich z przypadkowych źródeł. Powinni korzystać z Apollo, CRM lub zatwierdzonych źródeł danych.

---

## 10. Rola VS Code

VS Code jest środowiskiem orchestration.

Służy do:

- przechowywania plików kontekstowych,
- przechowywania promptów,
- trzymania configów kampanii,
- uruchamiania tasków,
- pracy ze skryptami,
- debugowania pipeline'u,
- zapisu outputów,
- wersjonowania zmian.

VS Code nie jest narzędziem wysyłkowym. Wysyłka odbywa się przez Apollo.

---

## 11. Rola agentów AI

Agenci AI odpowiadają za warstwę intelligence:

- selekcję,
- interpretację danych,
- budowę hipotez,
- personalizację,
- copywriting,
- kontrolę jakości,
- przygotowanie do rozmów.

Agenci nie powinni automatycznie wysyłać wiadomości bez przejścia przez zasady QA i progi jakości.

---

## 12. Główne role agentów

### 12.1. Lead Scoring Agent

Zadanie:

Ocenić, czy lead jest wart głębokiej personalizacji.

Analizuje:

- dopasowanie do ICP,
- branżę,
- wielkość firmy,
- stanowisko,
- seniority,
- potencjalny trigger,
- jakość danych kontaktowych,
- potencjał spotkania.

Output:

- lead score,
- priorytet,
- rekomendacja: deep personalization / light personalization / reject.

---

### 12.2. Account Research Agent

Zadanie:

Zebrać kontekst o firmie i zamienić go w krótki materiał sprzedażowy.

Nie tworzy długiego researchu. Tworzy kartę konta.

Output:

- 3 najważniejsze sygnały biznesowe,
- 2 możliwe problemy zakupowe lub kosztowe,
- 1 sensowny powód kontaktu teraz,
- 1 teza do pierwszej wiadomości,
- 1 propozycja CTA.

---

### 12.3. Persona Strategist Agent

Zadanie:

Dopasować komunikację do odbiorcy.

Ten sam account powinien być opowiedziany inaczej dla:

- CPO,
- kupca,
- CFO,
- zarządu.

Agent zmienia:

- język wartości,
- rodzaj ryzyka,
- oczekiwany efekt spotkania,
- poziom szczegółowości,
- typ proof pointu.

---

### 12.4. Hypothesis Agent

Zadanie:

Zamienić research w hipotezę problemu biznesowego.

Odpowiada na pytania:

- co może być problemem tej firmy,
- dlaczego teraz,
- jaki jest możliwy wpływ na zakupy, koszty, marżę lub ryzyko,
- jaka teza sprzedażowa ma sens,
- jaki kąt wiadomości będzie najbardziej trafny.

Ważne:

Nie pisać wiadomości bez hipotezy.

---

### 12.5. Trigger-to-Message Agent

Zadanie:

Zamienić konkretny trigger na logikę wiadomości.

Schemat:

> trigger → interpretacja wpływu → hipoteza problemu → narracja → CTA

Przykładowe triggery:

- wzrost kosztów,
- presja inflacyjna,
- inwestycja,
- ekspansja,
- spadek wyników,
- zmiana dostawcy,
- problem jakościowy,
- zmiana regulacyjna,
- reorganizacja,
- nowe ogłoszenia rekrutacyjne,
- presja na cash flow,
- zmiana w łańcuchu dostaw.

---

### 12.6. Dynamic Proof Agent

Zadanie:

Dobrać najbardziej trafny proof point do persony, branży i hipotezy.

Może wybierać:

- podobny case,
- przykład efektu,
- benchmark,
- insight,
- typowy problem branżowy,
- argument z obszaru negocjacji, kosztów, ryzyka lub budżetu.

Nie wolno zmyślać liczb, case studies ani efektów.

Jeżeli brak potwierdzonego proof pointu, należy użyć neutralnego sformułowania.

---

### 12.7. Message Writer Agent

Zadanie:

Napisać wiadomość mailową, LinkedIn lub follow-up.

Input:

- persona,
- trigger,
- 2–3 fakty o firmie,
- hipoteza,
- proof point,
- cel spotkania,
- ton komunikacji.

Output:

- temat maila,
- opener,
- główna wiadomość,
- CTA,
- wersja LinkedIn,
- follow-up.

Zasady:

- krótko,
- konkretnie,
- naturalnie,
- bez przesadnego pitchowania,
- bez ogólników,
- jedno CTA,
- jeden powód kontaktu teraz.

---

### 12.8. QA / Anti-LLM Agent

Zadanie:

Ocenić jakość wiadomości przed wysyłką.

Sprawdza:

- czy opener jest naprawdę spersonalizowany,
- czy wiadomość nie brzmi jak masówka,
- czy hipoteza jest logiczna,
- czy wartość dla persony jest czytelna,
- czy CTA jest adekwatne,
- czy mail nie jest za długi,
- czy nie ma halucynacji,
- czy nie ma „AI vibe",
- czy nie ma pustych fraz,
- czy personalizacja nie jest creepy.

Output:

- score jakości,
- lista problemów,
- decyzja: approve / rewrite / reject.

---

### 12.9. Sequencer Agent

Zadanie:

Przygotować follow-upy oparte na zmieniającej się logice.

Model:

- mail 1: trigger + hipoteza,
- follow-up 1: inny proof point,
- follow-up 2: krótkie pytanie diagnostyczne,
- follow-up 3: case / use case,
- follow-up 4: zamknięcie pętli.

Follow-upy nie powinny być pustym „podbijaniem".

---

### 12.10. Call Prep Agent

Zadanie:

Po odpowiedzi prospekta przygotować sprzedawcę do rozmowy.

Output:

- mini briefing przed rozmową,
- lista pytań discovery,
- możliwe obiekcje,
- hipotezy do potwierdzenia,
- szkic agendy,
- propozycja następnego kroku,
- notatka po callu.

---

### 12.11. CRM Note Agent

Zadanie:

Zamienić research, wiadomość i odpowiedź prospekta w krótką notatkę CRM.

Output:

- firma,
- osoba,
- persona,
- trigger,
- hipoteza,
- wysłana wiadomość,
- status,
- następny krok.

---

## 13. Zasady tworzenia wiadomości

Każda wiadomość powinna mieć:

1. Konkretny opener  
2. Hipotezę problemu  
3. Krótkie przełożenie na wartość  
4. Naturalne CTA  

Nie każda wiadomość musi mieć długi proof point. Czasem wystarczy krótki insight.

Preferowana długość pierwszego maila:

- 70–120 słów,
- maksymalnie 3–5 krótkich akapitów,
- bez ciężkiego bloku tekstu.

Styl:

- naturalny,
- rzeczowy,
- konsultacyjny,
- bez nadmiernej sprzedażowości.

---

## 14. Czego unikać w wiadomościach

Nie używać pustych lub generycznych fraz:

- „innowacyjne rozwiązanie",
- „synergia",
- „optymalizacja procesów" bez konkretu,
- „chciałbym przedstawić naszą platformę",
- „w dzisiejszych dynamicznych czasach",
- „kompleksowe wsparcie" bez wyjaśnienia,
- „liderzy rynkowi" bez dowodu.

Nie pisać wiadomości, które brzmią jak:

- masowy mailing,
- pitch produktu,
- automatyczna sekwencja,
- zbyt gładki tekst LLM,
- tekst bez konkretnego powodu kontaktu.

---

## 15. Zasady personalizacji

Personalizacja powinna opierać się na:

- publicznym i biznesowym kontekście,
- danych z Apollo,
- stronie firmy,
- oficjalnych newsach,
- komunikatach firmy,
- aktywności biznesowej,
- danych branżowych,
- własnych notatkach.

Nie personalizować na podstawie prywatnych lub zbyt osobistych informacji.

Nie pisać w sposób, który może brzmieć jak stalking.

Jeżeli brak twardego triggera, użyć neutralnego openeru.

---

## 16. Model triggerów

Trigger to sygnał, który uzasadnia kontakt teraz.

Przykładowe typy triggerów:

- wzrost kosztów,
- presja na marżę,
- ekspansja,
- nowy zakład,
- wejście na nowy rynek,
- inwestycja,
- zmiany regulacyjne,
- problemy w łańcuchu dostaw,
- zmiana dostawców,
- rekrutacja w zakupach / supply chain / finansach,
- presja cash flow,
- spadek wyników,
- konsolidacja rynku,
- zmiana cen surowców,
- zmiana technologiczna,
- zmiana w zarządzie.

Trigger nie jest celem samym w sobie. Musi zostać zinterpretowany.

Dobry schemat:

> Co się wydarzyło → jaki może mieć wpływ → dlaczego to istotne dla persony → dlaczego warto porozmawiać teraz.

---

## 17. Model CTA

CTA powinno być małe, naturalne i niskobarierowe.

Preferowane CTA:

- krótka rozmowa,
- 15–20 minut,
- sprawdzenie, czy temat jest aktualny,
- rozmowa o jednej kategorii lub jednym dostawcy,
- pokazanie przykładu podejścia,
- wspólna weryfikacja hipotezy.

Nie zaczynać od ciężkiego CTA:

- „umów demo",
- „zróbmy prezentację platformy",
- „porozmawiajmy o wdrożeniu systemu".

Lepsze CTA:

> Czy ma sens krótka rozmowa, żeby sprawdzić, czy taki sposób przygotowania negocjacji mógłby być u Państwa przydatny?

---

## 18. Model sekwencji Apollo

Apollo odpowiada za sekwencje i wysyłkę.

Sekwencja w Apollo jest szkieletem wykonawczym, a nie miejscem pełnej personalizacji.

Personalizacja powinna być zapisywana w custom fields i podstawiana do maili jako dynamic variables.

Nie tworzyć osobnej sekwencji dla każdego triggera.

Sekwencje powinny być podzielone według:

- persony,
- języka,
- typu CTA,
- rytmu follow-upów.

Przykładowe sekwencje:

- PL_CPO_MEETING_STD
- PL_BUYER_MEETING_STD
- PL_NAMED_ACCOUNT_SOFT
- EN_CPO_MEETING_STD

Trigger wpływa na treść pól, nie na wybór sekwencji.

---

## 19. Custom fields dla Apollo

Minimalny zestaw pól do personalizacji:

### Krok 1

- custom_subject_1
- custom_opener_1
- custom_problem_hypothesis_1
- custom_proof_1
- custom_cta_1

### Krok 2

- custom_subject_2
- custom_followup_angle_2
- custom_proof_2
- custom_cta_2

### Krok 3

- custom_subject_3
- custom_close_loop_3

### Pola sterujące

- trigger_type
- trigger_summary
- persona_type
- campaign_name
- language_code
- sequence_recommendation
- mailbox_group
- qa_score

Każde wymagane pole powinno być zwalidowane przed dodaniem kontaktu do sekwencji.

---

## 20. Scoring jakości

QA Agent powinien oceniać wiadomość w skali 1–5 lub 1–100.

Minimalne kryteria:

- personalizacja,
- trafność biznesowa,
- jakość hipotezy,
- wiarygodność,
- naturalność,
- jakość CTA,
- długość,
- brak halucynacji,
- brak generycznego języka.

Przykład progu:

- 85+ approve,
- 70–84 rewrite,
- poniżej 70 reject.

Wiadomości poniżej progu nie powinny trafiać do kampanii.

---

## 21. Guardrails

Agenci muszą przestrzegać poniższych zasad:

1. Nie zmyślaj faktów.  
2. Nie zmyślaj case studies.  
3. Nie zmyślaj liczb.  
4. Nie udawaj, że znasz sytuację firmy, jeśli masz tylko hipotezę.  
5. Odróżniaj fakt od hipotezy.  
6. Nie używaj prywatnych informacji do personalizacji.  
7. Nie pisz zbyt agresywnie.  
8. Nie pitchuj produktu za wcześnie.  
9. Nie wysyłaj wiadomości bez sensownej hipotezy.  
10. Nie dodawaj kontaktu do kampanii, jeśli email jest niepewny lub brak wymaganych pól.  
11. Nie używaj języka, który brzmi jak masowy mailing.  
12. Nie twórz treści niezgodnych z personą.

---

## 22. Ton komunikacji

Preferowany ton:

- rzeczowy,
- prosty,
- ekspercki,
- konsultacyjny,
- naturalny,
- bez marketingowego nadęcia.

Nie pisać zbyt formalnie ani zbyt luźno.

Unikać:

- przesadnych przymiotników,
- długich zdań,
- korporacyjnego żargonu,
- ogólnych deklaracji bez konkretu.

---

## 23. Przykładowy schemat pierwszej wiadomości

Struktura:

1. Personalizowany opener  
2. Hipoteza problemu  
3. Krótka wartość  
4. CTA  

Przykład strukturalny:

> Dzień dobry, {{first_name}},  
> {{custom_opener_1}}  
>   
> {{custom_problem_hypothesis_1}}  
>   
> {{custom_proof_1}}  
>   
> {{custom_cta_1}}

Nie kopiować tego jako sztywnego szablonu. To tylko struktura.

---

## 24. Przykładowy schemat follow-upu

Follow-up powinien wnosić nowy kąt.

Struktura:

1. Krótkie nawiązanie  
2. Nowy insight / proof / pytanie  
3. Mikro-CTA  

Przykład:

> Dopowiem tylko jedną rzecz — w podobnych rozmowach często punktem wyjścia nie jest sama cena, ale sprawdzenie, czy argumenty dostawcy są uzasadnione kosztowo.  
>   
> Czy to jest temat, który warto u Państwa krótko zweryfikować?

---

## 25. Reguła fakt vs hipoteza

Agenci muszą jasno odróżniać:

- fakt,
- obserwację,
- hipotezę,
- sugestię.

Nie pisać:

> Widzę, że macie problem z kosztami dostawców.

Lepiej:

> Przy takiej skali działalności często pojawia się pytanie, czy podwyżki dostawców są w pełni uzasadnione kosztowo.

---

## 26. Reguła produktu

Nie zaczynać od modułów SpendGuru.

Moduły mogą pojawić się dopiero później jako zaplecze rozwiązania.

W pierwszym outreachu preferować język:

- metoda,
- podejście,
- standard,
- przygotowanie negocjacji,
- analiza jednej kategorii,
- wsparcie konkretnej rozmowy z dostawcą.

---

## 27. Reguła pierwszego spotkania

Celem pierwszego maila nie jest sprzedaż całego rozwiązania.

Celem jest:

- zainteresowanie odbiorcy,
- otwarcie rozmowy,
- sprawdzenie aktualności problemu,
- umówienie krótkiego spotkania,
- przejście do rozmowy o jednej kategorii / jednym dostawcy.

---

## 28. Reguła POC / warsztatu

Jeśli komunikacja prowadzi dalej, naturalna ścieżka to:

1. Pierwszy kontakt  
2. Krótka rozmowa  
3. Rozpoznanie kategorii / dostawcy / problemu  
4. Warsztat lub POC  
5. Ocena efektu  
6. Skalowanie na kolejne kategorie lub dostawców

Nie proponować od razu dużego wdrożenia.

---

## 29. Minimalny zestaw outputów

Każdy pełny proces dla leada powinien tworzyć:

- account_brief.md
- persona_angle.json
- hypothesis.json
- outreach_pack.md
- qa_score.json
- apollo_fields.json
- crm_note.txt

---

## 30. Najważniejsza zasada końcowa

System ma pomagać w budowaniu lepszych rozmów sprzedażowych, nie tylko w zwiększaniu liczby wysyłanych maili.

Lepszy wynik oznacza:

- lepsze dopasowanie odbiorcy,
- lepszy powód kontaktu,
- lepszą hipotezę,
- bardziej naturalną wiadomość,
- wyższą jakość spotkań.

Zawsze preferuj jakość nad wolumenem.
