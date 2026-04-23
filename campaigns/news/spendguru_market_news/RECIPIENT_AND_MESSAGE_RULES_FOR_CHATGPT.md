# Recipient & Message Rules — For ChatGPT
**Kampania**: spendguru_market_news
**Data**: 2026-04-22
**Cel**: szybkie podsumowanie dla AI / kolejnej sesji

---

## 1. Co zostało zaimplementowane (5 kluczowych punktów)

1. **Tylko Tier 1 i Tier 2** — Tier 3 całkowicie wykluczony z kampanii. Nowa funkcja `select_campaign_contacts()` w `contact_finder.py` filtruje do T1+T2 i zastąpiła `select_best_contacts()` w `orchestrator.py`.

2. **Dwójskładnikowa reguła Tier 2** — funkcja `_is_valid_tier2_title(title)` wymaga obecności `head/director/chief/dyrektor` ORAZ `procurement/purchasing/zakup/sourcing`. Filtruje "Operations Director", "Brand Director" itp.

3. **Nowa struktura wiadomości** — `message_writer.md` przepisany: anchor (tytuł artykułu + źródło) → hipoteza z artykułu → bridge do marży → framework Profitia ("od 15 lat") → CTA z Calendly. Email 1: 120-170 słów, FU1: 60-100, FU2: 40-80.

4. **Tier-specyficzne Calendly** — T1: `zakupy-a-marza-firmy`, T2: `standard-negocjacji-i-oszczednosci`. Wstrzykiwane do promptu przez `{{tier_calendly_link}}`.

5. **Podpis z Apollo custom field** — LLM nie generuje podpisu. `body` kończy się na CTA. `_enrich_step()` nie wstawia `SIGNATURE_PLAIN`. Podpis: `pl_market_news_signature_tu` (Apollo merge tag).

---

## 2. Jak działa selekcja odbiorców

```
Apollo search → lista kandydatów
  ↓
_resolve_tier_from_mapping(title)
  → Tier 1: prezes, CEO, CFO, COO, dyrektor zarządzający, board member...
  → Tier 2: head/director/chief + procurement/purchasing/zakup/sourcing (dwójskładnik)
  → Tier 3: buyer, category manager, procurement specialist...
  ↓
select_campaign_contacts(contacts, campaign_config)
  → filtruje do T1+T2 only (Tier 3 i Uncertain wykluczone)
  → sortuje: T1 → T2 → confidence
  → max 10 kontaktów (campaign_config: max_contacts_for_draft: 10)
  ↓
email reveal → sequence_builder → Apollo list T1/T2 (nie T3)
```

---

## 3. Jak działają Tiery T1/T2

**Tier 1 (marża, EBIT, zarząd):**
- prezes, dyrektor zarządzający, dyrektor finansowy, CEO, CFO, COO, właściciel, zarząd
- CPO → **Tier 2** (nie Tier 1 — przeniesiony)
- Calendly: `zakupy-a-marza-firmy`

**Tier 2 (negocjacje, standard, kupcy):**
- CPO, Chief Procurement Officer, Dyrektor Zakupów, Head of Procurement, Procurement Director itd.
- Reguła: MUSI mieć poziom (head/director/chief/dyrektor) + zakupy (procurement/purchasing/zakup/sourcing)
- Calendly: `standard-negocjacji-i-oszczednosci`

**Tier 3 (wykluczony):**
- buyer, senior buyer, purchaser, category specialist, procurement specialist
- Nie trafiają do żadnej listy Apollo ani wiadomości

---

## 4. Jak działa logika inferred email

**Aktualny stan** (2026-04-22): Infrastruktura przygotowana, pattern-based inference = przyszły krok.

`ContactRecord` ma teraz pole `email_source`:
- `"apollo_direct"` — Apollo miał email w search
- `"apollo_reveal"` — email uzyskany przez `people/match` reveal (kosztuje kredyt)
- `"inferred_pattern"` — przyszłe: heurystyczne `tomasz.uscinski@firma.pl`
- `"unknown"` — brak emaila

Traktowanie: żaden `email_source` nie blokuje wysyłki. `email_source` zapisywany w logu sekwencji dla monitoringu.

---

## 5. Jak zmieniła się logika wiadomości

**Poprzednio (stary prompt):**
- Ogólny outreach do firmy/roli
- Brak obowiązkowej struktury
- Podpis wstawiany przez `_enrich_step()` (inline w Python)
- Jedno CTA dla wszystkich tierów
- Brak walidacji długości

**Teraz (nowy prompt):**
- **Obowiązkowy anchor**: pierwsze zdanie = tytuł artykułu + źródło
- **Hipoteza z artykułu**: konkretny fakt (nie ogólnik)
- **Bridge**: tytuł → marża/koszty tej konkretnej firmy
- **Framework**: "Tomasz Uściński, Profitia, 15 lat, branża X"
- **Tier-specyficzne Calendly** w CTA
- **Podpis NIE z LLM** — z Apollo custom field `pl_market_news_signature_tu`
- **Walidacja słów**: warning w logu gdy poza zakresem

---

## 6. Co jest następnym krokiem

1. **Live dry-run** z nową konfiguracją: `python src/news/orchestrator.py run-daily --dry-run --verbose`
2. **Monitoring word count** — sprawdź logi `[WordCount]` po pierwszym dry-run
3. **Inferred email pattern** — dodać `_infer_email_from_pattern()` gdy pojawi się zapotrzebowanie
4. **Apollo custom field** — upewnij się że `pl_market_news_signature_tu` jest poprawnie skonfigurowany w Apollo

---

## 7. Pliki zmienione w tej sesji

| Plik | Co zmieniono |
|------|-------------|
| `tier_mapping.yaml` | T1 uszczuplony (bez CPO/CTO/GM), T2 rozszerzony (CPO + spec roles), dwójskładnikowy komentarz |
| `campaign_config.yaml` | Usunięto tier_3 z apollo_lists, dodano max_contacts_for_draft: 10 |
| `message_writer.md` | Pełny rewrite: anchor/hipoteza/bridge/framework/CTA, limity słów, zakazane frazy |
| `contact_finder.py` | email_source w ContactRecord, _is_valid_tier2_title(), select_campaign_contacts() |
| `orchestrator.py` | select_campaign_contacts zamiast select_best_contacts |
| `message_generator.py` | CALENDLY_URLS, WORD_COUNT_LIMITS, nowe TIER_PERSPECTIVES, podpis usunięty z _enrich_step |
| `sequence_builder.py` | tier_list_map bez tier_3, email_source=apollo_reveal po reveal |
| `test_news_pipeline_smoke.py` | test_tier3 zaktualizowany (None = poprawne) |

**Smoke tests: 29/29 ✅**
