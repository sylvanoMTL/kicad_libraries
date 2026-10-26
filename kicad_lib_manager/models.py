from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    # Values equal the LogPanel.COLORS keys
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

    def __str__(self) -> str:
        # Python 3.10 has no StrEnum; on 3.12+ f-string formatting goes through __str__
        return self.value


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    text: str


@dataclass
class FootprintRef:
    library_name: str
    footprint_name: str
    found_in_repo: bool = False


STATUS_NEW = "new"
STATUS_CHANGED = "changed"


# Never hashed: params is a dict, so a FixSpec cannot be a set member or dict key
@dataclass(frozen=True)
class FixSpec:
    """A semantic fix, resolved into file edits only at preview time."""
    kind: str
    # repo-relative posix path of the file the fix edits
    rel_path: str
    # the symbol that physically holds the property ("" when not a symbol edit)
    symbol: str
    # plain-language row text shown in the fix dialog
    label: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Violation:
    """One broken atomic rule of one symbol."""
    rule: str
    text: str
    # safe one-click fixes
    fixes: tuple[FixSpec, ...] = ()
    # a template the dialog completes with typed or picked input
    fill: FixSpec | None = None
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    """A non-blocking note about a symbol (leftover data, unknown manufacturer)."""
    kind: str
    text: str
    fix: FixSpec | None = None


@dataclass
class SymbolEntry:
    name: str
    extends: str | None = None
    # STATUS_NEW, STATUS_CHANGED or None
    status: str | None = None
    violations: list[Violation] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def failing(self) -> bool:
        return bool(self.violations)


@dataclass(frozen=True)
class ChangedFootprint:
    name: str
    # STATUS_NEW or STATUS_CHANGED
    status: str


@dataclass
class SymbolLibrary:
    nickname: str
    rel_path: str
    source: str
    footprint_refs: list[FootprintRef] = field(default_factory=list)
    selected: bool = False
    # rel_paths of other symbol libraries with the same nickname (filled by the scan)
    collision_peers: list[str] = field(default_factory=list)
    # True when the atomic rule check applies to this library
    atomic: bool = False
    # Symbols to show as child rows: all checked symbols of an atomic library,
    # or only the new/changed ones of any other Custom library
    symbols: list[SymbolEntry] = field(default_factory=list)
    # Set when the atomic check could not read this library
    check_problem: str | None = None


@dataclass
class FootprintLibrary:
    nickname: str
    rel_path: str
    source: str
    selected: bool = False
    # rel_paths of other footprint libraries with the same nickname (filled by the scan)
    collision_peers: list[str] = field(default_factory=list)
    # Footprints new or changed since the last Custom commit
    changed: list[ChangedFootprint] = field(default_factory=list)


@dataclass
class ScanResult:
    symbol_libs: list[SymbolLibrary] = field(default_factory=list)
    footprint_libs: list[FootprintLibrary] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
