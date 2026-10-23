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


# Values vendors write for "nothing here" (D-06), compared trimmed and casefolded
PLACEHOLDER_VALUES = frozenset({"", "none", "n/a"})
# The KiCad standard fields; the cleanup never drops them, whatever their value
STANDARD_FIELDS = ("Reference", "Value", "Footprint", "Datasheet", "Description")


@dataclass(frozen=True)
class FieldRules:
    """Per-adapter rules carried on the candidate (D-05, D-08, D-09)."""

    volatile: tuple[str, ...] = GENERIC_VOLATILE
    manufacturer_aliases: tuple[str, ...] = MANUFACTURER_FIELDS
    mpn_aliases: tuple[str, ...] = MPN_FIELDS


GENERIC_RULES = FieldRules()


def is_placeholder(value: str) -> bool:
    """Return True when a property value is empty, "None" or "N/A", ignoring case and surrounding blanks."""
    return value.strip().casefold() in PLACEHOLDER_VALUES


def is_protected(name: str) -> bool:
    """Return True for a property the cleanup must never drop: a KiCad standard field or any ki_* name.

    The ki_* rule is wider than the standard list on purpose: KiCad reserves every ki_ name, and the
    Ultra Librarian symbol carries an empty ki_locked that must survive the placeholder rule.
    """
    return name in STANDARD_FIELDS or name.casefold().startswith("ki_")


def is_volatile(name: str, rules: FieldRules = GENERIC_RULES) -> bool:
    """Return True when a property name matches one of the rules' volatile patterns, ignoring case."""
    folded = name.strip().casefold()
    return any(fnmatch.fnmatchcase(folded, pattern) for pattern in rules.volatile)
