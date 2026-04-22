# Model Policy — zasady użycia modeli LLM w środowisku kampanijnym

## Tier'y modeli

### HIGH_QUALITY → gpt-5.4
Używany do:
- finalne maile do wysłania do klienta lub prospecta
- personalizacja treści
- rewrite i poprawa jakości kopii
- trudne decyzje copywriterskie
- tworzenie finalnych sekwencji outreachowych
- kampanie LinkedIn (finalne treści)

### STANDARD → gpt-5.4-mini
Używany do:
- szkice maili (draft mode)
- generowanie wariantów do wyboru
- mniej krytyczne generowanie treści
- fallback, jeśli gpt-5.4 zwróci błąd lub będzie niedostępny
- testy pipeline'u

### CHEAP_VALIDATION → gpt-5.4-nano
Używany do:
- klasyfikacja ICP (industry, persona)
- scoring leadów
- walidacja CTA (czy mail ma wyraźne CTA)
- sprawdzanie formatu (myślnik "-" zamiast em dash "—")
- sprawdzanie nagłówków THREAD
- wykrywanie zakazanych fraz
- kontrola jakości bez rewrite'u
- walidacja JSON/struktury

## Zasady oszczędzania budżetu

1. **Nie wysyłaj pełnych dokumentów do gpt-5.4** — jeśli wystarczy krótki brief lub fragment, ogranicz payload.
2. **Nie regeneruj całej kampanii** — jeśli zmieniany jest tylko jeden fragment (np. CTA), regeneruj tylko ten element.
3. **Zapisuj wyniki pośrednie** — hipotezy, research, persona selection — żeby nie generować ich ponownie.
4. **Używaj gpt-5.4-nano do walidacji** — QA, format check, CTA check — te zadania nie wymagają drogiego modelu.
5. **Używaj gpt-5.4 tylko dla finalnej jakości** — finalne maile, personalizacja, rewrite.
6. **Loguj użycie tokenów** — każde wywołanie API z usage w response jest logowane.
7. **Fallback chain chroni budżet** — jeśli gpt-5.4 zwróci błąd, automatycznie próbuje tańszy model zamiast retry'ować drogi.

## Zmiana modeli

Aby zmienić primary model globalnie:
1. Edytuj `.env` → `OPENAI_PRIMARY_MODEL=nowy-model`
2. Lub ustaw zmienną środowiskową: `export OPENAI_PRIMARY_MODEL=nowy-model`
3. Restart pipeline'u — nowy model zostanie użyty automatycznie.

Analogicznie dla `OPENAI_FALLBACK_MODEL` i `OPENAI_CHEAP_MODEL`.

## Fallback

- Jeśli gpt-5.4 zwróci błąd (rate limit, timeout, connection error) → automatycznie gpt-5.4-mini
- Jeśli gpt-5.4-mini też zwróci błąd → automatycznie gpt-5.4-nano
- Jeśli wszystkie modele zawiodą → heurystyczny fallback (bez LLM)
- Błąd autentykacji (AuthenticationError) → natychmiast heurystyczny fallback (nie próbuj kolejnych modeli)
- W logach zawsze informacja, który model został użyty i czy był fallback
- Klucz API NIGDY nie jest logowany
