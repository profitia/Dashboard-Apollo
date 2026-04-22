"""
Company Name Normalizer — lekka warstwa normalizacji nazw firm.

Cel: zapewnić spójne canonical_name, comparison_key i aliasy
dla firm pojawiających się w artykułach w różnych formach.

Przykład:
    "Evra Fish Sp. z o.o." i "EvraFish" → comparison_key: "evrafish"

Nie wymaga zewnętrznych rejestrów firm — prosta, deterministyczna logika.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Suffiksy prawne do usunięcia przy budowaniu comparison_key
# ---------------------------------------------------------------------------
_LEGAL_SUFFIXES_RE = re.compile(
    r"\b("
    r"sp\.?\s*z\s*o\.?\s*o\.?"   # Sp. z o.o.
    r"|s\.?\s*a\.?"               # S.A.
    r"|sp\.?\s*j\.?"              # Sp. j.
    r"|sp\.?\s*k\.?"              # Sp. k.
    r"|s\.?\s*k\.?\s*a\.?"        # S.K.A.
    r"|p\.?\s*s\.?\s*a\.?"        # P.S.A.
    r"|gmbh"
    r"|ltd\.?"
    r"|inc\.?"
    r"|llc\.?"
    r"|b\.?\s*v\.?"               # B.V.
    r"|n\.?\s*v\.?"               # N.V.
    r")\b",
    flags=re.IGNORECASE,
)


@dataclass
class CompanyRecord:
    """
    Pełny rekord firmy z canonical name, comparison key i aliasami.

    Pola:
        source_name     — nazwa firmy tak jak pojawiła się w artykule / danych wejściowych
        canonical_name  — preferowana forma nazwy (brand firmy, strona firmowa, stopka)
        comparison_key  — znormalizowany klucz do deduplikacji i porównań
                          (lowercase, bez spacji, bez znaków spec, bez suffixu prawnego)
        aliases         — wszystkie znane warianty nazwy (łącznie z source i canonical)
    """
    source_name: str
    canonical_name: str
    comparison_key: str
    aliases: list[str] = field(default_factory=list)

    def matches(self, other_name: str) -> bool:
        """Sprawdza czy inny wariant nazwy pasuje do tego rekordu."""
        return make_comparison_key(other_name) == self.comparison_key


def make_comparison_key(name: str) -> str:
    """
    Tworzy znormalizowany klucz porównawczy z nazwy firmy.

    Transformacje (w kolejności):
    1. Strip whitespace
    2. Usuń suffiksy prawne (Sp. z o.o., S.A., Ltd., GmbH, ...)
    3. Zamień znaki niealfanumeryczne na spacje
    4. Konwertuj na lowercase
    5. Usuń wszystkie spacje (collapse)

    Przykłady:
        "Evra Fish Sp. z o.o."  → "evrafish"
        "EvraFish"              → "evrafish"
        "Evra Fish"             → "evrafish"
        "ORLEN S.A."            → "orlen"
        "Bio Planet Sp. z o.o." → "bioplanet"
        "Grycan"                → "grycan"
    """
    if not name:
        return ""
    n = name.strip()
    n = _LEGAL_SUFFIXES_RE.sub(" ", n)
    n = re.sub(r"[^\w\s]", " ", n)   # znaki spec → spacja
    n = n.lower()
    n = re.sub(r"\s+", "", n)          # usuń wszystkie spacje
    return n


def make_company_record(
    source_name: str,
    canonical_name: str | None = None,
    aliases: list[str] | None = None,
) -> CompanyRecord:
    """
    Tworzy CompanyRecord z source_name, opcjonalnego canonical_name i aliasów.

    Reguły:
    - Jeśli canonical_name nie podany, używamy source_name jako canonical.
    - comparison_key jest zawsze budowany z canonical_name.
    - aliases zawsze zawiera zarówno source_name jak i canonical_name.

    Przykład (Evra Fish → EvraFish):
        make_company_record(
            source_name="Evra Fish",
            canonical_name="EvraFish",
        )
        → CompanyRecord(
            source_name="Evra Fish",
            canonical_name="EvraFish",
            comparison_key="evrafish",
            aliases=["Evra Fish", "EvraFish"],
          )
    """
    canonical = canonical_name or source_name
    key = make_comparison_key(canonical)

    # Zbierz unikalne aliasy (source + canonical + dodatkowe)
    # Deduplikacja po dokładnej nazwie (nie po comparison_key) —
    # "Evra Fish" i "EvraFish" to dwa różne warianty, oba wartościowe.
    alias_list: list[str] = []
    seen_names: set[str] = set()
    for variant in [source_name, canonical] + (aliases or []):
        if variant and variant not in seen_names:
            alias_list.append(variant)
            seen_names.add(variant)

    return CompanyRecord(
        source_name=source_name,
        canonical_name=canonical,
        comparison_key=key,
        aliases=alias_list,
    )
