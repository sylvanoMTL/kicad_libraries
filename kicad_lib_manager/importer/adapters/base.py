"""Adapter contract plus the shared locate step that reads names and metadata from inside the files."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from ...kicad_files import (
    SymbolRef,
    file_kind,
    file_version,
    find_models,
    find_property,
    find_symbols,
    footprint_name,
    parse_bytes,
)
from ...models import Issue, Severity
from .. import package as _package
from ..candidate import FootprintItem, ImportCandidate, ModelItem, PartMeta, SymbolItem
from ..package import Package, PackageFile

GENERIC_VENDOR = "Unknown"
GENERIC_CONFIDENCE = 0.1

_BOM = b"\xef\xbb\xbf"
_ASCII_SPACE = b" \t\r\n\x0b\x0c"
_LISTED_NAMES = 20

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


def _read_limited(pf: PackageFile) -> bytes | Issue:
    """Read a symbol or footprint file, refusing anything over the text cap; failures come back as a WARNING Issue.

    The cap counts raw bytes as stored, before any decoding. 3D models never come through here.
    """
    cap = min(_package.MAX_KICAD_TEXT_BYTES, _package.MAX_MEMBER_BYTES)
    try:
        with open(pf.path, "rb") as handle:
            data = handle.read(cap + 1)
    except OSError as e:
        return Issue(Severity.WARNING, "intake.unreadable_file", f"Could not read {pf.member}: {e.strerror or e}")
    if len(data) > cap:
        return Issue(
            Severity.WARNING,
            "intake.unreadable_file",
            f"Skipped {pf.member}: larger than {cap} bytes, the limit for one KiCad symbol or footprint file",
        )
    return data


def _model_magic(member: str) -> tuple[bytes, str] | None:
    """Return the leading bytes and label a 3D model of this name must carry, or None for other suffixes."""
    suffix = PurePosixPath(member).suffix.casefold()
    if suffix in (".step", ".stp"):
        return b"ISO-10303-21;", "a STEP file"
    if suffix == ".wrl":
        return b"#VRML", "a VRML file"
    return None


def _check_model(pf: PackageFile) -> Issue | None:
    """Return a WARNING when a 3D model file does not start with its format's magic text."""
    magic = _model_magic(pf.member)
    if magic is None:
        return None
    try:
        with open(pf.path, "rb") as handle:
            head = handle.read(256)
    except OSError as e:
        return Issue(Severity.WARNING, "intake.unreadable_file", f"Could not read {pf.member}: {e.strerror or e}")
    if head.startswith(_BOM):
        head = head[len(_BOM):]
    head = head.lstrip(_ASCII_SPACE)
    if head.startswith(magic[0]):
        return None
    return Issue(Severity.WARNING, "intake.content_mismatch", f"{pf.member} does not look like {magic[1]}")


def _locate_symbols(pf: PackageFile, loaded, issues: list[Issue]) -> list[SymbolItem]:
    kind = file_kind(loaded.root)
    if kind != "kicad_symbol_lib":
        issues.append(
            Issue(Severity.WARNING, "intake.content_mismatch", f"{pf.member} is not a KiCad symbol library (found {kind})")
        )
        return []
    refs = find_symbols(loaded.root)
    if not refs:
        issues.append(Issue(Severity.WARNING, "intake.content_mismatch", f"{pf.member} holds no symbols"))
        return []
    version = file_version(loaded.root)
    return [SymbolItem(ref.name, pf, part_meta(ref), format_version=version) for ref in refs]


def _locate_footprint(pf: PackageFile, loaded, issues: list[Issue]) -> FootprintItem | None:
    kind = file_kind(loaded.root)
    ref = footprint_name(loaded.root) if kind in ("footprint", "module") else None
    if ref is None:
        issues.append(
            Issue(Severity.WARNING, "intake.content_mismatch", f"{pf.member} is not a KiCad footprint (found {kind})")
        )
        return None
    head = ref.node.head or "footprint"
    if head == "module":
        # D-18: the KiCad 5 spelling is read by KiCad 6+, so it is a footprint, not a legacy file
        issues.append(
            Issue(
                Severity.WARNING,
                "intake.legacy_footprint_syntax",
                f"{pf.member} uses the KiCad 5 (module ...) syntax; it is accepted and KiCad 6+ upgrades it on save",
            )
        )
    return FootprintItem(
        ref.name,
        pf,
        root_head=head,
        format_version=file_version(loaded.root) if head == "footprint" else None,
        model_paths=tuple(m.path for m in find_models(ref.node)),
        has_embedded_files=any(child.head == "embedded_files" for child in ref.node.children),
    )


