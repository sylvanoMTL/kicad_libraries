import hashlib
import subprocess
import zipfile
from functools import partial
from pathlib import Path

import pytest

from kicad_lib_manager.fsutil import (
    SourceText,
    atomic_write_bytes,
    decode_source,
    encode_source,
)
from kicad_lib_manager.sexpr import apply_edits, parse

REPO = Path(__file__).resolve().parent.parent
ZIP = REPO / "downloaded_examples" / "ul_CSD85301Q2.zip"
ZIP_SHA256 = "9890115a990c03797a3d011eb62f0d7cd067fa10f982771fa8b38595d9399f3e"
_MAX_MEMBER_BYTES = 5_000_000
_KICAD_SUFFIXES = (".kicad_sym", ".kicad_mod")


def _zip_members(path: Path, cap: int = _MAX_MEMBER_BYTES) -> list[tuple[str, bytes]]:
    """Read the KiCad members of an untrusted vendor zip into memory, never to disk."""
    members = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if not info.filename.lower().endswith(_KICAD_SUFFIXES):
                continue
            # Declared size is checked before any bytes are read
            if info.file_size > cap:
                raise ValueError(f"zip member {info.filename} exceeds {cap} bytes")
            members.append((info.filename, zf.read(info)))
    return members


def _read_zip_member(name: str) -> bytes:
    for member_name, data in _zip_members(ZIP):
        if member_name == name:
            return data
    raise KeyError(f"zip member {name} not found")


def _repo_owned_params() -> list:
    params = []

    custom = REPO / "Custom"
    custom_files = sorted(
        [p for suffix in _KICAD_SUFFIXES for p in custom.rglob(f"*{suffix}")],
        key=lambda p: p.relative_to(custom).as_posix(),
    )
    if custom_files:
        for p in custom_files:
            params.append(pytest.param(
                partial(Path.read_bytes, p),
                id=f"custom/{p.relative_to(custom).as_posix()}",
            ))
    else:
        params.append(pytest.param(
            lambda: b"",
            id="custom/none",
            marks=pytest.mark.skip(
                reason="Custom submodule not checked out (git submodule update --init Custom)"
            ),
        ))

    fixtures = REPO / "tests" / "fixtures"
    fixture_files = [p for p in (fixtures / "sexpr").glob("*") if p.is_file()]
    for pattern in ("*.sym-lib-table", "*.fp-lib-table"):
        fixture_files.extend((fixtures / "tables").glob(pattern))
    for p in sorted(fixture_files, key=lambda p: p.relative_to(fixtures).as_posix()):
        params.append(pytest.param(
            partial(Path.read_bytes, p),
            id=f"fixture/{p.relative_to(fixtures).as_posix()}",
        ))

    if ZIP.exists():
        for name, _ in sorted(_zip_members(ZIP)):
            params.append(pytest.param(partial(_read_zip_member, name), id=f"zip/{name}"))
    return params


def _check_roundtrip(data: bytes, name: str, assert_tiles) -> None:
    src = decode_source(data, name)
    assert isinstance(src, SourceText), f"{name}: decode failed with {getattr(src, 'code', '?')}"
    root = parse(src.text)
    assert_tiles(src.text, root)
    assert apply_edits(src.text, []) == src.text, f"{name}: apply_edits with no edits changed the text"
    out = encode_source(src.text, src.bom)
    if out != data:
        offset = next(
            (i for i, (a, b) in enumerate(zip(out, data)) if a != b),
            min(len(out), len(data)),
        )
        raise AssertionError(f"round-trip mismatch for {name} at byte offset {offset}")


_REPO_PARAMS = _repo_owned_params()


@pytest.mark.parametrize("loader", _REPO_PARAMS)
def test_roundtrip_repo_owned(loader, request, tmp_path, assert_tiles):
    data = loader()
    name = request.node.callspec.id
    _check_roundtrip(data, name, assert_tiles)
    src = decode_source(data, name)
    target = tmp_path / "out.bin"
    assert atomic_write_bytes(target, encode_source(src.text, src.bom)) is None
    assert target.read_bytes() == data, f"{name}: atomic write changed the bytes"


def test_ul_zip_is_pinned_and_tracked():
    assert hashlib.sha256(ZIP.read_bytes()).hexdigest() == ZIP_SHA256
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "downloaded_examples/ul_CSD85301Q2.zip"],
        cwd=REPO,
        capture_output=True,
    )
    assert result.returncode == 0, "UL sample zip is not tracked by git"


def test_zip_member_cap_boundary():
    with zipfile.ZipFile(ZIP) as zf:
        sizes = {
            i.filename: i.file_size
            for i in zf.infolist()
            if i.filename.lower().endswith(_KICAD_SUFFIXES)
        }
    largest_name = max(sizes, key=sizes.get)
    largest = sizes[largest_name]
    assert len(_zip_members(ZIP, cap=largest)) == 2
    with pytest.raises(ValueError, match="exceeds") as excinfo:
        _zip_members(ZIP, cap=largest - 1)
    assert largest_name in str(excinfo.value)


def test_corpus_sources_are_present():
    ids = [p.id for p in _REPO_PARAMS]
    assert sum(i.startswith("fixture/sexpr/") for i in ids) >= 9
    assert sum(i.startswith("fixture/tables/") for i in ids) >= 5
    assert sum(i.startswith("zip/") for i in ids) == 2
