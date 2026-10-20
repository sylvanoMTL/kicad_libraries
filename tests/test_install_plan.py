"""Refusals and contract edges of build_plan / apply_plan, the D-01 version table and the LIB-02 library rules (Phase 4)."""

import dataclasses
import hashlib
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from fakecli import FakeCli
from installfixtures import extends_pair, target_lib, vendor_footprint, vendor_symbol_lib
from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib, unpack_sample, write_custom_layout

from kicad_lib_manager.importer import kicad_cli, planner
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, Rename, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.verify import verify_install
from kicad_lib_manager.kicad_files import (
    extends_name,
    file_version,
    find_models,
    find_property,
    find_symbol,
    find_symbols,
    footprint_name,
    model_insert_edit,
    parse_bytes,
    symbol_insert_edit,
    unit_library_text,
)
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.sexpr import apply_edits, unquote

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


def test_candidate_carries_package_issues(layout, tmp_path):
    members = [*_members(), ("readme.txt", b"notes")]
    zip_path = make_zip(_src(tmp_path) / "pkg.zip", members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, detection = detect_candidate(package)
        assert candidate is not None
        ignored = [i for i in package.issues if i.code == "intake.ignored_members"]
        assert len(ignored) == 1 and ignored[0].severity is Severity.INFO
        # WR-03: the package's own Issues lead the candidate's, with no caller forwarding
        assert candidate.issues[0] == ignored[0]
        # The list beside the candidate holds detection Issues only, so showing both never repeats one
        assert "intake.ignored_members" not in [i.code for i in detection]
        for extra in ((), package.issues):
            plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, package_issues=extra)
            assert [i.code for i in plan.issues].count("intake.ignored_members") == 1


# -- WR-05: a blank override means not set --------------------------------------

_TEXT_FIELDS = ("value", "datasheet", "description", "manufacturer", "mpn")


def test_blank_options_mean_not_set():
    blank = InstallOptions(library="X", value="", datasheet="  ", description="\t", manufacturer="", mpn="")
    assert [getattr(blank, name) for name in _TEXT_FIELDS] == [None] * 5
    assert InstallOptions(library="X", mpn=" CSD85301Q2 ").mpn == " CSD85301Q2 "
    assert dataclasses.replace(InstallOptions(library="X", mpn="A"), mpn="").mpn is None
    kept = InstallOptions(library=" X ", symbol=" ", model="")
    assert (kept.library, kept.symbol, kept.model) == (" X ", " ", "")


@pytest.mark.parametrize("blank", ["", "  "], ids=["empty", "spaces"])
def test_blank_option_keeps_ul_vendor_values(custom_copy, ul_package, blank):
    _, candidate = ul_package
    unset = build_plan(candidate, InstallOptions(library=UL_LIBRARY), custom_copy)
    blanked = build_plan(
        candidate,
        InstallOptions(library=UL_LIBRARY, **dict.fromkeys(_TEXT_FIELDS, blank)),
        custom_copy,
    )
    assert not blanked.blocked, blanked.issues
    assert blanked.ops == unset.ops
    assert blanked.model_file == "CSD85301Q2.stp"
    sym_op = next(op for op in blanked.ops if op.kind == "symbol_lib")
    symbol = find_symbol(parse_bytes(sym_op.data, "lib").root, "CSD85301Q2")
    values = {name: find_property(symbol.node, name) for name in ("Value", "Datasheet", "MPN", "Manufacturer")}
    assert {name: prop.value for name, prop in values.items()} == {
        "Value": "CSD85301Q2",
        "Datasheet": "https://www.ti.com/lit/gpn/csd85301q2",
        "MPN": "CSD85301Q2",
        "Manufacturer": "TI",
    }
    assert find_property(symbol.node, "ki_description") is None
    assert find_property(symbol.node, "Description") is None


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


# -- write helpers of kicad_files on shapes the UL sample does not have ---------


def test_model_block_follows_tab_indentation():
    text = '(footprint "FP"\n\t(layer "F.Cu")\n)\n'
    loaded = parse_bytes(text.encode(), "fp")
    node = footprint_name(loaded.root).node
    edit = model_insert_edit(text, node, "${CUSTOM_3DMODEL_DIR}/X.step", "\n")
    result = apply_edits(text, [edit])
    assert result == (
        '(footprint "FP"\n\t(layer "F.Cu")\n'
        '\t(model "${CUSTOM_3DMODEL_DIR}/X.step"\n'
        "\t\t(offset (xyz 0 0 0))\n\t\t(scale (xyz 1 1 1))\n\t\t(rotate (xyz 0 0 0))\n\t)\n)\n"
    )
    assert parse_bytes(result.encode(), "fp").root is not None


def test_symbol_goes_into_a_library_without_symbols():
    text = "(kicad_symbol_lib (version 20211014) (generator test)\n)\n"
    target = parse_bytes(text.encode(), "lib")
    edit = symbol_insert_edit(target, '(symbol "A"\n)')
    result = apply_edits(text, [edit])
    loaded = parse_bytes(result.encode(), "lib")
    assert [s.name for s in find_symbols(loaded.root)] == ["A"]


# -- D-01 version table (plan 04-06, task 1) ------------------------------------

VENDOR = "PART"
V6, V8, V9 = 20211014, 20231120, 20241209


@pytest.fixture(autouse=True)
def _fresh_cli_cache():
    kicad_cli.clear_cache()
    yield
    kicad_cli.clear_cache()


class _MarkingCli(FakeCli):
    """A FakeCli whose output differs from its input in the block, not only in the header."""

    def _bump(self, data):
        return super()._bump(data).replace(b'"Reference" "U"', b'"Reference" "U_FROM_CLI"')


def _tools(fake):
    return ToolContext(kicad_cli=Path("kicad-cli-for-tests.exe"), cli_runner=fake)


def _target_layout(tmp_path, version, names=("EXISTING_A",), *, library=LIBRARY, eol=None):
    """A synthetic Custom/ holding library as a symbol/footprint pair whose symbol file has the given format version."""
    write_custom_layout(tmp_path, [library], [library])
    layout = RepoLayout.for_repo(tmp_path)
    (layout.symbols_dir / f"{library}.kicad_sym").write_bytes(target_lib(version, names, eol=eol))
    return layout


def _vendor(symbol=None, *, model=True, model_name="part.step", footprint_bytes=None):
    """Package members: one vendor symbol (default PART at 20211014), footprint FP and optionally a STEP file."""
    members = [
        ("part.kicad_sym", vendor_symbol_lib(VENDOR) if symbol is None else symbol),
        ("FP.kicad_mod", vendor_footprint("FP") if footprint_bytes is None else footprint_bytes),
    ]
    if model:
        members.append((model_name, STEP_BYTES))
    return members


def _plan(tmp_path, layout, tools, symbol=None, options=None, **kwargs):
    with _open(tmp_path, _vendor(symbol, **kwargs)) as (_, candidate):
        return build_plan(candidate, options or InstallOptions(library=LIBRARY), layout, tools)


def _op(plan, kind):
    return next(op for op in plan.ops if op.kind == kind)


def _block(data, name=VENDOR):
    loaded = parse_bytes(data, "lib")
    ref = find_symbol(loaded.root, name)
    return loaded.source.text[ref.node.start : ref.node.end].replace("\r\n", "\n")


def _sub_symbol(data, name=VENDOR):
    """Text of the first unit sub-symbol of a symbol (the part no field edit touches)."""
    loaded = parse_bytes(data, "lib")
    ref = find_symbol(loaded.root, name)
    sub = next(c for c in ref.node.children if c.head == "symbol")
    return loaded.source.text[sub.start : sub.end].replace("\r\n", "\n")


def _codes_of(plan, severity):
    return [i.code for i in plan.issues if i.severity is severity]


def test_version_equal_as_is(tmp_path):
    layout = _target_layout(tmp_path, V6)
    fake = FakeCli()
    vendor = vendor_symbol_lib(VENDOR, version=V6)
    plan = _plan(tmp_path, layout, _tools(fake), vendor)
    assert not plan.blocked, plan.issues
    assert (plan.normalised, plan.source_version, plan.target_version) == (False, V6, V6)
    assert fake.calls == []
    planned = _op(plan, "symbol_lib").data
    assert _sub_symbol(planned) == _sub_symbol(vendor)
    assert "(id " in _block(planned)  # untouched vendor text keeps its KiCad 6 ids
    assert not [i for i in plan.issues if i.code.startswith("install.version")]


def test_version_older_cli_match(tmp_path):
    layout = _target_layout(tmp_path, V9)
    fake = _MarkingCli(output_version=V9)
    plan = _plan(tmp_path, layout, _tools(fake))
    assert not plan.blocked, plan.issues
    assert (plan.normalised, plan.source_version, plan.target_version) == (True, V6, V9)
    assert [" ".join(call[1:3]) for call in fake.calls] == ["sym upgrade"]
    assert "U_FROM_CLI" in _block(_op(plan, "symbol_lib").data)
    assert "install.version_mismatch" not in _codes_of(plan, Severity.WARNING)


