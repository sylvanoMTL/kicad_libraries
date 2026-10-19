"""Text caps for untrusted symbol and footprint files (CR-01, reopened T-03-15, INTK-06, INTK-01, D-06).

A hostile .kicad_sym or .kicad_mod can sit inside every zip limit (ratio, member size,
total size) and still cost minutes of CPU and gigabytes of RAM in the pure-Python
S-expression parser. locate therefore refuses to hand the parser more than
MAX_KICAD_TEXT_BYTES of text and stops it past MAX_KICAD_TEXT_NODES nodes. Either way
the file is skipped with a WARNING intake.unreadable_file and the rest of the package
is still read. The hostile files are generated in memory or tmp_path; none is committed.
"""

import hashlib
import os
import random
import zipfile
import zlib
from pathlib import Path

import pytest
from zipfixtures import (
    REPO_ROOT,
    STEP_BYTES,
    UL_FOOTPRINT_MEMBER,
    UL_SYMBOL_MEMBER,
    UL_ZIP,
    footprint,
    make_zip,
    symbol_lib,
)

from kicad_lib_manager.importer import package as package_module
from kicad_lib_manager.importer.adapters import base
from kicad_lib_manager.importer.adapters.base import Detection, locate
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import Package, PackageFile, open_package
from kicad_lib_manager.kicad_files import LoadedFile, parse_bytes
from kicad_lib_manager.models import Severity

_TOKENS = [b"(a)", b"(b 1)", b"()", b"(c d)", b"(e (f))"]


def _hostile_symbol(tokens: int, seed: int = 0) -> bytes:
    """Dense balanced-token symbol text that deflates about 10:1 and holds about 2.6 nodes per token."""
    body = b" ".join(random.Random(seed).choices(_TOKENS, k=tokens))
    return b"(kicad_symbol_lib (version 20211014) " + body + b")"


def _detect(tmp_path, members, name="pkg.zip"):
    """Open a synthetic zip and return (refused, candidate, issues)."""
    zip_path = make_zip(tmp_path / name, members)
    with open_package(zip_path, REPO_ROOT) as package:
        refused = package.refused
        candidate, issues = detect_candidate(package)
    return refused, candidate, issues


def _codes(issues, code):
    return [i for i in issues if i.code == code]


def _inside_every_zip_limit(data: bytes) -> None:
    assert len(data) < package_module.MAX_MEMBER_BYTES
    assert len(data) // len(zlib.compress(data)) < package_module.MAX_RATIO


# -- task 1: node ceiling, end to end --------------------------------------------


def test_text_cap_constants():
    assert package_module.MAX_KICAD_TEXT_NODES == 1_000_000
    assert package_module.MAX_MEMBERS == 1000
    assert package_module.MAX_MEMBER_BYTES == 100 * 1024 * 1024
    assert package_module.MAX_TOTAL_BYTES == 250 * 1024 * 1024
    assert package_module.MAX_RATIO == 200
    assert package_module.RATIO_MIN_SIZE == 1024 * 1024


def test_hostile_text_over_node_ceiling_is_skipped(tmp_path):
    hostile = _hostile_symbol(700_000)
    assert len(hostile) < 8 * 1024 * 1024  # under the byte cap, so only the node ceiling can stop it
    _inside_every_zip_limit(hostile)
    members = [("hostile.kicad_sym", hostile), ("good.kicad_mod", footprint("GOOD"))]
    refused, candidate, issues = _detect(tmp_path, members)
    assert refused is False
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert "hostile.kicad_sym" in skipped[0].text
    assert "more than 1000000 nodes" in skipped[0].text
    assert not [i for i in issues if i.severity is Severity.ERROR]
    assert candidate is not None
    assert [f.name for f in candidate.footprints] == ["GOOD"]


# -- task 2: byte cap, read before the parser ------------------------------------


def _folder_package(tmp_path: Path, files: dict[str, bytes]) -> Package:
    """Write files under tmp_path/loose and describe them as a folder Package, as test_adapters does."""
    folder = tmp_path / "loose"
    folder.mkdir()
    entries = []
    for name, data in files.items():
        path = folder / name
        path.write_bytes(data)
        kind = "symbol" if name.endswith(".kicad_sym") else "footprint" if name.endswith(".kicad_mod") else "model"
        entries.append(PackageFile(name, path, kind, len(data), hashlib.sha256(data).hexdigest(), False))
    return Package(source=folder, kind="folder", names=list(files), files=entries)


def _spy_parse(monkeypatch) -> list[str]:
    """Record every member name that reaches the parser."""
    seen: list[str] = []
    real = base.parse_bytes

    def spy(data, name, **kwargs):
        seen.append(name)
        return real(data, name, **kwargs)

    monkeypatch.setattr(base, "parse_bytes", spy)
    return seen


