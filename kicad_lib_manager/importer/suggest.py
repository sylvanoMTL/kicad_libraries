"""Suggest a <Type>_<SubCategory>_<Manufacturer> library name for a part (D-01, D-02, D-03, D-04).

The suggestion is only an overridable default: the user-chosen library name is a plain
string, and every helper here that Phases 4 and 5 call on it takes a plain string.

D-04 contract: Phases 4 and 5 must refuse to install while placeholder_tokens(name) is
non-empty for the chosen library name.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from ..models import Issue, Severity
from .candidate import ExistingLibrary, PartMeta
from .naming import case_clash, sanitize_name

PLACEHOLDER_TOKENS = ("Type", "SubCategory", "Manufacturer")
MAX_ALTERNATIVES = 5

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
        # Hyphens and any other non-alphanumerics go, so the guess stays one name token
        label = re.sub(r"[^a-z0-9]", "", domain.split(".")[0])
        if label:
            return TokenChoice(label.capitalize(), "host_guess", False)
    return TokenChoice("Manufacturer", "placeholder", False)


def placeholder_tokens(name: str) -> list[str]:
    """Return the placeholder tokens still present in a library name.

    A token matches only as a whole "_"-separated part, case-insensitively. It works on any
    user-edited string. D-04 contract: Phases 4 and 5 must refuse to install while this list
    is non-empty for the chosen library name.
    """
    parts = {part.casefold() for part in name.split("_")}
    return [token for token in PLACEHOLDER_TOKENS if token.casefold() in parts]


def _part_tokens(meta: PartMeta) -> set[str]:
    """Return the whole lower-case words of the description, keywords and value (D-01)."""
    # Existing descriptions hold literal backslash-n escapes and runs of blanks
    text = " ".join((meta.description, meta.keywords, meta.value)).replace("\\n", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return {token for token in re.split(r"[^a-z0-9]+", text) if token}


def _parse_library(name: str) -> tuple[str, tuple[str, ...], str] | None:
    """Split a library name into (type, middle tokens, manufacturer); None when it has fewer than three."""
    tokens = name.split("_")
    if len(tokens) < 3 or not all(tokens):
        return None
    return tokens[0], tuple(tokens[1:-1]), tokens[-1]


def _subcategory(
    type_: TokenChoice, part_tokens: set[str], existing: Sequence[ExistingLibrary]
) -> tuple[TokenChoice, TokenChoice]:
    """Return the (possibly updated) Type and the SubCategory choice from the existing vocabulary (D-01).

    A library matches only when every one of its middle tokens is a whole word of the part
    text; the match with the most middle tokens wins, ties broken by casefolded name. When the
    Type came from the Reference prefix only libraries of that Type count. Spelling rule: the
    SubCategory copies the matched library's middle tokens verbatim, so adding to an existing
    library reuses its exact text; Type and Manufacturer are never re-spelled from the library
    and keep their canonical tokens. An existing ic_battery_charger_ti therefore gives
    IC_battery_charger_TI, which naming.case_clash reports and matches_existing never counts
    as equal (D-16). When the Type was a placeholder it takes the library's own spelling,
    not confident.
    """
    matches = []
    for lib in existing:
        parsed = _parse_library(lib.name)
        if parsed is None:
            continue
        lib_type, middle, _ = parsed
        if type_.source == "reference" and lib_type.casefold() != type_.token.casefold():
            continue
        if all(token.casefold() in part_tokens for token in middle):
            matches.append((-len(middle), lib.name.casefold(), lib.name, lib_type, middle))
    if not matches:
        return type_, TokenChoice("SubCategory", "placeholder", False)
    _, _, _, lib_type, middle = min(matches)
    if type_.source == "placeholder":
        type_ = TokenChoice(lib_type, "vocab", False)
    return type_, TokenChoice("_".join(middle), "vocab", True)


def _rank(
    type_: TokenChoice,
    manufacturer: TokenChoice,
    part_tokens: set[str],
    existing: Sequence[ExistingLibrary],
) -> tuple[RankedLibrary, ...]:
    """Rank existing libraries by 3 x same manufacturer + 2 x same Type + shared middle tokens (D-03)."""
    ranked = []
    for lib in existing:
        parsed = _parse_library(lib.name)
        if parsed is None:
            continue
        lib_type, middle, lib_mfr = parsed
        type_eq = type_.source != "placeholder" and lib_type.casefold() == type_.token.casefold()
        mfr_eq = manufacturer.source != "placeholder" and lib_mfr.casefold() == manufacturer.token.casefold()
        shared = [token for token in middle if token.casefold() in part_tokens]
        score = 3 * mfr_eq + 2 * type_eq + len(shared)
        if score <= 0:
            continue
        tokens = ((lib_type,) if type_eq else ()) + tuple(shared) + ((lib_mfr,) if mfr_eq else ())
        ranked.append(RankedLibrary(lib.name, score, tokens, lib.has_symbols, lib.has_footprints))
    ranked.sort(key=lambda r: (-r.score, r.name.casefold(), r.name))
    return tuple(ranked[:MAX_ALTERNATIVES])


def suggest_library(meta: PartMeta, existing: Sequence[ExistingLibrary] = ()) -> LibrarySuggestion:
    """Suggest a library name for a part; unknown tokens stay as placeholders the user must edit.

    The primary name is built from the part alone plus the existing vocabulary; ranked
    alternatives are only offered beside it and never replace it.
    """
    part_tokens = _part_tokens(meta)
    type_, subcategory = _subcategory(type_choice(meta.reference), part_tokens, existing)
    manufacturer = manufacturer_choice(meta)
    cleaned = sanitize_name("_".join((type_.token, subcategory.token, manufacturer.token)))
    name = cleaned.sanitized
    placeholders = tuple(placeholder_tokens(name))
    choices = (type_, subcategory, manufacturer)
    confidence = "high" if all(c.confident for c in choices) else "low"
    existing_names = [lib.name for lib in existing]
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
    issues.extend(cleaned.issues)
    issues.extend(case_clash(name, existing_names))
    if confidence == "low":
        unsure = ", ".join(f"{c.token} ({c.source})" for c in choices if not c.confident)
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
        matches_existing=name in existing_names,
        alternatives=_rank(type_, manufacturer, part_tokens, existing),
        issues=tuple(issues),
    )
