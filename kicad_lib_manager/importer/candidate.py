"""Intake data model: what a vendor package holds, as consumed by the install and GUI phases."""

from dataclasses import dataclass
from pathlib import Path

from ..models import Issue
from .package import PackageFile


@dataclass(frozen=True)
class PartMeta:
    symbol_name: str
    reference: str = ""
    value: str = ""
    datasheet: str = ""
    description: str = ""
    keywords: str = ""
    footprint_field: str = ""
    fp_filters: str = ""
    manufacturer: str = ""
    mpn: str = ""


@dataclass(frozen=True)
class SymbolItem:
    name: str
    file: PackageFile
    meta: PartMeta
    format_version: int | None = None


@dataclass(frozen=True)
class FootprintItem:
    name: str
    file: PackageFile
    root_head: str = "footprint"
    format_version: int | None = None
    model_paths: tuple[str, ...] = ()
    has_embedded_files: bool = False


@dataclass(frozen=True)
class ModelItem:
    filename: str
    file: PackageFile


@dataclass(frozen=True)
class ImportCandidate:
    vendor: str
    confidence: float
    source: Path
    symbols: tuple[SymbolItem, ...]
    footprints: tuple[FootprintItem, ...]
    models: tuple[ModelItem, ...]
    legacy_ignored: tuple[str, ...]
    ignored: tuple[str, ...]
    issues: tuple[Issue, ...]

    @property
    def has_model(self) -> bool:
        return bool(self.models)


@dataclass(frozen=True)
class ExistingLibrary:
    name: str
    has_symbols: bool
    has_footprints: bool
