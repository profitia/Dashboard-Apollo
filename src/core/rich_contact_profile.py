#!/usr/bin/env python3
"""
Rich Contact Profile — rozszerzony model danych kontaktu.

Buduje per-contact pełny profil wiedzy, podzielony na sekcje:
- core_identity: imię, nazwisko, email, stanowisko, seniority
- org_context: firma, branża, departments, keywords
- urls: LinkedIn, website, social media
- location: osoby i firmy
- company_metadata: telefon, inne pola firmowe
- raw_input_metadata: oryginalne dane z CSV

Zasada: Input contact row = pełny profil wiedzy o odbiorcy, nie tylko rekord mailingowy.
"""

import json
import logging
import os
import re
from datetime import datetime

log = logging.getLogger(__name__)

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROFILES_DIR = os.path.join(_ROOT_DIR, "data", "contact_engagement")


# ============================================================
# Extended column mapping — aliasy dla bogatych inputów
# ============================================================

EXTENDED_COLUMN_MAP: dict[str, str] = {
    # --- core_identity ---
    "first name": "first_name",
    "first_name": "first_name",
    "contact_first_name": "first_name",
    "imię": "first_name",
    "last name": "last_name",
    "last_name": "last_name",
    "contact_last_name": "last_name",
    "nazwisko": "last_name",
    "name": "full_name",
    "full name": "full_name",
    "full_name": "full_name",
    "contact name": "full_name",
    "contact_name": "full_name",
    "email": "email",
    "email address": "email",
    "email_address": "email",
    "e-mail": "email",
    "contact_email": "email",
    "title": "job_title",
    "job title": "job_title",
    "job_title": "job_title",
    "job role": "job_title",
    "job_role": "job_title",
    "contact_title": "job_title",
    "role": "job_title",
    "position": "job_title",
    "stanowisko": "job_title",
    "seniority": "seniority",
    "seniority level": "seniority",
    "seniority_level": "seniority",

    # --- org_context ---
    "company": "company_name",
    "company name": "company_name",
    "company_name": "company_name",
    "firma": "company_name",
    "departments": "departments",
    "department": "departments",
    "sub departments": "sub_departments",
    "sub_departments": "sub_departments",
    "subdepartments": "sub_departments",
    "industry": "industry",
    "branża": "industry",
    "keywords": "keywords",
    "keyword": "keywords",
    "tags": "keywords",

    # --- urls ---
    "person linkedin url": "person_linkedin_url",
    "person_linkedin_url": "person_linkedin_url",
    "linkedin url": "person_linkedin_url",
    "linkedin_url": "person_linkedin_url",
    "linkedin": "person_linkedin_url",
    "website": "website",
    "company website": "website",
    "company_website": "website",
    "domain": "company_domain",
    "company domain": "company_domain",
    "company_domain": "company_domain",
    "company linkedin url": "company_linkedin_url",
    "company_linkedin_url": "company_linkedin_url",
    "facebook url": "facebook_url",
    "facebook_url": "facebook_url",
    "facebook": "facebook_url",
    "twitter url": "twitter_url",
    "twitter_url": "twitter_url",
    "twitter": "twitter_url",

    # --- location (person) ---
    "city": "city",
    "miasto": "city",
    "state": "state",
    "województwo": "state",
    "country": "country",
    "kraj": "country",

    # --- location (company) ---
    "company address": "company_address",
    "company_address": "company_address",
    "company city": "company_city",
    "company_city": "company_city",
    "company state": "company_state",
    "company_state": "company_state",
    "company country": "company_country",
    "company_country": "company_country",

    # --- company_metadata ---
    "company phone": "company_phone",
    "company_phone": "company_phone",
    "phone": "company_phone",
    "telefon": "company_phone",
    "# employees": "employees_count",
    "employees": "employees_count",
    "number of employees": "employees_count",
    "employees_count": "employees_count",
    "annual revenue": "annual_revenue",
    "annual_revenue": "annual_revenue",
    "revenue": "annual_revenue",
    "company description": "company_description",
    "company_description": "company_description",
    "opis firmy": "company_description",
    "description": "company_description",
    "short description": "company_description",
    "short_description": "company_description",
    "company bio": "company_description",
    "company_bio": "company_description",
    "about": "company_description",
    "about company": "company_description",
    "seo description": "company_description",
    "seo_description": "company_description",

    # --- notes ---
    "notes": "notes",
    "note": "notes",
    "comment": "notes",
    "comments": "notes",
    "uwagi": "notes",
}


def _normalize_column_key(col: str) -> str:
    """Normalizuje nazwę kolumny: lowercase, strip, spacje → single space."""
    return re.sub(r'\s+', ' ', col.strip().lower())


