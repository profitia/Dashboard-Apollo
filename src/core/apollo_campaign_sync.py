#!/usr/bin/env python3
"""
Apollo Campaign Integration — synchronizacja nazwy kampanii z Apollo.

Odpowiada za:
- Tworzenie/aktualizację nazwy sekwencji w Apollo
- Przypisywanie kontaktów do kampanii
- Mapowanie campaign_name VSC → apollo_sequence_name
- Synchronizacja treści outreach_pack → custom fields Apollo (sg_email_step_*)

Nie wykonuje operacji destrukcyjnych.
Jeśli Apollo API nie pozwala na operację, loguje warning i kontynuuje flow.
"""

import logging
import os

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

log = logging.getLogger(__name__)

# ============================================================
# Source of truth — Apollo campaign types
# ============================================================

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TYPES_PATH = os.path.join(_ROOT_DIR, "source_of_truth", "apollo_campaign_types.yaml")
_CUSTOM_FIELDS_PATH = os.path.join(_ROOT_DIR, "source_of_truth", "apollo_custom_fields.yaml")

_cached_types: dict | None = None


def _load_types() -> dict:
    """Wczytuje apollo_campaign_types.yaml (z cache)."""
    global _cached_types
    if _cached_types is not None:
        return _cached_types
    if yaml is None:
        raise ImportError("PyYAML jest wymagany: pip install pyyaml")
    if not os.path.exists(_TYPES_PATH):
        raise FileNotFoundError(f"Brak pliku: {_TYPES_PATH}")
    with open(_TYPES_PATH, "r", encoding="utf-8") as f:
        _cached_types = yaml.safe_load(f)
    return _cached_types


def reset_types_cache():
    """Czyści cache (np. w testach)."""
    global _cached_types
    _cached_types = None


# ============================================================
# Sequence cadence defaults — centralne źródło prawdy
# ============================================================

# Domyślny cadence: D0 / D+2 / D+2 (w minutach Apollo API)
DEFAULT_SEQUENCE_CADENCE_MINUTES = [0, 2880, 2880]


def get_sequence_cadence(config: dict | None = None) -> list[int]:
    """
    Zwraca listę wait_time (w minutach) dla 3-step sequence.

    Hierarchia:
    1. config["sequence_cadence"] z pliku YAML kampanii (override)
    2. sequence_cadence z apollo_custom_fields.yaml (source of truth)
    3. DEFAULT_SEQUENCE_CADENCE_MINUTES (hardcoded fallback)

    Returns:
        [0, 2880, 2880] — wait_time w minutach dla step 1, 2, 3
    """
    # 1. Override z configa kampanii
    if config and "sequence_cadence" in config:
        sc = config["sequence_cadence"]
        if isinstance(sc, list):
            return [int(v) for v in sc]
        if isinstance(sc, dict):
            return [
                int(sc.get("step_1", {}).get("wait_time_minutes", 0)),
                int(sc.get("step_2", {}).get("wait_time_minutes", 2880)),
                int(sc.get("step_3", {}).get("wait_time_minutes", 2880)),
            ]

    # 2. Source of truth z YAML
    try:
        cfg = _load_custom_fields_config()
        sc = cfg.get("sequence_cadence")
        if sc:
            return [
                int(sc["step_1"]["wait_time_minutes"]),
                int(sc["step_2"]["wait_time_minutes"]),
                int(sc["step_3"]["wait_time_minutes"]),
            ]
    except Exception:
        pass

    # 3. Fallback
    return list(DEFAULT_SEQUENCE_CADENCE_MINUTES)


# ============================================================
# Custom fields mapping — sequence email content
# ============================================================

_cached_custom_fields_config: dict | None = None


def _load_custom_fields_config() -> dict:
    """Wczytuje apollo_custom_fields.yaml (z cache)."""
    global _cached_custom_fields_config
    if _cached_custom_fields_config is not None:
        return _cached_custom_fields_config
    if yaml is None:
        raise ImportError("PyYAML jest wymagany: pip install pyyaml")
    if not os.path.exists(_CUSTOM_FIELDS_PATH):
        raise FileNotFoundError(f"Brak pliku: {_CUSTOM_FIELDS_PATH}")
    with open(_CUSTOM_FIELDS_PATH, "r", encoding="utf-8") as f:
        _cached_custom_fields_config = yaml.safe_load(f)
    return _cached_custom_fields_config