def test_version_older_cli_mismatch(tmp_path):
    layout = _target_layout(tmp_path, V8)
    fake = _MarkingCli(output_version=V9)
    plan = _plan(tmp_path, layout, _tools(fake))
    assert not plan.blocked, plan.issues
    assert plan.normalised is False
    block = _block(_op(plan, "symbol_lib").data)
    assert "U_FROM_CLI" not in block and "(id " in block  # the vendor text is merged unchanged
    mismatch = [i for i in plan.issues if i.code == "install.version_mismatch"]
    assert [i.severity for i in mismatch] == [Severity.WARNING]
    for number in ("20211014", "20231120", "20241209"):
        assert number in mismatch[0].text


def test_version_older_no_cli(tmp_path):
    layout = _target_layout(tmp_path, V9)
    plan = _plan(tmp_path, layout, ToolContext(kicad_cli=None))
    assert not plan.blocked, plan.issues
    assert plan.normalised is False
    assert (plan.source_version, plan.target_version) == (V6, V9)
    assert "(id " in _block(_op(plan, "symbol_lib").data)
    assert [i.severity for i in plan.issues if i.code == "install.version_mismatch"] == [Severity.WARNING]
    assert [i.severity for i in plan.issues if i.code == "install.cli_not_found"] == [Severity.INFO]


def test_version_newer_refused(tmp_path, snapshot):
    layout = _target_layout(tmp_path, V6)
    before = snapshot(layout.custom_dir)
    fake = FakeCli()
    plan = _plan(tmp_path, layout, _tools(fake), vendor_symbol_lib(VENDOR, version=V9))
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.version_newer_than_target"]
    text = _error(plan, "install.version_newer_than_target").text
    assert LIBRARY in text and "save" in text
    assert fake.calls == []
    assert apply_plan(plan).ok is False
    assert snapshot(layout.custom_dir) == before


def test_version_unknown(tmp_path):
    layout = _target_layout(tmp_path, V9)
    path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    path.write_bytes(path.read_bytes().replace(b"\t(version 20241209)\n", b""))
    assert file_version(parse_bytes(path.read_bytes(), "lib").root) is None
    fake = FakeCli()
    plan = _plan(tmp_path, layout, _tools(fake))
    assert not plan.blocked, plan.issues
    assert plan.normalised is False and plan.target_version is None
    assert [i.severity for i in plan.issues if i.code == "install.version_unknown"] == [Severity.WARNING]
    assert fake.calls == []


def test_version_cli_rejects(tmp_path):
    layout = _target_layout(tmp_path, V9)
    plan = _plan(tmp_path, layout, _tools(FakeCli(modes={"sym upgrade": "reject"})))
    assert plan.blocked and not plan.ops
    assert "install.cli_gate_failed" in _codes(plan)


def test_version_memoised(tmp_path):
    layout = _target_layout(tmp_path, V9)
    fake = FakeCli(output_version=V9)
    with _open(tmp_path, _vendor()) as (_, candidate):
        first = build_plan(candidate, InstallOptions(library=LIBRARY, value="ONE"), layout, _tools(fake))
        second = build_plan(candidate, InstallOptions(library=LIBRARY, value="TWO"), layout, _tools(fake))
    assert not first.blocked and not second.blocked
    assert [call[1:3] for call in fake.calls] == [["sym", "upgrade"]]
    # The caller's Value is the only difference between the two builds; both start from the one CLI result
    assert _value_of(first, "Value") == "ONE" and _value_of(second, "Value") == "TWO"
    assert _op(first, "symbol_lib").data.replace(b"ONE", b"TWO") == _op(second, "symbol_lib").data


def test_version_cli_sees_the_chosen_unit_only(tmp_path):
    layout = _target_layout(tmp_path, V9)
    other = vendor_symbol_lib("OTHER").decode()
    mine = vendor_symbol_lib(VENDOR).decode()
    # One file holding both symbols: the first file's body, then the second file's body
    both = (other[: other.rindex(")")] + mine.split("\r\n", 1)[1]).encode()
    fake = FakeCli(output_version=V9)
    plan = _plan(tmp_path, layout, _tools(fake), both, InstallOptions(library=LIBRARY, symbol=VENDOR))
    assert not plan.blocked, plan.issues
    sent = next(iter(fake.inputs[0].values())).decode()
    assert f'(symbol "{VENDOR}"' in sent and '(symbol "OTHER"' not in sent


def test_version_extends_parent_missing(tmp_path):
    layout = _target_layout(tmp_path, V6)
    pair = parse_bytes(extends_pair("PARENT_X", "CHILD_Y"), "lib")
    child_only = unit_library_text(pair, keep={"CHILD_Y"}).encode()
    fake = FakeCli()
    plan = _plan(tmp_path, layout, _tools(fake), child_only)
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.extends_parent_missing"]
    assert "PARENT_X" in _error(plan, "install.extends_parent_missing").text
    assert fake.calls == []


def _real_tools():
    tools = planner.detect_tools(find_kicad_footprint_dir())
    if tools.kicad_cli is None:
        pytest.skip("kicad-cli not found")
    return tools


@pytest.mark.kicad_cli
def test_version_real_cli_into_20241209(tmp_path, ul_package):
    tools = _real_tools()
    layout = _target_layout(tmp_path, V9, ("EXISTING_A",))
    original = (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, tools)
    assert not plan.blocked, plan.issues
    assert plan.normalised and plan.target_version == V9
    sym_op = _op(plan, "symbol_lib")
    block = _block(sym_op.data, "CSD85301Q2")
    assert "(hide yes)" in block and "(id " not in block
    footprints = [(op.path.stem, op.data) for op in plan.ops if op.kind == "footprint"]
    issues = kicad_cli.load_gate(
        tools.kicad_cli, library=LIBRARY, symbol_lib=sym_op.data, footprints=footprints, original_symbol_lib=original
    )
    assert issues == []


def test_version_detect_tools_finds_the_install_next_to_the_footprints(tmp_path):
    root = tmp_path / "9.0"
    exe = root / "bin" / ("kicad-cli.exe" if sys.platform == "win32" else "kicad-cli")
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    fp_dir = root / "share" / "kicad" / "footprints"
    fp_dir.mkdir(parents=True)
    (root / "share" / "kicad" / "symbols").mkdir()
    runner = FakeCli()
    tools = planner.detect_tools(fp_dir, runner=runner)
    assert tools.kicad_cli == exe
    assert tools.kicad_symbols_dir == root / "share" / "kicad" / "symbols"
    assert tools.cli_runner is runner


def test_version_detect_tools_explicit_cli_wins(tmp_path):
    explicit = tmp_path / "my-kicad-cli.exe"
    explicit.write_bytes(b"")
    tools = planner.detect_tools(None, explicit_cli=explicit)
    assert tools.kicad_cli == explicit
    assert tools.kicad_symbols_dir is None


# -- LIB-02 library rules (plan 04-06, task 2) ----------------------------------

NEW_LIBRARY = "IC_New_TI"


def _pair_layout(tmp_path, symbol_libs=(LIBRARY,), footprint_libs=(LIBRARY,)):
    write_custom_layout(tmp_path, list(symbol_libs), list(footprint_libs))
    return RepoLayout.for_repo(tmp_path)


def _header(data):
    """The text before the first top-level symbol."""
    loaded = parse_bytes(data, "lib")
    return loaded.source.text[: find_symbols(loaded.root)[0].node.start]


def test_library_new_pair_with_cli(tmp_path):
    layout = _pair_layout(tmp_path)
    fake = FakeCli(output_version=V9)
    plan = _plan(tmp_path, layout, _tools(fake), options=InstallOptions(library=NEW_LIBRARY))
    assert not plan.blocked, plan.issues
    assert [op.kind for op in plan.ops] == ["mkdir", "model", "footprint", "symbol_lib"]
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (True, True)
    assert plan.ops[0].path == layout.footprints_dir / f"{NEW_LIBRARY}.pretty"
    sym_op = _op(plan, "symbol_lib")
    assert sym_op.path == layout.symbols_dir / f"{NEW_LIBRARY}.kicad_sym"
    assert sym_op.base_sha256 is None
    loaded = parse_bytes(sym_op.data, "lib")
    assert file_version(loaded.root) == V9
    assert [s.name for s in find_symbols(loaded.root)] == [VENDOR]
    assert (plan.source_version, plan.target_version, plan.normalised) == (V6, V9, True)
    assert [" ".join(call[1:3]) for call in fake.calls] == ["sym upgrade"]
    # The edited block is what ended up in the new file
    symbol = find_symbol(loaded.root, VENDOR)
    assert find_property(symbol.node, "Footprint").value == f"{NEW_LIBRARY}:FP"


