"""Field-cleanup rules for incoming vendor symbols, shared by the adapters, candidate, planner and form.

A leaf module: it imports only the standard library, so every layer reads one definition of which
properties are Manufacturer or MPN aliases and which are volatile (stale price and stock data).
"""

import fnmatch
from dataclasses import dataclass

MANUFACTURER_FIELDS = ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")
MPN_FIELDS = ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")
DESCRIPTION_FIELDS = ("Description", "ki_description")

# Casefolded fnmatch patterns for properties that go stale (D-05). "*stock*" is deliberately not
# used, so a stock-code identifier is kept.
GENERIC_VOLATILE = ("price", "prices", "stock", "availability", "check_prices", "*price/stock")


@dataclass(frozen=True)
class FieldRules:
    """Per-adapter rules carried on the candidate (D-05, D-08, D-09)."""

    volatile: tuple[str, ...] = GENERIC_VOLATILE
    manufacturer_aliases: tuple[str, ...] = MANUFACTURER_FIELDS
    mpn_aliases: tuple[str, ...] = MPN_FIELDS


GENERIC_RULES = FieldRules()


def is_volatile(name: str, rules: FieldRules = GENERIC_RULES) -> bool:
    """Return True when a property name matches one of the rules' volatile patterns, ignoring case."""
    folded = name.strip().casefold()
    return any(fnmatch.fnmatchcase(folded, pattern) for pattern in rules.volatile)
