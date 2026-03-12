from dataclasses import dataclass, field


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
    selected: bool = True


@dataclass
class FootprintLibrary:
    nickname: str
    rel_path: str
    source: str
    selected: bool = True


@dataclass
class ScanResult:
    symbol_libs: list[SymbolLibrary] = field(default_factory=list)
    footprint_libs: list[FootprintLibrary] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
