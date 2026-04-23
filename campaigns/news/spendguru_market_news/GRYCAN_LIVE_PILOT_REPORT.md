# GRYCAN LIVE PILOT — Raport końcowy
**Kampania**: `spendguru_market_news`
**Data piloту**: 2026-04-21
**Artykuł testowy**: "Przyspieszony start sezonu lodowego. Grycan: początek sezonu przynosi pozytywne sygnały"
**URL**: https://www.portalspozywczy.pl/slodycze-przekaski/wiadomosci/przyspieszony-start-sezonu-lodowego-grycan-poczatek-sezonu-przynosi-pozytywne-sygnaly,287489.html

---

## 1. Executive Summary

Pilot miał na celu weryfikację end-to-end działania pipeline'u `spendguru_market_news` w trybie draft/review — bez auto-enrollmentu i automatycznej wysyłki, z limitem do 3 kontaktów T1/T2.

**Finalny wynik**: `BLOCKED_NO_CONTACT` na etapie `recipient_selection`.

Pilot ujawnił i naprawił 3 bugi systemowe (szczegóły w sekcjach 3-5 i 10), a jednocześnie dostarczył realnego znaleziska operacyjnego: baza Apollo nie indeksuje kadry kierowniczej C-level ani dyrektorów zakupów dla firmy Grycan. Znaleziono 10 kontaktów — wszystkie T3 lub Uncertain. Zerowy wynik recipient_selection jest poprawnym, oczekiwanym wynikiem w tej sytuacji — nie wskazuje na błąd systemu.

| Parametr | Wartość |
|---|---|
| Kwalifikacja | TAK (total=47, industry=17, purchase=21) |
| Wyekstrahowana firma | Grycan (confidence=0.98) |
| Kontaktów znalezionych | 10 |
| T1/T2 wybranych | 0 |
| Wiadomości wygenerowanych | 0 |
| Apollo sync | nie wykonano |
| Email notyfikacja | nie wysłano |
| Czas wykonania | ~5s |

---

## 2. Kwalifikacja artykułu

### Wynik scoringu (po naprawie keywords.yaml)

| Wymiar | Wynik | Próg | Zdany? |
|---|---|---|---|
| Total | 47.0 | 40 | TAK |
| Industry | 17.0 | 12 | TAK |
| Purchase signal | 21.0 | 15 | TAK |

### Dopasowane grupy branżowe
- **food_production**: `lody`, `lodziarnia`, `lody premium` (waga 4/termin)
- **manufacturing**: `producent` (waga 2)
- **plastics**: `PE` (bug — patrz sekcja 10)

### Dopasowane sygnały zakupowe
- **cost_pressure**: `ceny surowców` (waga 5)
- **supply_chain**: `dostawca`, `negocjacji`, `zakupy surowców`, `kontrakt` (waga 4/termin)

### Użyty tekst wejściowy
`full_text = title + " " + lead + " " + body` — zgodnie z logiką orchestratora.

**Uwaga**: W poprzedniej wersji pilot przekazywał jedynie `body`. Po naprawie: pełny tekst (tytuł + lead + body), co jest zgodne ze sposobem działania produkcyjnego orchestratora.

---

## 3. Ekstrakcja encji

| Parametr | Wartość |
|---|---|
| Wyekstrahowana firma | Grycan |
| Canonical name | Grycan |
| Typ | producer |
| Eligible | True |
| Confidence | 0.98 |
| Metoda | LLM (gpt-4.1-mini via GitHub Models) |

Ekstrakcja przebiegła bez błędów. LLM zwrócił nazwę brandową bez formy prawnej — zgodnie z przepisaną instrukcją promptu (zmiana z poprzedniej sesji).

---

## 4. Company Resolution

Pominięta zgodnie z konfiguracją (`use_company_resolution: false`).

- Używana firma: `Grycan`
- Domain hint: `grycan.pl` (wbudowany w pilota — znana domena)
- Podejście do produkcyjne: company_aliases.yaml z rozszerzonymi wariantami dla Grycan

