"""The phase tracer: one v1 part plans, gates, applies and re-checks clean (Phase 13, MIG-02, MIG-03).

Every Custom/ here is built fresh under tmp_path from the installfixtures / zipfixtures /
migrationfixtures / customfixtures builders; the live Custom/ is never touched.
"""

import hashlib
from pathlib import Path

from customfixtures import atomic_lib, atomic_part, digest_tree
from fakecli import FakeCli
from installfixtures import V10_VERSION, vendor_footprint
from migrationfixtures import _id_lib, _id_symbol, _tab_lib, _tab_symbol
from zipfixtures import STEP_BYTES

from kicad_lib_manager import atomic_check, fsutil, kicad_files
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.applier import apply_migration
from kicad_lib_manager.importer.migration.gate import check_plan, end_state_context
from kicad_lib_manager.importer.migration.inventory import SHARED_FOOTPRINT_LIBRARY, read_inventory
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.migration.plan import (
    MigrationChoices,
    MigrationOp,
    MigrationPlan,
    PartChoice,
    PartPlan,
)
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, PartText, ToolContext
from kicad_lib_manager.models import FootprintLibrary

TODAY = "2026-11-11"


def _tools(output_version: int = V10_VERSION) -> ToolContext:
    return ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli(output_version=output_version))


def _plan_for(layout: RepoLayout, choices: MigrationChoices, *, output_version: int = V10_VERSION):
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _tools(output_version), None, today=TODAY)
    plan = build_migration_plan(inventory, choices, ctx)
    return inventory, plan


# -- Task 1: one complete part migrates end to end -----------------------------------------------

FUEL_GAUGE_LIBRARY = "IC_Fuel_Gauge_ADI"
FUEL_GAUGE_PART = "MAX17048G_T10"
FUEL_GAUGE_FOOTPRINT = "SON50P200X200X80-9N"
FUEL_GAUGE_MODEL = "MAX17048G.step"
FUEL_GAUGE_TARGET = "Atomic_Battery_Management"


def _fuel_gauge_key() -> tuple[str, str]:
    return (f"Custom/Symbols/{FUEL_GAUGE_LIBRARY}.kicad_sym", FUEL_GAUGE_PART)


def _write_fuel_gauge_tree(root: Path) -> RepoLayout:
    """One v1 library, one complete part, its footprint, its model and a stray .bak (Task 1 behavior)."""
    custom = root / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)

    (symbols_dir / f"{FUEL_GAUGE_LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    FUEL_GAUGE_PART,
                    [
                        ("Reference", "U", False),
                        ("Value", FUEL_GAUGE_PART, False),
                        ("Footprint", f"{FUEL_GAUGE_LIBRARY}:{FUEL_GAUGE_FOOTPRINT}", True),
                        (
                            "Datasheet",
                            "https://www.analog.com/media/en/technical-documentation/data-sheets/max17048-max17049.pdf",
                            True,
                        ),
                        ("Description", "1-Cell Fuel Gauge with ModelGauge", True),
                        ("MPN", "MAX17048G", True),
                        ("Manufacturer", "Analog Devices", True),
                    ],
                ),
            ],
        )
    )
    pretty = footprints_dir / f"{FUEL_GAUGE_LIBRARY}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / f"{FUEL_GAUGE_FOOTPRINT}.kicad_mod").write_bytes(
        vendor_footprint(FUEL_GAUGE_FOOTPRINT, model=f"{MODEL_DIR_VAR}/{FUEL_GAUGE_MODEL}", eol="\r\n")
    )
    (models_dir / FUEL_GAUGE_MODEL).write_bytes(STEP_BYTES)
    (symbols_dir / f"{FUEL_GAUGE_LIBRARY}.bak").write_bytes(b"old revision, kept for reference\r\n")
    return RepoLayout.for_repo(root)


