"""Symbol-side behaviour of the Atomic_ migration planner (Phase 13, MIG-02, MIG-03).

Every Custom/ here is built fresh under tmp_path from migrationfixtures/customfixtures/fakecli;
the live Custom/ is never touched. Task 1 (D-01, D-03, D-12, D-22): the whole v1 fixture plans to
its suggested libraries with canonical fields, a refused library name blocks Run, and a part
already in an Atomic_ library is edited in place.
"""

from pathlib import Path

from fakecli import FakeCli
from installfixtures import V10_VERSION, vendor_footprint
from migrationfixtures import (
    ATOMIC_OSCILLATOR,
    FFC_LIBRARY,
    FUEL_GAUGE_LIBRARY,
    IMU_LIBRARY,
    POWER_LIBRARY,
    USB_LIBRARY,
    EXPECTED_TARGETS,
    _tab_lib,
    _tab_symbol,
    write_v1_custom,
    write_v1_stock,
)

from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer import stems
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration import symbols
from kicad_lib_manager.importer.migration.gate import check_plan, end_state_context
from kicad_lib_manager.importer.migration.inventory import read_inventory
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.migration.plan import MigrationChoices, PartChoice, PartKey
from kicad_lib_manager.importer.plan import ToolContext
from kicad_lib_manager.models import Severity

TODAY = "2026-11-11"


def _key(library: str, name: str) -> PartKey:
    return (f"Custom/Symbols/{library}.kicad_sym", name)


def _tools(output_version: int = V10_VERSION, *, kicad_symbols_dir: Path | None = None, **kwargs) -> ToolContext:
    # Mirror detect_tools(): allowed_stems must be computed explicitly, never left at the
    # ToolContext default empty frozenset (that means "nothing is allowed" to the callees that
    # check `is None`, not "use the built-in snapshot").
    allowed = stems.allowed_stems(stems.installed_stems(kicad_symbols_dir))
    return ToolContext(
        kicad_cli=Path("kicad-cli"),
        cli_runner=FakeCli(output_version=output_version),
        kicad_symbols_dir=kicad_symbols_dir,
        allowed_stems=allowed,
        **kwargs,
    )


def _plan_for(layout, choices: MigrationChoices, *, tools: ToolContext | None = None, kicad_fp_dir: Path | None = None):
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, tools or _tools(), kicad_fp_dir, today=TODAY)
    plan = build_migration_plan(inventory, choices, ctx)
    return inventory, plan


# -- Task 1: the whole v1 fixture plans to its suggested libraries with canonical fields ---------


def test_default_targets_follow_the_suggestion(tmp_path):
    layout = write_v1_custom(tmp_path)
    symbols_dir, footprints_dir = write_v1_stock(tmp_path)
    inventory = read_inventory(layout)
    tools = _tools(kicad_symbols_dir=symbols_dir, kicad_footprints_dir=footprints_dir)
    ctx = prepare_context(inventory, tools, footprints_dir, today=TODAY)
    targets = symbols.target_libraries(inventory, MigrationChoices(), ctx)

    # write_v1_stock's own docstring names the sibling-vote cases this synthetic KiCad stand-in
    # supports: the USB parts into Connector, and the IMU-style part into Sensor_Motion at the ICM-
    # step (gap G-13-1-f). Every fixture part EXPECTED_TARGETS names for a *real* KiCad 10 install
    # (full stock libraries) that this stand-in does not carry correctly has no sibling or category
    # evidence here, and stays "" (ask) for the owner to place.
    placed_here = {
        _key("Connector_USB_GCT", "USB4056-03-A_REVA2"): "Atomic_Connector",
        _key("Connector_USB_GCT", "USB4730-GF-A_REVA"): "Atomic_Connector",
        _key(IMU_LIBRARY, "ICM-42688-P"): "Atomic_Sensor_Motion",
    }
    for key, expected in EXPECTED_TARGETS.items():
        if key in placed_here:
            assert targets.get(key) == placed_here[key], key
        else:
            assert targets.get(key, "") == "", key


