"""Folder intake: read-only walk, link skipping, depth and size caps (INTK-01, A9, D-07).

open_package(folder, repo_root) reads a user-picked folder of loose KiCad and 3D files
in place. These tests build synthetic folders in tmp_path for the edge cases; the real
Ultra Librarian files unpacked into tmp_path (D-17) are exercised further down.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from zipfixtures import STEP_BYTES, footprint, symbol_lib

from kicad_lib_manager.importer import package as pkg
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.models import Severity


def _make_folder(root: Path) -> Path:
    folder = root / "pick"
    (folder / "sub").mkdir(parents=True)
    (folder / "a.kicad_sym").write_bytes(symbol_lib(("LOOSE1",)))
    (folder / "sub" / "b.kicad_mod").write_bytes(footprint("FP"))
    (folder / "c.step").write_bytes(STEP_BYTES)
    (folder / "d.STP").write_bytes(STEP_BYTES + b"\n")
    (folder / "readme.txt").write_bytes(b"hello")
    return folder


def _codes(package, code):
    return [i for i in package.issues if i.code == code]


def _snapshot(folder: Path):
    """{relative path: (size, mtime_ns, sha256)} for files, plus the set of folders."""
    files = {}
    folders = set()
    for dirpath, dirnames, filenames in os.walk(folder):
        for name in dirnames:
            folders.add((Path(dirpath) / name).relative_to(folder).as_posix())
        for name in filenames:
            path = Path(dirpath) / name
            stat = path.stat()
            files[path.relative_to(folder).as_posix()] = (
                stat.st_size,
                stat.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return files, folders


def test_folder_reads_in_place(tmp_path):
    folder = _make_folder(tmp_path)
    with open_package(folder, tmp_path) as package:
        assert package.kind == "folder"
        assert package.staging_dir is None
        assert not package.refused
        assert [pf.member for pf in package.files] == ["a.kicad_sym", "c.step", "d.STP", "sub/b.kicad_mod"]
        assert package.names == ["a.kicad_sym", "c.step", "d.STP", "readme.txt", "sub/b.kicad_mod"]
        for pf in package.files:
            assert pf.staged is False
            assert pf.path == folder / pf.member
            data = (folder / pf.member).read_bytes()
            assert pf.size == len(data)
            assert pf.sha256 == hashlib.sha256(data).hexdigest()
        assert [pf.kind for pf in package.files] == ["symbol", "model", "model", "footprint"]
        assert package.ignored == ["readme.txt"]
        notes = _codes(package, "intake.ignored_members")
        assert len(notes) == 1
        assert notes[0].severity is Severity.INFO
        assert "readme.txt" in notes[0].text


def test_folder_is_not_modified(tmp_path):
    folder = _make_folder(tmp_path)
    (folder / "empty_dir").mkdir()
    before = _snapshot(folder)
    with open_package(folder, tmp_path) as package:
        detect_candidate(package)
    package.close()
    assert _snapshot(folder) == before


def test_folder_symlink_skipped(tmp_path):
    folder = _make_folder(tmp_path)
    outside = tmp_path / "outside.step"
    outside.write_bytes(STEP_BYTES)
    try:
        os.symlink(outside, folder / "linked.step")
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"symlinks not permitted here: {e}")
    with open_package(folder, tmp_path) as package:
        assert "linked.step" not in package.names
        assert all(pf.member != "linked.step" for pf in package.files)
        notes = _codes(package, "intake.link_skipped")
        assert len(notes) == 1
        assert notes[0].severity is Severity.INFO
        assert "linked.step" in notes[0].text


def test_is_link_detects_symlink_and_reparse_bit():
    """Covers both link signals without needing symlink privileges."""

    class Stat:
        def __init__(self, attributes):
            self.st_file_attributes = attributes

    class Entry:
        def __init__(self, symlink, attributes):
            self._symlink = symlink
            self._attributes = attributes

        def is_symlink(self):
            return self._symlink

        def stat(self, follow_symlinks=True):
            assert follow_symlinks is False
            return Stat(self._attributes)

    assert pkg._is_link(Entry(True, 0))
    assert pkg._is_link(Entry(False, pkg._WINDOWS_REPARSE))
    assert not pkg._is_link(Entry(False, 0x20))


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are a Windows feature")
def test_folder_junction_skipped(tmp_path):
    folder = _make_folder(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.kicad_sym").write_bytes(symbol_lib(("X",)))
    link = folder / "jct"
    made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
    if made.returncode != 0:
        pytest.skip("could not create a junction here")
    try:
        with open_package(folder, tmp_path) as package:
            assert all("x.kicad_sym" not in name for name in package.names)
            assert all("x.kicad_sym" not in pf.member for pf in package.files)
            notes = _codes(package, "intake.link_skipped")
            assert len(notes) == 1
            assert "jct" in notes[0].text
    finally:
        os.rmdir(link)


def test_folder_depth_limit(tmp_path, monkeypatch):
    folder = tmp_path / "pick"
    (folder / "d1" / "d2").mkdir(parents=True)
    (folder / "d1" / "x.step").write_bytes(STEP_BYTES)
    (folder / "d1" / "d2" / "y.step").write_bytes(STEP_BYTES)
    monkeypatch.setattr(pkg, "MAX_FOLDER_DEPTH", 1)
    with open_package(folder, tmp_path) as package:
        assert [pf.member for pf in package.files] == ["d1/x.step"]
        assert "d1/d2/y.step" not in package.names
        notes = _codes(package, "intake.depth_limit")
        assert len(notes) == 1
        assert notes[0].severity is Severity.WARNING
        assert "d1/d2" in notes[0].text


def test_folder_depth_default_is_eight():
    assert pkg.MAX_FOLDER_DEPTH == 8


def test_folder_caps(tmp_path, monkeypatch):
    folder = tmp_path / "pick"
    folder.mkdir()
    for name in ("a.kicad_sym", "b.kicad_sym", "c.step", "d.step"):
        (folder / name).write_bytes(STEP_BYTES)
    monkeypatch.setattr(pkg, "MAX_MEMBERS", 3)
    with open_package(folder, tmp_path) as package:
        assert package.refused
        assert [i.code for i in package.issues if i.severity is Severity.ERROR] == ["intake.too_many_members"]
        assert package.files == []
    monkeypatch.setattr(pkg, "MAX_MEMBERS", 4)
    with open_package(folder, tmp_path) as package:
        assert not package.refused

    monkeypatch.setattr(pkg, "MAX_MEMBERS", 1000)
    big = tmp_path / "big"
    big.mkdir()
    (big / "m.step").write_bytes(b"x" * 101)
    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", 100)
    with open_package(big, tmp_path) as package:
        assert package.refused
        assert [i.code for i in package.issues if i.severity is Severity.ERROR] == ["intake.too_large"]
        assert package.files == []

    # a non-whitelisted file is never read, so it does not count against the size caps
    small = tmp_path / "small"
    small.mkdir()
    (small / "readme.txt").write_bytes(b"y" * 500)
    (small / "ok.step").write_bytes(b"z" * 100)
    with open_package(small, tmp_path) as package:
        assert not package.refused
        assert [pf.member for pf in package.files] == ["ok.step"]

    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", 100 * 1024 * 1024)
    pair = tmp_path / "pair"
    pair.mkdir()
    (pair / "a.step").write_bytes(b"1" * 80)
    (pair / "b.step").write_bytes(b"2" * 80)
    monkeypatch.setattr(pkg, "MAX_TOTAL_BYTES", 150)
    with open_package(pair, tmp_path) as package:
        assert package.refused
        assert [i.code for i in package.issues if i.severity is Severity.ERROR] == ["intake.too_large"]
        assert package.files == []


def test_folder_counted_read(tmp_path):
    path = tmp_path / "f.step"
    data = bytes(range(200))
    path.write_bytes(data)
    assert pkg._hash_file(path, 199) is None
    assert pkg._hash_file(path, 200) == (200, hashlib.sha256(data).hexdigest())


def test_folder_counted_read_refuses_a_file_that_outgrew_its_listing(tmp_path, monkeypatch):
    folder = tmp_path / "pick"
    folder.mkdir()
    (folder / "grow.step").write_bytes(b"a" * 50)
    real = pkg._hash_file

    def grown(path, limit):
        Path(path).write_bytes(b"a" * 500)  # the file grows between listing and reading
        return real(path, limit)

    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", 100)
    monkeypatch.setattr(pkg, "_hash_file", grown)
    with open_package(folder, tmp_path) as package:
        assert package.refused
        assert [i.code for i in package.issues if i.severity is Severity.ERROR] == ["intake.too_large"]
        assert package.files == []


def test_folder_progress(tmp_path):
    folder = _make_folder(tmp_path)
    calls = []
    with open_package(folder, tmp_path, progress=lambda *a: calls.append(a)):
        pass
    assert [(i, total) for _, i, total in calls] == [(0, 4), (1, 4), (2, 4), (3, 4)]
    assert all(isinstance(message, str) and message for message, _, _ in calls)


def test_folder_unreadable_folder_and_file_are_warnings(tmp_path, monkeypatch):
    folder = _make_folder(tmp_path)
    (folder / "locked").mkdir()
    real_scandir = os.scandir

    def scandir(path):
        if Path(path).name == "locked":
            raise PermissionError(13, "Permission denied")
        return real_scandir(path)

    real_hash = pkg._hash_file

    def hash_file(path, limit):
        if Path(path).name == "c.step":
            raise OSError(13, "Permission denied")
        return real_hash(path, limit)

    monkeypatch.setattr(pkg.os, "scandir", scandir)
    monkeypatch.setattr(pkg, "_hash_file", hash_file)
    with open_package(folder, tmp_path) as package:
        assert not package.refused
        folder_warn = _codes(package, "intake.unreadable_folder")
        file_warn = _codes(package, "intake.unreadable_file")
        assert len(folder_warn) == 1 and "locked" in folder_warn[0].text
        assert folder_warn[0].severity is Severity.WARNING
        assert len(file_warn) == 1 and "c.step" in file_warn[0].text
        assert [pf.member for pf in package.files] == ["a.kicad_sym", "d.STP", "sub/b.kicad_mod"]


def test_folder_dispatch(tmp_path):
    folder = _make_folder(tmp_path)
    with open_package(folder, tmp_path) as package:
        assert [i.code for i in package.issues if i.code == "intake.unsupported"] == []
    missing = open_package(tmp_path / "nope", tmp_path)
    assert missing.refused
    assert [i.code for i in missing.issues] == ["intake.not_found"]
