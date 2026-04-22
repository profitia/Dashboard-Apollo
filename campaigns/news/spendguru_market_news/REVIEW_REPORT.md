# REVIEW REPORT — spendguru_market_news

**Data review:** 2026-04-22  
**Reviewer:** GitHub Copilot (automated technical review)  
**Status:** Read-only review — brak automatycznych refaktorów

---

## 1. Executive Summary

Implementacja `campaigns/news/spendguru_market_news` to solidnie zaprojektowany **Early MVP** — architektura jest spójna, podział odpowiedzialności poprawny, a konfiguracja jest zewnętrzna i edytowalna bez dotykania kodu. Pipeline logicznie odwzorowuje specyfikację: scan → qualify → extract → contacts → messages → Apollo.

Główne zastrzeżenia dotyczą **czterech obszarów krytycznych**:

1. **Generator wiadomości**: vocative placeholder `{{vocative_first_name}}` jest wypełniany surowym `first_name` zamiast formą wołacza. Nie ma pola `_gender` w `ContactRecord`, więc forma Pan/Pani jest zawsze neutralna. To jest widoczny problem jakościowy w mailach.
2. **`create_weekly_sequence()` — sygnatura niesprawdzona**: `sequence_builder.py` zakłada, że funkcja z `core.weekly_sequence_orchestrator` przyjmuje argumenty `(sequence_name, cadence, step_templates, activate=False)`. Jeśli tak nie jest, cały live run padnie na tym kroku. NOT VERIFIED - requires live Apollo/API test.
3. **State manager — logika re-processingu**: `is_article_processed()` zwraca `True` TYLKO dla statusu `sequence_created`. Artykuły z `scoring_failed`, `no_company`, `no_contacts` będą ponownie fetchowane i scorowane przy każdym uruchomieniu dziennym.
4. **`article_key_facts`**: do LLM przekazywana jest lista dopasowanych słów kluczowych ze scorera, nie wyekstrahowane fakty biznesowe z artykułu. Prompt sugeruje że chodzi o realne fakty ("kluczowe fakty z artykułu do użycia w wiadomości"), tymczasem dostaje keyword debug string.

Implementacja nadaje się do dalszego review przez zewnętrzne narzędzie (np. ChatGPT), ale **nie powinna trafić na live run bez adresowania punktów 1, 2, i 4**.

---

## 2. Inventory Reviewed

| Plik | Typ | Przeczytany |
|---|---|---|
| `src/news/orchestrator.py` | CLI + główny pipeline | ✅ |
| `src/news/ingestion/scanner.py` | Skanowanie URL-i artykułów | ✅ |
| `src/news/ingestion/article_fetcher.py` | Fetch + parse artykułu | ✅ |
| `src/news/relevance/scorer.py` | Scoring relewantności | ✅ |
| `src/news/entity/entity_extractor.py` | Ekstrakcja firmy | ✅ |
| `src/news/contacts/contact_finder.py` | Szukanie kontaktów Apollo | ✅ |
| `src/news/messaging/message_generator.py` | Generowanie OutreachPack | ✅ |
| `src/news/apollo/sequence_builder.py` | Tworzenie sekwencji Apollo | ✅ |
| `src/news/state/state_manager.py` | Stan + dedup | ✅ |
| `src/news/notifications/notifier.py` | Powiadomienia | ✅ |
| `campaigns/news/spendguru_market_news/config/campaign_config.yaml` | Konfiguracja | ✅ |
| `campaigns/news/spendguru_market_news/config/sources.yaml` | Serwisy | ✅ |
| `campaigns/news/spendguru_market_news/config/keywords.yaml` | Słowa kluczowe | ✅ |
| `campaigns/news/spendguru_market_news/config/tier_mapping.yaml` | Mapowanie tierów | ✅ (pełny) |
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | Prompt LLM | ✅ |
| `campaigns/news/spendguru_market_news/README.md` | Dokumentacja | ✅ |
| `campaigns/news/spendguru_market_news/.env.example` | Env przykład | ✅ |
| `tests/test_news_pipeline_smoke.py` | Testy | ✅ + 4 bugfixy |
| `.vscode/tasks.json` | Taski VS Code | ✅ |
| `requirements.txt` | Zależności | ✅ |

---

## 3. What Appears Implemented Correctly

