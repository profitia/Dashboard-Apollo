# ICP Tier Examples — Przykłady użycia dla LLM

Plik referencyjny pokazujący, jak LLM powinien interpretować polecenia
kampanijne z Tierami i jak dopasować kontekst do odbiorcy.

---

## Przykład 1: Kampania Tier 1 — CEO sieci retail

**Input:**
"Przygotuj kampanię do Tier 1 dla CEO sieci retail"

**Expected context:**
- Mówić o marży, wzroście, budżecie, cash flow, strategii, ryzyku.
- Nie mówić o codziennym przygotowaniu kupca.
- Value proposition: kontrola marży i ryzyka kosztowego.
- Savings accountability: CEO odpowiada za wynik firmy - oczekuje, że zakupy dowiozą oszczędności.
- Pain points: presja na marżę, zmienność kosztów, rozjazd między strategią a zakupami.
- Ton: strategiczny, biznesowy, zarządczy.
- CTA: rozmowa o wpływie zakupów na wynik firmy.
- Unikać: "narzędzie dla kupców", "dashboard", "moduły SpendGuru".

**Przykładowy opening Email 1:**
"Dzień dobry Panie Marku, w sieciach handlowych wzrost sprzedaży często idzie w parze z rosnącą presją kosztową po stronie dostawców. W Pana roli jako CEO RetailMax kluczowe pytanie brzmi - ile z tego wzrostu faktycznie zostaje na marży firmy."

---

## Przykład 2: Kampania Tier 2 — Dyrektor Zakupów firmy produkcyjnej

**Input:**
"Przygotuj kampanię do Tier 2 dla dyrektora zakupów firmy produkcyjnej"

**Expected context:**
- Mówić o savings całej firmy, standardzie negocjacji, zespole, benchmarkach, unikniętych podwyżkach.
- Value proposition: systemowe dowożenie oszczędności przez powtarzalny standard negocjacji.
- Savings accountability: odpowiada przed zarządem / CFO / CEO za savings w skali firmy.
- Pain points: presja na dowiezienie oszczędności, kupcy przygotowują się różnie, brak powtarzalnego mechanizmu.
- Ton: procurementowy, zarządczy, praktyczny, metodyczny.
- CTA: rozmowa o POC dla jednej kategorii / jednego dostawcy.
- Unikać: zbyt ogólny język zarządczy, komunikacja jak do CFO.

**Przykładowy opening Email 1:**
"Dzień dobry Panie Janie, w firmie produkcyjnej z dużą ekspozycją na koszty surowców i opakowań, dowiezienie savings w wielu kategoriach jednocześnie to wyzwanie systemowe. Jako Dyrektor Zakupów FoodProduction Group odpowiada Pan za to, żeby standard przygotowania negocjacji był powtarzalny - niezależnie od doświadczenia poszczególnych kupców."

---

## Przykład 3: Kampania Tier 3 — Category Manager

**Input:**
"Przygotuj kampanię do Tier 3 dla category managera"

**Expected context:**
- Mówić o savings w kategorii, ocenie fair/unfair oferty, benchmarkach, cost drivers, argumentacji, czasie przygotowania.
- Value proposition: szybciej przygotować negocjacje i dowieźć wynik kategorii.
- Savings accountability: odpowiada przed przełożonym za savings i avoided cost w swojej kategorii.
- Pain points: podwyżki zjadają target, brak danych do obrony, za dużo improwizacji.
- Ton: praktyczny, konkretny, codzienny język kupca.
- CTA: pokazanie przykładu przygotowania do jednej negocjacji.
- Unikać: zbyt wysokopoziomowy język o strategii, odniesienia do EBIT i transformacji.

**Przykładowy opening Email 1:**
"Dzień dobry Panie Piotrze, w pracy z markami własnymi kluczowy jest każdy punkt procentowy marży. Jako Senior Category Manager w PrivateLabel Foods na co dzień ocenia Pan, czy cena dostawcy jest uzasadniona - i szuka argumentów, żeby ją obronić albo zakwestionować."

---

## Rozstrzyganie ról warunkowych

**Input:**
"Kontakt: Procurement Manager w dużej firmie, odpowiada za zespół 5 kupców"

**Rozstrzygnięcie:** Tier 2 (odpowiedzialność za zespół = management)

**Input:**
"Kontakt: Procurement Manager w małej firmie, sam prowadzi 3 kategorie"

**Rozstrzygnięcie:** Tier 3 (operacyjna praca z kategoriami bez zespołu)

---

## Jak dodać nową rolę do Tieru

1. Otwórz `source_of_truth/icp_tiers.yaml`.
2. Dodaj rolę w sekcji `roles` odpowiedniego Tieru.
3. Dodaj wpis w `role_to_tier_mapping` na dole pliku.
4. Jeśli rola jest warunkowa, dodaj ją w `conditional_roles` z opisem warunku.
5. Uruchom test: `python tests/test_icp_tiers.py`.

## Jak nadpisać Tier ręcznie przy kampanii

W konfiguracji kampanii (YAML) lub w poleceniu:
- "Użyj Tier 2 dla tego kontaktu" - wymusza Tier niezależnie od stanowiska.
- "Traktuj jako Tier 1" - nadpisuje automatyczny mapping.
- W output kampanii pole `tier_reason` pokaże "manual_override" lub "auto_detected".

## Jak sprawdzić, czy kampania użyła właściwego Tieru

1. W output JSON/CSV sprawdź pola: `tier`, `tier_label`, `tier_reason`.
2. W QA report sprawdź: `tier_alignment_pass`, `wrong_tier_language_detected`.
3. Uruchom test: `python tests/test_icp_tiers.py` - sprawdza mapping i walidację.