def test_library_new_pair_without_cli(tmp_path):
    layout = _pair_layout(tmp_path)
    vendor = vendor_symbol_lib(VENDOR)
    plan = _plan(tmp_path, layout, ToolContext(), vendor, InstallOptions(library=NEW_LIBRARY))
    assert not plan.blocked, plan.issues
    assert [op.kind for op in plan.ops] == ["mkdir", "model", "footprint", "symbol_lib"]
    data = _op(plan, "symbol_lib").data
    assert file_version(parse_bytes(data, "lib").root) == V6
    # The header is the vendor's own, so version and content agree
    assert _header(data) == _header(vendor)
    assert [s.name for s in find_symbols(parse_bytes(data, "lib").root)] == [VENDOR]
    assert plan.target_version == V6 and plan.normalised is False
    assert [i.severity for i in plan.issues if i.code == "install.cli_not_found"] == [Severity.INFO]


def test_library_pair_completed_pretty_missing(custom_copy, ul_package, tmp_path, snapshot):
    # IC_IMU_TDK has a symbol library and no footprint library today
    assert not (custom_copy.footprints_dir / "IC_IMU_TDK.pretty").exists()
    real_before = snapshot(REPO_ROOT / "Custom" / "Footprints")
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library="IC_IMU_TDK"), custom_copy, ToolContext())
    assert not plan.blocked, plan.issues
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (False, True)
    assert [op.path for op in plan.ops if op.kind == "mkdir"] == [custom_copy.footprints_dir / "IC_IMU_TDK.pretty"]
    assert _op(plan, "symbol_lib").base_sha256 is not None
    assert [i.severity for i in plan.issues if i.code == "install.pair_completed"] == [Severity.WARNING]
    assert "IC_IMU_TDK.pretty" in _error_or_warning(plan, "install.pair_completed").text
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    assert (custom_copy.footprints_dir / "IC_IMU_TDK.pretty" / "DQK0006B.kicad_mod").is_file()
    assert snapshot(REPO_ROOT / "Custom" / "Footprints") == real_before


def _error_or_warning(plan, code):
    found = [i for i in plan.issues if i.code == code]
    assert found, f"no {code} in {[i.code for i in plan.issues]}"
    return found[0]


def test_library_pair_completed_sym_missing(tmp_path):
    layout = _pair_layout(tmp_path, symbol_libs=(), footprint_libs=(LIBRARY,))
    plan = _plan(tmp_path, layout, ToolContext(), options=InstallOptions(library=LIBRARY))
    assert not plan.blocked, plan.issues
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (True, False)
    assert [op.kind for op in plan.ops] == ["model", "footprint", "symbol_lib"]
    sym_op = _op(plan, "symbol_lib")
    assert sym_op.path == layout.symbols_dir / f"{LIBRARY}.kicad_sym" and sym_op.base_sha256 is None
    assert [s.name for s in find_symbols(parse_bytes(sym_op.data, "lib").root)] == [VENDOR]
    assert [i.severity for i in plan.issues if i.code == "install.pair_completed"] == [Severity.WARNING]
    assert "kicad_sym" in _error_or_warning(plan, "install.pair_completed").text


@pytest.mark.parametrize(
    "symbol_libs, footprint_libs",
    [((LIBRARY,), (LIBRARY,)), ((LIBRARY,), ()), ((), (LIBRARY,))],
    ids=["pair", "symbols-only", "footprints-only"],
)
def test_library_case_clash(tmp_path, snapshot, symbol_libs, footprint_libs):
    layout = _pair_layout(tmp_path, symbol_libs, footprint_libs)
    before = snapshot(layout.custom_dir)
    twin = LIBRARY.lower()
    plan = _plan(tmp_path, layout, ToolContext(), options=InstallOptions(library=twin))
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.library_case_clash"]
    assert LIBRARY in _error(plan, "install.library_case_clash").text
    assert snapshot(layout.custom_dir) == before


@pytest.mark.parametrize("name, suggestion", [("IC/Bad_TI", "IC_Bad_TI"), ("IC Bad TI", "IC_Bad_TI"), ("", None)])
def test_library_invalid_name(tmp_path, snapshot, name, suggestion):
    layout = _pair_layout(tmp_path)
    before = snapshot(layout.custom_dir)
    plan = _plan(tmp_path, layout, ToolContext(), options=InstallOptions(library=name))
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.invalid_library"]
    if suggestion is not None:
        assert suggestion in _error(plan, "install.invalid_library").text
    assert apply_plan(plan).ok is False
    assert snapshot(layout.custom_dir) == before


@pytest.mark.parametrize("version", [V6, V8, V9])
def test_library_existing_header_unchanged(tmp_path, version):
    layout = _target_layout(tmp_path, version, ("EXISTING_A", "EXISTING_B"))
    original = (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
    plan = _plan(tmp_path, layout, _tools(FakeCli(output_version=version)))
    assert not plan.blocked, plan.issues
    assert (plan.new_symbol_lib, plan.new_footprint_lib) == (False, False)
    planned = _op(plan, "symbol_lib").data
    first = find_symbols(parse_bytes(original, "lib").root)[0].node.start
    assert first > 0
    assert planned[:first] == original[:first]
    # Everything the library held before is still there, followed by the new symbol
    names = [s.name for s in find_symbols(parse_bytes(planned, "lib").root)]
    assert names == ["EXISTING_A", "EXISTING_B", VENDOR]


@pytest.mark.kicad_cli
def test_library_real_cli_new_header(tmp_path, ul_package):
    tools = _real_tools()
    layout = _pair_layout(tmp_path)
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=NEW_LIBRARY), layout, tools)
    assert not plan.blocked, plan.issues
    sym_op = _op(plan, "symbol_lib")
    header = _header(sym_op.data)
    assert "(version 20241209)" in header
    assert '(generator "kicad_symbol_editor")' in header
    assert '(generator_version "9.0")' in header
    footprints = [(op.path.stem, op.data) for op in plan.ops if op.kind == "footprint"]
    assert kicad_cli.load_gate(tools.kicad_cli, library=NEW_LIBRARY, symbol_lib=sym_op.data, footprints=footprints) == []


# -- D-11..D-15 field rules, exact renames, caller footprint names (plan 04-08, task 1) --------


def _symbol_in(plan, name=VENDOR):
    """(loaded library, symbol ref) of a symbol in the planned .kicad_sym bytes."""
    loaded = parse_bytes(_op(plan, "symbol_lib").data, "lib")
    assert not isinstance(loaded, Issue), loaded
    symbol = find_symbol(loaded.root, name)
    assert symbol is not None, [s.name for s in find_symbols(loaded.root)]
    return loaded, symbol


def _property_names(symbol):
    return [unquote(c.children[1].text) for c in symbol.node.children if c.head == "property"]


def _property_text(loaded, symbol, name):
    prop = find_property(symbol.node, name)
    assert prop is not None, _property_names(symbol)
    return loaded.source.text[prop.node.start : prop.node.end]


def _value_of(plan, name, symbol_name=VENDOR):
    _, symbol = _symbol_in(plan, symbol_name)
    prop = find_property(symbol.node, name)
    return None if prop is None else prop.value


def _vendor_property_names(data, name=VENDOR):
    return _property_names(find_symbol(parse_bytes(data, "lib").root, name))


def test_fields_mf_mp_renamed_in_place(tmp_path):
    layout = _target_layout(tmp_path, V6)
    vendor = vendor_symbol_lib(VENDOR, props={"MF": "Texas Instruments", "MP": "XYZ123"})
    original = _vendor_property_names(vendor)
    plan = _plan(tmp_path, layout, ToolContext(), vendor, model_name="part.stp")
    assert not plan.blocked, plan.issues
    _, symbol = _symbol_in(plan)
    assert _property_names(symbol) == [{"MF": "Manufacturer", "MP": "MPN"}.get(n, n) for n in original]
    assert (_value_of(plan, "Manufacturer"), _value_of(plan, "MPN")) == ("Texas Instruments", "XYZ123")
    assert plan.model_file == "XYZ123.stp"
    assert "install.manufacturer_missing" not in [i.code for i in plan.issues]


def test_fields_exact_manufacturer_kept(tmp_path):
    layout = _target_layout(tmp_path, V6)
    vendor = vendor_symbol_lib(VENDOR, props={"Manufacturer": "Exact Co", "MANUFACTURER": "Other Co"})
    plan = _plan(tmp_path, layout, ToolContext(), vendor)
    assert not plan.blocked, plan.issues
    _, symbol = _symbol_in(plan)
    names = _property_names(symbol)
    assert names.count("Manufacturer") == 1 and names.count("MANUFACTURER") == 1
    assert (_value_of(plan, "Manufacturer"), _value_of(plan, "MANUFACTURER")) == ("Exact Co", "Other Co")


def test_fields_added_hidden_20211014(tmp_path, ul_package):
    layout = _target_layout(tmp_path, V6)
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, ToolContext())
    assert not plan.blocked, plan.issues
    loaded, symbol = _symbol_in(plan, "CSD85301Q2")
    assert (_value_of(plan, "Manufacturer", "CSD85301Q2"), _value_of(plan, "MPN", "CSD85301Q2")) == ("TI", "CSD85301Q2")
    ids = {}
    for name in ("Manufacturer", "MPN"):
        text = _property_text(loaded, symbol, name)
        assert "(hide yes)" not in text and re.search(r"\bhide\)", text), text
        found = re.search(r"\(id (\d+)\)", text)
        assert found, text
        ids[name] = int(found.group(1))
    # The UL symbol's own ids run 0..6, so the new properties continue at 7
    assert ids == {"Manufacturer": 7, "MPN": 8}


