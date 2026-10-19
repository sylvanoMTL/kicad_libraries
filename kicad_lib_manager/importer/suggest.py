"""Suggest a <Type>_<SubCategory>_<Manufacturer> library name for a part (D-01, D-02, D-04)."""

import re
import unicodedata
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

# Manufacturer names as they appear in Custom/ symbols, folded (casefold, letters and digits only)
MANUFACTURER_ALIASES = {
    "texasinstruments": "TI",
    "ti": "TI",
    "analogdevices": "ADI",
    "adi": "ADI",
    "maximintegrated": "ADI",
    "maxim": "ADI",
    "lineartechnology": "ADI",
    "linear": "ADI",
    "tdk": "TDK",
    "invensense": "TDK",
    "tdkinvensense": "TDK",
    "murata": "Murata",
    "muratamanufacturing": "Murata",
    "gct": "GCT",
    "globalconnectortechnology": "GCT",
    "memsic": "Memsic",
    "ublox": "uBlox",
    "abracon": "Abracon",
}
_CORPORATE_WORDS = frozenset(
    {"inc", "ltd", "gmbh", "corp", "corporation", "co", "ag", "llc", "plc", "limited", "incorporated"}
)
# Distributor and library sites: registrable label (first label of the registered domain), any TLD
AGGREGATOR_DOMAINS = frozenset(
    {
        "snapeda",
        "snapmagic",
        "ultralibrarian",
        "componentsearchengine",
        "samacsys",
        "digikey",
        "mouser",
        "octopart",
        "lcsc",
        "arrow",
        "farnell",
        "alldatasheet",
    }
)


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


def is_aggregator_host(host: str) -> bool:
    """Return True for a distributor or library site, whatever its TLD."""
    return registered_domain(host.casefold()).split(".")[0] in AGGREGATOR_DOMAINS


def manufacturer_token(value: str) -> TokenChoice:
    """Map a manufacturer property value to a token: a known name is confident, the first word is a guess."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(c for c in folded if not unicodedata.combining(c)).casefold()
    words = [w for w in re.findall(r"[a-z0-9]+", folded) if w not in _CORPORATE_WORDS]
    if not words:
        return TokenChoice("Manufacturer", "placeholder", False)
    alias = MANUFACTURER_ALIASES.get("".join(words))
    if alias is not None:
        return TokenChoice(alias, "name_alias", True)
    return TokenChoice(words[0][0].upper() + words[0][1:], "property", False)


def manufacturer_choice(meta: PartMeta) -> TokenChoice:
    """Pick the manufacturer token: mapped name, mapped host, unmapped name, host guess, placeholder (D-02)."""
    named = manufacturer_token(meta.manufacturer)
    if named.source == "name_alias":
        return named
    host = datasheet_host(meta.datasheet)
    domain = None
    if host is not None and not is_aggregator_host(host):
        domain = registered_domain(host.casefold())
    if domain is not None:
        token = HOST_TOKENS.get(domain)
        if token is not None:
            return TokenChoice(token, "host_table", True)
    if named.source == "property":
        return named
    if domain is not None:
        label = domain.split(".")[0].replace("-", "")
        if label:
            return TokenChoice(label.capitalize(), "host_guess", False)
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
    host = datasheet_host(meta.datasheet)
    if host is not None and is_aggregator_host(host):
        issues.append(
            Issue(
                Severity.INFO,
                "naming.aggregator_host",
                f"Datasheet host {host} is a distributor or library site; "
                "it was not used as the manufacturer",
            )
        )
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
