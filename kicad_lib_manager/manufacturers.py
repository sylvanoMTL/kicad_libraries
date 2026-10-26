"""The one canonical manufacturer table, read by the atomic check, the importer and the migration (D-09).

A leaf module: it imports only the standard library, so every layer reads one definition of which
spellings are the same company. To teach the tool a new manufacturer, add one line to MANUFACTURERS.
An acquired brand keeps its own canonical name (D-08): Maxim Integrated is never rewritten to Analog
Devices, the owner field is only a note for keyword generation.
"""

import re
import unicodedata
from dataclasses import dataclass

CORPORATE_WORDS = frozenset(
    {"inc", "ltd", "gmbh", "corp", "corporation", "co", "ag", "llc", "plc", "limited", "incorporated"}
)


@dataclass(frozen=True)
class Manufacturer:
    """One company: canonical name, other spellings, v1.0 library token and optional owner."""

    name: str
    aliases: tuple[str, ...] = ()
    # Short library token kept only for importer.suggest until Phase 10 drops it (LIB-04)
    token: str = ""
    # Informational (Phase 10 keywords); never changes the Manufacturer field (D-08)
    owner: str | None = None


@dataclass(frozen=True)
class ManufacturerMatch:
    """A table hit; exact is True only for the identical canonical spelling (D-10)."""

    entry: Manufacturer
    exact: bool


MANUFACTURERS: tuple[Manufacturer, ...] = (
    Manufacturer("Texas Instruments", ("TI",), "TI"),
    Manufacturer("Analog Devices", ("ADI",), "ADI"),
    Manufacturer("Maxim Integrated", ("Maxim", "Maxim Integrated Products"), "ADI", "Analog Devices"),
    Manufacturer("Linear Technology", ("Linear", "Linear Tech"), "ADI", "Analog Devices"),
    Manufacturer("TDK", (), "TDK"),
    Manufacturer("InvenSense", ("TDK InvenSense",), "TDK", "TDK"),
    Manufacturer("Murata", ("Murata Manufacturing", "Murata Electronics"), "Murata"),
    Manufacturer("Global Connector Technology", ("GCT",), "GCT"),
    Manufacturer("Memsic", ("Memsic Inc.",), "Memsic"),
    Manufacturer("u-blox", ("U-BLOX", "uBlox", "u-blox AG"), "uBlox"),
    Manufacturer("Abracon", ("Abracon LLC",), "Abracon"),
    Manufacturer("RECOM", ("RECOM Power", "RECOM Power GmbH"), "RECOM"),
)


def fold(text: str) -> str:
    """Fold a name for matching: NFKD, no combining marks, casefold, ASCII letters and digits, no corporate words."""
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c)).casefold()
    return "".join(w for w in re.findall(r"[a-z0-9]+", folded) if w not in CORPORATE_WORDS)


def _index(entries: tuple[Manufacturer, ...]) -> dict[str, Manufacturer]:
    """Map the folded name and aliases of every entry to that entry; two companies on one key is an error."""
    index: dict[str, Manufacturer] = {}
    for entry in entries:
        for spelling in (entry.name, *entry.aliases):
            key = fold(spelling)
            if not key:
                continue
            held = index.get(key)
            if held is not None and held != entry:
                raise ValueError(
                    f"manufacturers {held.name!r} and {entry.name!r} both fold to {key!r} ({spelling!r})"
                )
            index[key] = entry
    return index


# Built at import, so a bad table edit fails at once
_BY_FOLDED = _index(MANUFACTURERS)


def lookup(value: str) -> ManufacturerMatch | None:
    """Return the table entry a manufacturer value folds to, or None when it is empty or unknown."""
    key = fold(value)
    if not key:
        return None
    entry = _BY_FOLDED.get(key)
    if entry is None:
        return None
    return ManufacturerMatch(entry, value == entry.name)


def token_map() -> dict[str, str]:
    """Return folded name and aliases of every entry with a library token, mapped to that token."""
    return {key: entry.token for key, entry in _BY_FOLDED.items() if entry.token}