def test_fields_added_hidden_20241209(tmp_path):
    layout = _target_layout(tmp_path, V9)
    plan = _plan(
        tmp_path, layout, ToolContext(), target_lib(V9, (VENDOR,)), InstallOptions(library=LIBRARY, manufacturer="TI")
    )
    assert not plan.blocked, plan.issues
    loaded, symbol = _symbol_in(plan)
    assert (_value_of(plan, "Manufacturer"), _value_of(plan, "MPN")) == ("TI", VENDOR)
    for name in ("Manufacturer", "MPN"):
        text = _property_text(loaded, symbol, name)
        assert "(hide yes)" in text and "(id " not in text, text


def test_fields_overrides_win(tmp_path):
    layout = _target_layout(tmp_path, V6)
    vendor = vendor_symbol_lib(VENDOR, props={"MF": "Old Co", "MP": "OLD123"})
    options = InstallOptions(
        library=LIBRARY,
        value="VAL",
        datasheet="https://example.com/ds.pdf",
        description="A description",
        manufacturer="NewCo",
        mpn="NEW-1",
    )
    plan = _plan(tmp_path, layout, ToolContext(), vendor, options)
    assert not plan.blocked, plan.issues
    _, symbol = _symbol_in(plan)
    names = _property_names(symbol)
    assert names.count("Manufacturer") == 1 and names.count("MPN") == 1
    assert "MF" not in names and "MP" not in names
    assert [_value_of(plan, n) for n in ("Value", "Datasheet", "ki_description", "Manufacturer", "MPN")] == [
        "VAL",
        "https://example.com/ds.pdf",
        "A description",
        "NewCo",
        "NEW-1",
    ]
    assert plan.model_file == "NEW-1.step"
    assert "install.manufacturer_missing" not in [i.code for i in plan.issues]


def test_fields_manufacturer_missing_warns(tmp_path):
    layout = _target_layout(tmp_path, V6)
    plan = _plan(tmp_path, layout, ToolContext(), vendor_symbol_lib(VENDOR, datasheet=""))
    assert not plan.blocked, plan.issues
    assert _value_of(plan, "Manufacturer") == ""
    assert _value_of(plan, "MPN") == VENDOR
    assert [i.severity for i in plan.issues if i.code == "install.manufacturer_missing"] == [Severity.WARNING]


@pytest.mark.parametrize(
    "version, vendor, expected, absent",
    [
        (V6, vendor_symbol_lib(VENDOR, version=V6), "ki_description", "Description"),
        (V9, vendor_symbol_lib(VENDOR, version=V9), "Description", "ki_description"),
        (V6, vendor_symbol_lib(VENDOR, version=V6, props={"Description": "old"}), "Description", "ki_description"),
        (V6, vendor_symbol_lib(VENDOR, version=V6, props={"ki_description": "old"}), "ki_description", "Description"),
    ],
    ids=["v6-new", "v9-new", "existing-description", "existing-ki_description"],
)
def test_fields_description_name_by_version(tmp_path, version, vendor, expected, absent):
    layout = _target_layout(tmp_path, version)
    options = InstallOptions(library=LIBRARY, description="New text")
    plan = _plan(tmp_path, layout, ToolContext(), vendor, options)
    assert not plan.blocked, plan.issues
    _, symbol = _symbol_in(plan)
    names = _property_names(symbol)
    assert names.count(expected) == 1 and absent not in names
    assert _value_of(plan, expected) == "New text"


def test_rename_sanitised_symbol(tmp_path):
    layout = _target_layout(tmp_path, V6)
    vendor = vendor_symbol_lib("PART/X", units=2, keywords="PART/X PART/XY power")
    plan = _plan(tmp_path, layout, ToolContext(), vendor)
    assert not plan.blocked, plan.issues
    assert plan.symbol_names == ("PART_X",)
    assert Rename("symbol", "PART/X", "PART_X") in plan.renames
    loaded, symbol = _symbol_in(plan, "PART_X")
    subs = [unquote(c.children[1].text) for c in symbol.node.children if c.head == "symbol"]
    assert subs == ["PART_X_1_1", "PART_X_2_1"]
    assert find_symbol(loaded.root, "PART/X") is None
    assert _value_of(plan, "Value", "PART_X") == "PART_X"
    # Only a token equal to the old name changes: PART/XY is a different word
    assert _value_of(plan, "ki_keywords", "PART_X") == "PART_X PART/XY power"
    assert _value_of(plan, "MPN", "PART_X") == "PART/X"
    assert plan.model_file == "PART_X.step"


def test_rename_not_listed_when_the_name_is_clean(tmp_path):
    layout = _target_layout(tmp_path, V6)
    plan = _plan(tmp_path, layout, ToolContext())
    assert not plan.blocked, plan.issues
    assert plan.renames == ()


def test_rename_value_override_beats_the_token_rewrite(tmp_path):
    layout = _target_layout(tmp_path, V6)
    plan = _plan(
        tmp_path, layout, ToolContext(), vendor_symbol_lib("PART/X"), InstallOptions(library=LIBRARY, value="Mine")
    )
    assert not plan.blocked, plan.issues
    assert _value_of(plan, "Value", "PART_X") == "Mine"


def test_footprint_consistency_after_override(custom_copy, ul_package):
    _, candidate = ul_package
    options = InstallOptions(library=UL_LIBRARY, footprint_names={"DQK0006B": "DQK0006B_TI"})
    plan = build_plan(candidate, options, custom_copy)
    assert not plan.blocked, plan.issues
    assert plan.footprint_names == ("DQK0006B_TI",) and plan.linked_footprint == "DQK0006B_TI"
    assert Rename("footprint", "DQK0006B", "DQK0006B_TI") in plan.renames
    fp_op = next(op for op in plan.ops if op.kind == "footprint")
    assert fp_op.path.name == "DQK0006B_TI.kicad_mod"
    ref = footprint_name(parse_bytes(fp_op.data, "fp").root)
    value = next(c for c in ref.node.children if c.head == "fp_text" and c.children[1].text == "value")
    assert ref.name == unquote(value.children[2].text) == "DQK0006B_TI"
    assert _value_of(plan, "Footprint", "CSD85301Q2") == f"{UL_LIBRARY}:DQK0006B_TI"
    assert _value_of(plan, "ki_fp_filters", "CSD85301Q2") == "DQK0006B_TI"


def test_footprint_consistency_override_is_sanitised(custom_copy, ul_package):
    _, candidate = ul_package
    options = InstallOptions(library=UL_LIBRARY, footprint_names={"DQK0006B": "DQK 0006/B"})
    plan = build_plan(candidate, options, custom_copy)
    assert not plan.blocked, plan.issues
    assert plan.footprint_names == ("DQK_0006_B",)
    assert [i.severity for i in plan.issues if i.code == "naming.changed"] == [Severity.INFO]
    assert Rename("footprint", "DQK0006B", "DQK_0006_B") in plan.renames


def test_footprint_consistency_unusable_override_refused(custom_copy, ul_package, snapshot):
    _, candidate = ul_package
    before = snapshot(custom_copy.custom_dir)
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, footprint_names={"DQK0006B": "///"}), custom_copy)
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.invalid_name"]
    assert apply_plan(plan).ok is False
    assert snapshot(custom_copy.custom_dir) == before


def test_fields_value_injection_quoted(tmp_path):
    layout = _target_layout(tmp_path, V6)
    hostile = 'A") (x'
    plan = _plan(tmp_path, layout, ToolContext(), options=InstallOptions(library=LIBRARY, mpn=hostile))
    assert not plan.blocked, plan.issues
    loaded, symbol = _symbol_in(plan)
    assert find_property(symbol.node, "MPN").value == hostile
    assert plan.model_file == "A_x.step"
    assert [op.path.name for op in plan.ops if op.kind == "model"] == ["A_x.step"]
    # One quoted token: the planned library re-parses and holds exactly the old and the new symbol
    assert [s.name for s in find_symbols(loaded.root)] == ["EXISTING_A", VENDOR]


