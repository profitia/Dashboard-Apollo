#!/usr/bin/env python3
"""
LLM Client for AI Outreach System.

BACKWARD-COMPATIBLE WRAPPER — deleguje do centralnego llm_router.
Wszystkie nowe flow powinny importować bezpośrednio z:
    from src.config.llm_router import generate_json, TaskTier
    from src.config.openai_client import is_available
"""

import os
import sys

# Upewnij się, że src/ i root projektu są w path
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SRC_DIR)
for _d in (_SRC_DIR, _ROOT_DIR):
    if _d not in sys.path:
        sys.path.insert(0, _d)

# --- Centralny import ---
from src.config.openai_client import is_available as _is_available, get_config_summary
from src.config.llm_router import (
    generate_json as _router_generate_json,
    TaskTier,
    get_total_usage,
)


def is_llm_available() -> bool:
    """Backward-compatible: sprawdza czy LLM jest dostępny."""
    return _is_available()


def generate_json(
    agent_name: str = None,
    prompt_path: str = None,
    user_payload: dict = None,
    context_files: dict[str, str] | None = None,
    relevant_context_keys: list[str] | None = None,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1500,
    tier: str = TaskTier.HIGH_QUALITY,
    # --- OLD SIGNATURE (legacy callers: entity_extractor, message_generator) ---
    prompt: str | None = None,
    system_prompt: str | None = None,
) -> dict | None:
    """
    Backward-compatible wrapper — deleguje do centralnego llm_router.

    Obsługuje dwa sygnatury:
      NOWA: generate_json(agent_name, prompt_path, user_payload, ...)
      STARA (legacy): generate_json(prompt=..., system_prompt=..., temperature=..., max_tokens=...)
    """
    # --- LEGACY PATH: stara sygnatura z raw prompt / system_prompt ---
    if prompt is not None:
        import json as _json
        import re as _re
        from src.config.openai_client import get_client, get_fallback_model, is_available
        if not is_available():
            return None
        client = get_client()
        _model = model or get_fallback_model()
        _sys = system_prompt or "Odpowiedz w JSON."
        try:
            response = client.chat.completions.create(
                model=_model,
                messages=[
                    {"role": "system", "content": _sys},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            try:
                return _json.loads(raw)
            except _json.JSONDecodeError:
                from src.config.llm_router import _repair_llm_json
                return _json.loads(_repair_llm_json(raw))
        except Exception as e:
            print(f"  [LLM] legacy generate_json: błąd — {e}")
            return None

    # --- NEW PATH: deleguje do centralnego llm_router ---
    return _router_generate_json(
        agent_name=agent_name,
        prompt_path=prompt_path,
        user_payload=user_payload or {},
        context_files=context_files,
        relevant_context_keys=relevant_context_keys,
        tier=tier,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
