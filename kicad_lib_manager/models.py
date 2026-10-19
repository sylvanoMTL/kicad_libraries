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


@dataclass
class SymbolLibrary:
    nickname: str
    rel_path: str
    source: str
    footprint_refs: list[FootprintRef] = field(default_factory=list)
    selected: bool = False
    # rel_paths of other symbol libraries with the same nickname (filled by the scan)
    collision_peers: list[str] = field(default_factory=list)


@dataclass
class FootprintLibrary:
    nickname: str
    rel_path: str
    source: str
    selected: bool = False
    # rel_paths of other footprint libraries with the same nickname (filled by the scan)
    collision_peers: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    symbol_libs: list[SymbolLibrary] = field(default_factory=list)
    footprint_libs: list[FootprintLibrary] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
