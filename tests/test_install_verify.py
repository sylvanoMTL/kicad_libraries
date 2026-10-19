"""Post-install verification: hard checks, pin/pad and name-elsewhere warnings (Phase 4, plan 05).

Every plan here is built by hand over a synthetic Custom/ tree under tmp_path, so nothing reads the
real Custom/ submodule. verify.py is reached through the module object so a missing function fails
its own test instead of breaking collection.
"""

import time
from pathlib import Path

import pytest
from installfixtures import extends_pair, target_lib, vendor_footprint, vendor_symbol_lib
from zipfixtures import symbol_lib, write_custom_layout

from kicad_lib_manager import library_scanner
from kicad_lib_manager.importer import verify
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, FileOp, InstallPlan, ToolContext
from kicad_lib_manager.kicad_files import find_symbol, footprint_name, parse_bytes
from kicad_lib_manager.models import Severity

LIB = "IC_Test_TI"


def _layout(tmp_path: Path) -> RepoLayout:
    write_custom_layout(tmp_path, [], [])
    return RepoLayout.for_repo(tmp_path)


def make_plan(
    tmp_path: Path,
    *,
    sym: bytes | None = None,
    footprints: dict[str, bytes] | None = None,
    models: tuple[str, ...] = ("X.stp",),
    library: str = LIB,
    **fields,
) -> InstallPlan:
    """Write a consistent install under tmp_path and return the plan that describes it.

    Defaults: symbol PART linked to LIB:FP, footprint FP with two pads and the model X.stp.
    Keyword fields override InstallPlan fields.
    """
    layout = _layout(tmp_path)
    sym_path = layout.symbols_dir / f"{library}.kicad_sym"
    if sym is None:
        sym = vendor_symbol_lib("PART", footprint_field=f"{library}:FP")
    sym_path.write_bytes(sym)
    pretty = layout.footprints_dir / f"{library}.pretty"
    pretty.mkdir()
    if footprints is None:
        footprints = {"FP.kicad_mod": vendor_footprint("FP", model=f"{MODEL_DIR_VAR}/X.stp")}
    ops = [FileOp("symbol_lib", sym_path, data=sym)]
    for file_name, data in footprints.items():
        (pretty / file_name).write_bytes(data)
        ops.append(FileOp("footprint", pretty / file_name, data=data))
    for model in models:
        (layout.models_dir / model).write_bytes(b"step")
    values = dict(
        vendor="Ultra Librarian",
        source=tmp_path / "pkg.zip",
        layout=layout,
        tools=ToolContext(),
        library=library,
        new_symbol_lib=False,
        new_footprint_lib=False,
        symbol_names=("PART",),
        footprint_names=("FP",),
        linked_footprint="FP",
        model_file="X.stp",
        source_version=20211014,
        target_version=20211014,
        normalised=False,
        ops=tuple(ops),
        conflicts=(),
        renames=(),
        issues=(),
    )
    values.update(fields)
    return InstallPlan(**values)


def _by_code(issues, code):
    return [i for i in issues if i.code == code]


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


# -- hard checks (INST-08, D-18) ------------------------------------------------


def test_hard_ok(tmp_path):
    plan = make_plan(tmp_path)
    assert verify.verify_install(plan) == []


