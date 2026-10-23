"""Second-source intake for a separately downloaded 3D model (plan 07-07, G-07-2).

open_model_source reads a model-only zip (every Phase 3 hostile-zip refusal and cap applies, D-05
to D-08, D-19) or one bare .step/.stp/.wrl in place and read-only. Hostile zips are generated with
tests/zipfixtures.py; none are committed. Every test that stages points tempfile.tempdir at a folder
it created first, so "nothing staged" is asserted by listing that folder. Tests that fake a stat
result patch pkg._lstat only, never the os module, so the stub reaches nothing else in the process.
"""

import hashlib
import os
import stat
import tempfile
import types
import zipfile

import pytest
from vendorfixtures import SNAPEDA_MODEL_NOTE, SNAPEDA_MODEL_STEM, snapeda_model_zip
from zipfixtures import (
    REPO_ROOT,
    STEP_BYTES,
    VRML_BYTES,
    corrupt_member,
    footprint,
    make_zip,
    mark_encrypted,
    symbol_lib,
    symlink_info,
    zip_bytes,
)

from kicad_lib_manager.importer import package as pkg
from kicad_lib_manager.importer.package import open_model_source, open_package
from kicad_lib_manager.models import Severity

_FLIP_OFFSET = 10


@pytest.fixture
def _tmpdir(tmp_path, monkeypatch):
    """Temp folder for staging; created first because tempfile never creates a missing one."""
    folder = tmp_path / "tmp"
    folder.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _codes(package, severity=Severity.ERROR):
    return [i.code for i in package.issues if i.severity is severity]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- zip source -----------------------------------------------------------------------


def test_model_zip_stages_only_models(tmp_path, _tmpdir):
    path = snapeda_model_zip(tmp_path / "dl" / "model.zip")
    with open_model_source(path, REPO_ROOT) as package:
        assert not package.refused
        assert package.kind == "zip"
        assert len(package.files) == 1
        pf = package.files[0]
        assert (pf.kind, pf.staged, pf.member) == ("model", True, f"{SNAPEDA_MODEL_STEM}.stp")
        assert pf.size == len(STEP_BYTES) and pf.sha256 == _sha(STEP_BYTES)
        assert pf.path.is_relative_to(package.staging_dir)
        assert not package.staging_dir.is_relative_to(REPO_ROOT)
        assert package.ignored == [f"{SNAPEDA_MODEL_STEM}.txt"]
        notes = [i for i in package.issues if i.code == "intake.ignored_members"]
        assert len(notes) == 1 and notes[0].severity is Severity.INFO
        assert f"{SNAPEDA_MODEL_STEM}.txt" in notes[0].text
        assert package.markers == {}


def test_model_zip_ignores_kicad_and_legacy_files(tmp_path, _tmpdir):
    path = make_zip(
        tmp_path / "mixed.zip",
        [
            ("a.stp", STEP_BYTES),
            ("sym.kicad_sym", symbol_lib(("S",))),
            ("fp.kicad_mod", footprint("F")),
            ("old.lib", b"EESchema-LIBRARY Version 2.3\n"),
            ("part_info.txt", SNAPEDA_MODEL_NOTE),
        ],
    )
    with open_model_source(path, REPO_ROOT) as package:
        assert not package.refused
        assert [f.member for f in package.files] == ["a.stp"]
        assert set(package.ignored) == {"sym.kicad_sym", "fp.kicad_mod", "old.lib", "part_info.txt"}
        assert package.legacy == []
        assert package.markers == {}
        staged = sorted(p.name for p in package.staging_dir.iterdir())
        assert len(staged) == 1 and staged[0].startswith("model_")


def test_model_zip_nested_one_level(tmp_path, _tmpdir):
    inner = zip_bytes([("inner.stp", STEP_BYTES), ("note.txt", SNAPEDA_MODEL_NOTE)])
    outer = make_zip(tmp_path / "outer.zip", [("inner.zip", inner)])
    with open_model_source(outer, REPO_ROOT) as package:
        assert not package.refused
        assert [f.member for f in package.files] == ["inner.zip/inner.stp"]
    deeper = make_zip(tmp_path / "deep.zip", [("inner.zip", zip_bytes([("deeper.zip", b"x")]))])
    package = open_model_source(deeper, REPO_ROOT)
    assert _codes(package) == ["intake.nested_too_deep"]
    assert package.files == []


