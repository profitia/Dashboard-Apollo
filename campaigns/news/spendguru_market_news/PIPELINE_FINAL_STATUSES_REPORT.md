# PIPELINE FINAL STATUSES REPORT — spendguru_market_news

**Data:** 2026-04-22  
**Wersja:** 1.0  
**Kampania:** spendguru_market_news  
**Status:** WDROŻONE I PRZETESTOWANE

---

## 1. Executive Summary

### Po co wykonano uspójnienie

Pipeline przetwarzał każdy artykuł przez wiele etapów (fetch → qualify → entity → contacts → messages → Apollo), ale nie miał spójnego modelu statusów końcowych. Ten sam case mógł być opisany różnymi stringami w zależności od warstwy:

- `state.mark_article()` używał wartości z `ArticleStateManager` (np. `"article_qualified_but_no_contacts"`)
- `results.append()` używał innych stringów (np. `"no_contacts"`)
- Powiadomienia email używały własnych statusów (`"READY_FOR_REVIEW"`, `"BLOCKED_NO_EMAIL"`)
- Niektóre statusy były literałami hard-coded w orchestratorze (np. `"company_in_cooldown"`, `"resolution_no_match"`)

Brak single source of truth powodował:
- niemożność rzetelnego raportowania per-status
- ryzyko dryfu nazw przy przyszłych zmianach
- utrudnioną diagnostykę ("dlaczego ten case się zatrzymał?")

### Co zostało uporządkowane

Wprowadzono jeden spójny model finalnych statusów pipeline'u:

1. Jeden plik źródłowy: **`src/news/pipeline_status.py`** — jedyne miejsce definiowania statusów
2. **`state_manager.py`** — stałe `STATUS_*` są teraz aliasami na `PipelineStatus.*`
3. **`orchestrator.py`** — `state.mark_article()` i `results.append()` używają tych samych wartości z `PipelineStatus`
4. Dodano `final_stage` i `final_reason` do każdego wywołania `mark_article()` — zapisywane w pliku stanu

### Finalny model

14 statusów w 5 kategoriach. Jeden finalny status per artykuł/case.

---

## 2. Final Status Model

| Status | Znaczenie | Etap | Wysyła mail | Wymaga review | Retryable |
|--------|-----------|------|-------------|---------------|-----------|
| **READY_FOR_REVIEW** | Flow kompletny — sekwencja gotowa | apollo_write | ✅ 🟢 | ✅ | ❌ |
| **REJECTED_QUALIFICATION** | Artykuł nie spełnił kryteriów | qualification | ❌ | ❌ | ❌ |
| **SKIPPED_FETCH_FAILED** | Nie udało się pobrać artykułu | fetch | ❌ | ❌ | ✅ |
| **SKIPPED_DUPLICATE** | Artykuł już przetworzony | dedup | ❌ | ❌ | ❌ |
| **SKIPPED_COOLDOWN** | Firma w oknie cooldown | dedup | ❌ | ❌ | ❌ |
| **REVIEW_ONLY** | Tryb review_only — sekwencja nie zapisana | review | ❌ | ✅ | ✅ |
| **BLOCKED_COMPANY_NOT_FOUND** | Brak firmy w artykule | entity_extraction | ❌ | ❌ | ❌ |
| **BLOCKED_COMPANY_EXCLUDED** | Firma wykluczona z ICP | entity_extraction | ❌ | ❌ | ❌ |
| **BLOCKED_COMPANY_NO_MATCH** | Company resolver: brak dopasowania | company_resolution | ❌ | ❌ | ❌ |
| **BLOCKED_COMPANY_AMBIGUOUS** | Company resolver: niejednoznaczny wynik | company_resolution | ❌ | ✅ | ❌ |
| **BLOCKED_NO_CONTACT** | Brak kontaktów w Apollo | contact_search | ❌ | ❌ | ✅ |
| **BLOCKED_NO_EMAIL** | Kontakty znalezione, brak emaila | contact_search | ✅ 🔴 | ✅ | ✅ |
| **BLOCKED_MESSAGE_GENERATION_FAILED** | LLM nie wygenerował treści | message_generation | ❌ | ❌ | ✅ |
| **PENDING_MANUAL_REVIEW** | Human review gate aktywny | review_gate | ❌ | ✅ | ✅ |

---

## 3. Mapping starych stanów na nowy model

### Warstwa state manager (`state.mark_article()`)

