# Pipeline Final Statuses — Podsumowanie dla ChatGPT

**Data:** 2026-04-22 | **Kampania:** spendguru_market_news | **Status:** WDROŻONE

---

## Po co powstał ten model

Pipeline nie miał spójnego modelu statusów. Różne warstwy używały różnych stringów dla tego samego case'u:
- state manager: `"article_qualified_but_no_contacts"`
- results dict: `"no_contacts"`
- email notyfikacje: `"BLOCKED_NO_EMAIL"`

Teraz jest jeden `PipelineStatus` — jedyne źródło prawdy, używane we wszystkich warstwach.

---

## 5 najważniejszych wniosków

1. **Jeden plik, jeden model** — `src/news/pipeline_status.py` definiuje wszystkie 14 statusów + metadane. Żadna inna warstwa nie definiuje własnych stringów statusów.

2. **State i results teraz mówią to samo** — przed zmianą `state.mark_article()` i `results.append()` używały różnych wartości. Teraz obydwa używają `PipelineStatus.*` — ten sam string w obu miejscach.

3. **`BLOCKED_NO_CONTACT` vs `BLOCKED_NO_EMAIL` — wyraźne rozróżnienie** — wcześniej obie blokady na kontaktach miały ten sam status. Teraz: brak kontaktów = `BLOCKED_NO_CONTACT`, kontakty bez emaila = `BLOCKED_NO_EMAIL` (+ mail powiadamiający).

4. **`final_stage` + `final_reason` w pliku stanu** — każdy artykuł w `processed_articles.json` ma teraz pole `final_stage` (na którym etapie się zatrzymał) i `final_reason` (dlaczego). Diagnostyka bez czytania logów.

5. **Backward compat z istniejącymi plikami stanu** — artykuły przetworzone przed zmianą nadal są rozpoznawane jako "przetworzone". Stary `"pending_review"` nadal pozwala na re-processing.

---

## Finalna lista statusów

```
SUKCES:
  READY_FOR_REVIEW                  — flow kompletny, mail 🟢 wysłany

ODRZUCONE:
  REJECTED_QUALIFICATION            — artykuł nie przeszedł scoringu

POMINIĘTE (operacyjne):
  SKIPPED_FETCH_FAILED              — błąd pobierania artykułu
  SKIPPED_DUPLICATE                 — artykuł już przetworzony
  SKIPPED_COOLDOWN                  — firma w oknie cooldown
  REVIEW_ONLY                       — tryb review_only, brak zapisu do Apollo

ZABLOKOWANE — firma:
  BLOCKED_COMPANY_NOT_FOUND         — nie wykryto firmy w artykule
  BLOCKED_COMPANY_EXCLUDED          — firma poza ICP
  BLOCKED_COMPANY_NO_MATCH          — resolver: brak dopasowania
  BLOCKED_COMPANY_AMBIGUOUS         — resolver: niejednoznaczny wynik

ZABLOKOWANE — kontakty:
  BLOCKED_NO_CONTACT                — brak kontaktów w Apollo
  BLOCKED_NO_EMAIL                  — kontakty bez emaila, mail 🔴 wysłany

ZABLOKOWANE — techniczne:
  BLOCKED_MESSAGE_GENERATION_FAILED — LLM nie wygenerował treści

REVIEW:
  PENDING_MANUAL_REVIEW             — human_review_gate aktywny
```

---

## Co wysyła mail

| Status | Mail | Kolor |
|--------|------|-------|
| `READY_FOR_REVIEW` | ✅ | 🟢 Zielony |
| `BLOCKED_NO_EMAIL` | ✅ | 🔴 Czerwony |
| Wszystkie pozostałe | ❌ | — |

---

## Ocena czytelności operacyjnej

**Przed:** Patrząc na logi lub pliki stanu, nie było jasne co oznacza `"no_contacts"` — czy zero kontaktów? czy kontakty bez emaila? Mapping między warstwami wymagał znajomości kodu.

**Po:** Każdy case ma `status`, `final_stage` i `final_reason` w pliku stanu. Np.:
```json
{
  "status": "BLOCKED_NO_EMAIL",
  "final_stage": "contact_search",
  "final_reason": "Contacts identified in Apollo but no email address available"
}
```

Pipeline jest teraz znacznie bardziej czytelny operacyjnie. Statusy mówią co się stało, na jakim etapie i dlaczego — bez potrzeby czytania kodu.
