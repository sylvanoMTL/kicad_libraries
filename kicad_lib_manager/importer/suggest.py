"""Suggest the Atomic_ library for a part: own siblings, KiCad's siblings, the category map, else ask (LIB-04, D-01 to D-07).

The suggestion is only an overridable default and it is always "" or Atomic_ plus an allowed KiCad
library stem, never a manufacturer (D-01). The user-chosen library name is a plain string that
build_plan judges again with stems.name_verdict.

The datasheet helpers (datasheet_host, registered_domain, is_aggregator_host and
manufacturer_from_datasheet) are the one way a datasheet link is turned into a manufacturer; the planner
and the form call manufacturer_from_datasheet (D-23).
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from ..manufacturers import by_host
from ..models import Issue, Severity
from .candidate import PartMeta
from .categories import classify
from .siblings import EMPTY_INDEX, SiblingIndex, SiblingPick, pick
from .stems import ATOMIC_PREFIX, allowed_stems, name_verdict

MAX_ALTERNATIVES = 5

_SLD_LABELS = {"co", "com", "org", "net", "ac", "gov", "edu"}

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
class Alternative:
    """Another library that holds similar parts, as Atomic_<stem> with the number of parts found there."""

    name: str
    count: int


@dataclass(frozen=True)
class LibrarySuggestion:
    """The suggested library: name is "" or Atomic_<allowed stem>; source is "own", "stock", "category" or "ask"."""

    name: str
    source: str
    reason: str
    alternatives: tuple[Alternative, ...]
    related_stems: tuple[str, ...]
    issues: tuple[Issue, ...]
    # True when the library is only a best guess from similar part numbers and nothing in the description confirms it
    weak: bool = False


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


def is_aggregator_host(host: str) -> bool:
    """Return True for a distributor or library site, whatever its TLD."""
    return registered_domain(host.casefold()).split(".")[0] in AGGREGATOR_DOMAINS


def manufacturer_from_datasheet(datasheet: str) -> tuple[str, str | None]:
    """Find the manufacturer a datasheet link names: (canonical name or "", the aggregator host or None).

    Only a registered domain listed in the manufacturer table names a company. A distributor or library
    site never does; its host is returned so the caller can say why nothing was used (D-23).
    """
    host = datasheet_host(datasheet)
    if host is None:
        return "", None
    if is_aggregator_host(host):
        return "", host
    entry = by_host(registered_domain(host.casefold()))
    return (entry.name if entry is not None else ""), None


# -- the Atomic_ suggestion (LIB-04) ---------------------------------------------------------------

NO_STOCK_TEXT = "KiCad's symbol libraries were not found, so similar KiCad parts were not looked up"


def _alternatives(found: SiblingPick | None, chosen: str | None, stems: frozenset[str]) -> tuple[Alternative, ...]:
    """The other counted stems of a pick that are allowed, as Atomic_<stem>, largest first."""
    if found is None:
        return ()
    others = [
        Alternative(ATOMIC_PREFIX + stem, count)
        for stem, count in found.counts
        if stem != chosen and stem in stems
    ]
    return tuple(others[:MAX_ALTERNATIVES])


def _related(chosen: str | None, alternatives: Iterable[Alternative], runner_up: Iterable[str]) -> tuple[str, ...]:
    """The chosen stem, the alternatives' stems, then the category runner-ups, without repeats."""
    stems = [chosen] if chosen else []
    stems.extend(a.name[len(ATOMIC_PREFIX) :] for a in alternatives)
    stems.extend(runner_up)
    return tuple(dict.fromkeys(stems))


def suggest_library(meta: PartMeta, *, own: SiblingIndex = EMPTY_INDEX, stock: SiblingIndex | None = None, allowed: frozenset[str] | None = None) -> LibrarySuggestion:
    """Suggest an Atomic_ library: the owner's siblings, then KiCad's, then the category map, else ask (D-01).

    stock None means KiCad's symbol libraries were not found: that step is skipped with one INFO line
    and the other two still run (D-07). A name that cannot be placed stays "" so the owner decides (D-05).
    """
    stems = allowed_stems() if allowed is None else allowed
    part = meta.mpn or meta.symbol_name
    issues: list[Issue] = []
    last: SiblingPick | None = None

    def decided(found: SiblingPick) -> bool:
        return found.stem is not None and found.stem in stems

    def from_vote(found: SiblingPick, source: str, reason: str) -> LibrarySuggestion:
        """The vote's suggestion; a weak vote yields to the description, is confirmed by it, or is marked weak."""
        alternatives = _alternatives(found, found.stem, stems)
        voted = LibrarySuggestion(
            ATOMIC_PREFIX + str(found.stem), source, reason, alternatives,
            _related(found.stem, alternatives, ()), tuple(issues),
        )
        if not found.weak:
            return voted
        match = classify(meta, stems)
        if match.stem is None:
            return replace(voted, weak=True)
        if match.stem == found.stem:
            return voted
        by_category = _alternatives(found, match.stem, stems)
        return LibrarySuggestion(
            ATOMIC_PREFIX + match.stem, "category", f"Suggested from {match.detail}", by_category,
            _related(match.stem, by_category, match.runner_up), tuple(issues),
        )

    found = pick(own, part)
    if found.counts:
        last = found
    if decided(found):
        count = found.counts[0][1]
        return from_vote(found, "own", f"Suggested from {count} similar parts in your {ATOMIC_PREFIX}{found.stem}")

    if stock is None:
        issues.append(Issue(Severity.INFO, "naming.no_stock_libraries", NO_STOCK_TEXT))
    else:
        found = pick(stock, part)
        if found.counts:
            last = found
        if decided(found):
            count = found.counts[0][1]
            return from_vote(found, "stock", f"Suggested from {count} similar parts in KiCad's {found.stem}")

    match = classify(meta, stems)
    if match.stem is not None:
        alternatives = _alternatives(last, match.stem, stems)
        return LibrarySuggestion(
            ATOMIC_PREFIX + match.stem, "category", f"Suggested from {match.detail}", alternatives,
            _related(match.stem, alternatives, match.runner_up), tuple(issues),
        )

    alternatives = _alternatives(last, None, stems)
    return LibrarySuggestion("", "ask", "", alternatives, _related(None, alternatives, match.runner_up), tuple(issues))


def suggestion_text(suggestion: LibrarySuggestion) -> str:
    """The reason for the tooltip: why the library was suggested, and the other libraries that hold similar parts."""
    others = ", ".join(
        f"{a.name[len(ATOMIC_PREFIX) :] if a.name.startswith(ATOMIC_PREFIX) else a.name} ({a.count})"
        for a in suggestion.alternatives
    )
    if suggestion.reason and others:
        return f"{suggestion.reason}. Other matches: {others}."
    if suggestion.reason:
        return f"{suggestion.reason}."
    if others:
        return f"Similar parts were found in several libraries: {others}."
    return ""


def existing_libraries(names: Iterable[str], allowed: frozenset[str] | None = None) -> list[str]:
    """The names that pass the name rule, sorted ignoring letter case (D-12); v1 and hand-made names drop out."""
    return sorted((n for n in names if name_verdict(n, allowed).ok), key=lambda n: (n.casefold(), n))