def test_model_zip_without_model_refused(tmp_path, _tmpdir):
    path = make_zip(tmp_path / "notes.zip", [("note.txt", SNAPEDA_MODEL_NOTE)])
    package = open_model_source(path, REPO_ROOT)
    assert package.refused
    assert _codes(package) == ["intake.no_model_in_source"]
    assert package.files == []
    assert package.staging_dir is None
    assert list(_tmpdir.iterdir()) == []


def _hostile_name(tmp_path):
    return make_zip(tmp_path / "h.zip", [("../evil.stp", STEP_BYTES)]), "intake.hostile_member"


def _hostile_symlink(tmp_path):
    return make_zip(tmp_path / "h.zip", [(symlink_info("link.stp"), b"/etc/passwd")]), "intake.hostile_member"


def _encrypted(tmp_path):
    path = tmp_path / "h.zip"
    path.write_bytes(mark_encrypted(zip_bytes([("a.stp", STEP_BYTES)])))
    return path, "intake.encrypted"


def _duplicate(tmp_path):
    return make_zip(tmp_path / "h.zip", [("a.stp", STEP_BYTES), ("A.STP", STEP_BYTES)]), "intake.duplicate_member"


def _too_large(tmp_path):
    return make_zip(tmp_path / "h.zip", [("a.stp", STEP_BYTES + b"x" * 400)]), "intake.too_large"


def _corrupt(tmp_path):
    path = tmp_path / "h.zip"
    path.write_bytes(corrupt_member(zip_bytes([("a.stp", symbol_lib(("PART",)))]), 0, _FLIP_OFFSET))
    return path, "intake.corrupt"


@pytest.mark.parametrize(
    "build", [_hostile_name, _hostile_symlink, _encrypted, _duplicate, _too_large, _corrupt]
)
def test_model_zip_hostile_refused(build, tmp_path, _tmpdir, monkeypatch):
    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", 300)
    path, code = build(tmp_path)
    package = open_model_source(path, REPO_ROOT)
    assert package.refused
    assert _codes(package) == [code]
    assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_open_package_unchanged_for_model_zip(tmp_path, _tmpdir):
    path = snapeda_model_zip(tmp_path / "dl" / "model.zip")
    with open_package(path, REPO_ROOT) as package:
        assert package.kind == "zip"
        assert [f.kind for f in package.files] == ["model"]
        notes = [i for i in package.issues if i.code == "intake.ignored_members"]
        assert len(notes) == 1 and f"{SNAPEDA_MODEL_STEM}.txt" in notes[0].text


# -- bare model file --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "data"), [("part.stp", STEP_BYTES), ("PART.STEP", STEP_BYTES), ("part.wrl", VRML_BYTES)]
)
def test_bare_model_read_in_place(name, data, tmp_path, _tmpdir):
    path = tmp_path / "pick" / name
    path.parent.mkdir()
    path.write_bytes(data)
    mtime = path.stat().st_mtime_ns
    package = open_model_source(path, REPO_ROOT)
    assert not package.refused
    assert package.kind == "file"
    assert package.staging_dir is None
    assert len(package.files) == 1
    pf = package.files[0]
    assert (pf.member, pf.path, pf.kind, pf.staged) == (name, path, "model", False)
    assert pf.size == len(data) and pf.sha256 == _sha(data)
    package.close()
    assert path.read_bytes() == data and path.stat().st_mtime_ns == mtime
    assert list(_tmpdir.iterdir()) == []


