#!/usr/bin/env python3
"""
Contact Campaign History — zarządzanie historią kampanii per kontakt.

Jeden kontakt może otrzymać wiele kampanii.
Moduł zapewnia:
- last_campaign_* — pola bieżące (ostatnia kampania)
- campaign_history — pełna lista kampanii per kontakt
- Ochrona przed duplikatami
- Aktualizację pól operacyjnych

Storage: JSON per run / wewnętrzna baza. Apollo dostaje tylko last_campaign_*.
"""

import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

# ============================================================
# Ścieżka do lokalnego storage historii kampanii
# ============================================================

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HISTORY_DIR = os.path.join(_ROOT_DIR, "data", "campaign_history")


def _ensure_history_dir():
    os.makedirs(_HISTORY_DIR, exist_ok=True)


def _contact_key(contact: dict) -> str:
    """Generuje unikalny klucz kontaktu (email lub first+last+company)."""
    email = contact.get("email", "").strip().lower()
    if email:
        return email
    first = contact.get("first_name", "").strip().lower()
    last = contact.get("last_name", "").strip().lower()
    company = contact.get("company", "").strip().lower()
    return f"{first}_{last}_{company}"


def _history_path(contact_key: str) -> str:
    """Ścieżka do pliku historii kontaktu."""
    # Sanitize key for filesystem
    safe_key = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in contact_key)
    return os.path.join(_HISTORY_DIR, f"{safe_key}.json")


# ============================================================
# Load / Save
# ============================================================

def load_contact_history(contact: dict) -> dict:
    """
    Wczytuje historię kampanii kontaktu.

    Returns:
        dict z polami:
        - contact_key
        - last_campaign_name
        - last_campaign_sent_at
        - last_campaign_type
        - last_campaign_tier
        - last_campaign_segment
        - last_campaign_angle
        - last_apollo_sequence_name
        - campaign_history: list[dict]
    """
    _ensure_history_dir()
    key = _contact_key(contact)
    path = _history_path(key)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "contact_key": key,
        "last_campaign_name": None,
        "last_campaign_sent_at": None,
        "last_campaign_type": None,
        "last_campaign_tier": None,
        "last_campaign_segment": None,
        "last_campaign_angle": None,
        "last_apollo_sequence_name": None,
        "campaign_history": [],
    }


def save_contact_history(history: dict):
    """Zapisuje historię kampanii kontaktu."""
    _ensure_history_dir()
    key = history.get("contact_key", "unknown")
    path = _history_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ============================================================
# Update
# ============================================================

def update_contact_campaign_history(
    contact: dict,
    campaign_metadata: dict,
    apollo_metadata: dict | None = None,
) -> dict:
    """
    Dodaje nową kampanię do historii kontaktu.

    Zasady:
    - Nie nadpisuje poprzednich wpisów
    - Jeśli kampania o tej samej nazwie już istnieje — nie duplikuje, oznacza duplicate_prevented
    - Aktualizuje last_campaign_* na najnowszą kampanię

    Args:
        contact: dane kontaktu (min. first_name, last_name, company)
        campaign_metadata: wynik z build_campaign_metadata()
        apollo_metadata: wynik z create_or_find_sequence() (opcjonalny)

    Returns:
        Zaktualizowana historia kontaktu (dict).
    """
    history = load_contact_history(contact)
    campaign_name = campaign_metadata.get("campaign_name", "")
    now = datetime.now().isoformat()

    # Sprawdź duplikat
    existing_names = [e.get("campaign_name") for e in history.get("campaign_history", [])]
    if campaign_name in existing_names:
        log.info("Duplikat kampanii '%s' dla kontaktu '%s' — pomijam.",
                 campaign_name, history["contact_key"])
        # Zaktualizuj timestamp na istniejącym wpisie
        for entry in history["campaign_history"]:
            if entry.get("campaign_name") == campaign_name:
                entry["last_seen_at"] = now
                entry["duplicate_prevented"] = True
                break
        save_contact_history(history)
        return history

    # Nowy wpis
    entry = {
        "campaign_name": campaign_name,
        "sent_at": now,
        "campaign_type": campaign_metadata.get("campaign_type", ""),
        "tier": campaign_metadata.get("tier", ""),
        "segment": campaign_metadata.get("segment", ""),
        "angle": campaign_metadata.get("angle", ""),
        "market": campaign_metadata.get("market", ""),
        "version": campaign_metadata.get("version", 1),
        "apollo_sequence_name": None,
        "status": "assigned",
    }

    if apollo_metadata:
        entry["apollo_sequence_name"] = apollo_metadata.get("apollo_sequence_name")
        entry["apollo_sync_status"] = apollo_metadata.get("apollo_sync_status", "")

    history["campaign_history"].append(entry)

    # Aktualizuj last_campaign_*
    history["last_campaign_name"] = campaign_name
    history["last_campaign_sent_at"] = now
    history["last_campaign_type"] = campaign_metadata.get("campaign_type", "")
    history["last_campaign_tier"] = campaign_metadata.get("tier", "")
    history["last_campaign_segment"] = campaign_metadata.get("segment", "")
    history["last_campaign_angle"] = campaign_metadata.get("angle", "")
    if apollo_metadata:
        history["last_apollo_sequence_name"] = apollo_metadata.get("apollo_sequence_name")

    save_contact_history(history)
    log.info("Kampania '%s' dodana do historii kontaktu '%s' (total: %d)",
             campaign_name, history["contact_key"], len(history["campaign_history"]))

    return history


# ============================================================
# Enrichment — dodaje pola kampanijne do outputu kontaktu
# ============================================================

def enrich_contact_output(contact: dict, campaign_metadata: dict,
                          apollo_metadata: dict | None = None) -> dict:
    """
    Zwraca pola kampanijne gotowe do dołączenia do outputu kontaktu.

    Returns:
        dict z polami: campaign_name, apollo_sequence_name, campaign_metadata,
        last_campaign_name, campaign_history_count, has_previous_campaigns,
        prior_campaign_names
    """
    history = load_contact_history(contact)

    result = {
        "campaign_name": campaign_metadata.get("campaign_name", ""),
        "apollo_sequence_name": (apollo_metadata or {}).get("apollo_sequence_name"),
        "campaign_metadata": campaign_metadata,
        "last_campaign_name": history.get("last_campaign_name"),
        "campaign_history_count": len(history.get("campaign_history", [])),
        "has_previous_campaigns": len(history.get("campaign_history", [])) > 1,
    }

    # Prior campaigns (bez bieżącej)
    current_name = campaign_metadata.get("campaign_name", "")
    prior = [
        e.get("campaign_name")
        for e in history.get("campaign_history", [])
        if e.get("campaign_name") != current_name
    ]
    if prior:
        result["prior_campaign_names"] = prior

    return result
