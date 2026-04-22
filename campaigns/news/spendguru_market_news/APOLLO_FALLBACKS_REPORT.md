# Apollo Contact Search Fallbacks — Raport implementacji

**Data:** 2026-04-22  
**Wersja:** 1.0  
**Autor:** AI Coding Agent (GitHub Copilot)  
**Scope:** `src/news/contacts/contact_finder.py` + `src/news/orchestrator.py`

---

## 1. Executive Summary

Zaimplementowano rozszerzony flow wyszukiwania kontaktów w Apollo z dwoma warstwami fallbacków:

1. **Domain fallback** — jeśli search po nazwie firmy zwraca 0 kontaktów z emailem, pipeline szuka po domenie firmy (`q_organization_domains_list`)
2. **Associated company fallback** — jeśli name + domain search oba zwracają 0 emaili, pipeline próbuje firm powiązanych z artykułem (wyekstrahowanych przez entity_extractor)

**Cel:** Zwiększyć szanse na znalezienie kontaktów z emailem dla małych polskich firm słabo zindeksowanych w Apollo (np. Evra Fish, Grycan).

**Wynik diagnostyki (live Apollo):** Fallbacki triggerują się poprawnie, Apollo zwraca kontakty dla obu firm — brak emaili jest kwestią limitów Apollo (emaile zablokowane za kredyty, nie brak rekordów).

---

## 2. Domain Fallback

### Cel
Apollo może mieć kontakty powiązane z domeną firmy nawet jeśli nazwa wyszukiwania nie pasuje dokładnie do ich bazy.

### Implementacja
```
_search_apollo_contacts_by_domain(domain, campaign_config)
→ POST mixed_people/api_search
→ payload: { q_organization_domains_list: [domain], person_seniorities: [...], per_page: N }
```

**Cleaning domeny:** Automatyczne usunięcie protokołu (`https://`), trailing slash, ścieżki — zwraca czysty hostname.

### Warunek triggerowania
- `use_domain_fallback: true` w campaign_config (domyślnie `True`)
- `company_domain` dostępna (z resolwera lub alias dict)
- name search = 0 kontaktów z walidowanym emailem

### Wyniki live
| Firma | Domain searched | Contacts found | Emails unlocked |
|-------|----------------|----------------|-----------------|
| EvraFish | evrafish.com | 2 | 0 (Apollo limit) |
| Grycan | grycan.pl | 10 | 0 (Apollo limit) |

---

## 3. Associated Company Fallback

### Cel
Artykuły o firmie X często wspominają powiązane firmy Y (partnerzy, dystrybutorzy, grupy kapitałowe). Jeśli Apollo ma lepiej zindeksowaną firmę Y, można znaleźć kontakty przez nią.

### Implementacja
```
associated_companies = company.related_companies  (z entity_extractor LLM)
→ iteruje max N firm (max_associated_company_candidates)
→ dla każdej: _search_apollo_contacts(assoc_name, campaign_config)
→ zatrzymuje się na pierwszej z > 0 emailami
```

### Warunek triggerowania
- `use_associated_company_fallback: true` w campaign_config (domyślnie `True`)
- `associated_companies` niepusta lista (z `company.related_companies`)
- name + domain search = 0 emaili

### Filtrowanie
Automatycznie wyklucza z listy kandydatów nazwę firmy głównej (bez duplikatów).

---

## 4. Nowy Contact Search Flow

```
find_contacts_with_fallbacks(company_name, domain, tier_mapping, config, associated_companies)
    │
    ├─► [1] Name search → _search_apollo_contacts(name)
    │      ✅ email > 0? → RETURN, winning="name"
    │      ❌ 0 emails → next step
    │
    ├─► [2] Domain fallback (if use_domain_fallback AND domain available)
    │      → _search_apollo_contacts_by_domain(domain)
    │      ✅ email > 0? → RETURN, winning="domain"
    │      ❌ 0 emails → next step
    │
    ├─► [3] Associated company fallback (if use_assoc_fallback AND assoc_companies)
    │      → iteruje firmy powiązane (max N)
    │      ✅ email > 0? → RETURN, winning="associated:<company>"
    │      ❌ wszystkie 0 → next step
    │
    └─► RETURN name_contacts (best available, może być puste), winning="none"
        (brak emaili — nie crash, nie skip — kontakty bez emaila zostają w pipelinie)
```

---

## 5. Nowe funkcje — `contact_finder.py`

| Funkcja | Opis |
|---------|------|
| `_map_raw_contacts(raw, name, domain, tier_mapping)` | Wyekstrahowana logika mapowania Apollo → ContactRecord. Wspólna dla name i domain search. |
| `_count_email_contacts(records)` | Liczy kontakty z walidowanym emailem. |
| `_search_apollo_contacts_by_domain(domain, config)` | Domain search via `q_organization_domains_list`. |
| `find_contacts_with_fallbacks(...)` | Główna funkcja z pełnym fallback flow. Zwraca `ContactSearchResult`. |
| `ContactSearchResult` (dataclass) | Wynik z kontaktami + pełną diagnostyką (strategy, winning, counts, search_log). |

