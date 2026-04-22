# Notification Statuses — Podsumowanie dla ChatGPT

**Data:** 2026-04-22 | **Kampania:** spendguru_market_news | **Status:** WDROŻONE

---

## 5 najważniejszych wniosków

1. **Dwa statusy, jeden temat** — zarówno READY_FOR_REVIEW jak i BLOCKED_NO_EMAIL używają identycznego tematu maila: "Kampania spendguru_market_news czeka na zatwierdzenie". Różnica jest tylko w treści i kolorze.

2. **Brak emaila = notyfikacja, nie cisza** — poprzednio pipeline po prostu pomijał artykuł bez powiadomienia gdy brakowało emaila. Teraz użytkownik zawsze wie, że coś się wydarzyło.

3. **Treści sekwencji są w mailu zawsze** — zarówno READY jak i BLOCKED zawierają pełne Step 1/2/3 (temat + body każdego emaila), wygenerowane przez LLM. Użytkownik może przejrzeć jakość treści nawet jeśli flow się zatrzymał.

4. **Apollo jest modyfikowane tylko w READY_FOR_REVIEW** — BLOCKED path generuje treści wyłącznie do notyfikacji. Żadne dane nie są zapisywane do Apollo (brak tworzenia kontaktu, brak listy, brak stage).

5. **Toggle bezpieczeństwa** — `send_blocked_email_notification: true/false` w campaign_config pozwala wyłączyć notyfikację BLOCKED bez zmiany kodu.

---

## READY_FOR_REVIEW

**Kiedy:** Kontakt znaleziony z emailem, treści wygenerowane, dane zapisane do Apollo.

**Baner:**
```
🟢 FLOW GOTOWY DO REVIEW I URUCHOMIENIA W APOLLO
```
(zielone tło `#d4edda`, zielona ramka `#28a745`)

**Co jest w mailu:**
- Kampania, status "Gotowy do review", artykuł (tytuł + link), firma
- Kontakt: tier, imię i nazwisko, **aktualny email**, lista Apollo, stage Apollo
- Sekwencja mailowa: Step 1 (temat + body), Step 2, Step 3
- Brak "Powód zatrzymania" — flow kompletny

---

## BLOCKED_NO_EMAIL

**Kiedy:** Kontakt znaleziony w Apollo ale bez emaila. Pipeline zatrzymuje się, treści są generowane tylko do powiadomienia.

**Baner:**
```
🔴 FLOW ZATRZYMANY — BRAK ADRESU EMAIL
```
(czerwone tło `#f8d7da`, czerwona ramka `#dc3545`)

**Co jest w mailu:**
- Identyczna struktura jak READY — artykuł, firma, kontakt, sekwencja Step 1-3
- Kontakt: email = **"brak adresu email"** (czerwony tekst)
- **⚠ Reason box** — "Powód zatrzymania: Brak adresu email — kontakt rozpoznany w Apollo, ale adres e-mail nie jest dostępny"
- Pole "Powód zatrzymania" w sekcji kontaktu

---

## Co dokładnie trafia do maila

Oba warianty zawierają:

| Element | READY_FOR_REVIEW | BLOCKED_NO_EMAIL |
|---------|-----------------|-----------------|
| Tytuł artykułu | ✅ | ✅ |
| Link do artykułu | ✅ | ✅ |
| Nazwa firmy | ✅ | ✅ |
| Tier kontaktu | ✅ | ✅ |
| Imię i nazwisko | ✅ | ✅ |
| Adres email | ✅ (rzeczywisty) | ❌ (czerwone "brak") |
| Lista Apollo | ✅ | ➖ (brak — nie dodano) |
| Stage Apollo | ✅ | ➖ (brak — nie ustawiono) |
| Step 1 temat+body | ✅ | ✅ |
| Step 2 temat+body | ✅ | ✅ |
| Step 3 temat+body | ✅ | ✅ |
| Powód zatrzymania | ➖ | ✅ |
| Status banner zielony | ✅ | ➖ |
| Status banner czerwony | ➖ | ✅ |

---

## Czy rozwiązanie działa sensownie?

**TAK.** Spełnia wymagania biznesowe:
- Pipeline nigdy nie milczy po wartościowej pracy
- Oba statusy są natychmiast czytelne wizualnie (kolor + emoji)
- Treści sekwencji są dostępne do przejrzenia w każdym przypadku
- Apollo nie jest modyfikowane bez emaila (czyste dane)
- Backward compatible — draft-only flow niezmieniony

**Jedyne ograniczenie:** Emaile Apollo są zablokowane za Apollo credits (Evra Fish, Grycan) — to ograniczenie konta, nie kodu. BLOCKED_NO_EMAIL mail będzie wysyłany dla tych firm.
