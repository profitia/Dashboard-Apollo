# Recipient & Message Rules — Implementation Report
**Kampania**: spendguru_market_news
**Data**: 2026-04-22
**Autor**: GitHub Copilot (VS Code)
**Status**: ✅ Zaimplementowane i przetestowane (29/29 smoke tests passing)

---

## 1. Executive Summary

Zaimplementowano dwie warstwy zmian:

**A. Warstwa selekcji odbiorców** — kto dostaje wiadomości:
- Tylko Tier 1 (C-Level) i Tier 2 (Procurement Management)
- Tier 3 (kupcy operacyjni) całkowicie wykluczony z kampanii
- Zaostrzone reguły klasyfikacji tytułów
- Dwójskładnikowa reguła dla Tier 2
- Email inferred traktowany jako email produkcyjny (z flagą `email_source`)

**B. Warstwa treści wiadomości** — co piszemy i jak:
- Nowa obowiązkowa struktura: anchor → hipoteza → bridge → framework → CTA
- Tier-specyficzne linki Calendly
- Limity słów egzekwowane (warning + log)
- Podpis pochodzi z Apollo custom field (nie z LLM)
- Nowe narracje Tier 1 (marża/EBIT) i Tier 2 (negocjacje/standard)

---

## 2. Reguły selekcji odbiorców

### 2.1 Tier 1 — kto się kwalifikuje (ścisła lista per spec)

| Rola PL | Rola EN |
|---|---|
| prezes zarządu | CEO, Chief Executive Officer |
| dyrektor zarządzający | Managing Director, Managing Partner |
| dyrektor operacyjny | COO, Chief Operating Officer |
| dyrektor finansowy | CFO, Chief Financial Officer |
| właściciel / współwłaściciel | Owner, Founder, Co-founder |
| wiceprezes | President, Chairman |
| członek zarządu | Board Member, Member of the Board |

**Usunięte z Tier 1 vs. poprzednia wersja:**
- CPO → przeniesiony do Tier 2
- CTO, CSO → usunięte (nie są decydentami zakupowymi)
- general manager, country manager → usunięte (niejednoznaczne)
- VP Finance, VP Operations, VP Sales → usunięte (poziom dyrektora, nie zarząd)
- executive director → usunięte (niejednoznaczne)

### 2.2 Tier 2 — kto się kwalifikuje + dwójskładnikowa reguła

**Definicja**: tytuł musi zawierać OBA elementy:
- **Poziom**: `head` | `director` | `chief` | `dyrektor`
- **Komponent zakupowy**: `procurement` | `purchasing` | `zakup` | `sourcing`

**Lista dopuszczonych ról (per spec):**
- CPO, Chief Procurement Officer
- Dyrektor Zakupów, Dyrektor ds. Zakupów
- Head of Procurement, Procurement Director, Director of Procurement
- Head of Procurement and Logistics, Head of Strategic Procurement
- Director of Procurement Division, Head of Procurement Department
- Head of Group Procurement
- Purchasing Director, VP Procurement, VP Purchasing, VP Sourcing

**Przykłady odfiltrowanych (nie kwalifikują się):**
- "Operations Director" — brak komponentu zakupowego
- "Supply Chain Director" → filtrowany (supply chain ≠ procurement)
- "Category Director" → filtrowany (brak słowa procurement/zakup)
- "Procurement Manager" → Tier 3 (manager bez head/director)

### 2.3 Tier 3 — wykluczony całkowicie

Kontakty z tytułami: buyer, senior buyer, purchaser, category specialist, procurement specialist, operational managers — nie trafiają do żadnej wiadomości ani listy Apollo.

### 2.4 Logika cited person

Jeśli artykuł cytuje osobę z T1/T2 → do niej. Jeśli kilka → do wszystkich. Jeśli brak cytowanej → spray do wszystkich znalezionych T1/T2 dla firmy.

---

## 3. Tier Mapping — zmiany w plikach

### `campaign_config.yaml`
- Usunięto `tier_3` z `apollo_lists` — brak listy = brak przypisania
- Dodano `max_contacts_for_draft: 10` (praktycznie bez limitu dla T1+T2)

### `tier_mapping.yaml`
- `tier_1_titles`: uszczuplone o CPO, CTO, CSO, general manager, country manager, VP Finance itd.
- `tier_2_titles`: rozszerzone o pełną listę per spec + CPO (przeniesiony)
- `tier_1_keywords`: usunięte CPO i "managing" (zbyt szerokie)
- `tier_2_keywords`: tylko prokurementowe terminy

### `sequence_builder.py`
- `tier_list_map`: `tier_3_buyers_operational → None` (brak listy)
- `email_source = "apollo_reveal"` po udanym reveal

---

## 4. Inferred Email Logic

**Status**: Infrastruktura przygotowana, pattern-based inference jako przyszły krok.

**Dodane**:
- `email_source: str = "unknown"` w `ContactRecord` (domyślnie)
- Wartości: `"apollo_direct"` (Apollo ma email) | `"apollo_reveal"` (reveal po API) | `"inferred_pattern"` (przyszłe, heurystycznie) | `"unknown"`
- `email_source` zapisywany w `contact_entry` w wynikach sekwencji
- Traktowany jak normalny email produkcyjny (brak blokad na `inferred_pattern`)

