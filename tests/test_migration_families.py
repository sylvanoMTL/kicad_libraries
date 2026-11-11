"""find_families and derived_edits, the variant-family side of the Atomic_ migration (D-06).

Every Custom/ here is built fresh under tmp_path by migrationfixtures, installfixtures or by
hand; the live Custom/ is never touched.
"""

from pathlib import Path

from fakecli import FakeCli
from installfixtures import V10_VERSION, vendor_footprint
from migrationfixtures import EXPECTED_TARGETS, POWER_LIBRARY, _tab_lib, _tab_symbol, write_v1_custom
from zipfixtures import STEP_BYTES

from kicad_lib_manager import fsutil, kicad_files
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.families import derived_edits, find_families
from kicad_lib_manager.importer.migration.gate import check_plan, end_state_context
from kicad_lib_manager.importer.migration.inventory import Inventory, read_inventory
from kicad_lib_manager.importer.migration.plan import FamilyRow, MigrationChoices, PartChoice, PartKey
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, ToolContext
from kicad_lib_manager.sexpr import apply_edits

TODAY = "2026-11-11"


def _tools(output_version: int = V10_VERSION) -> ToolContext:
    return ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli(output_version=output_version))


def _ltc_key(name: str) -> PartKey:
    return (f"Custom/Symbols/{POWER_LIBRARY}.kicad_sym", name)


def _ltc_mpns(inventory: Inventory) -> dict[PartKey, str]:
    return {
        part.key: part.fields.get("MPN") or part.fields.get("MP") or part.fields.get("Value") or part.name
        for part in inventory.parts
    }


def _ltc_targets(inventory: Inventory) -> dict[PartKey, str]:
    return {part.key: EXPECTED_TARGETS.get(part.key, "") for part in inventory.parts}


def _ltc_choices() -> MigrationChoices:
    names = ("LTC2954-1-DFN8", "LTC2954-1-TSOT-23", "LTC2954-2-DFN8", "LTC2954-2-TSOT-23")
    return MigrationChoices(parts={_ltc_key(name): PartChoice(library="Atomic_Power_Management") for name in names})


# -- Task 1: identical family members plan as derived symbols and pass the gate ------------------


def test_identical_members_become_derived(tmp_path):
    layout = write_v1_custom(tmp_path)
    inventory = read_inventory(layout)
    targets = _ltc_targets(inventory)
    mpns = _ltc_mpns(inventory)

    fam = find_families(inventory, MigrationChoices(), targets=targets, mpns=mpns)

    dfn8_1 = _ltc_key("LTC2954-1-DFN8")
    dfn8_2 = _ltc_key("LTC2954-2-DFN8")
    tsot_1 = _ltc_key("LTC2954-1-TSOT-23")
    tsot_2 = _ltc_key("LTC2954-2-TSOT-23")

    # The DFN8 pair share identical graphics (same 2-pin layout, computed purely from pin index)
    # and only differ by Value, so the second becomes a derived symbol of the first.
    assert fam.derived[dfn8_2] == dfn8_1
    assert dfn8_1 not in fam.derived

    rows_by_member = {row.member: row for row in fam.rows}
    assert rows_by_member[dfn8_2] == FamilyRow(dfn8_1, dfn8_2, True)

    # The TSOT-23 pair carries a third pin: each differs from the DFN8 parent by one pin, so
    # neither gets a row and neither is in derived.
    assert tsot_1 not in fam.derived
    assert tsot_2 not in fam.derived
    assert tsot_1 not in rows_by_member
    assert tsot_2 not in rows_by_member


