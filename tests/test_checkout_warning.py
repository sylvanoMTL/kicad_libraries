"""D-26: a visible, non-blocking warning when KiCad reads its libraries from another
checkout than the one this app writes -- after Generate Tables (plan 13-19 Task 1) and
after Install Part (Task 2).

Own fixture (tests do not import from other test modules): isolated QSettings and
main_window.CHECKOUT_CONFIG_BASE pointed at a tmp folder in every test, so the owner's
real %APPDATA% KiCad config is never read.
"""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QMessageBox, QToolButton

from kicad_lib_manager import kicad_setup, library_scanner, main_window, settings
from kicad_lib_manager.models import FootprintLibrary, ScanResult, SymbolLibrary


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def _write_checkout_common(cfg: Path, version: str, github: str | None):
    folder = cfg / version
    folder.mkdir(parents=True, exist_ok=True)
    vars_obj = {"KICAD_LIB_GITHUB": github} if github is not None else None
    (folder / "kicad_common.json").write_text(
        json.dumps({"environment": {"vars": vars_obj}}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _new_lib_scan() -> ScanResult:
    return ScanResult(
        symbol_libs=[SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom", selected=True)],
        footprint_libs=[FootprintLibrary("NewFP", "Custom/Footprints/NewFP.pretty", "Custom", selected=True)],
    )


@pytest.fixture
def make_window(qtbot, monkeypatch, tmp_path):
    def make(scan=None, github=None, config_exists=True, wait=True):
        repo = tmp_path / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        fp_dir = tmp_path / "kicad_fp"
        fp_dir.mkdir(exist_ok=True)

        checkout_cfg = tmp_path / "checkout_cfg"
        if config_exists:
            _write_checkout_common(checkout_cfg, "10.0", github)
        make.checkout_cfg = checkout_cfg

        # The path-variable sync runs too (an independent writer, _sync_path_vars);
        # redirect it to its own synthetic tree so it never reaches the owner's real
        # %APPDATA% KiCad config either
        path_var_cfg = tmp_path / "path_var_cfg"
        (path_var_cfg / "10.0").mkdir(parents=True, exist_ok=True)
        (path_var_cfg / "10.0" / "kicad_common.json").write_text(
            '{"environment": {"vars": null}}\n', encoding="utf-8",
        )

        def fake_sync(repo_root, **kwargs):
            kwargs.setdefault("running", lambda: [])
            return library_scanner.sync_kicad_path_vars(
                repo_root, **kwargs,
                config_base=path_var_cfg, backup_root=tmp_path / "backups",
            )

        def fake_scan(root, progress=None, kicad_fp_dir=None, *, skip=None, checking=None):
            return scan if scan is not None else ScanResult()

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        monkeypatch.setattr(main_window, "CHECKOUT_CONFIG_BASE", checkout_cfg)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_path_vars", fake_sync)
        make.repo = repo
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        if wait:
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        return w

    make.repo = None
    make.checkout_cfg = None

    monkeypatch.setattr(
        main_window.MainWindow, "_question", lambda self, *a: QMessageBox.StandardButton.No
    )
    monkeypatch.setattr(main_window, "kicad_running", lambda: [])
    return make


def settle(qtbot, w):
    """Wait until the off-thread KiCad check and the path-variable question are done."""
    qtbot.waitUntil(lambda: not w._path_var_busy, timeout=5000)


# -- Task 1: Generate Tables (D-26) ---------------------------------------------------------


def test_generate_warns_on_other_checkout(qtbot, make_window, tmp_path):
    other = tmp_path / "other-checkout"
    w = make_window(scan=_new_lib_scan(), github=str(other))
    w.show()
    repo = make_window.repo

    w._on_generate()
    settle(qtbot, w)

    # the tables are still written (D-26: warn, not block)
    assert (repo / "sym-lib-table").exists()
    assert (repo / "fp-lib-table").exists()

    assert w._checkout_banner.isVisible()
    mismatch = kicad_setup.checkout_mismatch(repo, config_base=make_window.checkout_cfg)
    expected = kicad_setup.wrong_checkout_warning(mismatch)
    assert w._checkout_label.text() == expected
    assert str(repo).replace("\\", "/") in expected
    assert str(other).replace("\\", "/") in expected

    log_text = w._log._text.toPlainText()
    assert log_text.count(expected) == 1


def test_generate_without_variable_shows_nothing(qtbot, make_window):
    w = make_window(scan=_new_lib_scan(), github=None, config_exists=False)
    w.show()

    w._on_generate()
    settle(qtbot, w)

    assert not w._checkout_banner.isVisible()
    log_text = w._log._text.toPlainText()
    assert "KICAD_LIB_GITHUB" not in log_text
    assert "KiCad reads its libraries from" not in log_text


def test_matching_generate_hides_banner(qtbot, make_window, tmp_path):
    other = tmp_path / "other-checkout"
    w = make_window(scan=_new_lib_scan(), github=str(other))
    w.show()
    repo = make_window.repo

    w._on_generate()
    settle(qtbot, w)
    assert w._checkout_banner.isVisible()

    # Point KICAD_LIB_GITHUB at the repo itself: the next Generate hides the banner
    _write_checkout_common(make_window.checkout_cfg, "10.0", str(repo))
    w._on_generate()
    settle(qtbot, w)

    assert not w._checkout_banner.isVisible()


def test_banner_dismiss_and_plain_text(qtbot, make_window, tmp_path):
    github = str(tmp_path / "other") + "<b>BOLD"
    w = make_window(scan=_new_lib_scan(), github=github)
    w.show()

    w._on_generate()
    settle(qtbot, w)

    assert w._checkout_label.textFormat() == Qt.TextFormat.PlainText
    assert "<b>BOLD" in w._checkout_label.text()  # shown literally, never as markup
    assert w._checkout_banner.isVisible()

    dismiss = w._checkout_banner.findChild(QToolButton)
    dismiss.click()
    assert not w._checkout_banner.isVisible()