@pytest.mark.parametrize("version", [V6, V9])
def test_fields_existing_symbols_untouched(tmp_path, version):
    layout = _target_layout(tmp_path, version, ("EXISTING_A", "EXISTING_B"))
    original = (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
    parsed = parse_bytes(original, "lib")
    cut = len(parsed.source.text[: find_symbols(parsed.root)[-1].node.end].encode("utf-8"))
    options = InstallOptions(library=LIBRARY, mpn="NEW")
    plan = _plan(tmp_path, layout, _tools(FakeCli(output_version=version)), options=options)
    assert not plan.blocked, plan.issues
    planned = _op(plan, "symbol_lib").data
    # Header and every existing symbol are byte-identical; text is only inserted after the last symbol
    assert planned[:cut] == original[:cut]
    assert planned.endswith(original[cut:])
    assert len(planned) > len(original)


# -- D-16 extends units, D-17 several footprints, INTK-08 no-model path (plan 04-08, task 2) --------

PARENT, CHILD = "PARENT_X", "CHILD_Y"


def _symbol_names(plan):
    return [s.name for s in find_symbols(parse_bytes(_op(plan, "symbol_lib").data, "lib").root)]


@pytest.mark.parametrize("new_library", [False, True], ids=["existing", "new"])
def test_unit_parent_first(tmp_path, new_library):
    layout = _pair_layout(tmp_path)
    library = NEW_LIBRARY if new_library else LIBRARY
    options = InstallOptions(library=library, symbol=CHILD)
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair(PARENT, CHILD, child_first=True), options)
    assert not plan.blocked, plan.issues
    assert plan.symbol_names == (PARENT, CHILD) and plan.symbol_name == CHILD
    names = _symbol_names(plan)
    assert names == ([PARENT, CHILD] if new_library else [LIBRARY, PARENT, CHILD])
    # The library still parses with the child after its parent and the child still extends it
    _, child = _symbol_in(plan, CHILD)
    assert extends_name(child.node) == PARENT


def test_unit_fields_on_every_symbol(tmp_path):
    layout = _pair_layout(tmp_path)
    options = InstallOptions(library=LIBRARY, symbol=CHILD, mpn="CHILD-MPN", manufacturer="TI")
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair(PARENT, CHILD), options)
    assert not plan.blocked, plan.issues
    for name in (PARENT, CHILD):
        assert _value_of(plan, "Footprint", name) == f"{LIBRARY}:FP"
        assert _value_of(plan, "ki_fp_filters", name) == "FP"
        assert _value_of(plan, "Manufacturer", name) == "TI"
    # The caller's part number belongs to the chosen symbol; its parent keeps its own name
    assert _value_of(plan, "MPN", CHILD) == "CHILD-MPN"
    assert _value_of(plan, "MPN", PARENT) == PARENT
    assert plan.model_file == "CHILD-MPN.step"


def test_unit_parent_rename_updates_extends(tmp_path):
    layout = _pair_layout(tmp_path)
    options = InstallOptions(library=LIBRARY, symbol=CHILD)
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair("PARENT/X", CHILD), options)
    assert not plan.blocked, plan.issues
    assert plan.symbol_names == (PARENT, CHILD)
    assert Rename("symbol", "PARENT/X", PARENT) in plan.renames
    loaded, child = _symbol_in(plan, CHILD)
    assert extends_name(child.node) == PARENT
    _, parent = _symbol_in(plan, PARENT)
    assert [unquote(c.children[1].text) for c in parent.node.children if c.head == "symbol"] == ["PARENT_X_1_1"]
    assert "PARENT/X" not in loaded.source.text.replace('(property "MPN" "PARENT/X"', "")


def test_unit_existing_parent_is_a_conflict(tmp_path):
    layout = _target_layout(tmp_path, V6, (PARENT,))
    options = InstallOptions(library=LIBRARY, symbol=CHILD)
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair(PARENT, CHILD), options)
    assert [c.key for c in plan.conflicts] == [f"symbol:{LIBRARY}:{PARENT}"]
    assert plan.blocked


@pytest.mark.parametrize("size", [1, 2], ids=["1", "2"])
def test_unit_invariant(layout, tmp_path, size):
    symbol = vendor_symbol_lib(PARENT) if size == 1 else extends_pair(PARENT, CHILD)
    chosen = PARENT if size == 1 else CHILD
    with _open(tmp_path, _vendor(symbol)) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY, symbol=chosen), layout, ToolContext())
        assert not plan.blocked, plan.issues
        assert len(plan.symbol_names) == size
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    assert not [i for i in verify_install(plan) if i.severity is Severity.ERROR]
    library = parse_bytes((layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes(), "lib")
    present = [s.name for s in find_symbols(library.root)]
    for name in plan.symbol_names:
        assert present.count(name) == 1
        assert find_property(find_symbol(library.root, name).node, "Footprint").value == f"{LIBRARY}:FP"


def test_several_footprints_order(layout, tmp_path):
    members = [
        ("part.kicad_sym", vendor_symbol_lib(VENDOR)),
        ("FP_A.kicad_mod", vendor_footprint("FP_A")),
        ("FP_B.kicad_mod", vendor_footprint("FP_B")),
        ("part.step", STEP_BYTES),
    ]
    with _open(tmp_path, members) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=LIBRARY, footprints=("FP_B", "FP_A")), layout, ToolContext())
    assert not plan.blocked, plan.issues
    footprints = [op for op in plan.ops if op.kind == "footprint"]
    assert [op.path.stem for op in footprints] == ["FP_B", "FP_A"]
    assert _value_of(plan, "Footprint") == f"{LIBRARY}:FP_B"
    assert _value_of(plan, "ki_fp_filters") == "FP_B FP_A"
    carried = {op.path.stem: [m.path for m in find_models(footprint_name(parse_bytes(op.data, "fp").root).node)] for op in footprints}
    assert carried == {"FP_B": ["${CUSTOM_3DMODEL_DIR}/PART.step"], "FP_A": []}


def test_no_model_package(layout, tmp_path):
    plan = _plan(tmp_path, layout, ToolContext(), model=False)
    assert not plan.blocked, plan.issues
    assert plan.model_file is None
    assert not [op for op in plan.ops if op.kind in ("model",)]
    assert b"(model" not in _op(plan, "footprint").data
    found = [i for i in plan.issues if i.code == "install.no_model"]
    assert [i.severity for i in found] == [Severity.WARNING]
    assert "No 3D model found in pkg.zip" in found[0].text
    assert "install.model_declined" not in [i.code for i in plan.issues]


def test_no_model_declined(custom_copy, ul_package):
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, no_model=True), custom_copy)
    assert not plan.blocked, plan.issues
    assert plan.model_file is None
    assert not [op for op in plan.ops if op.kind == "model"]
    assert b"(model" not in next(op for op in plan.ops if op.kind == "footprint").data
    assert [i.severity for i in plan.issues if i.code == "install.model_declined"] == [Severity.INFO]
    assert "install.no_model" not in [i.code for i in plan.issues]


@pytest.mark.parametrize(
    "path, stale",
    [
        ("${KIPRJMOD}/x.step", True),
        ("C:/models/x.step", True),
        ("x.step", True),
        ("${KICAD9_3DMODEL_DIR}/Pkg.3dshapes/x.step", False),
        ("${CUSTOM_3DMODEL_DIR}/x.step", False),
    ],
    ids=["kiprjmod", "absolute", "relative", "stock", "custom"],
)
def test_no_model_stale_vendor_path(layout, tmp_path, path, stale):
    plan = _plan(tmp_path, layout, ToolContext(), model=False, footprint_bytes=vendor_footprint("FP", model=path))
    assert not plan.blocked, plan.issues
    assert plan.model_file is None
    # The vendor path is never edited
    assert [m.path for m in find_models(footprint_name(parse_bytes(_op(plan, "footprint").data, "fp").root).node)] == [path]
    assert ("install.stale_model_path" in [i.code for i in plan.issues]) is stale
    if stale:
        assert [i.severity for i in plan.issues if i.code == "install.stale_model_path"] == [Severity.WARNING]


def test_model_extra_blocks_warn(layout, tmp_path):
    plan = _plan(tmp_path, layout, ToolContext(), footprint_bytes=vendor_footprint("FP", models=("a.step", "b.step")))
    assert not plan.blocked, plan.issues
    paths = [m.path for m in find_models(footprint_name(parse_bytes(_op(plan, "footprint").data, "fp").root).node)]
    assert paths == ["${CUSTOM_3DMODEL_DIR}/PART.step", "b.step"]
    assert [i.severity for i in plan.issues if i.code == "install.extra_models"] == [Severity.WARNING]
    # The remaining block is reported once, as an extra block, not a second time as a stale path
    assert "install.stale_model_path" not in [i.code for i in plan.issues]


def test_model_embedded_files_warn(layout, tmp_path):
    plan = _plan(tmp_path, layout, ToolContext(), footprint_bytes=vendor_footprint("FP", embedded=True))
    assert not plan.blocked, plan.issues
    assert [i.severity for i in plan.issues if i.code == "install.embedded_files"] == [Severity.WARNING]
    loaded = parse_bytes(_op(plan, "footprint").data, "fp")
    node = footprint_name(loaded.root).node
    embedded = [c for c in node.children if c.head == "embedded_files"]
    assert [loaded.source.text[c.start : c.end] for c in embedded] == ["(embedded_files)"]