def test_derived_block_shape(tmp_path):
    layout = write_v1_custom(tmp_path)
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _tools(), None, today=TODAY)
    plan = build_migration_plan(inventory, _ltc_choices(), ctx)

    power_parts = {p.old_name: p for p in plan.parts if p.source_library == POWER_LIBRARY}
    parent_plan = power_parts["LTC2954-1-DFN8"]
    member_plan = power_parts["LTC2954-2-DFN8"]
    assert member_plan.parent == _ltc_key("LTC2954-1-DFN8")
    assert parent_plan.parent is None

    write_op = next(
        op
        for op in plan.ops
        if op.kind == "write" and op.rel == "Custom/Symbols/Atomic_Power_Management.kicad_sym"
    )
    loaded = kicad_files.parse_bytes(write_op.data, "Atomic_Power_Management.kicad_sym")
    names = [ref.name for ref in kicad_files.find_symbols(loaded.root)]
    # The parent is written before its derived member.
    assert names.index(parent_plan.new_name) < names.index(member_plan.new_name)

    # symbols.py does not yet call derived_edits (no call site was wired by plan 13-06); apply it
    # here to prove the shape it would produce once wired (see SUMMARY Issues Encountered).
    member_ref = kicad_files.find_symbol(loaded.root, member_plan.new_name)
    edits = derived_edits(loaded, member_ref, parent_plan.new_name)
    edited_text = apply_edits(loaded.source.text, edits)
    reparsed = kicad_files.parse_bytes(
        fsutil.encode_source(edited_text, loaded.source.bom), "Atomic_Power_Management.kicad_sym"
    )

    new_ref = kicad_files.find_symbol(reparsed.root, member_plan.new_name)
    assert kicad_files.extends_name(new_ref.node) == parent_plan.new_name
    assert [c for c in new_ref.node.children if c.head == "symbol"] == []

    value_prop = kicad_files.find_property(new_ref.node, "Value")
    assert value_prop is not None and value_prop.value == member_plan.mpn
    footprint_prop = kicad_files.find_property(new_ref.node, "Footprint")
    assert footprint_prop is not None and footprint_prop.value == member_plan.footprint_new


FAMILY_LIBRARY = "IC_Family_Test_ADI"
FAMILY_FOOTPRINT = "SON50P200X200X80-9N"
FAMILY_MODEL = "LTC2954.step"
FAMILY_TARGET = "Atomic_Power_Management"


def _fam_key(name: str) -> PartKey:
    return (f"Custom/Symbols/{FAMILY_LIBRARY}.kicad_sym", name)


def _write_family_tree(root: Path) -> RepoLayout:
    """Two identical-graphics parts (D-06): one shared footprint+model, complete fields, differ only by Value/MPN."""
    custom = root / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)

    def _props(name: str) -> list[tuple[str, str, bool]]:
        return [
            ("Reference", "U", False),
            ("Value", name, False),
            ("Footprint", f"{FAMILY_LIBRARY}:{FAMILY_FOOTPRINT}", True),
            ("Datasheet", "https://www.analog.com/ltc2954", True),
            ("Description", "Overvoltage protection controller", True),
            ("MPN", name, True),
            ("Manufacturer", "Analog Devices", True),
        ]

    (symbols_dir / f"{FAMILY_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            V10_VERSION,
            [_tab_symbol("LTC2954CDE-1", _props("LTC2954CDE-1")), _tab_symbol("LTC2954CDE-2", _props("LTC2954CDE-2"))],
        )
    )
    pretty = footprints_dir / f"{FAMILY_LIBRARY}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / f"{FAMILY_FOOTPRINT}.kicad_mod").write_bytes(
        vendor_footprint(FAMILY_FOOTPRINT, model=f"{MODEL_DIR_VAR}/{FAMILY_MODEL}", eol="\r\n")
    )
    (models_dir / FAMILY_MODEL).write_bytes(STEP_BYTES)
    return RepoLayout.for_repo(root)


def test_derived_members_pass_the_gate(tmp_path):
    layout = _write_family_tree(tmp_path)
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _tools(), None, today=TODAY)
    choices = MigrationChoices(
        parts={
            _fam_key("LTC2954CDE-1"): PartChoice(library=FAMILY_TARGET),
            _fam_key("LTC2954CDE-2"): PartChoice(library=FAMILY_TARGET),
        }
    )
    plan = build_migration_plan(inventory, choices, ctx)

    assert any(row.member == _fam_key("LTC2954CDE-2") for row in plan.families)

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)

    # Once every field is complete, the derived member's own fields pass the gate exactly like a
    # standalone part's would (gate.py judges each part's own written fields).
    assert outcome.run_enabled, outcome.lines
