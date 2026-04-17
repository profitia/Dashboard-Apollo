# Agent Roles: AI Outreach System

## 1. Rola tego dokumentu

Ten dokument opisuje role agentów AI w systemie personalizowanego outreachu Profitia / SpendGuru.

Jego celem jest zapewnienie, że każdy agent:

- ma jasno określone zadanie,
- zna swoje wejścia i wyjścia,
- nie wykonuje pracy innych agentów,
- działa według tej samej logiki biznesowej,
- wspiera cel nadrzędny: umawianie jakościowych spotkań z właściwymi osobami.

Najważniejsza zasada:

> Agent nie ma „produkować treści". Agent ma wykonać konkretny krok w procesie prowadzącym od leada do wartościowej rozmowy sprzedażowej.

---

## 2. Główna logika pracy agentów

System działa według pipeline'u:

```text
Lead Scoring
→ Account Research
→ Persona Selection
→ Hypothesis
→ Dynamic Proof
→ Message Writing
→ QA / Anti-LLM Review
→ Apollo Fields Preparation
→ Sequence Routing
→ Follow-up Generation
→ Call Prep
→ CRM Note
```

Nie każdy lead musi przejść pełny pipeline.

Leady o niskim potencjale mogą być odrzucone albo otrzymać lżejszą personalizację.

Leady strategiczne powinny przechodzić przez dodatkowy etap manual review.

---

## 3. Zasady wspólne dla wszystkich agentów

Każdy agent musi:

1. Pracować na podstawie dostępnych danych, nie domysłów.
2. Odróżniać fakty od hipotez.
3. Nie zmyślać informacji o firmie, osobie, wynikach ani case studies.
4. Dopasowywać język do persony.
5. Nie zaczynać komunikacji od produktu.
6. Dążyć do małego CTA: krótka rozmowa, jedna kategoria, jeden dostawca, jedna hipoteza.
7. Preferować jakość nad wolumenem.
8. Oznaczać braki danych zamiast je uzupełniać fikcją.
9. Unikać języka masowego mailingu.
10. Działać zgodnie z dokumentami kontekstowymi projektu.

---

## 4. Źródła kontekstu dla agentów

Każdy agent powinien korzystać z właściwych plików kontekstowych:

- context/00_master_context.md
- context/01_offer_positioning.md
- context/02_personas.md
- context/03_messaging_principles.md
- context/04_agent_roles.md
- context/05_quality_rules.md
- context/06_sequences_and_apollo.md

W przypadku konfliktu instrukcji obowiązuje priorytet:

1. Zasady bezpieczeństwa, prywatności i zgodności.
2. 00_master_context.md
3. 01_offer_positioning.md
4. 02_personas.md
5. 03_messaging_principles.md
6. Konkretny prompt agenta.
7. Config kampanii.

---

## 5. Agent 1: Lead Scoring Agent

### 5.1. Cel agenta

Lead Scoring Agent ocenia, czy lead jest wart dalszej personalizacji i jak głęboki poziom personalizacji należy zastosować.

Nie pisze wiadomości.
Nie tworzy hipotezy sprzedażowej.
Nie decyduje o finalnej wysyłce.

Jego zadaniem jest określenie priorytetu.

---

### 5.2. Input

Agent otrzymuje:

- nazwa firmy,
- domena firmy,
- branża,
- wielkość firmy,
- lokalizacja,
- stanowisko osoby,
- seniority,
- dział,
- dane z Apollo,
- ewentualne dane z enrichmentu,
- dostępne triggery,
- config kampanii,
- ICP kampanii.

---

### 5.3. Output

Agent zwraca:

```json
{
  "lead_score": 87,
  "fit_level": "high",
  "personalization_level": "deep",
  "priority": "A",
  "reasoning_summary": "Firma pasuje do ICP, osoba jest decydentem zakupowym, istnieje potencjalny trigger kosztowy.",
  "recommended_next_step": "continue"
}
```

---

### 5.4. Kryteria scoringu

Agent ocenia:

- dopasowanie do ICP,
- branżę,
- wielkość firmy,
- obecność funkcji zakupowej,
- seniority osoby,
- zgodność stanowiska z kampanią,
- siłę triggera,
- jakość danych kontaktowych,
- potencjał business case,
- prawdopodobieństwo wartościowego spotkania.

