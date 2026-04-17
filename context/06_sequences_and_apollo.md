# 06_sequences_and_apollo.md
# Sequences & Apollo: AI Outreach System

## 1. Rola tego dokumentu

Ten dokument opisuje, jak system AI Outreach ma współpracować z Apollo.

Apollo odpowiada za:

- wyszukiwanie firm i osób,
- enrichment,
- adresy email,
- kontakty,
- sekwencje,
- wysyłkę maili,
- obsługę skrzynek pocztowych,
- podstawowe statystyki kampanii.

VS Code i agenci AI odpowiadają za:

- logikę kampanii,
- wybór właściwej osoby,
- scoring,
- research,
- hipotezę,
- personalizację,
- treść wiadomości,
- QA,
- przygotowanie pól personalizacyjnych,
- routing do sekwencji.

Najważniejsza zasada:

> Apollo jest warstwą danych i wykonania.  
> Agenci AI są warstwą selekcji, interpretacji, personalizacji i kontroli jakości.

---

## 2. Główna zasada pracy z Apollo

Nie należy tworzyć osobnej sekwencji dla każdego triggera, branży, newsu lub firmy.

Sekwencja w Apollo powinna być traktowana jako:

- szkielet wykonawczy,
- harmonogram kroków,
- rytm follow-upów,
- kontener dla dynamic variables,
- mechanizm wysyłki.

Personalizacja powinna być generowana przez agentów i zapisywana w custom fields kontaktu.

Czyli:

> Sekwencja = struktura kampanii.  
> Custom fields = unikalna treść dla konkretnego kontaktu.

---

## 3. Docelowy model

Docelowy przepływ:

```text
VS Code task
→ Apollo Organization Search / input CSV
→ Apollo People Search
→ Apollo Enrichment
→ Lead Scoring Agent
→ Persona Selection Agent
→ Account Research Agent
→ Hypothesis Agent
→ Message Writer Agent
→ QA Agent
→ Apollo Fields Agent
→ Sequence Router Agent
→ Create / Update Contact in Apollo
→ Add Contact to Apollo Sequence
→ Apollo sends emails
→ Results are analyzed
```

Apollo wysyła wiadomości z podpiętych skrzynek pocztowych.
Agenci AI nie wysyłają maili bezpośrednio.

---

## 4. Podział odpowiedzialności

### 4.1. Apollo

Apollo odpowiada za:

- bazę firm,
- bazę osób,
- email enrichment,
- status emaila,
- zapis kontaktu,
- dodanie kontaktu do sekwencji,
- wysyłkę wiadomości,
- follow-upy zgodnie z sekwencją,
- mailbox rotation lub wybór skrzynki,
- podstawowe metryki kampanii.

### 4.2. Agenci AI

Agenci odpowiadają za:

- ocenę, czy lead jest wart kontaktu,
- wybór najlepszej osoby w firmie,
- interpretację triggera,
- budowę hipotezy,
- dobór proof pointu,
- stworzenie personalizacji,
- przygotowanie treści do custom fields,
- ocenę jakości,
- rekomendację sekwencji,
- przygotowanie call prep po odpowiedzi.

---

## 5. Źródła danych

System może korzystać z kilku źródeł wejściowych.

### 5.1. CSV z listą firm

Najprostszy wariant.

Plik może zawierać:

- company_name,
- company_domain,
- country,
- industry,
- account_priority,
- notes,
- target_persona,
- campaign_name.

### 5.2. Apollo Organization Search

Wariant, w którym Apollo wyszukuje firmy po filtrach.

Przykładowe kryteria:

- branża,
- lokalizacja,
- liczba pracowników,
- revenue,
- technologie,
- słowa kluczowe,
- segment rynku.

### 5.3. Apollo People Search

Wariant, w którym Apollo wyszukuje osoby w wybranych firmach.

Przykładowe kryteria:

- domena firmy,
- tytuły stanowisk,
- seniority,
- dział,
- kraj,
- lokalizacja,
- dostępność emaila.

### 5.4. Dane wewnętrzne

System może korzystać również z:

- CRM,
- wcześniejszych notatek,
- list named accounts,
- list konferencyjnych,
- odpowiedzi z kampanii,
- ręcznych dopisków użytkownika.

---

## 6. Rekomendowany model sekwencji

Na start zalecane są 4 główne sekwencje.

### 6.1. PL_CPO_MEETING_STD

Dla:

- Dyrektor Zakupów,
- CPO,
- Head of Procurement,
- Procurement Director,
- Purchasing Director.

Cel:

- umówienie pierwszej rozmowy o jakości przygotowania negocjacji.

Charakter:

- strategiczny,
- zarządczy,
- skoncentrowany na standardzie pracy zespołu,
- kontrola nad jakością negocjacji,
- ochrona marży i budżetu.

Rekomendowana liczba kroków:

- 3–4.

### 6.2. PL_BUYER_MEETING_STD

Dla:

- Kupiec,
- Category Manager,
- Senior Buyer,
- Sourcing Manager,
- Procurement Manager.

Cel:

- rozmowa o praktycznym przygotowaniu negocjacji dla jednej kategorii lub jednego dostawcy.

Charakter:

- praktyczny,
- konkretny,
- operacyjny,
- blisko codziennej pracy kupca.

Rekomendowana liczba kroków:

- 3.

### 6.3. PL_NAMED_ACCOUNT_SOFT

Dla:

- strategiczne konta,
- duże firmy,
- firmy o wysokiej wartości potencjalnej,
- kontakty wymagające ostrożnego podejścia.

Cel:

- miękkie otwarcie relacji.

Charakter:

- bardziej indywidualny,
- mniej automatyczny,
- krótszy,
- ostrożniejszy.

Rekomendowana liczba kroków:

- 2.

Wymagane:

- manual review przed dodaniem do sekwencji.

### 6.4. EN_CPO_MEETING_STD

Dla:

- anglojęzyczni decydenci zakupowi,
- CPO,
- Procurement Director,
- Head of Procurement.

Cel:

- first meeting around negotiation preparation, supplier cost pressure and data-based procurement decisions.

Charakter:

- strategiczny,
- biznesowy,
- bez ciężkiego pitchowania produktu.

Rekomendowana liczba kroków:

- 3.

---

## 7. Sekwencje opcjonalne do dodania później

Po MVP można dodać kolejne sekwencje:

### 7.1. PL_EXEC_MARGIN_MEETING

Dla:

- CFO,
- CEO,
- zarząd,
- właściciel.

Cel:

- rozmowa o ochronie marży, kontroli kosztów i zasadności podwyżek dostawców.

### 7.2. PL_FINANCE_COST_CONTROL

Dla:

- CFO,
- Finance Director,
- Controlling Manager.

Cel:

- rozmowa o przewidywalności kosztów, budżecie i wpływie zakupów na wynik.

### 7.3. PL_SUPPLY_CHAIN_TCO

Dla:

- Supply Chain,
- Operations,
- Logistics.

Cel:

- rozmowa o TCO, kosztach zapasu, timing decyzji zakupowych i ryzyku dostawców.

### 7.4. PL_REENGAGE_WARM

Dla:

- osoby po wcześniejszym kontakcie,
- osoby po wydarzeniu,
- kontakty z LinkedIn,
- osoby, które znały Profitia / SpendGuru.

Cel:

- reaktywacja rozmowy.

---

## 8. Zasada wyboru sekwencji

Sekwencję wybiera się na podstawie:

1. persony,
2. języka,
3. typu kampanii,
4. priorytetu konta,
5. poziomu personalizacji,
6. potrzeby manual review.

Nie wybierać sekwencji na podstawie samego triggera.

Trigger zasila treść wiadomości, a nie strukturę sekwencji.