| Obszar | Co działa dobrze | Dlaczego to jest dobre |
|---|---|---|
| **Architektura** | Każdy moduł ma jedną odpowiedzialność, importy są lazy | Brak cyklicznych zależności; można testować moduły niezależnie |
| **Konfiguracja** | `campaign_config.yaml`, `sources.yaml`, `keywords.yaml`, `tier_mapping.yaml` są poza kodem | Dodanie nowego serwisu lub zmiana progów nie wymaga edycji Pythona |
| **Dry-run** | `--dry-run` zatrzymuje się przed write do Apollo i zwraca realistyczny wynik | Bezpieczne testowanie end-to-end bez API sideeffects |
| **Tier perspectives** | `TIER_PERSPECTIVES` w `message_generator.py` są dobrze zróżnicowane i on-brand | Tier 1 = marża/EBIT; Tier 2 = standard przygotowania; Tier 3 = konkretna negocjacja |
| **Prompt template** | `message_writer.md` zawiera explicit "ZAKAZANE" listę, zasady Pan/Pani, anty-em-dash, anty-"nasza platforma" | Zgodne z Gold Standard z `campaign-writing-rules.md` w user memory |
| **State manager** | Deduplication firmy w 30-dniowym oknie przez `company_normalized` | Zapobiega spamowaniu tej samej firmy po każdym artykule |
| **Sequence naming** | Format `NEWS-YYYY-MM-DD-{company}-{topic}` z slugify | Czytelna nazwa, bezpieczna dla API Apollo |
| **Apollo merge tags** | `{{sg_email_step_1_body}}{{pl_signature_tu}}` w step 1, bez podpisu w followupach | Spójne ze standardem projektu |
| **Cadence** | `[0, 2880, 2880]` (D0/D+2/D+2) skonfigurowane w YAML | Zmiana kadencji bez edycji kodu |
| **`activate_automatically: false`** | Sekwencja zawsze nieaktywna po creation | Zabezpieczenie przed przypadkowym wysyłaniem |
| **Fallback heurystyczny** | Entity extractor i message generator mają fallback gdy LLM niedostępny | Pipeline nie pada bez LLM |
| **4900-char truncation** | Custom fields przycinane do 4900 znaków | Respektuje limit Apollo 5000 |
| **`tier_mapping.yaml`** | Kompletna: Tier 1/2/3 + EN/PL + keyword hints | Obsługuje realne tytuły z Apollo bazy |

---

## 4. Gaps and Incomplete Areas

| Obszar | Brak / Problem | Wpływ | Priorytet |
|---|---|---|---|
| **Message Generator** | `vocative_first_name` = `contact.first_name`, nie forma wołacza. "Tomasz" zamiast "Tomaszu" | Każdy mail wygląda nienaturalnie po "Dzień dobry, Tomasz" | **High** |
| **Message Generator** | `_gender` nie jest polem w `ContactRecord` — zawsze `""` → forma zawsze neutralna | Pan/Pani nie jest dopasowane do płci | **High** |
- **Sequence Builder** | `create_weekly_sequence()` wywołana z `step_templates` i `activate` — te argumenty NIE ISTNIEJĄ w sygnaturze. POTWIERDZONE. Live run → `TypeError` | **High** |
| **Message Generator** | `article_key_facts` = `score_result.explanation` = lista słów kluczowych, nie fakty | LLM dostaje "Industry/food_production: produkcja żywności" zamiast faktów z artykułu | **High** |
| **State Manager** | `is_article_processed()` zwraca `True` tylko dla `sequence_created` — reszta statusów nie blokuje re-processingu | Ten sam artykuł fetchowany i scorowany przy każdym uruchomieniu | **High** |
| **Contact Finder** | `client.search_contacts()` — istnienie metody na ApolloClient nie zweryfikowane | NOT VERIFIED - requires live Apollo/API test | **High** |
| **Scanner** | Selektor `a[href*='/artykuly/']` pasuje do nav links, sidebaru, paginacji, nie tylko artykułów | Dużo false positive URL-i, które przechodzą do fetchera i marnują requesty | **Medium** |
| **Article Fetcher** | `companies_mentioned_raw` regex wymaga formy prawnej (Sp. z o.o., S.A.) — nie wyłapuje "Biedronka", "Lidl", "Danone" | Entity extractor dostaje pustą listę firm, LLM musi zgadywać z tekstu | **Medium** |
| **Scorer** | Tytuł artykułu liczony 3x: raz w `full_text`, raz ponownie w `search_text = full_text + tags_text + title`, raz w `title_hits` bonus | Zawyżone scory dla artykułów z dobrymi tytułami | **Medium** |
| **State Manager** | Brak atomic write (no temp file + rename) — crash podczas zapisu = korupcja JSON | Utrata stanu po nieoczekiwanym przerwaniu | **Medium** |
| **Smoke Tests** | `pytest tests/` odkrywa wszystkie testy w folderze; inne testy (live Apollo) blokują wykonanie | `python -m pytest tests/test_news_pipeline_smoke.py` wymaga `--ignore` flag lub dedykowanego `pytest.ini` | **Medium** |
| **Notifier** | `_notify_email` wywołuje `send_mail.py` przez `subprocess.run([..., "send", to_email, subject, message])` — format argumentów niesprawdzony | Powiadomienia email mogą nie działać | **Low** |
| **Article Fetcher** | `article_hash` oparty o canonical URL, nie treść — jeśli artykuł zmieni treść, hash pozostaje ten sam | Zaktualizowane artykuły nie są re-qualifikowane | **Low** |
| **Orchestrator** | `company_domain` przekazywane jako `None` do `find_contacts_for_company` | Apollo search mniej precyzyjny bez domeny | **Low** |
| **Scorer** | Brak koncepcji "false positive exclusion" — artykuł o pogodzie z jednym słowem "producent" może zebrać punkty | Niska precision kwalifikacji | **Low** |

