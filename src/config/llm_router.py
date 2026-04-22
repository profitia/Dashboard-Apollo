#!/usr/bin/env python3
"""
LLM Router dla całego środowiska kampanijnego.

Obsługuje 3 tier'y zadań:
    HIGH_QUALITY      → OPENAI_PRIMARY_MODEL  (gpt-5.4)
    STANDARD          → OPENAI_FALLBACK_MODEL (gpt-5.4-mini)
    CHEAP_VALIDATION  → OPENAI_CHEAP_MODEL    (gpt-5.4-nano)

Wbudowany fallback: jeśli primary model zwróci błąd → automatycznie fallback model.
Logowanie użycia tokenów (jeśli response zwraca usage).
"""

import json
import logging
import os
import re
import sys

# Ensure project root is in path
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_CONFIG_DIR)
_ROOT_DIR = os.path.dirname(_SRC_DIR)
for _d in (_ROOT_DIR, _SRC_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

try:
    import openai as _openai_lib
except ImportError:
    _openai_lib = None

from src.config.openai_client import (
    get_client,
    get_primary_model,
    get_fallback_model,
    get_cheap_model,
    is_available,
)

logger = logging.getLogger("llm_router")


# ---------------------------------------------------------------------------
# Task tier'y
# ---------------------------------------------------------------------------

class TaskTier:
    HIGH_QUALITY = "HIGH_QUALITY"
    STANDARD = "STANDARD"
    CHEAP_VALIDATION = "CHEAP_VALIDATION"


# Mapowanie tier → funkcja zwracająca model
_TIER_MODEL_GETTERS = {
    TaskTier.HIGH_QUALITY: get_primary_model,
    TaskTier.STANDARD: get_fallback_model,
    TaskTier.CHEAP_VALIDATION: get_cheap_model,
}


def get_model_for_tier(tier: str) -> str:
    """Zwraca nazwę modelu dla danego tier'u."""
    getter = _TIER_MODEL_GETTERS.get(tier)
    if getter:
        return getter()
    return get_primary_model()


def get_fallback_chain(tier: str) -> list[str]:
    """Zwraca łańcuch fallbacków dla danego tier'u."""
    primary = get_model_for_tier(tier)
    fallback = get_fallback_model()
    cheap = get_cheap_model()

    if tier == TaskTier.HIGH_QUALITY:
        return [primary, fallback, cheap]
    elif tier == TaskTier.STANDARD:
        return [primary, cheap]
    else:  # CHEAP_VALIDATION
        return [primary]


# ---------------------------------------------------------------------------
# Token usage logging
# ---------------------------------------------------------------------------

_total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}


def _log_usage(response, model: str, agent_name: str):
    """Loguje użycie tokenów z odpowiedzi API."""
    usage = getattr(response, "usage", None)
    if usage:
        prompt_t = getattr(usage, "prompt_tokens", 0) or 0
        completion_t = getattr(usage, "completion_tokens", 0) or 0
        total_t = getattr(usage, "total_tokens", 0) or 0
        _total_usage["prompt_tokens"] += prompt_t
        _total_usage["completion_tokens"] += completion_t
        _total_usage["total_tokens"] += total_t
        _total_usage["calls"] += 1
        logger.info(
            f"[TOKEN] {agent_name} ({model}): "
            f"prompt={prompt_t}, completion={completion_t}, total={total_t}"
        )


def get_total_usage() -> dict:
    """Zwraca sumaryczne użycie tokenów w bieżącej sesji."""
    return dict(_total_usage)


def reset_usage():
    """Resetuje liczniki użycia tokenów."""
    _total_usage.update({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0})


# ---------------------------------------------------------------------------
# JSON repair (przeniesiony z llm_client.py)
# ---------------------------------------------------------------------------

def _repair_llm_json(s: str) -> str:
    """Naprawia JSON z LLM: trailing \\n padding, obcięte odpowiedzi, dosłowne newlines."""
    # 1. Usuń masywne ciągi \\n (model padding bug)
    s = re.sub(r'(\\n\s*){5,}', r'\\n', s)
    # 2. Zamień dosłowne newline w stringach na \\n
    repaired = ""
    in_string = False
    escape_next = False
    for ch in s:
        if escape_next:
            repaired += ch
            escape_next = False
            continue
        if ch == '\\' and in_string:
            repaired += ch
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            repaired += ch
            continue
        if in_string and ch == '\n':
            repaired += '\\n'
            continue
        if in_string and ch == '\r':
            continue
        repaired += ch
    # 3. Napraw obcięty JSON (finish_reason=length) — domknij strukturę
    stripped = repaired.rstrip()
    if stripped and stripped[-1] != '}':
        if in_string:
            stripped += '"'
        open_braces = stripped.count('{') - stripped.count('}')
        for _ in range(max(0, open_braces)):
            stripped += '}'
    return stripped


# ---------------------------------------------------------------------------
# Główna funkcja routera
# ---------------------------------------------------------------------------