def test_hostile_text_over_byte_cap_never_parsed(tmp_path, monkeypatch):
    big = _hostile_symbol(1_700_000)
    assert package_module.MAX_KICAD_TEXT_BYTES < len(big) < package_module.MAX_MEMBER_BYTES
    _inside_every_zip_limit(big)
    real = base.parse_bytes

    def spy(data, name, **kwargs):
        if name == "big.kicad_sym":
            pytest.fail("the over-cap member reached the parser")
        return real(data, name, **kwargs)

    monkeypatch.setattr(base, "parse_bytes", spy)
    members = [("big.kicad_sym", big), ("good.kicad_mod", footprint("GOOD"))]
    refused, candidate, issues = _detect(tmp_path, members)
    assert refused is False
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert "big.kicad_sym" in skipped[0].text
    assert "8388608" in skipped[0].text
    assert [f.name for f in candidate.footprints] == ["GOOD"]


def test_text_byte_cap_boundary(tmp_path, monkeypatch):
    data = symbol_lib(("EDGE",))
    fp = footprint("F")
    assert len(fp) < len(data) - 1  # the footprint stays under every cap tried below
    package = _folder_package(tmp_path, {"edge.kicad_sym": data, "f.kicad_mod": fp})
    seen = _spy_parse(monkeypatch)
    detection = Detection("Loose", 0.3)
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", len(data))
    candidate, issues = locate(package, detection)
    assert [s.name for s in candidate.symbols] == ["EDGE"]
    assert not _codes(issues, "intake.unreadable_file")

    seen.clear()
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", len(data) - 1)
    candidate, issues = locate(package, detection)
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert "edge.kicad_sym" in skipped[0].text
    assert candidate.symbols == ()
    assert seen == ["f.kicad_mod"]  # the skipped symbol never reached the parser

    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", len(data) + 1)
    candidate, issues = locate(package, detection)
    assert [s.name for s in candidate.symbols] == ["EDGE"]


def test_text_byte_cap_counts_raw_bytes(tmp_path, monkeypatch):
    data = b"\xef\xbb\xbf" + symbol_lib(("OHM",), props={"Description": "10k" + chr(0x2126)})
    assert len(data) > len(data.decode("utf-8-sig"))
    fp = footprint("F")
    assert len(fp) < len(data) - 1
    package = _folder_package(tmp_path, {"ohm.kicad_sym": data, "f.kicad_mod": fp})
    detection = Detection("Loose", 0.3)
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", len(data))
    candidate, _ = locate(package, detection)
    assert [s.name for s in candidate.symbols] == ["OHM"]
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", len(data) - 1)
    candidate, issues = locate(package, detection)
    assert candidate.symbols == ()
    assert len(_codes(issues, "intake.unreadable_file")) == 1


def test_text_cap_never_exceeds_member_cap(tmp_path, monkeypatch):
    data = symbol_lib(("BIG",), props={"Description": "x" * 4000})
    package = _folder_package(tmp_path, {"big.kicad_sym": data, "f.kicad_mod": footprint("F")})
    monkeypatch.setattr(package_module, "MAX_MEMBER_BYTES", len(data) - 1)
    assert package_module.MAX_MEMBER_BYTES < package_module.MAX_KICAD_TEXT_BYTES
    candidate, issues = locate(package, Detection("Loose", 0.3))
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert f"larger than {len(data) - 1} bytes" in skipped[0].text
    assert candidate.symbols == ()


def test_zero_byte_text_file_is_not_a_cap_issue(tmp_path):
    package = _folder_package(tmp_path, {"empty.kicad_sym": b"", "good.kicad_mod": footprint("GOOD")})
    candidate, issues = locate(package, Detection("Loose", 0.3))
    mismatches = _codes(issues, "intake.content_mismatch")
    assert len(mismatches) == 1
    assert mismatches[0].severity is Severity.WARNING
    assert "empty.kicad_sym" in mismatches[0].text
    assert not [i for i in issues if "larger than" in i.text]
    assert candidate.symbols == ()


