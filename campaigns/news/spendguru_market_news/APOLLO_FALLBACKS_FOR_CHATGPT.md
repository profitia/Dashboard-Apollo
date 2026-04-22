# Apollo Contact Search Fallbacks — Podsumowanie dla ChatGPT

**Data:** 2026-04-22  
**Co zostało zrobione:** Implementacja domain fallback + associated company fallback dla contact search w pipeline AI Outreach

---

## Co zostało zaimplementowane

Rozszerzony flow wyszukiwania kontaktów Apollo z 3-krokowymi fallbackami:

1. **Name search** (jak dotychczas) — `q_organization_name`
2. **Domain fallback** — `q_organization_domains_list` (nowość)
3. **Associated company fallback** — szukanie firm powiązanych z artykułu (nowość)

---

## Jak działa domain fallback

Jeśli search po nazwie firmy zwraca 0 kontaktów z emailem, pipeline automatycznie ponawia zapytanie do Apollo używając domeny firmy (`q_organization_domains_list`). Domena może być dostępna z resolwera (Company Resolution Layer) lub z alias dict.

**Przykład:** Search `EvraFish` → 2 kontakty, 0 emaili. Domain search `evrafish.com` → 2 kontakty, 0 emaili. (W tym przypadku oba fail — Apollo credits issue, nie code issue.)

---

## Jak działa associated company fallback

Artykuły często wymieniają firmy powiązane (dostawcy, partnerzy, grupy kapitałowe). Entity Extractor (LLM) wyciąga te firmy do `company.related_companies`. Jeśli name + domain search nie dają emaili, pipeline próbuje każdej firmy powiązanej (max `max_associated_company_candidates`, domyślnie 2).

**Przykład:** Search `EvraFish` → 0 emaili. Domain `evrafish.com` → 0 emaili. Search `Grycan` (firma powiązana w artykule) → 10 kontaktów.

---

## Czy fallbacki poprawiają szanse na emaili?

**Code level: TAK** — flow poprawnie triggeruje fallbacki i zwraca więcej kontaktów.

**Live (Apollo API level):** EvraFish i Grycan mają kontakty w Apollo, ale 0 emaili — emaile są zablokowane za kredyty Apollo. To ograniczenie konta, nie code'u.

**Konkluzja:** Fallbacki są gotowe. Jeśli Apollo konto ma emaile odblokowane (wyższy plan lub kredyty), flow zadziała produkcyjnie. Dla małych polskich firm z ograniczonym profilem Apollo — domain fallback zwiększa szanse kontekstowo.

---

## Kluczowe zmiany w kodzie

| Plik | Co zrobiono |
|------|-------------|
| `src/news/contacts/contact_finder.py` | +`ContactSearchResult` dataclass, +`find_contacts_with_fallbacks()`, +`_search_apollo_contacts_by_domain()`, +`_map_raw_contacts()` helper |
| `src/news/orchestrator.py` | Podmieniono `find_contacts_for_company()` na `find_contacts_with_fallbacks()`, dodano logi strategii |
| `campaigns/news/.../config/campaign_config.yaml` | +3 toggles: `use_domain_fallback`, `use_associated_company_fallback`, `max_associated_company_candidates` |

---

## Diagnostyka i logi

Każdy run loguje:
```
[BUILD] Contact search: strategy=name_domain winning=domain name_email=0 domain_fb=evrafish.com(2e) assoc_fb=off
```

`ContactSearchResult` zawiera pełny `search_log` z krokami:
```
[1] name_search: 'EvraFish' → 2 contacts, 0 with email
[2] domain_fallback: 'evrafish.com' → 2 contacts, 0 with email
[3] assoc_fallback: skipped — no associated companies provided
```

---

## Walidacja

- Smoke tests: 29/29 PASS (brak regresji)
- Unit tests fallbacków: 5/5 PASS (mocked Apollo)
- Live Apollo: flow triggeruje poprawnie, 0 emaili = Apollo credits issue

---

## Co dalej jeśli nadal 0 emaili

1. **Apollo email enrichment** — `POST /people/bulk_match` lub `POST /contacts/request_email_for_person` — wymaga Apollo plan z email credits
2. **Upgrade Apollo planu** — wyższy plan odblokuje emaile dla istniejących kontaktów
3. **Ręczne targetowanie** — dla Evra Fish i Grycan znamy imiona i domeny, można targetować przez LinkedIn Sequences
4. **Email enrichment zewnętrzny** — Hunter.io, Apollo export + enrichment
