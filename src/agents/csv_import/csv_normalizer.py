#!/usr/bin/env python3
"""
CSV Normalizer — moduł normalizacji danych kontaktowych z importu CSV.

Jawne mapowanie kolumn, rozdzielanie Name, inferencja płci,
wyznaczanie wołacza polskiego. Logika deterministyczna (bez LLM).

v2: Rozszerzony o rich_contact_profile — buduje pełny profil wiedzy o odbiorcy,
nie tylko minimalny rekord mailingowy.
"""

import json
import os
import re
import sys
from typing import Any

# Dodaj src/ do path żeby zaimportować core
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from core.polish_names import get_polish_name_data as _csv_lookup, resolve_polish_contact
from core.rich_contact_profile import (
    build_rich_profile,
    flatten_to_normalized_contact,
    build_llm_context,
    save_or_merge_rich_profile,
)


# ============================================================
# Ścieżka do pliku reguł imion (legacy fallback)
# ============================================================

# csv_normalizer.py is at: src/agents/csv_import/csv_normalizer.py
# Project root is 4 dirs up: csv_import → agents → src → project_root
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_RULES_PATH = os.path.join(_BASE_DIR, "data", "reference", "pl_first_name_rules.json")

_name_rules: dict | None = None


def _load_name_rules() -> dict:
    """Ładuje reguły imion z pliku JSON — legacy fallback (lazy, raz)."""
    global _name_rules
    if _name_rules is not None:
        return _name_rules
    if os.path.exists(_RULES_PATH):
        with open(_RULES_PATH, "r", encoding="utf-8") as f:
            _name_rules = json.load(f)
    else:
        _name_rules = {
            "female_names": [],
            "male_names": [],
            "male_names_ending_a": [],
            "vocative_exceptions": {},
        }
    return _name_rules


# ============================================================
# Mapowanie kolumn CSV → pola wewnętrzne
# ============================================================

# Klucze: warianty nazw kolumn (lowercase), wartości: docelowa nazwa pola
COLUMN_MAP: dict[str, str] = {
    # Name (full)
    "name": "full_name",
    "full name": "full_name",
    "full_name": "full_name",
    "contact name": "full_name",
    "contact_name": "full_name",
    # First name (jeśli już rozdzielone)
    "first name": "first_name",
    "first_name": "first_name",
    "contact_first_name": "first_name",
    # Last name (jeśli już rozdzielone)
    "last name": "last_name",
    "last_name": "last_name",
    "contact_last_name": "last_name",
    # Company
    "company": "company_name",
    "company name": "company_name",
    "company_name": "company_name",
    # Domain
    "domain": "company_domain",
    "company domain": "company_domain",
    "company_domain": "company_domain",
    # Country
    "country": "country",
    # Industry
    "industry": "industry",
    # Job title
    "job role": "job_title",
    "job_role": "job_title",
    "job title": "job_title",
    "job_title": "job_title",
    "title": "job_title",
    "contact_title": "job_title",
    "role": "job_title",
    "position": "job_title",
    # Notes
    "notes": "notes",
    "note": "notes",
    "comment": "notes",
    "comments": "notes",
}


def map_columns(row: dict) -> dict:
    """Mapuje kolumny CSV na pola wewnętrzne. Zwraca znormalizowany dict."""
    mapped: dict[str, str] = {
        "full_name": "",
        "first_name": "",
        "last_name": "",
        "company_name": "",
        "company_domain": "",
        "country": "",
        "industry": "",
        "job_title": "",
        "notes": "",
    }

    for csv_col, value in row.items():
        key = csv_col.strip().lower()
        if key in COLUMN_MAP:
            target = COLUMN_MAP[key]
            val = value.strip() if value else ""
            # Nie nadpisuj jeśli już ustawione (first_name ma priorytet nad full_name)
            if target in ("first_name", "last_name") and val:
                mapped[target] = val
            elif not mapped.get(target):
                mapped[target] = val

    return mapped


# ============================================================
# Rozdzielanie Name → first_name + last_name
# ============================================================

def split_name(full_name: str) -> tuple[str, str, list[str]]:
    """
    Rozdziela pełną nazwę na (first_name, last_name, warnings).
    Zakłada: pierwsza część = imię, reszta = nazwisko.
    """
    warnings: list[str] = []

    if not full_name or not full_name.strip():
        return "", "", ["Name is empty — cannot split"]

    parts = full_name.strip().split()

    if len(parts) == 1:
        warnings.append(f"Name '{full_name}' has only one part — treating as first_name, last_name empty")
        return parts[0], "", warnings

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    if len(parts) > 3:
        warnings.append(f"Name '{full_name}' has {len(parts)} parts — split may be imprecise")

    return first_name, last_name, warnings


# ============================================================
# Inferencja płci
# ============================================================

def infer_gender(first_name: str) -> str:
    """
    Inferencja płci na podstawie imienia.
    Priorytet: 1) CSV (context/Vocative names od VSC.csv), 2) legacy fallback.
    Zwraca: 'female', 'male', 'unknown'.
    """
    if not first_name or not first_name.strip():
        return "unknown"

    # 1. CSV — źródło prawdy
    csv_data = _csv_lookup(first_name)
    if csv_data:
        return csv_data["gender"]

    # 2. Fallback: bezpieczny unknown (nie zgadujemy)
    return "unknown"


# ============================================================
# Wołacz (vocative case)
# ============================================================

def get_vocative(first_name: str) -> str | None:
    """
    Zwraca wołacz polskiego imienia lub None jeśli nieznany.
    Priorytet: 1) CSV (context/Vocative names od VSC.csv), 2) None (bezpieczny fallback).
    """
    if not first_name or not first_name.strip():
        return None

    # 1. CSV — źródło prawdy
    csv_data = _csv_lookup(first_name)
    if csv_data:
        return csv_data["vocative"]

    # 2. Fallback: None (bezpieczny — nie zgadujemy wołacza)
    return None


