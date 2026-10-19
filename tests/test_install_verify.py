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