def _name_list(names: list[str]) -> str:
    """Join up to 20 names with ", " and summarise the rest as "and N more"."""
    shown = ", ".join(names[:_LISTED_NAMES])
    extra = len(names) - _LISTED_NAMES
    return f"{shown}, and {extra} more" if extra > 0 else shown


def _legacy_rules(
    package: Package,
    symbols: list[SymbolItem],
    footprints: list[FootprintItem],
    models: list[ModelItem],
) -> list[Issue]:
    """Apply the KiCad 5 decision matrix (D-10, D-11, D-12, A5) to the located v6+ items."""
    name = package.source.name
    legacy = list(package.legacy)
    symbol_side = [n for n in legacy if PurePosixPath(n).suffix.casefold() in (".lib", ".dcm")]
    footprint_side = [n for n in legacy if PurePosixPath(n).suffix.casefold() == ".mod"]
    sym6, fp6 = bool(symbols), bool(footprints)
    if not sym6 and not fp6:
        if legacy:
            return [
                Issue(
                    Severity.ERROR,
                    "intake.legacy_only",
                    f"{name} only holds KiCad 5 files ({_name_list(legacy)}); re-download as KiCad v6+",
                )
            ]
        return [Issue(Severity.ERROR, "intake.nothing_found", f"{name} holds no KiCad v6+ symbol or footprint")]
    if sym6 and not fp6 and footprint_side:
        return [
            Issue(
                Severity.ERROR,
                "intake.half_legacy",
                f"{name} has a KiCad v6+ symbol but its footprint only exists as KiCad 5 files "
                f"({_name_list(footprint_side)}); re-download as KiCad v6+",
            )
        ]
    if fp6 and not sym6 and symbol_side:
        return [
            Issue(
                Severity.ERROR,
                "intake.half_legacy",
                f"{name} has a KiCad v6+ footprint but its symbol only exists as KiCad 5 files "
                f"({_name_list(symbol_side)}); re-download as KiCad v6+",
            )
        ]
    issues: list[Issue] = []
    if legacy:
        issues.append(
            Issue(Severity.INFO, "intake.legacy_ignored", f"Ignored KiCad 5 files in {name}: {_name_list(legacy)}")
        )
    if not fp6:
        issues.append(Issue(Severity.WARNING, "intake.no_footprint", f"{name} holds a symbol but no footprint"))
    if not sym6:
        issues.append(Issue(Severity.WARNING, "intake.no_symbol", f"{name} holds a footprint but no symbol"))
    if not models:
        issues.append(Issue(Severity.INFO, "intake.no_model", f"{name} holds no 3D model"))
    return issues


def locate(package: Package, detection: Detection) -> tuple[ImportCandidate | None, list[Issue]]:
    """Find the symbols, footprints and models of a staged package; names come from inside the files."""
    issues: list[Issue] = []
    symbols: list[SymbolItem] = []
    footprints: list[FootprintItem] = []
    models: list[ModelItem] = []
    for pf in package.files:
        if pf.kind == "model":
            problem = _check_model(pf)
            if problem is None:
                models.append(ModelItem(PurePosixPath(pf.member).name, pf))
            else:
                issues.append(problem)
            continue
        data = _read_limited(pf)
        if isinstance(data, Issue):
            issues.append(data)
            continue
        loaded = parse_bytes(data, pf.member, max_nodes=_package.MAX_KICAD_TEXT_NODES)
        if isinstance(loaded, Issue):
            issues.append(Issue(Severity.WARNING, "intake.unreadable_file", loaded.text))
            continue
        if pf.kind == "symbol":
            symbols.extend(_locate_symbols(pf, loaded, issues))
        else:
            item = _locate_footprint(pf, loaded, issues)
            if item is not None:
                footprints.append(item)
    issues.extend(_legacy_rules(package, symbols, footprints, models))
    if any(i.severity is Severity.ERROR for i in issues):
        return None, issues
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
