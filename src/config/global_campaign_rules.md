# Globalne reguły kampanii — AI Outreach System

Wszystkie kampanie outreachowe (standard, CSV import, AdHoc, LinkedIn, news, konferencje)
muszą przestrzegać poniższych reguł.

---

## 1. Logika maila (obowiązkowa sekwencja)

panel/kontekst → rola odbiorcy → firma odbiorcy → napięcie biznesowe → framework/podejście → lekkie CTA

- Panel jest PUNKTEM WEJŚCIA, ale wartość maila jest w przełożeniu na rolę i firmę
- Zawsze mów do konkretnej osoby w konkretnej roli (CFO, CEO, GM, Commercial Director...)
- Zawsze pokaż biznesowy koszt problemu (marża, gotówka, przewidywalność, zapas, pricing, warunki, ryzyko)

## 2. Personalizacja

Mail musi być osadzony w:
- stanowisku i odpowiedzialności biznesowej odbiorcy
- realiach i modelu biznesowym firmy
- napięciach typowych dla tej funkcji
- wpływie na: marżę, cash flow, dostępność, pricing, zapas, ryzyko, wzrost, rentowność

## 3. Ton i styl

- Profesjonalny, konkretny, elegancki, ludzki
- NIE brzmi jak automatyczny prospecting ani masowy cold mail
- Brzmi jak sensowny follow-up po konferencji, nie oferta sprzedażowa
- Framework używany naturalnie, nie nachalnie

## 4. CTA

- Każdy mail MUSI kończyć się wyraźnym, praktycznym CTA
- Łatwe do odpisania, zachęca do telefonu/Teams/podania terminu
- Styl: "Proszę o informację, jak będzie Panu/Pani wygodnie porozmawiać"
- Najpierw CTA, potem podpis

## 5. Typografia i ortografia

- NIGDY em dash "—" → ZAWSZE zwykły myślnik " - "
- Po kropce ZAWSZE wielka litera
- Po powitaniu z przecinkiem ("Dzień dobry Panie Marku,") → następny akapit od MAŁEJ litery

## 6. Rola odbiorcy — jednoznaczność

- NIGDY "Z perspektywy [stanowisko]..." → sugeruje że nadawca pełni tę rolę
- ZAWSZE: "W Pana/Pani roli jako...", "Dla osoby odpowiedzialnej za...", "Jako [stanowisko], odpowiada Pan/Pani za..."

## 7. Sekwencja 3 maili

- Email 1: Spersonalizowane podziękowanie + panel + hipoteza + framework + CTA
- Email 2: WNOSI NOWĄ WARTOŚĆ (nie jest tylko przypomnieniem!) — rozwija problem, pokazuje 1 konkretny mechanizm/konsekwencję
- Email 3: Krótki, prosty, bez presji, jasne CTA

## 8. Kampanie pokonferencyjne

- Email 1 MUSI zawierać pełną nazwę wydarzenia w pierwszym akapicie, np. "podczas Poland & CEE Retail Summit 2026"
- Nazwa eventu nie może być skrócona ani pominięta

## 9. Nagłówek THREAD i temat

- Nagłówki EMAIL 1/2/3 — identyczny styl
- Etykiety Od/Do/Temat — identyczny styl
- Spójność czcionki/koloru/rozmiaru w klasie
- Email 2 i Email 3: temat w formacie "Re: [temat Email 1]" — tworzy naturalny wątek
- NIE stosuj "Re: Re:" — zawsze tylko jeden prefix "Re:" oparty na temacie Email 1

## 10. Zakazane

- Generyczne sformułowania pasujące do każdej firmy
- Abstrakcyjny język o "strategii/danych/procesach" BEZ konsekwencji biznesowych
- Nadmiernie sprzedażowy ton
- Mechaniczne wklejanie frameworku bez kontekstu
- "porządek danych", "uporządkowanie informacji" jako główny benefit
- "nasza platforma", "nasze narzędzie"
- Zaczynanie od produktu/firmy nadawcy/demo
- Maile wysyłalne do 20 osób bez zmian