@pytest.mark.kicad_cli
@pytest.mark.parametrize("new_library", [False, True], ids=["existing", "new"])
def test_unit_real_cli_loads_in_kicad(tmp_path, new_library):
    tools = _real_tools()
    layout = _target_layout(tmp_path, V9, ("EXISTING_A",))
    library = NEW_LIBRARY if new_library else LIBRARY
    original = (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
    options = InstallOptions(library=library, symbol=CHILD)
    plan = _plan(tmp_path, layout, tools, extends_pair(PARENT, CHILD, child_first=True), options)
    assert not plan.blocked, plan.issues
    assert plan.symbol_names == (PARENT, CHILD)
    sym_op = _op(plan, "symbol_lib")
    footprints = [(op.path.stem, op.data) for op in plan.ops if op.kind == "footprint"]
    kwargs = {} if new_library else {"original_symbol_lib": original}
    assert kicad_cli.load_gate(tools.kicad_cli, library=library, symbol_lib=sym_op.data, footprints=footprints, **kwargs) == []


# -- conflicts, the identical rule and stable keys (plan 04-09, task 1) ------------------

SYM_KEY = f"symbol:{LIBRARY}:{VENDOR}"
FP_KEY = f"footprint:{LIBRARY}:fp"
MODEL_KEY = "model:part.step"


def _pretty(layout):
    return layout.footprints_dir / f"{LIBRARY}.pretty"


def _put_footprint(layout, file_name="FP.kicad_mod", data=None):
    """An existing footprint file in the target .pretty; the default differs from what the vendor footprint plans."""
    (_pretty(layout) / file_name).write_bytes(vendor_footprint("FP", pads=("1",)) if data is None else data)


def _put_model(layout, file_name="PART.step", data=b"some other model"):
    layout.models_dir.mkdir(parents=True, exist_ok=True)
    (layout.models_dir / file_name).write_bytes(data)


def _clashing_layout(tmp_path, *, symbol=True, footprint=True, model=True, extra_names=()):
    """A target library where the planned symbol, footprint and model each already exist with other content."""
    names = ("EXISTING_A", *((VENDOR,) if symbol else ()), *extra_names)
    layout = _target_layout(tmp_path, V6, names)
    if footprint:
        _put_footprint(layout)
    if model:
        _put_model(layout)
    return layout


def _apply(plan, tmp_path):
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    return result


def _install(tmp_path, layout, tools=ToolContext(), symbol=None, options=None, **kwargs):
    """Build and apply one plan while its package is open; returns the plan."""
    with _open(tmp_path, _vendor(symbol, **kwargs)) as (_, candidate):
        plan = build_plan(candidate, options or InstallOptions(library=LIBRARY), layout, tools)
        _apply(plan, tmp_path)
    return plan


def test_noop_second_plan_after_apply(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    options = InstallOptions(library=UL_LIBRARY)
    first = build_plan(candidate, options, custom_copy)
    assert not first.blocked and first.ops, first.issues
    _apply(first, tmp_path)
    second = build_plan(candidate, options, custom_copy)
    assert second.ops == () and second.conflicts == ()
    assert not second.blocked, second.issues
    assert second.is_noop
    # The symbol and footprint names are still reported, so a preview can show what is already there
    assert second.symbol_names == ("CSD85301Q2",) and second.linked_footprint == "DQK0006B"
    assert second.model_file == "CSD85301Q2.stp"


@pytest.mark.kicad_cli
def test_noop_second_plan_after_normalised_apply(tmp_path, ul_package):
    tools = _real_tools()
    layout = _target_layout(tmp_path, V9, ("EXISTING_A",))
    _, candidate = ul_package
    options = InstallOptions(library=LIBRARY)
    first = build_plan(candidate, options, layout, tools)
    assert not first.blocked and first.normalised, first.issues
    _apply(first, tmp_path)
    second = build_plan(candidate, options, layout, tools)
    assert second.ops == () and second.conflicts == ()
    assert second.is_noop, second.issues


def test_noop_symbol_identical_is_not_spliced(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _install(tmp_path, layout)
    after_first = (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
    # Only the footprint and the model go missing again: the identical symbol must not be written a second time
    (_pretty(layout) / "FP.kicad_mod").unlink()
    (layout.models_dir / "PART.step").unlink()
    plan = _plan(tmp_path, layout, ToolContext())
    assert not plan.blocked and plan.conflicts == (), plan.issues
    assert [op.kind for op in plan.ops] == ["model", "footprint"]
    assert (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes() == after_first


def test_noop_eol_difference_is_identical(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _install(tmp_path, layout)
    path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    # The same library saved with other line endings still holds the same block (D-07)
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    assert b"\r\n" not in path.read_bytes()
    plan = _plan(tmp_path, layout, ToolContext())
    assert plan.ops == () and plan.conflicts == () and plan.is_noop, plan.issues


def test_conflict_symbol_different(tmp_path):
    layout = _clashing_layout(tmp_path, footprint=False, model=False)
    plan = _plan(tmp_path, layout, ToolContext())
    assert [c.key for c in plan.conflicts] == [SYM_KEY]
    conflict = plan.conflicts[0]
    assert (conflict.kind, conflict.name, conflict.resolution) == ("symbol", VENDOR, None)
    assert LIBRARY in conflict.existing and VENDOR in conflict.existing
    assert plan.unresolved_conflicts == plan.conflicts and plan.blocked


def test_conflict_symbol_case_twin_warns(tmp_path):
    layout = _target_layout(tmp_path, V6, ("EXISTING_A", VENDOR.lower()))
    plan = _plan(tmp_path, layout, ToolContext())
    assert plan.conflicts == () and not plan.blocked, plan.issues
    clash = [i for i in plan.issues if i.code == "naming.case_clash"]
    assert [i.severity for i in clash] == [Severity.WARNING]
    assert VENDOR.lower() in clash[0].text
    names = [s.name for s in find_symbols(parse_bytes(_op(plan, "symbol_lib").data, "lib").root)]
    assert names == ["EXISTING_A", VENDOR.lower(), VENDOR]


def test_conflict_footprint_bytes_differ(tmp_path):
    layout = _clashing_layout(tmp_path, symbol=False, model=False)
    plan = _plan(tmp_path, layout, ToolContext())
    assert [c.key for c in plan.conflicts] == [FP_KEY]
    conflict = plan.conflicts[0]
    assert (conflict.kind, conflict.name, conflict.resolution) == ("footprint", "FP", None)
    assert plan.blocked


def test_conflict_footprint_case_twin(tmp_path):
    layout = _target_layout(tmp_path, V6)
    planned = _op(_plan(tmp_path, layout, ToolContext()), "footprint").data
    # Identical bytes under a case-different file name still clash: Windows sees one file (D-10, INST-03/adjacency)
    _put_footprint(layout, "fp.kicad_mod", planned)
    plan = _plan(tmp_path, layout, ToolContext())
    assert [c.key for c in plan.conflicts] == [FP_KEY]
    assert "fp.kicad_mod" in plan.conflicts[0].existing
    assert plan.blocked


def test_conflict_footprint_identical_is_not_written(tmp_path):
    layout = _target_layout(tmp_path, V6)
    planned = _op(_plan(tmp_path, layout, ToolContext()), "footprint").data
    _put_footprint(layout, "FP.kicad_mod", planned)
    plan = _plan(tmp_path, layout, ToolContext())
    assert plan.conflicts == () and not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "footprint"]
    assert plan.linked_footprint == "FP"
    assert _value_of(plan, "Footprint") == f"{LIBRARY}:FP"


def test_model_same_sha_reused(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _put_model(layout, "PART.step", STEP_BYTES)
    plan = _plan(tmp_path, layout, ToolContext())
    assert plan.conflicts == () and not plan.blocked, plan.issues
    assert not [op for op in plan.ops if op.kind == "model"]
    assert plan.model_file == "PART.step"
    footprint_op = _op(plan, "footprint")
    paths = [m.path for m in find_models(footprint_name(parse_bytes(footprint_op.data, "fp").root).node)]
    assert paths == ["${CUSTOM_3DMODEL_DIR}/PART.step"]


def test_model_different_sha_conflict(tmp_path):
    layout = _clashing_layout(tmp_path, symbol=False, footprint=False)
    plan = _plan(tmp_path, layout, ToolContext())
    assert [c.key for c in plan.conflicts] == [MODEL_KEY]
    conflict = plan.conflicts[0]
    assert (conflict.kind, conflict.name, conflict.resolution) == ("model", "PART.step", None)
    assert not [op for op in plan.ops if op.kind == "model"]
    assert plan.blocked


def test_model_case_twin_conflict(tmp_path):
    layout = _target_layout(tmp_path, V6)
    # The same bytes under another spelling: the link would be case-wrong on Linux, so it clashes (D-10)
    _put_model(layout, "part.STEP", STEP_BYTES)
    plan = _plan(tmp_path, layout, ToolContext())
    assert [c.key for c in plan.conflicts] == [MODEL_KEY]
    assert "part.STEP" in plan.conflicts[0].existing
    assert plan.blocked


def test_conflict_keys_stable(tmp_path):
    layout = _clashing_layout(tmp_path)
    plain = _plan(tmp_path, layout, ToolContext())
    changed = _plan(tmp_path, layout, ToolContext(), options=InstallOptions(library=LIBRARY, value="OTHER", mpn=None))
    assert [c.key for c in plain.conflicts] == [SYM_KEY, FP_KEY, MODEL_KEY]
    assert [c.key for c in changed.conflicts] == [c.key for c in plain.conflicts]


def test_conflict_suggested_names(tmp_path):
    layout = _clashing_layout(tmp_path)
    plan = _plan(tmp_path, layout, ToolContext())
    assert {c.kind: c.suggested_name for c in plan.conflicts} == {
        "symbol": "PART_2",
        "footprint": "FP_2",
        "model": "PART_2.step",
    }
    # Taken names are skipped: symbols compare exactly, files compare ignoring case
    layout = _clashing_layout(tmp_path / "taken", extra_names=("PART_2", "part_3"))
    _put_footprint(layout, "fp_2.kicad_mod")
    _put_model(layout, "PART_2.STEP")
    plan = _plan(tmp_path / "taken", layout, ToolContext())
    assert {c.kind: c.suggested_name for c in plan.conflicts} == {
        "symbol": "PART_3",
        "footprint": "FP_3",
        "model": "PART_3.step",
    }


def test_conflict_suggest_free_name_rules():
    free = planner.suggest_free_name
    assert free("A", set(), casefold=False) == "A_2"
    assert free("A", {"A_2", "A_3"}, casefold=False) == "A_4"
    assert free("A", {"a_2"}, casefold=False) == "A_2"
    assert free("A", {"a_2"}, casefold=True) == "A_3"
    assert free("A", {"a_2.STP"}, suffix=".stp", casefold=True) == "A_3.stp"
    # The suffix survives the 64 character limit: the base is cut, not the number
    long = "L" * 64
    got = free(long, set(), casefold=False)
    assert got.endswith("_2") and len(got) <= 64


def test_conflict_unresolved_blocks(tmp_path, snapshot):
    layout = _clashing_layout(tmp_path)
    before = snapshot(layout.custom_dir)
    plan = _plan(tmp_path, layout, ToolContext())
    assert plan.blocked and len(plan.unresolved_conflicts) == 3
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok and not result.touched
    unresolved = [i for i in result.issues if i.code == "install.conflict_unresolved"]
    assert len(unresolved) == 1
    for key in (SYM_KEY, FP_KEY, MODEL_KEY):
        assert key in unresolved[0].text
    assert snapshot(layout.custom_dir) == before


# -- resolutions: overwrite in place, rename with validation, skip uses the existing item (plan 04-09, task 2) --------


def _res(action, rename_to=None):
    return Resolution(action, rename_to)


def _with(resolutions, **kwargs):
    return InstallOptions(library=LIBRARY, resolutions=resolutions, **kwargs)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _footprint_of(plan, name="FP"):
    op = next(op for op in plan.ops if op.kind == "footprint" and op.path.stem == name)
    loaded = parse_bytes(op.data, "fp")
    return op, loaded, footprint_name(loaded.root)


def test_resolution_overwrite_symbol_in_place(tmp_path):
    layout = _clashing_layout(tmp_path, footprint=False, model=False, extra_names=("EXISTING_C",))
    path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    original = path.read_bytes()
    old = parse_bytes(original, "lib")
    span = find_symbol(old.root, VENDOR).node
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({SYM_KEY: _res("overwrite")}))
    assert not plan.blocked, plan.issues
    op = _op(plan, "symbol_lib")
    assert op.base_sha256 == _sha(original) and op.listed_path is None
    planned = parse_bytes(op.data, "lib")
    # Everything before and after the old block is byte-identical, so the library keeps its order (D-08)
    assert planned.source.text[: span.start] == old.source.text[: span.start]
    assert planned.source.text.endswith(old.source.text[span.end :])
    assert [s.name for s in find_symbols(planned.root)] == ["EXISTING_A", VENDOR, "EXISTING_C"]
    assert find_property(find_symbol(planned.root, VENDOR).node, "Footprint").value == f"{LIBRARY}:FP"
    assert [(c.key, c.resolution) for c in plan.conflicts] == [(SYM_KEY, _res("overwrite"))]


@pytest.mark.parametrize("existing", ["FP.kicad_mod", "fp.kicad_mod"], ids=["same-spelling", "case-twin"])
def test_resolution_overwrite_footprint(tmp_path, existing):
    layout = _target_layout(tmp_path, V6)
    _put_footprint(layout, existing)
    on_disk = (_pretty(layout) / existing).read_bytes()
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({FP_KEY: _res("overwrite")}))
    assert not plan.blocked, plan.issues
    op = _op(plan, "footprint")
    assert op.base_sha256 == _sha(on_disk)
    # Paths compare ignoring case on Windows, so the spelling is compared as text
    assert (None if op.listed_path is None else op.listed_path.name) == (None if existing == "FP.kicad_mod" else existing)
    assert op.path.name == "FP.kicad_mod"


def test_resolution_overwrite_model_case_twin(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _put_model(layout, "part.STEP", b"other bytes")
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({MODEL_KEY: _res("overwrite")}))
    assert not plan.blocked, plan.issues
    op = _op(plan, "model")
    assert (op.path.name, op.listed_path.name) == ("PART.step", "part.STEP")
    assert op.base_sha256 == _sha(b"other bytes")
    assert plan.model_file == "PART.step"


@pytest.mark.skipif(sys.platform != "win32", reason="replacing a case twin leaves one entry only on NTFS (research spike S7)")
def test_resolution_overwrite_model_case_twin_applies_on_ntfs(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _put_model(layout, "part.STEP", b"other bytes")
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({MODEL_KEY: _res("overwrite")}), layout, ToolContext())
        _apply(plan, tmp_path)
    assert os.listdir(layout.models_dir) == ["PART.step"]
    assert (layout.models_dir / "PART.step").read_bytes() == STEP_BYTES


def test_resolution_rename_symbol(tmp_path):
    layout = _clashing_layout(tmp_path, footprint=False, model=False)
    vendor = vendor_symbol_lib(VENDOR, units=2)
    plan = _plan(tmp_path, layout, ToolContext(), vendor, _with({SYM_KEY: _res("rename")}))
    assert not plan.blocked, plan.issues
    assert plan.symbol_names == ("PART_2",)
    loaded, symbol = _symbol_in(plan, "PART_2")
    assert [unquote(c.children[1].text) for c in symbol.node.children if c.head == "symbol"] == ["PART_2_1_1", "PART_2_2_1"]
    assert [s.name for s in find_symbols(loaded.root)] == ["EXISTING_A", VENDOR, "PART_2"]
    assert _value_of(plan, "MPN", "PART_2") == VENDOR
    assert _value_of(plan, "Value", "PART_2") == "PART_2"
    assert Rename("symbol", VENDOR, "PART_2") in plan.renames
    assert [(c.key, c.resolution) for c in plan.conflicts] == [(SYM_KEY, _res("rename"))]


def test_resolution_rename_symbol_follows_extends(tmp_path):
    layout = _target_layout(tmp_path, V6, (PARENT,))
    key = f"symbol:{LIBRARY}:{PARENT}"
    options = InstallOptions(library=LIBRARY, symbol=CHILD, resolutions={key: _res("rename", "PARENT_NEW")})
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair(PARENT, CHILD, child_first=True), options)
    assert not plan.blocked, plan.issues
    assert plan.symbol_names == ("PARENT_NEW", CHILD)
    loaded, child = _symbol_in(plan, CHILD)
    assert extends_name(child.node) == "PARENT_NEW"
    _, parent = _symbol_in(plan, "PARENT_NEW")
    assert [unquote(c.children[1].text) for c in parent.node.children if c.head == "symbol"] == ["PARENT_NEW_1_1"]
    assert [s.name for s in find_symbols(loaded.root)] == [PARENT, "PARENT_NEW", CHILD]


def test_resolution_rename_footprint_flows(tmp_path):
    layout = _clashing_layout(tmp_path, symbol=False, model=False)
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({FP_KEY: _res("rename", "FP_ALT")}))
    assert not plan.blocked, plan.issues
    op, loaded, ref = _footprint_of(plan, "FP_ALT")
    assert op.path.name == "FP_ALT.kicad_mod" and op.base_sha256 is None
    value = next(c for c in ref.node.children if c.head == "fp_text" and c.children[1].text == "value")
    assert ref.name == unquote(value.children[2].text) == "FP_ALT"
    assert _value_of(plan, "Footprint") == f"{LIBRARY}:FP_ALT"
    assert _value_of(plan, "ki_fp_filters") == "FP_ALT"
    assert plan.linked_footprint == "FP_ALT" and plan.footprint_names == ("FP_ALT",)
    assert Rename("footprint", "FP", "FP_ALT") in plan.renames
    # The existing FP.kicad_mod is not written
    assert [o.path.name for o in plan.ops if o.kind == "footprint"] == ["FP_ALT.kicad_mod"]


def test_resolution_rename_footprint_uses_the_suggestion(tmp_path):
    layout = _clashing_layout(tmp_path, symbol=False, model=False)
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({FP_KEY: _res("rename")}))
    assert not plan.blocked, plan.issues
    assert plan.footprint_names == ("FP_2",)
    assert _value_of(plan, "Footprint") == f"{LIBRARY}:FP_2"


def test_resolution_rename_model_flows(tmp_path):
    layout = _clashing_layout(tmp_path, symbol=False, footprint=False)
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({MODEL_KEY: _res("rename")}))
    assert not plan.blocked, plan.issues
    op = _op(plan, "model")
    assert op.path == layout.models_dir / "PART_2.step" and op.base_sha256 is None and op.listed_path is None
    assert plan.model_file == "PART_2.step"
    _, _, ref = _footprint_of(plan)
    assert [m.path for m in find_models(ref.node)] == ["${CUSTOM_3DMODEL_DIR}/PART_2.step"]
    assert Rename("model", "PART.step", "PART_2.step") in plan.renames