| Stara wartość | Nowa wartość (PipelineStatus) |
|---------------|-------------------------------|
| `"fetch_failed"` (literal) | `SKIPPED_FETCH_FAILED` |
| `"scoring_failed"` (stała) | `REJECTED_QUALIFICATION` |
| `"no_company"` (stała) | `BLOCKED_COMPANY_NOT_FOUND` |
| `"excluded"` (stała) | `BLOCKED_COMPANY_EXCLUDED` |
| `"company_in_cooldown"` (literal) | `SKIPPED_COOLDOWN` |
| `"resolution_no_match"` (literal) | `BLOCKED_COMPANY_NO_MATCH` |
| `"resolution_ambiguous"` (literal) | `BLOCKED_COMPANY_AMBIGUOUS` |
| `"article_qualified_but_no_contacts"` (stała) | `BLOCKED_NO_CONTACT` (brak kontaktów) |
| `"no_contacts"` (stała) | `BLOCKED_NO_EMAIL` (kontakty bez emaila) |
| `"pending_review"` (stała) | `PENDING_MANUAL_REVIEW` |
| `"sequence_created"` (stała) | `READY_FOR_REVIEW` |

### Warstwa results (`results.append()`)

| Stara wartość | Nowa wartość |
|---------------|--------------|
| `"no_company"` | `BLOCKED_COMPANY_NOT_FOUND` |
| `"excluded"` | `BLOCKED_COMPANY_EXCLUDED` |
| `"company_in_cooldown"` | `SKIPPED_COOLDOWN` |
| `"resolution_no_match"` | `BLOCKED_COMPANY_NO_MATCH` |
| `"resolution_ambiguous"` | `BLOCKED_COMPANY_AMBIGUOUS` |
| `"no_contacts"` | `BLOCKED_NO_CONTACT` lub `BLOCKED_NO_EMAIL` (zależnie od przypadku) |
| `"no_contacts_with_email"` | `BLOCKED_NO_EMAIL` |
| `"pending_review"` | `PENDING_MANUAL_REVIEW` |
| `"review_only"` | `REVIEW_ONLY` |
| `"sequence_created"` | `READY_FOR_REVIEW` |

### Kluczowe naprawienie niespójności

**Poprzednio:** Dwa różne przypadki braku kontaktów były nierozróżnialne:
1. Brak kontaktów w Apollo w ogóle → state: `"article_qualified_but_no_contacts"`, results: `"no_contacts"`
2. Kontakty znalezione, ale bez emaila → state: `"no_contacts"`, results: `"no_contacts_with_email"`

**Teraz:**
1. Brak kontaktów → `BLOCKED_NO_CONTACT` (obydwie warstwy)
2. Kontakty bez emaila → `BLOCKED_NO_EMAIL` (obydwie warstwy) + wysłanie powiadomienia

---

## 4. Technical Implementation

### Pliki zmienione

| Plik | Zmiana |
|------|--------|
| **`src/news/pipeline_status.py`** | NOWY — jedyne źródło prawdy. Klasa `PipelineStatus` z 14 stałymi + `STATUS_META` z metadanymi każdego statusu + `REPROCESSABLE_STATUSES`, `NOTIFICATION_STATUSES`, `RETRYABLE_STATUSES`. |
| **`src/news/state/state_manager.py`** | Import `PipelineStatus`. Stałe `STATUS_*` to teraz aliasy na `PipelineStatus.*`. Zaktualizowano `is_article_processed()` — używa `REPROCESSABLE_STATUSES` zamiast hard-coded `STATUS_PENDING_REVIEW` string. Backward compat: stary `"pending_review"` nadal rozpoznawany. |
| **`src/news/orchestrator.py`** | Import `PipelineStatus`. Wszystkie `state.mark_article()` i `results.append()` używają `PipelineStatus.*`. Dodano `final_stage` i `final_reason` do każdego call `mark_article()`. Naprawiono rozbieżność contact status: teraz `BLOCKED_NO_CONTACT` vs `BLOCKED_NO_EMAIL` są rozróżniane. |

### Pliki niezmienione

| Plik | Powód braku zmiany |
|------|--------------------|
| `src/news/apollo/sequence_builder.py` | Używa `"READY_FOR_REVIEW"` i `"BLOCKED_NO_EMAIL"` — identyczne wartości jak w `PipelineStatus`. Brak ryzyka dryfu. |
| `src/news/notifications/notifier.py` | Nie definiuje statusów, tylko dispatches results. |
| `src/news/entity/company_resolver.py` | Ma własny wewnętrzny model (`MATCH_CONFIDENT`, itp.) — to statusy resolvera, nie pipeline'u. |
| `src/news/contacts/contact_finder.py` | Nie definiuje statusów pipeline'u. |