def get_outreach_pack_mapping() -> dict:
    """
    Zwraca mapowanie outreach_pack → Apollo custom fields.

    Returns:
        dict np.:
        {
            "email_1": {"subject": "sg_email_step_1_subject", "body": "sg_email_step_1_body"},
            "follow_up_1": {"subject": "sg_email_step_2_subject", "body": "sg_email_step_2_body"},
            "follow_up_2": {"subject": "sg_email_step_3_subject", "body": "sg_email_step_3_body"},
        }
    """
    config = _load_custom_fields_config()
    return config["outreach_pack_mapping"]


def outreach_pack_to_custom_fields(outreach_pack: dict) -> dict:
    """
    Mapuje outreach_pack (email_1, follow_up_1, follow_up_2) na dict custom fields Apollo.

    Od 2026-04-20: body mapowane z klucza body_html_nosig (HTML bez podpisu).
    Podpis jest w osobnym polu pl_signature_tu (dodawany przez sync_outreach_pack_to_apollo).

    Args:
        outreach_pack: dict z kluczami email_1, follow_up_1, follow_up_2,
                       każdy z: subject, body_html_nosig

    Returns:
        dict {apollo_field_name: value}, np.:
        {
            "sg_email_step_1_subject": "Temat",
            "sg_email_step_1_body": "<HTML treść bez podpisu>",
            ...
        }
    """
    mapping = get_outreach_pack_mapping()
    fields = {}
    for pack_key, field_map in mapping.items():
        step = outreach_pack.get(pack_key)
        if not step:
            log.warning("outreach_pack brakuje klucza '%s' — pomijam", pack_key)
            continue
        for content_key, apollo_field in field_map.items():
            value = step.get(content_key, "")
            if value:
                fields[apollo_field] = value
    return fields


def get_signature_field_name() -> str:
    """Zwraca nazwę pola podpisu z source of truth."""
    config = _load_custom_fields_config()
    return config.get("signature_field", "pl_signature_tu")


def sync_outreach_pack_to_apollo(
    contact_email: str,
    outreach_pack: dict,
) -> dict:
    """
    Zapisuje treści outreach_pack do custom fields kontaktu w Apollo.

    Flow:
    1. Mapuje outreach_pack → 6 custom fields (sg_email_step_*)
    2. Szuka kontaktu w Apollo po email
    3. PATCH kontaktu z typed_custom_fields

    Args:
        contact_email: Email kontaktu w Apollo
        outreach_pack: dict z email_1, follow_up_1, follow_up_2

    Returns:
        dict z wynikiem: status, contact_id, fields_written, etc.
    """
    client = _get_apollo_client()
    if client is None:
        return {"status": "unavailable", "reason": "apollo_client_not_available"}

    # 1. Mapuj treści na pola Apollo
    field_values = outreach_pack_to_custom_fields(outreach_pack)
    if not field_values:
        return {"status": "error", "reason": "no_fields_mapped"}

    # 2. Znajdź kontakt
    try:
        contact = client.search_contact(contact_email)
        if not contact:
            return {"status": "error", "reason": "contact_not_found", "email": contact_email}
        contact_id = contact["id"]
    except Exception as exc:
        return {"status": "error", "reason": f"search_failed: {exc}"}

    # 3. Zapisz custom fields
    try:
        result = client.update_contact_custom_fields(contact_id, field_values)
        log.info("Apollo: zapisano %d pól sekwencji dla %s", len(field_values), contact_email)
        return {
            "status": "success",
            "contact_id": contact_id,
            "contact_email": contact_email,
            "fields_written": list(field_values.keys()),
            "fields_count": len(field_values),
        }
    except Exception as exc:
        return {"status": "error", "reason": f"update_failed: {exc}", "contact_id": contact_id}

# Lazy import ApolloClient — nie blokuje jeśli moduł niedostępny
_apollo_client = None


def _get_apollo_client():
    """Lazy init ApolloClient. Zwraca None jeśli niedostępny."""
    global _apollo_client
    if _apollo_client is not None:
        return _apollo_client

    try:
        import sys
        # Integracje/ jest poza src/ — dodaj do path
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


def is_apollo_available() -> bool:
    """Sprawdza czy Apollo client jest dostępny."""
    return _get_apollo_client() is not None


