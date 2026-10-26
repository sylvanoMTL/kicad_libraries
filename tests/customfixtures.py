"""The synthetic Custom/ the writing tests install into, instead of a copy of the live tree (D-01).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so pytest does
not collect it. Test modules import it with ``from customfixtures import ...``, like
``zipfixtures``. ``write_synthetic_custom`` writes only under the root it is given and never
reads the repo's own Custom/; every byte comes from the ``installfixtures`` and ``zipfixtures``
builders. The owner's real parts (the Ultra Librarian sample among them) are therefore absent
by construction, whatever the live Custom/ holds on the day.
"""

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from installfixtures import V10_VERSION, _tree, _v10_pin, _v10_property, target_lib, vendor_footprint
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR
from zipfixtures import STEP_BYTES, _quote

# Today's v1 library names (D-02). IC_MOSFET_Dual_TI is the one a new-library test creates.
BATTERY_CHARGER = "IC_Battery_Charger_TI"
IMU = "IC_IMU_TDK"
MAGNETOMETER = "IC_Magnetometer_Memsic"
POWER_MOSFET = "IC_PowerManagementMosfet_TI"
WIRELESS = "IC_Wireless_BLE_uBlox"
ABSENT_LIBRARY = "IC_MOSFET_Dual_TI"
UL_PART_TOKENS = ("CSD85301Q2", "DQK0006B", "DLV0006A")

# One library per symbol format version the real Custom/ holds
FORMAT_VERSIONS = (20211014, 20231120, 20241209, 20251024)


@dataclass(frozen=True)
class SyntheticLibrary:
    """One library of the synthetic Custom/; an empty footprints tuple means no .pretty folder.

    Footprint i links models[i] when that index exists.
    """

    name: str
    version: int
    symbols: tuple[str, ...]
    footprints: tuple[str, ...]
    models: tuple[str, ...]


# The single inventory source; later phases append their libraries here
SYNTHETIC_LIBRARIES = (
    SyntheticLibrary(
        BATTERY_CHARGER,
        20211014,
        ("BQ25180YBGR", "BQ24072RGTR"),
        ("BGA8N40P2X4", "QFN-16_RGT"),
        ("BQ25180YBGR.step",),
    ),
    SyntheticLibrary(IMU, 20231120, ("ICM-42688-P",), (), ()),
    SyntheticLibrary(
        MAGNETOMETER, 20241209, ("MMC5983MA",), ("LGA-16_MMC5983MA",), ("MMC5983MA.step",)
    ),
    SyntheticLibrary(
        POWER_MOSFET, 20241209, ("TPS22918DBVR",), ("SOT-23-6_DBV",), ("TPS22918DBVR.step",)
    ),
    SyntheticLibrary(
        WIRELESS,
        20251024,
        ("NORA-W106-00B", "NORA-W106-10B"),
        ("NORA-W1",),
        ("NORA-W106-00B.step",),
    ),
)


def write_synthetic_custom(root: Path) -> RepoLayout:
    """Write the SYNTHETIC_LIBRARIES under root/Custom and return the layout over root."""
    custom = root / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)
    for lib in SYNTHETIC_LIBRARIES:
        (symbols_dir / f"{lib.name}.kicad_sym").write_bytes(target_lib(lib.version, lib.symbols))
        if lib.footprints:
            pretty = footprints_dir / f"{lib.name}.pretty"
            pretty.mkdir(parents=True, exist_ok=True)
            for index, footprint in enumerate(lib.footprints):
                model = f"{MODEL_DIR_VAR}/{lib.models[index]}" if index < len(lib.models) else None
                (pretty / f"{footprint}.kicad_mod").write_bytes(vendor_footprint(footprint, model=model))
        for model_name in lib.models:
            (models_dir / model_name).write_bytes(STEP_BYTES)
    return RepoLayout.for_repo(root)


# ── Atomic_ libraries (Phase 9) ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AtomicSymbol:
    """One symbol of an atomic fixture library; props exclude Reference, which is always written first."""

    name: str
    props: tuple[tuple[str, str], ...]
    extends: str | None = None


@dataclass(frozen=True)
class AtomicLibrary:
    """One .kicad_sym of the atomic inventory; folder is repo-relative and posix."""

    name: str
    symbols: tuple[AtomicSymbol, ...]
    folder: str = "Custom/Symbols"


