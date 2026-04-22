# NOTIFICATION STATUSES REPORT — spendguru_market_news

**Data:** 2026-04-22  
**Wersja:** 1.0  
**Kampania:** spendguru_market_news  
**Status:** WDROŻONE I PRZETESTOWANE

---

## 1. Executive Summary

Wdrożono uspójniony system powiadomień email dla workflow `spendguru_market_news`. System wysyła mail na `tomasz.uscinski@profitia.pl` w dwóch jednoznacznych przypadkach końcowych:

| Status | Znaczenie |
|--------|-----------|
| **READY_FOR_REVIEW** | Flow kompletny — firma, kontakt, email i treści gotowe. Rekord gotowy do review i uruchomienia w Apollo. |
| **BLOCKED_NO_EMAIL** | Flow zatrzymany wyłącznie z powodu braku adresu email — firma i osoba rozpoznane, treści wygenerowane, ale brak emaila. |

**Temat maila** jest identyczny dla obu statusów:
```
Kampania spendguru_market_news czeka na zatwierdzenie
```

**Kluczowe zasady:**
- Brak emaila = notyfikacja, nie cisza
- Obie ścieżki generują pełne treści sekwencji (Step 1-3) i umieszczają je w mailu
- Status jest wyraźnie oznaczony kolorem: 🟢 zielony (READY) / 🔴 czerwony (BLOCKED)
- Draft-only flow niezmieniony — brak auto-enrollmentu, brak zmian w Apollo bez zatwierdzenia

---

## 2. READY_FOR_REVIEW

### Warunki
- ✅ Artykuł znaleziony przez scanner
- ✅ Kwalifikacja pozytywna (score ≥ progi z campaign_config)
- ✅ Firma rozpoznana (entity_extractor + opcjonalny resolver)
- ✅ Co najmniej 1 kontakt z poprawnym adresem email
- ✅ Treści sekwencji wygenerowane (Step 1/2/3)
- ✅ Kontakt dodany do listy Apollo + stage ustawiony

### Zawartość maila
| Sekcja | Zawartość |
|--------|-----------|
| **Status banner** | 🟢 zielony baner — "FLOW GOTOWY DO REVIEW I URUCHOMIENIA W APOLLO" |
| **Artykuł i firma** | Kampania, status, tytuł artykułu, link, firma |
| **Kontakt 1..N** | Tier, imię i nazwisko, email (aktywny), lista Apollo, stage |
| **Sekwencja mailowa** | Step 1 (temat + body), Step 2, Step 3 — wszystkie treści |

### Kiedy jest wysyłany
Po wywołaniu `create_news_sequence()` — gdy kontakty zostały przetworzone przez Apollo (znajdź/utwórz kontakt, dodaj do listy, ustaw stage, zapisz custom fields). Konfiguracja: `send_approval_email: true`.

---

## 3. BLOCKED_NO_EMAIL

### Warunki
- ✅ Artykuł znaleziony
- ✅ Kwalifikacja pozytywna
- ✅ Firma rozpoznana
- ✅ Co najmniej 1 kontakt znaleziony w Apollo (nawet bez emaila)
- ✅ Treści sekwencji wygenerowane (do notyfikacji)
- ❌ Brak adresu email → flow nie domknięty

### Zawartość maila
| Sekcja | Zawartość |
|--------|-----------|
| **Status banner** | 🔴 czerwony baner — "FLOW ZATRZYMANY — BRAK ADRESU EMAIL" |
| **Reason box** | ⚠ Powód zatrzymania: Brak adresu email — kontakt rozpoznany, ale email niedostępny |
| **Artykuł i firma** | Identyczne jak w READY_FOR_REVIEW |
| **Kontakt 1..N** | Tier, imię i nazwisko, **brak adresu email** (czerwony), lista = "—", stage = "—" |
| **Powód zatrzymania** | Wyraźne pole w każdym contact blocku |
| **Sekwencja mailowa** | Step 1/2/3 — wygenerowane treści (mimo braku emaila) |

### Kiedy jest wysyłany
W `orchestrator.py`, gdy `validate_contact_threshold()` zwraca False z powodu braku emaili, ale lista kontaktów jest niepusta. Pipeline:
1. Wykrywa kontakty bez emaila (`contacts_no_email`)
2. Generuje packs dla max 3 kontaktów (bez wysyłki do Apollo)
3. Wywołuje `send_blocked_no_email_notification()`
4. Kontynuuje (artykuł odkładany, Apollo nie jest modyfikowane)

---

## 4. Technical Implementation

### Pliki zmienione