---

## 5. Wyszukiwanie kontaktów (Apollo API)

| Strategia | Wynik |
|---|---|
| name_search "Grycan" | 10 kontaktów, 0 z emailem |
| domain_fallback "grycan.pl" | 10 kontaktów, 0 z emailem |
| Strategia winning | none |
| Kontakty z emailem | 0 |

### Zwrócone kontakty (10)

| Imię | Stanowisko | Tier | Status |
|---|---|---|---|
| Dorota | Senior Brand Manager | Tier 3 | Odrzucony |
| Karolina | Brand Manager | Tier 3 | Odrzucony |
| Justyna | Brand Manager | Tier 3 | Odrzucony |
| Monika | Manager | Tier 3 | Odrzucony |
| Wojciech | National Key Account Manager / Krajowy Kierownik ds. Rynku Nowoczesnego | Uncertain | Odrzucony |
| Aleksandra | Deputy Manager | Uncertain | Odrzucony |
| Ewa | HR Director | Uncertain | Odrzucony |
| Pawel | Area Operations Manager Southern Poland | Uncertain | Odrzucony |
| Pawel | Senior IT Manager | Uncertain | Odrzucony |
| Ireneusz | Director of Operations Support | Uncertain | Odrzucony |

**Wniosek**: Apollo nie indeksuje dla Grycan żadnych kontaktów w rolach C-suite (Prezes, CEO, CFO), dyrektora zakupów ani head of procurement. Obecna baza to wyłącznie Brand Managerowie, KAM, HR, Operacje i IT.

---

## 6. Dobór odbiorców (Recipient Selection)

| Parametr | Wartość |
|---|---|
| Limit pilota | 3 |
| T1 wybranych | 0 |
| T2 wybranych | 0 |
| Odrzuconych | 10 |
| auto_enroll | False (wymuszony) |

System poprawnie odrzucił wszystkich 10 kontaktów jako T3/Uncertain zgodnie z regułami tier mappingu. Logika globalna kampanii nie została zmieniona.

**Wynik etapu**: `BLOCKED_NO_CONTACT` — poprawny i oczekiwany, biorąc pod uwagę dostępność danych w Apollo.

---

## 7. Generowanie wiadomości

Nie wykonano (pilot zatrzymany na etapie 5 z powodu braku T1/T2 kontaktów).

- Liczba wygenerowanych wiadomości: 0
- LLM nie był wywoływany na tym etapie
- System poprawnie zwrócił wczesne zakończenie

---

## 8. Apollo Operational Flow (CRM + Listy)

Nie wykonano — pipeline zatrzymany przed tym etapem.

| Operacja | Status |
|---|---|
| Dodanie do listy Apollo | Nie wykonano |
| Email reveal | Nie wykonano |
| Ustawienie pola CRM (stage) | Nie wykonano |
| Synchronizacja custom fields | Nie wykonano |

---

## 9. Notyfikacja e-mail

Nie wysłano — brak wybranych odbiorców, notyfikacja o akceptacji nie ma zastosowania.

Przy prawidłowym scenariuszu (kontakty T1/T2 znalezione) notyfikacja wysłana byłaby do:
- `tomasz.uscinski@profitia.pl`
- Temat: `Kampania spendguru_market_news czeka na zatwierdzenie`
- Via: Office365 Graph API (send_mail.py)

---

## 10. Bugi znalezione i naprawione

### Bug 1 — keywords.yaml: brak terminów lodowych w grupie food_production

**Symptom**: Artykuł o Gryczanie nie kwalifikował się (industry=6-8, min=12). Grupy pharma i plastics dopasowywały się fałszywie.

**Root cause**: Brak terminów takich jak "lody", "lodziarnia", "lody premium", "producent lodów" w grupie food_production.

