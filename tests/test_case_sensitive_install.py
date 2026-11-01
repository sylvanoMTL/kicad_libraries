"""VER-02, the owner's UAT file: real installs on a case-sensitive folder (Phase 12, D-13, D-14).

Every test here builds its Custom/ layout inside a folder that really tells "part.STEP" from
"PART.step" (see casefixtures.case_sensitive_dir) and runs the real apply_plan on it.
Nothing mocks a directory listing and nothing touches the live Custom/. When no such folder can
be made, the tests skip with a message starting "could not make a case-sensitive folder:".
"""

import os

import pytest
from casefixtures import case_sensitive_dir
from test_install_plan import (
    LIBRARY,
    MODEL_KEY,
    V6,
    _open,
    _put_model,
    _res,
    _target_layout,
    _vendor,
    _with,
)
from zipfixtures import STEP_BYTES

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, Rename, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import find_models, footprint_name, parse_bytes


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
