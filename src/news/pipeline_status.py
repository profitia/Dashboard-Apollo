"""
Pipeline Final Status — jednolity model statusów końcowych.

Jeden status na jeden case przetwarzany przez pipeline.
Używany przez:
  - orchestrator.py   (results dict + state.mark_article)
  - state_manager.py  (stałe stanów — aliasy)
  - sequence_builder.py (statusy notyfikacji mailowych)

Kategorie:
  success    — flow kompletny
  rejected   — artykuł odrzucony na etapie kwalifikacji
  skipped    — case pominięty z przyczyn operacyjnych (dup, cooldown)
  blocked    — firma lub kontakty nie spełniają warunków
  review     — case wymaga działania manualnego

Dla każdego statusu dostępne metadane w STATUS_META:
  - description       — opis po polsku
  - stage             — etap pipeline'u, na którym status został nadany
  - sends_notification — czy wysyła mail do approval_email_to
  - requires_review   — czy wymaga manualnego przeglądu
  - retryable         — czy można ponowić przy zmianie danych
  - category          — kategoria (success/rejected/skipped/blocked/review)
"""
from __future__ import annotations


class PipelineStatus:
    """Stałe końcowych statusów pipeline'u. Jeden status na jeden case."""

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    """Flow kompletny — sekwencja draftu gotowa, mail do review wysłany."""

    # --------------------------------------------------------
    # REJECTED — artykuł odrzucony, nie spełnia kryteriów
    # --------------------------------------------------------
    REJECTED_QUALIFICATION = "REJECTED_QUALIFICATION"
    """Artykuł nie spełnił kryteriów kwalifikacji (score, tagi, czas)."""

    # --------------------------------------------------------
    # SKIPPED — case pominięty z przyczyn operacyjnych
    # --------------------------------------------------------
    SKIPPED_FETCH_FAILED = "SKIPPED_FETCH_FAILED"
    """Nie udało się pobrać artykułu — błąd HTTP/parser."""

    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
    """Artykuł już przetworzony — pominięty przez state manager."""

    SKIPPED_COOLDOWN = "SKIPPED_COOLDOWN"
    """Firma w oknie cooldown — sekwencja już istnieje dla tej firmy."""

    REVIEW_ONLY = "REVIEW_ONLY"
    """Tryb review_only — treści wygenerowane, sekwencja nie zapisana do Apollo."""

    # --------------------------------------------------------
    # BLOCKED — firma nie spełnia warunków
    # --------------------------------------------------------
    BLOCKED_COMPANY_NOT_FOUND = "BLOCKED_COMPANY_NOT_FOUND"
    """Nie wykryto firmy w artykule — entity extractor nie zwrócił wyniku."""

    BLOCKED_COMPANY_EXCLUDED = "BLOCKED_COMPANY_EXCLUDED"
    """Firma wykluczona z outreach — nie spełnia kryteriów ICP/eligibility."""

    BLOCKED_COMPANY_NO_MATCH = "BLOCKED_COMPANY_NO_MATCH"
    """Company resolver: brak dopasowania firmy w Apollo."""

    BLOCKED_COMPANY_AMBIGUOUS = "BLOCKED_COMPANY_AMBIGUOUS"
    """Company resolver: niejednoznaczny wynik — wiele kandydatów, wymaga przeglądu."""

    # --------------------------------------------------------
    # BLOCKED — kontakty nie spełniają warunków
    # --------------------------------------------------------
    BLOCKED_NO_CONTACT = "BLOCKED_NO_CONTACT"
    """Brak kontaktów dla firmy w Apollo — osoba niepowiązana z żadnym kontem."""

    BLOCKED_NO_EMAIL = "BLOCKED_NO_EMAIL"
    """Kontakty znalezione w Apollo, ale brak adresu email — powiadomienie wysłane."""

    # --------------------------------------------------------
    # BLOCKED — błąd techniczny / operacyjny
    # --------------------------------------------------------
    BLOCKED_MESSAGE_GENERATION_FAILED = "BLOCKED_MESSAGE_GENERATION_FAILED"
    """Generowanie treści LLM nie powiodło się — błąd modelu lub timeout."""

    # --------------------------------------------------------
    # REVIEW — case czeka na działanie manualne
    # --------------------------------------------------------
    PENDING_MANUAL_REVIEW = "PENDING_MANUAL_REVIEW"
    """Human review gate aktywny — case czeka na ręczne zatwierdzenie."""


# ---------------------------------------------------------------------------
# Status metadata — właściwości każdego statusu
# ---------------------------------------------------------------------------

