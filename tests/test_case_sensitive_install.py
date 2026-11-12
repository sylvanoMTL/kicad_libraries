"""VER-02, the owner's UAT file: real installs on a case-sensitive folder (Phase 12, D-13, D-14).

Every test here builds its Custom/ layout inside a folder that really tells "part.STEP" from
"PART.step" (see casefixtures.case_sensitive_dir) and runs the real apply_plan on it.
Nothing mocks a directory listing and nothing touches the live Custom/. When no such folder can
be made, the tests skip with a message starting "could not make a case-sensitive folder:".
"""

import dataclasses
import os

import pytest
from casefixtures import case_sensitive_dir
from test_install_apply import _flaky_writes, _hand_plan, _sha
from test_install_plan import (
    FP_KEY,
    LIBRARY,
    MODEL_KEY,
    V6,
    VENDOR,
    _open,
    _pretty,
    _put_footprint,
    _put_model,
    _res,
    _target_layout,
    _vendor,
    _with,
)
from zipfixtures import STEP_BYTES, footprint_library_for, write_custom_layout

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, FileOp, Rename, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import find_models, find_property, find_symbol, footprint_name, parse_bytes
from kicad_lib_manager.widgets.import_dialog import incoming_op


@pytest.fixture
def case_root(tmp_path):
    """An empty case-sensitive folder under tmp_path."""
    return case_sensitive_dir(tmp_path / "cs")


def _spellings(folder, name):
    """Every on-disk spelling in folder of name, compared ignoring case."""
    return [n for n in os.listdir(folder) if n.casefold() == name.casefold()]


def test_overwrite_model_twin_keeps_disk_spelling(tmp_path, case_root):
    layout = _target_layout(case_root, V6)
    _put_model(layout, "part.STEP", b"other bytes")
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({MODEL_KEY: _res("overwrite")}), layout, ToolContext())
        assert not plan.blocked, plan.issues
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    assert _spellings(layout.models_dir, "part.step") == ["part.STEP"]
    assert (layout.models_dir / "part.STEP").read_bytes() == STEP_BYTES
    op = next(op for op in plan.ops if op.kind == "model")
    assert op.path.name == "part.STEP" and op.listed_path is None
    assert plan.model_file == "part.STEP"
    footprint = next(op for op in plan.ops if op.kind == "footprint")
    written = parse_bytes(footprint.path.read_bytes(), "fp")
    links = [m.path for m in find_models(footprint_name(written.root).node)]
    assert links == [f"{MODEL_DIR_VAR}/part.STEP"]
    assert Rename("model", "PART.step", "part.STEP") in plan.renames


def test_rollback_removes_hand_built_twin(tmp_path, case_root, snapshot, monkeypatch):
    write_custom_layout(case_root, [], [])
    layout = RepoLayout.for_repo(case_root)
    original = b"original model bytes"
    twin = layout.models_dir / "foo.STEP"
    twin.write_bytes(original)
    plan = _hand_plan(layout, new_library=True)
    overwrite = FileOp(
        "model", layout.models_dir / "Foo.step", data=STEP_BYTES, base_sha256=_sha(original), listed_path=twin
    )
    plan = dataclasses.replace(plan, ops=tuple(overwrite if op.kind == "model" else op for op in plan.ops))
    before = snapshot(layout.custom_dir)
    _flaky_writes(monkeypatch, fail_on=2)  # the model write under the other spelling succeeds, the footprint fails

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert not result.ok
    assert _spellings(layout.models_dir, "foo.step") == ["foo.STEP"]
    assert twin.read_bytes() == original
    assert snapshot(layout.custom_dir) == before
    assert (result.backup_dir / "foo.STEP_backup_1").read_bytes() == original


def test_rollback_planner_overwrite_keeps_disk_spelling(tmp_path, case_root, monkeypatch):
    layout = _target_layout(case_root, V6)
    _put_model(layout, "part.STEP", b"other bytes")
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({MODEL_KEY: _res("overwrite")}), layout, ToolContext())
        assert not plan.blocked, plan.issues
        state = _flaky_writes(monkeypatch, fail_on=2)  # the model overwrite succeeds, the footprint fails
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert state["paths"][0].name == "part.STEP"
    assert _spellings(layout.models_dir, "part.step") == ["part.STEP"]
    assert (layout.models_dir / "part.STEP").read_bytes() == b"other bytes"


def test_overwrite_footprint_twin_keeps_disk_spelling(tmp_path, case_root):
    layout = _target_layout(case_root, V6)
    _put_footprint(layout, "fp.kicad_mod")
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({FP_KEY: _res("overwrite")}), layout, ToolContext())
        assert not plan.blocked, plan.issues
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    assert _spellings(_pretty(layout), "fp.kicad_mod") == ["fp.kicad_mod"]
    library = parse_bytes((layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes(), "lib")
    field = find_property(find_symbol(library.root, VENDOR).node, "Footprint")
    assert field.value == f"{footprint_library_for(LIBRARY)}:fp"
    assert Rename("footprint", "FP", "fp") in plan.renames


def test_incoming_op_finds_case_twin_footprint(tmp_path):
    layout = _target_layout(tmp_path, V6)
    _put_footprint(layout, "fp.kicad_mod")
    with _open(tmp_path, _vendor()) as (_, candidate):
        plan = build_plan(candidate, _with({FP_KEY: _res("overwrite")}), layout, ToolContext())
    conflict = next(c for c in plan.conflicts if c.key == FP_KEY)
    op = incoming_op(plan, conflict)
    assert op is not None and op.path.name == "fp.kicad_mod"
