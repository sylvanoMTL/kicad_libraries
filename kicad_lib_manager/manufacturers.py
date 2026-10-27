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
    """One company: canonical name, other spellings, v1.0 library token, optional owner and datasheet domains."""

    name: str
    aliases: tuple[str, ...] = ()
    # Short library token kept only for importer.suggest until Phase 10 drops it (LIB-04)
    token: str = ""
    # Informational (Phase 10 keywords); never changes the Manufacturer field (D-08)
    owner: str | None = None
    # Registered datasheet domains of the company, lowercase; aggregator sites are never listed (D-23)
    hosts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManufacturerMatch:
    """A table hit; exact is True only for the identical canonical spelling (D-10)."""

    entry: Manufacturer
    exact: bool


MANUFACTURERS: tuple[Manufacturer, ...] = (
    Manufacturer("Texas Instruments", ("TI",), "TI", hosts=("ti.com",)),
    Manufacturer("Analog Devices", ("ADI",), "ADI", hosts=("analog.com",)),
    Manufacturer(
        "Maxim Integrated",
        ("Maxim", "Maxim Integrated Products"),
        "ADI",
        "Analog Devices",
        hosts=("maximintegrated.com",),
    ),
    Manufacturer(
        "Linear Technology", ("Linear", "Linear Tech"), "ADI", "Analog Devices", hosts=("linear.com",)
    ),
    Manufacturer("TDK", (), "TDK", hosts=("tdk.com",)),
    Manufacturer("InvenSense", ("TDK InvenSense",), "TDK", "TDK", hosts=("invensense.com",)),
    Manufacturer(
        "Murata", ("Murata Manufacturing", "Murata Electronics"), "Murata", hosts=("murata.com",)
    ),
    Manufacturer("Global Connector Technology", ("GCT",), "GCT", hosts=("gct.co",)),
    Manufacturer("Memsic", ("Memsic Inc.",), "Memsic", hosts=("memsic.com",)),
    Manufacturer("u-blox", ("U-BLOX", "uBlox", "u-blox AG"), "uBlox", hosts=("u-blox.com",)),
    Manufacturer("Abracon", ("Abracon LLC",), "Abracon", hosts=("abracon.com",)),
    Manufacturer("RECOM", ("RECOM Power", "RECOM Power GmbH"), "RECOM", hosts=("recom-power.com",)),
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


def _index_hosts(entries: tuple[Manufacturer, ...]) -> dict[str, Manufacturer]:
    """Map the casefolded datasheet domain of every entry to that entry; one domain on two companies is an error."""
    index: dict[str, Manufacturer] = {}
    for entry in entries:
        for host in entry.hosts:
            key = host.casefold()
            held = index.get(key)
            if held is not None and held != entry:
                raise ValueError(f"manufacturers {held.name!r} and {entry.name!r} both claim the host {key!r}")
            index[key] = entry
    return index


# Built at import, so a bad table edit fails at once
_BY_FOLDED = _index(MANUFACTURERS)
_BY_HOST = _index_hosts(MANUFACTURERS)


def lookup(value: str) -> ManufacturerMatch | None:
    """Return the table entry a manufacturer value folds to, or None when it is empty or unknown."""
    key = fold(value)
    if not key:
        return None
    entry = _BY_FOLDED.get(key)
    if entry is None:
        return None
    return ManufacturerMatch(entry, value == entry.name)


def by_host(domain: str) -> Manufacturer | None:
    """Return the company that registered this datasheet domain, or None for an empty or unlisted one.

    The caller passes a registered domain such as "ti.com"; a subdomain or a path is not a match.
    """
    key = domain.strip().casefold()
    if key.endswith("."):
        key = key[:-1]
    return _BY_HOST.get(key)


def token_map() -> dict[str, str]:
    """Return folded name and aliases of every entry with a library token, mapped to that token."""
    return {key: entry.token for key, entry in _BY_FOLDED.items() if entry.token}
