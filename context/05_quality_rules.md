# 05_quality_rules.md
# Quality Rules: AI Outreach System

## 1. Rola tego dokumentu

Ten dokument definiuje zasady jakości dla wiadomości outboundowych, researchu, hipotez, scoringu i decyzji o dodaniu kontaktu do kampanii.

Jego celem jest zapewnienie, że system nie produkuje masowych, generycznych wiadomości, tylko pomaga tworzyć komunikację:

- trafną,
- wiarygodną,
- krótką,
- naturalną,
- dopasowaną do persony,
- opartą na faktach lub jasno oznaczonych hipotezach.

Najważniejsza zasada:

> Wiadomość może zostać wysłana tylko wtedy, gdy ma sensowny powód kontaktu, logiczną hipotezę i nie brzmi jak masowy mailing.

---

## 2. Ogólna zasada jakości

Każdy lead, hipoteza i wiadomość powinny przejść przez ocenę jakości.

System powinien preferować:

- mniej wiadomości, ale lepszych,
- mniej automatyzacji, ale większą trafność,
- mniej pitchowania, ale więcej kontekstu,
- mniej ogólników, ale więcej konkretu.

Jakość jest ważniejsza niż wolumen.

---

## 3. Minimalne warunki dopuszczenia leada do kampanii

Lead może przejść dalej tylko wtedy, gdy spełnia minimum jakościowe.

Wymagane warunki:

1. Firma pasuje do ICP kampanii.
2. Osoba pasuje do jednej z docelowych person.
3. Email jest dostępny i ma akceptowalny poziom pewności.
4. Istnieje przynajmniej minimalny kontekst do personalizacji.
5. Można zbudować logiczną hipotezę problemu.
6. Wiadomość może zostać dopasowana do persony.
7. Nie ma oczywistych ryzyk reputacyjnych.

Jeżeli którykolwiek z tych elementów jest słaby, lead powinien trafić do:

- manual review,
- light personalization,
- albo reject.

---

## 4. Kryteria oceny lead scoring

Lead Scoring Agent powinien oceniać leady w skali 0–100.

Rekomendowane kryteria:

| Kryterium | Waga |
|---|---:|
| Dopasowanie firmy do ICP | 20 |
| Dopasowanie persony | 20 |
| Seniority / wpływ decyzyjny | 15 |
| Siła triggera | 15 |
| Potencjał business case | 10 |
| Jakość danych kontaktowych | 10 |
| Dopasowanie branży | 5 |
| Dostępność kontekstu do personalizacji | 5 |

### Interpretacja wyniku

| Wynik | Decyzja |
|---:|---|
| 85–100 | Deep personalization / wysoki priorytet |
| 70–84 | Standard personalization |
| 50–69 | Light personalization lub manual review |
| <50 | Reject |

---

## 5. Kryteria jakości researchu

Account Research Agent powinien dostarczać krótki, użyteczny research, a nie długi raport.

Dobry research zawiera:

- krótkie podsumowanie firmy,
- 2–3 sygnały biznesowe,
- wskazanie potencjalnego triggera,
- możliwe implikacje dla zakupów, kosztów, dostawców lub marży,
- jasne oznaczenie poziomu pewności,
- oddzielenie faktów od hipotez.

Zły research:

- jest zbyt długi,
- kopiuje treści ze strony firmy,
- nie prowadzi do żadnej hipotezy,
- miesza fakty z domysłami,
- używa niepewnych danych jako pewników,
- nie pokazuje, dlaczego warto kontaktować się teraz.

---

## 6. Zasada faktów i hipotez

Każdy agent musi odróżniać:

- fakt,
- obserwację,
- hipotezę,
- rekomendację.

### Fakt

Informacja potwierdzona źródłem lub danymi.

Przykład:

> Firma ogłosiła budowę nowego zakładu.

### Obserwacja

Wniosek z dostępnych danych.

Przykład:

> Rozbudowa zakładu może zwiększać znaczenie stabilności dostaw.

### Hipoteza

Ostrożnie sformułowane przypuszczenie.

Przykład:

> Warto sprawdzić, czy warunki dostawców w kluczowych kategoriach nadal odzwierciedlają aktualne realia kosztowe.

### Rekomendacja

Propozycja działania.

Przykład:

> Rekomendowany kąt wiadomości: rozmowa o przygotowaniu negocjacji dla jednej kategorii.

