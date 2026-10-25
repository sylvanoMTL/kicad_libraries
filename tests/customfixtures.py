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

from installfixtures import target_lib, vendor_footprint
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR
from zipfixtures import STEP_BYTES

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