def test_imu_is_suggested_into_sensor_motion(tmp_path):
    layout = write_v1_custom(tmp_path)
    symbols_dir, footprints_dir = write_v1_stock(tmp_path)
    key = _key(IMU_LIBRARY, "ICM-42688-P")
    inventory = read_inventory(layout)
    tools = _tools(kicad_symbols_dir=symbols_dir, kicad_footprints_dir=footprints_dir)
    ctx = prepare_context(inventory, tools, footprints_dir, today=TODAY)

    suggestion = ctx.suggestions[key]

    assert (suggestion.name, suggestion.source) == ("Atomic_Sensor_Motion", "stock")
    assert symbols.target_libraries(inventory, MigrationChoices(), ctx)[key] == "Atomic_Sensor_Motion"


def test_crystal_stays_in_atomic_oscillator(tmp_path):
    layout = write_v1_custom(tmp_path)
    key = _key(ATOMIC_OSCILLATOR, "CM315D32768DZFT")
    # D-22: the owner keeps the crystal in its current library (the bare suggestion has no sibling
    # or category evidence for a 2-letter MPN prefix and would otherwise ask); this test is about
    # the in-place-edit mechanism once that library is chosen, not about the suggestion itself.
    choices = MigrationChoices(parts={key: PartChoice(library=ATOMIC_OSCILLATOR)})
    inventory, plan = _plan_for(layout, choices)

    part = next(p for p in plan.parts if p.key == key)
    assert part.target_library == ATOMIC_OSCILLATOR
    assert part.issues == ()

    target_rel = f"Custom/Symbols/{ATOMIC_OSCILLATOR}.kicad_sym"
    rels = {(op.kind, op.rel) for op in plan.ops}
    assert ("write", target_rel) in rels
    assert ("delete", target_rel) not in rels

    write_op = next(op for op in plan.ops if op.kind == "write" and op.rel == target_rel)
    loaded = kicad_files.parse_bytes(write_op.data, f"{ATOMIC_OSCILLATOR}.kicad_sym")
    names = [ref.name for ref in kicad_files.find_symbols(loaded.root)]
    assert names == ["CM315D32768DZFT"]  # no duplicate block from the in-place edit


def test_snapeda_fields_become_canonical(tmp_path):
    layout = write_v1_custom(tmp_path)
    key = _key(FFC_LIBRARY, "FFC2A32-06-T")
    choices = MigrationChoices(parts={key: PartChoice(library="Atomic_Connector")})
    inventory, plan = _plan_for(layout, choices)

    part = next(p for p in plan.parts if p.key == key)
    assert part.target_library == "Atomic_Connector"

    write_op = next(op for op in plan.ops if op.kind == "write" and op.rel == "Custom/Symbols/Atomic_Connector.kicad_sym")
    loaded = kicad_files.parse_bytes(write_op.data, "Atomic_Connector.kicad_sym")
    ref = kicad_files.find_symbol(loaded.root, part.new_name)
    fields = {prop.name: prop.value for prop in kicad_files.list_properties(ref.node)}

    assert fields["Manufacturer"] == "Global Connector Technology"
    assert fields["MPN"] == "FFC2A32-06-T"
    assert fields["Value"] == fields["MPN"]
    assert "MF" not in fields
    assert "MP" not in fields
    assert "Price" not in fields
    assert "Check_prices" not in fields
    assert "purchase-url" not in fields

    dropped = {(c.field, c.action) for c in part.field_changes}
    assert ("MF", "rename") in dropped
    assert ("MP", "rename") in dropped
    assert ("Price", "drop") in dropped
    assert ("Check_prices", "drop") in dropped
    assert ("purchase-url", "drop") in dropped


