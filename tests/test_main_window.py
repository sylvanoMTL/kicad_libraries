"""Offscreen MainWindow tests.

The harness never touches the owner's machine: QSettings is redirected into
tmp_path and scan, KiCad detection, REPO_ROOT and the KiCad config writer are
replaced before the window exists.
"""

import json
import os
import stat
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt

from kicad_lib_manager import library_scanner, main_window, settings
from kicad_lib_manager.models import (
    FootprintLibrary, FootprintRef, Issue, ScanResult, Severity, SymbolLibrary,
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
    def make(results, repo=None, empty_config=False, wait=True):
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

        # The real sync runs, but only against a synthetic KiCad tree and backup folder in tmp_path
        config_base = tmp_path / "kicad_cfg"
        config_base.mkdir(exist_ok=True)
        config_file = config_base / "10.0" / "kicad_common.json"
        if not empty_config:
            config_file.parent.mkdir(exist_ok=True)
            config_file.write_text('{"environment": {"vars": null}}\n', encoding="utf-8")

        def fake_sync(repo_root):
            return library_scanner.sync_kicad_path_vars(
                repo_root,
                config_base=config_base,
                backup_root=tmp_path / "backups",
                running=lambda: [],
            )

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_path_vars", fake_sync)
        make.calls = calls
        make.repo = repo
        make.config_file = config_file
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        if wait:
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


def _new_lib_scan():
    return ScanResult(
        symbol_libs=[SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom", selected=True)],
        footprint_libs=[
            FootprintLibrary("NewFP", "Custom/Footprints/NewFP.pretty", "Custom", selected=True)
        ],
    )


def test_generate_with_read_only_sym_table_logs_one_error_and_finishes(
    make_window, qtbot
):
    w = make_window([_new_lib_scan()])
    repo = make_window.repo
    sym_table = repo / "sym-lib-table"
    # The table lacks "New", so the regenerated text differs and a write is attempted
    sym_table.write_bytes(_managed_table("sym_lib_table", []))
    os.chmod(sym_table, stat.S_IREAD)
    try:
        with qtbot.captureExceptions() as exceptions:
            w._on_generate()
        assert exceptions == []
    finally:
        os.chmod(sym_table, stat.S_IREAD | stat.S_IWRITE)

    lines = w._log._text.toPlainText().splitlines()
    assert len([ln for ln in lines if "Could not write sym-lib-table" in ln]) == 1
    assert (repo / "fp-lib-table").exists()
    config = json.loads(make_window.config_file.read_text(encoding="utf-8"))
    assert config["environment"]["vars"]["KICAD_LIB_GITHUB"] == str(repo).replace("\\", "/")
    assert any("Updated" in ln for ln in lines)
    assert w._dest_combo.itemText(0) == str(repo)


def test_generate_without_kicad_config_warns_and_still_writes_both_tables(make_window):
    w = make_window([_new_lib_scan()], empty_config=True)
    repo = make_window.repo

    w._on_generate()

    text = w._log._text.toPlainText()
    assert text.count("Could not find KiCad config directory") == 1
    html = w._log._text.toHtml()
    line = next(ln for ln in html.splitlines() if "Could not find KiCad config directory" in ln)
    assert "#cc7700" in line.lower()
    assert (repo / "sym-lib-table").exists()
    assert (repo / "fp-lib-table").exists()


# ── Scan funnel and busy guard (HARD-05) ──────────────────────────────────


def _gated(result, gate):
    """A fake scan that blocks until gate is set (5 s cap so a broken guard fails)."""
    def run():
        gate.wait(5)
        return result
    return run


def _raising(message):
    def run():
        raise RuntimeError(message)
    return run


def _scan_controls(w):
    return [
        w._act_rescan, w._act_set_kicad_path, w._act_generate,
        w._rescan_btn, w._generate_btn,
    ]


def _log_text(w):
    return w._log._text.toPlainText()


def test_busy_rescans_are_dropped_and_controls_disabled(make_window, qtbot):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    calls = make_window.calls
    try:
        qtbot.waitUntil(lambda: len(calls) == 1, timeout=5000)
        assert not any(c.isEnabled() for c in _scan_controls(w))

        w._on_rescan()
        w._on_rescan()

        assert len(calls) == 1
        assert _log_text(w).count("already running") == 2
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert all(c.isEnabled() for c in _scan_controls(w))
    # Dropped requests are never replayed after the scan ends
    qtbot.wait(100)
    assert len(calls) == 1


def test_busy_state_clears_then_one_rescan_starts_exactly_one_scan(make_window, qtbot):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    calls = make_window.calls
    gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert len(calls) == 1

    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert len(calls) == 2


def test_busy_set_kicad_path_opens_no_dialog_and_starts_no_scan(
    make_window, qtbot, monkeypatch
):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    calls = make_window.calls
    dialogs = []
    monkeypatch.setattr(
        main_window.QFileDialog, "getExistingDirectory",
        lambda *a, **k: dialogs.append(a) or "",
    )
    try:
        qtbot.waitUntil(lambda: len(calls) == 1, timeout=5000)
        w._on_set_kicad_path()
        assert dialogs == []
        assert len(calls) == 1
        assert "already running" in _log_text(w)
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)


def test_scan_error_clears_busy_state(make_window, qtbot):
    w = make_window([ScanResult(), _raising("boom")])

    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert "Scan error: boom" in _log_text(w)
    assert all(c.isEnabled() for c in _scan_controls(w))


def test_busy_state_clears_after_empty_scan_result(make_window):
    w = make_window([ScanResult()])

    assert "Found 0 symbol libraries" in _log_text(w)
    assert w._worker is None
    assert all(c.isEnabled() for c in _scan_controls(w))


def test_rescan_with_populate_raising_still_clears_busy_state(
    make_window, qtbot, monkeypatch
):
    w = make_window([ScanResult()])

    def boom(_result):
        raise RuntimeError("populate boom")

    monkeypatch.setattr(w._tree, "populate", boom)
    with qtbot.captureExceptions() as exceptions:
        w._on_rescan()
        qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert any("populate boom" in str(exc[1]) for exc in exceptions)
    assert all(c.isEnabled() for c in _scan_controls(w))


def test_scan_issue_is_logged_in_its_severity_colour(make_window):
    scan = ScanResult(issues=[Issue(Severity.WARNING, "scan.test", "[x] warn")])

    w = make_window([scan])

    assert "[x] warn" in _log_text(w)
    assert "No warnings." not in _log_text(w)
    html = w._log._text.toHtml()
    line = next(ln for ln in html.splitlines() if "[x] warn" in ln)
    assert "#cc7700" in line.lower()


def test_close_while_scanning_waits_for_worker(make_window):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    worker = w._worker
    timer = threading.Timer(0.2, gate.set)
    timer.start()
    try:
        w.close()
        assert not worker.isRunning()
    finally:
        gate.set()
        timer.cancel()
        worker.wait(5000)


# ── Selection policy: startup pre-selection vs rescan re-apply (D-01, D-04, D-05) ──

WURTH_SYM = "WurthElektronik/KiCad-Library/symbols/{}.kicad_sym"
WURTH_FP = "WurthElektronik/KiCad-Library/footprints/{}.pretty"


def _sym(nickname, source="Custom", refs=(), peers=(), selected=False):
    base = "Custom/Symbols/{}.kicad_sym" if source == "Custom" else WURTH_SYM
    return SymbolLibrary(
        nickname, base.format(nickname), source,
        footprint_refs=[FootprintRef(*r) for r in refs],
        selected=selected, collision_peers=list(peers),
    )


def _fp(nickname, source="Custom", peers=(), selected=False):
    base = "Custom/Footprints/{}.pretty" if source == "Custom" else WURTH_FP
    return FootprintLibrary(
        nickname, base.format(nickname), source,
        selected=selected, collision_peers=list(peers),
    )


def _write_tables(dest, sym_paths=None, fp_paths=None):
    """Write managed sym-lib-table / fp-lib-table files holding the given rel_paths."""
    for file_name, tag, paths in (
        ("sym-lib-table", "sym_lib_table", sym_paths),
        ("fp-lib-table", "fp_lib_table", fp_paths),
    ):
        if paths is None:
            continue
        entries = [(Path(p).stem, p) for p in paths]
        (dest / file_name).write_bytes(_managed_table(tag, entries))


def _selected(libs):
    return {lib.rel_path for lib in libs if lib.selected}


def _rescan_and_wait(w, qtbot):
    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)


