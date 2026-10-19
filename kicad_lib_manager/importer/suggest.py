"""Suggest a <Type>_<SubCategory>_<Manufacturer> library name for a part (D-01, D-02, D-04)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from ..models import Issue, Severity
from .candidate import ExistingLibrary, PartMeta

PLACEHOLDER_TOKENS = ("Type", "SubCategory", "Manufacturer")

REFERENCE_TYPE = {
    "U": "IC",
    "IC": "IC",
    "Q": "Transistor",
    "J": "Connector",
    "P": "Connector",
    "CN": "Connector",
    "Y": "Oscillator",
    "X": "Oscillator",
    "XTAL": "Oscillator",
    "C": "Capacitor",
    "L": "Inductor",
    "FB": "Ferrite",
    "D": "Diode",
    "LED": "LED",
    "R": "Resistor",
    "F": "Fuse",
    "SW": "Switch",
    "S": "Switch",
    "K": "Relay",
    "TP": "TestPoint",
    "BT": "Battery",
    "B": "Battery",
}

HOST_TOKENS = {
    "ti.com": "TI",
    "analog.com": "ADI",
    "murata.com": "Murata",
    "tdk.com": "TDK",
    "gct.co": "GCT",
    "memsic.com": "Memsic",
    "u-blox.com": "uBlox",
    "abracon.com": "Abracon",
    "invensense.com": "TDK",
    "maximintegrated.com": "ADI",
    "linear.com": "ADI",
}

_SLD_LABELS = {"co", "com", "org", "net", "ac", "gov", "edu"}


@dataclass(frozen=True)
class TokenChoice:
    token: str
    # reference | vocab | property | name_alias | host_table | host_guess | placeholder
    source: str
    confident: bool


@dataclass(frozen=True)
class RankedLibrary:
    name: str
    score: int
    shared_tokens: tuple[str, ...]
    has_symbols: bool
    has_footprints: bool


@dataclass(frozen=True)
class LibrarySuggestion:
    name: str
    type: TokenChoice
    subcategory: TokenChoice
    manufacturer: TokenChoice
    confidence: str
    placeholders: tuple[str, ...]
    matches_existing: bool
    alternatives: tuple[RankedLibrary, ...]
    issues: tuple[Issue, ...]


def datasheet_host(value: str) -> str | None:
    """Return the host of a datasheet URL, or None for an empty, "~" or host-less value."""
    value = value.strip()
    if not value or value == "~":
        return None
    if "://" not in value and not value.startswith("//"):
        value = "//" + value
    try:
        host = urlsplit(value).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.rstrip(".")
    return host if "." in host else None


def registered_domain(host: str) -> str:
    """Return the registered domain of a host: last two labels, three under a two-letter ccTLD with co/com/..."""
    labels = host.split(".")
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SLD_LABELS:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def type_choice(reference: str) -> TokenChoice:
    """Map the leading letters of a reference designator to a library Type token."""
    match = re.match(r"[A-Za-z]+", reference.strip())
    if match is not None:
        found = REFERENCE_TYPE.get(match.group(0).upper())
        if found is not None:
            return TokenChoice(found, "reference", True)
    return TokenChoice("Type", "placeholder", False)


def manufacturer_choice(meta: PartMeta) -> TokenChoice:
    """Map the datasheet host to a manufacturer suffix through the host table."""
    host = datasheet_host(meta.datasheet)
    if host is not None:
        token = HOST_TOKENS.get(registered_domain(host.casefold()))
        if token is not None:
            return TokenChoice(token, "host_table", True)
    return TokenChoice("Manufacturer", "placeholder", False)


def placeholder_tokens(name: str) -> list[str]:
    """Return the placeholder tokens still present in a library name.

    A token matches only as a whole "_"-separated part, case-insensitively. D-04 contract:
    Phases 4 and 5 refuse to install while this list is non-empty.
    """
    parts = {part.casefold() for part in name.split("_")}
    return [token for token in PLACEHOLDER_TOKENS if token.casefold() in parts]


def suggest_library(meta: PartMeta, existing: Sequence[ExistingLibrary] = ()) -> LibrarySuggestion:
    """Suggest a library name for a part; unknown tokens stay as placeholders the user must edit."""
    type_ = type_choice(meta.reference)
    subcategory = TokenChoice("SubCategory", "placeholder", False)
    manufacturer = manufacturer_choice(meta)
    name = "_".join((type_.token, subcategory.token, manufacturer.token))
    placeholders = tuple(placeholder_tokens(name))
    choices = (type_, subcategory, manufacturer)
    confidence = "high" if all(c.confident for c in choices) else "low"
    issues: list[Issue] = []
    if confidence == "low":
        unsure = ", ".join(c.token for c in choices if not c.confident)
        issues.append(
            Issue(
                Severity.WARNING,
                "naming.low_confidence",
                f"Library name {name} is a low-confidence guess; check {unsure}",
            )
        )
    if placeholders:
        issues.append(
            Issue(
                Severity.WARNING,
                "naming.placeholder",
                f"Library name {name} still contains placeholder token(s) {', '.join(placeholders)}; "
                "edit it before installing",
            )
        )
    return LibrarySuggestion(
        name=name,
        type=type_,
        subcategory=subcategory,
        manufacturer=manufacturer,
        confidence=confidence,
        placeholders=placeholders,
        matches_existing=any(lib.name == name for lib in existing),
        alternatives=(),
        issues=tuple(issues),
    )