Przykład:

```
Persona: CPO
Language: PL
Campaign type: standard outbound
→ sequence: PL_CPO_MEETING_STD

Persona: Buyer
Language: PL
Campaign type: standard outbound
→ sequence: PL_BUYER_MEETING_STD

Persona: CPO
Language: PL
Account priority: strategic
→ sequence: PL_NAMED_ACCOUNT_SOFT
```

---

## 9. Custom fields jako warstwa personalizacji

Personalizacja powinna trafiać do custom fields w Apollo.

Template w sekwencji powinien korzystać z dynamic variables opartych o te pola.

Przykład:

```
{{custom_opener_1}}

{{custom_problem_hypothesis_1}}

{{custom_proof_1}}

{{custom_cta_1}}
```

Dzięki temu wiele kontaktów może być w tej samej sekwencji, ale każdy otrzymuje inną wiadomość.

---

## 10. Minimalny zestaw custom fields

### 10.1. Pola dla pierwszego maila

- custom_subject_1
- custom_opener_1
- custom_problem_hypothesis_1
- custom_proof_1
- custom_cta_1

### 10.2. Pola dla drugiego kroku

- custom_subject_2
- custom_followup_angle_2
- custom_proof_2
- custom_cta_2

### 10.3. Pola dla trzeciego kroku

- custom_subject_3
- custom_close_loop_3
- custom_cta_3

### 10.4. Pola sterujące

- trigger_type
- trigger_summary
- persona_type
- campaign_name
- language_code
- sequence_recommendation
- mailbox_group
- lead_score
- qa_score
- risk_level
- personalization_level
- manual_review_required

---

## 11. Zalecany template pierwszego maila w Apollo

Subject:

```
{{custom_subject_1}}
```

Body:

```
Dzień dobry, {{first_name}},

{{custom_opener_1}}

{{custom_problem_hypothesis_1}}

{{custom_proof_1}}

{{custom_cta_1}}

Pozdrawiam,
{{sender_first_name}}
```

Uwaga:

Jeżeli wiadomość jest w języku angielskim, template musi mieć angielskie powitanie i podpis.

---

## 12. Zalecany template follow-up 1

Subject:

```
{{custom_subject_2}}
```

Body:

```
Dzień dobry, {{first_name}},

{{custom_followup_angle_2}}

{{custom_proof_2}}

{{custom_cta_2}}

Pozdrawiam,
{{sender_first_name}}
```

Follow-up 1 powinien wnosić nowy kąt, a nie powtarzać pierwszego maila.

---

## 13. Zalecany template follow-up 2 / close loop

Subject:

```
{{custom_subject_3}}
```

Body:

```
Dzień dobry, {{first_name}},

{{custom_close_loop_3}}

{{custom_cta_3}}

Pozdrawiam,
{{sender_first_name}}
```

Close loop powinien być spokojny i bez presji.

---

## 14. Alternatywny model: pełna treść w custom field

Jeżeli Apollo template złożony z wielu zmiennych okaże się zbyt kruchy, można zastosować prostszy model.

Custom fields:

- custom_email_subject_1
- custom_email_body_1
- custom_email_subject_2
- custom_email_body_2
- custom_email_subject_3
- custom_email_body_3

Template w Apollo:

```
{{custom_email_body_1}}
```

Zaleta:

- większa elastyczność,
- łatwiejsza kontrola całości wiadomości,
- mniej problemów z pustymi fragmentami.

Wada:

- trudniejsza analiza poszczególnych elementów wiadomości,
- trudniej porównywać opener, proof i CTA osobno.

Rekomendacja:

Na start używać modelu z rozbiciem na pola, a dla bardzo spersonalizowanych named accounts rozważyć pełne body jako custom field.

---

## 15. Walidacja przed dodaniem do sekwencji

Kontakt może zostać dodany do sekwencji tylko wtedy, gdy:

- lead_score jest powyżej progu kampanii,
- qa_score jest powyżej progu kampanii,
- risk_level nie jest high,
- decision = approve,
- email jest dostępny i akceptowalny,
- persona_type jest przypisane,
- sequence_recommendation jest przypisane,
- mailbox_group jest przypisane,
- wymagane custom fields są uzupełnione,
- nie ma placeholderów typu TBD,
- manual_review_required = false.

Jeśli którykolwiek warunek nie jest spełniony, kontakt nie powinien zostać automatycznie dodany do sekwencji.

---

## 16. Manual review

Manual review jest wymagany, gdy:

- konto jest strategiczne,
- lead ma wysoką wartość potencjalną,
- trigger dotyczy wrażliwego tematu,
- używany jest konkretny proof liczbowy,
- dane są częściowo niepewne,
- persona jest nietypowa,
- QA wskazuje ryzyko medium lub high,
- wiadomość zawiera silną hipotezę biznesową,
- kontakt ma trafić do sekwencji PL_NAMED_ACCOUNT_SOFT.

Manual review powinien zakończyć się decyzją:

- approve,
- rewrite,
- reject,
- hold.

---

## 17. Mailbox routing

Apollo obsługuje wysyłkę ze skrzynek pocztowych. System powinien rekomendować właściwą skrzynkę lub grupę skrzynek.

Mailbox routing powinien uwzględniać:

- język kampanii,
- personę,
- typ konta,
- właściciela relacji,
- obciążenie skrzynek,
- historię kontaktu,
- ryzyko reputacyjne.

Przykładowe grupy:

- pl_sales_primary
- pl_sales_secondary
- en_sales
- named_accounts
- reengagement

Reguła:

Sekwencji nie mnożymy przez skrzynki.
Skrzynka jest parametrem wykonawczym, nie osobną logiką kampanii.

---

## 18. Routing do sekwencji i mailboxa

Przykładowa logika:

```json
{
  "persona_type": "cpo",
  "language_code": "pl",
  "account_priority": "standard",
  "campaign_type": "outbound",
  "sequence_recommendation": "PL_CPO_MEETING_STD",
  "mailbox_group": "pl_sales_primary"
}
```

Dla named account:

```json
{
  "persona_type": "cpo",
  "language_code": "pl",
  "account_priority": "strategic",
  "campaign_type": "high_touch",
  "sequence_recommendation": "PL_NAMED_ACCOUNT_SOFT",
  "mailbox_group": "named_accounts",
  "manual_review_required": true
}
```

---

## 19. Recommended sequence routing table

| Persona | Language | Account priority | Campaign type | Sequence |
|---|---|---|---|---|
| CPO / Procurement Director | PL | Standard | Outbound | PL_CPO_MEETING_STD |
| Buyer / Category Manager | PL | Standard | Outbound | PL_BUYER_MEETING_STD |
| CPO / Procurement Director | PL | Strategic | High touch | PL_NAMED_ACCOUNT_SOFT |
| CPO / Procurement Director | EN | Standard | Outbound | EN_CPO_MEETING_STD |
| CFO / Finance | PL | Standard | Margin / Cost | PL_EXEC_MARGIN_MEETING |
| CEO / Owner | PL | Standard | Margin / Cost | PL_EXEC_MARGIN_MEETING |
| Supply Chain / Operations | PL | Standard | TCO / Risk | PL_SUPPLY_CHAIN_TCO |
| Warm contact | PL | Any | Reengagement | PL_REENGAGE_WARM |

---

## 20. Apollo contact lifecycle

Rekomendowany cykl życia kontaktu:

1. Person found in Apollo.
2. Person enriched.
3. Persona selected.
4. Lead scored.
5. Content generated.
6. QA completed.
7. Custom fields prepared.
8. Contact created or updated in Apollo.
9. Contact added to proper sequence.
10. Apollo sends emails.
11. Reply / outcome tracked.
12. Feedback added to CRM / outputs.