def _assert_one_selected_per_nickname(w):
    for libs in (w._scan_result.symbol_libs, w._scan_result.footprint_libs):
        by_nickname = {}
        for lib in libs:
            if lib.selected:
                by_nickname.setdefault(lib.nickname, []).append(lib.rel_path)
        assert all(len(paths) == 1 for paths in by_nickname.values()), by_nickname


def _check(item, on=True):
    item.setCheckState(
        0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
    )


def test_startup_preselects_tables_including_unreferenced_footprint(
    make_window, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], ["Custom/Footprints/Solo.pretty"])

    w = make_window([ScanResult(symbol_libs=[_sym("S")], footprint_libs=[_fp("Solo")])], repo=repo)

    assert _selected(w._scan_result.symbol_libs) == {"Custom/Symbols/S.kicad_sym"}
    assert _selected(w._scan_result.footprint_libs) == {"Custom/Footprints/Solo.pretty"}
    solo_item = w._tree._fp_items["Custom/Footprints/Solo.pretty"]
    assert solo_item.checkState(0) == Qt.CheckState.Checked
    _assert_one_selected_per_nickname(w)


def _selection_scan_one():
    return ScanResult(
        symbol_libs=[_sym("S"), _sym("S2"), _sym("Gone")],
        footprint_libs=[_fp("Solo2")],
    )


