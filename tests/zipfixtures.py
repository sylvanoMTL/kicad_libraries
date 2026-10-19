"""Shared byte builders for the Phase 3 package-intake tests (D-14, D-17).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so
pytest does not collect it. Test modules import it with ``from zipfixtures import
...``, which works because pytest's default prepend import mode puts ``tests/`` on
``sys.path``. It imports the standard library only; the builders produce bytes and
the self-tests in ``test_zipfixtures.py`` parse them with ``kicad_files``.

Every builder writes only under the path the test passes (``tmp_path``). The
committed Ultra Librarian zip is only read, never changed. ``unpack_sample`` is the
one place that turns it into a real folder of loose files: the owner's D-17 waiver
of the loose-files sample rule for Phase 3.
"""

import io
import struct
import warnings
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
UL_SYMBOL_MEMBER = "KiCADv6/2026-10-18_09-12-49.kicad_sym"
UL_FOOTPRINT_MEMBER = "KiCADv6/footprints.pretty/DQK0006B.kicad_mod"
UL_MODEL_MEMBER = "DLV0006A.stp"
BS = chr(92)
KICAD_SUFFIXES = (".kicad_sym", ".kicad_mod", ".step", ".stp", ".wrl")

_LOCAL_SIG = b"PK\x03\x04"
_CENTRAL_SIG = b"PK\x01\x02"
_EOCD_SIG = b"PK\x05\x06"


# -- zip builders --------------------------------------------------------------


def zip_bytes(
    members: list[tuple[str | zipfile.ZipInfo, bytes]],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> bytes:
    """Build a zip in memory; members is a list so duplicate names are possible."""
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # duplicate-name warning
        with zipfile.ZipFile(buffer, "w", compression=compression) as zf:
            for name, data in members:
                zf.writestr(name, data, compress_type=compression)
    return buffer.getvalue()


def make_zip(
    path: Path,
    members: list[tuple[str | zipfile.ZipInfo, bytes]],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
) -> Path:
    """Write zip_bytes(members) to path and return path."""
    path.write_bytes(zip_bytes(members, compression=compression))
    return path


def symlink_info(name: str) -> zipfile.ZipInfo:
    """Return a ZipInfo whose Unix mode says symlink (stat.S_ISLNK on external_attr >> 16)."""
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    return info


def _central_directory(data: bytes) -> tuple[int, int]:
    """Return (offset, entry count) of the central directory, read from the end record."""
    eocd = data.rfind(_EOCD_SIG)
    if eocd < 0:
        raise ValueError("not a zip: no end-of-central-directory record")
    count = struct.unpack_from("<H", data, eocd + 10)[0]
    offset = struct.unpack_from("<I", data, eocd + 16)[0]
    return offset, count


def lie_about_size(data: bytes, declared: int) -> bytes:
    """Patch the declared uncompressed size of the first member in both of its headers."""
    out = bytearray(data)
    cd_offset, _ = _central_directory(data)
    if data[cd_offset:cd_offset + 4] != _CENTRAL_SIG or data[:4] != _LOCAL_SIG:
        raise ValueError("unexpected zip layout")
    struct.pack_into("<I", out, cd_offset + 24, declared)
    struct.pack_into("<I", out, 22, declared)
    return bytes(out)


def mark_encrypted(data: bytes) -> bytes:
    """Set general-purpose flag bit 0 (encrypted) in every local and central header."""
    out = bytearray(data)
    pos, count = _central_directory(data)
    for _ in range(count):
        if data[pos:pos + 4] != _CENTRAL_SIG:
            raise ValueError("unexpected zip layout")
        flags = struct.unpack_from("<H", out, pos + 8)[0]
        struct.pack_into("<H", out, pos + 8, flags | 0x1)
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", data, pos + 28)
        local = struct.unpack_from("<I", data, pos + 42)[0]
        local_flags = struct.unpack_from("<H", out, local + 6)[0]
        struct.pack_into("<H", out, local + 6, local_flags | 0x1)
        pos += 46 + name_len + extra_len + comment_len
    return bytes(out)


def corrupt_member(data: bytes, index: int, offset: int, length: int = 2) -> bytes:
    """Flip length bytes of member index's compressed payload, leaving every header intact."""
    pos, count = _central_directory(data)
    if index < 0 or index >= count:
        raise ValueError(f"member index {index} is not below the entry count {count}")
    for _ in range(index):
        if data[pos:pos + 4] != _CENTRAL_SIG:
            raise ValueError("unexpected zip layout")
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", data, pos + 28)
        pos += 46 + name_len + extra_len + comment_len
    if data[pos:pos + 4] != _CENTRAL_SIG:
        raise ValueError("unexpected zip layout")
    compressed = struct.unpack_from("<I", data, pos + 20)[0]
    local = struct.unpack_from("<I", data, pos + 42)[0]
    if data[local:local + 4] != _LOCAL_SIG:
        raise ValueError("unexpected zip layout")
    local_name_len, local_extra_len = struct.unpack_from("<HH", data, local + 26)
    start = local + 30 + local_name_len + local_extra_len
    if offset < 0 or offset + length > compressed:
        raise ValueError(f"cannot flip {length} bytes at offset {offset} of a {compressed} byte payload")
    out = bytearray(data)
    for i in range(start + offset, start + offset + length):
        out[i] ^= 0xFF
    return bytes(out)


def unpack_sample(dest: Path, *, flat: bool = False, kicad_only: bool = False) -> Path:
    """Write members of the committed UL sample under dest: the real loose-files case for Phase 3 (CONTEXT.md D-17)."""
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(UL_ZIP) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            posix = PurePosixPath(name)
            if kicad_only and posix.suffix.casefold() not in KICAD_SUFFIXES:
                continue
            # The sample is trusted; the asserts keep this helper honest about it.
            assert ".." not in name.split("/"), name
            assert not name.startswith(("/", BS)), name
            assert ":" not in name, name
            target = dest / posix.name if flat else dest.joinpath(*posix.parts)
            assert target.resolve().is_relative_to(dest_resolved), name
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "xb") as handle:
                handle.write(zf.read(info))
    return dest