def generate_json(
    agent_name: str,
    prompt_path: str,
    user_payload: dict,
    context_files: dict[str, str] | None = None,
    relevant_context_keys: list[str] | None = None,
    tier: str = TaskTier.HIGH_QUALITY,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1500,
) -> dict | None:
    """
    Wywołuje LLM i zwraca sparsowany JSON z automatycznym fallbackiem.

    Args:
        agent_name: Nazwa agenta (do logów).
        prompt_path: Ścieżka do pliku .md z promptem.
        user_payload: Dict z danymi wejściowymi.
        context_files: Opcjonalne pliki kontekstowe.
        relevant_context_keys: Fragmenty nazw plików do włączenia.
        tier: Tier zadania (HIGH_QUALITY / STANDARD / CHEAP_VALIDATION).
        model: Override modelu (wyłącza tier routing i fallback chain).
        temperature: Temperatura generacji.
        max_tokens: Max tokenów odpowiedzi.

    Returns:
        Sparsowany dict z odpowiedzią LLM (z metadanymi _llm_*),
        lub None jeśli błąd / brak dostępności.
    """
    if not is_available():
        return None

    # Wczytaj prompt
    system_prompt = _load_prompt_file(prompt_path)
    if not system_prompt:
        print(f"  [LLM] UWAGA: Brak pliku promptu {prompt_path} — fallback.")
        return None

    # Dodaj kontekst
    if context_files:
        context_block = _build_context_block(context_files, relevant_context_keys)
        if context_block:
            system_prompt += (
                "\n\n---\n\n"
                "# Kontekst systemu (pliki referencyjne)\n\n"
                + context_block
            )

    # Przygotuj user message
    user_message = json.dumps(user_payload, ensure_ascii=False, indent=2)

    # Zbuduj listę modeli do próbowania
    if model:
        models_to_try = [model]
    else:
        models_to_try = get_fallback_chain(tier)

    client = get_client()
    last_error = None

    for idx, llm_model in enumerate(models_to_try):
        is_fallback = idx > 0
        if is_fallback:
            print(f"  [LLM] {agent_name}: fallback → {llm_model}")
            logger.warning(f"{agent_name}: fallback model → {llm_model} (previous error: {last_error})")

        try:
            response = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            # Log token usage
            _log_usage(response, llm_model, agent_name)

            raw = response.choices[0].message.content
            if not raw:
                print(f"  [LLM] {agent_name}: pusta odpowiedź ({llm_model}) — próbuję dalej.")
                last_error = "empty_response"
                continue

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                repaired = _repair_llm_json(raw)
                try:
                    result = json.loads(repaired)
                except json.JSONDecodeError as e:
                    print(f"  [LLM] {agent_name}: niepoprawny JSON ({llm_model}) — {e}")
                    last_error = f"json_error: {e}"
                    continue

            # Sukces — dodaj metadata
            result["_llm_model_used"] = llm_model
            result["_llm_tier"] = tier
            if is_fallback:
                result["_llm_fallback"] = True
                print(f"  [LLM] {agent_name}: sukces z fallback → {llm_model}")
            return result

        except _openai_lib.RateLimitError:
            print(f"  [LLM] {agent_name}: rate limit ({llm_model})")
            last_error = f"rate_limit:{llm_model}"
            continue
        except _openai_lib.APITimeoutError:
            print(f"  [LLM] {agent_name}: timeout ({llm_model})")
            last_error = f"timeout:{llm_model}"
            continue
        except _openai_lib.APIConnectionError:
            print(f"  [LLM] {agent_name}: brak połączenia ({llm_model})")
            last_error = f"connection_error:{llm_model}"
            continue
        except _openai_lib.AuthenticationError:
            print(f"  [LLM] {agent_name}: błąd autentykacji API — fallback heurystyczny.")
            logger.error(f"{agent_name}: authentication error — aborting LLM call")
            return None
        except Exception as e:
            print(f"  [LLM] {agent_name}: nieoczekiwany błąd ({llm_model}) — {e}")
            last_error = f"error:{llm_model}:{e}"
            continue

    # Wyczerpano wszystkie modele
    logger.error(f"{agent_name}: wyczerpano fallback chain, ostatni błąd: {last_error}")
    print(f"  [LLM] {agent_name}: wyczerpano wszystkie modele. Ostatni błąd: {last_error}")
    return None


# ---------------------------------------------------------------------------
# Helpery (prompt / context) — przeniesione z llm_client.py
# ---------------------------------------------------------------------------

def _load_prompt_file(prompt_path: str) -> str:
    """Wczytuje plik promptu z dysku."""
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _build_context_block(context_files: dict[str, str], relevant_keys: list[str] | None = None) -> str:
    """Buduje blok kontekstowy z plików *.md do systemu promptu."""
    if not context_files:
        return ""

    parts = []
    for name in sorted(context_files.keys()):
        if relevant_keys:
            if not any(k in name for k in relevant_keys):
                continue
        content = context_files[name]
        if len(content) > 2000:
            content = content[:2000] + "\n\n[... skrócono ...]"
        parts.append(f"### {name}\n{content}")

    if not parts:
        return ""
    return "\n\n---\n\n".join(parts)
