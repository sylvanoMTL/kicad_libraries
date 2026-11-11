"""find_families and derived_edits, the variant-family side of the Atomic_ migration (D-06).

Every Custom/ here is built fresh under tmp_path by migrationfixtures, installfixtures or by
hand; the live Custom/ is never touched.
"""

from pathlib import Path

import pytest
from fakecli import FakeCli
from installfixtures import V10_VERSION, vendor_footprint
from migrationfixtures import EXPECTED_TARGETS, POWER_LIBRARY, _tab_lib, _tab_symbol, write_v1_custom
from zipfixtures import STEP_BYTES

from kicad_lib_manager import fsutil, kicad_files
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.families import derived_edits, find_families
from kicad_lib_manager.importer.migration.gate import check_plan, end_state_context
from kicad_lib_manager.importer.migration.inventory import Inventory, InventoryPart, read_inventory
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

    # plan_symbols applies derived_edits itself (wired after the wave-4 merge), so the written
    # library already holds the member as (extends <parent>) plus its own properties.
    new_ref = member_ref = kicad_files.find_symbol(loaded.root, member_plan.new_name)
    assert member_ref is not None
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


# -- Task 2: untick, edge families and a real KiCad load ------------------------------------------


def _raw_symbol(
    name: str,
    *,
    pins: tuple[tuple[str, str, str], ...] = (("1", "-5.08", "0"), ("2", "5.08", "180")),
    extra: str = "",
) -> str:
    pin_lines = "\n".join(
        f'      (pin passive line (at {x} 0 {angle}) (length 2.54) (name "~") (number "{num}"))'
        for num, x, angle in pins
    )
    return (
        f'  (symbol "{name}"\n'
        f"    (exclude_from_sim no) (in_bom yes) (on_board yes)\n"
        f'    (property "Reference" "U" (at 0 0 0))\n'
        f'    (property "Value" "{name}" (at 0 0 0))\n'
        + extra
        + f'    (symbol "{name}_1_1"\n'
        + f"{pin_lines}\n"
        + "    )\n"
        + "  )\n"
    )


def _raw_lib(symbols: list[str]) -> str:
    return '(kicad_symbol_lib (version 20231120) (generator "x")\n' + "".join(symbols) + ")\n"


def _parts_inventory(root: Path, library: str, names: list[str]) -> Inventory:
    layout = RepoLayout.for_repo(root)
    rel_path = f"Custom/Symbols/{library}.kicad_sym"
    parts = tuple(
        InventoryPart(
            key=(rel_path, name),
            library=library,
            rel_path=rel_path,
            name=name,
            extends=None,
            fields={},
            footprint="",
            version=20231120,
            block_sha256="",
            atomic=False,
        )
        for name in names
    )
    return Inventory(
        layout=layout,
        parts=parts,
        footprints=(),
        models=(),
        model_linkers={},
        bak_files=(),
        symbol_libraries=(library,),
        footprint_libraries=(),
        issues=(),
    )


def _write_lib(root: Path, library: str, text: str) -> None:
    symbols_dir = root / "Custom" / "Symbols"
    symbols_dir.mkdir(parents=True, exist_ok=True)
    (symbols_dir / f"{library}.kicad_sym").write_bytes(text.encode("utf-8"))


def test_untick_keeps_member_standalone(tmp_path):
    library = "TestLib"
    _write_lib(tmp_path, library, _raw_lib([_raw_symbol("PARTA"), _raw_symbol("PARTB")]))
    inventory = _parts_inventory(tmp_path, library, ["PARTA", "PARTB"])
    targets = {part.key: "Atomic_Test" for part in inventory.parts}
    mpns = {part.key: "PART100" for part in inventory.parts}
    parent_key = (f"Custom/Symbols/{library}.kicad_sym", "PARTA")
    member_key = (f"Custom/Symbols/{library}.kicad_sym", "PARTB")
    choices = MigrationChoices(parts={member_key: PartChoice(derive=False)})

    fam = find_families(inventory, choices, targets=targets, mpns=mpns)

    assert member_key not in fam.derived
    row = next(r for r in fam.rows if r.member == member_key)
    assert row == FamilyRow(parent_key, member_key, False)


