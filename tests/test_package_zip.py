"""Zip intake hardening: D-05, D-06, D-07, D-08, D-19, INTK-06.

Hostile zips are generated in memory or tmp_path with tests/zipfixtures.py; none are
committed. Every test that stages files points tempfile.tempdir at a folder it created
first, so "nothing staged" can be asserted by listing that folder.
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import types
import zipfile
from pathlib import Path

import pytest
from zipfixtures import (
    BS,
    REPO_ROOT,
    STEP_BYTES,
    UL_ZIP,
    corrupt_member,
    footprint,
    lie_about_size,
    make_zip,
    mark_encrypted,
    symbol_lib,
    symlink_info,
    zip_bytes,
)

from kicad_lib_manager.importer import package as pkg
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.models import Severity

# A 2-byte flip at this payload offset raises the codec's own error (LZMAError, ZstdError, zlib.error,
# OSError or BadZipFile), measured on Python 3.14.4; the two fixture pin tests re-check it on every run.
_FLIP_OFFSET = 10


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


# -- D-06: caps on declared sizes ----------------------------------------------


def _step(size: int) -> bytes:
    return b"x" * size


def test_cap_member_count_boundary(tmp_path, _tmpdir, monkeypatch):
    monkeypatch.setattr(pkg, "MAX_MEMBERS", 3)
    ok = make_zip(
        tmp_path / "three.zip", [("d/", b""), ("a.step", STEP_BYTES), ("b.step", STEP_BYTES)]
    )
    with open_package(ok, REPO_ROOT) as package:
        assert _errors(package) == []
        assert len(package.files) == 2
    over = make_zip(
        tmp_path / "four.zip",
        [("d/", b""), ("a.step", STEP_BYTES), ("b.step", STEP_BYTES), ("c.step", STEP_BYTES)],
    )
    with open_package(over, REPO_ROOT) as package:
        assert _codes(package) == ["intake.too_many_members"]
        assert package.files == []
        assert package.staging_dir is None
    assert list(_tmpdir.iterdir()) == []


def test_cap_member_size_boundary(tmp_path, _tmpdir, monkeypatch):
    monkeypatch.setattr(pkg, "MAX_MEMBER_BYTES", 100)
    ok = make_zip(tmp_path / "at.zip", [("a.step", _step(100))])
    with open_package(ok, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.size for f in package.files] == [100]
    over = make_zip(tmp_path / "over.zip", [("a.step", _step(101))])
    with open_package(over, REPO_ROOT) as package:
        assert _codes(package) == ["intake.too_large"]
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_cap_total_boundary(tmp_path, _tmpdir, monkeypatch):
    monkeypatch.setattr(pkg, "MAX_TOTAL_BYTES", 150)
    ok = make_zip(tmp_path / "at.zip", [("a.step", _step(75)), ("b.step", _step(75))])
    with open_package(ok, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.size for f in package.files] == [75, 75]
    over = make_zip(tmp_path / "over.zip", [("a.step", _step(75)), ("b.step", _step(76))])
    with open_package(over, REPO_ROOT) as package:
        assert _codes(package) == ["intake.too_large"]
    ignored = make_zip(tmp_path / "ignored.zip", [("readme.txt", _step(151))])
    with open_package(ignored, REPO_ROOT) as package:
        assert _codes(package) == ["intake.too_large"]
    assert list(_tmpdir.iterdir()) == []


def test_ratio_rule_boundaries():
    minimum = pkg.RATIO_MIN_SIZE
    assert pkg._ratio_exceeded(minimum, 1) is False
    assert pkg._ratio_exceeded(minimum + 1, 1) is True
    c = minimum // 100
    assert pkg._ratio_exceeded(pkg.MAX_RATIO * c, c) is False
    assert pkg._ratio_exceeded(pkg.MAX_RATIO * c + 1, c) is True
    assert pkg._ratio_exceeded(minimum + 1, 0) is True


def test_ratio_bomb_refused_and_random_accepted(tmp_path, _tmpdir):
    bomb = make_zip(tmp_path / "bomb.zip", [("bomb.txt", bytes(2 * 1024 * 1024))])
    with open_package(bomb, REPO_ROOT) as package:
        assert _codes(package) == ["intake.high_ratio"]
        assert "'bomb.txt'" in _errors(package)[0].text
    random_zip = make_zip(
        tmp_path / "random.zip",
        [("big.step", os.urandom(2 * 1024 * 1024))],
        compression=zipfile.ZIP_STORED,
    )
    with open_package(random_zip, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.size for f in package.files] == [2 * 1024 * 1024]
    assert list(_tmpdir.iterdir()) == []


# -- D-06: real bytes -----------------------------------------------------------


def test_copy_capped_counts_real_bytes():
    assert pkg._copy_capped(io.BytesIO(b"x" * 1001), io.BytesIO(), 1000) is None
    dst = io.BytesIO()
    sha = hashlib.sha256()
    assert pkg._copy_capped(io.BytesIO(b"x" * 1000), dst, 1000, sha) == 1000
    assert dst.getvalue() == b"x" * 1000
    assert sha.hexdigest() == hashlib.sha256(b"x" * 1000).hexdigest()


def test_lying_header(tmp_path, _tmpdir):
    data = make_zip(tmp_path / "real.zip", [("big.kicad_sym", b"x" * 5_000_000)]).read_bytes()
    under = tmp_path / "under.zip"
    under.write_bytes(lie_about_size(data, 100))
    with open_package(under, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.corrupt"]
        assert "'big.kicad_sym'" in errors[0].text
        assert package.files == []
    over = tmp_path / "over.zip"
    over.write_bytes(lie_about_size(data, 200 * 1024 * 1024))
    with open_package(over, REPO_ROOT) as package:
        assert _codes(package) == ["intake.too_large"]
    assert list(_tmpdir.iterdir()) == []


def test_empty_and_not_a_zip(tmp_path, _tmpdir):
    empty = make_zip(tmp_path / "empty.zip", [])
    with open_package(empty, REPO_ROOT) as package:
        assert package.names == []
        assert package.files == []
        assert package.issues == []
    zero = tmp_path / "zero.zip"
    zero.write_bytes(b"")
    text = tmp_path / "text.zip"
    text.write_bytes(b"hello")
    for bad in (zero, text):
        with open_package(bad, REPO_ROOT) as package:
            assert _codes(package) == ["intake.corrupt"]
            assert package.files == []


# -- D-08: nested zips ----------------------------------------------------------


def test_nested_one_level(tmp_path, _tmpdir):
    inner = zip_bytes([("p.kicad_sym", symbol_lib()), ("f.kicad_mod", footprint())])
    outer = make_zip(tmp_path / "outer.zip", [("inner.zip", inner)])
    with open_package(outer, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.member for f in package.files] == ["inner.zip/p.kicad_sym", "inner.zip/f.kicad_mod"]
        assert all(f.path.is_file() for f in package.files)
        assert "inner.zip" in package.names
        assert "inner.zip/p.kicad_sym" in package.names
        assert "inner.zip/f.kicad_mod" in package.names
        assert not list(package.staging_dir.glob("nested_*"))
        candidate, _ = detect_candidate(package)
        assert [s.name for s in candidate.symbols] == ["PART"]
        assert [f.name for f in candidate.footprints] == ["FP"]


def test_nested_two_deep_refused(tmp_path, _tmpdir):
    inner = zip_bytes([("deeper.zip", b"x")])
    outer = make_zip(tmp_path / "outer.zip", [("inner.zip", inner)])
    with open_package(outer, REPO_ROOT) as package:
        assert _codes(package) == ["intake.nested_too_deep"]
        assert package.staging_dir is None
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_nested_hostile_and_budget(tmp_path, _tmpdir, monkeypatch):
    inner = zip_bytes([("../x.step", STEP_BYTES)])
    outer = make_zip(tmp_path / "outer.zip", [("ok.step", STEP_BYTES), ("inner.zip", inner)])
    with open_package(outer, REPO_ROOT) as package:
        errors = _errors(package)
        assert [e.code for e in errors] == ["intake.hostile_member"]
        assert "inner.zip/../x.step" in errors[0].text
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []

    monkeypatch.setattr(pkg, "MAX_MEMBERS", 3)
    inner_two = zip_bytes([("b.step", STEP_BYTES), ("c.step", STEP_BYTES)])
    budget = make_zip(tmp_path / "budget.zip", [("a.step", STEP_BYTES), ("inner.zip", inner_two)])
    with open_package(budget, REPO_ROOT) as package:
        assert _codes(package) == ["intake.too_many_members"]
        assert package.files == []
    assert list(_tmpdir.iterdir()) == []


# -- junk names, staging, cleanup ----------------------------------------------


def test_junk_members_ignored(tmp_path, _tmpdir):
    zip_path = make_zip(
        tmp_path / "mac.zip",
        [
            ("ok.step", STEP_BYTES),
            ("__MACOSX/._DQK.kicad_mod", footprint()),
            ("__MACOSX/x/a.step", STEP_BYTES),
            ("._y.step", STEP_BYTES),
        ],
    )
    with open_package(zip_path, REPO_ROOT) as package:
        assert _errors(package) == []
        assert [f.member for f in package.files] == ["ok.step"]
        for junk in ("__MACOSX/._DQK.kicad_mod", "__MACOSX/x/a.step", "._y.step"):
            assert junk in package.ignored


def test_staging_in_repo_refused(tmp_path, monkeypatch):
    fake_repo = tmp_path / "repo"
    (fake_repo / "tmp").mkdir(parents=True)
    monkeypatch.setattr(tempfile, "tempdir", str(fake_repo / "tmp"))
    with open_package(UL_ZIP, fake_repo) as package:
        assert _codes(package) == ["intake.staging_in_repo"]
        assert package.files == []
        assert package.staging_dir is None
    assert list((fake_repo / "tmp").iterdir()) == []


def _git_status() -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(
        [git, "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_ul_sample_leaves_repo_unchanged(_tmpdir):
    before = _git_status()
    if before is None:
        pytest.skip("git is not on PATH")
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        listing = sorted(p.name for p in package.staging_dir.iterdir())
    assert listing == ["fp_002.kicad_mod", "model_000.stp", "sym_001.kicad_sym"]
    assert _git_status() == before


def test_cleanup_on_exception_and_concurrent(_tmpdir):
    staging = None
    with pytest.raises(RuntimeError):
        with open_package(UL_ZIP, REPO_ROOT) as package:
            staging = package.staging_dir
            assert staging.is_dir()
            raise RuntimeError("boom")
    assert staging is not None
    assert not staging.exists()

    with open_package(UL_ZIP, REPO_ROOT) as first, open_package(UL_ZIP, REPO_ROOT) as second:
        assert first.staging_dir != second.staging_dir
        assert first.staging_dir.is_dir()
        assert second.staging_dir.is_dir()
        both = [first.staging_dir, second.staging_dir]
    assert not any(p.exists() for p in both)
    assert list(_tmpdir.iterdir()) == []


# -- CR-02: damaged members and unusable temp folders ----------------------------


def _lzma_part_zip(path: Path) -> Path:
    data = zip_bytes([("p.kicad_sym", symbol_lib(("PART",)))], compression=zipfile.ZIP_LZMA)
    path.write_bytes(corrupt_member(data, 0, _FLIP_OFFSET))
    return path


def test_corrupt_lzma_fixture_raises_lzma_error(tmp_path):
    import lzma

    path = _lzma_part_zip(tmp_path / "bad.zip")
    with zipfile.ZipFile(path) as zf:
        info = zf.infolist()[0]
        with pytest.raises(lzma.LZMAError):
            with zf.open(info) as src:
                while src.read(65536):
                    pass


def test_corrupt_lzma_member_refused_and_cleaned_up(tmp_path, _tmpdir):
    path = _lzma_part_zip(tmp_path / "bad.zip")
    package = open_package(path, REPO_ROOT)
    assert package.refused is True
    assert _codes(package) == ["intake.corrupt"]
    text = _errors(package)[0].text
    assert "p.kicad_sym" in text
    assert "bad.zip" in text
    assert package.files == []
    assert package.staging_dir is None
    assert list(_tmpdir.iterdir()) == []


_CODEC_NAMES = ["ZIP_STORED", "ZIP_DEFLATED", "ZIP_BZIP2", "ZIP_LZMA", "ZIP_ZSTANDARD"]


def _codec(name: str) -> int:
    method = getattr(zipfile, name, None)
    if method is None:
        pytest.skip(f"this Python's zipfile has no {name}")
    return method


def _corrupt_part_zip(path: Path, method: int) -> Path:
    data = zip_bytes([("p.kicad_sym", symbol_lib(("PART",)))], compression=method)
    path.write_bytes(corrupt_member(data, 0, _FLIP_OFFSET))
    return path


@pytest.mark.parametrize("name", _CODEC_NAMES)
def test_corrupt_member_every_codec_refused_and_cleaned_up(name, tmp_path, _tmpdir):
    path = _corrupt_part_zip(tmp_path / "bad.zip", _codec(name))
    package = open_package(path, REPO_ROOT)
    assert package.refused is True
    assert _codes(package) == ["intake.corrupt"]
    assert "p.kicad_sym" in _errors(package)[0].text
    assert package.files == []
    assert package.staging_dir is None
    assert list(_tmpdir.iterdir()) == []


def test_corrupt_zstd_fixture_raises_zstd_error(tmp_path):
    method = _codec("ZIP_ZSTANDARD")
    from compression.zstd import ZstdError

    path = _corrupt_part_zip(tmp_path / "bad.zip", method)
    with zipfile.ZipFile(path) as zf:
        with pytest.raises(ZstdError):
            with zf.open(zf.infolist()[0]) as src:
                while src.read(65536):
                    pass


def test_corrupt_member_covers_every_zip_codec():
    # Tripwire: a codec this zipfile can write but the corrupt-member test does not cover
    # may raise an error class that _READ_ERRORS misses, so it must be reviewed first.
    writable = set()
    for attr in dir(zipfile):
        value = getattr(zipfile, attr)
        if not attr.startswith("ZIP_") or not isinstance(value, int) or value not in zipfile.compressor_names:
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(), "w") as zf:
                zf.writestr("a.txt", b"x" * 100, compress_type=value)
        except (NotImplementedError, RuntimeError):
            continue
        writable.add(value)
    covered = {getattr(zipfile, n) for n in _CODEC_NAMES if getattr(zipfile, n, None) is not None}
    assert writable == covered


def test_corrupt_nested_lzma_member_refused(tmp_path, _tmpdir):
    inner = corrupt_member(
        zip_bytes([("p.kicad_sym", symbol_lib(("PART",)))], compression=zipfile.ZIP_LZMA), 0, _FLIP_OFFSET
    )
    outer = make_zip(tmp_path / "outer.zip", [("inner.zip", inner)])
    package = open_package(outer, REPO_ROOT)
    assert _codes(package) == ["intake.corrupt"]
    assert "inner.zip/p.kicad_sym" in _errors(package)[0].text
    assert package.files == []
    assert list(_tmpdir.iterdir()) == []


def test_corrupt_member_mid_staging_removes_earlier_files_and_spares_other_package(tmp_path, _tmpdir):
    with open_package(UL_ZIP, REPO_ROOT) as held:
        recorded = [(f.path, hashlib.sha256(f.path.read_bytes()).hexdigest()) for f in held.files]
        assert recorded
        data = zip_bytes(
            [
                ("a.step", STEP_BYTES),
                ("b.kicad_mod", footprint()),
                ("c.kicad_sym", symbol_lib(("PART",))),
            ],
            compression=zipfile.ZIP_LZMA,
        )
        bad = tmp_path / "bad.zip"
        bad.write_bytes(corrupt_member(data, 2, _FLIP_OFFSET))
        package = open_package(bad, REPO_ROOT)
        assert _codes(package) == ["intake.corrupt"]
        assert "c.kicad_sym" in _errors(package)[0].text
        assert package.files == []
        assert [p.name for p in _tmpdir.iterdir()] == [held.staging_dir.name]
        for path, digest in recorded:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert list(_tmpdir.iterdir()) == []


def test_staging_failed_missing_temp_folder(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    monkeypatch.setattr(tempfile, "tempdir", str(missing))
    package = open_package(UL_ZIP, REPO_ROOT)
    assert _codes(package) == ["intake.staging_failed"]
    assert "ul_CSD85301Q2.zip" in _errors(package)[0].text
    assert package.files == []
    assert package.staging_dir is None
    assert not missing.exists()


def test_staging_failed_permission_error(monkeypatch, _tmpdir):
    def deny(*args, **kwargs):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(pkg, "tempfile", types.SimpleNamespace(TemporaryDirectory=deny))
    package = open_package(UL_ZIP, REPO_ROOT)
    assert _codes(package) == ["intake.staging_failed"]
    assert "Access is denied" in _errors(package)[0].text
    assert package.files == []
    assert package.staging_dir is None


def _build_missing_path(tmp_path, monkeypatch):
    return tmp_path / "absent.zip"


def _build_text_file(tmp_path, monkeypatch):
    path = tmp_path / "notes.txt"
    path.write_bytes(b"hello")
    return path


def _build_zero_byte_zip(tmp_path, monkeypatch):
    path = tmp_path / "zero.zip"
    path.write_bytes(b"")
    return path


def _build_text_zip(tmp_path, monkeypatch):
    path = tmp_path / "text.zip"
    path.write_bytes(b"hello")
    return path


def _build_corrupt_lzma(tmp_path, monkeypatch):
    return _corrupt_part_zip(tmp_path / "bad.zip", zipfile.ZIP_LZMA)


def _build_corrupt_zstd(tmp_path, monkeypatch):
    return _corrupt_part_zip(tmp_path / "bad.zip", _codec("ZIP_ZSTANDARD"))


def _build_lying_header(tmp_path, monkeypatch):
    data = zip_bytes([("big.kicad_sym", b"x" * 5_000_000)])
    path = tmp_path / "lie.zip"
    path.write_bytes(lie_about_size(data, 100))
    return path


def _build_encrypted(tmp_path, monkeypatch):
    path = tmp_path / "enc.zip"
    path.write_bytes(mark_encrypted(zip_bytes([("a.kicad_sym", symbol_lib())])))
    return path


def _build_hostile_name(tmp_path, monkeypatch):
    return make_zip(tmp_path / "evil.zip", [("../evil.step", STEP_BYTES)])


def _build_missing_temp_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "missing"))
    return UL_ZIP


NEVER_RAISES = {
    "missing_path": (_build_missing_path, "intake.not_found"),
    "text_file": (_build_text_file, "intake.unsupported"),
    "zero_byte_zip": (_build_zero_byte_zip, "intake.corrupt"),
    "text_zip": (_build_text_zip, "intake.corrupt"),
    "corrupt_lzma": (_build_corrupt_lzma, "intake.corrupt"),
    "corrupt_zstd": (_build_corrupt_zstd, "intake.corrupt"),
    "lying_header": (_build_lying_header, "intake.corrupt"),
    "encrypted": (_build_encrypted, "intake.encrypted"),
    "hostile_name": (_build_hostile_name, "intake.hostile_member"),
    "missing_temp_folder": (_build_missing_temp_folder, "intake.staging_failed"),
}


@pytest.mark.parametrize("case", list(NEVER_RAISES), ids=list(NEVER_RAISES))
def test_open_package_never_raises_on_expected_faults(case, tmp_path, _tmpdir, monkeypatch):
    build, expected = NEVER_RAISES[case]
    path = build(tmp_path, monkeypatch)
    package = open_package(path, REPO_ROOT)
    assert package.refused is True
    assert _codes(package) == [expected]
    assert package.files == []
    assert package.staging_dir is None
