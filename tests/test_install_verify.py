"""Post-install verification: hard checks, pin/pad and name-elsewhere warnings (Phase 4, plan 05).

Every plan here is built by hand over a synthetic Custom/ tree under tmp_path, so nothing reads the
real Custom/ submodule. verify.py is reached through the module object so a missing function fails
its own test instead of breaking collection.
"""

import time
from pathlib import Path

import pytest
from installfixtures import extends_pair, vendor_footprint, vendor_symbol_lib
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