---

## 5. Detailed Findings by Module

### `orchestrator.py`
**Rola:** CLI (argparse) + koordynacja 4 trybów (scan/qualify/build-sequence/run-daily).

**OK:**
- Tryby logicznie podzielone i niezależnie wywoływalne
- `dry_run` i `review_only` działają na właściwym poziomie (przed Apollo API calls)
- Obsługa `single_article_url` do testowania jednego artykułu

**Wątpliwości:**
- `run_qualify` tworzy default `source_config` dla nieznanego `source_id` z pustymi selektorami — artykuł nie zostanie poprawnie zparsowany
- Liczniki `tier_1/2/3` w orchestratorze mapują `tier_1_c_level → "tier_1"` — działa, ale jest to dodatkowe mapowanie którego można zapomnieć zaktualizować

**Ocena:** Real logic, nie scaffold.

---

### `scanner.py`
**Rola:** Odkrywanie URL-i artykułów z list stron serwisów.

**OK:**
- Deduplication URL-i w obrębie scan
- Respektuje `max_articles_per_scan`
- Obsługuje zarówno string jak i dict w `scan_urls`

**Wątpliwości:**
- Filtr "nie-artykułowych" URL-i (`/kontakt`, `/regulamin`, etc.) jest hardcoded i nie konfigurowalny — nowe serwisy mogą mieć inne patterny
- Selektor `a[href*='/artykuly/']` jest bardzo szeroki — paginacja, breadcrumbs, sidebar też pasują
- Brak retry na failed page fetch — jeden timeout = pominięta strona bez logu

**Ocena:** Scaffold dla multi-source, real logic dla single source (wiadomoscihandlowe.pl).

---

### `article_fetcher.py`
**Rola:** Fetching + HTML parsing + company extraction.

**OK:**
- Paywall detection przez CSS selektory i frazy tekstowe
- Fallback date extraction (meta OG → `time[datetime]` → CSS selector)
- `is_usable` property jako jednoznaczna bramka

**Wątpliwości:**
- Regex w `_extract_companies_raw` wymaga formy prawnej — nic nie wyłapie dla "Biedronka", "Nestlé", "Danone", "Unilever"
- `body_el.get_text(separator=" ", strip=True)` daje płaski tekst bez kontekstu akapitów — szczególnie problematyczne dla artykułów z tabelami
- CSS selektory dla wiadomoscihandlowe.pl (`h1.article-title`, `.article-body`) nie zostały zwalidowane na żywych stronach (NOT VERIFIED)

**Ocena:** Real logic, ale niesprawdzona na live data.

---

### `scorer.py`
**Rola:** Scoring relewantności 0-100 przez keyword matching.

**OK:**
- Wielowymiarowy scoring (industry + purchase signal + freshness + amplifiers + procurement vocab)
- Konfigurowalne progi i wagi w YAML
- Disqualification_reason wyjaśnia dlaczego odrzucony

