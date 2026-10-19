"""Refusals and contract edges of build_plan / apply_plan, the D-01 version table and the LIB-02 library rules (Phase 4)."""

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
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import (
    file_version,
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


def _vendor(symbol=None, *, model=True):
    """Package members: one vendor symbol (default PART at 20211014), footprint FP and optionally a STEP file."""
    members = [
        ("part.kicad_sym", vendor_symbol_lib(VENDOR) if symbol is None else symbol),
        ("FP.kicad_mod", vendor_footprint("FP")),
    ]
    if model:
        members.append(("part.step", STEP_BYTES))
    return members


def _plan(tmp_path, layout, tools, symbol=None, options=None):
    with _open(tmp_path, _vendor(symbol)) as (_, candidate):
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
    assert _op(first, "symbol_lib").data == _op(second, "symbol_lib").data


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
