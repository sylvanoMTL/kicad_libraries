"""Refusals and contract edges of build_plan / apply_plan (Phase 4, plan 01, task 2)."""

from contextlib import contextmanager
from pathlib import Path

import pytest
from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib, unpack_sample, write_custom_layout

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import (
    find_property,
    find_symbol,
    footprint_name,
    parse_bytes,
)
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.sexpr import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_LIBRARY = "IC_Battery_Charger_TI"
LIBRARY = "IC_Test_TI"
DATASHEET = {"Datasheet": "https://example.com/part"}


def _errors(plan):
    return [i for i in plan.issues if i.severity is Severity.ERROR]


def _codes(plan):
    return [i.code for i in _errors(plan)]


def _error(plan, code):
    found = [i for i in plan.issues if i.code == code]
    assert found, f"no {code} in {[i.code for i in plan.issues]}"
    return found[0]


@pytest.fixture
def layout(tmp_path):
    """A synthetic Custom/ holding one symbol/footprint library pair named IC_Test_TI."""
    write_custom_layout(tmp_path, [LIBRARY], [LIBRARY])
    return RepoLayout.for_repo(tmp_path)


@contextmanager
def _open(tmp_path, members, name="pkg.zip"):
    """Open a synthetic zip, yielding (package, candidate)."""
    zip_path = make_zip(_src(tmp_path) / name, members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def _src(tmp_path):
    folder = tmp_path / "src"
    folder.mkdir(exist_ok=True)
    return folder


def _members(symbols=("PART",), footprints=("FP",), models=()):
    members = [("part.kicad_sym", symbol_lib(symbols, props=DATASHEET))]
    members += [(f"{name}.kicad_mod", footprint(name)) for name in footprints]
    members += [(name, STEP_BYTES) for name in models]
    return members


# -- Phase 3 D-04: placeholder library names are refused ------------------------


def test_placeholder_library_blocked_and_nothing_written(custom_copy, ul_package, snapshot):
    _, candidate = ul_package
    before = snapshot(custom_copy.custom_dir)
    plan = build_plan(candidate, InstallOptions(library="IC_SubCategory_TI"), custom_copy)
    assert plan.blocked
    assert not plan.ops
    assert "install.placeholder_library" in _codes(plan)
    assert "SubCategory" in _error(plan, "install.placeholder_library").text
    result = apply_plan(plan)
    assert not result.ok
    assert snapshot(custom_copy.custom_dir) == before


def test_placeholder_check_runs_before_the_target_is_read(layout, tmp_path):
    # The library does not exist, yet the placeholder is what gets reported
    with _open(tmp_path, _members()) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library="Type_SubCategory_Manufacturer"), layout)
    assert _codes(plan) == ["install.placeholder_library"]


# -- D-17: one symbol, one or more footprints, zero or one model ---------------


def test_no_symbol_refused(layout, tmp_path):
    members = [("fp.kicad_mod", footprint("FP"))]
    with _open(tmp_path, members) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.no_symbol"]


def test_no_footprint_refused(layout, tmp_path):
    members = [("part.kicad_sym", symbol_lib(("PART",), props=DATASHEET))]
    with _open(tmp_path, members) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.no_footprint"]


def test_choice_required_for_two_footprints(layout, tmp_path):
    with _open(tmp_path, _members(footprints=("FP_A", "FP_B"))) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
        assert _codes(plan) == ["install.choice_required"]
        text = _error(plan, "install.choice_required").text
        assert "FP_A" in text and "FP_B" in text
        chosen = build_plan(candidate, InstallOptions(library=LIBRARY, footprints=("FP_A",)), layout)
    assert not chosen.blocked, chosen.issues
    assert chosen.footprint_names == ("FP_A",)
    assert [op.path.name for op in chosen.ops if op.kind == "footprint"] == ["FP_A.kicad_mod"]


def test_choice_required_for_two_symbols(layout, tmp_path):
    with _open(tmp_path, _members(symbols=("PART_A", "PART_B"))) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
        assert _codes(plan) == ["install.choice_required"]
        chosen = build_plan(candidate, InstallOptions(library=LIBRARY, symbol="PART_B"), layout)
    assert not chosen.blocked, chosen.issues
    assert chosen.symbol_name == "PART_B"


def test_choice_required_for_two_models_and_no_model_installs_without(layout, tmp_path):
    with _open(tmp_path, _members(models=("m1.step", "m2.step"))) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
        assert _codes(plan) == ["install.choice_required"]
        without = build_plan(candidate, InstallOptions(library=LIBRARY, no_model=True), layout)
        picked = build_plan(candidate, InstallOptions(library=LIBRARY, model="m2.step"), layout)
    assert not without.blocked, without.issues
    assert without.model_file is None
    assert not [op for op in without.ops if op.kind == "model"]
    assert not picked.blocked, picked.issues
    assert picked.model_file == "PART.step"


def test_no_model_in_package_warns(layout, tmp_path):
    with _open(tmp_path, _members()) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert not plan.blocked, plan.issues
    assert plan.model_file is None
    assert [i.severity for i in plan.issues if i.code == "install.no_model"] == [Severity.WARNING]


@pytest.mark.parametrize(
    "options, kwargs, missing",
    [
        (InstallOptions(library=LIBRARY, symbol="NOPE"), {}, "NOPE"),
        (InstallOptions(library=LIBRARY, footprints=("NOPE",)), {}, "NOPE"),
        (InstallOptions(library=LIBRARY, model="nope.step"), {"models": ("m1.step",)}, "nope.step"),
    ],
    ids=["symbol", "footprint", "model"],
)
def test_unknown_item_refused(layout, tmp_path, options, kwargs, missing):
    with _open(tmp_path, _members(**kwargs)) as (_, candidate):
        plan = build_plan(candidate, options, layout)
    assert plan.blocked
    assert _codes(plan) == ["install.unknown_item"]
    assert missing in _error(plan, "install.unknown_item").text