---

## 21. Contact status

System powinien przypisywać status techniczny kontaktu.

Rekomendowane statusy:

- found
- enriched
- scored
- selected
- content_generated
- qa_approved
- ready_for_sequence
- added_to_sequence
- replied
- meeting_booked
- rejected
- manual_review
- do_not_contact

---

## 22. Do-not-contact rules

Nie dodawać kontaktu do sekwencji, jeśli:

- firma jest na liście wykluczeń,
- osoba jest na liście wykluczeń,
- kontakt wcześniej odpisał negatywnie,
- kontakt jest już w aktywnej sekwencji,
- istnieje otwarta rozmowa sprzedażowa,
- email jest niepewny,
- osoba nie pasuje do persony,
- QA decision nie jest approve,
- risk_level = high,
- brak wymaganych custom fields.

---

## 23. Duplicate handling

Przed dodaniem do sekwencji należy sprawdzić:

- czy kontakt już istnieje w Apollo,
- czy kontakt jest już w innej aktywnej sekwencji,
- czy firma jest już aktywnie kontaktowana,
- czy ktoś z zespołu ma otwartą relację,
- czy kontakt był już wcześniej targetowany w podobnej kampanii.

Reguła:

Nie wysyłać tej samej lub podobnej wiadomości do kilku osób w jednej firmie bez świadomej strategii account-based.

---

## 24. Multi-person outreach w jednej firmie

Dopuszczalne jest kontaktowanie kilku osób z jednej firmy, ale tylko jeśli:

- mają różne role,
- otrzymują różne wiadomości,
- komunikacja nie wygląda jak masowy atak,
- istnieje jasna logika account-based,
- wysyłki są rozłożone w czasie.

Nie wysyłać identycznej wiadomości do CPO, CFO i kupca.

Każda persona musi mieć inną:

- hipotezę,
- CTA,
- proof point,
- poziom szczegółowości.

---

## 25. Dane zwracane przez pipeline do Apollo

Przykładowy obiekt gotowy do zapisu:

```json
{
  "contact": {
    "first_name": "Jan",
    "last_name": "Kowalski",
    "title": "Procurement Director",
    "email": "jan.kowalski@example.com",
    "company": "Example SA",
    "domain": "example.com"
  },
  "routing": {
    "persona_type": "cpo",
    "language_code": "pl",
    "sequence_recommendation": "PL_CPO_MEETING_STD",
    "mailbox_group": "pl_sales_primary"
  },
  "quality": {
    "lead_score": 88,
    "qa_score": 91,
    "risk_level": "low",
    "manual_review_required": false
  },
  "custom_fields": {
    "custom_subject_1": "Pytanie o przygotowanie negocjacji",
    "custom_opener_1": "Widziałem informację o rozbudowie zakładu...",
    "custom_problem_hypothesis_1": "Przy takiej zmianie często pojawia się pytanie...",
    "custom_proof_1": "W takich projektach zwykle zaczynamy od jednej kategorii...",
    "custom_cta_1": "Czy ma sens krótka rozmowa...",
    "trigger_type": "expansion",
    "trigger_summary": "Firma rozbudowuje zakład.",
    "campaign_name": "procurement_director_pl"
  }
}
```

---

## 26. Naming convention dla sekwencji

Zalecany format:

```
LANG_PERSONA_GOAL_VARIANT
```

Przykłady:

```
PL_CPO_MEETING_STD
PL_BUYER_MEETING_STD
PL_NAMED_ACCOUNT_SOFT
EN_CPO_MEETING_STD
PL_EXEC_MARGIN_MEETING
PL_SUPPLY_CHAIN_TCO
PL_REENGAGE_WARM
```

Nie używać nazw typu:

```
Kampania 1
Test 2
News trigger
Nowa sekwencja
```

Nazwa sekwencji ma pozwalać od razu zrozumieć:

- język,
- personę,
- cel,
- wariant.