def _fp_libs(layout: RepoLayout) -> list[FootprintLibrary]:
    if not layout.footprints_dir.is_dir():
        return []
    return [
        FootprintLibrary(p.stem, f"Custom/Footprints/{p.name}", "Custom")
        for p in sorted(layout.footprints_dir.iterdir())
        if p.is_dir() and p.suffix == ".pretty"
    ]


def test_one_part_migrates_end_to_end(tmp_path):
    layout = _write_fuel_gauge_tree(tmp_path)
    key = _fuel_gauge_key()
    choices = MigrationChoices(parts={key: PartChoice(library=FUEL_GAUGE_TARGET)})
    inventory, plan = _plan_for(layout, choices)

    rels = {(op.kind, op.rel) for op in plan.ops}
    assert ("write", f"Custom/Symbols/{FUEL_GAUGE_TARGET}.kicad_sym") in rels
    assert ("write", f"Custom/Footprints/Atomic_Footprints.pretty/{FUEL_GAUGE_FOOTPRINT}.kicad_mod") in rels
    assert ("delete", f"Custom/Symbols/{FUEL_GAUGE_LIBRARY}.kicad_sym") in rels
    assert ("delete", f"Custom/Footprints/{FUEL_GAUGE_LIBRARY}.pretty/{FUEL_GAUGE_FOOTPRINT}.kicad_mod") in rels
    assert ("delete", f"Custom/Symbols/{FUEL_GAUGE_LIBRARY}.bak") in rels
    assert ("rmdir", f"Custom/Footprints/{FUEL_GAUGE_LIBRARY}.pretty") in rels
    assert ("write", "Custom/MIGRATION-ATOMIC.md") in rels

    gate_ctx = end_state_context(plan, inventory, None)
    gate = check_plan(plan, inventory, gate_ctx)
    assert gate.run_enabled, gate.lines

    result = apply_migration(plan)
    assert result.ok, result.issues

    new_layout = RepoLayout.for_repo(tmp_path)
    assert not (new_layout.symbols_dir / f"{FUEL_GAUGE_LIBRARY}.kicad_sym").exists()
    assert not (new_layout.footprints_dir / f"{FUEL_GAUGE_LIBRARY}.pretty").exists()
    assert not (new_layout.symbols_dir / f"{FUEL_GAUGE_LIBRARY}.bak").exists()
    v1_syms = [
        p.name for p in new_layout.symbols_dir.iterdir() if p.suffix == ".kicad_sym" and not p.stem.startswith("Atomic_")
    ]
    assert v1_syms == []
    v1_pretty = [p.name for p in new_layout.footprints_dir.iterdir() if p.suffix == ".pretty" and p.stem != "Atomic_Footprints"]
    assert v1_pretty == []

    new_inventory = read_inventory(new_layout)
    part = next(p for p in new_inventory.parts if p.library == FUEL_GAUGE_TARGET)
    assert part.fields["Value"] == "MAX17048G"
    assert part.footprint == f"Atomic_Footprints:{FUEL_GAUGE_FOOTPRINT}"

    lib_path = new_layout.symbols_dir / f"{FUEL_GAUGE_TARGET}.kicad_sym"
    loaded = kicad_files.load(lib_path)
    ctx = atomic_check.repo_context(new_layout.repo_root, _fp_libs(new_layout), None)
    entry = atomic_check.check_symbol(
        loaded.root, part.name, rel_path=f"Custom/Symbols/{FUEL_GAUGE_TARGET}.kicad_sym", fixable=False, ctx=ctx
    )
    assert entry.violations == []