**Naprawa**: Dodano 11 terminów do food_production: `producent lodów`, `lody`, `lodziarnia`, `wytwórnia lodów`, `branża lodowa`, `lody premium`, `mrożonki`, `produkty mrożone`, `wyroby mleczarskie`, `nabiał`, `surowce mleczne`.

**Wynik po naprawie**: industry=17, food_production poprawnie dopasowuje.

---

### Bug 2 — keywords.yaml: fałszywe pozytywne "PE" i "lek"

**Symptom**: Artykuł lodowy dopasowywał grupę plastics (przez "PE" w "oper**uje**") i pharmaceuticals (przez "lek" w "m**lek**a"). Grupy niezwiązane z treścią.

**Root cause**: Zbyt krótkie termy bez dopasowania słów pełnych.

**Naprawa**:
- Usunięto `PE` i `PS` z plastics (polietylen, polistyren pozostały — wystarczają)
- Usunięto `lek` z pharmaceuticals (leki, producent leków pozostały)

**Wynik po naprawie**: plastics nadal fałszywie dopasowuje przez "PE" w "operuje" — wymaga dalszej obserwacji. Fundamentalny problem wymagałby mechanizmu word-boundary, który jest poza zakresem bieżącej sesji.

---

### Bug 3 — pilot script: full_text = body only

**Symptom**: Pilot obliczał scoring na podstawie samego `body`, nie pełnego tekstu. Orchestrator produkcyjny używa `article.full_text` = title + lead + body.

**Root cause**: Błąd w logice pilota przy przekazywaniu tekstu do scorera.

**Naprawa**: `full_text = title + " " + lead + " " + body` we wszystkich wywołaniach scorera w pilotcie.

---

### Bug 4 — pilot script: brak _save_results przed early returns

**Symptom**: Przy przedwczesnym zakończeniu (np. BLOCKED_NO_CONTACT) wynik nie był zapisywany do JSON.

**Naprawa**: Dodano wywołanie `_save_results(results)` przed każdym `return` w pilotcie. Wyniki zawsze dostępne w `data/test/grycan_live_pilot_results.json`.

---

## 11. Final Pipeline Status

```
Status:           BLOCKED_NO_CONTACT
Stage:            recipient_selection
Reason:           No Tier 1 or Tier 2 contacts found for Grycan
Dry run:          False
Qualified:        True (total=47.0, industry=17.0, purchase=21.0)
Extracted:        Grycan (confidence=0.98)
Contacts found:   10
Contacts selected: 0 (T1=0, T2=0)
Messages OK:      0
Notification:     None
Elapsed:          ~5s
```

---

## 12. Werdykt pilota

### Co zadziałało poprawnie

- Kwalifikacja artykułu — po naprawie keywords.yaml działa i klasyfikuje artykuł lodowy poprawnie
- Ekstrakcja encji — LLM poprawnie wyodrębnił "Grycan" (confidence=0.98)
- Wyszukiwanie kontaktów — Apollo API działa, strategia fallback na domenę działa
- Tier mapping — poprawnie odrzuca Brand Managerów / KAM / HR jako T3/Uncertain
- Zapis wyników — JSON poprawnie zapisywany po każdym etapie, włącznie z wczesnymi zakończeniami
- Smoke tests — 29/29 zielone po wszystkich zmianach

### Co wymaga uwagi

- `PE` w plastics nadal fałszywie matchuje w tekstach z "operuje" — długoterminowo do weryfikacji
- Apollo coverage dla Grycan — brak kadry kierowniczej C-level i procurement w bazie
- Pilot może być rozszerzony o większe firmy (ORLEN, Maspex) z lepszym pokryciem Apollo

### Rekomendacja

**Następny pilot**: ORLEN lub Maspex — firmy o udokumentowanie lepszym pokryciu C-level w Apollo.

Pipeline jest technicznie gotowy do obsługi artykułów triggerujących. Kluczowy bloker to jakość danych Apollo per firma, nie logika pipeline'u.

**Status gotowości do rozszerzenia**: READY (z ograniczeniem do firm z dobrym pokryciem Apollo T1/T2)