**Backward compatibility:** `find_contacts_for_company()` zachowana niezmieniona (teraz używa `_map_raw_contacts()` wewnętrznie — zero breaking change).

---

## 6. Pliki zmienione

| Plik | Zmiana |
|------|--------|
| `src/news/contacts/contact_finder.py` | +`ContactSearchResult`, +`_map_raw_contacts()`, +`_search_apollo_contacts_by_domain()`, +`_count_email_contacts()`, +`find_contacts_with_fallbacks()`, refactor `find_contacts_for_company()` |
| `src/news/orchestrator.py` | Import `find_contacts_with_fallbacks`, zamiana `find_contacts_for_company` na `find_contacts_with_fallbacks`, log strategii |
| `campaigns/news/spendguru_market_news/config/campaign_config.yaml` | +`use_domain_fallback`, +`use_associated_company_fallback`, +`max_associated_company_candidates` |
| `tests/test_contact_fallbacks_diagnostic.py` | Nowy skrypt diagnostyczny (5 unit tests mocked + 2 live Apollo tests) |

---

## 7. Walidacja

### Smoke tests (29/29 PASS)
```
pytest tests/test_news_pipeline_smoke.py -q
29 passed in 0.17s
```

### Unit tests fallbacków (5/5 PASS)
```
✅ name_search_succeeds:     strategy=name_only     winning=name
✅ domain_fallback_triggered: strategy=name_domain   winning=domain
✅ assoc_fallback_triggered:  strategy=name_domain_assoc  winning=associated:Grycan
✅ all_fallbacks_fail:        strategy=name_only     winning=none (graceful)
✅ no_domain_no_assoc:        strategy=name_only     winning=none (graceful)
```

### Live Apollo tests
- EvraFish: domain fallback triggeruje, 2 kontakty znalezione, 0 emaili (Apollo credits issue)
- Grycan: domain + assoc fallback triggerują, 10 kontaktów znalezione, 0 emaili (Apollo credits issue)
- Brak crashy, poprawne logowanie, search_log czytelny

---

## 8. Diagnostyka ContactSearchResult

Każdy wynik `find_contacts_with_fallbacks()` zawiera:

```python
result.strategy_used          # "name_only" | "name_domain" | "name_domain_assoc" | "name_assoc"
result.winning_strategy       # "name" | "domain" | "associated:<name>" | "none"
result.name_search_email_count
result.domain_fallback_triggered
result.domain_searched
result.domain_search_email_count
result.assoc_fallback_triggered
result.assoc_fallback_company
result.assoc_search_email_count
result.search_log             # ["[1] name_search: 'X' → 2 contacts, 0 with email", ...]
```

Logi w orchestrator.py: `[BUILD] Contact search: strategy=... winning=... name_email=... domain_fb=... assoc_fb=...`

---

## 9. Ryzyko i ograniczenia

| Ryzyko | Poziom | Uwaga |
|--------|--------|-------|
| Apollo rate limits | Niski | Fallbacki = max 3 requesty zamiast 1. Przy dużej skali może wymagać throttlingu. |
| Associated company pobiera "złe" kontakty | Średni | Firma powiązana ≠ ta sama firma. Kontakty z `winning=associated:X` powinny być traktowane jako "proxy approach", nie target. |
| `related_companies` z LLM może być puste | Akceptowalny | Fallback po prostu nie triggeruje — brak crashu. |
| Domain cleaning uproszczone | Niski | Usuwamy protokół i ścieżkę. Subdomain (np. `mail.grycan.pl`) → `mail.grycan.pl`. Ręczne poprawki przez alias dict. |
| Emaile nie są dostępne bez Apollo credits | Informacyjny | To ograniczenie konta Apollo, nie kodu. |

---

## 10. Konfiguracja (campaign_config.yaml)

```yaml
# Contact search fallbacks
use_domain_fallback: true
use_associated_company_fallback: true
max_associated_company_candidates: 2
```

Aby wyłączyć selektywnie:
```yaml
use_domain_fallback: false           # tylko name search
use_associated_company_fallback: false   # bez szukania firm powiązanych
max_associated_company_candidates: 1    # tylko 1 firma powiązana
```

---

## 11. Rekomendacja

Flow zaimplementowany poprawnie i gotowy do produkcji. Kluczowe ograniczenie to Apollo email credits — kontakty są w bazie, ale emaile zablokowane za plan płatny. To ograniczenie niezwiązane z fallbackami.

**Następny krok jeśli potrzeba emaili:** Rozważyć Apollo email enrichment (POST /people/bulk_match lub /contacts/request_email_for_person) lub import przez Sequences z ręcznym unlock.