def _snapshot(folder: Path) -> dict[str, tuple[int, str]]:
    """{relative path: (size, sha256)} for every file and folder under folder."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(folder):
        for name in dirnames:
            found[(Path(dirpath) / name).relative_to(folder).as_posix() + "/"] = (0, "")
        for name in filenames:
            path = Path(dirpath) / name
            found[path.relative_to(folder).as_posix()] = (
                path.stat().st_size,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
    return found


def test_folder_text_over_cap_is_skipped(tmp_path, monkeypatch):
    folder = tmp_path / "pick"
    folder.mkdir()
    sym = symbol_lib(("S",))
    (folder / "sym.kicad_sym").write_bytes(sym)
    (folder / "big.kicad_mod").write_bytes(footprint("BIG") + b"\n" * (len(sym) + 1))
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", len(sym))
    before = _snapshot(folder)
    with open_package(folder, REPO_ROOT) as package:
        assert package.refused is False
        candidate, issues = detect_candidate(package)
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert "big.kicad_mod" in skipped[0].text
    assert [s.name for s in candidate.symbols] == ["S"]
    assert candidate.footprints == ()
    assert _snapshot(folder) == before


def test_models_skip_the_text_caps(tmp_path, monkeypatch):
    sym = symbol_lib(("S",))
    fp = footprint("F")
    cap = max(len(sym), len(fp))
    model = STEP_BYTES + b"\n" * (cap + 1)
    assert len(model) > cap
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_BYTES", cap)
    members = [("s.kicad_sym", sym), ("f.kicad_mod", fp), ("m.step", model)]
    refused, candidate, issues = _detect(tmp_path, members)
    assert refused is False
    assert [m.filename for m in candidate.models] == ["m.step"]
    assert [s.name for s in candidate.symbols] == ["S"]
    assert [f.name for f in candidate.footprints] == ["F"]
    assert not [i for i in issues if "m.step" in i.text]


# -- task 3: node ceiling boundary, MemoryError guard, real files ------------------


def _node_count(root) -> int:
    """Count every list, atom and string below the root (the root itself is not counted)."""
    total = 0
    stack = list(root.children)
    while stack:
        node = stack.pop()
        total += 1
        stack.extend(node.children)
    return total


def test_node_ceiling_boundary_in_locate(tmp_path, monkeypatch):
    data = symbol_lib(("EDGE",))
    loaded = parse_bytes(data, "e")
    assert isinstance(loaded, LoadedFile)
    n = _node_count(loaded.root)
    package = _folder_package(tmp_path, {"edge.kicad_sym": data, "f.kicad_mod": footprint("F")})
    detection = Detection("Loose", 0.3)

    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_NODES", n)
    candidate, issues = locate(package, detection)
    assert [s.name for s in candidate.symbols] == ["EDGE"]
    assert not _codes(issues, "intake.unreadable_file")

    # The small footprint has fewer nodes than the symbol file, so only the symbol is cut
    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_NODES", n - 1)
    candidate, issues = locate(package, detection)
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert f"more than {n - 1} nodes" in skipped[0].text
    assert candidate.symbols == ()

    monkeypatch.setattr(package_module, "MAX_KICAD_TEXT_NODES", n + 1)
    candidate, _ = locate(package, detection)
    assert [s.name for s in candidate.symbols] == ["EDGE"]


def test_memory_error_is_a_warning(tmp_path, monkeypatch):
    real = base.parse_bytes

    def flaky(data, name, **kwargs):
        if name == "a.kicad_sym":
            raise MemoryError
        return real(data, name, **kwargs)

    monkeypatch.setattr(base, "parse_bytes", flaky)
    members = [
        ("a.kicad_sym", symbol_lib(("A",))),
        ("b.kicad_sym", symbol_lib(("B",))),
        ("f.kicad_mod", footprint("F")),
    ]
    refused, candidate, issues = _detect(tmp_path, members)
    assert refused is False
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert "a.kicad_sym" in skipped[0].text
    assert "not enough memory" in skipped[0].text
    assert [s.name for s in candidate.symbols] == ["B"]
    assert [f.name for f in candidate.footprints] == ["F"]


def test_real_files_are_below_both_caps():
    custom = REPO_ROOT / "Custom"
    paths = []
    if custom.is_dir():
        paths = sorted(custom.rglob("*.kicad_sym")) + sorted(custom.rglob("*.kicad_mod"))
    if not paths:
        pytest.skip("Custom submodule not checked out (git submodule update --init Custom)")
    named = [(p.name, p.read_bytes()) for p in paths]
    with zipfile.ZipFile(UL_ZIP) as zf:
        for member in (UL_SYMBOL_MEMBER, UL_FOOTPRINT_MEMBER):
            named.append((member, zf.read(member)))
    for name, data in named:
        assert len(data) <= package_module.MAX_KICAD_TEXT_BYTES, name
        loaded = parse_bytes(data, name, max_nodes=package_module.MAX_KICAD_TEXT_NODES)
        assert isinstance(loaded, LoadedFile), f"{name}: {loaded}"