RENAME_CASES = [
    ("symbol", "../x", "x"),
    ("symbol", "EXISTING_A", None),
    ("symbol", "///", None),
    ("footprint", "../x", "x"),
    ("footprint", "OTHER", None),
    ("footprint", "///", None),
    ("model", "../x.step", "x.step"),
    ("model", "OTHER.step", None),
    ("model", "///", None),
]


@pytest.mark.parametrize("kind, rename_to, expected", RENAME_CASES, ids=[f"{k}-{r}" for k, r, _ in RENAME_CASES])
def test_resolution_rename_invalid(tmp_path, kind, rename_to, expected):
    layout = _clashing_layout(tmp_path)
    _put_footprint(layout, "OTHER.kicad_mod", vendor_footprint("OTHER"))
    _put_model(layout, "OTHER.step", b"yet another model")
    keys = {"symbol": SYM_KEY, "footprint": FP_KEY, "model": MODEL_KEY}
    # The other two kinds are overwritten, so only the rename under test can go wrong
    resolutions = {key: _res("overwrite") for key in keys.values()}
    resolutions[keys[kind]] = _res("rename", rename_to)
    plan = _plan(tmp_path, layout, ToolContext(), options=_with(resolutions))
    if expected is None:
        assert plan.blocked
        assert _codes(plan) == ["install.bad_rename"]
        return
    assert not plan.blocked, plan.issues
    assert "naming.changed" in [i.code for i in plan.issues if i.severity is Severity.INFO]
    if kind == "symbol":
        assert plan.symbol_names == (expected,)
    elif kind == "footprint":
        assert plan.footprint_names == (expected,)
        assert _op(plan, "footprint").path.name == f"{expected}.kicad_mod"
    else:
        assert plan.model_file == expected
        assert _op(plan, "model").path.name == expected