| Plik | Zmiana |
|------|--------|
| **`src/news/apollo/sequence_builder.py`** | Zastąpiono `_build_approval_email_html()` nowym `_build_status_notification_html(status, ...)`. Zaktualizowano `_send_draft_approval_email()` (nowy temat, status param). Dodano `send_blocked_no_email_notification()`. Zaktualizowano `create_news_sequence()` — contact_blocks teraz zawiera step data (step_1_subject/body, step_2..., step_3...). |
| **`src/news/orchestrator.py`** | Import `send_blocked_no_email_notification`. W bloku `validate_contact_threshold` skip: dodano detekcję `contacts_no_email`, generację packed i wywołanie `send_blocked_no_email_notification()`. |
| **`campaigns/news/spendguru_market_news/config/campaign_config.yaml`** | Dodano `send_blocked_email_notification: true`. |
| **`tests/test_news_pipeline_smoke.py`** | Zaktualizowano 2 testy — `_build_approval_email_html` → `_build_status_notification_html`. |
| **`tests/test_notification_statuses.py`** | Nowy skrypt walidacyjny — 10 testów. |

### Funkcje kluczowe

```python
# HTML builder — oba statusy
_build_status_notification_html(
    status: str,           # "READY_FOR_REVIEW" | "BLOCKED_NO_EMAIL"
    article_title: str,
    article_url: str,
    company_name: str,
    contact_blocks: list[dict],  # zawiera step_1/2/3 subject+body
    campaign_name: str = "spendguru_market_news",
    contact_stage: str = "News pipeline - drafted",
) -> str

# Wysyłka — unified subject, status param
_send_draft_approval_email(
    ...,
    status: str = "READY_FOR_REVIEW",
) -> bool

# Public API dla blocked path
send_blocked_no_email_notification(
    article_title, article_url, company_name,
    contacts_with_packs,  # [{contact, pack}]
    campaign_config,
) -> bool
```

### Office365 send — jak działa
`_send_draft_approval_email()` dynamicznie ładuje `send_mail.py` z `Integracja z Office365/` przez `importlib.util.spec_from_file_location`. Używa `send_single(to_email, subject, body_html)` → Microsoft Graph API (`/me/sendMail`). Token cache w `.token_cache.json`.

### Contact blocks — format (rozszerzony)
```python
{
    "first_name": ..., "last_name": ..., "email": ...,
    "tier": ..., "tier_label": ..., "list_name": ...,
    # Nowości:
    "step_1_subject": ..., "step_1_body": ...,
    "step_2_subject": ..., "step_2_body": ...,
    "step_3_subject": ..., "step_3_body": ...,
}
```

---

## 5. Validation

### Smoke tests: 29/29 PASS
```
pytest tests/test_news_pipeline_smoke.py -q
29 passed in 0.20s
```

### Notification tests: 10/10 PASS
```
python tests/test_notification_statuses.py
  ✅ [1] READY_FOR_REVIEW HTML builds OK
  ✅ [2] BLOCKED_NO_EMAIL HTML builds OK
  ✅ [3] Status banners correct colors/text
  ✅ [4] Subject identical: 'Kampania spendguru_market_news czeka na zatwierdzenie'
  ✅ [5] Steps 1-3 present in both email variants
  ✅ [6] Email display correct (READY shows email, BLOCKED shows 'brak')
  ✅ [7] BLOCKED notification respects toggle=false
  ✅ [8] Subject unified for both statuses
  ✅ [9] Article info (title, URL, company) present in both
  ✅ [10] BLOCKED_NO_EMAIL has clear 'Powód zatrzymania' box
  10/10 PASS | 0/10 FAIL
```

### HTML Previews (do inspekcji wizualnej)
Wygenerowane w `outputs/`:
- `_notification_preview_READY.html`
- `_notification_preview_BLOCKED.html`

---

## 6. Risks / Limitations

| Ryzyko | Poziom | Uwaga |
|--------|--------|-------|
| Office365 token cache wygasł | Akceptowalny | `send_single` rzuci wyjątek → log warning, pipeline kontynuuje |
| Brak `approval_email_to` w configu | Niski | Funkcja loguje warning i zwraca False (nie crashuje) |
| Generowanie paku dla kontaktu bez emaila może fail | Niski | Wrapped w try/except; jeśli 0 packed → BLOCKED notification nie jest wysyłana (zamiast pół-pustego maila) |
| `contacts_no_email` = [] bo Apollo zwrócił 0 kontaktów | Informacyjny | Poprawne — BLOCKED wysyłamy tylko gdy rozpoznano osobę. 0 kontaktów = stan "no_company_found", nie BLOCKED |
| Treści step 1-3 mogą być bardzo długie | Niski | Trzy emaile outreach są wklejone do jednego maila powiadamiającego — może być długi. Akceptowalne. |
| BLOCKED mail nie trafia do Apollo | Celowo | Apollo jest czyste — tylko READY_FOR_REVIEW tworzy kontakty/rekordy |

---

## 7. Final Recommendation

Rozwiązanie jest **gotowe do użycia produkcyjnego**.

Nie wymaga żadnych dalszych zmian przed pierwszym uruchomieniem. Toggle `send_blocked_email_notification: true` jest aktywny.

**Co można opcjonalnie dodać później:**
- Liczniki statusów w run report (ile READY, ile BLOCKED w ciągu dnia)
- "Preview" link do HTML wygenerowanego na serwerze (zamiast pełnych treści inline)
- Webhook jako drugi kanał dla BLOCKED (np. Slack alert)
- Limit długości body step 1-3 w mailu (np. pierwsze 2000 znaków z linkiem "rozwiń")