def _selection_scan_two():
    return ScanResult(
        symbol_libs=[_sym("S"), _sym("S2"), _sym("New")],
        footprint_libs=[_fp("Solo2")],
    )


def test_rescan_keeps_selection_by_rel_path_and_ignores_tables(
    make_window, qtbot, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(
        repo, ["Custom/Symbols/S.kicad_sym", "Custom/Symbols/Gone.kicad_sym"], []
    )
    w = make_window([_selection_scan_one, _selection_scan_two], repo=repo)
    assert _selected(w._scan_result.symbol_libs) == {
        "Custom/Symbols/S.kicad_sym", "Custom/Symbols/Gone.kicad_sym",
    }

    _check(w._tree._sym_items["Custom/Symbols/S2.kicad_sym"])
    _check(w._tree._sym_items["Custom/Symbols/S.kicad_sym"], on=False)
    _check(w._tree._fp_items["Custom/Footprints/Solo2.pretty"])
    # A changed table must not matter any more: it would select New if consulted
    _write_tables(
        repo, ["Custom/Symbols/New.kicad_sym"], ["Custom/Footprints/Other.pretty"]
    )

    _rescan_and_wait(w, qtbot)

    result = w._scan_result
    assert _selected(result.symbol_libs) == {"Custom/Symbols/S2.kicad_sym"}
    assert _selected(result.footprint_libs) == {"Custom/Footprints/Solo2.pretty"}
    new_item = w._tree._sym_items["Custom/Symbols/New.kicad_sym"]
    assert new_item.checkState(0) == Qt.CheckState.Unchecked
    text = _log_text(w)
    assert "Kept 2 selections" in text
    dropped = next(ln for ln in text.splitlines() if "Dropped 1 selections" in ln)
    assert "Custom/Symbols/Gone.kicad_sym" in dropped
    _assert_one_selected_per_nickname(w)


def _collision_scan():
    custom_path = "Custom/Symbols/Same.kicad_sym"
    wurth_path = WURTH_SYM.format("Same")
    return ScanResult(symbol_libs=[
        _sym("Same", peers=[wurth_path]),
        _sym("Same", source="WurthElektronik", peers=[custom_path]),
    ])


def test_rescan_keeps_the_collided_library_the_user_chose(make_window, qtbot):
    w = make_window([_collision_scan])
    wurth_path = WURTH_SYM.format("Same")
    assert _selected(w._scan_result.symbol_libs) == set()

    _check(w._tree._sym_items[wurth_path])
    _rescan_and_wait(w, qtbot)

    assert _selected(w._scan_result.symbol_libs) == {wurth_path}
    assert w._tree._sym_items[wurth_path].checkState(0) == Qt.CheckState.Checked
    custom_item = w._tree._sym_items["Custom/Symbols/Same.kicad_sym"]
    assert custom_item.checkState(0) == Qt.CheckState.Unchecked
    _assert_one_selected_per_nickname(w)


def test_set_kicad_path_rescans_with_the_same_reapply_behaviour(
    make_window, qtbot, monkeypatch, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], [])
    folder = tmp_path / "new_kicad_fp"
    folder.mkdir()
    monkeypatch.setattr(
        main_window.QFileDialog, "getExistingDirectory", lambda *a, **k: str(folder)
    )
    w = make_window([_selection_scan_one, _selection_scan_two], repo=repo)
    _check(w._tree._sym_items["Custom/Symbols/S2.kicad_sym"])
    _check(w._tree._sym_items["Custom/Symbols/S.kicad_sym"], on=False)

    w._on_set_kicad_path()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert make_window.calls[-1][1] == folder
    assert _selected(w._scan_result.symbol_libs) == {"Custom/Symbols/S2.kicad_sym"}
    _assert_one_selected_per_nickname(w)


def _both_peers_in_tables_scan():
    same_c, same_w = "Custom/Symbols/Same.kicad_sym", WURTH_SYM.format("Same")
    dup_c, dup_w = "Custom/Footprints/Dup.pretty", WURTH_FP.format("Dup")
    return ScanResult(
        symbol_libs=[
            _sym("Same", peers=[same_w]),
            _sym("Same", source="WurthElektronik", peers=[same_c]),
        ],
        footprint_libs=[
            _fp("Dup", peers=[dup_w]),
            _fp("Dup", source="WurthElektronik", peers=[dup_c]),
        ],
    )