---

## 27. Naming convention dla kampanii w configach

Zalecany format:

```
persona_language_segment_month
```

Przykłady:

```
cpo_pl_manufacturing_2026_04
buyer_pl_fmcg_2026_04
cpo_en_enterprise_2026_05
named_pl_top_accounts_2026_04
```

---

## 28. Sequence steps: CPO standard

Sequence: PL_CPO_MEETING_STD

Krok 1:

- mocno personalizowany mail,
- trigger lub neutralna hipoteza,
- nacisk na jakość przygotowania negocjacji.

Krok 2:

- inny kąt: standard pracy zespołu / przewidywalność / podwyżki dostawców,
- krótki proof lub insight.

Krok 3:

- pytanie diagnostyczne,
- niskie CTA.

Krok 4 opcjonalny:

- spokojne zamknięcie pętli.

---

## 29. Sequence steps: Buyer standard

Sequence: PL_BUYER_MEETING_STD

Krok 1:

- konkretny problem kupca,
- podwyżka, oferta, argumentacja, benchmark.

Krok 2:

- przykład praktycznego use case,
- ocena fair oferty lub cost drivers.

Krok 3:

- krótkie pytanie, czy warto sprawdzić jedną kategorię.

---

## 30. Sequence steps: Named account soft

Sequence: PL_NAMED_ACCOUNT_SOFT

Krok 1:

- bardzo indywidualny mail,
- miękki ton,
- bez ciężkiego CTA.

Krok 2:

- krótki follow-up,
- bez presji.

Wymagania:

- manual review,
- wysoka jakość researchu,
- brak automatycznego „podbijania".

---

## 31. Sequence steps: Executive margin

Sequence: PL_EXEC_MARGIN_MEETING

Krok 1:

- krótko o marży, kosztach i wpływie zakupów na wynik.

Krok 2:

- weryfikacja zasadności podwyżek / przewidywalność kosztów.

Krok 3:

- pytanie o aktualność tematu.

Nie wchodzić w szczegóły modułów.

---

## 32. Subject line rules

Subject line powinien być:

- krótki,
- spokojny,
- bez clickbaitu,
- bez przesadnych obietnic,
- dopasowany do persony.

Przykłady:

```
Pytanie o negocjacje z dostawcami
Przygotowanie negocjacji zakupowych
Jedna kategoria / jeden dostawca
Weryfikacja podwyżek dostawców
Krótka hipoteza dot. kosztów dostawców
```

Nie używać:

```
Rewolucja w zakupach
Zwiększ oszczędności już dziś
Demo SpendGuru
Oferta współpracy
Pilne
```

---

## 33. Apollo template safety rules

Każdy template w Apollo powinien mieć:

- sprawdzone dynamic variables,
- brak pustych placeholderów,
- poprawne powitanie,
- poprawny podpis,
- zgodność języka z kampanią,
- fallback albo blokadę wysyłki przy pustym polu.

Nie dopuszczać template'u, który może wysłać wiadomość typu:

```
Dzień dobry, ,
{{custom_opener_1}}
```

lub:

```
Dzień dobry, Jan,

TBD

Pozdrawiam
```

---

## 34. Fallback content

Jeżeli brakuje personalizacji, nie należy udawać triggera.

Fallback powinien być neutralny.

Przykład:

> Piszę z krótką hipotezą dotyczącą przygotowania negocjacji zakupowych w firmach o podobnej skali.

Fallback może być użyty tylko wtedy, gdy kampania dopuszcza light personalization.

Dla named accounts brak personalizacji oznacza manual review, nie fallback.

---

## 35. Outputy lokalne z pipeline'u

Każdy run kampanii powinien zapisywać lokalnie:

```
outputs/runs/YYYY-MM-DD_campaign_name/
  accounts_raw.json
  people_raw.json
  enriched_contacts.json
  selected_contacts.json
  generated_messages.json
  qa_results.json
  apollo_payloads.json
  approved.csv
  rejected.csv
  manual_review.csv
  run_report.md
```

