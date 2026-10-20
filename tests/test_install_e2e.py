"""The Ultra Librarian sample installed into a tmp_path copy of Custom/: ROADMAP Phase 4 success criteria 1-5 end to end.

Every install targets the ``custom_copy`` fixture (a tmp_path copy of the real Custom/ libraries) or a
tmp_path folder; the module-scoped ``_real_custom_untouched`` fixture proves the checkout's own Custom/
is never written (D-22).
"""

import hashlib
import zipfile
from pathlib import Path

import pytest
from installfixtures import vendor_footprint
from zipfixtures import UL_MODEL_MEMBER, UL_SYMBOL_MEMBER, make_zip, unpack_sample

from kicad_lib_manager import fsutil
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, InstallOptions, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.verify import verify_install
from kicad_lib_manager.kicad_files import (
    find_models,
    find_property,
    find_symbol,
    find_symbols,
    footprint_name,
    load,
)
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