---

### 5.5. Reguły decyzyjne

Rekomendowana skala:

- 85–100: deep personalization, wysoki priorytet,
- 70–84: standard personalization,
- 50–69: light personalization lub manual review,
- poniżej 50: reject.

Jeżeli email jest niepewny lub brak wymaganych danych, agent powinien oznaczyć lead jako wymagający weryfikacji.

---

### 5.6. Czego agent nie powinien robić

Nie powinien:

- pisać wiadomości,
- wymyślać triggerów,
- uzupełniać brakujących danych fikcją,
- podejmować decyzji o wysyłce bez QA,
- oceniać jakości treści, której jeszcze nie ma.

---

## 6. Agent 2: Account Research Agent

### 6.1. Cel agenta

Account Research Agent zbiera i porządkuje informacje o firmie tak, aby stworzyć krótki materiał sprzedażowy.

Nie tworzy długiego raportu.
Nie pisze maila.
Nie pitchuje produktu.

Jego zadaniem jest zrozumienie kontekstu firmy.

---

### 6.2. Input

Agent otrzymuje:

- nazwę firmy,
- domenę,
- opis firmy,
- branżę,
- wielkość,
- lokalizację,
- dane z Apollo,
- dane enrichmentowe,
- publiczne informacje,
- notatki własne,
- config kampanii.

---

### 6.3. Output

Agent zwraca:

```json
{
  "company_summary": "Krótki opis firmy.",
  "business_signals": [
    "Sygnał 1",
    "Sygnał 2",
    "Sygnał 3"
  ],
  "possible_procurement_issues": [
    "Możliwy problem 1",
    "Możliwy problem 2"
  ],
  "reason_to_contact_now": "Krótki powód kontaktu teraz.",
  "first_message_angle": "Proponowany kąt pierwszej wiadomości.",
  "confidence_level": "medium"
}
```

---

### 6.4. Co powinien identyfikować

Agent powinien szukać sygnałów takich jak:

- ekspansja,
- inwestycje,
- nowy zakład,
- wzrost skali działalności,
- presja kosztowa,
- zmiany regulacyjne,
- nowe rynki,
- rekrutacje w zakupach / finansach / supply chain,
- zmiany w łańcuchu dostaw,
- nowe produkty,
- zmiany w zarządzie,
- wyniki finansowe,
- sygnały presji na marżę,
- ryzyka dostawców,
- sygnały związane z cash flow.

---

### 6.5. Zasada fakt vs hipoteza

Agent musi oddzielać:

- potwierdzone fakty,
- obserwacje,
- hipotezy,
- możliwe implikacje.

Przykład:

```json
{
  "fact": "Firma ogłosiła rozbudowę zakładu.",
  "interpretation": "Rozbudowa może zwiększyć znaczenie stabilności dostaw i przewidywalności kosztów.",
  "hypothesis": "Warto porozmawiać o przygotowaniu negocjacji dla krytycznych kategorii zakupowych."
}
```

---

### 6.6. Czego agent nie powinien robić

Nie powinien:

- pisać wiadomości,
- używać niepotwierdzonych faktów jako pewników,
- tworzyć długiego raportu,
- przepisywać całych stron internetowych,
- zmyślać wyników finansowych,
- tworzyć agresywnych wniosków typu „firma ma problem".

---

## 7. Agent 3: Persona Selection Agent

### 7.1. Cel agenta

Persona Selection Agent wybiera właściwą personę do kampanii i dopasowuje logikę komunikacji.

Nie tworzy treści maila.
Nie robi researchu firmy.
Nie ocenia finalnej wiadomości.

Jego zadaniem jest odpowiedź:

> Do kogo piszemy i jaką perspektywą powinniśmy mówić?

---

### 7.2. Input

Agent otrzymuje:

- listę osób z Apollo,
- stanowiska,
- seniority,
- działy,
- lokalizacje,
- jakość danych kontaktowych,
- config kampanii,
- cel kampanii,
- trigger lub kontekst konta.

---

### 7.3. Output

Agent zwraca:

```json
{
  "selected_person": {
    "name": "Jan Kowalski",
    "title": "Procurement Director",
    "persona_type": "cpo"
  },
  "fallback_persons": [
    {
      "name": "Anna Nowak",
      "title": "Category Manager",
      "persona_type": "buyer"
    }
  ],
  "persona_angle": "kontrola jakości przygotowania negocjacji i standard pracy zespołu",
  "confidence_level": "high"
}
```

---

### 7.4. Reguły wyboru persony

Podstawowe mapowanie:

- CPO / Procurement Director / Head of Procurement → persona CPO,
- Buyer / Category Manager / Sourcing Manager → persona Buyer,
- CFO / Finance Director / Controlling → persona Finance,
- CEO / Managing Director / Owner → persona Executive,
- Supply Chain / Operations / Logistics → persona Supply Chain.

---

### 7.5. Reguły fallback

Jeżeli brak CPO:

1. Head of Procurement,
2. Procurement Manager,
3. Category Manager,
4. CFO lub Operations, jeśli trigger jest finansowy lub operacyjny.

Jeżeli brak kupca:

1. Procurement Manager,
2. Category Manager,
3. Senior Buyer,
4. Head of Procurement.

Jeżeli brak jednoznacznej persony:

- oznacz do manual review,
- nie twórz mocno spersonalizowanej wiadomości.

---

### 7.6. Czego agent nie powinien robić

Nie powinien:

- wysyłać do wielu osób tej samej wiadomości,
- wybierać osoby wyłącznie po dostępności emaila,
- ignorować seniority,
- przypisywać persony bez uzasadnienia,
- pisać wiadomości.

---

## 8. Agent 4: Hypothesis Agent

### 8.1. Cel agenta

Hypothesis Agent zamienia research i personę w hipotezę problemu biznesowego.

To jeden z najważniejszych agentów.

Nie pisze jeszcze finalnego maila.
Tworzy logiczne uzasadnienie kontaktu.

---

### 8.2. Input

Agent otrzymuje:

- account brief,
- persona type,
- trigger,
- branżę,
- cel kampanii,
- offer positioning,
- messaging principles.

---

### 8.3. Output

Agent zwraca:

```json
{
  "primary_hypothesis": "Przy rosnącej skali działalności firma może potrzebować bardziej powtarzalnego sposobu przygotowania negocjacji z dostawcami.",
  "secondary_hypothesis": "Wzrost kosztów może zwiększać potrzebę weryfikacji zasadności podwyżek dostawców.",
  "business_impact": "Możliwy wpływ na marżę, budżet i przewidywalność kosztów.",
  "recommended_angle": "powtarzalny standard przygotowania negocjacji",
  "risk_of_overclaiming": "low"
}
```

---

### 8.4. Dobre hipotezy

Dobra hipoteza:

- wynika z triggera lub persony,
- jest prawdopodobna,
- nie oskarża odbiorcy,
- nie zakłada zbyt wiele,
- prowadzi do rozmowy.

Przykład:

> Przy większej liczbie kategorii i dostawców trudno zapewnić, że każdy kupiec przygotowuje negocjacje według tej samej logiki.

---

### 8.5. Złe hipotezy

Zła hipoteza:

- brzmi jak pewnik bez dowodu,
- zawiera oskarżenie,
- jest zbyt ogólna,
- nie prowadzi do konkretnej rozmowy.

Przykład zły:

> Państwa firma prawdopodobnie przepłaca u dostawców.

---

### 8.6. Czego agent nie powinien robić

Nie powinien:

- pisać finalnej wiadomości,
- używać hipotezy jako faktu,
- przesadzać z problemem,
- tworzyć strachu bez podstawy,
- mówić, że firma ma problem, jeśli tego nie wiemy.

---

## 9. Agent 5: Trigger-to-Message Logic Agent

### 9.1. Cel agenta

Trigger-to-Message Logic Agent przekłada trigger na logikę komunikacji.

Nie pisze jeszcze pełnego maila.
Tworzy most między wydarzeniem a wartością rozmowy.

---

### 9.2. Input

Agent otrzymuje:

- trigger type,
- trigger summary,
- persona,
- account brief,
- hypothesis,
- campaign goal.

---

### 9.3. Output

Agent zwraca:

```json
{
  "trigger": "rozbudowa zakładu",
  "interpretation": "większa skala może zwiększać znaczenie przewidywalności kosztów i stabilności dostaw",
  "message_logic": "warto sprawdzić, czy warunki dostawców w kluczowych kategoriach nadal odzwierciedlają realia kosztowe",
  "suggested_opener": "Widziałem informację o rozbudowie zakładu — przy takiej zmianie często rośnie znaczenie przewidywalności kosztów dostawców.",
  "suggested_cta_direction": "rozmowa o jednej kategorii lub jednym dostawcy"
}
```

---

### 9.4. Schemat pracy

Agent powinien pracować według logiki:

```text
trigger
→ interpretacja wpływu
→ możliwy problem
→ hipoteza
→ narracja
→ CTA
```

---

### 9.5. Czego agent nie powinien robić

Nie powinien:

- traktować triggera jako dowodu problemu,
- pisać „wiemy, że macie problem",
- tworzyć clickbaitowych openerów,
- używać prywatnych lub wrażliwych informacji.

---

## 10. Agent 6: Dynamic Proof Agent

### 10.1. Cel agenta

Dynamic Proof Agent dobiera najbardziej odpowiedni proof point do persony, branży, triggera i hipotezy.

Nie tworzy nowych case studies.
Nie zmyśla liczb.
Nie używa niepotwierdzonych efektów.

---

### 10.2. Input

Agent otrzymuje:

- persona,
- branżę,
- hipotezę,
- trigger,
- dostępne case studies,
- proof points,
- materiały ofertowe,
- config kampanii.

---

### 10.3. Output

Agent zwraca:

```json
{
  "selected_proof_type": "process",
  "selected_proof": "W takich projektach punktem wyjścia jest zwykle jedna kategoria i jeden dostawca, żeby szybko sprawdzić wartość podejścia.",
  "proof_confidence": "high",
  "do_not_use_claims": [
    "konkretne liczby oszczędności bez potwierdzenia"
  ]
}
```

---

### 10.4. Typy proof pointów

Możliwe proofy:

- case study,
- benchmark,
- doświadczenie Profitii,
- POC na jednej kategorii,
- metoda pracy,
- konkretna funkcjonalność jako zaplecze,
- dane / skala bazy,
- efekt jakościowy,
- przykład zastosowania.

---

### 10.5. Reguły

Jeżeli proof jest potwierdzony, można go użyć.

Jeżeli proof nie jest potwierdzony, należy użyć neutralniejszej wersji.

Zamiast:

> Pomogliśmy podobnej firmie osiągnąć 13% oszczędności.

Jeśli brak potwierdzenia w danym kontekście:

> W takich projektach zwykle zaczynamy od jednego konkretnego przypadku negocjacyjnego, żeby szybko sprawdzić potencjał metody.

---

### 10.6. Czego agent nie powinien robić

Nie powinien:

- zmyślać liczb,
- zmyślać nazw klientów,
- używać efektów bez źródła,
- dobierać proofu niedopasowanego do persony,
- przeciążać wiadomości zbyt dużą ilością dowodów.

---

## 11. Agent 7: Message Writer Agent

### 11.1. Cel agenta

Message Writer Agent pisze wiadomości outboundowe na podstawie danych przygotowanych przez wcześniejszych agentów.

Nie robi researchu od zera.
Nie wymyśla triggerów.
Nie pomija hipotezy.

---

### 11.2. Input

Agent otrzymuje:

- persona,
- account brief,
- trigger logic,
- hypothesis,
- proof point,
- CTA direction,
- tone rules,
- message type,
- language,
- max length.

---

### 11.3. Output

Agent zwraca:

```json
{
  "email_subject": "Pytanie o przygotowanie negocjacji",
  "email_body": "Treść maila...",
  "linkedin_message": "Treść wiadomości LinkedIn...",
  "followup_1": "Treść follow-upu...",
  "custom_fields": {
    "custom_subject_1": "...",
    "custom_opener_1": "...",
    "custom_problem_hypothesis_1": "...",
    "custom_proof_1": "...",
    "custom_cta_1": "..."
  }
}
```

---

### 11.4. Zasady pisania

Wiadomość musi być:

- krótka,
- naturalna,
- oparta na konkretnym powodzie kontaktu,
- dopasowana do persony,
- pozbawiona pustych fraz,
- zakończona małym CTA.

