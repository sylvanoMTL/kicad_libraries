"""The fix engine behind the check dialog: previewed, backed up, written atomically, gone on the next scan (SCAN-03).

Every test writes only into tmp_path trees; none touches the real Custom/.
"""

import hashlib
import os
from pathlib import Path

import pytest

from customfixtures import write_atomic_custom, write_fake_kicad
from kicad_lib_manager import atomic_fixes
from kicad_lib_manager.atomic_fixes import apply_preview, build_preview, preview_text
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import Severity

SYMBOL_REL = "Custom/Symbols/Atomic_Connector.kicad_sym"
FOOTPRINT_DIR = "Custom/Footprints/Atomic_Footprints.pretty"


def _no_kicad() -> list[str]:
    return []


def _setup(tmp_path):
    """Write the atomic inventory and a fake KiCad install; return (repo root, KiCad footprints folder)."""
    root = tmp_path / "repo"
    write_atomic_custom(root)
    footprints, _ = write_fake_kicad(tmp_path)
    return root, footprints


def _entries(root, footprints, library="Atomic_Connector"):
    """Scan and return {symbol name: SymbolEntry} of one library."""
    result = scan_all(root, kicad_fp_dir=footprints)
    lib = next(lib for lib in result.symbol_libs if lib.nickname == library)
    return {entry.name: entry for entry in lib.symbols}


def _fixes(entry):
    """Every one-click FixSpec of a symbol: violation fixes and finding fixes."""
    specs = [spec for violation in entry.violations for spec in violation.fixes]
    specs += [finding.fix for finding in entry.findings if finding.fix is not None]
    return specs


def _fill(entry, kind):
    return next(v.fill for v in entry.violations if v.fill is not None and v.fill.kind == kind)


def _preview(root, specs):
    return build_preview(root, specs, running=_no_kicad)


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


def test_value_to_mpn_is_previewed_backed_up_written_and_gone_on_the_next_scan(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    before = path.read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])
    assert [s.kind for s in specs] == ["value_to_mpn"]

    preview = _preview(root, specs)

    assert preview.issues == []
    assert len(preview.changes) == 1
    change = preview.changes[0]
    shown = preview_text(change).splitlines()
    assert any(line.startswith("-") and '"FFC20"' in line for line in shown)
    assert any(line.startswith("+") and '"FH12-20S-0.5SH"' in line for line in shown)
    assert shown[0] == f"--- before: {SYMBOL_REL}" and shown[1] == f"+++ after: {SYMBOL_REL}"
    # Only that one value token differs from the file as it was
    assert change.old_text == before
    assert change.new_text == before.replace('(property "Value" "FFC20"', '(property "Value" "FH12-20S-0.5SH"')
    assert path.read_text(encoding="utf-8") == before

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is True
    assert [i.code for i in result.issues] == ["atomic.fixed"]
    backups = list((tmp_path / "bk" / "atomic_fixes").rglob("Atomic_Connector.kicad_sym_backup_1"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == before
    assert path.read_text(encoding="utf-8") == change.new_text
    assert "value" not in {v.rule for v in _entries(root, footprints)["FFC-0.5-20"].violations}


def test_the_bytes_outside_the_edited_token_are_unchanged_line_endings_included(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    before = path.read_bytes()
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])

    result = apply_preview(_preview(root, specs), backup_root=tmp_path / "bk")

    assert result.ok is True
    expected = before.replace(b'(property "Value" "FFC20"', b'(property "Value" "FH12-20S-0.5SH"')
    assert path.read_bytes() == expected


def test_default_fix_backup_dir_sits_under_atomic_fixes_and_never_repeats(tmp_path):
    from datetime import datetime

    stamp = datetime(2026, 10, 26, 14, 30, 5)
    first = atomic_fixes.default_fix_backup_dir(tmp_path, now=stamp)
    assert first == tmp_path / "atomic_fixes" / "20261026-143005"

    first.mkdir(parents=True)
    second = atomic_fixes.default_fix_backup_dir(tmp_path, now=stamp)

    assert second == tmp_path / "atomic_fixes" / "20261026-143005-2"
    assert atomic_fixes.default_fix_backup_dir(tmp_path, now=stamp) != first
    assert not second.exists()
