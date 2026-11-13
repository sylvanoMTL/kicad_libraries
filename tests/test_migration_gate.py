"""The Run gate: every blocker as a plain, clickable line in a stable order (Phase 13, MIG-02, D-15).

Every Custom/ here is built fresh under tmp_path from the installfixtures / migrationfixtures /
customfixtures builders; the live Custom/ is never touched.
"""

import hashlib
from pathlib import Path

from customfixtures import atomic_lib, atomic_part
from fakecli import FakeCli
from installfixtures import V10_VERSION, vendor_footprint
from migrationfixtures import (
    BOARD_FEATURES,
    EXPECTED_TARGETS,
    IMU_LIBRARY,
    WIRELESS_LIBRARY,
    write_v1_custom,
    write_v1_stock,
)
from stockfixtures import write_stock_kicad
from zipfixtures import STEP_BYTES

from kicad_lib_manager.importer import stems
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration import gate as gate_module
from kicad_lib_manager.importer.migration.gate import (
    TARGET_LIBRARY,
    TARGET_NAME,
    check_plan,
    end_state_context,
)
from kicad_lib_manager.importer.migration.inventory import SHARED_FOOTPRINT_LIBRARY, read_inventory
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.migration.plan import (
    MigrationChoices,
    MigrationOp,
    MigrationPlan,
    PartChoice,
    PartPlan,
)
from kicad_lib_manager.importer.plan import Conflict, MODEL_DIR_VAR, PartText, ToolContext
from kicad_lib_manager.models import Issue, Severity

TODAY = "2026-11-11"


def _tools(output_version: int = V10_VERSION) -> ToolContext:
    return ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli(output_version=output_version))


def _shared_footprint_layout(tmp_path: Path) -> RepoLayout:
    """A layout whose Atomic_Footprints.pretty already holds GENERIC-2PIN linking a real model.

    atomic_part()'s default Footprint is "Atomic_Footprints:GENERIC-2PIN" (customfixtures), so any
    hand-built symbol that keeps that default resolves cleanly against this layout.
    """
    layout = RepoLayout.for_repo(tmp_path)
    shared_pretty = layout.footprints_dir / f"{SHARED_FOOTPRINT_LIBRARY}.pretty"
    shared_pretty.mkdir(parents=True, exist_ok=True)
    layout.models_dir.mkdir(parents=True, exist_ok=True)
    (shared_pretty / "GENERIC-2PIN.kicad_mod").write_bytes(
        vendor_footprint("GENERIC-2PIN", model=f"{MODEL_DIR_VAR}/GENERIC.step")
    )
    (layout.models_dir / "GENERIC.step").write_bytes(STEP_BYTES)
    return layout


def _bare_plan(layout: RepoLayout, *, parts: tuple, ops: tuple = (), conflicts: tuple = (), issues: tuple = ()) -> MigrationPlan:
    return MigrationPlan(
        layout=layout,
        parts=parts,
        ops=ops,
        library_map=(),
        symbol_renames=(),
        footprint_links=(),
        model_renames=(),
        leftovers=(),
        families=(),
        conflicts=conflicts,
        removed_libraries=(),
        bak_files=(),
        map_text="",
        issues=issues,
    )


def _part_plan(key: tuple[str, str], *, target_library: str, new_name: str, footprint: str, issues: tuple = ()) -> PartPlan:
    return PartPlan(
        key=key,
        source_library="V1Lib",
        target_library=target_library,
        suggestion=None,
        old_name=key[1],
        new_name=new_name,
        mpn=new_name,
        parent=None,
        footprint_old=footprint,
        footprint_new=footprint,
        footprint_target="shared",
        model_files=(),
        field_changes=(),
        generated_text=PartText(),
        part_text=PartText(),
        issues=issues,
    )


def _write_symbol_op(layout: RepoLayout, target_library: str, data: bytes) -> MigrationOp:
    return MigrationOp(
        "write",
        layout.symbols_dir / f"{target_library}.kicad_sym",
        f"Custom/Symbols/{target_library}.kicad_sym",
        data=data,
        base_sha256=None,
    )


# -- Task 1: the strip lists every blocker in order, judged on the end state --------------------


