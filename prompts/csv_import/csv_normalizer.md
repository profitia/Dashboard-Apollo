# CSV Normalizer — dokumentacja roli

## Cel
Normalizacja danych kontaktowych importowanych z pliku CSV, zanim trafią do agentów LLM.

## Dlaczego normalizacja jest jawna (nie przez LLM)
CSV-e z różnych źródeł mają różne układy kolumn, różne konwencje nazewnictwa i różny poziom kompletności danych.
Poleganie na LLM w kwestii rozdzielenia imienia od nazwiska, odgadnięcia płci czy wyznaczenia wołacza jest nieprzewidywalne i trudne do debugowania.

Dlatego:
- mapowanie kolumn jest deterministyczne (Python),
- rozdzielanie Name → first_name + last_name jest jawne,
- inferencja płci opiera się na słowniku polskich imion,
- wołacz jest generowany z reguł + słownika wyjątków,
- LLM dostaje dane już znormalizowane.

## Co robi normalizer
1. Mapuje kolumny CSV na pola wewnętrzne (COLUMN_MAP).
2. Rozdziela `Name` na `first_name` i `last_name`.
3. Inferencja `gender` na podstawie imienia (słownik + heurystyka końcówki).
4. Wyznacza `first_name_vocative` (wołacz) z reguł polskich.
5. Buduje `greeting` na podstawie gender + vocative.
6. Zapisuje `normalization_warnings` jeśli coś jest niejasne.

## Kiedy LLM może być potrzebny
Normalizer celowo NIE używa LLM. Jednak w przyszłości LLM mógłby być użyty do:
- walidacji wyjątkowo nietypowych imion (np. zagranicznych),
- lepszej inferencji płci dla imion niepolskich,
- destylacji notes/comments do formatu triggera.

To wymaga osobnego agenta — nie powinno być mieszane z normalizacją.

## Format wyjściowy
Każdy znormalizowany kontakt to dict z polami:
- `full_name`, `first_name`, `last_name`
- `first_name_vocative` (str | null)
- `gender` ("female" | "male" | "unknown")
- `greeting` (gotowe powitanie po polsku)
- `job_title`, `company_name`, `company_domain`
- `country`, `industry`, `notes`
- `normalization_warnings` (lista stringów)
