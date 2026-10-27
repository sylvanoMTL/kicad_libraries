"""attach_models and the install of an attached model (plan 07-07, G-07-2).

A SnapEDA CAD zip holds no 3D model; the model is a separate download. attach_models merges a second
source's models into the open candidate. These tests cover its rules (magic check, filename clash,
duplicate bytes, nothing mutated) and prove that an attached model flows through the unchanged
build_plan / apply_plan: saved as <MPN>.<ext>, linked through ${CUSTOM_3DMODEL_DIR}, re-planned as a
no-op, and refused cleanly when its source changed or was closed. Everything is synthetic and built
under tmp_path; the owner's real Custom/ tree is never read.
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from vendorfixtures import (
    SNAPEDA_FOOTPRINT,
    SNAPEDA_MODEL_STEM,
    SNAPEDA_MODEL_ZIP_NAME,
    SNAPEDA_MPN,
    SNAPEDA_SYMBOL,
    snapeda_members,
    snapeda_model_zip,
    snapeda_zip,
)
from zipfixtures import (
    CURRENT_ATOMIC_FOOTPRINT_LIBS,
    CURRENT_ATOMIC_SYMBOL_LIBS,
    REPO_ROOT,
    STEP_BYTES,
    VRML_BYTES,
    footprint_library_for,
    make_zip,
    write_custom_layout,
)

from kicad_lib_manager.importer.adapters.base import attach_models
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_model_source, open_package
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import find_models, footprint_name, load
from kicad_lib_manager.models import Severity

LIBRARY = "Atomic_Connector"


@pytest.fixture(autouse=True)
def _tmpdir(tmp_path, monkeypatch):
    """Staging folder under tmp_path, created first because tempfile never creates a missing one."""
    folder = tmp_path / "tmp"
    folder.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


@contextmanager
def _candidate(tmp_path, members=None):
    """Open a synthetic SnapEDA package (optionally with other members) and yield its candidate."""
    path = tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip"
    if members is None:
        snapeda_zip(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        make_zip(path, members)
    with open_package(path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield candidate


def _layout(tmp_path) -> RepoLayout:
    write_custom_layout(tmp_path / "repo", CURRENT_ATOMIC_SYMBOL_LIBS, CURRENT_ATOMIC_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(tmp_path / "repo")


def _codes(issues, severity=None):
    return [i.code for i in issues if severity is None or i.severity is severity]


def _zip(tmp_path, name, members):
    path = tmp_path / "dl" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return make_zip(path, members)


def _bare(tmp_path, name, data, folder="pick"):
    path = tmp_path / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_attach_zip_model(tmp_path):
    with _candidate(tmp_path) as candidate:
        assert candidate.models == ()
        before = candidate.issues
        model_path = snapeda_model_zip(tmp_path / "dl" / SNAPEDA_MODEL_ZIP_NAME)
        with open_model_source(model_path, REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
            assert attached is not None
            assert [m.filename for m in attached.models] == [f"{SNAPEDA_MODEL_STEM}.stp"]
            assert attached.models[0].file is model_package.files[0]
            assert "intake.no_model" not in _codes(attached.issues)
            infos = [i for i in issues if i.code == "intake.model_attached"]
            assert len(infos) == 1 and infos[0].severity is Severity.INFO
            assert SNAPEDA_MODEL_ZIP_NAME in infos[0].text
            assert str(tmp_path) not in infos[0].text
            ignored = [i for i in issues if i.code == "intake.ignored_members"]
            assert len(ignored) == 1 and ignored[0] in attached.issues
            for name in ("vendor", "confidence", "source", "symbols", "footprints", "field_rules", "ignored", "legacy_ignored"):
                assert getattr(attached, name) == getattr(candidate, name)
        # the input is never mutated
        assert candidate.models == ()
        assert candidate.issues == before


@pytest.mark.parametrize(("name", "data"), [("part.stp", STEP_BYTES), ("part.wrl", VRML_BYTES)])
def test_attach_bare_model(name, data, tmp_path):
    with _candidate(tmp_path) as candidate:
        with open_model_source(_bare(tmp_path, name, data), REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
            assert attached is not None
            assert [m.filename for m in attached.models] == [name]
            assert _codes(issues) == ["intake.model_attached"]


def test_attach_rejects_wrong_magic(tmp_path):
    with _candidate(tmp_path) as candidate:
        path = _bare(tmp_path, "fake.stp", b"MZ" + b"not a model " * 10)
        with open_model_source(path, REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
        assert attached is None
        assert "intake.content_mismatch" in _codes(issues, Severity.WARNING)
        assert _codes(issues, Severity.ERROR) == ["intake.no_model_in_source"]
        assert candidate.models == ()


def test_attach_rejects_partly_bad_zip(tmp_path):
    """G-07-5: one failing file rejects the whole source; the good file beside it is not attached."""
    source = _zip(tmp_path, "two.zip", [("good.stp", STEP_BYTES), ("bad.step", b"MZ not a model")])
    with _candidate(tmp_path) as candidate:
        with open_model_source(source, REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
        assert attached is None
        assert _codes(issues, Severity.ERROR) == ["intake.unusable_model_in_source"]
        error = next(i for i in issues if i.severity is Severity.ERROR)
        assert "two.zip" in error.text and "bad.step" in error.text
        assert "nothing from it was attached" in error.text
        assert str(tmp_path) not in error.text
        mismatch = [i for i in issues if i.code == "intake.content_mismatch"]
        assert len(mismatch) == 1 and "bad.step" in mismatch[0].text
        assert candidate.models == ()


def test_attach_rejects_bad_beside_duplicate(tmp_path):
    """A bad file beside a duplicate is the partly bad case: the duplicate passes the magic check."""
    members = [*snapeda_members(), ("part.stp", STEP_BYTES)]
    source = _zip(tmp_path, "mix.zip", [("dup.stp", STEP_BYTES), ("bad.stp", b"MZ not a model")])
    with _candidate(tmp_path, members) as candidate:
        with open_model_source(source, REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
        assert attached is None
        assert _codes(issues, Severity.ERROR) == ["intake.unusable_model_in_source"]
        assert "intake.model_already_present" not in _codes(issues)
        assert [m.filename for m in candidate.models] == ["part.stp"]


def test_attach_rejects_all_bad_zip(tmp_path):
    """A zip in which no model passes the check keeps the intake.no_model_in_source wording the user saw."""
    source = _zip(tmp_path, "allbad.zip", [("a.stp", b"MZ not a model"), ("b.step", b"not a model either")])
    with _candidate(tmp_path) as candidate:
        with open_model_source(source, REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
        assert attached is None
        assert _codes(issues, Severity.ERROR) == ["intake.no_model_in_source"]
        assert next(i for i in issues if i.severity is Severity.ERROR).text == "allbad.zip holds no usable 3D model"
        assert _codes(issues, Severity.WARNING) == ["intake.content_mismatch", "intake.content_mismatch"]
        assert "intake.unusable_model_in_source" not in _codes(issues)
        assert candidate.models == ()


def test_attach_refused_package(tmp_path):
    source = _zip(tmp_path, "notes.zip", [("note.txt", b"just text")])
    with _candidate(tmp_path) as candidate:
        with open_model_source(source, REPO_ROOT) as model_package:
            assert model_package.refused
            attached, issues = attach_models(candidate, model_package)
        assert attached is None
        assert _codes(issues, Severity.ERROR) == ["intake.no_model_in_source"]


def test_attach_filename_clash(tmp_path):
    other = STEP_BYTES + b"-- second\n"
    third = STEP_BYTES + b"-- third\n"
    members = [*snapeda_members(), ("part.stp", STEP_BYTES)]
    source = _zip(tmp_path, "clash.zip", [("PART.STP", other), ("sub/part.stp", third)])
    with _candidate(tmp_path, members) as candidate:
        assert [m.filename for m in candidate.models] == ["part.stp"]
        with open_model_source(source, REPO_ROOT) as model_package:
            attached, _ = attach_models(candidate, model_package)
        assert attached is not None
        assert [m.filename for m in attached.models] == ["part.stp", "PART_2.STP", "part_3.stp"]
        assert [m.file.sha256 for m in attached.models[1:]] != [attached.models[0].file.sha256] * 2


def test_attach_duplicate_sha(tmp_path):
    members = [*snapeda_members(), ("part.stp", STEP_BYTES)]
    with _candidate(tmp_path, members) as candidate:
        path = _bare(tmp_path, "same.stp", STEP_BYTES)
        with open_model_source(path, REPO_ROOT) as model_package:
            attached, issues = attach_models(candidate, model_package)
        assert attached is None
        assert _codes(issues) == ["intake.model_already_present"]
        assert issues[0].severity is Severity.INFO
        assert "same.stp" in issues[0].text and "part.stp" in issues[0].text


def _install(tmp_path, candidate, layout):
    options = InstallOptions(library=LIBRARY)
    return build_plan(candidate, options, layout, ToolContext()), options


@pytest.mark.parametrize("how", ["zip", "bare"])
def test_attach_then_install(how, tmp_path):
    layout = _layout(tmp_path)
    if how == "zip":
        path = snapeda_model_zip(tmp_path / "dl" / SNAPEDA_MODEL_ZIP_NAME)
    else:
        path = _bare(tmp_path, f"{SNAPEDA_MODEL_STEM}.stp", STEP_BYTES)
    with _candidate(tmp_path) as candidate, open_model_source(path, REPO_ROOT) as model_package:
        attached, _ = attach_models(candidate, model_package)
        assert attached is not None
        plan, _ = _install(tmp_path, attached, layout)
        assert not plan.blocked, [i.text for i in plan.issues]
        assert plan.model_file == f"{SNAPEDA_MPN}.stp"
        model_op = next(op for op in plan.ops if op.kind == "model")
        assert model_op.source is attached.models[0].file
        assert "install.no_model" not in _codes(plan.issues)

        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert result.ok, [i.text for i in result.issues]
        assert (layout.models_dir / f"{SNAPEDA_MPN}.stp").read_bytes() == STEP_BYTES
        installed = layout.footprints_dir / f"{footprint_library_for(LIBRARY)}.pretty" / f"{SNAPEDA_FOOTPRINT}.kicad_mod"
        ref = footprint_name(load(installed).root)
        assert [m.path for m in find_models(ref.node)] == [f"{MODEL_DIR_VAR}/{SNAPEDA_MPN}.stp"]

        again, _ = _install(tmp_path, attached, layout)
        assert again.is_noop


def test_attach_source_edited_after_preview(tmp_path, snapshot):
    layout = _layout(tmp_path)
    path = _bare(tmp_path, f"{SNAPEDA_MODEL_STEM}.stp", STEP_BYTES)
    with _candidate(tmp_path) as candidate, open_model_source(path, REPO_ROOT) as model_package:
        attached, _ = attach_models(candidate, model_package)
        plan, _ = _install(tmp_path, attached, layout)
        assert not plan.blocked
        path.write_bytes(STEP_BYTES + b"edited after the preview\n")
        before = snapshot(layout.custom_dir)
        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert not result.ok
        assert _codes(result.issues, Severity.ERROR)
        assert snapshot(layout.custom_dir) == before


def test_attach_zip_closed_before_install(tmp_path, snapshot):
    layout = _layout(tmp_path)
    path = snapeda_model_zip(tmp_path / "dl" / SNAPEDA_MODEL_ZIP_NAME)
    with _candidate(tmp_path) as candidate:
        model_package = open_model_source(path, REPO_ROOT)
        attached, _ = attach_models(candidate, model_package)
        plan, _ = _install(tmp_path, attached, layout)
        assert not plan.blocked
        model_package.close()
        before = snapshot(layout.custom_dir)
        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert not result.ok
        assert _codes(result.issues, Severity.ERROR)
        assert snapshot(layout.custom_dir) == before