### `final_stage` i `final_reason` w pliku stanu

Każde `mark_article()` teraz zapisuje:
```json
{
  "status": "BLOCKED_NO_EMAIL",
  "final_stage": "contact_search",
  "final_reason": "Contacts identified in Apollo but no email address available",
  "updated_at": "2026-04-22T..."
}
```

### Backward compatibility

Istniejące pliki stanu JSON (z poprzednio przetworzonymi artykułami) nadal działają poprawnie:
- `is_article_processed()` zwraca `True` dla każdego niepustego statusu, który NIE jest w `REPROCESSABLE_STATUSES`
- Stary `"pending_review"` jest w `REPROCESSABLE_STATUSES` → pipeline może ponowić te artykuły
- Stare statusy jak `"sequence_created"`, `"no_company"` itp. są traktowane jako "przetworzone" — bez re-processingu

---

## 5. Validation

### Smoke tests: 29/29 PASS
```
pytest tests/test_news_pipeline_smoke.py -q
29 passed in 0.16s
```

### Notification tests: 10/10 PASS
```
python tests/test_notification_statuses.py
10/10 PASS | 0/10 FAIL
```

### Consistency assertions (inline validation)
```python
# Wszystkie assertions przeszły:
assert ArticleStateManager.STATUS_SEQUENCE_CREATED == PipelineStatus.READY_FOR_REVIEW
assert ArticleStateManager.STATUS_NO_COMPANY == PipelineStatus.BLOCKED_COMPANY_NOT_FOUND
assert PipelineStatus.READY_FOR_REVIEW in NOTIFICATION_STATUSES
assert PipelineStatus.BLOCKED_NO_EMAIL in NOTIFICATION_STATUSES
assert PipelineStatus.PENDING_MANUAL_REVIEW in REPROCESSABLE_STATUSES
assert 'pending_review' in REPROCESSABLE_STATUSES
# + wszystkie statusy z PipelineStatus mają wpis w STATUS_META
OK — all assertions pass, pipeline_status model is consistent
```

---

## 6. Risks / Limitations

| Ryzyko | Poziom | Uwaga |
|--------|--------|-------|
| Istniejące pliki stanu mają stare wartości | Niski | Backward compat działa — stare statusy są traktowane jako "przetworzone" (nie będą re-procesowane) |
| `sequence_builder.py` używa string literałów zamiast `PipelineStatus.*` | Niski | Wartości są identyczne — ryzyko dryfu tylko przy przyszłych zmianach nazw |
| `BLOCKED_MESSAGE_GENERATION_FAILED` nie jest jeszcze używany | Informacyjny | Status jest zdefiniowany i gotowy do użycia — nie jest jeszcze wpięty w pipeline (generacja nie ma obsługi wyjątku z takim statusem) |
| Brak agregacji statusów w run report | Operacyjny | Nie ma automatycznego podsumowania "X READY, Y BLOCKED, Z REJECTED" po run-daily. Dane są w results[], ale nie ma tabelki |
| `SKIPPED_DUPLICATE` nie jest zapisywany | Informacyjny | Deduplikacja przez `is_article_processed()` działa, ale nie wywołuje `mark_article()` — brak śladu w stanie. To historyczne zachowanie, nie nowy problem. |

---

## 7. Final Recommendation

Model jest **wystarczający i gotowy do użycia produkcyjnego**.

**Co działa teraz:**
- Jeden status na jeden case — spójny między state, results i notyfikacjami
- `final_stage` + `final_reason` zapisane w pliku stanu — diagnostyka bez czytania logów
- Dwie kategorie blokady kontaktowej wyraźnie rozróżnione
- Backward compat z istniejącymi plikami stanu

**Co można zrobić w kolejnych krokach:**
1. Wpiąć `BLOCKED_MESSAGE_GENERATION_FAILED` — obsłużyć wyjątek w `generate_outreach_pack()`
2. Dodać podsumowanie statusów na koniec `run_daily()` (np. `Counter(r["status"] for r in results)`)
3. Zamienić literały w `sequence_builder.py` na `from news.pipeline_status import PipelineStatus`
4. Dodać test E2E, który sprawdza status w pliku stanu po mock-run przez orchestrator