def test_bare_model_symlink_refused(tmp_path):
    real = tmp_path / "real.stp"
    real.write_bytes(STEP_BYTES)
    link = tmp_path / "linked.stp"
    try:
        os.symlink(real, link)
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"symlinks not permitted here: {e}")
    package = open_model_source(link, REPO_ROOT)
    assert _codes(package) == ["intake.link_refused"]
    assert package.files == []


def _fake_stat(**changes):
    values = {
        "st_mode": stat.S_IFREG | 0o644,
        "st_size": len(STEP_BYTES),
        "st_dev": 1,
        "st_ino": 1,
        "st_file_attributes": 0,
    }
    values.update(changes)
    return types.SimpleNamespace(**values)


def test_bare_model_reparse_point_refused(tmp_path, monkeypatch):
    path = tmp_path / "junction.stp"
    path.write_bytes(STEP_BYTES)
    monkeypatch.setattr(pkg, "_lstat", lambda p: _fake_stat(st_file_attributes=pkg._WINDOWS_REPARSE))
    package = open_model_source(path, REPO_ROOT)
    assert _codes(package) == ["intake.link_refused"]
    assert package.files == []


def test_bare_model_handle_mismatch_refused(tmp_path, monkeypatch):
    path = tmp_path / "swapped.stp"
    path.write_bytes(STEP_BYTES)
    real = os.lstat(path)
    monkeypatch.setattr(
        pkg,
        "_lstat",
        lambda p: _fake_stat(
            st_mode=real.st_mode,
            st_size=real.st_size,
            st_dev=real.st_dev,
            st_ino=real.st_ino + 1,
            st_file_attributes=getattr(real, "st_file_attributes", 0),
        ),
    )
    package = open_model_source(path, REPO_ROOT)
    assert _codes(package) == ["intake.link_refused"]
    assert package.files == []


def test_bare_model_oversize_refused(tmp_path, monkeypatch):
    path = tmp_path / "big.stp"
    path.write_bytes(STEP_BYTES)
    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", len(STEP_BYTES) - 1)
    package = open_model_source(path, REPO_ROOT)
    assert _codes(package) == ["intake.too_large"]
    assert package.files == []


def test_bare_model_grown_after_listing_refused(tmp_path, monkeypatch):
    path = tmp_path / "grown.stp"
    path.write_bytes(STEP_BYTES)
    real = os.lstat(path)
    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", len(STEP_BYTES) - 1)
    monkeypatch.setattr(
        pkg,
        "_lstat",
        lambda p: _fake_stat(
            st_mode=real.st_mode,
            st_size=1,
            st_dev=real.st_dev,
            st_ino=real.st_ino,
            st_file_attributes=getattr(real, "st_file_attributes", 0),
        ),
    )
    package = open_model_source(path, REPO_ROOT)
    assert _codes(package) == ["intake.too_large"]
    assert "larger than it was listed" in package.issues[0].text


# -- everything else is refused, never raised --------------------------------------------


def test_model_source_unsupported_and_missing(tmp_path, monkeypatch):
    folder = tmp_path / "x.step"
    folder.mkdir()
    text = tmp_path / "note.txt"
    text.write_bytes(SNAPEDA_MODEL_NOTE)
    kicad = tmp_path / "fp.kicad_mod"
    kicad.write_bytes(footprint("F"))
    for path in (folder, text, kicad):
        package = open_model_source(path, REPO_ROOT)
        assert _codes(package) == ["intake.unsupported"], path
        assert package.files == []

    package = open_model_source(tmp_path / "missing.stp", REPO_ROOT)
    assert _codes(package) == ["intake.not_found"]

    def denied(_path):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(pkg, "_lstat", denied)
    package = open_model_source(text, REPO_ROOT)
    assert _codes(package) == ["intake.unreadable_source"]


def test_open_model_source_zip_is_a_regular_zip(tmp_path):
    """A .zip name that is not a zip is refused as corrupt, not raised."""
    path = tmp_path / "bad.zip"
    path.write_bytes(b"not a zip")
    package = open_model_source(path, REPO_ROOT)
    assert _codes(package) == ["intake.corrupt"]
    assert zipfile.is_zipfile(path) is False