# ============================================================
# Greeting builder
# ============================================================

def build_greeting(gender: str, first_name_vocative: str | None) -> str:
    """Buduje powitanie na podstawie płci i wołacza. Deleguje do shared helper."""
    from core.polish_names import build_greeting as _shared_build_greeting
    return _shared_build_greeting(gender, first_name_vocative)


# ============================================================
# Pełna normalizacja jednego rekordu
# ============================================================

def normalize_contact(row: dict) -> dict:
    """
    Normalizuje jeden rekord CSV. Zwraca znormalizowany dict z polami:
    full_name, first_name, last_name, first_name_vocative, gender,
    job_title, company_name, company_domain, country, industry, notes,
    greeting, normalization_warnings.
    """
    warnings: list[str] = []

    # 1. Mapuj kolumny
    mapped = map_columns(row)

    # 2. Rozdziel Name jeśli first_name/last_name puste
    if mapped["full_name"] and not mapped["first_name"] and not mapped["last_name"]:
        fn, ln, split_warnings = split_name(mapped["full_name"])
        mapped["first_name"] = fn
        mapped["last_name"] = ln
        warnings.extend(split_warnings)
    elif not mapped["full_name"] and mapped["first_name"]:
        # first_name + last_name podane osobno
        mapped["full_name"] = f"{mapped['first_name']} {mapped['last_name']}".strip()
    elif not mapped["full_name"] and not mapped["first_name"]:
        warnings.append("No name data found in record")

    # 3. Inferencja płci
    gender = infer_gender(mapped["first_name"])
    if gender == "unknown" and mapped["first_name"]:
        warnings.append(f"Could not determine gender for '{mapped['first_name']}'")

    # 4. Wołacz
    vocative = get_vocative(mapped["first_name"])
    if vocative is None and mapped["first_name"]:
        warnings.append(f"Could not determine vocative for '{mapped['first_name']}' — will use neutral greeting")

    # 5. Greeting
    greeting = build_greeting(gender, vocative)

    # 6. Walidacja
    if not mapped["company_name"]:
        warnings.append("Missing company_name")
    if not mapped["job_title"]:
        warnings.append("Missing job_title")
    if not mapped["country"]:
        warnings.append("Missing country")

    return {
        "full_name": mapped["full_name"],
        "first_name": mapped["first_name"] or None,
        "last_name": mapped["last_name"] or None,
        "first_name_vocative": vocative,
        "gender": gender,
        "greeting": greeting,
        "job_title": mapped["job_title"],
        "company_name": mapped["company_name"],
        "company_domain": mapped["company_domain"],
        "country": mapped["country"].upper() if mapped["country"] else "",
        "industry": mapped["industry"],
        "notes": mapped["notes"],
        "normalization_warnings": warnings,
    }


def normalize_contacts(rows: list[dict]) -> list[dict]:
    """Normalizuje listę rekordów CSV."""
    return [normalize_contact(row) for row in rows]


# ============================================================
# Rich profile normalization (v2)
# ============================================================

def normalize_contact_rich(row: dict, persist: bool = True) -> dict:
    """
    Normalizuje jeden rekord CSV do rozszerzonego profilu kontaktu.

    1. Buduje rich_profile z pełnym zestawem pól (core_identity, org_context, urls, location, ...)
    2. Rozwiązuje gender/vocative z polskiego źródła imion
    3. Spłaszcza do backward-compatible formatu (z rich_profile jako nested field)
    4. Opcjonalnie zapisuje/merguje do trwałego storage

    Args:
        row: surowy rekord CSV
        persist: czy zapisać/zmergować profil do storage (domyślnie True)

    Returns:
        Backward-compatible normalized contact dict z dodatkowymi polami
        i zagnieżdżonym rich_profile.
    """
    # 1. Build rich profile
    rich = build_rich_profile(row)
    first_name = rich["core_identity"].get("first_name") or ""

    # 2. Gender / vocative
    gender_data = {}
    if first_name:
        csv_data = _csv_lookup(first_name)
        if csv_data:
            gender_data["gender"] = csv_data["gender"]
            gender_data["vocative"] = csv_data["vocative"]
            gender_data["greeting"] = build_greeting(csv_data["gender"], csv_data["vocative"])
        else:
            gender_data["gender"] = "unknown"
            gender_data["vocative"] = None
            gender_data["greeting"] = build_greeting("unknown", None)
            rich["normalization_warnings"].append(
                f"Could not determine gender/vocative for '{first_name}'"
            )
    else:
        gender_data["gender"] = "unknown"
        gender_data["vocative"] = None
        gender_data["greeting"] = build_greeting("unknown", None)

    # 3. Flatten to backward-compatible format
    normalized = flatten_to_normalized_contact(rich, gender_data)
    # Preserve notes from the original normalize_contact output
    mapped_notes = ""
    for csv_col, value in row.items():
        key = csv_col.strip().lower()
        if key in ("notes", "note", "comment", "comments"):
            mapped_notes = (value or "").strip()
            break
    normalized["notes"] = mapped_notes

    # 4. Persist
    if persist:
        try:
            save_or_merge_rich_profile(rich)
        except Exception as exc:
            rich["normalization_warnings"].append(f"Profile save failed: {exc}")

    return normalized


def normalize_contacts_rich(rows: list[dict], persist: bool = True) -> list[dict]:
    """Normalizuje listę rekordów CSV do rozszerzonych profili."""
    return [normalize_contact_rich(row, persist=persist) for row in rows]