**Wątpliwości:**
- **Triple-counting tytułu**: `full_text = title + lead + body`, `search_text = full_text + tags_text + title`. Tytuł jest w `full_text` (via `score_article` przekazuje `full_text` bezpośrednio), a potem doklejany ponownie do `search_text`, plus osobny `title_hits` bonus. Artykuły z silnymi tytułami mogą mieć zawyżony score nawet przy słabej treści.
- `_get_article_age_days` ma błędną logikę parsowania: próbuje każdy format ze slicingiem `fmt[:len(published_at[:19])]` — może dawać błędne wyniki dla dat bez czasu
- Brak semantycznego rozumienia — "producent opon" i "producent żywności" mają takie same szanse na kwalifikację

**Ocena:** Real logic, z zachowawczym ryzykiem false positives.

---

### `entity_extractor.py`
**Rola:** Identyfikacja głównej firmy z artykułu (LLM + heuristics).

**OK:**
- LLM prompt precyzyjnie priorytetyzuje typy firm (producent żywności >> retailer >> dystrybutor)
- `campaign_eligible` eliminuje `tech_vendor` i `other` bez zatwardzania logiki w kodzie
- Heurystyczny fallback wybiera firmę najczęściej wspomnianą w tekście

**Wątpliwości:**
- Heurystyczny fallback robi count przez `full_text.lower().count(term)` gdzie `term = company.lower()[:15]` — jeśli kilka firm zaczyna się tak samo (np. "Maspex" i "Maspex Wadowice"), deduplikacja jest błędna
- LLM może halucynować firmę która nie istnieje w artykule — brak walidacji że zwrócona firma pojawia się w tekście
- `campaign_eligible` dla typu `"other"` zwraca `False` w heurystyce, ale LLM może zwrócić `"other"` z `campaign_eligible: true` — asymetria

**Ocena:** Real logic dla LLM path; heuristic to scaffold.

---

### `contact_finder.py`
**Rola:** Wyszukiwanie kontaktów w Apollo, mapowanie do tierów.

**OK:**
- `_resolve_tier_from_mapping` prawidłowo czyta strukturę YAML (`tier_1_titles.titles`)
- Keyword hints działają poprawnie (struktura dict zgodna z `tier_mapping.yaml`)
- Sortowanie wyników: tier 1 → 2 → 3 → uncertain

**Wątpliwości:**
- **NOT VERIFIED**: czy `client.search_contacts({"email": ...})` istnieje w `ApolloClient` — może brakować tej metody
- **NOT VERIFIED**: czy `client.create_contact()` istnieje i ma oczekiwany format
- `organization_name` jako jedyne kryterium search Apollo może dawać słabe wyniki jeśli nazwa firmy w Apollo różni się od nazwy z artykułu (np. "Biedronka" vs "Jeronimo Martins Polska")
- Partial matching w tier resolution: `t.lower() in title_lower or title_lower in t.lower()` — drugi warunek (`title_lower in t.lower()`) spowoduje że tytuł "Manager" pasuje do "Strategic Procurement Manager" (Tier 2), nawet jeśli stanowisko to np. "Product Manager"

**Ocena:** Scaffold dla Apollo integration; real logic dla tier mapping.

---

### `message_generator.py`
**Rola:** Generowanie 3-mailowej sekwencji (Email 1 / FU1 / FU2) per kontakt.

**OK:**
- `TIER_PERSPECTIVES` są szczegółowe i adekwatne — różnicują język, pain points, proof points, CTA per tier
- Prompt template zawiera explicit zasady (em dash, Pan/Pani, CTA przed podpisem)
- `review_notes` w JSON output umożliwia QA
- Heurystyczny fallback poprawnie różnicuje `perspective_short` per tier

**Wątpliwości:**
- **Krytyczne**: `{{vocative_first_name}}` = `contact.first_name` = "Tomasz" — nie "Tomaszu". Dla PL outreach to jest duży błąd gramatyczny.
- **Krytyczne**: `getattr(contact, "_gender", "")` — `_gender` nie istnieje w `ContactRecord` dataclass. Zawsze zwraca `""` → gender = "neutralnie: Pani/Pana" → prompt dostaje nierozstrzygniętą płeć.
- `article_key_facts` = wynik `score_result.explanation` który wygląda np. tak: `"[Industry/food_production]: produkcja żywności, producent; [Signal/cost_pressure]: koszty, marża"`. To debug log, nie fakty biznesowe.
- `body_core` w `_enrich_step` = `step.get("body_core") or step.get("body", "")` — ale `step` z LLM ma tylko `"body"`, nie `"body_core"`. Więc `body_core` = `body` = pełny tekst Z podpisem. Funkcja `_nosig_html` w `sequence_builder.py` potem szuka "Z poważaniem," by je usunąć — to działa, ale jest kruche.
- `max_tokens=3000` może być za mało dla 3 maili po PL. Każdy mail ~400 tokenów + JSON structure = możliwe obcięcie.