STATUS_META: dict[str, dict] = {
    PipelineStatus.READY_FOR_REVIEW: {
        "description": "Flow kompletny — sekwencja gotowa do review i uruchomienia w Apollo",
        "stage": "apollo_write",
        "sends_notification": True,
        "requires_review": True,
        "retryable": False,
        "category": "success",
    },
    PipelineStatus.REJECTED_QUALIFICATION: {
        "description": "Artykuł nie spełnił kryteriów kwalifikacji (score, tagi, czas)",
        "stage": "qualification",
        "sends_notification": False,
        "requires_review": False,
        "retryable": False,
        "category": "rejected",
    },
    PipelineStatus.SKIPPED_FETCH_FAILED: {
        "description": "Nie udało się pobrać artykułu — błąd HTTP lub parser",
        "stage": "fetch",
        "sends_notification": False,
        "requires_review": False,
        "retryable": True,
        "category": "skipped",
    },
    PipelineStatus.SKIPPED_DUPLICATE: {
        "description": "Artykuł już przetworzony — pominięty przez state manager",
        "stage": "dedup",
        "sends_notification": False,
        "requires_review": False,
        "retryable": False,
        "category": "skipped",
    },
    PipelineStatus.SKIPPED_COOLDOWN: {
        "description": "Firma w oknie cooldown — sekwencja dla tej firmy już istnieje",
        "stage": "dedup",
        "sends_notification": False,
        "requires_review": False,
        "retryable": False,
        "category": "skipped",
    },
    PipelineStatus.REVIEW_ONLY: {
        "description": "Tryb review_only — treści wygenerowane, sekwencja nie zapisana",
        "stage": "review",
        "sends_notification": False,
        "requires_review": True,
        "retryable": True,
        "category": "review",
    },
    PipelineStatus.BLOCKED_COMPANY_NOT_FOUND: {
        "description": "Nie wykryto firmy w artykule — entity extractor bez wyniku",
        "stage": "entity_extraction",
        "sends_notification": False,
        "requires_review": False,
        "retryable": False,
        "category": "blocked",
    },
    PipelineStatus.BLOCKED_COMPANY_EXCLUDED: {
        "description": "Firma wykluczona z outreach — nie spełnia kryteriów ICP",
        "stage": "entity_extraction",
        "sends_notification": False,
        "requires_review": False,
        "retryable": False,
        "category": "blocked",
    },
    PipelineStatus.BLOCKED_COMPANY_NO_MATCH: {
        "description": "Company resolver: brak dopasowania w Apollo dla tej firmy",
        "stage": "company_resolution",
        "sends_notification": False,
        "requires_review": False,
        "retryable": False,
        "category": "blocked",
    },
    PipelineStatus.BLOCKED_COMPANY_AMBIGUOUS: {
        "description": "Company resolver: niejednoznaczny wynik — wymaga przeglądu manualnego",
        "stage": "company_resolution",
        "sends_notification": False,
        "requires_review": True,
        "retryable": False,
        "category": "blocked",
    },
    PipelineStatus.BLOCKED_NO_CONTACT: {
        "description": "Brak kontaktów dla firmy w Apollo — firma nierozpoznana lub brak rekordów",
        "stage": "contact_search",
        "sends_notification": False,
        "requires_review": False,
        "retryable": True,
        "category": "blocked",
    },
    PipelineStatus.BLOCKED_NO_EMAIL: {
        "description": "Kontakty znalezione i dodane do listy Apollo — próba email reveal nieudana — powiadomienie BLOCKED wysłane",
        "stage": "email_reveal",
        "sends_notification": True,
        "requires_review": True,
        "retryable": True,
        "category": "blocked",
    },
    PipelineStatus.BLOCKED_MESSAGE_GENERATION_FAILED: {
        "description": "Generowanie treści LLM nie powiodło się",
        "stage": "message_generation",
        "sends_notification": False,
        "requires_review": False,
        "retryable": True,
        "category": "blocked",
    },
    PipelineStatus.PENDING_MANUAL_REVIEW: {
        "description": "Human review gate aktywny — case czeka na zatwierdzenie ręczne",
        "stage": "review_gate",
        "sends_notification": False,
        "requires_review": True,
        "retryable": True,
        "category": "review",
    },
}

# Statusy, które NIE blokują ponownego przetworzenia artykułu
# (pipeline może ponowić te case'y przy kolejnym uruchomieniu)
REPROCESSABLE_STATUSES: frozenset[str] = frozenset({
    PipelineStatus.PENDING_MANUAL_REVIEW,
    # Backward compat z poprzednim modelem:
    "pending_review",
})

# Statusy, które wysyłają powiadomienie email
NOTIFICATION_STATUSES: frozenset[str] = frozenset(
    s for s, meta in STATUS_META.items() if meta["sends_notification"]
)

# Statusy wymagające przeglądu manualnego
REVIEW_REQUIRED_STATUSES: frozenset[str] = frozenset(
    s for s, meta in STATUS_META.items() if meta["requires_review"]
)

# Statusy retryable (można ponowić)
RETRYABLE_STATUSES: frozenset[str] = frozenset(
    s for s, meta in STATUS_META.items() if meta["retryable"]
)


def get_meta(status: str) -> dict:
    """Zwraca metadane statusu. Jeśli nieznany — zwraca pusty dict."""
    return STATUS_META.get(status, {})