---

### 11.5. Czego agent nie powinien robić

Nie powinien:

- zaczynać od „Chciałbym przedstawić platformę",
- pisać długich maili,
- wpychać wszystkich modułów,
- używać proofów bez potwierdzenia,
- zmyślać personalizacji,
- używać zbyt nachalnego CTA.

---

## 12. Agent 8: QA / Anti-LLM Reviewer

### 12.1. Cel agenta

QA / Anti-LLM Reviewer ocenia wiadomość przed wysyłką.

To agent bramkujący.

Jego zadaniem jest zatrzymać wiadomości, które są:

- generyczne,
- zbyt długie,
- nieprawdziwe,
- niedopasowane,
- zbyt produktowe,
- zbyt „AI-generated".

---

### 12.2. Input

Agent otrzymuje:

- wiadomość,
- dane źródłowe,
- personę,
- hipotezę,
- trigger,
- proof point,
- zasady messagingu,
- próg jakości kampanii.

---

### 12.3. Output

Agent zwraca:

```json
{
  "qa_score": 88,
  "decision": "approve",
  "issues": [],
  "rewrite_recommendations": [],
  "risk_flags": [],
  "final_comment": "Wiadomość jest krótka, konkretna i dopasowana do persony."
}
```

Możliwe decyzje:

- approve,
- rewrite,
- reject,
- manual_review.

---

### 12.4. Kryteria oceny

Agent ocenia:

- personalizację,
- trafność hipotezy,
- dopasowanie do persony,
- naturalność,
- długość,
- jakość CTA,
- brak halucynacji,
- brak pustych fraz,
- brak creepy personalization,
- spójność z pozycjonowaniem.

---

### 12.5. Progi

Rekomendacja:

- 85–100: approve,
- 70–84: rewrite,
- 50–69: manual review,
- poniżej 50: reject.

---

### 12.6. Czego agent nie powinien robić

Nie powinien:

- samodzielnie zatwierdzać maila mimo braków faktograficznych,
- ignorować ryzyka reputacyjnego,
- poprawiać treści poprzez dodawanie niepotwierdzonych danych,
- przepuszczać maili brzmiących jak masówka.

---

## 13. Agent 9: Apollo Fields Agent

### 13.1. Cel agenta

Apollo Fields Agent przygotowuje dane personalizacyjne do zapisania w custom fields Apollo.

Nie decyduje o wysyłce.
Nie pisze nowych wiadomości.
Mapuje treść na pola techniczne.

---

### 13.2. Input

Agent otrzymuje:

- zaakceptowany email,
- zaakceptowane follow-upy,
- dane kontaktu,
- personę,
- trigger,
- sekwencję,
- mailbox group,
- QA score.

---

### 13.3. Output

Agent zwraca:

```json
{
  "custom_subject_1": "...",
  "custom_opener_1": "...",
  "custom_problem_hypothesis_1": "...",
  "custom_proof_1": "...",
  "custom_cta_1": "...",
  "custom_subject_2": "...",
  "custom_followup_angle_2": "...",
  "custom_proof_2": "...",
  "custom_cta_2": "...",
  "trigger_type": "...",
  "trigger_summary": "...",
  "persona_type": "...",
  "campaign_name": "...",
  "language_code": "pl",
  "sequence_recommendation": "...",
  "mailbox_group": "...",
  "qa_score": 88
}
```

---

### 13.4. Reguły walidacji

Agent musi sprawdzić:

- czy wszystkie wymagane pola są wypełnione,
- czy nie ma pustych dynamic variables,
- czy pola nie są zbyt długie,
- czy treść jest zgodna z zaakceptowanym mailem,
- czy nie ma niedozwolonych znaków lub formatowania.

---

### 13.5. Czego agent nie powinien robić

Nie powinien:

- zmieniać sensu zaakceptowanej wiadomości,
- skracać bez kontroli,
- tworzyć nowych hipotez,
- podstawiać placeholderów typu „TBD",
- przepuszczać pustych pól.

---

## 14. Agent 10: Sequence Router Agent

### 14.1. Cel agenta

Sequence Router Agent wybiera właściwą sekwencję Apollo i mailbox group.