Nie wolno pisać hipotezy jako faktu.

---

## 7. Kryteria dobrej hipotezy

Dobra hipoteza powinna być:

- logiczna,
- oparta na triggerze, personie lub branży,
- możliwa do obrony,
- nienachalna,
- sformułowana ostrożnie,
- powiązana z wartością Profitia / SpendGuru,
- prowadząca do krótkiej rozmowy.

Przykład dobrej hipotezy:

> Przy większej liczbie kategorii i dostawców trudno zapewnić, że każdy kupiec przygotowuje negocjacje według tej samej logiki i na podstawie porównywalnych danych.

Przykład złej hipotezy:

> Państwa kupcy prawdopodobnie przepłacają u dostawców.

Dlaczego zła:

- oskarża,
- nie ma dowodu,
- brzmi agresywnie,
- może zaszkodzić reputacji.

---

## 8. Kryteria jakości wiadomości

Każda wiadomość powinna być oceniana w skali 0–100.

Rekomendowane kryteria:

| Kryterium | Waga |
|---|---:|
| Dopasowanie do persony | 15 |
| Trafność triggera / powodu kontaktu | 15 |
| Jakość hipotezy | 15 |
| Naturalność języka | 15 |
| Konkret i zwięzłość | 10 |
| Jakość CTA | 10 |
| Wiarygodność / brak halucynacji | 10 |
| Brak generycznego języka | 5 |
| Brak nadmiernego pitchowania produktu | 5 |

### Interpretacja wyniku

| Wynik | Decyzja |
|---:|---|
| 85–100 | Approve |
| 70–84 | Rewrite |
| 50–69 | Manual review |
| <50 | Reject |

---

## 9. Minimalne warunki approve

Wiadomość może otrzymać status `approve` tylko wtedy, gdy:

1. Ma jasno określoną personę.
2. Ma powód kontaktu lub neutralną, uczciwą hipotezę.
3. Nie zaczyna od produktu.
4. Nie używa niepotwierdzonych faktów.
5. Jest krótka.
6. Ma jedno CTA.
7. Brzmi naturalnie.
8. Nie zawiera pustych fraz.
9. Nie brzmi jak masowy mailing.
10. Nie tworzy ryzyka reputacyjnego.

Jeżeli którykolwiek punkt jest niespełniony, wiadomość nie powinna przejść bez poprawy.

---

## 10. Automatyczne powody odrzucenia wiadomości

QA Agent powinien automatycznie oznaczyć wiadomość jako `reject`, jeśli zawiera:

- zmyślone fakty,
- zmyślone liczby,
- zmyślone case studies,
- niepotwierdzone twierdzenia o problemach firmy,
- agresywne lub oskarżające sformułowania,
- personalizację opartą na prywatnych informacjach,
- „creepy personalization",
- zbyt ciężkie CTA,
- brak hipotezy,
- brak persony,
- brak sensownego powodu kontaktu,
- język mocno masowy lub spamowy.

---

## 11. Powody do rewrite

QA Agent powinien oznaczyć wiadomość jako `rewrite`, jeśli:

- jest za długa,
- brzmi zbyt gładko lub sztucznie,
- ma zbyt ogólny opener,
- CTA jest zbyt ciężkie,
- za wcześnie pitchuje produkt,
- proof point jest niedopasowany,
- brakuje konkretu,
- język nie pasuje do persony,
- temat maila brzmi generycznie,
- follow-up powtarza pierwszy mail.

---

## 12. Powody do manual review

QA Agent powinien oznaczyć wiadomość jako `manual_review`, jeśli:

- konto jest strategiczne lub named account,
- dane są częściowo niepewne,
- trigger jest mocny, ale wymaga ostrożnej interpretacji,
- persona jest nietypowa,
- wiadomość jest dobra, ale ryzyko reputacyjne jest wyższe,
- używany jest konkretny proof point liczbowy,
- wiadomość odnosi się do wrażliwego kontekstu biznesowego, np. słabszych wyników lub restrukturyzacji.

---

## 13. Anti-LLM filter

QA Agent powinien wyłapywać język, który brzmi jak typowa treść wygenerowana przez AI.

Sygnały ostrzegawcze:

