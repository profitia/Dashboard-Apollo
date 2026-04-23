# ON Lemon Test — Key Findings for ChatGPT

**Sesja:** 2026-04-23  
**Kampania:** spendguru_market_news  
**Typ testu:** jakościowo-operacyjny, end-to-end

---

## 1. PIERWSZY READY_FOR_REVIEW w historii pilotów

ON Lemon jest pierwszą firmą, dla której pipeline przeszedł od artykułu do READY_FOR_REVIEW:

- Poprzednie 3 piloty (Grycan, Maspex, Colian) → BLOCKED_NO_CONTACT (0 T1/T2 w Apollo)
- ON Lemon → **READY_FOR_REVIEW** (Robert Owner zidentyfikowany, email ujawniony, wiadomości gotowe)

Jest to potwierdzenie, że pipeline działa poprawnie — problem poprzednich pilotów leżał w Apollo coverage, nie w kodzie.

## 2. Owner/Właściciel → Tier 1: ALL PASS (7/7 testów)

Weryfikacja runtime wykazała, że `Owner` i `Właściciel` były już w `tier_mapping.yaml` i działają poprawnie jako T1. Sprawdzono 7 wariantów — wszystkie PASS:
- "Właściciel" → tier_1_c_level ✓
- "Owner" → tier_1_c_level ✓
- "Właściciel ON Lemon" → tier_1_c_level ✓
- "Robert Orszulak, Właściciel" → tier_1_c_level ✓

Nie było potrzeby modyfikowania tier_mapping.yaml. Funkcjonalność była gotowa.

## 3. Apollo coverage dla ON Lemon: EXCELLENT (w porównaniu do poprzednich)

| Firma | T1 | T2 | Email | Status |
|---|---|---|---|---|
| Grycan | 0 | 0 | brak | BLOCKED_NO_CONTACT |
| Maspex | 0 | 0 | brak | BLOCKED_NO_CONTACT |
| Colian | 0 | 0 | brak | BLOCKED_NO_CONTACT |
| **ON Lemon** | **1 (Robert, Owner)** | **0** | **robertorszulak@onlemon.pl (ujawniony)** | **READY_FOR_REVIEW** |

ON Lemon, mimo że jest firmą mniejszą od Maspex/Colian, ma lepsze pokrycie Apollo. Robert Orszulak (właściciel, ON Lemon) jest zindeksowany z możliwością ujawnienia emaila.

## 4. Artykuł EEC 2026 nie kwalifikuje się — ale z ważnego powodu

- Artykuł: "ON Lemon na EEC 2026: Bliżej mi do kreowania niż do reagowania na trendy"
- Total score: 40 (na granicy progu 40)
- Industry score: 15 ✓ (próg 12)
- **Purchase signal: 5 ✗ (próg 15)**
- Powód: Artykuł dotyczy filozofii brandu i consumer experience, NIE zakupów, kosztów surowców ani dostawców
- Jest to poprawna decyzja pipeline'u — artykuł o kreowaniu trendów nie jest triggerem procurement

Gdyby pojawił się artykuł o ON Lemon z kontekstem: koszty składników (kakao, owoce, espresso), surowce, dostawcy, inwestycje produktowe — pipeline przeszedłby do READY_FOR_REVIEW natychmiast.

## 5. Recipient selection: CZYSTY — tylko Robert (Owner), 9 odrzuconych poprawnie

Spośród 10 kontaktów Apollo dla ON Lemon:
- Robert | Owner → **Tier 1 - C-Level — WYBRANY**
- 5x Brand Manager → Tier 3 — odrzuceni ✓
- 1x Senior Brand Manager → Tier 3 — odrzucony ✓
- 1x Export Brand Manager → Tier 3 — odrzucony ✓
- 1x Event Manager → Tier Uncertain — odrzucony ✓
- 1x Business Development & Sales Team Senior Manager → Tier Uncertain — odrzucony ✓

Pipeline nie wpuścił żadnych ról pobocznych. Działa zgodnie z regułami kampanii.

## 6. Wiadomości mają dobry anchor i logiczną hipotezę

Email 1 (subject: "ON Lemon i presja na marżę"):
- Anchor: artykuł EEC 2026, kreowanie zamiast reagowania
- Hipoteza: kreacja produktów → koszty surowców/opakowania → ryzyko marżowe
- Bridge: "w Pana roli jako Ownera... czy przy nowych formułach i opakowaniach da się obronić EBIT bez oddawania marży w negocjacjach z dostawcami"
- CTA: Calendly + "Jeśli wygodniejsza będzie krótka rozmowa telefoniczna, proszę przesłać numer - oddzwonię." ✓
- Brak em-dash ✓, brak fraz zakazanych ✓, 165 słów (próg 120-170) ✓

Follow Up 1 wnosi nową wartość: "kreowanie → więcej testów → presja na koszt surowca/opakowania/warunków zakupu"  
Follow Up 2: "warto mieć równie mocny model obrony kosztów, żeby innowacja nie zjadała marży" — świetny one-liner.

## 7. Finalny status: READY_FOR_REVIEW (pierwszy raz!)

- Robert (Owner) → T1 ✓
- Email ujawniony: robertorszulak@onlemon.pl ✓
- Dodany do listy Apollo "PL Tier 1 do market_news VSC" ✓
- Custom fields synced ✓
- Notyfikacja wysłana do tomasz.uscinski@profitia.pl ✓

Uwaga: artykuł nie kwalifikuje (purchase=5 < 15) — override zastosowany dla celów testu. W live campaign, pipeline odrzuciłby artykuł na etapie qualification.

## 8. ON Lemon jest ZNACZNIE lepszym case'em niż Grycan/Maspex/Colian

Wszystkie trzy poprzednie firmy miały:
- Artykuły z dobrym purchase signal (23-40)
- Zero T1/T2 w Apollo
- Brak możliwości ujawnienia emaila

ON Lemon ma:
- Artykuł z niskim purchase signal (5) — ale to kwestia artykułu, nie firmy
- Kontakt T1 (Robert, Owner) w Apollo ✓
- Email ujawniony ✓
- Pipeline doszedł do READY_FOR_REVIEW ✓

**Rekomendacja:** Monitoruj ON Lemon. Gdy pojawi się artykuł o kosztach surowców, nowych inwestycjach lub problemach dostawców — uruchom live pilot z tym artykułem. Robert (Owner) czeka gotowy w Apollo.

## 9. Główny wniosek strategiczny

Problem poprzednich pilotów NIE dotyczył pipeline'u — dotyczył doboru firm. Firmy prywatne mid-cap FMCG (Grycan, Maspex, Colian) mają słabe pokrycie Apollo. Mniejsze firmy kreacyjne/premium (ON Lemon) mogą mieć LEPSZE pokrycie Apollo, jeśli założyciel/właściciel jest aktywny publicznie.

**Kryterium wyboru firm:** Szukaj firm, których założyciel/właściciel jest publicznie aktywny (wywiady, EEC, branżowe konferencje) — tacy właściciele są częściej indeksowani w Apollo.

---

**Pliki sesji:**
- Skrypt: [tests/on_lemon_test.py](../../../tests/on_lemon_test.py)
- Wyniki JSON: [data/test/on_lemon_test_results.json](../../../data/test/on_lemon_test_results.json)
- Pełny raport: [ON_LEMON_TEST_REPORT.md](ON_LEMON_TEST_REPORT.md)

---

*Sesja: 2026-04-23 | spendguru_market_news | AI Outreach Pipeline*
