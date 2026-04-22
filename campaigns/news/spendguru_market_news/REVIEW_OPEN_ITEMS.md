# REVIEW OPEN ITEMS — spendguru_market_news

**Data:** 2026-04-22  
**Po smoke testach:** 21/21 passed  
**Cel:** Focused review przed pierwszym ograniczonym live runem

---

## 1. Closed since previous review

| Issue | Status | What changed |
|---|---|---|
| scorer.py — TypeError na obiektach datetime w `_get_article_age_days` | CLOSED | Dodano `isinstance(published_at, datetime)` + `.replace(tzinfo=timezone.utc)` przed delta obliczeniem. String formats obsługiwane przez `strptime` z try/except. |
| sequence_builder.py — TypeError w `build_sequence_name` gdy `article_date` jest obiektem `datetime` | CLOSED | `if isinstance(article_date, datetime): date_str = article_date.strftime("%Y-%m-%d")` — obsługa zarówno stringa jak i obiektu datetime. |
| state_manager.py — `is_article_processed` nie blokowało re-processingu failed articles | CLOSED | `is_article_processed` zwraca `True` dla wszystkich statusów poza `pending_review`. Linia: `if status and status != self.STATUS_PENDING_REVIEW: return True`. |

---

## 2. Still open

| # | Issue | Confirmed from code | Affected file | Exact reason | Production impact | Priority |
|---|---|---|---|---|---|---|
| 1 | `create_weekly_sequence` — signature mismatch, TypeError na live run | YES | `src/news/apollo/sequence_builder.py:291-297` | Wywołanie: `step_templates=MERGE_TAG_TEMPLATES, activate=False` — oba parametry **nie istnieją** w sygnaturze `create_weekly_sequence(sequence_name, cadence=None)`. Python rzuci `TypeError: unexpected keyword argument`. | Sekwencja nigdy nie zostanie utworzona w Apollo. Cały pipeline padnie po syncowaniu kontaktów. | CRITICAL |
| 2 | `client.search_contacts()` — metoda nie istnieje w ApolloClient | YES | `src/news/apollo/sequence_builder.py:132`, `Integracje/apollo_client.py` | `grep` nie zwraca `def search_contacts` w ApolloClient. Metoda wywoływana bez `hasattr` check, bez fallbacku. | `_find_or_create_apollo_contact()` rzuci `AttributeError` przy każdym contact ID lookup. Kontakty nie trafią do sekwencji. | HIGH |
| 3 | `vocative_first_name` = raw `first_name`, nie wołacz | YES | `src/news/messaging/message_generator.py:122` | `"{{vocative_first_name}}": contact.first_name` — imię bez odmiany. LLM dostaje "Tomasz", nie "Tomaszu". Prompt instruuje LLM do użycia jako wołacza w powitaniu. | Każdy mail w PL ma gramatycznie błędne powitanie: "Dzień dobry, Tomasz," zamiast "Dzień dobry, Tomaszu,". Niszczy wiarygodność. | HIGH |
| 4 | `gender` — pole nie istnieje w `ContactRecord`, zawsze neutralna forma | YES | `src/news/contacts/contact_finder.py:22-35` (dataclass), `src/news/messaging/message_generator.py:104` | `ContactRecord` nie ma pola `gender`. `getattr(contact, "_gender", "")` zawsze zwraca `""` → `gender_form = "neutralnie: Pani/Pana"` dla każdego kontaktu bez wyjątku. | Wszyscy odbiorcy — w tym mężczyźni z łatwym do rozpoznania imieniem — dostają `Pani/Pana`. Maile brzmią mniej personalnie. | HIGH |
| 5 | `article_key_facts` = debug string ze scorera, nie fakty z artykułu | YES | `src/news/orchestrator.py:292`, `src/news/relevance/scorer.py:207-220` | `article_key_facts = score_result.explanation`. Pole `explanation` zbudowane w scorer jako: `"[Industry/food_production]: produkcja żywności; [Signal/cost_pressure]: koszty"` — to lista matched keyword groups, nie streszczenie artykułu. | LLM dostaje instrukcję "Kluczowe fakty z artykułu (do użycia w wiadomości):" i dostaje debug string zamiast faktów. Hipotezy i trigger w mailu będą generyczne. | MEDIUM |
| 6 | Title double-counting w scorerze — zawyżone score'y | YES | `src/news/relevance/scorer.py:129-142` | `search_text = full_text + " " + tags_text + " " + title` — `full_text` już zawiera tytuł (opis: "połączony tytuł + lead + body"). Słowa z tytułu wchodzą raz w `hits` (przez `search_text`) i drugi raz przez osobne `title_hits` × weight. Suma `score_contribution = (len(hits) * weight) + (len(title_hits) * weight)`. | Score artykułów z silnymi tytułami może być zawyżony o kilka-kilkanaście punktów. Ryzyko kwalifikowania słabo pasujących artykułów. | MEDIUM |

---

## 3. Evidence snippets to paste into ChatGPT