def test_model_on_delete_list_fails_even_if_present(tmp_path):
    layout = _shared_footprint_layout(tmp_path)
    inventory = read_inventory(layout)

    key = ("Custom/Symbols/v1.kicad_sym", "TESTPART")
    symbol = atomic_part("TESTPART")  # default Footprint links Atomic_Footprints:GENERIC-2PIN -> ${...}/GENERIC.step
    data = atomic_lib((symbol,))
    part_plan = _part_plan(
        key, target_library="Atomic_Test", new_name="TESTPART", footprint=f"{SHARED_FOOTPRINT_LIBRARY}:GENERIC-2PIN"
    )
    write_op = _write_symbol_op(layout, "Atomic_Test", data)
    model_path = layout.models_dir / "GENERIC.step"
    delete_op = MigrationOp(
        "delete",
        model_path,
        "Custom/3DModels/GENERIC.step",
        base_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
    )
    plan = _bare_plan(layout, parts=(part_plan,), ops=(write_op, delete_op))

    ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, ctx)

    assert not outcome.run_enabled
    model_lines = [line for line in outcome.lines if line.key == key and line.target == "model"]
    assert model_lines
    # The gate judged the planned end state, not the file: the model is still really on disk.
    assert model_path.exists()


def test_whole_set_lines_come_first_and_block(tmp_path):
    layout = _shared_footprint_layout(tmp_path)
    inventory = read_inventory(layout)

    key_a = ("Custom/Symbols/v1.kicad_sym", "PARTA")
    key_b = ("Custom/Symbols/v1.kicad_sym", "PARTB")
    part_a = _part_plan(key_a, target_library="", new_name="PARTA", footprint="")
    symbol_b = atomic_part("PARTB", drop=("MPN",))
    data_b = atomic_lib((symbol_b,))
    part_b = _part_plan(
        key_b, target_library="Atomic_Target", new_name="PARTB", footprint=f"{SHARED_FOOTPRINT_LIBRARY}:GENERIC-2PIN"
    )
    write_op = _write_symbol_op(layout, "Atomic_Target", data_b)

    conflict = Conflict(key="footprint:F1", kind="footprint", name="FP1", existing="old bytes", resolution=None)
    issues = (
        Issue(Severity.ERROR, "migration.cli_missing", "kicad-cli was not found"),
        Issue(Severity.ERROR, "migration.conflict_unresolved", "Atomic_Footprints already has a different FP1"),
    )
    plan = _bare_plan(layout, parts=(part_a, part_b), ops=(write_op,), conflicts=(conflict,), issues=issues)

    ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, ctx)

    assert not outcome.run_enabled
    texts = [line.text for line in outcome.lines]
    targets = [line.target for line in outcome.lines]
    assert texts[0] == "kicad-cli was not found"
    assert targets[0] is None
    assert texts[1] == "Atomic_Footprints already has a different FP1"
    assert targets[1] == "conflict:footprint:F1"
    # Whole-set lines come first; part lines follow ordered by target library ("" first), then name.
    assert texts[2] == "Choose a library for PARTA"
    assert targets[2] == TARGET_LIBRARY
    assert "PARTB" in texts[3]


def test_failing_counts_per_part(tmp_path):
    layout = _shared_footprint_layout(tmp_path)
    inventory = read_inventory(layout)

    key = ("Custom/Symbols/v1.kicad_sym", "MULTIFAIL")
    symbol = atomic_part("MULTIFAIL", drop=("MPN", "Datasheet"))
    data = atomic_lib((symbol,))
    part_plan = _part_plan(
        key, target_library="Atomic_Target", new_name="MULTIFAIL", footprint=f"{SHARED_FOOTPRINT_LIBRARY}:GENERIC-2PIN"
    )
    write_op = _write_symbol_op(layout, "Atomic_Target", data)
    plan = _bare_plan(layout, parts=(part_plan,), ops=(write_op,))

    ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, ctx)

    part_lines = [line for line in outcome.lines if line.key == key]
    assert len(part_lines) == 2
    assert outcome.failing[key] == 2


