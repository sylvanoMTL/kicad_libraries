"""Zip intake hardening: D-05, D-06, D-07, D-08, D-19, INTK-06.

Hostile zips are generated in memory or tmp_path with tests/zipfixtures.py; none are
committed. Every test that stages files points tempfile.tempdir at a folder it created
first, so "nothing staged" can be asserted by listing that folder.
"""

import re
import tempfile
import zipfile
from pathlib import Path

import pytest
from zipfixtures import (
    BS,
    REPO_ROOT,
    STEP_BYTES,
    footprint,
    make_zip,
    mark_encrypted,
    symbol_lib,
    symlink_info,
)

from kicad_lib_manager.importer import package as pkg
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.models import Severity


@pytest.fixture
def _tmpdir(tmp_path, monkeypatch):
    """Temp folder for staging; created first because tempfile never creates a missing one."""
    folder = tmp_path / "tmp"
    folder.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def _errors(package):
    return [i for i in package.issues if i.severity is Severity.ERROR]


def _codes(package):
    return [i.code for i in _errors(package)]


def _stored_name(zip_path: Path, index: int) -> str:
    """The member name as zipfile reads it back (backslashes are converted only on Windows)."""
    with zipfile.ZipFile(zip_path) as zf:
        return zf.infolist()[index].filename


# -- D-05: hostile names -------------------------------------------------------

HOSTILE_NAMES = [
    "../evil.kicad_sym",
    "a/../../evil.step",
    f"a{BS}..{BS}..{BS}evil.step",
    "a/.. /evil.step",
    "/abs.step",
    "//host/share/x.step",
    f"{BS}lead.step",
    "C:/x.step",
    "C:x.step",
    "a/b:stream.step",
    "a/\x01ctl.step",
    "../dir/",
]


@pytest.mark.parametrize("name", HOSTILE_NAMES, ids=[f"h{i}" for i in range(len(HOSTILE_NAMES))])
def test_hostile_member_refuses_package(name, tmp_path, _tmpdir):
    data = b"" if name.endswith("/") else STEP_BYTES
    zip_path = make_zip(tmp_path / "bad.zip", [("ok.kicad_sym", symbol_lib()), (name, data)])
    stored = _stored_name(zip_path, 1)
    with open_package(zip_path, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.hostile_member"]
        assert repr(stored) in errors[0].text
        assert package.staging_dir is None
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_hostile_ignored_member_still_refuses(tmp_path, _tmpdir):
    zip_path = make_zip(
        tmp_path / "bad.zip", [("ok.kicad_sym", symbol_lib()), ("readme/../../x.txt", b"x")]
    )
    with open_package(zip_path, REPO_ROOT) as package:
        assert _codes(package) == ["intake.hostile_member"]
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_hostile_reason_empty_name():
    assert pkg._hostile_reason("", zipfile.ZipInfo("x")) is not None


def test_hostile_symlink_member_refuses(tmp_path, _tmpdir):
    zip_path = make_zip(tmp_path / "link.zip", [(symlink_info("link.step"), b"target.step")])
    with open_package(zip_path, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.hostile_member"]
        assert "symbolic link" in errors[0].text
        assert "'link.step'" in errors[0].text
        assert package.staging_dir is None
    assert list(_tmpdir.iterdir()) == []


def test_hostile_reparse_point_member_refuses(tmp_path, _tmpdir):
    info = zipfile.ZipInfo("reparse.step")
    info.external_attr = 0x420
    zip_path = make_zip(tmp_path / "reparse.zip", [(info, STEP_BYTES)])
    with open_package(zip_path, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.hostile_member"]
        assert "reparse point" in errors[0].text
    assert list(_tmpdir.iterdir()) == []


def test_hostile_long_name_is_truncated_in_text(tmp_path, _tmpdir):
    name = "../" + "a" * 497 + ".step"
    assert len(name) == 505
    zip_path = make_zip(tmp_path / "long.zip", [(name, STEP_BYTES)])
    with open_package(zip_path, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.hostile_member"]
        text = errors[0].text
    assert len(text) <= 320
    assert repr(name)[:200] + "..." in text


# -- D-19: duplicates and encryption -------------------------------------------


@pytest.mark.parametrize(
    "members",
    [
        [("a.step", STEP_BYTES), ("a.step", STEP_BYTES)],
        [("A.STEP", STEP_BYTES), ("a.step", STEP_BYTES)],
        [("x/A.kicad_mod", footprint()), ("x/a.KICAD_MOD", footprint())],
    ],
    ids=["same", "case", "nested-case"],
)
def test_duplicate_member_refuses(members, tmp_path, _tmpdir):
    zip_path = make_zip(tmp_path / "dup.zip", members)
    with open_package(zip_path, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.duplicate_member"]
        assert package.staging_dir is None
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_duplicate_distinct_names_not_refused(tmp_path, _tmpdir):
    zip_path = make_zip(tmp_path / "ok.zip", [("a.step", STEP_BYTES), ("b.step", STEP_BYTES)])
    with open_package(zip_path, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.member for f in package.files] == ["a.step", "b.step"]


def test_encrypted_member_refuses(tmp_path, _tmpdir):
    data = mark_encrypted(
        make_zip(tmp_path / "plain.zip", [("a.kicad_sym", symbol_lib())]).read_bytes()
    )
    zip_path = tmp_path / "enc.zip"
    zip_path.write_bytes(data)
    with open_package(zip_path, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.encrypted"]
        assert "'a.kicad_sym'" in errors[0].text
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


# -- benign names stay accepted --------------------------------------------------


@pytest.mark.parametrize(
    ("name", "payload", "staged_re"),
    [
        ("sub/dir/ok.kicad_sym", symbol_lib(), r"sym_000\.kicad_sym"),
        ("x.y.z.step", STEP_BYTES, r"model_000\.step"),
        ("\u2126mega.step", STEP_BYTES, r"model_000\.step"),
    ],
    ids=["nested-dir", "dotted", "non-ascii"],
)
def test_hostile_benign_names_accepted(name, payload, staged_re, tmp_path, _tmpdir):
    zip_path = make_zip(tmp_path / "ok.zip", [(name, payload)])
    with open_package(zip_path, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.member for f in package.files] == [name]
        assert re.fullmatch(staged_re, package.files[0].path.name)
        assert package.files[0].path.is_file()
