"""Self-checks for the synthetic vendor fixtures and the D-01 originality guard.

The vendor downloads are licence-restricted and both GitHub repos are public, so the committed
builders in vendorfixtures must be written from scratch. These tests prove the builders parse,
carry each vendor's markers, stay tiny and reproducible, and share no bytes with the owner's real
downloads. The real zips (git-ignored, downloaded_examples/) are only read member by member in
memory when present, never extracted or copied.
"""

import hashlib
import io
import time
import types
import zipfile
from pathlib import Path

import pytest
import zipfixtures as zf
from vendorfixtures import (
    SAMACSYS_LICENSE,
    SAMACSYS_PART,
    SAMACSYS_PART_INFO,
    samacsys_footprint,
    samacsys_members,
    samacsys_symbol,
    snapeda_footprint,
    snapeda_members,
    snapeda_symbol,
)

from kicad_lib_manager.importer.adapters.samacsys import parse_part_info
from kicad_lib_manager.kicad_files import file_kind, find_property, find_symbols, parse_bytes
from kicad_lib_manager.models import Issue

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "downloaded_examples"
REAL_ZIPS = {
    "snapeda": SAMPLES / "USB4145-03-0170-C_REVA2.zip",
    "samacsys": SAMPLES / "LIB_RS3-1212S_H3.zip",
}
REAL_PART_NAMES = (b"USB4145-03-0170-C", b"RS3-1212S")
MAX_MEMBER_BYTES = 4096


def _all_members():
    """Every member of both builders, with the model-carrying SnapEDA variant."""
    return [*snapeda_members(with_model=True), *samacsys_members()]


def _parsed(name, data):
    loaded = parse_bytes(data, name)
    assert not isinstance(loaded, Issue), (name, loaded)
    return loaded


def test_fixture_members_parse():
    for name, data in _all_members():
        lower = name.lower()
        if lower.endswith(".kicad_sym"):
            loaded = _parsed(name, data)
            assert file_kind(loaded.root) == "kicad_symbol_lib", name
            assert len(find_symbols(loaded.root)) == 1, name
        elif lower.endswith(".kicad_mod"):
            loaded = _parsed(name, data)
            expected = "module" if name.startswith(f"{SAMACSYS_PART}/") else "footprint"
            assert file_kind(loaded.root) == expected, name
        elif lower.endswith((".step", ".stp")):
            assert data.startswith(b"ISO-10303-21;"), name


def test_fixture_markers_present():
    symbol = snapeda_symbol()
    assert b"\r" not in symbol
    assert symbol.startswith(b"\n(kicad_symbol_lib")
    loaded = _parsed("snapeda.kicad_sym", symbol)
    node = find_symbols(loaded.root)[0].node
    assert find_property(node, "SnapEDA_Link") is not None
    assert find_property(node, "SNAPEDA_PN") is not None
    assert find_property(node, "Datasheet") is None
    assert b"\r" not in snapeda_footprint()

    sam_symbol = samacsys_symbol()
    assert sam_symbol.count(b"\r\n") == sam_symbol.count(b"\n")
    assert b"(generator SamacSys_ECAD_Model)" in sam_symbol
    footprint = samacsys_footprint()
    assert footprint.startswith(b'(module "PSU7"')
    assert f"(model {SAMACSYS_PART}.stp ".encode() in footprint
    assert b"SamacSys" in SAMACSYS_LICENSE
    info = parse_part_info(SAMACSYS_PART_INFO.decode())
    assert {"manufacturer", "partnumber", "partcategory"} <= set(info)


def test_fixture_members_small():
    for name, data in _all_members():
        assert len(data) < MAX_MEMBER_BYTES, (name, len(data))


def test_fixtures_are_deterministic(monkeypatch):
    assert snapeda_members(with_model=True) == snapeda_members(with_model=True)
    assert samacsys_members() == samacsys_members()
    assert snapeda_symbol() == snapeda_symbol()
    assert samacsys_symbol() == samacsys_symbol()

    # zipfile stamps each member with the wall clock; freeze it to compare whole archives byte for byte
    frozen = types.SimpleNamespace(**{k: getattr(time, k) for k in dir(time) if not k.startswith("__")})
    frozen.time = lambda: 1_700_000_000.0
    monkeypatch.setattr(zipfile, "time", frozen)
    for members in (snapeda_members(with_model=True), samacsys_members()):
        assert zf.zip_bytes(members) == zf.zip_bytes(members)
        with zipfile.ZipFile(io.BytesIO(zf.zip_bytes(members))) as archive:
            assert [(i.filename, archive.read(i)) for i in archive.infolist()] == members


def _real_member_hashes(path):
    """SHA-256 of every file member of a real zip, read in memory one by one (never extracted)."""
    hashes = set()
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.is_dir():
                hashes.add(hashlib.sha256(archive.read(info)).hexdigest())
    return hashes


@pytest.mark.parametrize("vendor", ["snapeda", "samacsys"])
def test_fixture_originality(vendor):
    real = REAL_ZIPS[vendor]
    if not real.exists():
        pytest.skip(f"downloaded_examples/{real.name} not present (licence-restricted {vendor} sample, kept local)")
    real_hashes = _real_member_hashes(real)
    assert real_hashes
    for name, data in _all_members():
        assert hashlib.sha256(data).hexdigest() not in real_hashes, f"{name} is a byte copy of a real {vendor} member"
        for part_name in REAL_PART_NAMES:
            assert part_name not in data, f"{name} contains the real part name {part_name!r}"
