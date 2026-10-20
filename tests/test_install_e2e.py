"""The Ultra Librarian sample installed into a tmp_path copy of Custom/: ROADMAP Phase 4 success criteria 1-5 end to end.

Every install targets the ``custom_copy`` fixture (a tmp_path copy of the real Custom/ libraries) or a
tmp_path folder; the module-scoped ``_real_custom_untouched`` fixture proves the checkout's own Custom/
is never written (D-22).
"""

import hashlib
import os
import shutil
import zipfile
from pathlib import Path

import pytest
from installfixtures import vendor_footprint
from zipfixtures import UL_FOOTPRINT_MEMBER, UL_MODEL_MEMBER, UL_SYMBOL_MEMBER, make_zip, unpack_sample

from kicad_lib_manager import fsutil
from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import MAX_FOLDER_DEPTH, open_package
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, InstallOptions, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan, detect_tools
from kicad_lib_manager.importer.verify import verify_install
from kicad_lib_manager.kicad_files import (
    find_models,
    find_property,
    find_symbol,
    find_symbols,
    footprint_name,
    load,
)
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.sexpr import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = "IC_Battery_Charger_TI"


def _hidden(prop) -> bool:
    """True when the property carries a bare hide atom (KiCad 6/7 form) anywhere below it."""
    stack = [prop.node]
    while stack:
        node = stack.pop()
        if node.kind == "atom" and node.text == "hide":
            return True
        stack.extend(node.children)
    return False


def _value_text(footprint_node):
    for child in footprint_node.children:
        if child.head == "fp_text" and child.children[1].text == "value":
            return child.children[2]
    return None


def test_ul_symbol_added_others_identical(custom_copy, ul_package, tmp_path, snapshot):
    package, candidate = ul_package
    layout = custom_copy
    sym_path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    original = sym_path.read_bytes()
    original_loaded = load(sym_path)
    previous_end = find_symbols(original_loaded.root)[-1].node.end
    real_before = snapshot(REPO_ROOT / "Custom" / "Symbols") | snapshot(REPO_ROOT / "Custom" / "Footprints")

    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert not plan.blocked, plan.issues
    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert not [i for i in result.issues if i.severity is Severity.ERROR]
    pretty = layout.footprints_dir / f"{LIBRARY}.pretty"
    assert result.touched == (
        layout.models_dir / "CSD85301Q2.stp",
        pretty / "DQK0006B.kicad_mod",
        sym_path,
    )

    # Header and every other symbol are byte-identical: removing the inserted segment restores the file
    written = load(sym_path)
    new_node = find_symbol(written.root, "CSD85301Q2").node
    text = written.source.text
    restored = text[:previous_end] + text[new_node.end:]
    assert fsutil.encode_source(restored, written.source.bom) == original
    assert [s.name for s in find_symbols(written.root)][-1] == "CSD85301Q2"

    footprint = load(pretty / "DQK0006B.kicad_mod")
    ref = footprint_name(footprint.root)
    assert ref.name == "DQK0006B"
    value = _value_text(ref.node)
    assert value.kind == "str" and unquote(value.text) == "DQK0006B"
    models = find_models(ref.node)
    assert [m.path for m in models] == [f"{MODEL_DIR_VAR}/CSD85301Q2.stp"]

    symbol = find_symbol(written.root, "CSD85301Q2")
    assert find_property(symbol.node, "Footprint").value == f"{LIBRARY}:DQK0006B"
    assert find_property(symbol.node, "ki_fp_filters").value == "DQK0006B"
    manufacturer = find_property(symbol.node, "Manufacturer")
    mpn = find_property(symbol.node, "MPN")
    assert (manufacturer.value, mpn.value) == ("TI", "CSD85301Q2")
    assert _hidden(manufacturer) and _hidden(mpn)

    model = layout.models_dir / "CSD85301Q2.stp"
    assert hashlib.sha256(model.read_bytes()).hexdigest() == candidate.models[0].file.sha256

    assert result.backup_dir is not None
    assert result.backup_dir.parent == tmp_path / "bk" / "installs"
    assert (result.backup_dir / f"{LIBRARY}.kicad_sym_backup_1").read_bytes() == original

    # The checkout's own Custom/ was never written
    real_after = snapshot(REPO_ROOT / "Custom" / "Symbols") | snapshot(REPO_ROOT / "Custom" / "Footprints")
    assert real_after == real_before