def map_extended_columns(row: dict) -> dict:
    """
    Mapuje kolumny CSV na rozszerzone pola wewnętrzne.
    Rozpoznaje aliasy, różne wielkości liter, spacje.
    Zwraca dict z rozpoznanymi polami + raw_extra z nierozpoznanymi.
    """
    mapped: dict[str, str] = {}
    raw_extra: dict[str, str] = {}

    for csv_col, value in row.items():
        val = value.strip() if value else ""
        if not val:
            continue

        key = _normalize_column_key(csv_col)
        if key in EXTENDED_COLUMN_MAP:
            target = EXTENDED_COLUMN_MAP[key]
            # first_name / last_name mają priorytet nad full_name
            if target in ("first_name", "last_name"):
                mapped[target] = val
            elif target not in mapped or not mapped[target]:
                mapped[target] = val
        else:
            # Nierozpoznane pole — zachowaj w raw_extra
            raw_extra[csv_col.strip()] = val

    return {"mapped": mapped, "raw_extra": raw_extra}


# ============================================================
# Keywords processing
# ============================================================

def process_keywords(raw_keywords: str) -> dict:
    """
    Przetwarza pole keywords:
    - zachowuje raw
    - rozbija na listę tokenów
    - normalizuje (lowercase, trim)
    """
    if not raw_keywords or not raw_keywords.strip():
        return {
            "keywords_raw": "",
            "keywords_list": [],
            "keywords_normalized": [],
        }

    raw = raw_keywords.strip()
    # Rozbij po przecinkach, średnikach, pipe
    tokens = re.split(r'[,;|]+', raw)
    tokens = [t.strip() for t in tokens if t.strip()]
    normalized = [t.lower() for t in tokens]

    return {
        "keywords_raw": raw,
        "keywords_list": tokens,
        "keywords_normalized": normalized,
    }


# ============================================================
# Build rich contact profile
# ============================================================

def build_rich_profile(row: dict) -> dict:
    """
    Buduje rozszerzony profil kontaktu z jednego rekordu CSV.

    Sekcje:
    A. core_identity
    B. org_context
    C. urls
    D. location
    E. company_metadata
    F. raw_input_metadata

    Returns:
        dict z sekcjami profilu + normalization_warnings.
    """
    result = map_extended_columns(row)
    m = result["mapped"]
    raw_extra = result["raw_extra"]
    warnings: list[str] = []

    # --- Resolve full_name / first_name / last_name ---
    full_name = m.get("full_name", "")
    first_name = m.get("first_name", "")
    last_name = m.get("last_name", "")

    if full_name and not first_name and not last_name:
        parts = full_name.strip().split()
        if len(parts) == 1:
            first_name = parts[0]
            warnings.append(f"Name '{full_name}' has only one part")
        elif len(parts) >= 2:
            first_name = parts[0]
            last_name = " ".join(parts[1:])
    elif not full_name and first_name:
        full_name = f"{first_name} {last_name}".strip()

    # --- Keywords ---
    kw = process_keywords(m.get("keywords", ""))

    # --- Build sections ---
    profile = {
        "core_identity": {
            "first_name": first_name or None,
            "last_name": last_name or None,
            "full_name": full_name or None,
            "email": m.get("email") or None,
            "job_title": m.get("job_title") or None,
            "seniority": m.get("seniority") or None,
        },
        "org_context": {
            "company_name": m.get("company_name") or None,
            "departments": m.get("departments") or None,
            "sub_departments": m.get("sub_departments") or None,
            "industry": m.get("industry") or None,
            "keywords_raw": kw["keywords_raw"] or None,
            "keywords_list": kw["keywords_list"] or [],
            "keywords_normalized": kw["keywords_normalized"] or [],
        },
        "urls": {
            "person_linkedin_url": m.get("person_linkedin_url") or None,
            "website": m.get("website") or None,
            "company_domain": m.get("company_domain") or None,
            "company_linkedin_url": m.get("company_linkedin_url") or None,
            "facebook_url": m.get("facebook_url") or None,
            "twitter_url": m.get("twitter_url") or None,
        },
        "location": {
            "city": m.get("city") or None,
            "state": m.get("state") or None,
            "country": (m.get("country") or "").upper() or None,
            "company_address": m.get("company_address") or None,
            "company_city": m.get("company_city") or None,
            "company_state": m.get("company_state") or None,
            "company_country": (m.get("company_country") or "").upper() or None,
        },
        "company_metadata": {
            "company_phone": m.get("company_phone") or None,
            "employees_count": m.get("employees_count") or None,
            "annual_revenue": m.get("annual_revenue") or None,
            "company_description": m.get("company_description") or None,
        },
        "raw_input_metadata": {
            "original_row": {k: v for k, v in row.items() if v and v.strip()},
            "unmapped_fields": raw_extra,
            "imported_at": datetime.now().isoformat(),
        },
    }

    # --- Validation warnings ---
    if not profile["core_identity"]["first_name"]:
        warnings.append("Missing first_name")
    if not profile["core_identity"]["email"]:
        warnings.append("Missing email")
    if not profile["org_context"]["company_name"]:
        warnings.append("Missing company_name")
    if not profile["core_identity"]["job_title"]:
        warnings.append("Missing job_title")

    profile["normalization_warnings"] = warnings
    return profile