ATOMIC_FOOTPRINTS = "Atomic_Footprints"
ATOMIC_FOOTPRINT_NAMES = ("USB4105-GF-A", "GENERIC-2PIN")
_ATOMIC_CUSTOM_PREFIX = "Custom/"
# 3D model cases, each a footprint in Atomic_Footprints.pretty: (footprint name, model path or None for no model line)
ATOMIC_MODEL_FOOTPRINTS = (
    ("NO-MODEL", None),
    ("MISSING-MODEL", f"{MODEL_DIR_VAR}/MISSING-MODEL.step"),
    ("WRONG-CASE-MODEL", f"{MODEL_DIR_VAR}/wrong-case.step"),
    ("OTHER-VAR-MODEL", "${KIPRJMOD}/x.step"),
)
# The one model file those cases sit next to: only the exact name WRONG-CASE.step exists
ATOMIC_WRONG_CASE_MODEL = "WRONG-CASE.step"
# One footprint library name written twice (under Custom/ and under Other/), so its nickname is ambiguous
ATOMIC_DUP_LIBRARY = "Dup_Footprints"
ATOMIC_DUP_FOOTPRINT = "DUP-1"
# The one stock KiCad footprint the fake KiCad install holds, and the model it links
OFFICIAL_LIBRARY = "Package_TO_SOT_SMD"
OFFICIAL_FOOTPRINT = "SOT-23-5"
OFFICIAL_MODEL = f"{OFFICIAL_LIBRARY}.3dshapes/{OFFICIAL_FOOTPRINT}.step"


def atomic_part(
    name: str,
    *,
    replace: dict[str, str] | None = None,
    drop: tuple[str, ...] = (),
    extra: tuple[tuple[str, str], ...] = (),
    extends: str | None = None,
) -> AtomicSymbol:
    """Build a symbol that passes every atomic rule, then apply replace, drop and extra.

    Default properties in order: Value=name, Footprint, Datasheet, Description, MPN=name,
    Manufacturer. replace overrides a default value, drop removes defaults by name, extra
    appends (name, value) pairs after them.
    """
    replace = replace or {}
    defaults = (
        ("Value", name),
        ("Footprint", f"{ATOMIC_FOOTPRINTS}:GENERIC-2PIN"),
        ("Datasheet", f"https://example.com/{name}.pdf"),
        ("Description", f"Test part {name}"),
        ("MPN", name),
        ("Manufacturer", "Global Connector Technology"),
    )
    props = tuple((key, replace.get(key, value)) for key, value in defaults if key not in drop)
    return AtomicSymbol(name, props + tuple(extra), extends)


def _atomic_symbol_tree(symbol: AtomicSymbol) -> tuple:
    props = (_v10_property("Reference", "U", hide=False),) + tuple(
        _v10_property(key, value, hide=key != "Value") for key, value in symbol.props
    )
    if symbol.extends is not None:
        # A derived symbol as KiCad 10 writes it: the parent link, its own properties, no drawing
        return ("symbol", _quote(symbol.name), ("extends", _quote(symbol.extends)), *props, ("embedded_fonts", "no"))
    return (
        "symbol", _quote(symbol.name),
        ("exclude_from_sim", "no"),
        ("in_bom", "yes"),
        ("on_board", "yes"),
        ("in_pos_files", "yes"),
        ("duplicate_pin_numbers_are_jumpers", "no"),
        *props,
        (
            "symbol", _quote(f"{symbol.name}_1_1"),
            _v10_pin("1", x="-5.08", angle="0"),
            _v10_pin("2", x="5.08", angle="180"),
        ),
        ("embedded_fonts", "no"),
    )


def atomic_lib(symbols: tuple[AtomicSymbol, ...], *, eol: str = "\n") -> bytes:
    """Build a KiCad 10 (20251024) .kicad_sym holding the given symbols in order."""
    library = (
        "kicad_symbol_lib",
        ("version", str(V10_VERSION)),
        ("generator", _quote("kicad_symbol_editor")),
        ("generator_version", _quote("10.0")),
        *(_atomic_symbol_tree(symbol) for symbol in symbols),
    )
    return (eol.join(_tree(library)) + eol).encode("utf-8")


