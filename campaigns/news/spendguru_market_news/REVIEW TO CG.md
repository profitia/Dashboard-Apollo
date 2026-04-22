# REVIEW TO CG — spendguru_market_news

**Dla:** ChatGPT review  
**Data:** 2026-04-22  
**Projekt:** AI Outreach Pipeline — news-triggered campaign (SpendGuru/Profitia)

---

## Co było reviewowane

News-triggered outreach pipeline: nowy kanał kampanii Apollo oparty na monitoringu artykułów branżowych. Pełny kod w Pythonie: 10 modułów, 4 YAML configs, 1 prompt template, smoke tests.

Cel: artykuł o firmie z branży FMCG/retail → ekstrakcja firmy → szukanie kontaktów w Apollo → generowanie 3-mailowej sekwencji → zapis do Apollo sequence → enrollment.

---

## Co wygląda solidnie

- **Architektura modułowa**: każdy plik ma jedną odpowiedzialność (scan, fetch, score, extract, find_contacts, generate, push_to_apollo, track_state, notify)
- **YAML-driven konfiguracja**: wszystkie progi, słowa kluczowe, tiry, źródła artykułów, cadence — edytowalne bez dotykania kodu Python
- **Dry-run mode** działa i zatrzymuje pipeline przed każdym API call
- **Tier perspectives** w generatorze maili są dobrze zróżnicowane i on-brand: Tier 1 (marża/EBIT), Tier 2 (standard przygotowania), Tier 3 (konkretna negocjacja)
- **Prompt template** zawiera explicit zasady typograficzne (brak em dash, małe po przecinku, Pan/Pani per gender), zakazane frazy ("nasza platforma", "zapraszam na demo", "Z perspektywy..."), CTA przed podpisem
- **Company cooldown (30 dni)** przez znormalizowaną nazwę firmy — zapobiega spamowaniu tej samej firmy wieloma kampaniami
- **Apollo custom fields truncation** do 4900 znaków — respektuje limit 5000 znaków Apollo
- **`activate_automatically: false`** — sekwencja zawsze nieaktywna po utworzeniu, wymaga ręcznego zatwierdzenia
- **State tracking z 8 statusami**: structured logging, queryable, persistent

---

## Główne zastrzeżenia (High priority)

1. **Vocative błąd**: pole `{{vocative_first_name}}` jest wypełniane surowym `first_name` = "Tomasz" zamiast formy wołacza "Tomaszu". Każdy mail zaczyna się od gramatycznie błędnego powitania po PL.

2. **Gender zawsze neutralny**: brak pola `gender` w dataclass `ContactRecord`. Funkcja `getattr(contact, "_gender", "")` zawsze zwraca `""` → forma Pan/Pani nigdy nie jest zdeterminowana → wszyscy dostają "Pani/Pana" niezależnie od płci.

3. **`article_key_facts` = lista keywords, nie fakty**: do LLM jako "kluczowe fakty z artykułu" trafia debug string ze scorera: `"[Industry/food_production]: produkcja żywności; [Signal/cost_pressure]: koszty"`. LLM nie ma dostępu do realnych faktów biznesowych z artykułu.

4. **`create_weekly_sequence()` sygnatura POTWIERDZONA NIEZGODNA**: rzeczywista sygnatura to `(sequence_name, cadence=None)`. `sequence_builder.py` wywołuje ją z `step_templates=MERGE_TAG_TEMPLATES, activate=False` — oba argumenty nie istnieją. Live run zwróci `TypeError` przy próbie tworzenia sekwencji. Wymaga natychmiastowej poprawki.

5. **State manager nie blokuje re-processingu failed articles**: `is_article_processed()` zwraca `True` tylko dla `sequence_created`. Artykuły z `scoring_failed`, `no_company`, `no_contacts` będą re-fetchowane i re-processowane przy każdym codziennym uruchomieniu.

6. **`client.search_contacts()` niesprawdzone**: metoda używana w `contact_finder.py` i `sequence_builder.py` nie była weryfikowana na aktualnym `ApolloClient`. Requires live API test.

---

## Pliki warte szczegółowego sprawdzenia ręcznie

| Plik | Dlaczego |
|---|---|
| `src/news/messaging/message_generator.py` | Vocative bug, gender bug, article_key_facts bug, TIER_PERSPECTIVES do oceny |
| `src/news/state/state_manager.py` | is_article_processed logic, atomic write brak |
| `src/news/apollo/sequence_builder.py` | create_weekly_sequence signature assumption, dead import SIG_HTML |
| `src/news/relevance/scorer.py` | Title triple-counting, date parsing fragility |
| `campaigns/news/spendguru_market_news/prompts/message_writer.md` | Jakość promptu, czy ZAKAZANE jest wystarczające |

---

## Sugerowane pytania do review

1. Czy struktura JSONa zwracanego przez `message_writer.md` prompt (pola: `email_1`, `email_2`, `email_3`, `review_notes`) jest optymalna? Co by dodać/zmienić?
2. Jak najprościej przekazać realne fakty z artykułu do LLM-a? Osobny LLM call pre-generation czy rozszerzyć istniejący prompt?
3. Czy logika tier mapping (tytuł → tier 1/2/3 przez keyword matching) wydaje się wystarczająco robustna dla bazy danych Apollo?
4. W jaki sposób najlepiej pobrać vocative form polskich imion? (lookup table vs heurystyka vs LLM)
5. Jakie dodatkowe testy smoke warto napisać przed pierwszym live runem?

---

## Ogólna ocena

**Early MVP.** Architektura i konfiguracja są gotowe. Logika biznesowa i prompt są solidne i zgodne z Negotiation Intelligence pozycjonowaniem SpendGuru. Przed live runem wymagane są 3 poprawki jakościowe (vocative, gender, article_key_facts jako faktyczne fakty) i 2 weryfikacje integracji Apollo (sygnatura create_weekly_sequence, metody ApolloClient). State manager potrzebuje drobnej logiki poprawki (blokowanie re-processingu). Po tych zmianach pipeline nadaje się do ograniczonego live testu z `human_review_gate: true`. Najszybsza do naprawy jest pozycja 4 (sequence_builder.py — zmiana wywołania create_weekly_sequence na poprawną sygnaturę, ~5 minut pracy).
