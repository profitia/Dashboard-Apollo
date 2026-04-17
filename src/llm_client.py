#!/usr/bin/env python3
"""
LLM Client for AI Outreach System.

Obsługuje wywołania OpenAI API ze structured JSON output.
Fallback: jeśli brak klucza API lub błąd — zwraca None, a pipeline
używa heurystyk.
"""

import json
import os
import sys

# --- dotenv ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv opcjonalny — zmienne mogą być w środowisku

# --- openai ---
_openai_available = False
try:
    import openai
    _openai_available = True
except ImportError:
    pass


# GitHub Models endpoint (OpenAI-compatible)
_GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"


def _get_provider() -> str:
    """Zwraca znormalizowaną nazwę providera."""
    return os.getenv("LLM_PROVIDER", "").strip().lower()


def is_llm_available() -> bool:
    """Sprawdza, czy LLM jest skonfigurowany i dostępny."""
    if not _openai_available:
        return False
    provider = _get_provider()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    if provider == "github":
        return bool(os.getenv("GITHUB_TOKEN", "").strip())
    return False


def _build_openai_client():
    """Tworzy klienta OpenAI (lub GitHub Models z kompatybilnym API)."""
    provider = _get_provider()
    if provider == "github":
        api_key = os.getenv("GITHUB_TOKEN", "").strip()
        return openai.OpenAI(api_key=api_key, base_url=_GITHUB_MODELS_BASE_URL)
    # default: openai
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    return openai.OpenAI(api_key=api_key)


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
        # Jeśli podano relevant_keys, filtruj
        if relevant_keys:
            if not any(k in name for k in relevant_keys):
                continue
        content = context_files[name]
        # Ogranicz do ~2000 znaków per plik, żeby zmieścić się w kontekście
        if len(content) > 2000:
            content = content[:2000] + "\n\n[... skrócono ...]"
        parts.append(f"### {name}\n{content}")

    if not parts:
        return ""
    return "\n\n---\n\n".join(parts)


# Domyślna kolejność modeli do fallbacku.
# gpt-4o-mini celowo pominięty — ma bug z JSON padding.
_MODEL_FALLBACK_CHAIN = ["gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"]


def generate_json(
    agent_name: str,
    prompt_path: str,
    user_payload: dict,
    context_files: dict[str, str] | None = None,
    relevant_context_keys: list[str] | None = None,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1500,
) -> dict | None:
    """
    Wywołuje LLM i zwraca sparsowany JSON.
    Obsługuje fallback między modelami przy rate limit / błędach API.

    Args:
        agent_name: Nazwa agenta (do logów).
        prompt_path: Ścieżka do pliku .md z promptem.
        user_payload: Dict z danymi wejściowymi — zostanie przekazany jako user message.
        context_files: Opcjonalne pliki kontekstowe.
        relevant_context_keys: Fragmenty nazw plików do włączenia (np. ["03_messaging", "05_quality"]).
        model: Override modelu LLM (wyłącza fallback chain).
        temperature: Temperatura generacji.
        max_tokens: Max tokenów odpowiedzi.

    Returns:
        Sparsowany dict z odpowiedzią LLM (zawiera klucz _llm_model_used),
        lub None jeśli błąd / brak dostępności.
    """
    if not is_llm_available():
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
        # Explicit override — tylko ten model, bez fallbacku
        models_to_try = [model]
    else:
        primary = os.getenv("LLM_MODEL", "gpt-4o").strip()
        if primary in _MODEL_FALLBACK_CHAIN:
            # Zacznij od primary, potem reszta chain w kolejności
            models_to_try = [primary] + [m for m in _MODEL_FALLBACK_CHAIN if m != primary]
        else:
            models_to_try = [primary] + _MODEL_FALLBACK_CHAIN

    # Napraw typowe problemy z JSON z LLM
    def _repair_llm_json(s: str) -> str:
        """Naprawia JSON z LLM: trailing \\n padding, obcięte odpowiedzi, dosłowne newlines."""
        import re
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

    client = _build_openai_client()
    last_error = None

    for idx, llm_model in enumerate(models_to_try):
        is_fallback = idx > 0
        if is_fallback:
            print(f"  [LLM] {agent_name}: próbuję fallback model → {llm_model}")

        try:
            response = client.chat.completions.create(
                model=llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

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
                    print(f"  [LLM] {agent_name}: niepoprawny JSON ({llm_model}) — {e} — próbuję dalej.")
                    last_error = f"json_error: {e}"
                    continue

            # Sukces — dodaj metadata o użytym modelu
            result["_llm_model_used"] = llm_model
            if is_fallback:
                result["_llm_fallback"] = True
                print(f"  [LLM] {agent_name}: sukces z fallback modelem {llm_model}")
            return result

        except openai.RateLimitError:
            print(f"  [LLM] {agent_name}: rate limit ({llm_model})")
            last_error = f"rate_limit:{llm_model}"
            continue
        except openai.APITimeoutError:
            print(f"  [LLM] {agent_name}: timeout ({llm_model})")
            last_error = f"timeout:{llm_model}"
            continue
        except openai.APIConnectionError:
            print(f"  [LLM] {agent_name}: brak połączenia ({llm_model})")
            last_error = f"connection_error:{llm_model}"
            continue
        except openai.AuthenticationError:
            print(f"  [LLM] {agent_name}: błąd autentykacji API — fallback heurystyczny.")
            return None
        except Exception as e:
            print(f"  [LLM] {agent_name}: nieoczekiwany błąd ({llm_model}) — {e}")
            last_error = f"error:{llm_model}:{e}"
            continue

    # Wszystkie modele zawiodły
    print(f"  [LLM] {agent_name}: wszystkie modele zawiodły (ostatni błąd: {last_error}) — fallback heurystyczny.")
    return None