# The single atomic inventory source; every symbol of an Atomic_ library must pass every rule
# that is not named in ATOMIC_EXPECTED for it.
ATOMIC_LIBRARIES = (
    AtomicLibrary(
        "Atomic_Connector",
        (
            atomic_part("USB4105-GF-A", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:USB4105-GF-A"}),
            atomic_part("DS-EMPTY", replace={"Datasheet": "~"}),
            atomic_part("DS-WORDS", replace={"Datasheet": "see website"}),
            atomic_part("DESC-EMPTY", replace={"Description": ""}),
            atomic_part("MPN-NONE", drop=("MPN",)),
            atomic_part("MPN-AS-MP", drop=("MPN",), extra=(("MP", "MPN-AS-MP"),)),
            atomic_part("MFR-NONE", drop=("Manufacturer",)),
            atomic_part("MFR-AS-MF", drop=("Manufacturer",), extra=(("MF", "GCT"),)),
            atomic_part("MFR-SHORT", replace={"Manufacturer": "TI"}),
            atomic_part(
                "MFR-DUP-OK",
                drop=("Manufacturer",),
                extra=(("MF", "GCT"), ("MANUFACTURER", "Global Connector Technology")),
            ),
            atomic_part(
                "MFR-DUP-BAD", drop=("Manufacturer",), extra=(("MF", "GCT"), ("MANUFACTURER", "Molex"))
            ),
            atomic_part("FFC-0.5-20", replace={"Value": "FFC20", "MPN": "FH12-20S-0.5SH"}),
            # Price and stock leftovers and an unknown manufacturer are notes, never failures
            atomic_part(
                "LEFTOVER-1",
                extra=(("Price", "1.20"), ("Availability", "In stock"), ("Check_prices", "https://example.com/p")),
            ),
            atomic_part("MFR-HIROSE", replace={"Manufacturer": "Hirose"}),
            # Footprint rule: each way the field can fail to name exactly one existing footprint
            atomic_part("FP-EMPTY", replace={"Footprint": ""}),
            atomic_part("FP-NOLIB", replace={"Footprint": "GENERIC-2PIN"}),
            atomic_part("FP-UNKNOWN-LIB", replace={"Footprint": "Nope_Library:GENERIC-2PIN"}),
            atomic_part("FP-MISSING", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:NOT-THERE"}),
            atomic_part("FP-WRONG-CASE", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:generic-2pin"}),
            atomic_part("FP-AMBIG", replace={"Footprint": f"{ATOMIC_DUP_LIBRARY}:{ATOMIC_DUP_FOOTPRINT}"}),
            # A stock KiCad footprint, found only when the scan is given the fake KiCad folders
            atomic_part("OFFICIAL-FP", replace={"Footprint": f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"}),
            # 3D model rule: each way the linked footprint's model can fail
            atomic_part("MODEL-NONE", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:NO-MODEL"}),
            atomic_part("MODEL-MISSING", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:MISSING-MODEL"}),
            atomic_part("MODEL-WRONG-CASE", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:WRONG-CASE-MODEL"}),
            atomic_part("MODEL-OTHER-VAR", replace={"Footprint": f"{ATOMIC_FOOTPRINTS}:OTHER-VAR-MODEL"}),
        ),
    ),
    AtomicLibrary("Atomic_Empty", ()),
    # Variants: each derived symbol is judged on its own fields, a missing one is taken from the parent
    AtomicLibrary(
        "Atomic_Regulator",
        (
            atomic_part("TLV75533PDBVR", replace={"Manufacturer": "Texas Instruments"}),
            atomic_part("TLV75518PDBVR", drop=("Manufacturer",), extends="TLV75533PDBVR"),
            atomic_part(
                "TLV75525PDBVR",
                replace={"Manufacturer": "Texas Instruments"},
                drop=("MPN",),
                extends="TLV75533PDBVR",
            ),
            atomic_part(
                "TLV75530PDBVR",
                replace={"Manufacturer": "Texas Instruments", "Datasheet": "~"},
                extends="TLV75533PDBVR",
            ),
        ),
    ),
    # KiCad refuses a missing parent, so this library stays out of the kicad-cli load test
    AtomicLibrary(
        "Atomic_Orphan",
        (atomic_part("ORPHAN-1", drop=("Manufacturer",), extends="NOT-THERE"),),
    ),
    # Never checked: none carries the exact Atomic_ prefix, whatever its Datasheet says
    AtomicLibrary("Connector_Legacy", (atomic_part("LEGACY-1", replace={"Datasheet": ""}),)),
    AtomicLibrary("atomic_Lower", (atomic_part("LOWER-1", replace={"Datasheet": ""}),)),
    AtomicLibrary("ATOMIC_Upper", (atomic_part("UPPER-1", replace={"Datasheet": ""}),)),
    AtomicLibrary("AtomicNoUnderscore", (atomic_part("NOUNDERSCORE-1", replace={"Datasheet": ""}),)),
    AtomicLibrary(
        "WE-Connectors",
        (atomic_part("WE-1", replace={"Datasheet": ""}),),
        folder="WurthElektronik/KiCad-Library/symbols",
    ),
    # Judged like any Atomic_ library, but outside Custom/, so it gets no fix and no fill
    AtomicLibrary(
        "Atomic_Elsewhere",
        (atomic_part("ELSEWHERE-1", replace={"Datasheet": ""}),),
        folder="Other/Symbols",
    ),
)

# (library, symbol) -> the rule ids expected to fail, for every symbol of every Atomic_ library
ATOMIC_EXPECTED: dict[tuple[str, str], frozenset[str]] = {
    ("Atomic_Connector", "USB4105-GF-A"): frozenset(),
    ("Atomic_Connector", "DS-EMPTY"): frozenset({"datasheet"}),
    ("Atomic_Connector", "DS-WORDS"): frozenset({"datasheet"}),
    ("Atomic_Connector", "DESC-EMPTY"): frozenset({"description"}),
    ("Atomic_Connector", "MPN-NONE"): frozenset({"mpn"}),
    ("Atomic_Connector", "MPN-AS-MP"): frozenset({"mpn"}),
    ("Atomic_Connector", "MFR-NONE"): frozenset({"manufacturer"}),
    ("Atomic_Connector", "MFR-AS-MF"): frozenset({"manufacturer"}),
    ("Atomic_Connector", "MFR-SHORT"): frozenset({"manufacturer"}),
    ("Atomic_Connector", "MFR-DUP-OK"): frozenset({"manufacturer"}),
    ("Atomic_Connector", "MFR-DUP-BAD"): frozenset({"manufacturer"}),
    ("Atomic_Connector", "FFC-0.5-20"): frozenset({"value"}),
    ("Atomic_Connector", "LEFTOVER-1"): frozenset(),
    ("Atomic_Connector", "MFR-HIROSE"): frozenset(),
    ("Atomic_Connector", "FP-EMPTY"): frozenset({"footprint"}),
    ("Atomic_Connector", "FP-NOLIB"): frozenset({"footprint"}),
    ("Atomic_Connector", "FP-UNKNOWN-LIB"): frozenset({"footprint"}),
    ("Atomic_Connector", "FP-MISSING"): frozenset({"footprint"}),
    ("Atomic_Connector", "FP-WRONG-CASE"): frozenset({"footprint"}),
    ("Atomic_Connector", "FP-AMBIG"): frozenset({"footprint"}),
    ("Atomic_Connector", "OFFICIAL-FP"): frozenset(),
    ("Atomic_Connector", "MODEL-NONE"): frozenset({"model_3d"}),
    ("Atomic_Connector", "MODEL-MISSING"): frozenset({"model_3d"}),
    ("Atomic_Connector", "MODEL-WRONG-CASE"): frozenset({"model_3d"}),
    ("Atomic_Connector", "MODEL-OTHER-VAR"): frozenset({"model_3d"}),
    ("Atomic_Regulator", "TLV75533PDBVR"): frozenset(),
    ("Atomic_Regulator", "TLV75518PDBVR"): frozenset(),
    ("Atomic_Regulator", "TLV75525PDBVR"): frozenset({"mpn"}),
    ("Atomic_Regulator", "TLV75530PDBVR"): frozenset({"datasheet"}),
    ("Atomic_Orphan", "ORPHAN-1"): frozenset({"manufacturer"}),
    ("Atomic_Elsewhere", "ELSEWHERE-1"): frozenset({"datasheet"}),
}


def write_atomic_files(custom_dir: Path) -> None:
    """Write the Custom/ part of the atomic inventory directly under custom_dir.

    Symbol libraries whose folder starts with Custom/, the Atomic_Footprints.pretty folder
    and the STEP files its footprints link.
    """
    for lib in ATOMIC_LIBRARIES:
        if not lib.folder.startswith(_ATOMIC_CUSTOM_PREFIX):
            continue
        folder = custom_dir / lib.folder[len(_ATOMIC_CUSTOM_PREFIX):]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{lib.name}.kicad_sym").write_bytes(atomic_lib(lib.symbols))
    pretty = custom_dir / "Footprints" / f"{ATOMIC_FOOTPRINTS}.pretty"
    models = custom_dir / "3DModels"
    pretty.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)
    for name in ATOMIC_FOOTPRINT_NAMES:
        (pretty / f"{name}.kicad_mod").write_bytes(vendor_footprint(name, models=(f"{MODEL_DIR_VAR}/{name}.step",)))
        (models / f"{name}.step").write_bytes(STEP_BYTES)
    for name, model in ATOMIC_MODEL_FOOTPRINTS:
        links = (model,) if model is not None else ()
        (pretty / f"{name}.kicad_mod").write_bytes(vendor_footprint(name, models=links))
    (models / ATOMIC_WRONG_CASE_MODEL).write_bytes(STEP_BYTES)
    _write_dup_footprint(custom_dir / "Footprints")


def _write_dup_footprint(footprints_dir: Path) -> None:
    """Write Dup_Footprints.pretty/DUP-1.kicad_mod under footprints_dir, linking an existing Custom model."""
    pretty = footprints_dir / f"{ATOMIC_DUP_LIBRARY}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    model = f"{MODEL_DIR_VAR}/{ATOMIC_FOOTPRINT_NAMES[1]}.step"
    (pretty / f"{ATOMIC_DUP_FOOTPRINT}.kicad_mod").write_bytes(vendor_footprint(ATOMIC_DUP_FOOTPRINT, models=(model,)))


def write_fake_kicad(root: Path) -> tuple[Path, Path]:
    """Write a stand-in KiCad install under root/kicad and return (footprints dir, 3dmodels dir).

    It holds one stock footprint, Package_TO_SOT_SMD:SOT-23-5, and the model that footprint links,
    laid out like the real share/kicad folders (3dmodels next to footprints).
    """
    footprints = root / "kicad" / "footprints"
    models = root / "kicad" / "3dmodels"
    pretty = footprints / f"{OFFICIAL_LIBRARY}.pretty"
    shapes = models / f"{OFFICIAL_LIBRARY}.3dshapes"
    pretty.mkdir(parents=True, exist_ok=True)
    shapes.mkdir(parents=True, exist_ok=True)
    link = f"${{KICAD10_3DMODEL_DIR}}/{OFFICIAL_MODEL}"
    (pretty / f"{OFFICIAL_FOOTPRINT}.kicad_mod").write_bytes(vendor_footprint(OFFICIAL_FOOTPRINT, model=link))
    (shapes / f"{OFFICIAL_FOOTPRINT}.step").write_bytes(STEP_BYTES)
    return footprints, models


def write_atomic_custom(root: Path) -> RepoLayout:
    """Write the atomic inventory under root (Custom/ part plus libraries elsewhere) and return the layout."""
    write_atomic_files(root / "Custom")
    for lib in ATOMIC_LIBRARIES:
        if lib.folder.startswith(_ATOMIC_CUSTOM_PREFIX):
            continue
        folder = root / lib.folder
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{lib.name}.kicad_sym").write_bytes(atomic_lib(lib.symbols))
    # The second Dup_Footprints, outside Custom/, makes the nickname ambiguous
    _write_dup_footprint(root / "Other" / "Footprints")
    return RepoLayout.for_repo(root)


# ── Write-protect guard over the live Custom/ (D-13) ─────────────────────────────────────────

WATCHED_FOLDERS = ("Symbols", "Footprints", "3DModels")
_SHOWN_CHANGES = 10


def digest_tree(root: Path) -> dict[str, str]:
    """Map a folder to {relative path: sha256} for files and {relative path/: "dir"} for folders."""
    found: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            found[rel + "/"] = "dir"
        else:
            found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def digest_custom(custom_dir: Path) -> dict[str, str] | None:
    """Digest Symbols, Footprints and 3DModels under custom_dir; None when there is no Symbols folder.

    None covers a Custom submodule that is not checked out (the folder is absent or empty).
    """
    if not (custom_dir / "Symbols").is_dir():
        return None
    found: dict[str, str] = {}
    for name in WATCHED_FOLDERS:
        folder = custom_dir / name
        if folder.is_dir():
            found[f"{name}/"] = "dir"
            for key, value in digest_tree(folder).items():
                found[f"{name}/{key}"] = value
    return found


def custom_changes(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Return, sorted, every key that was added, removed or changed between two digests."""
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


def guard_custom(custom_dir: Path) -> Iterator[None]:
    """Digest custom_dir, yield, then fail the run when the digest moved (use with yield from).

    Does nothing when there was no Custom/ to watch at the start. An absent tree afterwards
    counts as empty, so deleting the whole tree is reported too.
    """
    before = digest_custom(custom_dir)
    yield
    if before is None:
        return
    changed = custom_changes(before, digest_custom(custom_dir) or {})
    if not changed:
        return
    message = "the test run changed the live Custom/ folder: " + ", ".join(changed[:_SHOWN_CHANGES])
    if len(changed) > _SHOWN_CHANGES:
        message += f" and {len(changed) - _SHOWN_CHANGES} more"
    pytest.fail(message, pytrace=False)
