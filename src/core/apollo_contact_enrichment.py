#!/usr/bin/env python3
"""
Apollo Contact Name Enrichment — deterministyczny enrichment pól kontaktu.

Uzupełnia custom fields Apollo:
- Vocative First Name
- Sex

Wyłącznie na podstawie zatwierdzonego source of truth (context/Vocative names od VSC.csv).
Nigdy nie zgaduje, nie inferuje heurystycznie, nie nadpisuje istniejących wartości.

Zasady:
1. Jeśli pole jest już uzupełnione w Apollo → nie nadpisuj.
2. Jeśli imię jest w source of truth → uzupełnij brakujące pola.
3. Jeśli imienia nie ma w source of truth → zostaw puste.
4. Nigdy nie twórz wołacza heurystycznie.
5. Nigdy nie inferuj płci z brzmienia imienia.
"""

import logging
import os
import sys
from typing import Optional

from core.polish_names import get_polish_name_data

log = logging.getLogger(__name__)

# ============================================================
# Apollo custom field names (exact match with Apollo)
# ============================================================

APOLLO_FIELD_VOCATIVE = "Vocative First Name"
APOLLO_FIELD_SEX = "Sex"

# Mapowanie gender z source of truth → wartość w Apollo
_SEX_VALUE_MAP = {
    "female": "female",
    "male": "male",
}

# ============================================================
# Lazy Apollo client
# ============================================================

_apollo_client = None


def _get_apollo_client():
    """Lazy init ApolloClient. Zwraca None jeśli niedostępny."""
    global _apollo_client
    if _apollo_client is not None:
        return _apollo_client

    try:
        integracje_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "Integracje",
        )
        if integracje_dir not in sys.path:
            sys.path.insert(0, integracje_dir)
        from apollo_client import ApolloClient
        _apollo_client = ApolloClient()
        return _apollo_client
    except Exception as exc:
        log.warning("Apollo client niedostępny: %s", exc)
        return None


# ============================================================
# Dictionary-only resolvers (no heuristics, no LLM)
# ============================================================

def resolve_vocative_from_dictionary(first_name: str) -> Optional[str]:
    """
    Zwraca wołacz z zatwierdzonej bazy imion lub None.
    Nie tworzy wołacza heurystycznie.
    """
    data = get_polish_name_data(first_name)
    return data["vocative"] if data else None


def resolve_sex_from_dictionary(first_name: str) -> Optional[str]:
    """
    Zwraca płeć z zatwierdzonej bazy imion lub None.
    Nie inferuje płci z brzmienia imienia.
    Zwraca: 'female', 'male' lub None (nie 'unknown').
    """
    data = get_polish_name_data(first_name)
    if data:
        return _SEX_VALUE_MAP.get(data["gender"])
    return None


# ============================================================
# Apollo field readers/writers
# ============================================================

def get_apollo_contact_custom_fields(contact_id: str) -> dict:
    """
    Pobiera resolved custom fields kontaktu z Apollo.

    Returns:
        dict z nazwami pól jako kluczami, np.:
        {"Vocative First Name": "Tomaszu", "Sex": "male", ...}
        Pusty dict jeśli Apollo niedostępny lub kontakt nie znaleziony.
    """
    client = _get_apollo_client()
    if client is None:
        return {}

    try:
        data = client.get_contact_details(contact_id)
        contact = data.get("contact", data)
        return client.resolve_custom_fields(contact)
    except Exception as exc:
        log.warning("Nie udało się pobrać custom fields dla %s: %s", contact_id, exc)
        return {}