def test_lines_are_plain(tmp_path):
    layout = _shared_footprint_layout(tmp_path)
    inventory = read_inventory(layout)

    atomic_key = ("Custom/Symbols/v1.kicad_sym", "PLAINPART")
    symbol = atomic_part("PLAINPART", drop=("Manufacturer",))
    data = atomic_lib((symbol,))
    atomic_part_plan = _part_plan(
        atomic_key, target_library="Atomic_Target", new_name="PLAINPART", footprint=f"{SHARED_FOOTPRINT_LIBRARY}:GENERIC-2PIN"
    )
    write_op = _write_symbol_op(layout, "Atomic_Target", data)

    clash_key = ("Custom/Symbols/v1.kicad_sym", "CLASHPART")
    clash_part_plan = _part_plan(
        clash_key, target_library="Atomic_Target", new_name="ZPART", footprint="",
        issues=(Issue(Severity.ERROR, "migration.name_clash", "ZPART already exists in Atomic_Target"),),
    )

    plan = _bare_plan(layout, parts=(atomic_part_plan, clash_part_plan), ops=(write_op,))

    ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, ctx)

    assert outcome.lines
    for line in outcome.lines:
        assert "ki_" not in line.text
        assert "install.atomic" not in line.text
        assert "migration." not in line.text
        assert '"' not in line.text or line.key is None  # no raw property name left quoted on a part line
    atomic_lines = [line for line in outcome.lines if line.key == atomic_key]
    assert atomic_lines and all(line.text.startswith("PLAINPART:") for line in atomic_lines)
    clash_lines = [line for line in outcome.lines if line.key == clash_key]
    assert clash_lines == [type(clash_lines[0])(clash_key, "ZPART already exists in Atomic_Target", TARGET_NAME)]


# -- fixture-backed behaviour: multi-model footprints and board features -------------------------


def _full_fixture_choices(extra: dict | None = None) -> MigrationChoices:
    parts = {key: PartChoice(library=target) for key, target in EXPECTED_TARGETS.items()}
    if extra:
        parts.update(extra)
    return MigrationChoices(parts=parts)


def _nora_keys() -> tuple[tuple[str, str], tuple[str, str]]:
    base = f"Custom/Symbols/{WIRELESS_LIBRARY}.kicad_sym"
    return (base, "NORA-W106-00B"), (base, "NORA-W106-10B")


def _build_fixture_plan(tmp_path: Path, extra: dict | None = None):
    layout = write_v1_custom(tmp_path)
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _tools(), None, today=TODAY)
    plan = build_migration_plan(inventory, _full_fixture_choices(extra), ctx)
    return inventory, plan


def test_multi_model_footprint_passes(tmp_path):
    nora1, nora2 = _nora_keys()
    extra = {
        nora1: PartChoice(
            library="Atomic_RF_Module",
            datasheet="https://example.com/nora.pdf",
            description="NORA-W106 BLE/Thread module",
        ),
        nora2: PartChoice(
            library="Atomic_RF_Module",
            datasheet="https://example.com/nora.pdf",
            description="NORA-W106 BLE/Thread module",
        ),
    }
    inventory, plan = _build_fixture_plan(tmp_path, extra)

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)

    assert nora1 not in outcome.failing
    assert nora2 not in outcome.failing
    assert not any(line.key in (nora1, nora2) for line in outcome.lines)


def test_board_features_never_judged(tmp_path):
    inventory, plan = _build_fixture_plan(tmp_path)

    gate_ctx = end_state_context(plan, inventory, None)
    outcome = check_plan(plan, inventory, gate_ctx)

    board_feature_names = [Path(rel).stem for rel in BOARD_FEATURES]
    for line in outcome.lines:
        for name in board_feature_names:
            assert name not in line.text


# -- plan 13-26 Task 1: a guessed library blocks Run until the owner confirms it ----------------

_IMU_KEY = (f"Custom/Symbols/{IMU_LIBRARY}.kicad_sym", "ICM-42688-P")
_USB_KEY = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB4056-03-A_REVA2")


def _guess_tools(symbols_dir: Path) -> ToolContext:
    # Mirror detect_tools(): an empty allowed set would filter every suggestion out
    return ToolContext(
        kicad_cli=Path("kicad-cli"),
        cli_runner=FakeCli(output_version=V10_VERSION),
        kicad_symbols_dir=symbols_dir,
        allowed_stems=stems.allowed_stems(stems.installed_stems(symbols_dir)),
    )