def create_or_find_sequence(campaign_name: str) -> dict:
    """
    Próbuje znaleźć lub utworzyć sekwencję o nazwie campaign_name w Apollo.

    Apollo API nie pozwala na tworzenie sekwencji przez API (to feature UI).
    Zamiast tego szukamy istniejącej sekwencji po nazwie.

    Returns:
        dict z polami:
        - apollo_sequence_name: nazwa znalezionej sekwencji (lub None)
        - apollo_sequence_id: ID sekwencji (lub None)
        - apollo_sync_status: "matched" | "not_found" | "unavailable"
        - apollo_campaign_created: False (API nie tworzy sekwencji)
        - apollo_campaign_name_matched: True/False
    """
    client = _get_apollo_client()
    if client is None:
        return {
            "apollo_sequence_name": None,
            "apollo_sequence_id": None,
            "apollo_sync_status": "unavailable",
            "apollo_campaign_created": False,
            "apollo_campaign_name_matched": False,
        }

    try:
        sequences = client.get_sequences()
        for seq in sequences:
            seq_name = seq.get("name", "")
            if seq_name == campaign_name:
                log.info("Apollo: znaleziono sekwencję '%s' (id=%s)", campaign_name, seq.get("id"))
                return {
                    "apollo_sequence_name": seq_name,
                    "apollo_sequence_id": seq.get("id"),
                    "apollo_sync_status": "matched",
                    "apollo_campaign_created": False,
                    "apollo_campaign_name_matched": True,
                }

        log.info("Apollo: sekwencja '%s' nie znaleziona. Kontakty będą oflagowane wewnętrznie.", campaign_name)
        return {
            "apollo_sequence_name": None,
            "apollo_sequence_id": None,
            "apollo_sync_status": "not_found",
            "apollo_campaign_created": False,
            "apollo_campaign_name_matched": False,
        }
    except Exception as exc:
        log.warning("Apollo: błąd wyszukiwania sekwencji: %s", exc)
        return {
            "apollo_sequence_name": None,
            "apollo_sequence_id": None,
            "apollo_sync_status": f"error: {exc}",
            "apollo_campaign_created": False,
            "apollo_campaign_name_matched": False,
        }


def update_contact_apollo_fields(
    contact_email: str,
    campaign_name: str,
    campaign_type: str = "",
    tier: str = "",
) -> dict:
    """
    Aktualizuje custom fields kontaktu w Apollo z informacją o kampanii.

    Ustawia:
    - last_campaign_name
    - last_campaign_sent_at
    - last_campaign_type
    - last_campaign_tier

    Returns:
        dict z wynikiem operacji.
    """
    client = _get_apollo_client()
    if client is None:
        return {"apollo_contact_update": "unavailable"}

    try:
        contact = client.search_contact(contact_email)
        if not contact:
            return {"apollo_contact_update": "contact_not_found"}

        # Sprawdź czy custom fields istnieją
        field_map = {
            "last_campaign_name": campaign_name,
            "last_campaign_sent_at": __import__("datetime").datetime.now().isoformat(),
            "last_campaign_type": campaign_type,
            "last_campaign_tier": tier,
        }

        # Apollo custom fields update byłby tu, ale wymaga custom_field_id.
        # Logujemy jako operacja do wykonania.
        log.info("Apollo: flagowanie kontaktu %s → campaign=%s", contact_email, campaign_name)
        return {
            "apollo_contact_update": "fields_prepared",
            "apollo_contact_id": contact.get("id"),
            "fields_to_set": field_map,
        }
    except Exception as exc:
        log.warning("Apollo: błąd aktualizacji kontaktu %s: %s", contact_email, exc)
        return {"apollo_contact_update": f"error: {exc}"}


def add_contacts_to_sequence(
    campaign_name: str,
    contact_ids: list[str],
    email_account_id: str | None = None,
) -> dict:
    """
    Dodaje kontakty do sekwencji Apollo (jeśli istnieje).

    Returns:
        dict z wynikiem operacji.
    """
    seq_info = create_or_find_sequence(campaign_name)
    if seq_info["apollo_sync_status"] != "matched":
        return {
            "added": False,
            "reason": f"sequence_status={seq_info['apollo_sync_status']}",
            "sequence_info": seq_info,
        }

    client = _get_apollo_client()
    if client is None:
        return {"added": False, "reason": "client_unavailable"}

    try:
        result = client.add_to_sequence(
            sequence_id=seq_info["apollo_sequence_id"],
            contact_ids=contact_ids,
            email_account_id=email_account_id,
        )
        log.info("Apollo: dodano %d kontaktów do '%s'", len(contact_ids), campaign_name)
        return {
            "added": True,
            "contacts_count": len(contact_ids),
            "sequence_info": seq_info,
            "api_response": result,
        }
    except Exception as exc:
        log.warning("Apollo: błąd dodawania kontaktów do '%s': %s", campaign_name, exc)
        return {"added": False, "reason": f"error: {exc}", "sequence_info": seq_info}


