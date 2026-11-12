"""read_inventory and migration_reason, the read side of the Atomic_ migration (Phase 13, MIG-02, MIG-03, D-13).

Every Custom/ here is built fresh under tmp_path by migrationfixtures or by hand; the live
Custom/ is never touched.
"""

from migrationfixtures import (
    BAK_FILES,
    FFC_LIBRARY,
    PART_NAMES,
    POWER_LIBRARY,
    USB_LIBRARY,
    WIRELESS_LIBRARY,
    write_v1_custom,
)

from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.inventory import migration_reason, read_inventory
from kicad_lib_manager.importer.package import MAX_KICAD_TEXT_BYTES
from kicad_lib_manager.models import Severity


def test_inventory_lists_every_part(tmp_path):
    layout = write_v1_custom(tmp_path)

    inventory = read_inventory(layout)

    assert inventory.issues == ()
    assert {part.name for part in inventory.parts} == set(PART_NAMES)
    assert len(inventory.parts) == len(PART_NAMES)
    keys = [part.key for part in inventory.parts]
    assert keys == sorted(keys)

    versions = {part.rel_path: part.version for part in inventory.parts}
    assert versions[f"Custom/Symbols/{FFC_LIBRARY}.kicad_sym"] == 20211014
    assert versions[f"Custom/Symbols/{POWER_LIBRARY}.kicad_sym"] == 20231120
    assert versions[f"Custom/Symbols/{WIRELESS_LIBRARY}.kicad_sym"] == 20251024

    ffc = next(part for part in inventory.parts if part.name == "FFC2A32-06-T")
    assert ffc.fields["MF"] == "Global Connector Technology"
    assert ffc.fields["MP"] == "FFC2A32-06-T"
    assert ffc.fields["Description"] == "FFC/FPC connector\nvertical, 32-pin, 0.5mm pitch"
    assert ffc.footprint == f"{FFC_LIBRARY}:FFC2A32-06-T"
    assert ffc.library == FFC_LIBRARY

    for part in inventory.parts:
        assert len(part.block_sha256) == 64
        int(part.block_sha256, 16)  # every character is hex
        assert part.atomic == (part.name == "CM315D32768DZFT")


def test_inventory_links_footprints_and_models(tmp_path):
    layout = write_v1_custom(tmp_path)

    inventory = read_inventory(layout)
    footprints = {(fp.library, fp.name): fp for fp in inventory.footprints}

    dfn8 = footprints[(POWER_LIBRARY, "DFN-8_DDB")]
    assert set(dfn8.linked_by) == {
        (f"Custom/Symbols/{POWER_LIBRARY}.kicad_sym", "LTC2954-1-DFN8"),
        (f"Custom/Symbols/{POWER_LIBRARY}.kicad_sym", "LTC2954-2-DFN8"),
    }
    tsot23 = footprints[(POWER_LIBRARY, "TSOT-23_TS8")]
    assert set(tsot23.linked_by) == {
        (f"Custom/Symbols/{POWER_LIBRARY}.kicad_sym", "LTC2954-1-TSOT-23"),
        (f"Custom/Symbols/{POWER_LIBRARY}.kicad_sym", "LTC2954-2-TSOT-23"),
    }

    nora_fp = footprints[(WIRELESS_LIBRARY, "XCVR_NORA-W106-00B")]
    assert nora_fp.models == ("NORA-W106-00B.step", "NORA-W106-10B.step")
    assert set(nora_fp.linked_by) == {
        (f"Custom/Symbols/{WIRELESS_LIBRARY}.kicad_sym", "NORA-W106-00B"),
        (f"Custom/Symbols/{WIRELESS_LIBRARY}.kicad_sym", "NORA-W106-10B"),
    }

    assert inventory.model_linkers["CM315D32768DZFT.step"] == ("Atomic_Footprints:CM315",)
    assert inventory.model_linkers["NORA-W106-00B.step"] == (f"{WIRELESS_LIBRARY}:XCVR_NORA-W106-00B",)
    assert inventory.model_linkers["NORA-W106-10B.step"] == (f"{WIRELESS_LIBRARY}:XCVR_NORA-W106-00B",)

    board_feature = footprints[("Atomic_Footprints", "USB-A-PCB")]
    assert board_feature.linked_by == ()
    testpoint = footprints[(USB_LIBRARY, "TESTPOINT-1")]
    assert testpoint.linked_by == ()


def test_inventory_lists_bak_files(tmp_path):
    layout = write_v1_custom(tmp_path)

    inventory = read_inventory(layout)

    assert inventory.bak_files == BAK_FILES
    assert list(inventory.bak_files) == sorted(inventory.bak_files)


def test_migration_reason(tmp_path):
    full_layout = write_v1_custom(tmp_path / "full")
    assert migration_reason(full_layout) == f"Custom still has the v1 library {FFC_LIBRARY}"

    clean_root = tmp_path / "clean"
    (clean_root / "Custom" / "Symbols").mkdir(parents=True)
    (clean_root / "Custom" / "Symbols" / "Atomic_Connector.kicad_sym").write_bytes(b"(kicad_symbol_lib)\r\n")
    (clean_root / "Custom" / "Footprints" / "Atomic_Footprints.pretty").mkdir(parents=True)
    clean_layout = RepoLayout.for_repo(clean_root)
    assert migration_reason(clean_layout) is None

    bak_root = tmp_path / "bak"
    (bak_root / "Custom" / "Symbols").mkdir(parents=True)
    (bak_root / "Custom" / "Symbols" / "Atomic_Connector.kicad_sym").write_bytes(b"(kicad_symbol_lib)\r\n")
    (bak_root / "Custom" / "Symbols" / "Old.bak").write_bytes(b"old\r\n")
    (bak_root / "Custom" / "Footprints" / "Atomic_Footprints.pretty").mkdir(parents=True)
    bak_layout = RepoLayout.for_repo(bak_root)
    assert migration_reason(bak_layout) == "Custom/Symbols still holds Old.bak"


def test_inventory_reports_unreadable_library(tmp_path):
    layout = write_v1_custom(tmp_path)
    oversized = layout.symbols_dir / f"{USB_LIBRARY}.kicad_sym"
    oversized.write_bytes(b"x" * (MAX_KICAD_TEXT_BYTES + 1))

    inventory = read_inventory(layout)

    assert len(inventory.issues) == 1
    issue = inventory.issues[0]
    assert issue.severity is Severity.ERROR
    assert issue.code == "migration.unreadable"
    assert f"{USB_LIBRARY}.kicad_sym" in issue.text
    assert not any(part.library == USB_LIBRARY for part in inventory.parts)
    assert len(inventory.parts) == len(PART_NAMES) - 2
    assert any(part.name == "FFC2A32-06-T" for part in inventory.parts)
