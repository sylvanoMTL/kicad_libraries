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