def test_startup_collision_trim_keeps_one_peer_and_warns_once_per_group(
    make_window, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    same_c, same_w = "Custom/Symbols/Same.kicad_sym", WURTH_SYM.format("Same")
    dup_c, dup_w = "Custom/Footprints/Dup.pretty", WURTH_FP.format("Dup")
    # A table written before Phase 2 can hold both peers under one nickname
    (repo / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("Same", same_c), ("Same", same_w)])
    )
    (repo / "fp-lib-table").write_bytes(
        _managed_table("fp_lib_table", [("Dup", dup_c), ("Dup", dup_w)])
    )

    w = make_window([_both_peers_in_tables_scan], repo=repo)

    assert _selected(w._scan_result.symbol_libs) == {same_c}
    assert _selected(w._scan_result.footprint_libs) == {dup_c}
    assert w._tree._sym_items[same_w].checkState(0) == Qt.CheckState.Unchecked
    assert w._tree._fp_items[dup_w].checkState(0) == Qt.CheckState.Unchecked
    lines = [
        ln for ln in _log_text(w).splitlines() if "only one library per nickname" in ln
    ]
    assert len(lines) == 2
    html_lines = [
        ln for ln in w._log._text.toHtml().splitlines()
        if "only one library per nickname" in ln
    ]
    assert len(html_lines) == 2
    assert all("#cc7700" in ln.lower() for ln in html_lines)
    _assert_one_selected_per_nickname(w)


def _linked_scan():
    fp_c, fp_w = "Custom/Footprints/FpLib.pretty", WURTH_FP.format("FpLib")
    return ScanResult(
        symbol_libs=[_sym("S", refs=[("FpLib", "X", True)])],
        footprint_libs=[
            _fp("FpLib", peers=[fp_w]),
            _fp("FpLib", source="WurthElektronik", peers=[fp_c]),
            _fp("Solo"),
        ],
    )


def test_startup_selects_footprints_linked_to_preselected_symbols_then_rescan_keeps_flags(
    make_window, qtbot, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    fp_c, fp_w = "Custom/Footprints/FpLib.pretty", WURTH_FP.format("FpLib")
    solo = "Custom/Footprints/Solo.pretty"
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], [solo])

    w = make_window([_linked_scan, _linked_scan], repo=repo)

    assert _selected(w._scan_result.footprint_libs) == {fp_c, solo}
    assert w._tree._fp_items[fp_c].checkState(0) == Qt.CheckState.Checked
    assert w._tree._fp_items[fp_w].checkState(0) == Qt.CheckState.Unchecked
    assert "linked to the pre-selected symbols" in _log_text(w)
    _assert_one_selected_per_nickname(w)

    # HARD-07: after a rescan the user's footprint flags are kept as they are
    _check(w._tree._fp_items[fp_c], on=False)
    _rescan_and_wait(w, qtbot)

    assert _selected(w._scan_result.symbol_libs) == {"Custom/Symbols/S.kicad_sym"}
    assert _selected(w._scan_result.footprint_libs) == {solo}
    _assert_one_selected_per_nickname(w)


def test_startup_scan_error_then_rescan_starts_unchecked(make_window, qtbot, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], ["Custom/Footprints/Solo.pretty"])

    def fresh():
        return ScanResult(
            symbol_libs=[_sym("S", refs=[("FpLib", "X", True)])],
            footprint_libs=[_fp("FpLib"), _fp("Solo")],
        )

    w = make_window([_raising("boom"), fresh], repo=repo)

    text = _log_text(w)
    assert "Scan error: boom" in text
    marker = "nothing was pre-selected from the destination tables"
    assert len([ln for ln in text.splitlines() if marker in ln]) == 1
    assert w._startup_pending is False
    assert w._scan_result is None

    _rescan_and_wait(w, qtbot)

    result = w._scan_result
    assert [lib.selected for lib in result.symbol_libs] == [False]
    assert [lib.selected for lib in result.footprint_libs] == [False, False]
    for item in list(w._tree._sym_items.values()) + list(w._tree._fp_items.values()):
        assert item.checkState(0) == Qt.CheckState.Unchecked
    text = _log_text(w)
    assert "Kept 0 selections after rescan" in text
    assert "linked to the pre-selected symbols" not in text


def test_startup_finish_raising_consumes_startup_flag(make_window, qtbot, monkeypatch):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    assert w._startup_pending is True

    def boom(_result):
        raise RuntimeError("populate boom")

    with monkeypatch.context() as patch:
        patch.setattr(w._tree, "populate", boom)
        with qtbot.captureExceptions() as exceptions:
            gate.set()
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert exceptions
    assert w._startup_pending is False

    calls = []
    with monkeypatch.context() as patch:
        patch.setattr(w, "_apply_existing_selection", lambda r: calls.append("apply"))
        patch.setattr(w, "_select_linked_footprints", lambda r: calls.append("linked"))
        _rescan_and_wait(w, qtbot)
    assert calls == []