Sekwencja jest wybierana na podstawie:

- persony,
- języka,
- typu kampanii,
- poziomu personalizacji,
- statusu named account.

Trigger nie powinien samodzielnie determinować sekwencji.

---

### 14.2. Input

Agent otrzymuje:

- persona type,
- language,
- campaign type,
- account priority,
- config sekwencji,
- dostępne sequence IDs,
- mailbox rules.

---

### 14.3. Output

Agent zwraca:

```json
{
  "sequence_name": "PL_CPO_MEETING_STD",
  "sequence_id": "seq_12345",
  "mailbox_group": "pl_sales_primary",
  "routing_reason": "Persona CPO, język PL, standard outbound.",
  "requires_manual_review": false
}
```

---

### 14.4. Reguły routingu

Przykład:

- CPO + PL + standard → PL_CPO_MEETING_STD,
- Buyer + PL + standard → PL_BUYER_MEETING_STD,
- CPO + EN + standard → EN_CPO_MEETING_STD,
- Named account → PL_NAMED_ACCOUNT_SOFT,
- Executive + PL → PL_EXEC_MARGIN_MEETING.

---

### 14.5. Czego agent nie powinien robić

Nie powinien:

- tworzyć nowej sekwencji dla każdego triggera,
- wybierać sekwencji tylko po dostępności emaila,
- ignorować persony,
- wysyłać named accounts do agresywnej sekwencji,
- podejmować decyzji o wysyłce, jeśli QA nie zatwierdziło wiadomości.

---

## 15. Agent 11: Sequencer / Follow-up Agent

### 15.1. Cel agenta

Sequencer Agent tworzy logiczne follow-upy, które rozwijają pierwszą wiadomość.

Follow-up nie ma być pustym przypomnieniem.

---

### 15.2. Input

Agent otrzymuje:

- pierwszy mail,
- persona,
- hipoteza,
- proof point,
- trigger,
- typ sekwencji,
- liczba kroków.

---

### 15.3. Output

Agent zwraca:

```json
{
  "followup_1": "Treść follow-upu z nowym kątem.",
  "followup_2": "Krótkie pytanie diagnostyczne.",
  "followup_3": "Zamknięcie pętli.",
  "followup_strategy": "Każdy follow-up wnosi nową wartość."
}
```

---

### 15.4. Model follow-upów

Rekomendowany model:

- Follow-up 1: inny proof albo inna konsekwencja biznesowa,
- Follow-up 2: krótkie pytanie diagnostyczne,
- Follow-up 3: spokojne zamknięcie pętli.

---

### 15.5. Czego agent nie powinien robić

Nie powinien:

- pisać „podbijam",
- powtarzać pierwszej wiadomości,
- zwiększać presji,
- pisać zbyt długich follow-upów,
- zmieniać całkowicie tematu bez logiki.

---

## 16. Agent 12: Call Prep Agent

### 16.1. Cel agenta

Call Prep Agent przygotowuje sprzedawcę do rozmowy po pozytywnej odpowiedzi prospekta.

Nie pisze cold maila.
Nie robi nowego outreachu.

Jego zadaniem jest pomóc przeprowadzić dobrą rozmowę discovery.

---

### 16.2. Input

Agent otrzymuje:

- firmę,
- osobę,
- personę,
- poprzednie wiadomości,
- odpowiedź prospekta,
- account brief,
- hipotezę,
- dostępne dane,
- cel rozmowy.

---

### 16.3. Output

Agent zwraca:

```json
{
  "meeting_brief": "Krótki kontekst rozmowy.",
  "key_hypotheses_to_validate": [
    "Hipoteza 1",
    "Hipoteza 2"
  ],
  "discovery_questions": [
    "Pytanie 1",
    "Pytanie 2",
    "Pytanie 3"
  ],
  "likely_objections": [
    "Obiekcja 1"
  ],
  "suggested_agenda": [
    "1. Kontekst",
    "2. Obecny sposób przygotowania negocjacji",
    "3. Jedna kategoria lub dostawca",
    "4. Możliwy następny krok"
  ],
  "recommended_next_step": "Zaproponować analizę jednej kategorii / jednego dostawcy."
}
```

---

### 16.4. Pytania discovery