**Ocena:** Real logic dla LLM path. Wymaga poprawek w danych wejściowych (vocative, gender, key_facts).

---

### `sequence_builder.py`
**Rola:** Tworzenie sekwencji Apollo, sync custom fields, enrollment.

**OK:**
- Merge tag templates zgodne ze standardem projektu (`{{sg_email_step_1_body}}{{pl_signature_tu}}`)
- Round-robin enrollment przez aktywne mailboxy
- `dry_run` zatrzymuje przed wszystkimi API calls

**Wątpliwości:**
- **KRYTYCZNE — POTWIERDZONE**: `create_weekly_sequence()` wywołana z `step_templates=MERGE_TAG_TEMPLATES, activate=False` — oba argumenty nie istnieją w sygnaturze (`src/core/weekly_sequence_orchestrator.py` linia 198). Live run padnie z `TypeError`. Prawa sygnatura: `(sequence_name, cadence=None)`.
- `_outreach_pack_to_custom_fields` importuje `SIGNATURE_HTML` jako `SIG_HTML` ale nigdy go nie używa — dead import
- `_nosig_html` jest nested function wewnątrz `_outreach_pack_to_custom_fields` — działa, ale utrudnia testowanie
- `sequence_active_in_other_campaigns: True` w enrollment payload — kontakty już w innych sekwencjach zostaną zaenrollowane. Może powodować conflict jeśli kontakt jest w aktywnej kamapnii VSC.
- Brak obsługi sytuacji gdzie contact_id zostaje znaleziony przez search ale ma `bounce_status: invalid` w Apollo

**Ocena:** Scaffold dla Apollo integration details; real logic dla flow.

---

### `state_manager.py`
**Rola:** Deduplication + persistentny stan.

**OK:**
- Cooldown firmy przez `company_normalized` (lowercase, bez form prawnych) — poprawna logika
- Structured state z explicit statusami (8 statusów)
- `get_recent_sequences()` umożliwia monitoring

**Wątpliwości:**
- **Krytyczne**: `is_article_processed()` zwraca `True` tylko gdy `status == "sequence_created"`. Artykuły z `scoring_failed`, `no_company`, `no_contacts`, `company_in_cooldown` będą refetchowane co dzień. Powinno blokować NA WSZYSTKICH statusach za wyjątkiem ewentualnie `"pending_review"`.
- Brak atomic write (write → crash → korupcja JSON). Wzorzec: `write to temp file → os.replace(temp, target)`.
- Brak backup/rotation pliku stanu — po korupcji brak fallbacku
- `_sequences` klucz = `sequence_name` (string) — jeśli ta sama sekwencja jest tworzona 2x (retry), drugi zapis nadpisuje pierwszy

**Ocena:** Real logic, ale z lukami bezpieczeństwa.

---

### `notifier.py`
**Rola:** Powiadomienia po utworzeniu sekwencji.

**OK:**
- Wielokanałowa architektura (log/json/email/webhook) — dobrze rozszerzalna
- JSON report ma timestamp i pełne dane

**Wątpliwości:**
- `_notify_email` wysyła `message` (plain text) przez subprocess z args `["send", to_email, subject, message]` — format CLI send_mail.py nie był sprawdzony
- Webhook nie ma retries ani timeout configurable
- Powiadomienie jest wysyłane ZAWSZE po `sequence_created`, nie ma możliwości konfiguracji "notify only on error"

**Ocena:** Real logic dla log/json; scaffold dla email/webhook.

---

## 6. Business Logic Alignment Check

### Negotiation Intelligence — zgodność

**Prompt template (message_writer.md)** jest dobrze napisany pod kątem NI:
- Explicit zakaz zaczynania od firmy/produktu
- Zakaz "nasza platforma", "nasze narzędzie", "demo request"
- Wymóg osadzenia w realiach firmy i roli odbiorcy
- "Z perspektywy..." zakazane — zgodne z `campaign-writing-rules.md`