- zbyt gładkie zdania,
- dużo przymiotników,
- brak konkretu,
- powtarzalna struktura zdań,
- „w dynamicznie zmieniającym się otoczeniu",
- „kompleksowe rozwiązanie",
- „innowacyjne podejście",
- „synergie",
- „optymalizacja procesów" bez konkretu,
- przesadnie formalny ton,
- nadmierna liczba rzeczowników odczasownikowych.

Lepszy styl:

- krótkie zdania,
- konkret,
- ostrożna hipoteza,
- naturalne pytanie,
- brak przesadnego marketingu.

---

## 14. Lista zakazanych lub ryzykownych fraz

Unikać lub oznaczać do poprawy:

- innowacyjne rozwiązanie,
- kompleksowa platforma,
- synergia,
- rewolucja w zakupach,
- transformacja procurement,
- game changer,
- w dzisiejszych dynamicznych czasach,
- zoptymalizujemy Państwa procesy,
- gwarantujemy oszczędności,
- wiemy, że macie problem,
- na pewno przepłacacie,
- chciałbym zaprezentować demo,
- chciałbym przedstawić naszą ofertę,
- nasze AI automatyzuje negocjacje,
- szybkie demo naszej platformy,
- oferta współpracy,
- zwiększ oszczędności już dziś.

---

## 15. Ocena openeru

Dobry opener:

- jest krótki,
- odnosi się do realnego kontekstu,
- nie przesadza,
- prowadzi do hipotezy,
- nie brzmi jak sztuczna personalizacja.

Zły opener:

- jest ogólny,
- mógłby pasować do każdej firmy,
- brzmi jak wygenerowany masowo,
- odnosi się do zbyt prywatnych informacji,
- nie ma związku z dalszą treścią.

### Przykład dobrego openeru

> Widziałem informację o rozbudowie zakładu — przy takiej zmianie często rośnie znaczenie przewidywalności kosztów dostawców.

### Przykład słabego openeru

> Widzę, że Państwa firma dynamicznie się rozwija i stawia na innowacje.

---

## 16. Ocena CTA

Dobre CTA:

- jest małe,
- jest konkretne,
- nie wymaga dużego zaangażowania,
- odnosi się do jednego problemu,
- brzmi naturalnie.

Przykład:

> Czy ma sens krótka rozmowa o jednej kategorii, w której warto byłoby sprawdzić zasadność obecnych warunków?

Słabe CTA:

> Czy możemy umówić 60-minutowe demo naszej platformy?

Dlaczego słabe:

- za ciężkie,
- produktowe,
- zbyt wczesne,
- nie wynika z wiadomości.

---

## 17. Ocena proof pointu

Dobry proof point:

- jest krótki,
- jest prawdziwy,
- pasuje do persony,
- wzmacnia hipotezę,
- nie dominuje wiadomości.

Zły proof point:

- jest zmyślony,
- jest zbyt ogólny,
- jest niedopasowany,
- zawiera liczbę bez źródła,
- brzmi jak przechwałka,
- przeciąża mail.

Jeżeli proof point nie jest potwierdzony, użyć neutralnej wersji.

---

## 18. Ocena follow-upu

Dobry follow-up:

- wnosi nowy kąt,
- jest krótszy niż pierwszy mail,
- nie powtarza tej samej treści,
- zawiera jedno pytanie,
- nie zwiększa presji.

Zły follow-up:

- zaczyna się od „podbijam",
- pyta tylko „czy udało się zapoznać",
- kopiuje pierwszy mail,
- robi się coraz bardziej nachalny,
- jest dłuższy niż pierwszy mail.

---

## 19. Ocena wiadomości LinkedIn

Dobra wiadomość LinkedIn:

- jest krótka,
- jest naturalna,
- ma jeden kontekst,
- nie brzmi jak mail przeniesiony 1:1,
- kończy się lekkim pytaniem.

Słaba wiadomość LinkedIn:

- ma kilka długich akapitów,
- od razu sprzedaje produkt,
- zawiera dużo linków,
- brzmi jak automatyczna sekwencja,
- ma zbyt formalny ton.

---

## 20. Reguła długości

Rekomendowane długości:

| Typ wiadomości | Długość |
|---|---:|
| Pierwszy email | 70–120 słów |
| Follow-up | 40–90 słów |
| LinkedIn invite note | 200–300 znaków |
| LinkedIn message | 250–500 znaków |
| Break-up email | 40–80 słów |