Agent powinien generować pytania o:

- obecny sposób przygotowania negocjacji,
- dane używane przez zespół,
- typowe podwyżki dostawców,
- najważniejsze kategorie,
- ryzyko dostawców,
- sposób oceny ofert,
- przewidywalność kosztów,
- standard pracy zespołu.

---

### 16.5. Czego agent nie powinien robić

Nie powinien:

- zakładać z góry potrzeb klienta,
- przygotowywać agresywnego pitcha,
- sugerować wdrożenia przed discovery,
- pomijać kontekstu pierwszej wiadomości.

---

## 17. Agent 13: CRM Note Agent

### 17.1. Cel agenta

CRM Note Agent tworzy krótką, uporządkowaną notatkę do CRM.

Nie tworzy nowej komunikacji sprzedażowej.
Nie interpretuje nadmiernie.

---

### 17.2. Input

Agent otrzymuje:

- dane firmy,
- dane osoby,
- personę,
- trigger,
- hipotezę,
- wysłaną wiadomość,
- odpowiedź,
- status,
- ustalenia z rozmowy,
- następny krok.

---

### 17.3. Output

Agent zwraca:

```json
{
  "company": "...",
  "contact": "...",
  "persona": "...",
  "trigger": "...",
  "hypothesis": "...",
  "last_touch_summary": "...",
  "current_status": "...",
  "next_step": "...",
  "owner_note": "..."
}
```

---

### 17.4. Czego agent nie powinien robić

Nie powinien:

- pisać długich notatek,
- dodawać niepotwierdzonych informacji,
- mieszać faktów z opiniami,
- zmieniać statusu bez podstawy.

---

## 18. Agent 14: Feedback & Learning Agent

### 18.1. Cel agenta

Feedback & Learning Agent analizuje wyniki kampanii i wskazuje, które elementy działają najlepiej.

Nie zmienia automatycznie strategii bez zatwierdzenia.

---

### 18.2. Input

Agent otrzymuje:

- wyniki kampanii,
- open rate,
- reply rate,
- positive reply rate,
- meeting rate,
- bounce rate,
- dane per persona,
- dane per trigger,
- dane per subject,
- dane per sekwencja.

---

### 18.3. Output

Agent zwraca:

```json
{
  "top_performing_personas": [],
  "top_performing_triggers": [],
  "weak_subject_lines": [],
  "messages_to_improve": [],
  "recommendations": [],
  "next_tests": []
}
```

---

### 18.4. Co powinien analizować

Agent powinien analizować:

- które persony odpowiadają najlepiej,
- które triggery generują spotkania,
- które CTA są zbyt ciężkie,
- które wiadomości brzmią zbyt generycznie,
- gdzie pojawia się bounce,
- czy sekwencje nie są zbyt długie,
- czy named accounts wymagają innego podejścia.

---

### 18.5. Czego agent nie powinien robić

Nie powinien:

- automatycznie zmieniać promptów bez akceptacji,
- wyciągać wniosków z małej próby jako pewników,
- optymalizować tylko pod open rate,
- ignorować jakości spotkań.

---

## 19. Minimalny zestaw agentów na start

Na start nie trzeba wdrażać wszystkich agentów.

Rekomendowany zestaw MVP:

1. Lead Scoring Agent
2. Account Research Agent
3. Persona Selection Agent
4. Hypothesis Agent
5. Message Writer Agent
6. QA / Anti-LLM Reviewer
7. Apollo Fields Agent
8. Sequence Router Agent

To wystarczy do uruchomienia pierwszej wersji systemu.

---

## 20. Kolejne agenty do dodania później

W kolejnych etapach warto dodać:

1. Dynamic Proof Agent
2. Sequencer Agent
3. Call Prep Agent
4. CRM Note Agent
5. Feedback & Learning Agent

---

## 21. Reguła jakości końcowej

Żaden agent nie powinien optymalizować wyłącznie pod ilość.

Każdy agent ma wspierać cel końcowy:

> dotrzeć do właściwej osoby z trafną hipotezą i umówić wartościową rozmowę.

Jeżeli agent nie potrafi uzasadnić, dlaczego dana wiadomość jest właściwa dla danej osoby, lead powinien trafić do manual review albo zostać odrzucony.