def update_apollo_contact_custom_fields_if_empty(
    contact_id: str,
    values: dict[str, str],
) -> dict:
    """
    Aktualizuje custom fields kontaktu w Apollo, ale TYLKO jeśli pole jest puste.

    Args:
        contact_id: Apollo contact ID
        values: dict {field_name: value}, np. {"Vocative First Name": "Tomaszu", "Sex": "male"}

    Returns:
        dict z wynikiem operacji.
    """
    client = _get_apollo_client()
    if client is None:
        return {"status": "apollo_unavailable", "fields_updated": []}

    # Pobierz aktualne wartości
    current_fields = get_apollo_contact_custom_fields(contact_id)

    # Filtruj — update tylko puste pola
    fields_to_update = {}
    fields_skipped = []
    for field_name, new_value in values.items():
        current_value = current_fields.get(field_name)
        if current_value and str(current_value).strip():
            fields_skipped.append(field_name)
            log.debug("Pole '%s' już wypełnione (%s) — pomijam.", field_name, current_value)
        else:
            field_id = client.get_custom_field_id(field_name)
            if field_id:
                fields_to_update[field_id] = new_value
            else:
                log.warning("Custom field '%s' nie znaleziony w Apollo.", field_name)

    if not fields_to_update:
        return {
            "status": "no_update_needed",
            "fields_updated": [],
            "fields_skipped": fields_skipped,
        }

    # PATCH contact via ApolloClient
    try:
        client.update_contact(contact_id, typed_custom_fields=fields_to_update)

        log.info(
            "Apollo: zaktualizowano pola kontaktu %s: %s",
            contact_id,
            [fn for fn in values if fn not in fields_skipped],
        )
        return {
            "status": "success",
            "fields_updated": [fn for fn in values if fn not in fields_skipped],
            "fields_skipped": fields_skipped,
        }
    except Exception as exc:
        log.warning("Apollo: błąd aktualizacji kontaktu %s: %s", contact_id, exc)
        return {
            "status": f"apollo_update_failed: {exc}",
            "fields_updated": [],
            "fields_skipped": fields_skipped,
        }


# ============================================================
# Main enrichment function
# ============================================================