def test_model_rename_cannot_overwrite_an_untouched_model(tmp_path):
    """Gap CR-01's second manifestation: a case-only collision with an untouched, unlinked model
    must never become a write, proved end to end through plan, gate, apply and disk."""
    layout = _write_fuel_gauge_tree(tmp_path)
    (layout.models_dir / "TAKEN.STEP").write_bytes(b"UNRELATED-ORIGINAL-CONTENT")
    key = _fuel_gauge_key()
    choices = MigrationChoices(parts={key: PartChoice(library=FUEL_GAUGE_TARGET, model_name="taken")})
    inventory, plan = _plan_for(layout, choices)

    assert not any(op.rel.startswith("Custom/3DModels/") for op in plan.ops)
    assert plan.model_renames == ()
    kept_issues = [i for i in plan.issues if i.code == "migration.model_kept_name"]
    assert len(kept_issues) == 1
    assert kept_issues[0].severity.value == "info"
    assert "MAX17048G.step" in kept_issues[0].text and "taken.step" in kept_issues[0].text
    assert not any(i.code == "migration.model_clash" for i in plan.issues)

    gate_ctx = end_state_context(plan, inventory, None)
    gate = check_plan(plan, inventory, gate_ctx)
    assert gate.run_enabled, gate.lines
    assert not any("taken" in line.text for line in gate.lines)

    result = apply_migration(plan)
    assert result.ok is True, result.issues

    new_layout = RepoLayout.for_repo(tmp_path)
    assert (new_layout.models_dir / "TAKEN.STEP").read_bytes() == b"UNRELATED-ORIGINAL-CONTENT"
    assert (new_layout.models_dir / FUEL_GAUGE_MODEL).read_bytes() == STEP_BYTES

    new_inventory = read_inventory(new_layout)
    part = next(p for p in new_inventory.parts if p.library == FUEL_GAUGE_TARGET)
    fp_path = new_layout.footprints_dir / f"{SHARED_FOOTPRINT_LIBRARY}.pretty" / f"{FUEL_GAUGE_FOOTPRINT}.kicad_mod"
    fp_data = fp_path.read_bytes()
    loaded_fp = kicad_files.parse_bytes(fp_data, fp_path.name)
    ref = kicad_files.footprint_name(loaded_fp.root)
    model_paths = [m.path for m in kicad_files.find_models(ref.node)]
    assert model_paths == [f"{MODEL_DIR_VAR}/{FUEL_GAUGE_MODEL}"]

    lib_path = new_layout.symbols_dir / f"{FUEL_GAUGE_TARGET}.kicad_sym"
    loaded = kicad_files.load(lib_path)
    ctx = atomic_check.repo_context(new_layout.repo_root, _fp_libs(new_layout), None)
    entry = atomic_check.check_symbol(
        loaded.root, part.name, rel_path=f"Custom/Symbols/{FUEL_GAUGE_TARGET}.kicad_sym", fixable=False, ctx=ctx
    )
    assert entry.violations == []


def test_gate_judges_the_end_state(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    other_pretty = layout.footprints_dir / "OtherLib.pretty"
    other_pretty.mkdir(parents=True)
    other_fp_path = other_pretty / "OTHER-FP.kicad_mod"
    other_fp_path.write_bytes(vendor_footprint("OTHER-FP"))

    inventory = read_inventory(layout)

    symbol = atomic_part("TESTPART", replace={"Footprint": "OtherLib:OTHER-FP"})
    data = atomic_lib((symbol,))
    key = ("Custom/Symbols/v1.kicad_sym", "TESTPART")

    part_plan = PartPlan(
        key=key,
        source_library="V1Lib",
        target_library=FUEL_GAUGE_TARGET,
        suggestion=None,
        old_name="TESTPART",
        new_name="TESTPART",
        mpn="TESTPART",
        parent=None,
        footprint_old="OtherLib:OTHER-FP",
        footprint_new="OtherLib:OTHER-FP",
        footprint_target="official",
        model_files=(),
        field_changes=(),
        generated_text=PartText(),
        part_text=PartText(),
        issues=(),
    )
    write_op = MigrationOp(
        "write",
        layout.symbols_dir / f"{FUEL_GAUGE_TARGET}.kicad_sym",
        f"Custom/Symbols/{FUEL_GAUGE_TARGET}.kicad_sym",
        data=data,
        base_sha256=None,
    )
    delete_op = MigrationOp(
        "delete",
        other_fp_path,
        "Custom/Footprints/OtherLib.pretty/OTHER-FP.kicad_mod",
        base_sha256=hashlib.sha256(other_fp_path.read_bytes()).hexdigest(),
    )
    plan = MigrationPlan(
        layout=layout,
        parts=(part_plan,),
        ops=(write_op, delete_op),
        library_map=(),
        symbol_renames=(),
        footprint_links=(),
        model_renames=(),
        leftovers=(),
        families=(),
        conflicts=(),
        removed_libraries=(),
        bak_files=(),
        map_text="",
        issues=(),
    )

    ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, ctx)

    assert not outcome.run_enabled
    footprint_lines = [line for line in outcome.lines if line.key == key and "ootprint" in line.text]
    assert footprint_lines
    assert other_fp_path.exists()


