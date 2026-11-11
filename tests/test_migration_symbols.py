"""Symbol-side behaviour of the Atomic_ migration planner (Phase 13, MIG-02, MIG-03).

Every Custom/ here is built fresh under tmp_path from migrationfixtures/customfixtures/fakecli;
the live Custom/ is never touched. Task 1 (D-01, D-03, D-12, D-22): the whole v1 fixture plans to
its suggested libraries with canonical fields, a refused library name blocks Run, and a part
already in an Atomic_ library is edited in place.
"""

from pathlib import Path

from fakecli import FakeCli
from installfixtures import V10_VERSION
from migrationfixtures import (
    ATOMIC_OSCILLATOR,
    FFC_LIBRARY,
    IMU_LIBRARY,
    EXPECTED_TARGETS,
    write_v1_custom,
    write_v1_stock,
)

from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer import stems
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

    # write_v1_stock's own docstring names exactly two sibling-vote cases this synthetic KiCad
    # stand-in supports: the USB parts into Connector, and the IMU-style part into (mis-suggested)
    # Timer (research Open Question 2, covered on its own below). Every fixture part EXPECTED_TARGETS
    # names for a *real* KiCad 10 install (full stock libraries) that this stand-in does not carry
    # correctly has no sibling or category evidence here, and stays "" (ask) for the owner to place.
    imu_key = _key(IMU_LIBRARY, "ICM-42688-P")
    placed_here = {
        _key("Connector_USB_GCT", "USB4056-03-A_REVA2"): "Atomic_Connector",
        _key("Connector_USB_GCT", "USB4730-GF-A_REVA"): "Atomic_Connector",
    }
    for key, expected in EXPECTED_TARGETS.items():
        if key in placed_here:
            assert targets.get(key) == placed_here[key], key
        elif key == imu_key:
            assert targets.get(key)  # placed somewhere, just not where EXPECTED_TARGETS lands it
        else:
            assert targets.get(key, "") == "", key


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
    assert targets[key] == "Atomic_Timer"  # the mis-suggestion the owner corrects in the preview

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