def enrich_contact_name_fields(
    contact: dict,
    write_to_apollo: bool = True,
) -> dict:
    """
    Deterministyczny enrichment pól Vocative First Name i Sex.

    Logika:
    1. Pobierz first_name z kontaktu.
    2. Sprawdź istniejące wartości (Apollo lub lokalne).
    3. Jeśli oba pola uzupełnione → skip.
    4. Jeśli brakujące → sprawdź source of truth.
    5. Uzupełnij brakujące z bazy (jeśli znalezione).
    6. Opcjonalnie zapisz do Apollo.

    Args:
        contact: dict z danymi kontaktu. Wymagane klucze:
            - first_name (str): imię kontaktu
            Opcjonalne:
            - apollo_contact_id (str): ID kontaktu w Apollo
            - vocative_first_name (str): istniejący wołacz
            - sex (str): istniejąca płeć

        write_to_apollo: czy zapisać wynik do Apollo (wymaga apollo_contact_id)

    Returns:
        dict z metadanymi enrichmentu:
        - vocative_first_name: str | None
        - sex: str | None
        - vocative_enrichment_attempted: bool
        - vocative_found_in_dictionary: bool
        - vocative_written_to_apollo: bool
        - sex_found_in_dictionary: bool
        - sex_written_to_apollo: bool
        - enrichment_skipped_reason: str | None
        - enrichment_status: str
    """
    first_name = contact.get("first_name") or contact.get("contact_first_name") or ""
    apollo_contact_id = contact.get("apollo_contact_id") or contact.get("id")

    result = {
        "vocative_first_name": None,
        "sex": None,
        "vocative_enrichment_attempted": False,
        "vocative_found_in_dictionary": False,
        "vocative_written_to_apollo": False,
        "sex_found_in_dictionary": False,
        "sex_written_to_apollo": False,
        "enrichment_skipped_reason": None,
        "enrichment_status": "pending",
    }

    # --- Brak imienia ---
    if not first_name or not first_name.strip():
        result["enrichment_skipped_reason"] = "no_first_name"
        result["enrichment_status"] = "skipped"
        return result

    first_name = first_name.strip()

    # --- Pobierz istniejące wartości ---
    existing_vocative = (
        contact.get("vocative_first_name")
        or contact.get("first_name_vocative")
        or ""
    ).strip()
    existing_sex = (contact.get("sex") or contact.get("gender") or "").strip()

    # Jeśli write_to_apollo i mamy apollo_contact_id, pobierz z Apollo
    if write_to_apollo and apollo_contact_id:
        apollo_fields = get_apollo_contact_custom_fields(apollo_contact_id)
        if not existing_vocative:
            existing_vocative = (apollo_fields.get(APOLLO_FIELD_VOCATIVE) or "").strip()
        if not existing_sex:
            existing_sex = (apollo_fields.get(APOLLO_FIELD_SEX) or "").strip()

    # --- Oba pola wypełnione → skip ---
    if existing_vocative and existing_sex:
        result["vocative_first_name"] = existing_vocative
        result["sex"] = existing_sex
        result["enrichment_skipped_reason"] = "fields_already_filled"
        result["enrichment_status"] = "skipped"
        return result

    # --- Lookup w source of truth ---
    result["vocative_enrichment_attempted"] = True
    name_data = get_polish_name_data(first_name)

    if name_data is None:
        result["enrichment_skipped_reason"] = "name_not_found_in_dictionary"
        result["enrichment_status"] = "not_found"
        # Zachowaj istniejące wartości
        result["vocative_first_name"] = existing_vocative or None
        result["sex"] = existing_sex or None
        return result

    # --- Resolve z bazy ---
    dict_vocative = name_data["vocative"]
    dict_sex = _SEX_VALUE_MAP.get(name_data["gender"])

    result["vocative_found_in_dictionary"] = True
    result["sex_found_in_dictionary"] = bool(dict_sex)

    # Ustaw wartości (zachowaj istniejące jeśli wypełnione)
    final_vocative = existing_vocative if existing_vocative else dict_vocative
    final_sex = existing_sex if existing_sex else dict_sex

    result["vocative_first_name"] = final_vocative
    result["sex"] = final_sex

    # --- Zapis do Apollo (opcjonalnie) ---
    if write_to_apollo and apollo_contact_id:
        fields_to_write = {}
        if not existing_vocative and dict_vocative:
            fields_to_write[APOLLO_FIELD_VOCATIVE] = dict_vocative
        if not existing_sex and dict_sex:
            fields_to_write[APOLLO_FIELD_SEX] = dict_sex

        if fields_to_write:
            apollo_result = update_apollo_contact_custom_fields_if_empty(
                apollo_contact_id, fields_to_write
            )
            if apollo_result["status"] == "success":
                if APOLLO_FIELD_VOCATIVE in fields_to_write:
                    result["vocative_written_to_apollo"] = True
                if APOLLO_FIELD_SEX in fields_to_write:
                    result["sex_written_to_apollo"] = True
                result["enrichment_status"] = "success"
            else:
                result["enrichment_status"] = f"apollo_update_failed"
                result["enrichment_skipped_reason"] = apollo_result["status"]
        else:
            result["enrichment_status"] = "success"
    else:
        result["enrichment_status"] = "success_local_only"

    return result


# ============================================================
# Batch enrichment (for pipeline use)
# ============================================================

def enrich_contacts_batch(
    contacts: list[dict],
    write_to_apollo: bool = False,
) -> list[dict]:
    """
    Enrichment dla listy kontaktów. Zwraca listę wyników enrichmentu.

    Args:
        contacts: lista kontaktów
        write_to_apollo: czy zapisywać do Apollo

    Returns:
        lista dict-ów z metadanymi enrichmentu (1:1 z contacts)
    """
    results = []
    for contact in contacts:
        result = enrich_contact_name_fields(contact, write_to_apollo=write_to_apollo)
        results.append(result)
    return results


# ============================================================
# Greeting fallback helper
# ============================================================

def build_safe_greeting(vocative_first_name: Optional[str], sex: Optional[str]) -> str:
    """
    Buduje bezpieczne powitanie z fallbackiem.

    Jeśli vocative i sex dostępne → "Dzień dobry Panie/Pani {vocative},"
    W przeciwnym razie → "Dzień dobry,"
    """
    if vocative_first_name and sex in ("female", "male"):
        prefix = "Pani" if sex == "female" else "Panie"
        return f"Dzień dobry {prefix} {vocative_first_name},"
    return "Dzień dobry,"
