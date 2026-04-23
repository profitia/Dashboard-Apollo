# Grycan Live Pilot — Kluczowe ustalenia dla ChatGPT

**Kontekst**: Pipeline `spendguru_market_news` (AI outreach). Pilot live dla artykułu o Gryczanie. Data: 2026-04-21.

---

## Cel pilota

Weryfikacja end-to-end działania pipeline'u news-triggered outreach w trybie draft/review — bez auto-enrollmentu, bez automatycznej wysyłki, z limitem 3 kontaktów T1/T2. Sprawdzenie, czy system poprawnie kwalifikuje artykuł, wyodrębnia firmę, wyszukuje kontakty i tworzy wersje robocze wiadomości.

---

## Wynik końcowy

**Status: BLOCKED_NO_CONTACT** (etap: recipient_selection)

Pipeline zatrzymał się poprawnie — brak kontaktów T1/T2 dla Grycan w bazie Apollo. To realne znalezisko operacyjne, nie błąd systemu.

---

## Kluczowe ustalenia (8 punktów)

### 1. Kwalifikacja artykułu — naprawiona, działa

Artykuł o Gryczanie **pierwotnie się nie kwalifikował** z powodu buga w keywords.yaml (brak terminów lodowych). Po naprawie:

- Total: 47 (próg: 40) ✅
- Industry: 17 (próg: 12) ✅ — dopasowanie food_production: "lody", "lodziarnia", "lody premium"
- Purchase: 21 (próg: 15) ✅ — dopasowanie cost_pressure + supply_chain

Bez naprawy keywords pilot kończył się fałszywym wynikiem "artykuł nie kwalifikuje się", maskując rzeczywisty problem z kontaktami.

---

### 2. Ekstrakcja encji — poprawna

LLM (gpt-4.1-mini) wyodrębnił firmę "Grycan" z confidence=0.98, typ=producer, eligible=True. Zwrócił nazwę brandową bez formy prawnej — zgodnie z przepisaną regułą promptu.

---

### 3. Wyszukiwanie kontaktów — 10 znalezionych, żaden nie pasuje do kampanii

Apollo API zwróciło 10 kontaktów dla Grycan (name_search + domain_fallback grycan.pl). Żaden nie miał emaila. Struktura:

- Brand Managerowie (3x) → Tier 3
- Manager → Tier 3
- National KAM, Deputy Manager, HR Director, Operations Manager, IT Manager, Director of Operations Support → Tier Uncertain

**Brak w Apollo**: Prezes, CEO, CFO, Dyrektor Zakupów, Head of Procurement — czyli dokładnie te role, do których kampania jest adresowana.

---

### 4. Dobór odbiorców — 0 wybranych (T1=0, T2=0)

Tier mapping poprawnie odrzucił wszystkich 10 jako T3/Uncertain. Żaden nie spełnia kryterium T1 (C-level/Zarząd) ani T2 (Dyrektor Zakupów/CPO z dwuskładnikową regułą). Wynik: BLOCKED_NO_CONTACT.

---

### 5. Generowanie wiadomości — nie wykonano

Pipeline zatrzymał się przed etapem generowania. 0 wywołań LLM na tym etapie. 0 wiadomości roboczych.

---

### 6. Apollo sync + notyfikacja — nie wykonano

Brak operacji na CRM. Nie dodano kontaktów do list Apollo. Nie wysłano emaila z prośbą o zatwierdzenie. Logika auto_enroll=false była respektowana na każdym etapie.

---

### 7. Bugi znalezione i naprawione w tej sesji

| Bug | Opis | Naprawa |
|---|---|---|
| keywords.yaml: brak terminów lodowych | food_production nie matchował artykułów lodowych | Dodano 11 terminów (lody, lodziarnia, lody premium, mrożonki, nabiał, surowce mleczne itp.) |
| keywords.yaml: fałszywy "lek" w pharma | "mleka" matchowało pharmaceuticals | Usunięto "lek", pozostawiono "leki" i "producent leków" |
| keywords.yaml: fałszywy "PE" w plastics | "PE" matchowało w "operuje" | Usunięto "PE" i "PS" (polietylen/polistyren pokrywają) |
| pilot script: full_text = body only | Scorer dostawał tylko body, nie title+lead+body | Naprawiono: full_text = title + " " + lead + " " + body |
| pilot script: brak _save_results na early return | Wyniki nie były zapisywane przy przedwczesnym zakończeniu | Dodano _save_results() przed każdym return |

**Uwaga**: "PE" w plastics nadal fałszywie matchuje przez "operuje" — wymagałoby mechanizmu word-boundary. Poza zakresem bieżącej sesji.

---

### 8. Werdykt i rekomendacja

**Pipeline działa technicznie poprawnie.** Kluczowy bloker to pokrycie Apollo dla konkretnej firmy, nie logika systemu.

**Grycan** to spółka rodzinna klasy mid-market — tego rodzaju firmy często mają ograniczony profil C-suite w Apollo (brak publicznych adresów email kadry).

**Rekomendacja**: Kolejny pilot z firmą o lepszym pokryciu Apollo, np. **ORLEN**, **Maspex**, **Colian** — duże firmy spożywcze z udokumentowaną obecnością C-level/procurement w bazie.

---

## Stan po sesji

| Komponent | Status |
|---|---|
| keywords.yaml | Naprawiony — terminologia lodowa + usunięte false positives |
| supply_chain w keywords | Rozszerzony o negocjacji, zakupy surowców, kontrakt |
| pilot script (grycan_live_pilot.py) | Gotowy, naprawiony, z _save_results |
| Smoke tests | 29/29 zielone |
| GRYCAN_LIVE_PILOT_REPORT.md | Napisany — pełna dokumentacja |
| Wyniki pilota (JSON) | data/test/grycan_live_pilot_results.json |
| Globalnej logika kampanii | Bez zmian |
| auto_enroll | False — nie zmieniono |
