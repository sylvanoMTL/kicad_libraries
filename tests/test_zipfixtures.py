"""Self-tests that keep the shared Phase 3 byte builders honest (D-14, D-17)."""

import hashlib
import io
import stat
import zipfile
from pathlib import PurePosixPath

from zipfixtures import (
    UL_FOOTPRINT_MEMBER,
    UL_MODEL_MEMBER,
    UL_SYMBOL_MEMBER,
    UL_ZIP,
    lie_about_size,
    mark_encrypted,
    symlink_info,
    unpack_sample,
    zip_bytes,
)

UL_MEMBERS = {
    UL_MODEL_MEMBER,
    "ImportGuides.html",
    "readme.txt",
    UL_SYMBOL_MEMBER,
    "KiCADv6/ImportGuide.html",
    UL_FOOTPRINT_MEMBER,
}


def _open(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


def _files_below(folder) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def test_make_zip_keeps_duplicates():
    data = zip_bytes([("a.step", b"one"), ("a.step", b"two")])
    names = [i.filename for i in _open(data).infolist()]
    assert names == ["a.step", "a.step"]


def test_symlink_info_mode():
    data = zip_bytes([(symlink_info("link.step"), b"target.step")])
    info = _open(data).getinfo("link.step")
    assert stat.S_ISLNK(info.external_attr >> 16)


def test_lie_about_size():
    data = zip_bytes([("a.kicad_sym", b"x" * 1000)])
    assert _open(data).getinfo("a.kicad_sym").file_size == 1000
    lied = lie_about_size(data, 10)
    assert _open(lied).getinfo("a.kicad_sym").file_size == 10


def test_mark_encrypted():
    data = zip_bytes([("a.step", b"one"), ("b.step", b"two"), ("c.step", b"three")])
    infos = _open(mark_encrypted(data)).infolist()
    assert len(infos) == 3
    assert all(i.flag_bits & 0x1 for i in infos)
    # Untouched zips stay unencrypted
    assert not any(i.flag_bits & 0x1 for i in _open(data).infolist())


def test_unpack_sample_full_layout(tmp_path):
    result = unpack_sample(tmp_path / "ul")
    assert result == tmp_path / "ul"
    assert _files_below(result) == UL_MEMBERS
    with zipfile.ZipFile(UL_ZIP) as zf:
        for member in UL_MEMBERS:
            assert (result.joinpath(*PurePosixPath(member).parts)).read_bytes() == zf.read(member)


def test_unpack_sample_flat_kicad_only(tmp_path):
    result = unpack_sample(tmp_path / "loose", flat=True, kicad_only=True)
    expected = {
        PurePosixPath(UL_SYMBOL_MEMBER).name: UL_SYMBOL_MEMBER,
        PurePosixPath(UL_FOOTPRINT_MEMBER).name: UL_FOOTPRINT_MEMBER,
        UL_MODEL_MEMBER: UL_MODEL_MEMBER,
    }
    assert sorted(p.name for p in result.iterdir()) == sorted(expected)
    assert not any(p.is_dir() for p in result.iterdir())
    with zipfile.ZipFile(UL_ZIP) as zf:
        for name, member in expected.items():
            digest = hashlib.sha256((result / name).read_bytes()).hexdigest()
            assert digest == hashlib.sha256(zf.read(member)).hexdigest()


def test_unpack_sample_writes_only_in_dest(tmp_path):
    before = hashlib.sha256(UL_ZIP.read_bytes()).hexdigest()
    unpack_sample(tmp_path / "ul")
    unpack_sample(tmp_path / "loose", flat=True, kicad_only=True)
    top = {p.name for p in tmp_path.iterdir()}
    assert top == {"ul", "loose"}
    for path in tmp_path.rglob("*"):
        assert path.relative_to(tmp_path).parts[0] in {"ul", "loose"}
    assert hashlib.sha256(UL_ZIP.read_bytes()).hexdigest() == before
