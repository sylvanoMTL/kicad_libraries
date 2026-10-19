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
import zlib
from pathlib import Path

import pytest
from zipfixtures import REPO_ROOT, STEP_BYTES, UL_ZIP, footprint, make_zip, symbol_lib

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