def test_imu_picked_library_passes_gate(tmp_path):
    layout = write_v1_custom(tmp_path)
    symbols_dir, footprints_dir = write_v1_stock(tmp_path)
    key = _key(IMU_LIBRARY, "ICM-42688-P")
    inventory = read_inventory(layout)
    tools = _tools(kicad_symbols_dir=symbols_dir, kicad_footprints_dir=footprints_dir)
    ctx = prepare_context(inventory, tools, footprints_dir, today=TODAY)

    targets = symbols.target_libraries(inventory, MigrationChoices(), ctx)
    assert targets[key] == "Atomic_Sensor_Motion"  # the ICM- step votes into KiCad's Sensor_Motion

    # The owner can still pick the library, with the fields the gate wants
    choices = MigrationChoices(
        parts={
            key: PartChoice(
                library="Atomic_Sensor_Motion",
                manufacturer="TDK InvenSense",
                datasheet="https://invensense.tdk.com/download-pdf/icm-42688-p-datasheet/",
                description="6-axis IMU with accelerometer and gyroscope",
            )
        }
    )
    plan = build_migration_plan(inventory, choices, ctx)
    part = next(p for p in plan.parts if p.key == key)
    assert part.target_library == "Atomic_Sensor_Motion"

    gate_ctx = end_state_context(plan, inventory, footprints_dir)
    outcome = check_plan(plan, inventory, gate_ctx)
    assert not any(line.key == key for line in outcome.lines), outcome.lines


def test_refused_library_name_blocks(tmp_path):
    layout = write_v1_custom(tmp_path)
    key = _key(FFC_LIBRARY, "FFC2A32-06-T")

    for bad_name in ("Atomic_Crystal", "Atomic_TI"):
        choices = MigrationChoices(parts={key: PartChoice(library=bad_name)})
        inventory, plan = _plan_for(layout, choices)
        part = next(p for p in plan.parts if p.key == key)

        assert part.target_library == bad_name
        errors = [i for i in part.issues if i.severity is Severity.ERROR]
        assert len(errors) == 1
        assert errors[0].code == "migration.no_library"

        rels = {(op.kind, op.rel) for op in plan.ops}
        assert ("write", f"Custom/Symbols/{bad_name}.kicad_sym") not in rels

        gate_ctx = end_state_context(plan, inventory, None)
        outcome = check_plan(plan, inventory, gate_ctx)
        assert not outcome.run_enabled
        assert any(line.key == key for line in outcome.lines)


# -- Task 2: names, MPN defaults and clashes (D-05, D-06 MPN rule) -------------------------------

FAMILY_LIBRARY = "LibD_Family"


def _write_family_tree(root: Path) -> RepoLayout:
    """One v1 library holding a parent and a derived part, both renamed-by-MPN candidates."""
    custom = root / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)

    (symbols_dir / f"{FAMILY_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    "PARENT1_REVA",
                    [
                        ("Reference", "U", False),
                        ("Value", "PARENT1_REVA", False),
                        ("Footprint", f"{FAMILY_LIBRARY}:FP1", True),
                        ("Datasheet", "https://example.com/parent.pdf", True),
                        ("Description", "Parent part", True),
                        ("MPN", "PARENT-NEW", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                ),
                _tab_symbol(
                    "CHILD1_REVA",
                    [
                        ("Reference", "U", False),
                        ("Value", "CHILD1_REVA", False),
                        ("Footprint", f"{FAMILY_LIBRARY}:FP1", True),
                        ("Datasheet", "https://example.com/child.pdf", True),
                        ("Description", "Child part", True),
                        ("MPN", "CHILD-NEW", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                    extends="PARENT1_REVA",
                ),
            ],
        )
    )
    pretty = footprints_dir / f"{FAMILY_LIBRARY}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / "FP1.kicad_mod").write_bytes(vendor_footprint("FP1", eol="\r\n"))
    return RepoLayout.for_repo(root)


def test_rename_to_sanitised_mpn(tmp_path):
    layout = write_v1_custom(tmp_path)
    usb_key = _key(USB_LIBRARY, "USB4056-03-A_REVA2")
    ffc_key = _key(FFC_LIBRARY, "FFC2A32-06-T")
    choices = MigrationChoices(
        parts={
            usb_key: PartChoice(library="Atomic_Connector"),
            # A typed MPN with a slash sanitises to an underscore.
            ffc_key: PartChoice(library="Atomic_Connector", mpn="RS3-1212S/H3"),
        }
    )
    inventory, plan = _plan_for(layout, choices)

    usb_part = next(p for p in plan.parts if p.key == usb_key)
    ffc_part = next(p for p in plan.parts if p.key == ffc_key)
    assert usb_part.new_name == "USB4056-03-A"
    assert ffc_part.new_name == "RS3-1212S_H3"
    assert f"{USB_LIBRARY}:USB4056-03-A_REVA2 -> Atomic_Connector:USB4056-03-A" in [
        f"{r.old} -> {r.new}" for r in plan.symbol_renames
    ]

    # A typed symbol_name wins over the MPN and is itself sanitised.
    choices = MigrationChoices(parts={usb_key: PartChoice(library="Atomic_Connector", symbol_name="Weird/Name")})
    inventory, plan = _plan_for(layout, choices)
    usb_part = next(p for p in plan.parts if p.key == usb_key)
    assert usb_part.new_name == "Weird_Name"


def test_shared_default_mpn_is_blanked(tmp_path):
    layout = write_v1_custom(tmp_path)
    inventory = read_inventory(layout)
    choices = MigrationChoices()
    mpns = symbols.part_mpns(inventory, choices)

    ltc_names = ("LTC2954-1-DFN8", "LTC2954-1-TSOT-23", "LTC2954-2-DFN8", "LTC2954-2-TSOT-23")
    for name in ltc_names:
        assert mpns[_key(POWER_LIBRARY, name)] == ""
    assert mpns[_key(FUEL_GAUGE_LIBRARY, "MAX17048G")] == "MAX17048G"
    assert mpns[_key(FUEL_GAUGE_LIBRARY, "MAX17048X")] == "MAX17048X"

    choices = MigrationChoices(parts={_key(POWER_LIBRARY, name): PartChoice(library="Atomic_Power_Management") for name in ltc_names})
    inventory, plan = _plan_for(layout, choices)
    for name in ltc_names:
        part = next(p for p in plan.parts if p.key == _key(POWER_LIBRARY, name))
        assert part.mpn == ""

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)
    assert not outcome.run_enabled
    for name in ltc_names:
        assert any(line.key == _key(POWER_LIBRARY, name) for line in outcome.lines)