# -- KiCad and 3D byte builders ------------------------------------------------


def _quote(text: str) -> str:
    """Return text as a double-quoted S-expression string."""
    return '"' + text.replace(BS, BS + BS).replace('"', BS + '"') + '"'


def symbol_lib(
    names: tuple[str, ...] = ("PART",),
    *,
    version: int | None = 20211014,
    props: dict[str, str] | None = None,
) -> bytes:
    """Build a KiCad 6+ .kicad_sym with one symbol per name, each carrying props."""
    lines = ["(kicad_symbol_lib"]
    if version is not None:
        lines.append(f"  (version {version})")
    lines.append('  (generator "test")')
    for name in names:
        lines.append(f"  (symbol {_quote(name)}")
        lines.append('    (property "Reference" "U" (at 0 0 0))')
        lines.append(f"    (property \"Value\" {_quote(name)} (at 0 0 0))")
        for key, value in (props or {}).items():
            lines.append(f"    (property {_quote(key)} {_quote(value)} (at 0 0 0))")
        lines.append("  )")
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


def footprint(
    name: str = "FP",
    *,
    head: str = "footprint",
    version: int | None = 20211014,
    model: str | None = None,
) -> bytes:
    """Build a .kicad_mod; head "module" gives the legacy KiCad 5 spelling."""
    lines = [f"({head} {_quote(name)}"]
    if version is not None:
        lines.append(f"  (version {version})")
    lines.append('  (layer "F.Cu")')
    if model is not None:
        lines.append(f"  (model {_quote(model)}")
        lines.append("    (offset (xyz 0 0 0))")
        lines.append("    (scale (xyz 1 1 1))")
        lines.append("    (rotate (xyz 0 0 0))")
        lines.append("  )")
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


STEP_BYTES = (
    b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('test'),'2;1');\nENDSEC;\n"
    b"DATA;\nENDSEC;\nEND-ISO-10303-21;\n"
)
VRML_BYTES = b"#VRML V2.0 utf8\nShape { geometry Box { size 1 1 1 } }\n"
LEGACY_LIB_BYTES = (
    b"EESchema-LIBRARY Version 2.4\n#encoding utf-8\n#\n# PART\n#\n"
    b"DEF PART U 0 40 Y Y 1 F N\nF0 \"U\" 0 0 50 H V C CNN\n"
    b"F1 \"PART\" 0 0 50 H V C CNN\nDRAW\nENDDRAW\nENDDEF\n#\n#End Library\n"
)
LEGACY_DCM_BYTES = (
    b"EESchema-DOCLIB  Version 2.0\n#\n$CMP PART\nD Test part\nK test\n$ENDCMP\n"
    b"#\n#End Doc Library\n"
)
LEGACY_MOD_BYTES = (
    b"PCBNEW-LibModule-V1  2020-01-01 00:00:00\n$INDEX\nFP\n$EndINDEX\n"
    b"$MODULE FP\nPo 0 0 0 15 00000000 00000000 ~~\nLi FP\n$EndMODULE FP\n$EndLIBRARY\n"
)


# -- synthetic Custom/ layout --------------------------------------------------

CURRENT_CUSTOM_SYMBOL_LIBS = (
    "Connector_FFC_GCT",
    "Connector_MicroSD_GCT",
    "Connector_USB_GCT",
    "IC_Battery_Charger_TI",
    "IC_Battery_Fuel_Gauge_ADI",
    "IC_Button_Controller_ADI",
    "IC_IMU_TDK",
    "IC_Magnetometer_Memsic",
    "IC_Wireless_BLE_uBlox",
    "Oscillator_TCXO_Abracon",
)
# IC_IMU_TDK has a symbol library but no footprint library today
CURRENT_CUSTOM_FOOTPRINT_LIBS = tuple(
    name for name in CURRENT_CUSTOM_SYMBOL_LIBS if name != "IC_IMU_TDK"
)


def write_custom_layout(
    root: Path, symbol_libs: Iterable[str], footprint_libs: Iterable[str]
) -> Path:
    """Create Custom/Symbols, Custom/Footprints and Custom/3DModels under root only."""
    custom = root / "Custom"
    (custom / "3DModels").mkdir(parents=True, exist_ok=True)
    (custom / "Symbols").mkdir(parents=True, exist_ok=True)
    (custom / "Footprints").mkdir(parents=True, exist_ok=True)
    for name in symbol_libs:
        (custom / "Symbols" / f"{name}.kicad_sym").write_bytes(symbol_lib((name,)))
    for name in footprint_libs:
        (custom / "Footprints" / f"{name}.pretty").mkdir(parents=True, exist_ok=True)
    return root