def test_hard_parse_failed(tmp_path):
    good = vendor_symbol_lib("PART", footprint_field=f"{LIB}:FP")
    plan = make_plan(tmp_path, sym=good[: len(good) // 2])
    found = _by_code(verify.verify_install(plan), "verify.parse_failed")
    assert len(found) == 1
    assert found[0].severity is Severity.ERROR
    assert f"{LIB}.kicad_sym" in found[0].text


def test_hard_parse_failed_footprint(tmp_path):
    plan = make_plan(tmp_path, footprints={"FP.kicad_mod": b'(footprint "FP" (layer "F.Cu")'})
    found = _by_code(verify.verify_install(plan), "verify.parse_failed")
    assert len(found) == 1
    assert "FP.kicad_mod" in found[0].text


def test_hard_symbol_missing(tmp_path):
    plan = make_plan(tmp_path, symbol_names=("NOPE",))
    found = _by_code(verify.verify_install(plan), "verify.symbol_missing")
    assert len(found) == 1
    assert "NOPE" in found[0].text


def test_hard_symbol_duplicated(tmp_path):
    sym = symbol_lib(("PART", "PART"), props={"Footprint": f"{LIB}:FP"})
    plan = make_plan(tmp_path, sym=sym)
    issues = verify.verify_install(plan)
    found = _by_code(issues, "verify.symbol_duplicated")
    assert len(found) == 1
    assert found[0].severity is Severity.ERROR
    assert not _by_code(issues, "verify.symbol_missing")


def test_hard_link_case(tmp_path):
    sym = vendor_symbol_lib("PART", footprint_field=f"{LIB}:DQK0006B")
    plan = make_plan(
        tmp_path,
        sym=sym,
        footprints={"dqk0006b.kicad_mod": vendor_footprint("dqk0006b", model=f"{MODEL_DIR_VAR}/X.stp")},
        footprint_names=("DQK0006B",),
        linked_footprint="DQK0006B",
    )
    found = _by_code(verify.verify_install(plan), "verify.link_unresolved")
    assert len(found) == 1
    assert "DQK0006B" in found[0].text


def test_hard_link_internal_name(tmp_path):
    plan = make_plan(
        tmp_path, footprints={"FP.kicad_mod": vendor_footprint("OTHER", model=f"{MODEL_DIR_VAR}/X.stp")}
    )
    found = _by_code(verify.verify_install(plan), "verify.link_unresolved")
    assert len(found) == 1
    assert "OTHER" in found[0].text


def test_hard_link_wrong_library(tmp_path):
    sym = vendor_symbol_lib("PART", footprint_field="Elsewhere_Lib:FP")
    plan = make_plan(tmp_path, sym=sym)
    found = _by_code(verify.verify_install(plan), "verify.link_unresolved")
    assert len(found) == 1
    assert "Elsewhere_Lib:FP" in found[0].text


def test_hard_link_skipped_without_planned_link(tmp_path):
    sym = vendor_symbol_lib("PART", footprint_field="Elsewhere_Lib:FP")
    plan = make_plan(tmp_path, sym=sym, linked_footprint=None, model_file=None)
    assert _errors(verify.verify_install(plan)) == []


def test_hard_model_case(tmp_path):
    plan = make_plan(tmp_path, models=("x.STP",))
    found = _by_code(verify.verify_install(plan), "verify.model_missing")
    assert len(found) == 1
    assert "X.stp" in found[0].text


def test_hard_model_path_mismatch(tmp_path):
    plan = make_plan(
        tmp_path, footprints={"FP.kicad_mod": vendor_footprint("FP", model="${KIPRJMOD}/other.stp")}
    )
    assert len(_by_code(verify.verify_install(plan), "verify.model_missing")) == 1


def test_hard_collects_every_failure(tmp_path):
    sym = vendor_symbol_lib("PART", footprint_field="Elsewhere_Lib:FP")
    plan = make_plan(tmp_path, sym=sym, symbol_names=("NOPE", "PART"))
    codes = {i.code for i in _errors(verify.verify_install(plan))}
    assert {"verify.symbol_missing", "verify.link_unresolved"} <= codes


def test_hard_reads_disk(tmp_path):
    plan = make_plan(tmp_path)
    assert verify.verify_install(plan) == []
    good = plan.ops[1].data
    target = plan.ops[1].path
    target.write_bytes(vendor_footprint("CHANGED", model=f"{MODEL_DIR_VAR}/X.stp"))
    assert plan.ops[1].data == good
    found = _by_code(verify.verify_install(plan), "verify.link_unresolved")
    assert len(found) == 1


def test_hard_reads_symbol_from_disk(tmp_path):
    plan = make_plan(tmp_path)
    plan.symbol_lib_path.write_bytes(vendor_symbol_lib("ELSE", footprint_field=f"{LIB}:FP"))
    assert len(_by_code(verify.verify_install(plan), "verify.symbol_missing")) == 1


# -- pin/pad soft check (POST-04, D-09, D-20) -----------------------------------


def _pin_pad_plan(tmp_path, *, pins=None, pads=("1", "2"), npth=False):
    sym = vendor_symbol_lib("PART", footprint_field=f"{LIB}:FP", pins=pins)
    fp = vendor_footprint("FP", pads=pads, npth=npth, model=f"{MODEL_DIR_VAR}/X.stp")
    return make_plan(tmp_path, sym=sym, footprints={"FP.kicad_mod": fp})


def _mismatch(issues):
    found = _by_code(issues, "verify.pin_pad_mismatch")
    assert len(found) <= 1, found
    return found[0] if found else None


def test_pin_pad_match(tmp_path):
    plan = _pin_pad_plan(tmp_path, pins=(tuple("12345678"),), pads=tuple("12345678"))
    assert _mismatch(verify.verify_install(plan)) is None


def test_pin_pad_extra_pad(tmp_path):
    plan = _pin_pad_plan(tmp_path, pads=("1", "2", "3"))
    issues = verify.verify_install(plan)
    issue = _mismatch(issues)
    assert issue.severity is Severity.WARNING
    assert "pads with no pin: 3" in issue.text
    assert "pins with no pad" not in issue.text
    assert _errors(issues) == []


def test_pin_pad_missing_pad(tmp_path):
    plan = _pin_pad_plan(tmp_path, pins=(("1", "2", "3"),), pads=("1", "2"))
    issue = _mismatch(verify.verify_install(plan))
    assert "pins with no pad: 3" in issue.text
    assert "pads with no pin" not in issue.text


def test_pin_pad_both_directions(tmp_path):
    plan = _pin_pad_plan(tmp_path, pins=(("1", "2", "3"),), pads=("1", "2", "4"))
    issues = verify.verify_install(plan)
    issue = _mismatch(issues)
    assert "pins with no pad: 3" in issue.text and "pads with no pin: 4" in issue.text
    assert len(_by_code(issues, "verify.pin_pad_mismatch")) == 1
    assert f"{LIB}:FP" in issue.text


def test_pin_pad_ignores_empty(tmp_path):
    plan = _pin_pad_plan(tmp_path, pads=("1", "2"), npth=True)
    assert _mismatch(verify.verify_install(plan)) is None
    root = parse_bytes(vendor_footprint("FP", pads=("1",), npth=True), "fp.kicad_mod").root
    assert verify.footprint_pad_numbers(footprint_name(root).node) == {"1"}


def test_pin_pad_extends_child(tmp_path):
    sym = extends_pair("PARENT_X", "CHILD_Y").replace(b'"Footprint" ""', f'"Footprint" "{LIB}:FP"'.encode())
    plan = make_plan(tmp_path, sym=sym, symbol_names=("PARENT_X", "CHILD_Y"))
    issues = verify.verify_install(plan)
    assert _mismatch(issues) is None
    assert _errors(issues) == []
    root = parse_bytes(sym, "lib.kicad_sym").root
    assert verify.symbol_pin_numbers(root, "CHILD_Y") == {"1", "2"}
    assert find_symbol(root, "CHILD_Y") is not None


def test_pin_pad_extends_child_still_reports_real_mismatch(tmp_path):
    sym = extends_pair("PARENT_X", "CHILD_Y").replace(b'"Footprint" ""', f'"Footprint" "{LIB}:FP"'.encode())
    fp = vendor_footprint("FP", pads=("1", "2", "3"), model=f"{MODEL_DIR_VAR}/X.stp")
    plan = make_plan(tmp_path, sym=sym, symbol_names=("PARENT_X", "CHILD_Y"), footprints={"FP.kicad_mod": fp})
    assert "pads with no pin: 3" in _mismatch(verify.verify_install(plan)).text


def test_pin_pad_all_units(tmp_path):
    sym = vendor_symbol_lib("PART", units=2, pins=(("1", "2"), ("3", "4")))
    root = parse_bytes(sym, "lib.kicad_sym").root
    assert verify.symbol_pin_numbers(root, "PART") == {"1", "2", "3", "4"}
    assert verify.symbol_pin_numbers(root, "ABSENT") == set()


def test_pin_pad_extends_cycle_terminates():
    text = (
        b'(kicad_symbol_lib (version 20211014)\n'
        b'  (symbol "A" (extends "B"))\n'
        b'  (symbol "B" (extends "A")\n'
        b'    (symbol "B_1_1" (pin passive line (at 0 0 0) (length 1) (name "~") (number "7"))))\n'
        b')\n'
    )
    root = parse_bytes(text, "lib.kicad_sym").root
    assert verify.symbol_pin_numbers(root, "A") == {"7"}


def test_pin_pad_numbers_unquoted_pad_atoms():
    text = b'(footprint "FP" (pad 1 smd rect (at 0 0) (size 1 1)) (pad "2" smd rect (at 1 0) (size 1 1)))'
    root = parse_bytes(text, "fp.kicad_mod").root
    assert verify.footprint_pad_numbers(footprint_name(root).node) == {"1", "2"}


def test_pin_pad_numbers_sorted():
    issues = verify.pin_pad_issues("S", "L:FP", {"2", "10", "1", "A10", "A2"}, set())
    assert len(issues) == 1
    assert "pins with no pad: 1, 2, 10, A2, A10" in issues[0].text


def test_pin_pad_issues_equal_sets():
    assert verify.pin_pad_issues("S", "L:FP", {"1", "2"}, {"2", "1"}) == []


def test_pin_pad_linked_footprint_is_the_one_read_from_disk(tmp_path):
    """A skipped footprint (D-09) is checked as it exists on disk, not as the vendor drew it."""
    plan = _pin_pad_plan(tmp_path, pads=("1", "2"))
    assert _mismatch(verify.verify_install(plan)) is None
    plan.pretty_path.joinpath("FP.kicad_mod").write_bytes(
        vendor_footprint("FP", pads=("1", "2", "9"), model=f"{MODEL_DIR_VAR}/X.stp")
    )
    assert "pads with no pin: 9" in _mismatch(verify.verify_install(plan)).text


def test_pin_pad_not_checked_without_a_link(tmp_path):
    sym = vendor_symbol_lib("PART", footprint_field="")
    fp = vendor_footprint("FP", pads=("1", "2", "3"))
    plan = make_plan(tmp_path, sym=sym, footprints={"FP.kicad_mod": fp}, linked_footprint=None, model_file=None)
    assert _mismatch(verify.verify_install(plan)) is None


# -- name elsewhere (POST-03, D-21) ---------------------------------------------

NAME = "CSD85301Q2"


def _search(layout, *names, tools=None, exclude=LIB):
    return verify.find_name_elsewhere(
        names or (NAME,), layout, exclude_library=exclude, tools=tools if tools is not None else ToolContext()
    )


def _names_in(layout, library, *names, lib_dir=None):
    folder = lib_dir if lib_dir is not None else layout.symbols_dir
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{library}.kicad_sym").write_bytes(symbol_lib(names))


def test_elsewhere_other_custom_lib(tmp_path):
    layout = _layout(tmp_path)
    _names_in(layout, LIB, NAME)
    _names_in(layout, "IC_Other_TI", NAME)
    issues = _search(layout)
    assert len(issues) == 1
    assert issues[0].severity is Severity.WARNING
    assert issues[0].code == "verify.name_elsewhere"
    assert NAME in issues[0].text and "IC_Other_TI" in issues[0].text
    assert LIB not in issues[0].text


def test_elsewhere_target_excluded(tmp_path):
    layout = _layout(tmp_path)
    _names_in(layout, LIB, NAME)
    _names_in(layout, "IC_Other_TI", "SOMETHING_ELSE")
    assert _search(layout) == []


def test_elsewhere_sub_symbol_not_counted(tmp_path):
    layout = _layout(tmp_path)
    (layout.symbols_dir / "IC_Other_TI.kicad_sym").write_bytes(
        f'(kicad_symbol_lib (version 20211014)\n  (symbol "PARENT"\n    (symbol "{NAME}_1_1"\n    )\n  )\n)\n'.encode()
    )
    (layout.symbols_dir / "IC_Third_TI.kicad_sym").write_bytes(
        f'(kicad_symbol_lib (version 20211014)\n  (symbol "PARENT"\n    (symbol "{NAME}"\n    )\n  )\n)\n'.encode()
    )
    (layout.symbols_dir / "IC_Fourth_TI.kicad_sym").write_bytes(
        f'(kicad_symbol_lib\n\t(symbol "PARENT"\n\t\t(symbol "{NAME}"\n\t\t)\n\t)\n)\n'.encode()
    )
    assert _search(layout) == []


def test_elsewhere_tab_indent_and_crlf(tmp_path):
    layout = _layout(tmp_path)
    (layout.symbols_dir / "IC_Tabs_TI.kicad_sym").write_bytes(target_lib(20231120, (NAME,)))
    (layout.symbols_dir / "IC_Crlf_TI.kicad_sym").write_bytes(target_lib(20211014, (NAME,)))
    text = _search(layout)[0].text
    assert "IC_Tabs_TI" in text and "IC_Crlf_TI" in text


def test_elsewhere_one_line_header(tmp_path):
    layout = _layout(tmp_path)
    (layout.symbols_dir / "IC_Flat_TI.kicad_sym").write_bytes(
        f'(kicad_symbol_lib (version 20211014) (symbol "{NAME}" (in_bom yes)))\n'.encode()
    )
    assert "IC_Flat_TI" in _search(layout)[0].text


def test_elsewhere_stock_dir(tmp_path):
    layout = _layout(tmp_path)
    stock = tmp_path / "stock"
    _names_in(layout, "Device", NAME, lib_dir=stock)
    issues = _search(layout, tools=ToolContext(kicad_symbols_dir=stock))
    assert len(issues) == 1
    assert "KiCad:Device" in issues[0].text


def test_elsewhere_wurth(tmp_path):
    layout = _layout(tmp_path)
    assert _search(layout) == []
    nested = tmp_path / "WurthElektronik" / "KiCad-Library" / "symbols"
    _names_in(layout, "WE-Connector", NAME, lib_dir=nested)
    issues = _search(layout)
    assert len(issues) == 1
    assert "WurthElektronik:WE-Connector" in issues[0].text


def test_elsewhere_extra_dirs(tmp_path):
    layout = _layout(tmp_path)
    extra = tmp_path / "extra"
    _names_in(layout, "Mine", NAME, lib_dir=extra)
    issues = _search(layout, tools=ToolContext(extra_symbol_dirs=(extra,)))
    assert len(issues) == 1 and "Mine" in issues[0].text


def test_elsewhere_none(tmp_path):
    layout = _layout(tmp_path)
    assert _search(layout) == []
    missing = ToolContext(kicad_symbols_dir=tmp_path / "no_such_folder", extra_symbol_dirs=(tmp_path / "none",))
    assert _search(layout, tools=missing) == []
    assert verify.find_name_elsewhere((), layout, exclude_library=LIB, tools=ToolContext()) == []


def test_elsewhere_labels_each_library_once_per_name(tmp_path):
    layout = _layout(tmp_path)
    _names_in(layout, "IC_A_TI", NAME, "OTHER_PART")
    _names_in(layout, "IC_B_TI", NAME)
    issues = _search(layout, NAME, "OTHER_PART", "ABSENT")
    assert [i.text.split(" ")[0] for i in issues] == [NAME, "OTHER_PART"]
    assert "IC_A_TI" in issues[0].text and "IC_B_TI" in issues[0].text
    assert "IC_B_TI" not in issues[1].text


def test_elsewhere_case_and_quotes(tmp_path):
    layout = _layout(tmp_path)
    _names_in(layout, "IC_Other_TI", NAME, 'A"B', "C\\D")
    assert _search(layout, NAME.lower()) == []
    assert len(_search(layout, 'A"B')) == 1
    assert len(_search(layout, "C\\D")) == 1
    assert _search(layout, "A") == []


def test_elsewhere_no_full_parse(tmp_path, monkeypatch):
    from kicad_lib_manager import kicad_files, sexpr

    layout = _layout(tmp_path)
    filler = "".join(f'  (symbol "FILLER_{i}"\n  )\n' for i in range(80000))
    big = f"(kicad_symbol_lib (version 20211014)\n{filler})\n".encode()
    assert len(big) > 2_000_000
    (layout.symbols_dir / "IC_Big_TI.kicad_sym").write_bytes(big)
    _names_in(layout, "IC_Other_TI", NAME)

    def boom(*args, **kwargs):
        raise AssertionError("a library was fully parsed")

    for owner, attr in ((kicad_files, "parse_bytes"), (kicad_files, "load"), (kicad_files, "parse"), (sexpr, "parse"), (verify, "load")):
        monkeypatch.setattr(owner, attr, boom)
    issues = _search(layout)
    assert len(issues) == 1 and "IC_Other_TI" in issues[0].text and "IC_Big_TI" not in issues[0].text


def test_elsewhere_search_dirs_order(tmp_path):
    layout = _layout(tmp_path)
    assert verify.symbol_search_dirs(layout, ToolContext()) == [("", layout.symbols_dir)]
    stock, extra = tmp_path / "stock", tmp_path / "extra"
    stock.mkdir()
    extra.mkdir()
    (tmp_path / "WurthElektronik").mkdir()
    dirs = verify.symbol_search_dirs(layout, ToolContext(kicad_symbols_dir=stock, extra_symbol_dirs=(extra,)))
    assert dirs == [
        ("", layout.symbols_dir),
        ("WurthElektronik:", tmp_path / "WurthElektronik"),
        ("KiCad:", stock),
        ("", extra),
    ]


def test_elsewhere_verify_install_appends_warning_without_blocking(tmp_path):
    plan = make_plan(tmp_path)
    _names_in(plan.layout, "IC_Other_TI", "PART")
    issues = verify.verify_install(plan)
    assert _errors(issues) == []
    found = _by_code(issues, "verify.name_elsewhere")
    assert len(found) == 1 and "IC_Other_TI" in found[0].text


def test_elsewhere_real_stock():
    fp_dir = library_scanner.find_kicad_footprint_dir()
    stock = fp_dir.parent / "symbols" if fp_dir is not None else None
    if stock is None or not stock.is_dir():
        pytest.skip("no KiCad install with a stock symbols folder")
    layout = RepoLayout.for_repo(Path("no_such_repo_for_stock_search"))
    started = time.perf_counter()
    issues = _search(layout, "R", tools=ToolContext(kicad_symbols_dir=stock))
    elapsed = time.perf_counter() - started
    assert elapsed < 5, elapsed
    assert len(issues) == 1
    assert "KiCad:Device" in issues[0].text
