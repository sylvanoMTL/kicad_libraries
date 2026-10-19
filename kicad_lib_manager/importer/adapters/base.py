"""Adapter contract plus the shared locate step that reads names and metadata from inside the files."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from ...kicad_files import SymbolRef, find_models, find_property, find_symbols, footprint_name, parse_bytes
from ...models import Issue, Severity
from ..candidate import FootprintItem, ImportCandidate, ModelItem, PartMeta, SymbolItem
from ..package import Package

GENERIC_VENDOR = "Unknown"
GENERIC_CONFIDENCE = 0.1

MANUFACTURER_FIELDS = ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")
MPN_FIELDS = ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")
DESCRIPTION_FIELDS = ("Description", "ki_description")


@dataclass(frozen=True)
class Detection:
    vendor: str
    confidence: float
    reasons: tuple[str, ...] = ()


class Adapter(Protocol):
    name: str

    def detect(self, package: Package) -> Detection | None: ...


def _prop(symbol: SymbolRef, name: str) -> str:
    found = find_property(symbol.node, name)
    return found.value if found is not None else ""


def _first(symbol: SymbolRef, names: tuple[str, ...]) -> str:
    for name in names:
        value = _prop(symbol, name)
        if value:
            return value
    return ""


def part_meta(symbol: SymbolRef) -> PartMeta:
    """Collect the part metadata the naming step reads from a symbol's properties."""
    return PartMeta(
        symbol_name=symbol.name,
        reference=_prop(symbol, "Reference"),
        value=_prop(symbol, "Value"),
        datasheet=_prop(symbol, "Datasheet"),
        description=_first(symbol, DESCRIPTION_FIELDS),
        keywords=_prop(symbol, "ki_keywords"),
        footprint_field=_prop(symbol, "Footprint"),
        fp_filters=_prop(symbol, "ki_fp_filters"),
        manufacturer=_first(symbol, MANUFACTURER_FIELDS),
        mpn=_first(symbol, MPN_FIELDS),
    )


def locate(package: Package, detection: Detection) -> tuple[ImportCandidate | None, list[Issue]]:
    """Find the symbols, footprints and models of a staged package; names come from inside the files."""
    issues: list[Issue] = []
    symbols: list[SymbolItem] = []
    footprints: list[FootprintItem] = []
    models: list[ModelItem] = []
    for pf in package.files:
        if pf.kind == "model":
            models.append(ModelItem(PurePosixPath(pf.member).name, pf))
            continue
        try:
            data = pf.path.read_bytes()
        except OSError as e:
            issues.append(
                Issue(Severity.WARNING, "intake.unreadable_file", f"Could not read {pf.member}: {e.strerror or e}")
            )
            continue
        loaded = parse_bytes(data, pf.member)
        if isinstance(loaded, Issue):
            issues.append(Issue(Severity.WARNING, "intake.unreadable_file", loaded.text))
            continue
        if pf.kind == "symbol":
            for ref in find_symbols(loaded.root):
                symbols.append(SymbolItem(ref.name, pf, part_meta(ref)))
        else:
            ref = footprint_name(loaded.root)
            if ref is None:
                issues.append(
                    Issue(Severity.WARNING, "intake.content_mismatch", f"{pf.member} holds no footprint")
                )
                continue
            footprints.append(
                FootprintItem(
                    ref.name,
                    pf,
                    root_head=ref.node.head or "footprint",
                    model_paths=tuple(m.path for m in find_models(ref.node)),
                )
            )
    candidate = ImportCandidate(
        vendor=detection.vendor,
        confidence=detection.confidence,
        source=package.source,
        symbols=tuple(symbols),
        footprints=tuple(footprints),
        models=tuple(models),
        legacy_ignored=tuple(package.legacy),
        ignored=tuple(package.ignored),
        issues=tuple(issues),
    )
    return candidate, issues