def test_typed_mpn_renames_the_part(tmp_path):
    layout = write_v1_custom(tmp_path)
    key = _key(POWER_LIBRARY, "LTC2954-1-DFN8")
    choices = MigrationChoices(
        parts={key: PartChoice(library="Atomic_Power_Management", mpn="LTC2954CTS8-1#TRMPBF")}
    )
    inventory, plan = _plan_for(layout, choices)
    part = next(p for p in plan.parts if p.key == key)
    assert part.mpn == "LTC2954CTS8-1#TRMPBF"
    assert part.new_name == "LTC2954CTS8-1_TRMPBF"  # the symbol name is sanitised; the MPN value is not

    write_op = next(op for op in plan.ops if op.kind == "write" and op.rel == "Custom/Symbols/Atomic_Power_Management.kicad_sym")
    loaded = kicad_files.parse_bytes(write_op.data, "Atomic_Power_Management.kicad_sym")
    ref = kicad_files.find_symbol(loaded.root, part.new_name)
    fields = {prop.name: prop.value for prop in kicad_files.list_properties(ref.node)}
    assert fields["Value"] == "LTC2954CTS8-1#TRMPBF"


def test_name_clash_blocks_run(tmp_path):
    layout = write_v1_custom(tmp_path)
    usb_key = _key(USB_LIBRARY, "USB4056-03-A_REVA2")
    ffc_key = _key(FFC_LIBRARY, "FFC2A32-06-T")
    choices = MigrationChoices(
        parts={
            usb_key: PartChoice(library="Atomic_Connector", symbol_name="CLASH"),
            ffc_key: PartChoice(library="Atomic_Connector", symbol_name="clash"),
        }
    )
    inventory, plan = _plan_for(layout, choices)

    usb_part = next(p for p in plan.parts if p.key == usb_key)
    ffc_part = next(p for p in plan.parts if p.key == ffc_key)
    for part in (usb_part, ffc_part):
        errors = [i for i in part.issues if i.severity is Severity.ERROR and i.code == "migration.name_clash"]
        assert len(errors) == 1
        assert "CLASH" in errors[0].text or "clash" in errors[0].text
        assert USB_LIBRARY in errors[0].text or FFC_LIBRARY in errors[0].text or "Atomic_Connector" in errors[0].text

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)
    assert not outcome.run_enabled
    assert any(line.key == usb_key for line in outcome.lines)
    assert any(line.key == ffc_key for line in outcome.lines)

    # A migrated part named like a part already committed in the target Atomic_ library clashes too.
    choices = MigrationChoices(parts={ffc_key: PartChoice(library=ATOMIC_OSCILLATOR, symbol_name="CM315D32768DZFT")})
    inventory, plan = _plan_for(layout, choices)
    ffc_part = next(p for p in plan.parts if p.key == ffc_key)
    errors = [i for i in ffc_part.issues if i.severity is Severity.ERROR and i.code == "migration.name_clash"]
    assert len(errors) == 1
    rels = {(op.kind, op.rel) for op in plan.ops}
    # The clash blocks the write: the existing Atomic_Oscillator target is left untouched.
    assert ("write", f"Custom/Symbols/{ATOMIC_OSCILLATOR}.kicad_sym") not in rels