Jeżeli wiadomość przekracza rekomendowaną długość o więcej niż 25%, QA Agent powinien oznaczyć ją do skrócenia.

---

## 21. Reguła jednego CTA

Każda wiadomość powinna mieć tylko jedno CTA.

Nie łączyć w jednej wiadomości:

- spotkania,
- demo,
- przesłania materiałów,
- rozmowy z inną osobą,
- zaproszenia na webinar,
- prośby o opinię,
- linku do strony.

Jedna wiadomość = jeden następny krok.

---

## 22. Reguła jednej głównej myśli

Każda wiadomość powinna mieć jeden główny temat.

Nie łączyć w jednym mailu:

- podwyżek,
- ryzyka dostawcy,
- prognoz,
- AI,
- benchmarków,
- modułów,
- POC,
- warsztatu,
- CIPS.

Jeżeli wiadomość ma więcej niż jeden temat, QA powinien wymusić uproszczenie.

---

## 23. Reguła braku wczesnego pitchowania produktu

Pierwszy mail nie powinien zaczynać się od:

- SpendGuru,
- Profitii,
- funkcjonalności,
- modułów,
- demo,
- platformy,
- AI.

Produkt może pojawić się dopiero po zbudowaniu kontekstu i hipotezy.

Dobra kolejność:

1. Sytuacja / trigger.
2. Hipoteza.
3. Wartość.
4. CTA.

---

## 24. Reguła neutralnego openeru

Jeżeli brak twardego triggera, nie udawać personalizacji.

Zamiast wymyślać kontekst, użyć neutralnego openeru:

> Piszę z krótką hipotezą dotyczącą przygotowania negocjacji zakupowych w firmach o podobnej skali.

Lepsza uczciwa neutralność niż sztuczna personalizacja.

---

## 25. Reguła named accounts

Dla strategicznych kont obowiązują wyższe standardy.

Named accounts powinny mieć:

- głębszy research,
- manual review,
- krótszą sekwencję,
- ostrożniejsze hipotezy,
- bardziej miękki ton,
- brak agresywnych follow-upów.

Nie wolno automatycznie dodawać named accounts do standardowej sekwencji bez zatwierdzenia.

---

## 26. Reguła danych Apollo

Lead może przejść do wysyłki tylko wtedy, gdy:

- ma właściwą personę,
- ma adres email o akceptowalnej jakości,
- ma przypisaną sekwencję,
- ma wypełnione wymagane custom fields,
- ma QA score powyżej progu,
- nie ma flag ryzyka.

Brak któregokolwiek pola powinien blokować automatyczne dodanie do sekwencji.

---

## 27. Reguła custom fields

Przed dodaniem kontaktu do sekwencji Apollo należy sprawdzić, czy uzupełnione są wymagane pola:

- custom_subject_1,
- custom_opener_1,
- custom_problem_hypothesis_1,
- custom_cta_1,
- persona_type,
- trigger_summary,
- campaign_name,
- language_code,
- sequence_recommendation,
- qa_score.

Jeżeli sekwencja wykorzystuje follow-upy z dynamic variables, należy sprawdzić także pola dla kolejnych kroków.

Nie wolno podstawiać wartości:

- TBD,
- brak,
- do uzupełnienia,
- placeholder,
- lorem ipsum.

---

## 28. Reguła mailboxów

Wybór mailboxa powinien być zgodny z:

- językiem kampanii,
- personą,
- typem konta,
- obciążeniem skrzynki,
- regułami kampanii.

Nie wysyłać strategicznych kontaktów z przypadkowej skrzynki.

---

## 29. Reguła zgodności i reputacji

System powinien minimalizować ryzyko reputacyjne.

Nie wolno:

- używać danych prywatnych do personalizacji,
- pisać personalizacji, która brzmi jak stalking,
- sugerować, że firma ma problem, jeśli to tylko hipoteza,
- używać agresywnego języka,
- zmyślać relacji, spotkań lub wcześniejszych kontaktów,
- udawać, że wiadomość nie jest outboundem.

---

## 30. Reguła języka ostrożnego

Preferować język:

- „często pojawia się pytanie",
- „może być dobry moment, żeby sprawdzić",
- „w firmach o podobnej skali często widzimy",
- „warto zweryfikować",
- „może mieć wpływ na".

Unikać języka:

- „na pewno",
- „wiemy, że",
- „macie problem",
- „przepłacacie",
- „gwarantujemy".

---

## 31. Reguła oceny ryzyka

Każda wiadomość powinna otrzymać jedną z flag ryzyka:

- none,
- low,
- medium,
- high.

### None

Brak ryzyka, wiadomość bezpieczna.

### Low

Drobne ryzyko stylistyczne lub zbyt neutralna personalizacja.

### Medium

Niepewny trigger, delikatny kontekst, strategiczne konto lub liczbowy proof point.

### High

Niepewne fakty, wrażliwy kontekst, agresywna hipoteza, potencjalna szkoda reputacyjna.

Wiadomości z ryzykiem high nie powinny być wysyłane automatycznie.

---

## 32. Format wyniku QA

QA Agent powinien zwracać wynik w strukturze:

```json
{
  "qa_score": 88,
  "decision": "approve",
  "risk_level": "low",
  "strengths": [
    "Dobra personalizacja",
    "Jasna hipoteza",
    "Naturalne CTA"
  ],
  "issues": [],
  "required_changes": [],
  "final_recommendation": "approved_for_sequence"
}
```

Możliwe wartości decision:

- approve,
- rewrite,
- manual_review,
- reject.

---

## 33. Przykład wyniku rewrite

```json
{
  "qa_score": 74,
  "decision": "rewrite",
  "risk_level": "low",
  "strengths": [
    "Dobra persona",
    "Sensowny kierunek komunikacji"
  ],
  "issues": [
    "Wiadomość jest za długa",
    "CTA brzmi jak demo produktu",
    "Za wcześnie pojawia się SpendGuru"
  ],
  "required_changes": [
    "Skrócić do maksymalnie 110 słów",
    "Przenieść produkt na dalszy plan",
    "Zamienić CTA na krótką rozmowę o jednej kategorii"
  ],
  "final_recommendation": "rewrite_before_sequence"
}
```

---

## 34. Przykład wyniku reject

```json
{
  "qa_score": 42,
  "decision": "reject",
  "risk_level": "high",
  "strengths": [],
  "issues": [
    "Wiadomość zawiera niepotwierdzone twierdzenie, że firma przepłaca",
    "Brak realnego triggera",
    "Brzmi jak masowy mailing",
    "CTA jest zbyt ciężkie"
  ],
  "required_changes": [
    "Zbudować nową hipotezę",
    "Usunąć oskarżające sformułowania",
    "Użyć neutralnego openeru"
  ],
  "final_recommendation": "do_not_send"
}
```

---

## 35. Minimalna checklista przed dodaniem do Apollo Sequence

Kontakt może zostać dodany do sekwencji tylko wtedy, gdy:

- lead_score >= próg kampanii,
- qa_score >= próg kampanii,
- decision = approve,
- risk_level ≠ high,
- email jest zweryfikowany lub akceptowalny,
- persona_type jest przypisane,
- sequence_recommendation jest przypisane,
- wszystkie wymagane custom fields są wypełnione,
- mailbox_group jest przypisany,
- brak flag manual review.

---

## 36. Reguła feedback loop

Po zakończeniu kampanii wyniki powinny być analizowane nie tylko ilościowo, ale jakościowo.

Mierzyć:

- reply rate,
- positive reply rate,
- meeting rate,
- bounce rate,
- unsubscribe / negative replies,
- jakość spotkań,
- skuteczność person,
- skuteczność triggerów,
- skuteczność CTA,
- skuteczność subject lines.

Nie optymalizować wyłącznie pod open rate.

Najważniejsze metryki:

- positive reply rate,
- meeting rate,
- jakość rozmów.

---

## 37. Reguła uczenia się

Feedback & Learning Agent może rekomendować zmiany, ale nie powinien automatycznie zmieniać:

- pozycjonowania,
- promptów głównych,
- reguł QA,
- sekwencji Apollo,
- CTA,
- person.

Zmiany strategiczne powinny wymagać akceptacji człowieka.

---

## 38. Najważniejsza zasada końcowa

Jeżeli wiadomość nie spełnia testu:

> Czy odbiorca może uznać, że ta wiadomość została napisana do niego na podstawie sensownego kontekstu biznesowego?

to wiadomość nie powinna zostać wysłana.

System ma zwiększać jakość rozmów sprzedażowych, a nie tylko liczbę wysłanych maili.