def build_rich_profiles(rows: list[dict]) -> list[dict]:
    """Buduje rozszerzone profile dla listy rekordów CSV."""
    return [build_rich_profile(row) for row in rows]


# ============================================================
# Flatten for backward compatibility
# ============================================================

def flatten_to_normalized_contact(profile: dict, gender_data: dict | None = None) -> dict:
    """
    Spłaszcza rich profile do formatu normalized_contact kompatybilnego
    z istniejącym pipeline (csv_normalizer output format).

    Zachowuje backward compatibility z run_csv_campaign.py i innymi agentami.
    Dodaje rich_profile jako nested field.
    """
    ci = profile.get("core_identity", {})
    oc = profile.get("org_context", {})
    urls = profile.get("urls", {})
    loc = profile.get("location", {})

    g = gender_data or {}

    return {
        # --- Backward-compatible fields ---
        "full_name": ci.get("full_name") or "",
        "first_name": ci.get("first_name") or None,
        "last_name": ci.get("last_name") or None,
        "first_name_vocative": g.get("vocative"),
        "gender": g.get("gender", "unknown"),
        "greeting": g.get("greeting", "Dzień dobry,"),
        "job_title": ci.get("job_title") or "",
        "company_name": oc.get("company_name") or "",
        "company_domain": urls.get("company_domain") or urls.get("website") or "",
        "country": loc.get("country") or "",
        "industry": oc.get("industry") or "",
        "notes": "",  # Preserved from original or empty
        "normalization_warnings": profile.get("normalization_warnings", []),
        # --- Extended: email ---
        "email": ci.get("email") or "",
        # --- Extended: seniority ---
        "seniority": ci.get("seniority") or "",
        # --- Extended: keywords ---
        "keywords_raw": oc.get("keywords_raw") or "",
        "keywords_list": oc.get("keywords_list", []),
        # --- Extended: urls (as individual fields) ---
        "person_linkedin_url": urls.get("person_linkedin_url") or "",
        "website": urls.get("website") or "",
        "company_linkedin_url": urls.get("company_linkedin_url") or "",
        "facebook_url": urls.get("facebook_url") or "",
        "twitter_url": urls.get("twitter_url") or "",
        # --- Extended: location ---
        "city": loc.get("city") or "",
        "state": loc.get("state") or "",
        "company_city": loc.get("company_city") or "",
        "company_country": loc.get("company_country") or "",
        # --- Extended: company_description ---
        "company_description": profile.get("company_metadata", {}).get("company_description") or "",
        # --- Full rich profile ---
        "rich_profile": profile,
    }


# ============================================================
# LLM context builder — selects what goes to LLM
# ============================================================

def build_llm_context(profile: dict) -> dict:
    """
    Buduje kontekst kontaktu do przekazania do LLM.

    Zasada: nie dumpuj całego raw CSV, ale wybierz rozsądne podsumowanie.
    LLM dostaje to, co pomaga w personalizacji. Metadata zostaje w storage.
    """
    ci = profile.get("core_identity", {})
    oc = profile.get("org_context", {})
    urls = profile.get("urls", {})
    loc = profile.get("location", {})
    cm = profile.get("company_metadata", {})

    context = {
        # Person
        "first_name": ci.get("first_name"),
        "last_name": ci.get("last_name"),
        "job_title": ci.get("job_title"),
        "seniority": ci.get("seniority"),
        # Company
        "company_name": oc.get("company_name"),
        "industry": oc.get("industry"),
        "departments": oc.get("departments"),
        # Keywords — important for angle/hypothesis
        "keywords": oc.get("keywords_list", []),
        # Location context (useful for messaging)
        "country": loc.get("country"),
        "city": loc.get("city"),
        "company_country": loc.get("company_country"),
        "company_city": loc.get("company_city"),
        # URLs — for context awareness (LLM can reference)
        "person_linkedin_url": urls.get("person_linkedin_url"),
        "website": urls.get("website") or urls.get("company_domain"),
        "company_linkedin_url": urls.get("company_linkedin_url"),
        # Company scale indicators
        "employees_count": cm.get("employees_count"),
        # Company description — high-value for personalization
        "company_description": cm.get("company_description"),
    }

    # Remove None values for cleaner prompt
    return {k: v for k, v in context.items() if v}