# -- ROADMAP Phase 4 success criteria 1-5 and idempotency (plan 04-10, Task 1) ----------------------------

NEW_LIBRARY = "IC_MOSFET_Dual_TI"
SYMBOL = "CSD85301Q2"
NO_CLI = ToolContext()


def _tree_digest(root: Path) -> dict[str, str]:
    """Map every file below root to its SHA-256 and every folder to "dir"; the same shape as the snapshot fixture."""
    found: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        found[rel + "/" if path.is_dir() else rel] = "dir" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return found


@pytest.fixture(scope="module", autouse=True)
def _real_custom_untouched():
    """Phase 4 never writes the checkout's own Custom/ (D-22): snapshot it before the module and compare after."""
    real = REPO_ROOT / "Custom"
    if not (real / "Symbols").is_dir():
        yield
        return
    before = _tree_digest(real)
    yield
    assert _tree_digest(real) == before, "a test wrote to the real Custom/ folder"


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def _install(candidate, layout, tmp_path, library=LIBRARY, tools=NO_CLI, **options):
    """Plan and apply one install with a tmp_path backup root; returns (plan, result)."""
    plan = build_plan(candidate, InstallOptions(library=library, **options), layout, tools)
    assert not plan.blocked, plan.issues
    return plan, apply_plan(plan, backup_root=tmp_path / "bk")


def _header(data: bytes) -> bytes:
    """The bytes before the first symbol of a .kicad_sym."""
    return data[: data.index(b"(symbol ")]