def test_members_in_different_libraries_are_not_a_family(tmp_path):
    library = "TestLib"
    _write_lib(tmp_path, library, _raw_lib([_raw_symbol("PARTA"), _raw_symbol("PARTB")]))
    inventory = _parts_inventory(tmp_path, library, ["PARTA", "PARTB"])
    key_a = (f"Custom/Symbols/{library}.kicad_sym", "PARTA")
    key_b = (f"Custom/Symbols/{library}.kicad_sym", "PARTB")
    targets = {key_a: "Atomic_One", key_b: "Atomic_Two"}
    mpns = {key_a: "PART100", key_b: "PART100"}

    fam = find_families(inventory, MigrationChoices(), targets=targets, mpns=mpns)

    assert fam.rows == ()
    assert fam.derived == {}


def test_name_only_difference_is_identical(tmp_path):
    library = "TestLib"
    names = ["PARTA", "PARTB", "PARTC", "PARTD", "PARTE"]
    text = _raw_lib(
        [
            _raw_symbol("PARTA"),
            # Identical graphics, differs only by its own name (and so its sub-symbol's name).
            _raw_symbol("PARTB"),
            # A different pin number (3 instead of 2) at the same position.
            _raw_symbol("PARTC", pins=(("1", "-5.08", "0"), ("3", "5.08", "180"))),
            # The same pin numbers, but one pin moved.
            _raw_symbol("PARTD", pins=(("1", "-6.00", "0"), ("2", "5.08", "180"))),
            # An extra graphic line the parent does not have.
            _raw_symbol("PARTE", extra='    (rectangle (start -2.54 2.54) (end 2.54 -2.54))\n'),
        ]
    )
    _write_lib(tmp_path, library, text)
    inventory = _parts_inventory(tmp_path, library, names)
    targets = {part.key: "Atomic_Test" for part in inventory.parts}
    mpns = {part.key: "PART100" for part in inventory.parts}

    fam = find_families(inventory, MigrationChoices(), targets=targets, mpns=mpns)

    rel_path = f"Custom/Symbols/{library}.kicad_sym"
    members = {row.member for row in fam.rows}
    assert members == {(rel_path, "PARTB")}
    assert fam.derived == {(rel_path, "PARTB"): (rel_path, "PARTA")}


def test_single_member_has_no_family(tmp_path):
    library = "TestLib"
    _write_lib(tmp_path, library, _raw_lib([_raw_symbol("PARTA")]))
    inventory = _parts_inventory(tmp_path, library, ["PARTA"])
    targets = {part.key: "Atomic_Test" for part in inventory.parts}
    mpns = {part.key: "PART100" for part in inventory.parts}

    fam = find_families(inventory, MigrationChoices(), targets=targets, mpns=mpns)

    assert fam.rows == ()
    assert fam.derived == {}


@pytest.mark.kicad_cli
def test_real_kicad_loads_derived_library(kicad_cli_path):
    from kicad_lib_manager.importer import kicad_cli

    text = _tab_lib(
        V10_VERSION,
        [
            _tab_symbol("PARTA", [("Reference", "U", False), ("Value", "PARTA", False)]),
            _tab_symbol("PARTB", [("Reference", "U", False), ("Value", "PARTB", False)]),
            _tab_symbol("PARTC", [("Reference", "U", False), ("Value", "PARTC", False)]),
        ],
    ).decode("utf-8")
    loaded = kicad_files.parse_bytes(text.encode("utf-8"), "AtomicFamilyTest.kicad_sym")

    edits = []
    for member_name in ("PARTB", "PARTC"):
        ref = kicad_files.find_symbol(loaded.root, member_name)
        edits.extend(derived_edits(loaded, ref, "PARTA"))
    edited_text = apply_edits(loaded.source.text, edits)
    final = kicad_files.parse_bytes(
        fsutil.encode_source(edited_text, loaded.source.bom), "AtomicFamilyTest.kicad_sym"
    )
    assert kicad_files.extends_name(kicad_files.find_symbol(final.root, "PARTB").node) == "PARTA"
    assert kicad_files.extends_name(kicad_files.find_symbol(final.root, "PARTC").node) == "PARTA"

    issues = kicad_cli.load_gate(
        kicad_cli_path,
        library="AtomicFamilyTest",
        symbol_lib=fsutil.encode_source(edited_text, loaded.source.bom),
        footprints=[],
    )
    assert issues == []