---

### Snippet A — `message_generator.py` / `_fill_prompt`

**File:** `src/news/messaging/message_generator.py`  
**Function:** `_fill_prompt` (lines ~100-137)  
**Why it matters:** Pokazuje vocative bug i gender bug w jednym miejscu.

```python
# Gender form
gender_form_map = {
    "male": "Pan (forma: Panu/Pana/Pan)",
    "female": "Pani (forma: Pani)",
}
gender_form = gender_form_map.get(getattr(contact, "_gender", ""), "neutralnie: Pani/Pana")
# ^ BUG: ContactRecord nie ma pola _gender. getattr zawsze zwraca "" → gender_form zawsze "neutralnie: Pani/Pana"

replacements = {
    "{{vocative_first_name}}": contact.first_name,
    # ^ BUG: contact.first_name = "Tomasz" (mianownik). Prompt oczekuje wołacza: "Tomaszu".
    "{{last_name}}": contact.last_name,
    "{{job_title}}": contact.job_title,
    "{{company_name}}": contact.company_name,
    "{{tier_label}}": tier_label,
    "{{article_title}}": article.title,
    "{{article_source}}": article.source_id,
    "{{article_date}}": pub_date,
    "{{article_url}}": article.canonical_url,
    "{{article_lead}}": article.lead or "",
    "{{article_body_excerpt}}": body_excerpt,
    "{{article_key_facts}}": article_key_facts,
    # ^ article_key_facts pochodzi z score_result.explanation — patrz Snippet C
    "{{tier_perspective}}": perspective.strip(),
    "{{gender_form}}": gender_form,
}
```

---

### Snippet B — `contact_finder.py` / `ContactRecord` dataclass

**File:** `src/news/contacts/contact_finder.py`  
**Function:** `ContactRecord` dataclass (lines ~22-35)  
**Why it matters:** Dowód że pole `gender` nie istnieje w modelu danych. Brak pola = brak możliwości gender-aware komunikacji.

```python
@dataclass
class ContactRecord:
    first_name: str
    last_name: str
    full_name: str
    email: str
    job_title: str
    company_name: str
    company_domain: str
    tier: str            # tier_1_c_level | tier_2_procurement_management | tier_3_buyers_operational | tier_uncertain
    tier_label: str
    tier_reason: str
    source: str          # apollo | manual | enrichment
    confidence: float    # 0.0-1.0
    apollo_contact_id: str | None = None
    linkedin_url: str | None = None
    # BUG: brak pola gender — _gender nie istnieje jako atrybut
    # getattr(contact, "_gender", "") w message_generator zawsze zwraca ""
```

---

### Snippet C — `orchestrator.py` + `scorer.py` / article_key_facts pipeline

**File:** `src/news/orchestrator.py` (line 292), `src/news/relevance/scorer.py` (lines 207-220)  
**Function:** `_process_article` + `score_article`  
**Why it matters:** Pokazuje co LLM faktycznie dostaje jako "kluczowe fakty z artykułu".

```python
# orchestrator.py:292
article_key_facts = score_result.explanation
# explanation jest zbudowane w scorer.py tak:

# scorer.py:207-220
parts = []
if matched_industry:
    for gid, terms in matched_industry.items():
        parts.append(f"[Industry/{gid}]: {', '.join(terms[:5])}")
if matched_purchase:
    for gid, terms in matched_purchase.items():
        parts.append(f"[Signal/{gid}]: {', '.join(terms[:5])}")
if amp_hits:
    parts.append(f"[Amplifiers]: {', '.join(amp_hits[:3])}")
if age_days is not None:
    parts.append(f"[Age]: {age_days} days")

explanation = "; ".join(parts) if parts else "No significant matches found."
# Przykładowy output: "[Industry/food_production]: produkcja żywności, żywność; [Signal/cost_pressure]: koszty, inflacja; [Age]: 2 days"

# To trafia do promptu jako:
# "Kluczowe fakty z artykułu (do użycia w wiadomości):
#  [Industry/food_production]: produkcja żywności, żywność; [Signal/cost_pressure]: koszty, inflacja; [Age]: 2 days"
```

---

### Snippet D — `sequence_builder.py` / `create_weekly_sequence` call

**File:** `src/news/apollo/sequence_builder.py` (lines ~287-298)  
**Function:** `create_news_sequence`  
**Why it matters:** CRITICAL bug — sygnatura niezgodna. Wywołanie z parametrami które nie istnieją.

```python
# sequence_builder.py — aktualne wywołanie:
seq_result = create_weekly_sequence(
    sequence_name=sequence_name,
    cadence=cadence,
    step_templates=MERGE_TAG_TEMPLATES,  # ← PARAMETR NIE ISTNIEJE
    activate=False,                      # ← PARAMETR NIE ISTNIEJE
)

# weekly_sequence_orchestrator.py — rzeczywista sygnatura:
def create_weekly_sequence(
    sequence_name: str,
    cadence: list[int] | None = None,   # ← TYLKO TE DWA PARAMETRY
) -> dict[str, Any]:
    ...
# Wywołanie z step_templates i activate rzuci:
# TypeError: create_weekly_sequence() got unexpected keyword argument 'step_templates'
```