def _zip_member(name: str) -> bytes:
    with zipfile.ZipFile(REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip") as zf:
        return zf.read(name)


def test_sc1_ul_footprint_model_and_fields(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    layout = custom_copy
    plan, result = _install(candidate, layout, tmp_path)
    assert result.ok, result.issues
    assert not result.new_library

    pretty = layout.footprints_dir / f"{LIBRARY}.pretty"
    assert sorted(p.name for p in pretty.glob("DQK0006B*")) == ["DQK0006B.kicad_mod"]
    footprint = load(pretty / "DQK0006B.kicad_mod")
    ref = footprint_name(footprint.root)
    assert ref.name == "DQK0006B"
    value = _value_text(ref.node)
    assert value.kind == "str" and unquote(value.text) == "DQK0006B"
    assert [m.path for m in find_models(ref.node)] == [f"{MODEL_DIR_VAR}/{SYMBOL}.stp"]

    # The STEP is copied under the part number, byte for byte
    assert (layout.models_dir / f"{SYMBOL}.stp").read_bytes() == _zip_member(UL_MODEL_MEMBER)

    library = load(layout.symbols_dir / f"{LIBRARY}.kicad_sym")
    symbol = find_symbol(library.root, SYMBOL)
    assert find_property(symbol.node, "Footprint").value == f"{LIBRARY}:DQK0006B"
    assert find_property(symbol.node, "ki_fp_filters").value == "DQK0006B"
    manufacturer, mpn = find_property(symbol.node, "Manufacturer"), find_property(symbol.node, "MPN")
    assert (manufacturer.value, mpn.value) == ("TI", SYMBOL)
    assert _hidden(manufacturer) and _hidden(mpn)
    assert plan.linked_footprint == "DQK0006B" and plan.model_file == f"{SYMBOL}.stp"


def test_sc2_rename_follows_sub_symbols(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    layout = custom_copy
    _install(candidate, layout, tmp_path)
    sym_path = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
    first = load(sym_path)
    first_block = first.source.text[find_symbol(first.root, SYMBOL).node.start : find_symbol(first.root, SYMBOL).node.end]

    key = f"symbol:{LIBRARY}:{SYMBOL}"
    options = InstallOptions(library=LIBRARY, value="CSD85301Q2-ALT", resolutions={key: Resolution("rename")})
    plan = build_plan(candidate, options, layout, NO_CLI)
    assert not plan.blocked, plan.issues
    assert plan.symbol_name == f"{SYMBOL}_2"
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues

    written = load(sym_path)
    renamed = find_symbol(written.root, f"{SYMBOL}_2")
    subs = [c.children[1].text for c in renamed.node.children if c.head == "symbol"]
    assert [unquote(s) for s in subs] == [f"{SYMBOL}_2_1_1", f"{SYMBOL}_2_2_1"]
    assert find_property(renamed.node, "Value").value == "CSD85301Q2-ALT"
    # Nothing else changed: the first block is still byte-identical and the new one is last
    old = find_symbol(written.root, SYMBOL).node
    assert written.source.text[old.start : old.end] == first_block
    assert [s.name for s in find_symbols(written.root)][-2:] == [SYMBOL, f"{SYMBOL}_2"]
    assert written.source.text[: renamed.node.start].rstrip().endswith(first_block)


def test_sc2_no_model_package(custom_copy, tmp_path):
    folder = unpack_sample(tmp_path / "pkg", kicad_only=True)
    for step in list(folder.rglob("*.stp")) + list(folder.rglob("*.step")):
        step.unlink()
    layout = custom_copy
    before = _tree_digest(layout.models_dir)
    with open_package(folder, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        plan, result = _install(candidate, layout, tmp_path)

        assert not [op for op in plan.ops if op.kind == "model"]
        footprint_op = next(op for op in plan.ops if op.kind == "footprint")
        assert b"(model" not in footprint_op.data
        for issues in (plan.issues, result.issues):
            found = [i for i in issues if i.code == "install.no_model"]
            assert [i.severity for i in found] == [Severity.WARNING]
    assert result.ok, result.issues
    assert _tree_digest(layout.models_dir) == before
    footprint = load(layout.footprints_dir / f"{LIBRARY}.pretty" / "DQK0006B.kicad_mod")
    assert find_models(footprint_name(footprint.root).node) == []


def test_package_issue_reaches_install_result_from_a_folder(custom_copy, tmp_path):
    # WR-03: a package-level WARNING survives open_package -> detect_candidate -> build_plan -> apply_plan
    folder = unpack_sample(tmp_path / "ul")
    deep = folder
    for level in range(MAX_FOLDER_DEPTH + 1):
        deep = deep / f"d{level}"
    deep.mkdir(parents=True)
    (deep / "note.txt").write_bytes(b"too deep to be read")
    with open_package(folder, REPO_ROOT) as package:
        own = [i for i in package.issues if i.code == "intake.depth_limit"]
        assert len(own) == 1 and own[0].severity is Severity.WARNING
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        plan, result = _install(candidate, custom_copy, tmp_path)
    assert result.ok, result.issues
    for issues in (plan.issues, result.issues):
        found = [i for i in issues if i.code == "intake.depth_limit"]
        assert found == own


def test_package_issue_reaches_install_result_from_a_zip(custom_copy, ul_package, tmp_path):
    package, candidate = ul_package
    own = [i for i in package.issues if i.code == "intake.ignored_members"]
    assert len(own) == 1 and own[0].severity is Severity.INFO
    plan, result = _install(candidate, custom_copy, tmp_path)
    assert result.ok, result.issues
    assert [i for i in plan.issues if i.code == "intake.ignored_members"] == own
    assert [i for i in result.issues if i.code == "intake.ignored_members"] == own


def test_sc3_new_library_pair(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    layout = custom_copy
    plan, result = _install(candidate, layout, tmp_path, library=NEW_LIBRARY)
    assert result.ok, result.issues
    assert result.new_library is True and plan.new_symbol_lib and plan.new_footprint_lib
    sym_path = layout.symbols_dir / f"{NEW_LIBRARY}.kicad_sym"
    pretty = layout.footprints_dir / f"{NEW_LIBRARY}.pretty"
    assert sym_path.is_file() and (pretty / "DQK0006B.kicad_mod").is_file()
    assert [s.name for s in find_symbols(load(sym_path).root)] == [SYMBOL]
    # A new library has no pre-existing file to back up
    assert result.backup_dir is None


@pytest.mark.parametrize(
    "library, version_mismatch, pair_completed",
    [
        ("IC_Battery_Charger_TI", False, False),
        ("IC_IMU_TDK", True, True),
        ("IC_Magnetometer_Memsic", True, False),
    ],
)
def test_sc3_existing_headers_unchanged(custom_copy, ul_package, tmp_path, library, version_mismatch, pair_completed):
    _, candidate = ul_package
    layout = custom_copy
    sym_path = layout.symbols_dir / f"{library}.kicad_sym"
    original = sym_path.read_bytes()

    plan, result = _install(candidate, layout, tmp_path, library=library)
    assert result.ok, result.issues
    codes = _codes(result.issues)
    assert ("install.version_mismatch" in codes) is version_mismatch
    assert ("install.pair_completed" in codes) is pair_completed
    assert plan.normalised is False

    written = sym_path.read_bytes()
    header = _header(original)
    assert header and written.startswith(header)
    assert [s.name for s in find_symbols(load(sym_path).root)][-1] == SYMBOL
    assert (layout.footprints_dir / f"{library}.pretty" / "DQK0006B.kicad_mod").is_file()


@pytest.mark.parametrize("fail_on", [1, 2, 3])
def test_sc4_fail_on_each_write(custom_copy, ul_package, tmp_path, snapshot, monkeypatch, fail_on):
    _, candidate = ul_package
    layout = custom_copy
    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, NO_CLI)
    assert not plan.blocked, plan.issues
    writes = [op for op in plan.ops if op.kind != "mkdir"]
    assert fail_on <= len(writes), "the install has fewer writes than the injected failure position"
    before = snapshot(layout.custom_dir)

    real = fsutil.atomic_write_bytes
    state = {"calls": 0, "failed": False}

    def flaky(path, data, **kwargs):
        if not state["failed"]:
            state["calls"] += 1
            if state["calls"] == fail_on:
                state["failed"] = True
                return Issue(Severity.ERROR, "fs.write_failed", "injected")
        return real(path, data, **kwargs)

    monkeypatch.setattr(fsutil, "atomic_write_bytes", flaky)
    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert state["failed"] and not result.ok
    assert _codes(i for i in result.issues if i.severity is Severity.ERROR) == ["fs.write_failed", "install.rolled_back"]
    assert snapshot(layout.custom_dir) == before
    assert not list(layout.custom_dir.rglob("*.tmp"))


def test_sc4_model_same_sha_reused(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    layout = custom_copy
    _install(candidate, layout, tmp_path)
    model = layout.models_dir / f"{SYMBOL}.stp"
    before = model.stat().st_mtime_ns

    plan, result = _install(candidate, layout, tmp_path, library=NEW_LIBRARY)
    assert result.ok, result.issues
    assert not [op for op in plan.ops if op.kind == "model"]
    assert not plan.conflicts
    assert model.stat().st_mtime_ns == before
    footprint = load(layout.footprints_dir / f"{NEW_LIBRARY}.pretty" / "DQK0006B.kicad_mod")
    assert [m.path for m in find_models(footprint_name(footprint.root).node)] == [f"{MODEL_DIR_VAR}/{SYMBOL}.stp"]


def test_sc4_model_different_sha_conflict(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    layout = custom_copy
    model = layout.models_dir / f"{SYMBOL}.stp"
    other = b"ISO-10303-21;\nsome other body\nEND-ISO-10303-21;\n"
    model.write_bytes(other)

    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, NO_CLI)
    assert plan.blocked
    assert [(c.key, c.kind, c.resolution) for c in plan.conflicts] == [("model:csd85301q2.stp", "model", None)]
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert model.read_bytes() == other
    assert not (layout.footprints_dir / f"{LIBRARY}.pretty" / "DQK0006B.kicad_mod").exists()


def test_sc5_name_elsewhere_and_verify(custom_copy, ul_package, tmp_path):
    _, candidate = ul_package
    layout = custom_copy
    _install(candidate, layout, tmp_path)
    plan, result = _install(candidate, layout, tmp_path, library=NEW_LIBRARY)

    assert result.ok, result.issues
    elsewhere = [i for i in result.issues if i.code == "verify.name_elsewhere"]
    assert len(elsewhere) == 1 and elsewhere[0].severity is Severity.WARNING
    assert LIBRARY in elsewhere[0].text and SYMBOL in elsewhere[0].text
    # The re-parse, link and model checks all hold on what is now on disk
    again = verify_install(plan)
    assert not [i for i in again if i.severity is Severity.ERROR], again
    assert "verify.name_elsewhere" in _codes(again)


def test_sc5_pin_pad_mismatch(custom_copy, tmp_path):
    (tmp_path / "src").mkdir()
    zip_path = make_zip(
        tmp_path / "src" / "pkg.zip",
        [
            ("part.kicad_sym", _zip_member(UL_SYMBOL_MEMBER)),
            ("DQK0006B.kicad_mod", vendor_footprint("DQK0006B", pads=tuple(str(n) for n in range(1, 10)))),
        ],
    )
    layout = custom_copy
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        plan, result = _install(candidate, layout, tmp_path)
    assert result.ok, result.issues
    mismatch = [i for i in result.issues if i.code == "verify.pin_pad_mismatch"]
    assert len(mismatch) == 1 and mismatch[0].severity is Severity.WARNING
    assert "9" in mismatch[0].text and SYMBOL in mismatch[0].text


def test_second_install_is_noop(custom_copy, ul_package, tmp_path, snapshot):
    _, candidate = ul_package
    layout = custom_copy
    _install(candidate, layout, tmp_path)
    custom_after_first = snapshot(layout.custom_dir)
    backups_after_first = snapshot(tmp_path / "bk")

    plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, NO_CLI)
    assert plan.is_noop and plan.ops == () and plan.conflicts == ()
    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert result.touched == ()
    assert result.backup_dir is None
    assert [i.severity for i in result.issues if i.code == "install.nothing_to_do"] == [Severity.INFO]
    assert snapshot(layout.custom_dir) == custom_after_first
    assert snapshot(tmp_path / "bk") == backups_after_first


def test_second_install_new_library_is_noop(custom_copy, ul_package, tmp_path, snapshot):
    _, candidate = ul_package
    layout = custom_copy
    _install(candidate, layout, tmp_path, library=NEW_LIBRARY)
    custom_after_first = snapshot(layout.custom_dir)

    plan = build_plan(candidate, InstallOptions(library=NEW_LIBRARY), layout, NO_CLI)
    assert plan.is_noop and plan.ops == ()
    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert result.touched == () and result.backup_dir is None
    assert "install.nothing_to_do" in _codes(result.issues)
    assert snapshot(layout.custom_dir) == custom_after_first
    assert not (tmp_path / "bk").exists()


# -- real kicad-cli: load check, the CONTEXT version scenarios, UAT scratch install (plan 04-10, Task 2) ----------


@pytest.fixture
def real_tools(kicad_cli_path):
    """The tools the app would detect on this machine; kicad-cli is present because kicad_cli_path did not skip."""
    tools = detect_tools(find_kicad_footprint_dir())
    assert tools.kicad_cli == kicad_cli_path
    return tools


def _written_gate_issues(exe, layout, library, footprint_names=("DQK0006B",)):
    """Run the real load check on the library and footprints now on disk."""
    pretty = layout.footprints_dir / f"{library}.pretty"
    footprints = [(name, (pretty / f"{name}.kicad_mod").read_bytes()) for name in footprint_names]
    symbol_lib = (layout.symbols_dir / f"{library}.kicad_sym").read_bytes()
    return kicad_cli.load_gate(exe, library=library, symbol_lib=symbol_lib, footprints=footprints)


@pytest.mark.kicad_cli
def test_cli_load_check_after_install(custom_copy, ul_package, tmp_path, real_tools, kicad_cli_path):
    _, candidate = ul_package
    plan, result = _install(candidate, custom_copy, tmp_path, tools=real_tools)
    assert result.ok, result.issues
    assert "install.cli_not_found" not in _codes(result.issues)
    issues = _written_gate_issues(kicad_cli_path, custom_copy, LIBRARY)
    assert [i for i in issues if i.severity is Severity.ERROR] == [], issues


def _scenario_same_version(candidate, layout, tmp_path, tools):
    plan, result = _install(candidate, layout, tmp_path, tools=tools)
    assert plan.normalised is False
    assert not [c for c in _codes(plan.issues) if c.startswith("install.version")]
    return result, LIBRARY


def _scenario_newer_target(candidate, layout, tmp_path, tools):
    plan, result = _install(candidate, layout, tmp_path, library="IC_Magnetometer_Memsic", tools=tools)
    assert plan.normalised is True and plan.target_version == 20241209
    assert not [c for c in _codes(plan.issues) if c.startswith("install.version")]
    block = layout.symbols_dir.joinpath("IC_Magnetometer_Memsic.kicad_sym").read_text(encoding="utf-8")
    assert "(id " not in block[block.index(f'(symbol "{SYMBOL}"') :]
    return result, "IC_Magnetometer_Memsic"


def _scenario_target_not_cli_format(candidate, layout, tmp_path, tools):
    plan, result = _install(candidate, layout, tmp_path, library="IC_IMU_TDK", tools=tools)
    assert plan.normalised is False
    found = {i.code: i.severity for i in plan.issues}
    assert found["install.version_mismatch"] is Severity.WARNING
    assert found["install.pair_completed"] is Severity.WARNING
    return result, "IC_IMU_TDK"


def _scenario_new_library(candidate, layout, tmp_path, tools):
    plan, result = _install(candidate, layout, tmp_path, library=NEW_LIBRARY, tools=tools)
    text = (layout.symbols_dir / f"{NEW_LIBRARY}.kicad_sym").read_text(encoding="utf-8")
    header = text[: text.index("(symbol ")]
    assert "(version 20241209)" in header and '(generator_version "9.0")' in header
    return result, NEW_LIBRARY


def _scenario_incoming_newer(candidate, layout, tmp_path, tools):
    """The real 20241209 Magnetometer library as the incoming file into the 20211014 Battery Charger library."""
    incoming = (layout.symbols_dir / "IC_Magnetometer_Memsic.kicad_sym").read_bytes()
    src = tmp_path / "src"
    src.mkdir()
    zip_path = make_zip(
        src / "pkg.zip",
        [("MMC5983MA.kicad_sym", incoming), ("DQK0006B.kicad_mod", _zip_member(UL_FOOTPRINT_MEMBER))],
    )
    before = _tree_digest(layout.custom_dir)
    with open_package(zip_path, REPO_ROOT) as package:
        mixed, _ = detect_candidate(package)
        assert mixed is not None
        plan = build_plan(mixed, InstallOptions(library=LIBRARY, symbol="MMC5983MA"), layout, tools)
        assert plan.blocked and not plan.ops
        errors = [i for i in plan.issues if i.severity is Severity.ERROR]
        assert [i.code for i in errors] == ["install.version_newer_than_target"]
        assert "20241209" in errors[0].text and "20211014" in errors[0].text
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert _tree_digest(layout.custom_dir) == before
    return None


_SCENARIOS = {
    "same_version_target": _scenario_same_version,
    "older_incoming_is_normalised": _scenario_newer_target,
    "target_in_another_format_warns": _scenario_target_not_cli_format,
    "incoming_newer_than_target_is_refused": _scenario_incoming_newer,
    "new_library_gets_cli_header": _scenario_new_library,
}


@pytest.mark.kicad_cli
@pytest.mark.parametrize("scenario", list(_SCENARIOS))
def test_cli_version_scenarios(scenario, custom_copy, ul_package, tmp_path, real_tools, kicad_cli_path):
    _, candidate = ul_package
    outcome = _SCENARIOS[scenario](candidate, custom_copy, tmp_path, real_tools)
    if outcome is None:  # a refused plan writes nothing, so there is nothing to load
        return
    result, library = outcome
    assert result.ok, result.issues
    issues = _written_gate_issues(kicad_cli_path, custom_copy, library)
    assert [i for i in issues if i.severity is Severity.ERROR] == [], issues


@pytest.mark.kicad_cli
def test_cli_second_install_is_noop(custom_copy, ul_package, tmp_path, real_tools, snapshot):
    _, candidate = ul_package
    layout = custom_copy
    library = "IC_Magnetometer_Memsic"
    plan, result = _install(candidate, layout, tmp_path, library=library, tools=real_tools)
    assert result.ok and plan.normalised, result.issues
    after_first = snapshot(layout.custom_dir)
    backups = snapshot(tmp_path / "bk")

    again = build_plan(candidate, InstallOptions(library=library), layout, real_tools)
    assert again.is_noop, (again.ops, again.conflicts, again.issues)
    second = apply_plan(again, backup_root=tmp_path / "bk")

    assert second.ok and second.touched == ()
    assert snapshot(layout.custom_dir) == after_first
    assert snapshot(tmp_path / "bk") == backups


@pytest.mark.skipif(not os.environ.get("KICAD_IMPORT_UAT_DIR"), reason="set KICAD_IMPORT_UAT_DIR to build the manual UAT scratch install")
def test_uat_scratch_install(ul_package):
    """Build the owner's KiCad 9 UAT scratch install (D-22) outside the repository; the real Custom/ is only read."""
    uat = Path(os.environ["KICAD_IMPORT_UAT_DIR"]).resolve()
    repo = REPO_ROOT.resolve()
    # T-04-28: a folder inside (or containing) the checkout could land the scratch copy on the real Custom/
    assert uat != repo and repo not in uat.parents and uat not in repo.parents, f"{uat} must lie outside the repository {repo}"
    scratch = uat / "Custom"
    assert not scratch.is_symlink(), f"{scratch} is a link"
    uat.mkdir(parents=True, exist_ok=True)
    if scratch.exists():
        shutil.rmtree(scratch)
    for name in ("Symbols", "Footprints", "3DModels"):
        shutil.copytree(repo / "Custom" / name, scratch / name)

    layout = RepoLayout.for_repo(uat)
    assert layout.custom_dir.resolve().is_relative_to(uat)
    tools = detect_tools(find_kicad_footprint_dir())
    _, candidate = ul_package
    plan, result = _install(candidate, layout, uat, tools=tools)
    assert result.ok, result.issues

    print(f"\nUAT scratch library:   {layout.symbols_dir / (LIBRARY + '.kicad_sym')}")
    print(f"UAT scratch footprint: {layout.footprints_dir / (LIBRARY + '.pretty') / 'DQK0006B.kicad_mod'}")
    print(f"UAT scratch model:     {layout.models_dir / (SYMBOL + '.stp')}")
    print(f"UAT scratch pretty:    {layout.footprints_dir / (LIBRARY + '.pretty')}")
    print(f"UAT scratch 3D folder: {layout.models_dir}")
