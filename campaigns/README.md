# Campaigns — Kampanie Apollo

Wszystkie kampanie outreachowe Profitia / SpendGuru są przechowywane w tym katalogu, podzielone na typy.

## Typy kampanii

### `ad_hoc/`
Kampanie budowane na podstawie jednorazowego kontekstu:
- posty LinkedIn
- konferencje i wydarzenia branżowe
- listy specjalne
- jednorazowe akcje outreachowe

### `news/`
Kampanie budowane na podstawie triggerów rynkowych:
- artykuły branżowe
- newsy rynkowe
- zmiany cen, regulacje, fuzje, restrukturyzacje
- sygnały z rynku dostawców

### `standard/`
Klasyczne kampanie prospectingowe:
- oparte o ICP, branże i role
- listy firm i kontaktów
- sekwencje Apollo
- cykliczny outreach

## Wspólne zasady

- Wszystkie kampanie korzystają ze wspólnego **source_of_truth/** (ICP, branże, framework, styl, compliance).
- Każda kampania ma własne foldery: `input/`, `output/`, `review/`, `prompts/`, `logs/`.
- Każda kampania ma plik `campaign_config.yaml` z konfiguracją.
- **Żadna kampania nie wysyła maili automatycznie** — wszystko trafia do review.
- Wyniki kampanii trafiają do folderu danej kampanii, nie do globalnego `outputs/`.
- Nie mieszaj inputów, outputów ani promptów między kampaniami.

## Struktura kampanii

```
campaigns/{typ}/{nazwa_kampanii}/
├── input/              # Dane wejściowe (CSV, JSON, listy)
├── output/             # Wyniki runów (wiadomości, raporty, payloady)
├── review/             # Kontakty do ręcznego przeglądu
├── prompts/            # Prompty specyficzne dla kampanii
├── logs/               # Logi runów
└── campaign_config.yaml # Konfiguracja kampanii
```
