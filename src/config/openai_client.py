#!/usr/bin/env python3
"""
Centralny klient OpenAI API dla całego środowiska kampanijnego.

Jedyne miejsce, w którym tworzony jest klient OpenAI.
Wszystkie flow kampanijne korzystają z tego modułu.

Konfiguracja przez zmienne środowiskowe:
    OPENAI_API_KEY          — klucz API (wymagany dla provider=openai)
    OPENAI_PRIMARY_MODEL    — model primary (gpt-5.4)
    OPENAI_FALLBACK_MODEL   — model fallback (gpt-5.4-mini)
    OPENAI_CHEAP_MODEL      — model cheap/validation (gpt-5.4-nano)
    OPENAI_REASONING_EFFORT — reasoning effort (low/medium/high)
    LLM_PROVIDER            — "openai" lub "github"
    GITHUB_TOKEN            — token dla GitHub Models
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import openai as _openai_lib
    _openai_available = True
except (ImportError, Exception):
    _openai_lib = None
    _openai_available = False


# ---------------------------------------------------------------------------
# Stałe
# ---------------------------------------------------------------------------

_GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"

# Domyślne modele (jeśli brak zmiennych środowiskowych)
_DEFAULT_PRIMARY_MODEL = "gpt-5.4"
_DEFAULT_FALLBACK_MODEL = "gpt-5.4-mini"
_DEFAULT_CHEAP_MODEL = "gpt-5.4-nano"
_DEFAULT_REASONING_EFFORT = "medium"


# ---------------------------------------------------------------------------
# Odczyt konfiguracji z env
# ---------------------------------------------------------------------------

def get_provider() -> str:
    """Zwraca znormalizowaną nazwę providera."""
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def get_primary_model() -> str:
    """Zwraca primary model (HIGH_QUALITY)."""
    return (
        os.getenv("OPENAI_PRIMARY_MODEL", "").strip()
        or os.getenv("LLM_MODEL", "").strip()
        or _DEFAULT_PRIMARY_MODEL
    )


def get_fallback_model() -> str:
    """Zwraca fallback model (STANDARD)."""
    return os.getenv("OPENAI_FALLBACK_MODEL", "").strip() or _DEFAULT_FALLBACK_MODEL


def get_cheap_model() -> str:
    """Zwraca cheap model (CHEAP_VALIDATION)."""
    return os.getenv("OPENAI_CHEAP_MODEL", "").strip() or _DEFAULT_CHEAP_MODEL


def get_reasoning_effort() -> str:
    """Zwraca reasoning effort (low/medium/high)."""
    return os.getenv("OPENAI_REASONING_EFFORT", "").strip() or _DEFAULT_REASONING_EFFORT


# ---------------------------------------------------------------------------
# Singleton klienta OpenAI
# ---------------------------------------------------------------------------

_client_instance = None


def _build_client():
    """Tworzy klienta OpenAI (lub GitHub Models z kompatybilnym API)."""
    if not _openai_available:
        raise RuntimeError("Pakiet 'openai' nie jest zainstalowany. Uruchom: pip install openai")

    provider = get_provider()

    if provider == "github":
        api_key = os.getenv("GITHUB_TOKEN", "").strip()
        if not api_key:
            raise RuntimeError("Brak GITHUB_TOKEN w zmiennych środowiskowych")
        return _openai_lib.OpenAI(api_key=api_key, base_url=_GITHUB_MODELS_BASE_URL)

    # default: openai
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Brak OPENAI_API_KEY w zmiennych środowiskowych")
    return _openai_lib.OpenAI(api_key=api_key)


def get_client():
    """Zwraca singleton klienta OpenAI. Tworzy go przy pierwszym wywołaniu."""
    global _client_instance
    if _client_instance is None:
        _client_instance = _build_client()
    return _client_instance


def reset_client():
    """Resetuje singleton klienta (np. po zmianie zmiennych środowiskowych w testach)."""
    global _client_instance
    _client_instance = None


def is_available() -> bool:
    """Sprawdza, czy klient LLM jest skonfigurowany i dostępny."""
    if not _openai_available:
        return False
    provider = get_provider()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    if provider == "github":
        return bool(os.getenv("GITHUB_TOKEN", "").strip())
    return False


# ---------------------------------------------------------------------------
# Eksport konfiguracji (do logów i raportów)
# ---------------------------------------------------------------------------

def get_config_summary() -> dict:
    """Zwraca podsumowanie konfiguracji (bez klucza API)."""
    provider = get_provider()
    has_key = False
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        has_key = bool(key)
    elif provider == "github":
        key = os.getenv("GITHUB_TOKEN", "").strip()
        has_key = bool(key)

    return {
        "provider": provider,
        "has_api_key": has_key,
        "primary_model": get_primary_model(),
        "fallback_model": get_fallback_model(),
        "cheap_model": get_cheap_model(),
        "reasoning_effort": get_reasoning_effort(),
        "openai_available": _openai_available,
    }
