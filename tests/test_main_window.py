"""Offscreen MainWindow tests.

The harness never touches the owner's machine: QSettings is redirected into
tmp_path and scan, KiCad detection, REPO_ROOT and the KiCad config writer are
replaced before the window exists.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from kicad_lib_manager import main_window, settings
from kicad_lib_manager.models import (
    FootprintLibrary, FootprintRef, ScanResult, SymbolLibrary,
)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


@pytest.fixture
def make_window(qtbot, monkeypatch, tmp_path):
    def make(results, repo=None):
        repo = Path(repo) if repo is not None else tmp_path / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        fp_dir = tmp_path / "kicad_fp"
        fp_dir.mkdir(exist_ok=True)
        queue = list(results)
        calls = []

        def fake_scan(root, progress=None, kicad_fp_dir=None):
            calls.append((root, kicad_fp_dir))
            item = queue.pop(0) if len(queue) > 1 else queue[0]
            return item() if callable(item) else item

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_path_vars", lambda repo_root: [])
        make.calls = calls
        make.repo = repo
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        return w

    make.calls = []
    make.repo = None
    return make


def test_generate_splices_table_and_logs_issues(make_window):
    scan = ScanResult(
        symbol_libs=[SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom")],
        footprint_libs=[FootprintLibrary("NewFP", "Custom/Footprints/NewFP.pretty", "Custom")],
    )
    w = make_window([scan])
    repo = make_window.repo

    original = (
        b"(sym_lib_table\r\n"
        b"  (version 7)\r\n"
        b'  (lib (name "Ext")(type "KiCad")(uri "C:/libs/Ext.kicad_sym")'
        b'(options "")(descr "hand made"))\r\n'
        b'  (lib (name "Old")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/Old.kicad_sym")'
        b'(options "")(descr ""))\r\n'
        b")\r\n"
    )
    (repo / "sym-lib-table").write_bytes(original)

    scan.symbol_libs[0].selected = True
    scan.footprint_libs[0].selected = True
    w._on_generate()

    data = (repo / "sym-lib-table").read_bytes()
    assert b"  (version 7)\r\n" in data
    assert (
        b'  (lib (name "Ext")(type "KiCad")(uri "C:/libs/Ext.kicad_sym")'
        b'(options "")(descr "hand made"))\r\n'
    ) in data
    assert b"Old.kicad_sym" not in data
    assert (
        b'(lib (name "New")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/New.kicad_sym")'
        b'(options "")(descr ""))'
    ) in data
    assert b"\n" not in data.replace(b"\r\n", b"")

    assert (repo / "sym-lib-table_backup_1").read_bytes() == original
    fp_data = (repo / "fp-lib-table").read_bytes()
    assert b'(name "NewFP")' in fp_data

    log_text = w._log._text.toPlainText()
    assert "Written sym-lib-table" in log_text
    assert "Written fp-lib-table" in log_text
    assert "#007700" in w._log._text.toHtml()


def _managed_table(tag, entries):
    lines = [f"({tag}", "  (version 7)"]
    for name, rel in entries:
        lines.append(
            f'  (lib (name "{name}")(type "KiCad")'
            f'(uri "${{KICAD_LIB_GITHUB}}/{rel}")(options "")(descr ""))'
        )
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_startup_preselection_matches_by_rel_path_not_nickname(make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("Same", "Custom/Symbols/Same.kicad_sym")])
    )
    (repo / "fp-lib-table").write_bytes(
        _managed_table("fp_lib_table", [("Solo", "Custom/Footprints/Solo.pretty")])
    )
    scan = ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Same", "Custom/Symbols/Same.kicad_sym", "Custom",
                footprint_refs=[FootprintRef("Solo", "X", True)],
            ),
            SymbolLibrary(
                "Same", "WurthElektronik/KiCad-Library/symbols/Same.kicad_sym",
                "WurthElektronik",
            ),
        ],
        footprint_libs=[FootprintLibrary("Solo", "Custom/Footprints/Solo.pretty", "Custom")],
    )

    w = make_window([scan], repo=repo)

    custom_same, wurth_same = w._scan_result.symbol_libs
    assert custom_same.selected is True
    assert wurth_same.selected is False
    assert w._scan_result.footprint_libs[0].selected is True


def test_destination_change_only_logs_and_never_on_keystrokes(make_window, tmp_path):
    scan = ScanResult(
        symbol_libs=[SymbolLibrary("A", "Custom/Symbols/A.kicad_sym", "Custom", selected=True)],
        footprint_libs=[FootprintLibrary("B", "Custom/Footprints/B.pretty", "Custom")],
    )
    w = make_window([scan])
    other = tmp_path / "other"
    other.mkdir()
    (other / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("A", "Custom/Symbols/A.kicad_sym")])
    )
    marker = f"Existing sym-lib-table found at {other}"

    w._dest_combo.setEditText(str(other))
    assert marker not in w._log._text.toPlainText()

    w._dest_combo.lineEdit().editingFinished.emit()
    assert w._log._text.toPlainText().count(marker) == 1
    assert [lib.selected for lib in scan.symbol_libs] == [True]
    assert [lib.selected for lib in scan.footprint_libs] == [False]