def test_resolution_rename_target_identical(tmp_path):
    layout = _clashing_layout(tmp_path)
    resolutions = {
        SYM_KEY: _res("rename", "PART_9"),
        FP_KEY: _res("rename", "FP_9"),
        MODEL_KEY: _res("rename", "PART_9.step"),
    }
    _install(tmp_path, layout, options=_with(resolutions))
    again = _plan(tmp_path, layout, ToolContext(), options=_with(resolutions))
    # The renamed items are already there with the planned content: nothing to write, nothing to ask again
    assert again.ops == () and not again.blocked and again.is_noop, again.issues
    assert [(c.key, c.resolution) for c in again.conflicts] == [(k, resolutions[k]) for k in (SYM_KEY, FP_KEY, MODEL_KEY)]
    assert again.symbol_names == ("PART_9",) and again.linked_footprint == "FP_9" and again.model_file == "PART_9.step"


def test_resolution_skip_footprint(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _put_footprint(layout, "fp.kicad_mod", vendor_footprint("fp", pads=("1",)))
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({FP_KEY: _res("skip")}), layout, ToolContext())
        assert not plan.blocked, plan.issues
        assert [op.kind for op in plan.ops] == ["symbol_lib"]
        assert plan.linked_footprint == "fp" and plan.footprint_names == ("fp",) and plan.model_file is None
        assert _value_of(plan, "Footprint") == f"{LIBRARY}:fp"
        assert _value_of(plan, "ki_fp_filters") == "fp"
        assert [i.severity for i in plan.issues if i.code == "install.model_not_attached"] == [Severity.INFO]
        assert plan.renames == ()
        result = _apply(plan, tmp_path)
    # D-09: the pin/pad check runs against the footprint that is really linked
    assert "verify.pin_pad_mismatch" in [i.code for i in result.issues]
    assert os.listdir(_pretty(layout)) == ["fp.kicad_mod"] and os.listdir(layout.models_dir) == []


def test_resolution_skip_model(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _put_model(layout, "part.STEP", b"other bytes")
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({MODEL_KEY: _res("skip")}), layout, ToolContext())
        assert not plan.blocked, plan.issues
        assert not [op for op in plan.ops if op.kind == "model"]
        assert plan.model_file == "part.STEP"
        _, _, ref = _footprint_of(plan)
        assert [m.path for m in find_models(ref.node)] == ["${CUSTOM_3DMODEL_DIR}/part.STEP"]
        _apply(plan, tmp_path)
    assert os.listdir(layout.models_dir) == ["part.STEP"]
    assert (layout.models_dir / "part.STEP").read_bytes() == b"other bytes"


def test_resolution_skip_symbol(tmp_path):
    layout = _clashing_layout(tmp_path, footprint=False, model=False)
    path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    original = path.read_bytes()
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({SYM_KEY: _res("skip")}), layout, ToolContext())
        assert not plan.blocked, plan.issues
        assert [op.kind for op in plan.ops] == ["model", "footprint"]
        kept = [i for i in plan.issues if i.code == "install.symbol_kept"]
        assert [i.severity for i in kept] == [Severity.WARNING]
        assert VENDOR in kept[0].text and "Footprint" in kept[0].text
        _apply(plan, tmp_path)
    assert path.read_bytes() == original
    assert (_pretty(layout) / "FP.kicad_mod").is_file() and (layout.models_dir / "PART.step").is_file()


def test_resolution_skip_parent_symbol_keeps_the_child_linked(tmp_path):
    layout = _target_layout(tmp_path, V6, (PARENT,))
    key = f"symbol:{LIBRARY}:{PARENT}"
    options = InstallOptions(library=LIBRARY, symbol=CHILD, resolutions={key: _res("skip")})
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair(PARENT, CHILD), options)
    assert not plan.blocked, plan.issues
    loaded, child = _symbol_in(plan, CHILD)
    assert [s.name for s in find_symbols(loaded.root)] == [PARENT, CHILD]
    assert extends_name(child.node) == PARENT
    assert _value_of(plan, "Footprint", CHILD) == f"{LIBRARY}:FP"
    assert plan.linked_footprint == "FP"
    assert [i.code for i in plan.issues if i.code == "install.symbol_kept"] == ["install.symbol_kept"]


def test_resolution_parent_before_child(tmp_path):
    layout = _target_layout(tmp_path, V6, ("EXISTING_A", CHILD))
    path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    old = parse_bytes(path.read_bytes(), "lib")
    span = find_symbol(old.root, CHILD).node
    key = f"symbol:{LIBRARY}:{CHILD}"
    options = InstallOptions(library=LIBRARY, symbol=CHILD, resolutions={key: _res("overwrite")})
    plan = _plan(tmp_path, layout, ToolContext(), extends_pair(PARENT, CHILD, child_first=True), options)
    assert [c.key for c in plan.conflicts] == [key]
    assert not plan.blocked, plan.issues
    planned = parse_bytes(_op(plan, "symbol_lib").data, "lib")
    assert [s.name for s in find_symbols(planned.root)] == ["EXISTING_A", PARENT, CHILD]
    assert extends_name(find_symbol(planned.root, CHILD).node) == PARENT
    # The parent goes in right where the child stood, and nothing around them moves
    assert planned.source.text[: span.start] == old.source.text[: span.start]
    assert planned.source.text.endswith(old.source.text[span.end :])


def test_resolution_no_global_default(tmp_path, snapshot):
    layout = _clashing_layout(tmp_path)
    before = snapshot(layout.custom_dir)
    resolutions = {SYM_KEY: _res("overwrite"), "symbol:Other_Lib:Nothing": _res("overwrite")}
    plan = _plan(tmp_path, layout, ToolContext(), options=_with(resolutions))
    # One resolved key resolves exactly that conflict; a key that matches nothing changes nothing
    assert plan.blocked
    assert [c.key for c in plan.unresolved_conflicts] == [FP_KEY, MODEL_KEY]
    assert [c.key for c in plan.conflicts if c.resolution is not None] == [SYM_KEY]
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok and not result.touched
    text = next(i.text for i in result.issues if i.code == "install.conflict_unresolved")
    assert FP_KEY in text and MODEL_KEY in text and SYM_KEY not in text
    assert snapshot(layout.custom_dir) == before


def test_resolution_unknown_action_is_refused(tmp_path):
    layout = _clashing_layout(tmp_path, footprint=False, model=False)
    plan = _plan(tmp_path, layout, ToolContext(), options=_with({SYM_KEY: _res("replace")}))
    assert plan.blocked
    assert "install.bad_resolution" in _codes(plan)
    assert [c.resolution for c in plan.conflicts] == [None]