**TIER_PERSPECTIVES** w `message_generator.py` prawidłowo różnicuje:
- Tier 1: marża, EBIT, odporność kosztowa — **correct**, to jest język zarządu
- Tier 2: standard przygotowania, delivery savings, uzasadnienie zarządowi — **correct**
- Tier 3: konkretna negocjacja, benchmark dostawcy, gotowy plan rozmowy — **correct**

### Ryzyko "product pitch"

**Heurystyczny fallback** (`_generate_fallback`) ma potencjalny problem:

```
# email_1, body:
"W Profitii pomagamy firmom z branży produkcyjnej i FMCG przygotowywać się 
do negocjacji zakupowych w sposób systematyczny..."
```

To jest blisko product pitch, choć nie zaczyna od produktu. Spójne z zasadami, ale na granicy. Fallback nie jest dostosowany per tier — wszystkie tiary dostają prawie identyczny tekst z różnym `perspective_short`.

### Gdzie generator może "odpłynąć"

- Bez poprawnego `article_key_facts` (teraz lista keywords zamiast faktów), LLM nie ma konkretnego triggera i może generować generyczne treści
- `article_body_excerpt` przekazuje pierwsze 1500 znaków body — jeśli paywall uciął, body może być słabe lub puste; LLM musi improvizować
- Brak instrukcji dla LLM co do długości subject line (prompt mówi "max 55 znaków", ale nie egzekwuje — post-processing QA nie istnieje)

---

## 7. Risk Register

| Ryzyko | Prawdopodobieństwo | Wpływ | Rekomendacja |
|---|---|---|---|
| `create_weekly_sequence()` ma inną sygnaturę niż zakładana | **POTWIERDZONE** | Krytyczny — live run nie tworzy sekwencji, TypeError | Napraw wywołanie w `sequence_builder.py`: usuń `step_templates` i `activate`, użyj `(sequence_name=..., cadence=...)` |
| Vocative = first_name → błąd gramatyczny w mailach | Pewne | Wysoki — każdy mail wygląda nienaturalnie | Dodaj vocative lookup lub LLM derivation |
| `article_key_facts` = keyword list → generic messages | Wysoki | Wysoki — maile mają słaby trigger, nie spersonalizowane | Implementuj ekstrakcję key facts przez LLM z artykułu |
| `is_article_processed` nie blokuje re-processingu failed articles | Pewny | Średni — marnowanie API calls, duplikaty fetch | Zmień logikę na: blokuj KAŻDY przetworzony status |
| Apollo people search po samej nazwie firmy daje błędne wyniki | Wysoki | Średni — złe kontakty, zły tier | Dodaj domain enrichment lub human review gate |
| Konta mailowe Apollo (`/api/v1/email_accounts`) mogą nie zwrócić kont | Średnie | Średni — enrollment bez mailboxa | Fallback na skonfigurowany `APOLLO_MAILBOX_ID` z .env |
| Paywall wiadomoscihandlowe.pl uniemożliwia scoring | Wysoki | Średni — artykuły z paywallem nie kwalifikują (body < 100 chars) | Zweryfikuj `is_usable` dla artykułów z paywallem; obniż próg |
| State file korupcja po crash | Niskie | Wysoki — utrata stanu deduplikacji | Implementuj atomic write |
| Heurystyczny fallback w LLM message gen → identyczne maile per tier | Wysoki (gdy LLM niedostępny) | Niski — fallback jest "wystarczający" | Akceptowalne dla MVP |

---

## 8. Missing Tests

Lista konkretnych testów których brakuje:

1. **Test end-to-end dry-run**: pełny pipeline scan→qualify→build dla jednego mockowanego artykułu HTML
2. **Test `is_article_processed` dla każdego statusu**: sprawdź że `scoring_failed`, `no_company`, `no_contacts` NIE blokują (lub powinny blokować — ustal intencję)
3. **Test gender form selection**: utwórz `ContactRecord` z poprawnym gender field i sprawdź czy prompt ma "Pan"/"Pani"
4. **Test truncation 4900 chars**: utwórz OutreachPack z treścią >5000 znaków i sprawdź czy pole w custom_fields ma ≤4900
5. **Test `_nosig_html` signature stripping**: sprawdź że "Z poważaniem," jest usuwane z body przed wysłaniem do Apollo
6. **Test `is_company_in_cooldown` boundary**: firma o tym samym `company_normalized` 31 dni temu powinna NIE być w cooldown (30-day window)
7. **Test entity extractor heuristic fallback**: bez LLM, artykuł z wieloma firmami → czy wybierany jest najczęściej wymieniony
8. **Test sequence name max length**: bardzo długa nazwa firmy i tytuł artykułu nie przekraczają 120 znaków
9. **Test scorer dla artykułu tylko z tytułem** (paywall body = ""): czy `is_usable = False` jest egzekwowane
10. **Test scorer date parsing**: różne formaty daty (ISO8601, "2026-04-21", "2026-04-21T12:00:00+02:00")
11. **Integration test `create_weekly_sequence` signature**: NOT VERIFIED — requires live Apollo/API test
12. **Test pytest isolation** (`pytest.ini` lub `pyproject.toml` wskazujący testdir na news-specific tests)