## 11. Modele LLM

- Finalne maile → gpt-5.4 (HIGH_QUALITY)
- Szkice i warianty → gpt-5.4-mini (STANDARD)
- Walidacja i scoring → gpt-5.4-nano (CHEAP_VALIDATION)
- Nie używaj lokalnych hardcoded modeli — korzystaj z centralnego llm_router
- Finalne maile v3 po kampaniach LinkedIn traktuj jako dobry wzorzec jakości

## 12. Referencja jakości

Finalne maile z kampanii Retail Summit 2026 (kwiecień 2026) są uznane za reference quality.

## 13. ICP TIERS — GLOBAL RULE

Od teraz przy generowaniu kampanii zawsze określ Tier odbiorcy:
- **Tier 1** - C-Level / Zarząd / Właściciele
- **Tier 2** - Procurement Management / Dyrektorzy zakupów / management zakupowy i operacyjny
- **Tier 3** - Buyers / Category Managers / osoby operacyjne

### Zasady przypisywania Tieru

1. Jeśli użytkownik poda Tier, użyj pełnego kontekstu z `source_of_truth/icp_tiers.yaml`.
2. Jeśli użytkownik poda tylko stanowisko, automatycznie przypisz Tier na podstawie `role_to_tier_mapping`.
3. Jeśli stanowisko jest niejednoznaczne, użyj reguł `conditional_tier_2_or_3`.
4. Jeśli nadal nie wiadomo, oznacz jako `tier_uncertain` i zaproponuj najbardziej prawdopodobny Tier z uzasadnieniem.

### Dopasowanie treści do Tieru

- **Tier 1**: wynik, marża, budżet, cash flow, ryzyko, strategia, egzekucja
- **Tier 2**: savings całej firmy, zespół, standard negocjacji, oszczędności, avoided cost, raportowanie do zarządu
- **Tier 3**: savings w kategorii, podwyżki, oferta fair/unfair, benchmarki, argumentacja, szybkie przygotowanie

### Savings accountability

- **Tier 1**: oczekuje, że Tier 2 dowiezie oszczędności w skali firmy
- **Tier 2**: odpowiada przed zarządem za savings delivery w całej organizacji
- **Tier 3**: odpowiada przed przełożonym za savings i avoided cost w swojej kategorii

### Pełna definicja Tierów

Plik `source_of_truth/icp_tiers.yaml` zawiera kompletną definicję każdego Tieru:
pain points, potrzeby, value proposition, ton komunikacji, czego unikać.

## 14. CAMPAIGN NAMING - GLOBAL RULE

Każda kampania musi mieć `campaign_name` generowane automatycznie według standardu:

```
{CampaignType}_{Tier}_{Segment}_{Angle}_{Market}_{Wxx_Mxx_Rxx}_{vX}
```

Przykład: `LinPost_T2_Prod_Savings_PL_W01_M05_R26_v1`

### Zasady

1. Każda kampania MUSI mieć `campaign_name` generowane przez `campaign_name_builder.py`.
2. Każda kampania MUSI mieć `campaign_metadata` zapisane osobno w outputach.
3. Jeśli Apollo sequence jest tworzona przez API, ma dostać tę samą nazwę co `campaign_name`.
4. Każdy kontakt MUSI mieć `last_campaign_*` i `campaign_history`.
5. Jeśli kontakt należy do wielu kampanii, historia NIE może być nadpisywana — tylko dopisywana.
6. `campaign_name` jest source of truth dla analityki kampanii.

### Timing (week-of-month)

Week-of-month liczony z numeru dnia:
- W01 = 1-7, W02 = 8-14, W03 = 15-21, W04 = 22-28, W05 = 29-31

NIE używaj ISO weeks ani tygodni od poniedziałku.

### Source of truth