def test_undecided_library_blocks_run(tmp_path):
    layout = _write_fuel_gauge_tree(tmp_path)
    key = _fuel_gauge_key()
    choices = MigrationChoices(parts={key: PartChoice(library="")})
    inventory, plan = _plan_for(layout, choices)

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)

    assert not outcome.run_enabled
    assert any(line.key == key and line.target == "library" for line in outcome.lines)


def test_apply_rolls_back_on_failure(tmp_path, monkeypatch):
    layout = _write_fuel_gauge_tree(tmp_path)
    key = _fuel_gauge_key()
    choices = MigrationChoices(parts={key: PartChoice(library=FUEL_GAUGE_TARGET)})
    inventory, plan = _plan_for(layout, choices)

    before = digest_tree(tmp_path / "Custom")

    real_write = fsutil.atomic_write_bytes
    calls = {"count": 0}

    def flaky(path, data, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("disk full (simulated)")
        return real_write(path, data, **kwargs)

    monkeypatch.setattr(fsutil, "atomic_write_bytes", flaky)

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    after = digest_tree(tmp_path / "Custom")
    assert before == after
    assert (tmp_path / "Custom" / "Symbols" / f"{FUEL_GAUGE_LIBRARY}.bak").exists()


def test_plan_never_leaves_custom(tmp_path):
    layout = _write_fuel_gauge_tree(tmp_path)
    key = _fuel_gauge_key()
    choices = MigrationChoices(parts={key: PartChoice(library=FUEL_GAUGE_TARGET)})
    _, plan = _plan_for(layout, choices)

    custom = layout.custom_dir.resolve()
    assert plan.ops
    for op in plan.ops:
        assert op.path.resolve().is_relative_to(custom)


# -- Task 2: several parts from mixed-format libraries merge into one Atomic_ library ------------

CONNECTOR_TARGET = "Atomic_Connector"


def _write_merge_tree(root: Path) -> RepoLayout:
    """LibA (20211014, two parts sharing one footprint) and LibB (20241209, one part, own footprint)."""
    custom = root / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)

    (symbols_dir / "LibA.kicad_sym").write_bytes(
        _id_lib(
            [
                _id_symbol(
                    "PARTA1",
                    [
                        ("Reference", "U", False),
                        ("Value", "PARTA1", False),
                        ("Footprint", "LibA:SHARED-FP", True),
                        ("Datasheet", "https://example.com/a1.pdf", True),
                        ("Description", "Connector A1", True),
                        ("MPN", "PARTA1", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                ),
                _id_symbol(
                    "PARTA2",
                    [
                        ("Reference", "U", False),
                        ("Value", "PARTA2", False),
                        ("Footprint", "LibA:SHARED-FP", True),
                        ("Datasheet", "https://example.com/a2.pdf", True),
                        ("Description", "Connector A2", True),
                        ("MPN", "PARTA2", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                ),
            ],
        )
    )
    (symbols_dir / "LibB.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    "PARTB1",
                    [
                        ("Reference", "U", False),
                        ("Value", "PARTB1", False),
                        ("Footprint", "LibB:FPB", True),
                        ("Datasheet", "https://example.com/b1.pdf", True),
                        ("Description", "Connector B1", True),
                        ("MPN", "PARTB1", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                ),
            ],
        )
    )

    liba_pretty = footprints_dir / "LibA.pretty"
    liba_pretty.mkdir(parents=True, exist_ok=True)
    (liba_pretty / "SHARED-FP.kicad_mod").write_bytes(
        vendor_footprint("SHARED-FP", model=f"{MODEL_DIR_VAR}/SHARED-FP.step", eol="\r\n")
    )
    libb_pretty = footprints_dir / "LibB.pretty"
    libb_pretty.mkdir(parents=True, exist_ok=True)
    (libb_pretty / "FPB.kicad_mod").write_bytes(vendor_footprint("FPB", model=f"{MODEL_DIR_VAR}/FPB.step", eol="\r\n"))
    (models_dir / "SHARED-FP.step").write_bytes(STEP_BYTES)
    (models_dir / "FPB.step").write_bytes(STEP_BYTES)
    return RepoLayout.for_repo(root)


def _merge_choices() -> MigrationChoices:
    keys = (
        ("Custom/Symbols/LibA.kicad_sym", "PARTA1"),
        ("Custom/Symbols/LibA.kicad_sym", "PARTA2"),
        ("Custom/Symbols/LibB.kicad_sym", "PARTB1"),
    )
    return MigrationChoices(parts={key: PartChoice(library=CONNECTOR_TARGET) for key in keys})


def test_two_libraries_merge_into_one_atomic_library(tmp_path):
    layout = _write_merge_tree(tmp_path)
    inventory, plan = _plan_for(layout, _merge_choices(), output_version=V10_VERSION)

    write_ops = [op for op in plan.ops if op.kind == "write" and op.rel.endswith(".kicad_sym")]
    assert [op.rel for op in write_ops] == [f"Custom/Symbols/{CONNECTOR_TARGET}.kicad_sym"]

    footprint_writes = [op.rel for op in plan.ops if op.kind == "write" and op.rel.endswith(".kicad_mod")]
    assert sorted(footprint_writes) == sorted(
        [
            "Custom/Footprints/Atomic_Footprints.pretty/SHARED-FP.kicad_mod",
            "Custom/Footprints/Atomic_Footprints.pretty/FPB.kicad_mod",
        ]
    )
    # The shared footprint is written exactly once even though two parts link it.
    assert footprint_writes.count("Custom/Footprints/Atomic_Footprints.pretty/SHARED-FP.kicad_mod") == 1

    rels = {(op.kind, op.rel) for op in plan.ops}
    assert ("delete", "Custom/Symbols/LibA.kicad_sym") in rels
    assert ("delete", "Custom/Symbols/LibB.kicad_sym") in rels
    assert ("rmdir", "Custom/Footprints/LibA.pretty") in rels
    assert ("rmdir", "Custom/Footprints/LibB.pretty") in rels

    data = write_ops[0].data
    loaded = kicad_files.parse_bytes(data, "Atomic_Connector.kicad_sym")
    names = [ref.name for ref in kicad_files.find_symbols(loaded.root)]
    assert names == ["PARTA1", "PARTA2", "PARTB1"]
    assert kicad_files.file_version(loaded.root) == V10_VERSION

    gate_ctx = end_state_context(plan, inventory, None)
    gate = check_plan(plan, inventory, gate_ctx)
    assert gate.run_enabled, gate.lines

    result = apply_migration(plan)
    assert result.ok, result.issues

    new_layout = RepoLayout.for_repo(tmp_path)
    lib_path = new_layout.symbols_dir / f"{CONNECTOR_TARGET}.kicad_sym"
    loaded_final = kicad_files.load(lib_path)
    assert kicad_files.file_version(loaded_final.root) == V10_VERSION

    ctx = atomic_check.repo_context(new_layout.repo_root, _fp_libs(new_layout), None)
    for name in ("PARTA1", "PARTA2", "PARTB1"):
        entry = atomic_check.check_symbol(
            loaded_final.root, name, rel_path=f"Custom/Symbols/{CONNECTOR_TARGET}.kicad_sym", fixable=False, ctx=ctx
        )
        assert entry.violations == [], (name, entry.violations)


def test_map_file_lists_the_changes(tmp_path):
    layout = _write_merge_tree(tmp_path)
    _, plan = _plan_for(layout, _merge_choices())

    text = plan.map_text
    assert "LibA -> Atomic_Connector" in text
    assert "LibB -> Atomic_Connector" in text
    assert "LibA:PARTA1 -> Atomic_Connector:PARTA1" in text
    assert "LibA:PARTA2 -> Atomic_Connector:PARTA2" in text
    assert "LibB:PARTB1 -> Atomic_Connector:PARTB1" in text
    assert "LibA:SHARED-FP -> Atomic_Footprints:SHARED-FP" in text
    assert "LibB:FPB -> Atomic_Footprints:FPB" in text

    link_index = text.index("Edit Symbol Library Links")
    update_index = text.index("Update Symbols from Library")
    pcb_index = text.index("Update PCB from Schematic")
    assert link_index < update_index < pcb_index

    # An existing MIGRATION-ATOMIC.md is kept below this run's section.
    (layout.custom_dir / "MIGRATION-ATOMIC.md").write_bytes(b"PREVIOUS_MARKER_TEXT\n")
    _, second_plan = _plan_for(layout, _merge_choices())
    second_text = second_plan.map_text
    assert second_text.index("# Atomic_ migration") < second_text.index("PREVIOUS_MARKER_TEXT")
    assert "Earlier migrations" in second_text


def test_split_library_keeps_the_staying_part(tmp_path):
    custom = tmp_path / "Custom"
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)

    (symbols_dir / "LibC.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    "PARTC1",
                    [
                        ("Reference", "U", False),
                        ("Value", "PARTC1", False),
                        ("Footprint", "Connector:USB_A", True),
                        ("Datasheet", "https://example.com/c1.pdf", True),
                        ("Description", "Part C1", True),
                        ("MPN", "PARTC1", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                ),
                _tab_symbol(
                    "PARTC2",
                    [
                        ("Reference", "U", False),
                        ("Value", "PARTC2", False),
                        ("Footprint", "LED:LED_5MM", True),
                        ("Datasheet", "https://example.com/c2.pdf", True),
                        ("Description", "Part C2", True),
                        ("MPN", "PARTC2", True),
                        ("Manufacturer", "Global Connector Technology", True),
                    ],
                ),
            ],
        )
    )
    layout = RepoLayout.for_repo(tmp_path)

    key1 = ("Custom/Symbols/LibC.kicad_sym", "PARTC1")
    key2 = ("Custom/Symbols/LibC.kicad_sym", "PARTC2")
    choices = MigrationChoices(
        parts={key1: PartChoice(library=CONNECTOR_TARGET), key2: PartChoice(library="Atomic_LED")}
    )
    inventory, plan = _plan_for(layout, choices)

    rels = {(op.kind, op.rel) for op in plan.ops}
    assert ("write", f"Custom/Symbols/{CONNECTOR_TARGET}.kicad_sym") in rels
    assert ("write", "Custom/Symbols/Atomic_LED.kicad_sym") in rels
    assert ("delete", "Custom/Symbols/LibC.kicad_sym") in rels

    assert set(plan.library_map) == {("LibC", CONNECTOR_TARGET), ("LibC", "Atomic_LED")}