---

### Snippet E — `sequence_builder.py` / `client.search_contacts`

**File:** `src/news/apollo/sequence_builder.py` (lines ~130-136)  
**Function:** `_find_or_create_apollo_contact`  
**Why it matters:** ApolloClient nie ma metody `search_contacts`. Brak hasattr check, brak fallbacku.

```python
# sequence_builder.py:
def _find_or_create_apollo_contact(client, contact) -> str | None:
    if contact.apollo_contact_id:
        return contact.apollo_contact_id

    # Szukaj po emailu
    try:
        result = client.search_contacts({"email": contact.email})
        # ^ ApolloClient nie ma def search_contacts — rzuci AttributeError
        # contact_finder.py używa client.people_search z hasattr check (bezpieczniejsze)
        # tu nie ma ani hasattr check, ani fallbacku na _request
        people = result.get("contacts", []) if isinstance(result, dict) else []
        if people:
            return people[0].get("id")
    except Exception as exc:
        log.debug("Apollo contact search failed: %s", exc)
    # Jeśli search_contacts rzuci AttributeError → caught by except, przechodzi do create
    # create_contact może zadziałać — ale duplikuje kontakty przy każdym uruchomieniu
```

---

### Snippet F — `message_writer.md` / {{article_key_facts}} context

**File:** `campaigns/news/spendguru_market_news/prompts/message_writer.md`  
**Section:** ARTYKUŁ BAZOWY  
**Why it matters:** Prompt oczekuje faktów, dostaje debug string ze scorera.

```markdown
## ARTYKUŁ BAZOWY (trigger)

Tytuł: {{article_title}}
Źródło: {{article_source}}
Data: {{article_date}}
URL: {{article_url}}

Streszczenie / lead: {{article_lead}}

Fragment treści: {{article_body_excerpt}}

Kluczowe fakty z artykułu (do użycia w wiadomości):
{{article_key_facts}}
```

Sekcja "Kluczowe fakty" sugeruje LLM że dostaje ustrukturyzowane fakty biznesowe.  
Faktycznie dostaje: `"[Industry/food_production]: produkcja żywności; [Signal/cost_pressure]: koszty; [Age]: 2 days"`  
LLM musi sobie z tym radzić bez żadnych realnych danych o tym co konkretnie napisano w artykule.

---

## 4. Final open issues before first limited live run

### MUST FIX (blokuje live run)

1. **`create_weekly_sequence` — signature mismatch** (`sequence_builder.py:291-297`)  
   Wywołanie z `step_templates` i `activate` które nie istnieją w sygnaturze.  
   Fix: usuń oba parametry z wywołania. Jeśli `step_templates` i `activate` są potrzebne, trzeba rozszerzyć sygnaturę w `weekly_sequence_orchestrator.py`.  
   Czas: ~15-30 min + weryfikacja czy orchestrator obsługuje te parametry wewnętrznie.

2. **`client.search_contacts()` — metoda nie istnieje** (`sequence_builder.py:132`)  
   Zastąp przez `client.people_search` z `hasattr` check (jak w `contact_finder.py`) lub przez `client._request("POST", "/api/v1/mixed_people/search", ...)`.  
   Czas: ~10 min.

### MUST VERIFY (potrzebny live API test przed szerszym rolloutem)

3. **`client.update_contact_custom_fields`** — metoda istnieje w ApolloClient (grep potwierdza linia 278), ale sygnatura i zachowanie niesprawdzone na żywym API. Test: wywołaj na jednym kontakcie testowym.

4. **Apollo list operations** (`_add_to_apollo_list`)  
   Używa `client._request("GET", "/api/v1/labels")` + add_contact_ids. Nie wiadomo czy Apollo API zwraca `labels` w tej formie i czy lista PL Tier 1/2/3 istnieje w środowisku produkcyjnym.

5. **Enrollment endpoint** (`/api/v1/emailer_campaigns/{id}/add_contact_ids`)  
   Format payloadu i dostępność niesprawdzone. Może wymagać innych pól niż `contact_ids` + `sequence_active_in_other_campaigns`.

### SHOULD FIX before wider rollout (jakość wiadomości)

6. **Vocative** — każda kampania PL będzie miała błędne powitanie do czasu naprawy. Rozwiązania: lookup table PL (najprostsza), heurystyka sufixów, LLM pre-call.

7. **Gender** — dodaj pole `gender` do `ContactRecord` i wypełniaj z danych Apollo (`person.get("gender")` lub `person.get("sex")`). Apollo zwraca to pole dla kontaktów z enrichment.

8. **`article_key_facts`** — zastąp `score_result.explanation` wyciągiem z `article.lead + article.body[:500]` lub dedykowanym LLM summarization call. Obecny debug string szkodzi jakości promptu.