def test_rename_follows_extends(tmp_path):
    layout = _write_family_tree(tmp_path)
    parent_key = _key(FAMILY_LIBRARY, "PARENT1_REVA")
    child_key = _key(FAMILY_LIBRARY, "CHILD1_REVA")
    choices = MigrationChoices(
        parts={
            parent_key: PartChoice(library="Atomic_Connector"),
            child_key: PartChoice(library="Atomic_Connector"),
        }
    )
    inventory, plan = _plan_for(layout, choices)

    write_op = next(op for op in plan.ops if op.kind == "write" and op.rel == "Custom/Symbols/Atomic_Connector.kicad_sym")
    loaded = kicad_files.parse_bytes(write_op.data, "Atomic_Connector.kicad_sym")
    names = [ref.name for ref in kicad_files.find_symbols(loaded.root)]
    assert names == ["PARENT-NEW", "CHILD-NEW"]

    child_ref = kicad_files.find_symbol(loaded.root, "CHILD-NEW")
    assert kicad_files.extends_name(child_ref.node) == "PARENT-NEW"

    rename_pairs = {f"{r.old} -> {r.new}" for r in plan.symbol_renames}
    assert f"{FAMILY_LIBRARY}:PARENT1_REVA -> Atomic_Connector:PARENT-NEW" in rename_pairs
    assert f"{FAMILY_LIBRARY}:CHILD1_REVA -> Atomic_Connector:CHILD-NEW" in rename_pairs


def test_parent_in_other_library_blocks(tmp_path):
    layout = _write_family_tree(tmp_path)
    parent_key = _key(FAMILY_LIBRARY, "PARENT1_REVA")
    child_key = _key(FAMILY_LIBRARY, "CHILD1_REVA")
    choices = MigrationChoices(
        parts={
            parent_key: PartChoice(library="Atomic_Connector"),
            child_key: PartChoice(library="Atomic_LED"),
        }
    )
    inventory, plan = _plan_for(layout, choices)

    child_part = next(p for p in plan.parts if p.key == child_key)
    errors = [i for i in child_part.issues if i.severity is Severity.ERROR and i.code == "migration.parent_elsewhere"]
    assert len(errors) == 1

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)
    assert not outcome.run_enabled


# -- Task 3: keywords, one file format per library, and the missing-tool block (D-11, F-13, A4) --


KEYWORD_LIBRARY = "LibE_Keywords"


def _write_keyword_part(root: Path) -> RepoLayout:
    """One v1 part whose ki_keywords is already "usb receptacle"."""
    custom = root / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)
    (symbols_dir / f"{KEYWORD_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    "USB4199-GF-A",
                    [
                        ("Reference", "U", False),
                        ("Value", "USB4199-GF-A", False),
                        ("Footprint", f"{KEYWORD_LIBRARY}:FP1", True),
                        ("Datasheet", "https://example.com/usb4199.pdf", True),
                        ("Description", "USB Type-C receptacle", True),
                        ("MPN", "USB4199-GF-A", True),
                        ("Manufacturer", "Global Connector Technology", True),
                        ("ki_keywords", "usb receptacle", True),
                    ],
                ),
            ],
        )
    )
    pretty = footprints_dir / f"{KEYWORD_LIBRARY}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / "FP1.kicad_mod").write_bytes(vendor_footprint("FP1", eol="\r\n"))
    return RepoLayout.for_repo(root)