- Reguły: `source_of_truth/campaign_naming_rules.yaml`
- Generator: `src/core/campaign_name_builder.py`
- Historia kontaktów: `src/core/contact_campaign_history.py`
- Sync Apollo: `src/core/apollo_campaign_sync.py`

### Output kampanii z Tierem

Każdy wygenerowany kontakt / kampania musi zawierać:
- `tier` - identyfikator Tieru
- `tier_label` - czytelna etykieta
- `tier_reason` - dlaczego ten Tier
- `savings_accountability` - kontekst oszczędnościowy
- `messaging_angle` - kąt komunikacji

## 15. APOLLO CAMPAIGN TYPES - GLOBAL RULE

Każda kampania musi mieć jawnie określony typ delivery i Apollo step type.
Typy NIE mogą być zgadywane ad hoc - muszą być rozstrzygane przez source of truth.

### Domyślna reguła

Standardowe kampanie mailowe (LinPost, LinEvent, NewsTrig, AdHoc, ApolloList, CSVImport, FollowUp, WebSignal, Intent) mają domyślnie:
- `delivery_type` = `email_auto`
- `apollo_step_type` = `Automatic email`
- `sequence_template_name` = `email_only`

### Wyjątki

- `NoEmail` - NIE mapuje się na Automatic email. Delivery type = `task`, Apollo step type = `Action item`.

### Kampanie wielokanałowe (przyszłość)

W przyszłości kampanie wielokanałowe mają używać `sequence_templates` z `source_of_truth/apollo_campaign_types.yaml`.
Dostępne templates: `email_only`, `email_plus_call`, `linkedin_plus_email`, `multichannel_light`, `no_email_research`.

### Metadata kampanii

Każda kampania MUSI zapisywać w metadanych:
- `delivery_type` - wewnętrzny typ delivery
- `apollo_step_type` - typ stepu Apollo
- `sequence_template_name` - nazwa użytego template'u
- `is_multichannel` - czy kampania jest wielokanałowa
- `apollo_delivery_source` = `"source_of_truth"`

### Source of truth

- Typy Apollo: `source_of_truth/apollo_campaign_types.yaml`
- Resolver: `src/core/apollo_campaign_sync.py` → `resolve_campaign_delivery_type()`, `resolve_apollo_step_type()`, `build_apollo_sequence_template()`

## 16. Apollo Contact Name Enrichment - Global Rule

### Źródło prawdy

Jedynym źródłem danych do uzupełniania pól kontaktu jest plik `context/Vocative names od VSC.csv` (~24 978 wpisów, separator `;`, kolumny: Mianownik;Wołacz;Płeć).

### Pola custom Apollo

- **Vocative First Name** - wołacz imienia (np. "Tomaszu", "Agnieszko")
- **Sex** - płeć kontaktu ("male" / "female")

### Reguły enrichmentu

1. Pobierz `first_name` kontaktu
2. Sprawdź aktualne wartości pól custom Apollo (Vocative First Name, Sex)
3. Jeśli OBA pola wypełnione → nie zmieniaj
4. Jeśli którekolwiek puste → sprawdź source of truth
5. Jeśli imię w source of truth → uzupełnij TYLKO puste pola
6. Jeśli imienia NIE MA w source of truth → zostaw puste, nie zgaduj, oznacz `not_found_in_dictionary`
7. NIGDY nie nadpisuj istniejących wartości Apollo

### Zakaz zgadywania

- LLM / kod NIE MA zgadywać vocative ani gender
- Jeśli imienia nie ma w słowniku → puste pole jest lepsze niż błędne
- Brak heurystyk, brak reguł końcówkowych, brak fallbacków

### Fallback greeting

Jeśli Vocative First Name jest puste po enrichmencie:
- Greeting = "Dzień dobry," (neutralne)
- NIGDY nie używaj pustego vocative w szablonach maili

### Moduł

- Resolver: `src/core/apollo_contact_enrichment.py`
- Funkcje: `enrich_contact_name_fields()`, `resolve_vocative_from_dictionary()`, `resolve_sex_from_dictionary()`, `build_safe_greeting()`
