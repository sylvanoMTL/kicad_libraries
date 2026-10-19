"""Self-tests that keep the shared Phase 3 byte builders honest (D-14, D-17)."""

import hashlib
import io
import stat
import zipfile
from pathlib import PurePosixPath

from kicad_lib_manager.kicad_files import (
    LoadedFile,
    find_models,
    find_property,
    find_symbols,
    footprint_name,
    parse_bytes,
)
from zipfixtures import (
    CURRENT_CUSTOM_FOOTPRINT_LIBS,
    CURRENT_CUSTOM_SYMBOL_LIBS,
    LEGACY_DCM_BYTES,
    LEGACY_LIB_BYTES,
    LEGACY_MOD_BYTES,
    STEP_BYTES,
    UL_FOOTPRINT_MEMBER,
    UL_MODEL_MEMBER,
    UL_SYMBOL_MEMBER,
    UL_ZIP,
    VRML_BYTES,
    footprint,
    lie_about_size,
    mark_encrypted,
    symbol_lib,
    symlink_info,
    unpack_sample,
    write_custom_layout,
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


def _loaded(data: bytes, name: str) -> LoadedFile:
    loaded = parse_bytes(data, name)
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def test_symbol_lib_round_trip():
    loaded = _loaded(symbol_lib(("A", "B"), props={"MF": "X"}), "x.kicad_sym")
    symbols = find_symbols(loaded.root)
    assert [s.name for s in symbols] == ["A", "B"]
    for ref in symbols:
        assert find_property(ref.node, "Reference").value == "U"
        assert find_property(ref.node, "MF").value == "X"


def test_footprint_round_trip():
    ref = footprint_name(_loaded(footprint("X"), "x.kicad_mod").root)
    assert ref.name == "X"
    assert ref.node.head == "footprint"

    legacy = footprint_name(_loaded(footprint("X", head="module", version=None), "x.kicad_mod").root)
    assert legacy.name == "X"
    assert legacy.node.head == "module"
    assert not [c for c in legacy.node.children if c.head == "version"]

    path = "${CUSTOM_3DMODEL_DIR}/x.step"
    modelled = footprint_name(_loaded(footprint("X", model=path), "x.kicad_mod").root)
    assert [m.path for m in find_models(modelled.node)] == [path]


def test_format_magic_bytes():
    assert STEP_BYTES.startswith(b"ISO-10303-21;")
    assert VRML_BYTES.startswith(b"#VRML V2.0 utf8")
    assert LEGACY_LIB_BYTES.startswith(b"EESchema-LIBRARY Version 2.4")
    assert LEGACY_DCM_BYTES.startswith(b"EESchema-DOCLIB  Version 2.0")
    assert LEGACY_MOD_BYTES.startswith(b"PCBNEW-LibModule-V1")


def test_write_custom_layout(tmp_path):
    assert write_custom_layout(tmp_path, ["IC_LDO_TI"], ["IC_LDO_TI"]) == tmp_path
    found = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")}
    assert found == {
        "Custom",
        "Custom/3DModels",
        "Custom/Symbols",
        "Custom/Symbols/IC_LDO_TI.kicad_sym",
        "Custom/Footprints",
        "Custom/Footprints/IC_LDO_TI.pretty",
    }


def test_current_custom_lists():
    assert len(CURRENT_CUSTOM_SYMBOL_LIBS) == 10
    assert len(CURRENT_CUSTOM_FOOTPRINT_LIBS) == 9
    assert "IC_IMU_TDK" in CURRENT_CUSTOM_SYMBOL_LIBS
    assert "IC_IMU_TDK" not in CURRENT_CUSTOM_FOOTPRINT_LIBS
    assert set(CURRENT_CUSTOM_FOOTPRINT_LIBS) < set(CURRENT_CUSTOM_SYMBOL_LIBS)