---

## 9. Minimum Changes Required Before First Live Run

1. **MUST**: Napraw wywołanie `create_weekly_sequence()` w `sequence_builder.py`. Rzeczywista sygnatura: `(sequence_name, cadence=None)`. Trzeba usunąć `step_templates` i `activate` z wywołania. Funkcja ma własne hardcoded `MERGE_TAG_TEMPLATES` — jeśli news potrzebuje innych templates, trzeba je dodać osobno do `weekly_sequence_orchestrator.py` lub przekazać cadence jawnie.
2. **MUST**: Napraw `article_key_facts` — wyekstrahuj realne fakty z artykułu zamiast przekazywać keyword debug string z scorera
3. **MUST**: Napraw `vocative_first_name` — albo pobierz z Apollo custom field, albo dodaj LLM derivation (PL vocative from first name), albo zastąp imię formą `Pan/Pani {last_name}`
4. **MUST**: Dodaj pole `gender` do `ContactRecord` i wypełniaj je z Apollo (field `gender` istnieje w Apollo contact data)
5. **MUST**: Zmień `is_article_processed()` — blokuj re-processing dla WSZYSTKICH statusów, nie tylko `sequence_created`
6. **MUST**: Zweryfikuj metody Apollo Clienta: czy `search_contacts`, `create_contact`, `people_search`, `get_label_id` istnieją w `Integracje/apollo_client.py`
7. **MUST**: Uruchom `--dry-run` z jednym prawdziwym URL artykułu i zweryfikuj cały log — sprawdź każdy moduł
8. **SHOULD**: Dodaj `pytest.ini` lub `pyproject.toml` wskazujący `testpaths = tests` i markujący live tests z `@pytest.mark.live` aby smoke testy mogły być uruchamiane bez `--ignore`

---

## 10. Nice-to-Have Improvements

1. **`article_key_facts` extractor**: osobny LLM call po fetch artykułu — "wylistuj 3-5 biznesowych faktów z tego artykułu istotnych dla negocjacji zakupowych"
2. **Company domain enrichment**: po znalezieniu firmy przez entity extractor, szukaj domeny przez Apollo lub Clearbit zanim przejdziesz do people search
3. **Atomic writes** w state_manager: `write to .tmp → os.replace(.tmp, target)`
4. **QA post-processing**: po wygenerowaniu OutreachPack, przejdź przez `campaign-writing-rules.md` checklist programatycznie (em dash detection, subject length, CTA presence)
5. **Konfigurowalne URL exclusion patterns** w scannerze (zamiast hardcoded `/kontakt`, `/regulamin`)
6. **Source HTML selector validation**: przy starcie pipeli, zwaliduj że selektory z `sources.yaml` pasują do przynajmniej jednego elementu na stronie
7. **Retry dla failed article fetches**: po 1 nieudanym fetchu, retry po `request_delay_ms * 2`
8. **Vocative names lookup**: zintegruj z istniejącym `Vocative names od VSC.csv` z folderu `context/` jeśli baza jest dostępna
9. **`human_review_gate: true` jako domyślny** dla pierwszych 3 live runów — po weryfikacji jakości maili przełącz na `false`
10. **Opoint integration**: zdefinowany w README jako "rozważana" — jako kolejny source YAML po zdobyciu API access

---

## 11. Final Verdict

### **Early MVP**

Uzasadnienie:

- **Architektura jest gotowa**: wszystkie moduły istnieją, podział odpowiedzialności jest poprawny, konfiguracja zewnętrzna, dry-run działa.
- **Logika biznesowa jest na miejscu**: tier perspectives poprawne, prompt template zgodny z Gold Standard, naming convention czytelna.
- **Są krytyczne luki w jakości danych wejściowych do LLM**: vocative zamiast imienia, brak gender, keyword list zamiast key facts. To bezpośrednio wpływa na jakość maili.
- **Apollo integration ma niesprawdzone założenia**: sygnatura `create_weekly_sequence()`, dostępne metody ApolloClient, format enrollment. Jeden błąd w którejkolwiek z tych punktów i live run pada bez sensownego błędu.
- **State manager** ma lukę która sprawi że pipeline działa kilkukrotnie na tych samych złych artykułach.

Do przejścia do "Usable with manual review" potrzebne są punkty 1-7 z sekcji 9 (Minimum Changes).

---

## 12. Appendix — Evidence Snippets

### A. `article_key_facts` = keyword debug string

```python
# orchestrator.py, run_build_sequence():
article_key_facts = score_result.explanation
# score_result.explanation z scorer.py wygląda tak:
# "[Industry/food_production]: produkcja żywności, producent; [Signal/cost_pressure]: koszty"
# Przekazywane do: generate_outreach_pack(..., article_key_facts=article_key_facts)
# Następnie wstawiane do prompta jako: {{article_key_facts}}
```

### B. `_gender` missing from ContactRecord

```python
# message_generator.py, _fill_prompt():
gender_form = gender_form_map.get(getattr(contact, "_gender", ""), "neutralnie: Pani/Pana")
# ContactRecord dataclass (contact_finder.py) nie ma pola "_gender"
# getattr() zawsze zwraca "" → gender_form = "neutralnie: Pani/Pana"
# Każdy mail ma niezdecydowaną formę płciową
```

### C. `is_article_processed` — tylko sequence_created blokuje

```python
# state_manager.py:
def is_article_processed(self, url: str, article_hash: str | None = None) -> bool:
    canonical_url = url.split("?")[0].rstrip("/")
    if canonical_url in self._articles:
        status = self._articles[canonical_url].get("status", "")
        if status == self.STATUS_SEQUENCE_CREATED:  # ← tylko ten status blokuje
            return True
    # scoring_failed, no_company, no_contacts → zwraca False → re-processed
```

### D. Triple-counting tytułu w scorer

```python
# scorer.py, score_article():
tags_text = " ".join(tags)
search_text = full_text + " " + tags_text + " " + title  # full_text już zawiera title!
# → hits = _count_hits(search_text, terms)  ← title counted twice in search_text
# → title_hits = _count_hits(title, terms)   ← title counted third time as bonus
# score_contribution = (len(hits) * weight) + (len(title_hits) * weight)
```

### E. `create_weekly_sequence` — POTWIERDZONA NIEZGODNOŚĆ SYGNATURY

Rzeczywista sygnatura (`src/core/weekly_sequence_orchestrator.py`, linia 198):
```python
def create_weekly_sequence(
    sequence_name: str,
    cadence: list[int] | None = None,
) -> dict[str, Any]:
```

Wywołanie w `sequence_builder.py`:
```python
seq_result = create_weekly_sequence(
    sequence_name=sequence_name,
    cadence=cadence,
    step_templates=MERGE_TAG_TEMPLATES,  # ← argument NIE ISTNIEJE w sygnaturze
    activate=False,                       # ← argument NIE ISTNIEJE w sygnaturze
)
# → TypeError: create_weekly_sequence() got an unexpected keyword argument 'step_templates'
# → LIVE RUN PADNIE przy próbie stworzenia każdej sekwencji
```

Dodatkowe konsekwencje:
- `step_templates` nie jest parametrem — funkcja ma własne hardcoded `MERGE_TAG_TEMPLATES`. Nie da się ich nadpisać z zewnątrz.
- `activate=False` nie jest parametrem — funkcja zawsze tworzy sekwencję nieaktywną (hardcoded `active=False`).
- Parametr `cadence` jest opcjonalny — jeśli nie podany, pobierany z `get_sequence_cadence()` z konfiguracji Apollo.

### F. Smoke test yaml import hang (naprawione)

```python
# Przed fix — test_news_pipeline_smoke.py:
for p in [_SRC_DIR, _ROOT_DIR]:  # _ROOT_DIR = workspace root z 20+ folderami
    sys.path.insert(0, p)
# Python skanuje cały workspace przy 'import yaml' → hang
# Po fix: tylko _SRC_DIR jest dodawany do sys.path
```