def build_apollo_sync_payload(campaign_metadata: dict | None) -> dict:
    """
    Buduje payload synchronizacji Apollo na podstawie metadanych kampanii.

    Może być dołączony do outputów kampanii.
    """
    if not campaign_metadata:
        return {"apollo_sync_status": "no_metadata", "campaign_name": ""}

    campaign_name = campaign_metadata.get("campaign_name", "")
    campaign_type = campaign_metadata.get("campaign_type", "")

    delivery_type, apollo_step_type = resolve_campaign_delivery_type(campaign_type)
    template_name = "email_only" if delivery_type == "email_auto" else None

    return {
        "apollo_sequence_name": campaign_name,
        "campaign_name": campaign_name,
        "campaign_type": campaign_type,
        "tier": campaign_metadata.get("tier", ""),
        "segment": campaign_metadata.get("segment", ""),
        "angle": campaign_metadata.get("angle", ""),
        "market": campaign_metadata.get("market", ""),
        "delivery_type": delivery_type,
        "apollo_step_type": apollo_step_type,
        "sequence_template_name": template_name,
        "is_multichannel": delivery_type != "email_auto",
        "apollo_delivery_source": "source_of_truth",
    }


# ============================================================
# Resolvers — delivery type, step type, sequence template
# ============================================================

def resolve_apollo_step_type(delivery_type: str) -> str:
    """
    Mapuje wewnętrzny delivery_type na Apollo step type label.

    Args:
        delivery_type: kod wewnętrzny (np. "email_auto")

    Returns:
        Apollo label (np. "Automatic email")
    """
    types = _load_types()
    internal = types.get("internal_delivery_types", {})
    dt_info = internal.get(delivery_type)

    if dt_info:
        step_key = dt_info.get("default_apollo_step_type", "")
        step_types = types.get("apollo_step_types", {})
        step_info = step_types.get(step_key)
        if step_info:
            return step_info.get("apollo_label", "Automatic email")

    # Fallback
    return "Automatic email"


def resolve_campaign_delivery_type(campaign_type: str) -> tuple[str, str]:
    """
    Rozstrzyga delivery type i Apollo step type dla danego campaign type.

    Args:
        campaign_type: kod kampanii (np. "LinPost", "NoEmail")

    Returns:
        (delivery_type, apollo_step_type) np. ("email_auto", "Automatic email")
    """
    types = _load_types()
    defaults = types.get("campaign_type_delivery_defaults", {})

    ct_info = defaults.get(campaign_type)
    if ct_info:
        return ct_info["delivery_type"], ct_info["apollo_step_type"]

    # Fallback: domyślna reguła
    rule = types.get("default_campaign_delivery_rule", {})
    applies_to = rule.get("applies_to", [])
    if campaign_type in applies_to:
        return rule["primary_delivery_type"], rule["default_apollo_step_type"]

    return "email_auto", "Automatic email"


def build_apollo_sequence_template(template_name: str) -> list[dict]:
    """
    Zwraca listę kroków sekwencji na podstawie template'u z source of truth.

    Args:
        template_name: np. "email_only", "email_plus_call"

    Returns:
        Lista dict-ów z polami: step, apollo_step_type, delivery_type, label
    """
    types = _load_types()
    templates = types.get("sequence_templates", {})
    template = templates.get(template_name)

    if not template:
        log.warning("Template '%s' nie znaleziony - fallback na email_only.", template_name)
        template = templates.get("email_only")
        if not template:
            return [
                {"step": 1, "apollo_step_type": "Automatic email", "delivery_type": "email_auto", "label": "Email 1"},
                {"step": 2, "apollo_step_type": "Automatic email", "delivery_type": "email_auto", "label": "Email 2"},
                {"step": 3, "apollo_step_type": "Automatic email", "delivery_type": "email_auto", "label": "Email 3"},
            ]

    return template.get("steps", [])