def test_several_footprints_first_is_linked_and_all_are_filters(layout, tmp_path):
    with _open(tmp_path, _members(footprints=("FP_A", "FP_B"))) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY, footprints=("FP_B", "FP_A")), layout)
        assert not plan.blocked, plan.issues
        assert plan.linked_footprint == "FP_B"
        assert plan.footprint_names == ("FP_B", "FP_A")
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    pretty = layout.footprints_dir / f"{LIBRARY}.pretty"
    assert sorted(p.name for p in pretty.iterdir()) == ["FP_A.kicad_mod", "FP_B.kicad_mod"]
    library = parse_bytes((layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes(), "lib")
    symbol = find_symbol(library.root, "PART")
    assert find_property(symbol.node, "Footprint").value == f"{LIBRARY}:FP_B"
    assert find_property(symbol.node, "ki_fp_filters").value == "FP_B FP_A"


# -- WR-04: staged files must still be what intake saw ---------------------------


def test_source_gone_after_package_close(custom_copy, ul_package):
    package, candidate = ul_package
    package.close()
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY), custom_copy)
    assert plan.blocked and not plan.ops
    assert "install.source_gone" in _codes(plan)


def test_source_changed_in_folder_package(custom_copy, tmp_path):
    folder = unpack_sample(tmp_path / "folder", kicad_only=True)
    with open_package(folder, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        edited = candidate.symbols[0].file.path
        edited.write_bytes(edited.read_bytes() + b"\n")
        plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY), custom_copy)
    assert plan.blocked and not plan.ops
    assert "install.source_changed" in _codes(plan)


def test_model_changed_after_plan_is_refused_by_apply(custom_copy, tmp_path, snapshot):
    folder = unpack_sample(tmp_path / "folder", kicad_only=True)
    before = snapshot(custom_copy.custom_dir)
    with open_package(folder, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY), custom_copy)
        assert not plan.blocked, plan.issues
        model = candidate.models[0].file.path
        model.write_bytes(model.read_bytes() + b" ")
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert "install.source_changed" in [i.code for i in result.issues]
    assert snapshot(custom_copy.custom_dir) == before


# -- WR-05: package and candidate Issues reach the plan -------------------------


def test_package_issues_come_first_then_candidate_issues(layout, tmp_path):
    skipped = Issue(Severity.WARNING, "intake.skipped_deep", "Skipped a folder nested too deep")
    with _open(tmp_path, _members()) as (_, candidate):
        plan = build_plan(
            candidate,
            InstallOptions(library=LIBRARY),
            layout,
            package_issues=(skipped, *candidate.issues[:1]),
        )
    assert plan.issues[0] == skipped
    assert list(plan.issues[1 : 1 + len(candidate.issues)]) == list(candidate.issues)
    # An Issue that package_issues and the candidate both carry appears once
    assert len(plan.issues) == len(set(plan.issues))


# -- Consistency of the installed names -----------------------------------------


def test_footprint_consistency_default_names(custom_copy, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY), custom_copy)
    assert not plan.blocked, plan.issues
    fp_op = next(op for op in plan.ops if op.kind == "footprint")
    sym_op = next(op for op in plan.ops if op.kind == "symbol_lib")
    loaded = parse_bytes(fp_op.data, "fp")
    ref = footprint_name(loaded.root)
    value = next(c for c in ref.node.children if c.head == "fp_text" and c.children[1].text == "value")
    assert ref.name == unquote(value.children[2].text) == fp_op.path.stem == "DQK0006B"
    library = parse_bytes(sym_op.data, "lib")
    symbol = find_symbol(library.root, plan.symbol_name)
    assert find_property(symbol.node, "Footprint").value == f"{UL_LIBRARY}:DQK0006B"
    assert find_property(symbol.node, "ki_fp_filters").value == "DQK0006B"


# -- Existing items block the plan (D-05) ---------------------------------------


def test_existing_symbol_name_is_an_unresolved_conflict_and_blocks(layout, tmp_path, snapshot):
    before = snapshot(layout.custom_dir)
    with _open(tmp_path, _members(symbols=(LIBRARY,))) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
        assert [c.key for c in plan.conflicts] == [f"symbol:{LIBRARY}:{LIBRARY}"]
        assert plan.unresolved_conflicts and plan.blocked
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert "install.conflict_unresolved" in [i.code for i in result.issues]
    assert snapshot(layout.custom_dir) == before


def test_existing_footprint_file_is_a_blocking_conflict(layout, tmp_path):
    pretty = layout.footprints_dir / f"{LIBRARY}.pretty"
    (pretty / "fp.kicad_mod").write_bytes(footprint("FP"))
    with _open(tmp_path, _members()) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert [c.key for c in plan.conflicts] == [f"footprint:{LIBRARY}:fp"]
    assert plan.blocked


def test_blocked_plan_is_never_applied_even_when_ops_exist(layout, tmp_path, snapshot):
    before = snapshot(layout.custom_dir)
    with _open(tmp_path, _members()) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library="Type_Sub_Manufacturer"), layout)
        assert plan.blocked
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok and not result.touched
    assert snapshot(layout.custom_dir) == before