def test_keywords_merge_existing_first(tmp_path):
    layout = _write_keyword_part(tmp_path)
    key = _key(KEYWORD_LIBRARY, "USB4199-GF-A")

    choices = MigrationChoices(parts={key: PartChoice(library="Atomic_Connector")})
    inventory, plan = _plan_for(layout, choices)
    part = next(p for p in plan.parts if p.key == key)
    written_words = part.part_text.keywords.split()
    assert written_words[:2] == ["usb", "receptacle"]
    assert len(written_words) > 2  # generated words not already present follow
    assert part.generated_text.keywords == part.part_text.keywords  # no override typed

    choices = MigrationChoices(parts={key: PartChoice(library="Atomic_Connector", keywords="exact words")})
    inventory, plan = _plan_for(layout, choices)
    part = next(p for p in plan.parts if p.key == key)
    assert part.part_text.keywords == "exact words"
    # the generated text (what the generator would have produced) differs from the typed override
    assert part.generated_text.keywords != "exact words"
    assert part.generated_text.keywords.split()[:2] == ["usb", "receptacle"]


def test_existing_target_in_older_format_is_normalised(tmp_path):
    layout = write_v1_custom(tmp_path)
    key = _key(FFC_LIBRARY, "FFC2A32-06-T")
    tools = _tools(output_version=20251024)
    choices = MigrationChoices(parts={key: PartChoice(library=ATOMIC_OSCILLATOR)})
    inventory, plan = _plan_for(layout, choices, tools=tools)

    target_rel = f"Custom/Symbols/{ATOMIC_OSCILLATOR}.kicad_sym"
    write_op = next(op for op in plan.ops if op.kind == "write" and op.rel == target_rel)
    loaded = kicad_files.parse_bytes(write_op.data, f"{ATOMIC_OSCILLATOR}.kicad_sym")
    assert kicad_files.file_version(loaded.root) == 20251024
    names = [ref.name for ref in kicad_files.find_symbols(loaded.root)]
    assert set(names) == {"CM315D32768DZFT", "FFC2A32-06-T"}
    for name in names:
        ref = kicad_files.find_symbol(loaded.root, name)
        assert ref is not None  # both blocks parse

    part = next(p for p in plan.parts if p.key == key)
    assert any(c.reason == "file format updated" for c in part.field_changes)


def test_missing_cli_blocks_run(tmp_path):
    layout = write_v1_custom(tmp_path)
    key = _key(FFC_LIBRARY, "FFC2A32-06-T")
    choices = MigrationChoices(parts={key: PartChoice(library="Atomic_Connector")})
    inventory = read_inventory(layout)
    tools = ToolContext(kicad_cli=None, allowed_stems=stems.allowed_stems())
    ctx = prepare_context(inventory, tools, None, today=TODAY)
    plan = build_migration_plan(inventory, choices, ctx)

    errors = [i for i in plan.issues if i.severity is Severity.ERROR and i.code == "migration.cli_missing"]
    assert len(errors) == 1
    assert "KiCad command-line tool" in errors[0].text
    assert not any(op.kind == "write" and op.rel.endswith(".kicad_sym") for op in plan.ops)

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)
    assert not outcome.run_enabled


def test_all_targets_share_one_format(tmp_path):
    layout = write_v1_custom(tmp_path)
    choices = MigrationChoices(parts={key: PartChoice(library=target) for key, target in EXPECTED_TARGETS.items()})
    inventory, plan = _plan_for(layout, choices, tools=_tools(output_version=V10_VERSION))

    versions = set()
    for op in plan.ops:
        if op.kind == "write" and op.rel.endswith(".kicad_sym"):
            loaded = kicad_files.parse_bytes(op.data, Path(op.rel).name)
            version = kicad_files.file_version(loaded.root)
            assert version is not None
            versions.add(version)
    assert versions == {V10_VERSION}