def _guess_plan(tmp_path: Path, choices: MigrationChoices | None = None):
    """The v1 fixture over a stock with ICM7xxx timers only: the IMU's only vote is on the letters ICM."""
    layout = write_v1_custom(tmp_path)
    symbols_dir, footprints_dir = write_stock_kicad(
        tmp_path,
        {
            "Connector": (("USB4105-GF-A", ""), ("USB4110-GF-A", ""), ("USB4085-GF-A", "")),
            "Timer": (("ICM7555", ""), ("ICM7556", ""), ("ICM7232", ""), ("ICM7211", "")),
        },
    )
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _guess_tools(symbols_dir), footprints_dir, today=TODAY)
    plan = build_migration_plan(inventory, choices or MigrationChoices(), ctx)
    return inventory, plan


def _part(plan: MigrationPlan, key) -> PartPlan:
    return next(part for part in plan.parts if part.key == key)


def _lines_for(plan: MigrationPlan, inventory, key):
    outcome = check_plan(plan, inventory, end_state_context(plan, inventory, None))
    return [line for line in outcome.lines if line.key == key]


def test_library_basis_follows_the_owner_choice(tmp_path):
    _, plan = _guess_plan(tmp_path)
    imu = _part(plan, _IMU_KEY)
    assert imu.suggestion is not None and imu.suggestion.weak
    assert imu.target_library == "Atomic_Timer"
    assert imu.library_basis == "guessed"
    assert _part(plan, _USB_KEY).library_basis == "suggested"

    choices = MigrationChoices(parts={_IMU_KEY: PartChoice(library="Atomic_Timer")})
    _, chosen = _guess_plan(tmp_path / "chosen", choices)
    assert _part(chosen, _IMU_KEY).library_basis == "chosen"

    # A part with neither a suggestion nor a choice has no library, hence no basis
    bare = _part_plan(("x", "Y"), target_library="", new_name="Y", footprint="")
    assert bare.library_basis == ""


def test_guessed_library_blocks_run_until_confirmed(tmp_path):
    inventory, plan = _guess_plan(tmp_path)
    imu = _part(plan, _IMU_KEY)
    expected = gate_module.GUESSED_LIBRARY_TEXT.format(name=imu.new_name, library="Atomic_Timer")

    guess_lines = [line for line in _lines_for(plan, inventory, _IMU_KEY) if line.text == expected]
    assert len(guess_lines) == 1
    assert guess_lines[0].target == TARGET_LIBRARY
    assert not check_plan(plan, inventory, end_state_context(plan, inventory, None)).run_enabled

    for library in ("Atomic_Timer", "Atomic_Sensor_Motion"):
        choices = MigrationChoices(parts={_IMU_KEY: PartChoice(library=library)})
        inv2, plan2 = _guess_plan(tmp_path / library, choices)
        lines = _lines_for(plan2, inv2, _IMU_KEY)
        assert not [line for line in lines if "only a guess" in line.text]
        assert not [line for line in lines if line.target == TARGET_LIBRARY]


def test_suggested_library_is_marked_but_does_not_block(tmp_path):
    layout = write_v1_custom(tmp_path)
    symbols_dir, footprints_dir = write_v1_stock(tmp_path)
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _guess_tools(symbols_dir), footprints_dir, today=TODAY)
    plan = build_migration_plan(inventory, MigrationChoices(), ctx)

    imu = _part(plan, _IMU_KEY)
    assert imu.library_basis == "suggested"
    assert imu.target_library == "Atomic_Sensor_Motion"
    outcome = check_plan(plan, inventory, end_state_context(plan, inventory, None))
    assert not [line for line in outcome.lines if "only a guess" in line.text]


def test_guessed_library_line_is_plain(tmp_path):
    inventory, plan = _guess_plan(tmp_path)
    imu = _part(plan, _IMU_KEY)
    guess = [line for line in _lines_for(plan, inventory, _IMU_KEY) if line.target == TARGET_LIBRARY]
    assert guess
    for line in guess:
        assert "migration." not in line.text
        assert "ki_" not in line.text
        assert "${" not in line.text
        assert imu.new_name in line.text
        assert "Atomic_Timer" in line.text