# ============================================================
# Storage — persist / load / merge profiles
# ============================================================

def _profile_key(profile: dict) -> str:
    """Generuje klucz storage z profilu."""
    ci = profile.get("core_identity", {})
    email = (ci.get("email") or "").strip().lower()
    if email:
        return email
    first = (ci.get("first_name") or "").strip().lower()
    last = (ci.get("last_name") or "").strip().lower()
    company = (profile.get("org_context", {}).get("company_name") or "").strip().lower()
    return f"{first}_{last}_{company}"


def _safe_filename(key: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in key)


def _profile_path(key: str) -> str:
    return os.path.join(_PROFILES_DIR, f"{_safe_filename(key)}_rich_profile.json")


def save_rich_profile(profile: dict) -> str:
    """Zapisuje rich profile na dysk. Zwraca ścieżkę."""
    os.makedirs(_PROFILES_DIR, exist_ok=True)
    key = _profile_key(profile)
    path = _profile_path(key)

    # Add storage metadata
    profile.setdefault("_storage_meta", {})
    profile["_storage_meta"]["contact_key"] = key
    profile["_storage_meta"]["last_saved_at"] = datetime.now().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    log.info("Rich profile saved: %s", key)
    return path


def load_rich_profile(key: str) -> dict | None:
    """Wczytuje rich profile z dysku po kluczu."""
    os.makedirs(_PROFILES_DIR, exist_ok=True)
    path = _profile_path(key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_rich_profile_by_contact(contact: dict) -> dict | None:
    """Wczytuje rich profile po danych kontaktu."""
    email = (contact.get("email") or "").strip().lower()
    if email:
        return load_rich_profile(email)
    first = (contact.get("first_name") or "").strip().lower()
    last = (contact.get("last_name") or "").strip().lower()
    company = (contact.get("company_name") or contact.get("company") or "").strip().lower()
    key = f"{first}_{last}_{company}"
    return load_rich_profile(key)


def merge_profiles(existing: dict, new: dict) -> dict:
    """
    Merguje nowy profil z istniejącym. Zasada:
    - Nie nadpisuj lepszych wartości gorszymi (non-empty stays)
    - Wzbogacaj profil o nowe dane
    - Zachowaj historię raw_input_metadata (dodaj nowy import)
    """
    merged = json.loads(json.dumps(existing))  # deep copy

    for section_key in ("core_identity", "org_context", "urls", "location", "company_metadata"):
        existing_section = merged.get(section_key, {})
        new_section = new.get(section_key, {})

        for field, new_val in new_section.items():
            if new_val is None:
                continue
            if isinstance(new_val, list) and not new_val:
                continue
            old_val = existing_section.get(field)
            # Preserve non-empty existing value unless new value is richer
            if old_val is None or old_val == "" or old_val == []:
                existing_section[field] = new_val
            elif isinstance(new_val, list) and isinstance(old_val, list):
                # Merge lists (union)
                combined = list(dict.fromkeys(old_val + new_val))
                existing_section[field] = combined

        merged[section_key] = existing_section

    # Merge raw_input_metadata — append new import
    existing_raw = merged.get("raw_input_metadata", {})
    new_raw = new.get("raw_input_metadata", {})
    if "import_history" not in existing_raw:
        existing_raw["import_history"] = []
    existing_raw["import_history"].append({
        "imported_at": new_raw.get("imported_at", datetime.now().isoformat()),
        "original_row": new_raw.get("original_row", {}),
        "unmapped_fields": new_raw.get("unmapped_fields", {}),
    })
    merged["raw_input_metadata"] = existing_raw

    # Preserve warnings from new
    merged["normalization_warnings"] = new.get("normalization_warnings", [])

    return merged


def save_or_merge_rich_profile(profile: dict) -> str:
    """
    Zapisuje rich profile. Jeśli istnieje — merguje (enrich, nie nadpisuj).
    Zwraca ścieżkę.
    """
    key = _profile_key(profile)
    existing = load_rich_profile(key)
    if existing:
        merged = merge_profiles(existing, profile)
        log.info("Rich profile merged (enriched): %s", key)
        return save_rich_profile(merged)
    else:
        return save_rich_profile(profile)