---

## 5. Reguły treści wiadomości

### 5.1 Obowiązkowa struktura Email 1

1. **Anchor** (pierwsze zdanie): tytuł artykułu + źródło + nawiązanie do firmy/roli
   - Wzorzec: *"Postanowiłem napisać do Pana po artykule „{title}" opublikowanym w {source}, bo wynika z niego, że…"*
2. **Hipoteza**: konkretny fakt z artykułu → problem dla tej firmy
3. **Bridge**: jak fakt łączy się z marżą/kosztami/rentownością
4. **Framework**: "Nazywam się Tomasz Uściński i jestem z Profitii — polskiej firmy, która od 15 lat pomaga firmom z branży {branża} ograniczać koszty związane z zakupami."
5. **CTA**: link Calendly (per tier) + alternatywa telefoniczna

### 5.2 Limity słów

| Krok | Min | Max |
|------|-----|-----|
| Email 1 | 120 | 170 |
| Follow-up 1 | 60 | 100 |
| Follow-up 2 | 40 | 80 |

Walidacja: `log.warning` gdy poza zakresem — nie blokuje wysyłki.

### 5.3 Calendly per tier

| Tier | Link |
|------|------|
| Tier 1 | `https://calendly.com/profitia/zakupy-a-marza-firmy` |
| Tier 2 | `https://calendly.com/profitia/standard-negocjacji-i-oszczednosci` |

### 5.4 Narracje

**Tier 1**: marża, rentowność, EBIT, presja kosztowa, przewidywalność, kontrola ryzyka
**Tier 2**: przygotowanie do negocjacji, standard pracy kupców, jakość argumentacji, cost drivers, should-cost, savings delivery

### 5.5 Podpis

NIE generowany przez LLM. Pochodzi z Apollo custom field `pl_market_news_signature_tu` — Apollo wstawia go przy wysyłce sekwencji. `body` z LLM kończy się na CTA (Calendly + alternatywa telefoniczna).

---

## 6. Zakazane frazy (enforced przez prompt)

- "w obecnych czasach firmy mierzą się z wieloma wyzwaniami"
- "dzisiejszy rynek jest zmienny"
- "zakupy odgrywają ważną rolę"
- "w dynamicznym środowisku biznesowym"
- "nasza platforma", "nasze narzędzie"
- "Z perspektywy [stanowisko]..." (sugeruje że nadawca = odbiorca)
- em dash "—" → zwykły myślnik " - "

---

## 7. Zmienione pliki

| Plik | Rodzaj zmiany |
|------|---------------|
| `campaigns/news/spendguru_market_news/config/tier_mapping.yaml` | T1 uszczuplony, T2 rozszerzony, CPO przeniesiony |
| `campaigns/news/spendguru_market_news/config/campaign_config.yaml` | tier_3 usunięty z apollo_lists, max_contacts_for_draft: 10 |
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | Pełny rewrite — nowa struktura anchor/hipoteza/bridge/framework/CTA |
| `src/news/contacts/contact_finder.py` | email_source, _is_valid_tier2_title, select_campaign_contacts |
| `src/news/orchestrator.py` | select_campaign_contacts zamiast select_best_contacts |
| `src/news/messaging/message_generator.py` | CALENDLY_URLS, WORD_COUNT_LIMITS, TIER_PERSPECTIVES update, signature usunięta |
| `src/news/apollo/sequence_builder.py` | tier_list_map bez tier_3, email_source=apollo_reveal po reveal |
| `tests/test_news_pipeline_smoke.py` | test_tier3_maps_to_market_news_list zaktualizowany |

---

## 8. Walidacja

- **Smoke tests**: 29/29 passing ✅
- **Dry-run**: nie wykonany w tej sesji (wymaga live API)
- **Testy jednostkowe** `_is_valid_tier2_title`: weryfikacja przez smoke test `test_tier_mapping_loaded_correctly`

---

## 9. Ryzyka i ograniczenia

| Ryzyko | Ocena | Mitygacja |
|--------|-------|-----------|
| Zbyt wąska Tier 1 → mniej odbiorców | NISKIE | Per spec — akceptowalne |
| "Head of Sales" może przejść przez keyword hint (sales zawiera brak procurement) | NISKIE | Dwójskładnikowa reguła filtruje poprawnie |
| Tier 2 bez emaila → brak sekwencji | NISKIE | `require_email_for_sequence: true` |
| Word count LLM nie respektuje limitów | ŚREDNIE | Log warning — nie blokuje; wymaga monitoringu |
| Podpis z custom field — brak fallbacku gdy pole puste | NISKIE | Fallback przez Apollo template default |

---

## 10. Zalecenia

1. **Monitoring word count** — po pierwszym live run sprawdź logi `[WordCount]` — jeśli LLM regularnie przekracza limity, dodaj do promptu explicit licznik zdań
2. **Inferred email pattern** — gdy będzie zapotrzebowanie, dodać `_infer_email_from_pattern(first, last, domain)` w `contact_finder.py` i ustawić `email_source = "inferred_pattern"`
3. **Live dry-run** z nową konfiguracją przed uruchomieniem produkcyjnym
4. **Apollo custom field** `pl_market_news_signature_tu` — upewnij się że jest skonfigurowany w Apollo dla konta Tomasz Uściński