---

## 36. Run report

Każdy run powinien generować raport:

```markdown
# Run Report

## Campaign
campaign_name

## Input
liczba firm
liczba osób

## Results
selected contacts
approved
rewrite
manual review
rejected

## Top rejection reasons
...

## QA summary
średni QA score
średni lead score

## Sequence routing
ile kontaktów do każdej sekwencji

## Issues
braki danych
puste pola
niepewne emaile
```

---

## 37. Tryby pracy

System powinien wspierać trzy tryby.

### 37.1. Draft mode

Tworzy wiadomości i raport, ale nic nie zapisuje do Apollo.

Używać do testów.

### 37.2. Prepare mode

Tworzy lub aktualizuje kontakty w Apollo i zapisuje custom fields, ale nie dodaje do sekwencji.

Używać do walidacji danych.

### 37.3. Launch mode

Tworzy / aktualizuje kontakt, zapisuje custom fields i dodaje do sekwencji.

Używać tylko po przetestowaniu kampanii.

---

## 38. Rekomendowany tryb MVP

Na start używać:

```
draft mode → manual review → prepare mode → manual approval → launch mode
```

Nie zaczynać od pełnego auto-launch.

---

## 39. Zasady auto-launch

Auto-launch jest dopuszczalny tylko wtedy, gdy:

- kampania była wcześniej testowana,
- lead_score >= 85,
- qa_score >= 85,
- risk_level = none lub low,
- email status jest akceptowalny,
- custom fields są kompletne,
- konto nie jest strategiczne,
- manual_review_required = false.

Wszystkie inne przypadki powinny trafić do review.

---

## 40. Feedback loop z Apollo

Po uruchomieniu kampanii należy analizować wyniki:

- open rate,
- reply rate,
- positive reply rate,
- meeting rate,
- bounce rate,
- unsubscribe,
- negative replies,
- sequence performance,
- persona performance,
- trigger performance,
- subject performance.

Nie optymalizować tylko pod open rate.

Najważniejsze są:

- positive reply rate,
- meeting rate,
- jakość rozmów.

---

## 41. Odpowiedzi i dalsze kroki

Po pozytywnej odpowiedzi:

1. zatrzymać dalsze automatyczne follow-upy, jeśli Apollo tego nie robi automatycznie,
2. uruchomić Call Prep Agent,
3. przygotować mini briefing,
4. zaproponować termin lub przejść do ręcznej obsługi,
5. zapisać notatkę do CRM.

Po negatywnej odpowiedzi:

1. oznaczyć jako do_not_contact lub not_interested,
2. nie kontynuować sekwencji,
3. nie wysyłać kolejnych follow-upów,
4. zapisać powód, jeśli dostępny.

---

## 42. Response classification

Odpowiedzi powinny być klasyfikowane jako:

- positive_reply,
- meeting_request,
- referral,
- not_now,
- not_interested,
- out_of_office,
- wrong_person,
- unsubscribe,
- negative_reply,
- unclear.

Dla każdej klasy rekomendowany następny krok:

**positive_reply**

- zatrzymaj sekwencję,
- przygotuj call prep,
- odpowiedz ręcznie.

**meeting_request**

- zatrzymaj sekwencję,
- zaproponuj termin,
- przygotuj call prep.

**referral**

- zapisz nową osobę,
- przygotuj personalizowany follow-up do wskazanej osoby.

**not_now**

- zapisz timing,
- zaplanuj reengagement.

**wrong_person**

- poproś o właściwą osobę lub znajdź fallback w Apollo.

**unsubscribe / negative_reply**

- oznacz do_not_contact,
- nie kontynuuj.

---

## 43. Integracja z CRM

Jeżeli pipeline integruje się z CRM, powinien zapisywać:

- firmę,
- osobę,
- personę,
- trigger,
- hipotezę,
- sekwencję,
- status,
- ostatni touchpoint,
- odpowiedź,
- następny krok,
- ownera.

Minimalna notatka CRM:

```
Persona: CPO
Trigger: rozbudowa zakładu
Hipoteza: większa skala może zwiększać znaczenie przewidywalności kosztów i standardu przygotowania negocjacji.
Wysłano: PL_CPO_MEETING_STD
Status: waiting for reply
Next step: follow-up in sequence
```

---

## 44. Bezpieczeństwo danych

Nie zapisywać w plikach:

- haseł,
- tokenów API,
- kluczy API,
- danych prywatnych niepotrzebnych do kampanii.

Dane wrażliwe powinny być przechowywane w:

- .env,
- bezpiecznym secrets managerze,
- ustawieniach środowiskowych.

Plik .env nie powinien być commitowany do repozytorium.

---

## 45. Minimalne zmienne środowiskowe

Przykład:

```
APOLLO_API_KEY=
APOLLO_BASE_URL=
DEFAULT_MAILBOX_GROUP=
DEFAULT_SEQUENCE_PL_CPO=
DEFAULT_SEQUENCE_PL_BUYER=
DEFAULT_SEQUENCE_PL_NAMED=
DEFAULT_SEQUENCE_EN_CPO=
```

---

## 46. Przykładowy config kampanii

```yaml
campaign_name: cpo_pl_manufacturing_2026_04
language_code: pl
target_persona: cpo
campaign_type: outbound
account_priority: standard

apollo:
  source: csv
  create_or_update_contact: true
  add_to_sequence: false
  mode: draft

filters:
  titles_include:
    - "Dyrektor Zakupów"
    - "Procurement Director"
    - "Head of Procurement"
    - "CPO"
  countries:
    - "PL"

quality:
  min_lead_score: 70
  min_qa_score: 85
  allow_manual_review: true
  reject_if_email_unverified: true

routing:
  default_sequence: PL_CPO_MEETING_STD
  default_mailbox_group: pl_sales_primary

personalization:
  required_fields:
    - custom_subject_1
    - custom_opener_1
    - custom_problem_hypothesis_1
    - custom_cta_1
```

---

## 47. Przykładowy tasks.json

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "AI Outreach: Draft CPO PL",
      "type": "shell",
      "command": "python src/run_campaign.py --config configs/cpo_pl_manufacturing_2026_04.yaml --mode draft",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "AI Outreach: Prepare Apollo",
      "type": "shell",
      "command": "python src/run_campaign.py --config configs/cpo_pl_manufacturing_2026_04.yaml --mode prepare",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "AI Outreach: Launch Apollo",
      "type": "shell",
      "command": "python src/run_campaign.py --config configs/cpo_pl_manufacturing_2026_04.yaml --mode launch",
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

---

## 48. Najważniejsze błędy do uniknięcia

Nie robić:

- jednej sekwencji per trigger,
- jednej sekwencji per firma,
- jednej sekwencji per skrzynka,
- wysyłki bez QA,
- auto-launch dla named accounts,
- maili bez wypełnionych custom fields,
- wiadomości z pustymi dynamic variables,
- kilku identycznych maili do jednej firmy,
- rozpoczynania wiadomości od produktu,
- używania Apollo tylko jako masowej wysyłarki.

---

## 49. Najważniejsza zasada końcowa

Apollo ma umożliwiać skalę i wysyłkę, ale nie może wymuszać generyczności.

Dlatego:

> Sekwencje powinny być proste i stabilne.
> Personalizacja powinna być głęboka i generowana per kontakt.
> QA powinno blokować wszystko, co wygląda jak masowy mailing.

Celem systemu nie jest wysłać więcej maili.

Celem systemu jest:

> wysłać mniej przypadkowych, a więcej trafnych wiadomości do właściwych osób — tak, aby zwiększyć liczbę jakościowych spotkań.
