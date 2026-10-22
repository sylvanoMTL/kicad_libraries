"""Import dialog tracer (plan 05-01): UL zip in, real plan previewed, that plan installed.

The dialog runs on real TaskWorker threads. The core functions are the real ones unless a
test swaps one for a gated fake (dataclasses.replace on ImportCore) to hold a worker open.
Everything is written into tmp_path copies; QSettings is redirected like test_main_window.
"""

import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from kicad_lib_manager import settings
from kicad_lib_manager.importer.package import open_package as real_open_package
from kicad_lib_manager.importer.plan import InstallResult, ToolContext
from kicad_lib_manager.importer.applier import apply_plan as real_apply_plan
from kicad_lib_manager.importer.planner import build_plan as real_build_plan
from kicad_lib_manager.importer.preview import file_counts, preview_sections
from kicad_lib_manager.importer.suggest import suggest_library as real_suggest_library
from kicad_lib_manager.widgets.import_dialog import ImportCore, ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
LIB = "IC_Battery_Charger_TI"


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
def gates():
    """Events a test hands to gated fakes; all are released at teardown so no worker outlives a test."""
    held: list[threading.Event] = []
    yield held
    for gate in held:
        gate.set()


def core_with(**changes) -> ImportCore:
    return replace(ImportCore(), detect_tools=lambda kicad_fp_dir: ToolContext(), **changes)


@pytest.fixture
def make_dialog(qtbot, custom_copy, tmp_path, gates):
    def make(core: ImportCore | None = None, open_now: bool = True, show: bool = False) -> ImportDialog:
        dialog = ImportDialog(
            custom_copy.repo_root,
            custom_copy,
            core=core or core_with(),
            backup_root=tmp_path / "backups",
        )
        qtbot.addWidget(dialog)
        if show:
            dialog.show()
        if open_now:
            dialog.open_path(UL_ZIP)
        return dialog

    return make


def wait_plan(qtbot, dialog: ImportDialog, timeout: int = 30000) -> None:
    qtbot.waitUntil(
        lambda: dialog._plan is not None and dialog._building is None and dialog._queued is None,
        timeout=timeout,
    )


def set_library(dialog: ImportDialog, name: str, activate: bool = True) -> None:
    dialog._library_combo.setEditText(name)
    if activate:
        dialog._library_combo.textActivated.emit(name)


def files_rows(dialog: ImportDialog) -> tuple[str, list[str]]:
    top = dialog._preview.topLevelItem(0)
    return top.text(0), [top.child(i).text(0) for i in range(top.childCount())]


def test_tracer_ul_import_end_to_end(qtbot, make_dialog, custom_copy):
    dialog = make_dialog()
    assert not dialog._install_btn.isEnabled()
    wait_plan(qtbot, dialog)
    set_library(dialog, LIB)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)

    title, rows = files_rows(dialog)
    assert title == "Files (3)"
    assert rows == [
        "+ Custom/3DModels/CSD85301Q2.stp",
        "+ Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
        "~ Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
    ]
    assert dialog._strip.text().startswith("✓ Ready to install: 2 new, 1 modified, 0 unchanged files")

    with qtbot.waitSignal(dialog.installed, timeout=60000) as blocker:
        dialog._install_btn.click()
    result, plan = blocker.args
    assert result.ok
    assert plan is dialog._plan
    assert dialog._stack.currentWidget() is dialog._result_page
    assert dialog._banner.text() == "✓ Installed CSD85301Q2 into IC_Battery_Charger_TI"
    assert dialog.result is result
    listed = [dialog._result_list.item(i).text() for i in range(dialog._result_list.count())]
    assert "Custom/3DModels/CSD85301Q2.stp" in listed
    pretty = custom_copy.footprints_dir / f"{LIB}.pretty"
    assert (pretty / "DQK0006B.kicad_mod").is_file()
    assert (custom_copy.models_dir / "CSD85301Q2.stp").is_file()


def test_tracer_nothing_written_before_install(qtbot, make_dialog, custom_copy, snapshot):
    before = snapshot(custom_copy.repo_root)
    dialog = make_dialog()
    wait_plan(qtbot, dialog)
    assert snapshot(custom_copy.repo_root) == before
    for name in ("A_x_TI", "B_x_TI"):
        set_library(dialog, name)
        qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
        assert dialog._plan.library == name
    assert snapshot(custom_copy.repo_root) == before


def test_supersede_discards_stale_result(qtbot, make_dialog, gates):
    calls: list[str] = []

    def gated_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        gate = threading.Event()
        gates.append(gate)
        calls.append(options.library)
        assert gate.wait(30)
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = make_dialog(core_with(build_plan=gated_build))
    qtbot.waitUntil(lambda: len(calls) == 1, timeout=30000)
    first = calls[0]
    for name in ("A_x_TI", "B_x_TI", "C_x_TI"):
        set_library(dialog, name, activate=False)
        dialog._request_rebuild()
    gates[0].set()
    qtbot.waitUntil(lambda: len(calls) == 2, timeout=30000)
    # the stale first result was dropped: nothing rendered, nothing installable
    assert dialog._plan is None
    assert dialog._preview.topLevelItemCount() == 0
    assert not dialog._install_btn.isEnabled()
    gates[1].set()
    wait_plan(qtbot, dialog)
    assert calls == [first, "C_x_TI"]
    assert dialog._plan.library == "C_x_TI"
    assert dialog._install_btn.isEnabled()


def test_install_uses_latest_plan_object(qtbot, make_dialog):
    recorded = []

    def recording_apply(plan, *, backup_root=None, progress=None):
        recorded.append(plan)
        return real_apply_plan(plan, backup_root=backup_root, progress=progress)

    dialog = make_dialog(core_with(apply_plan=recording_apply))
    wait_plan(qtbot, dialog)
    for name in ("A_x_TI", "B_x_TI"):
        set_library(dialog, name)
        wait_plan(qtbot, dialog)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    with qtbot.waitSignal(dialog.installed, timeout=60000):
        dialog._install_btn.click()
    assert len(recorded) == 1
    assert recorded[0] is dialog._plan
    assert recorded[0].library == "B_x_TI"


def _good_suggestion(meta, existing=()):
    return replace(real_suggest_library(meta, existing), name=LIB, placeholders=())


def test_rebuild_failure_keeps_tree_and_logs(qtbot, make_dialog):
    count = {"n": 0}

    def flaky_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        count["n"] += 1
        if count["n"] == 2:
            raise RuntimeError("boom")
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = make_dialog(core_with(build_plan=flaky_build, suggest_library=_good_suggestion), open_now=False)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    dialog.open_path(UL_ZIP)
    wait_plan(qtbot, dialog)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    first_rows = files_rows(dialog)
    assert first_rows[0] == "Files (3)"

    dialog._request_rebuild()
    qtbot.waitUntil(lambda: count["n"] == 2 and dialog._building is None, timeout=30000)
    assert files_rows(dialog) == first_rows
    assert not dialog._install_btn.isEnabled()
    assert any(i.text.startswith("Import step failed: RuntimeError: boom") for i in logged)

    # the next edit retries the build and recovers
    dialog._request_rebuild()
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)


def test_close_waits_and_closes_package(qtbot, make_dialog, gates):
    events: list[str] = []
    count = {"n": 0}

    def open_recording(path, repo_root, progress=None):
        package = real_open_package(path, repo_root, progress)
        original = package.close

        def close():
            events.append("close")
            original()

        package.close = close
        return package

    def gated_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        count["n"] += 1
        if count["n"] == 2:
            gate = threading.Event()
            gates.append(gate)
            assert gate.wait(30)
            events.append("build_end")
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = make_dialog(core_with(open_package=open_recording, build_plan=gated_build), show=True)
    wait_plan(qtbot, dialog)
    dialog._request_rebuild()
    qtbot.waitUntil(lambda: len(gates) == 1, timeout=30000)
    threading.Timer(0.3, gates[0].set).start()
    started = time.monotonic()
    dialog.reject()
    assert time.monotonic() - started >= 0.2
    assert events == ["build_end", "close"]
    assert not dialog.isVisible()


def test_close_refused_while_installing(qtbot, make_dialog, gates):
    started = threading.Event()

    def gated_apply(plan, *, backup_root=None, progress=None):
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        return real_apply_plan(plan, backup_root=backup_root, progress=progress)

    dialog = make_dialog(core_with(apply_plan=gated_apply), show=True)
    wait_plan(qtbot, dialog)
    set_library(dialog, LIB)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: started.is_set() and dialog.is_installing(), timeout=30000)

    dialog.reject()
    dialog.close()
    assert dialog.isVisible()
    assert dialog.is_installing()

    gates[0].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)
    qtbot.waitUntil(lambda: not dialog.is_installing(), timeout=30000)
    dialog.reject()
    assert not dialog.isVisible()


def test_core_calls_run_off_the_gui_thread(qtbot, make_dialog):
    main = threading.get_ident()
    seen: dict[str, int] = {}

    def spy(name, fn):
        def wrapper(*args, **kwargs):
            seen[name] = threading.get_ident()
            return fn(*args, **kwargs)

        return wrapper

    import kicad_lib_manager.importer.detect as detect
    from kicad_lib_manager.importer.layout import list_existing_libraries

    core = core_with(
        open_package=spy("open_package", real_open_package),
        detect_candidate=spy("detect_candidate", detect.detect_candidate),
        build_plan=spy("build_plan", real_build_plan),
        apply_plan=spy("apply_plan", real_apply_plan),
        list_existing_libraries=spy("list_existing_libraries", list_existing_libraries),
        suggest_library=spy("suggest_library", real_suggest_library),
    )
    dialog = make_dialog(core)
    wait_plan(qtbot, dialog)
    set_library(dialog, LIB)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    with qtbot.waitSignal(dialog.installed, timeout=60000):
        dialog._install_btn.click()
    assert set(seen) == {
        "open_package", "detect_candidate", "build_plan", "apply_plan",
        "list_existing_libraries", "suggest_library",
    }
    assert all(ident != main for ident in seen.values())


def test_noop_plan_disables_install(qtbot, make_dialog):
    first = make_dialog()
    wait_plan(qtbot, first)
    set_library(first, LIB)
    qtbot.waitUntil(lambda: first._install_btn.isEnabled(), timeout=30000)
    with qtbot.waitSignal(first.installed, timeout=60000):
        first._install_btn.click()
    first.accept()

    second = make_dialog()
    wait_plan(qtbot, second)
    set_library(second, LIB)
    wait_plan(qtbot, second)
    qtbot.waitUntil(lambda: second._strip.text().startswith("Nothing to install"), timeout=30000)
    assert second._strip.text() == f"Nothing to install: this part is already in {LIB}."
    assert not second._install_btn.isEnabled()


def test_refused_package_stays_on_start_and_logs(qtbot, make_dialog, tmp_path):
    bogus = tmp_path / "not_a_package.txt"
    bogus.write_text("x", encoding="utf-8")
    dialog = make_dialog(open_now=False)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    dialog.open_path(bogus)
    qtbot.waitUntil(lambda: bool(logged), timeout=30000)
    assert dialog._stack.currentWidget() is dialog._start_page
    assert dialog._issue_box.isHidden() is False
    assert any("not a .zip file" in row for row in issue_rows(dialog))
    assert dialog._plan is None


def test_preview_sections_follow_plan_ops(ul_package, custom_copy):
    from kicad_lib_manager.importer.plan import InstallOptions

    package, candidate = ul_package
    options = InstallOptions(
        library=LIB,
        symbol=candidate.symbols[0].name,
        footprints=tuple(f.name for f in candidate.footprints),
        model=candidate.models[0].filename,
    )
    plan = real_build_plan(candidate, options, custom_copy)
    files = preview_sections(plan, candidate, options)[0]  # plan 05-06 added the other sections after Files
    assert files.title == "Files (3)"
    assert [r.text for r in files.rows] == [
        "+ Custom/3DModels/CSD85301Q2.stp",
        "+ Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
        "~ Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
    ]
    assert files.rows[0].detail.startswith("new, ") and files.rows[0].detail.endswith(" KiB")
    assert [r.detail for r in files.rows[1:]] == ["new", "modified"]
    assert [r.op_index for r in files.rows] == [0, 1, 2]
    counts = file_counts(plan, candidate, options)
    assert (counts.new, counts.modified, counts.unchanged) == (2, 1, 0)

    fresh = real_build_plan(candidate, replace(options, library="A_x_TI"), custom_copy)
    fresh_files = preview_sections(fresh, candidate, options)[0]
    assert fresh_files.rows[0].text == "+ Custom/Footprints/A_x_TI.pretty/"
    assert file_counts(fresh, candidate, options).new == 3


# -- Start page (plan 05-05): these tests use a synthetic Custom/ layout and fake core calls, so
# they run without the Custom submodule ---------------------------------------------------------

import os  # noqa: E402

from kicad_lib_manager.importer.layout import RepoLayout  # noqa: E402
from kicad_lib_manager.importer.package import Package  # noqa: E402
from kicad_lib_manager.models import Issue, Severity  # noqa: E402


@pytest.fixture
def start_layout(tmp_path):
    from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS, write_custom_layout

    repo = write_custom_layout(tmp_path / "repo", CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(repo)


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "Downloads"
    folder.mkdir()
    return folder


def _zip_at(folder: Path, name: str, age_seconds: float) -> Path:
    path = folder / name
    path.write_bytes(b"PK")
    when = time.time() - age_seconds
    os.utime(path, (when, when))
    return path


def fake_package(path: Path, issues=()) -> Package:
    return Package(source=Path(path), kind="zip", issues=list(issues))


@pytest.fixture
def make_start_dialog(qtbot, start_layout, downloads, gates):
    def make(show: bool = True, **changes) -> ImportDialog:
        fields = {
            "detect_tools": lambda kicad_fp_dir: ToolContext(),
            "downloads_dir": lambda: downloads,
            **changes,
        }
        core = replace(ImportCore(), **fields)
        dialog = ImportDialog(start_layout.repo_root, start_layout, core=core)
        qtbot.addWidget(dialog)
        if show:
            dialog.show()
        return dialog

    return make


def wait_offer(qtbot, dialog: ImportDialog) -> None:
    qtbot.waitUntil(lambda: dialog._offer_label.isVisible(), timeout=10000)


def test_start_page_offers_newest_zip(qtbot, make_start_dialog, downloads):
    _zip_at(downloads, "older.zip", 7200)
    newer = _zip_at(downloads, "newer.zip", 5)
    dialog = make_start_dialog()
    wait_offer(qtbot, dialog)
    # full_text: the offscreen test platform has no fonts, so the shown text may be elided
    assert dialog._offer_label.full_text() == "Newest in Downloads: newer.zip (just now)"
    assert dialog._offer_label.toolTip() == str(newer)
    assert dialog._offer_open_btn.isVisible()
    assert dialog._offer_open_btn.isEnabled()


def test_start_page_no_zip_message(qtbot, make_start_dialog, downloads):
    (downloads / "notes.txt").write_text("x", encoding="utf-8")
    dialog = make_start_dialog()
    wait_offer(qtbot, dialog)
    assert dialog._offer_label.text() == "No .zip files found in your Downloads folder."
    assert not dialog._offer_open_btn.isVisible()


def test_start_page_no_downloads_folder(qtbot, make_start_dialog):
    dialog = make_start_dialog(downloads_dir=lambda: None)
    wait_offer(qtbot, dialog)
    assert dialog._offer_label.text() == "Downloads folder not found."
    assert not dialog._offer_open_btn.isVisible()


def test_start_page_never_auto_opens(qtbot, make_start_dialog, downloads):
    offered = _zip_at(downloads, "part.zip", 30)
    calls: list[Path] = []

    def recording_open(path, repo_root, progress=None):
        calls.append(Path(path))
        return fake_package(path)

    dialog = make_start_dialog(open_package=recording_open, detect_candidate=lambda package: (None, []))
    wait_offer(qtbot, dialog)
    qtbot.wait(150)
    assert calls == []

    dialog._offer_open_btn.click()
    qtbot.waitUntil(lambda: len(calls) == 1, timeout=10000)
    assert calls == [offered]


def test_start_page_layout_and_focus(qtbot, make_start_dialog):
    dialog = make_start_dialog()
    assert dialog._start_heading.text() == "Choose a part package"
    assert dialog._start_heading.font().pointSize() == 10
    assert dialog._start_heading.font().bold()
    assert dialog._start_body.text() == (
        "Open a .zip from Ultra Librarian, SnapEDA or SamacSys, or a folder of KiCad files. "
        "Nothing is written until you click Install Part."
    )
    assert dialog._start_column.maximumWidth() == 560
    assert dialog.focusWidget() is dialog._browse_btn


def test_start_page_offer_elides_long_name_and_keeps_full_path(qtbot, make_start_dialog, downloads):
    long_name = "ul_" + "very_long_component_name_" * 8 + "end.zip"
    path = _zip_at(downloads, long_name, 3 * 86400)
    dialog = make_start_dialog()
    wait_offer(qtbot, dialog)
    shown = dialog._offer_label.text()
    assert dialog._offer_label.full_text() == f"Newest in Downloads: {long_name} (3 days ago)"
    assert shown != dialog._offer_label.full_text()
    assert shown.startswith("Newest in Downloads: ul")
    assert shown.endswith(" (3 days ago)")
    assert "…" in shown
    assert dialog._offer_label.toolTip() == str(path)


# -- Browse, refused or empty packages, package header (plan 05-05 task 2) -----------------------

from kicad_lib_manager.widgets import import_dialog as import_dialog_module  # noqa: E402
from kicad_lib_manager.widgets.theme import AMBER, ERROR  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402


def issue_rows(dialog: ImportDialog) -> list[str]:
    return [dialog._issue_list.item(i).text() for i in range(dialog._issue_list.count())]


def wait_issue_box(qtbot, dialog: ImportDialog) -> None:
    qtbot.waitUntil(lambda: dialog._issue_box.isVisible(), timeout=30000)


def nothing_found_core(issues=(), **changes) -> dict:
    """Core fields for a package that opens fine but yields no candidate."""
    return {
        "open_package": lambda path, repo_root, progress=None: fake_package(path, issues),
        "detect_candidate": lambda package: (None, []),
        **changes,
    }


def test_start_page_browse_uses_last_dir(qtbot, make_start_dialog, downloads, tmp_path, monkeypatch):
    opened: list[Path] = []

    def recording_open(path, repo_root, progress=None):
        opened.append(Path(path))
        return fake_package(path)

    dialog = make_start_dialog(open_package=recording_open, detect_candidate=lambda package: (None, []))
    saved = tmp_path / "saved"
    saved.mkdir()
    settings.save_import_dir(saved)
    picked = tmp_path / "picked"
    picked.mkdir()
    zip_path = picked / "p.zip"
    zip_path.write_bytes(b"PK")
    folder_path = picked / "loose_files"
    folder_path.mkdir()
    starts: list[str] = []

    def fake_open_file(parent, caption, directory, file_filter):
        starts.append(directory)
        return str(zip_path), ""

    def fake_open_dir(parent, caption, directory):
        starts.append(directory)
        return str(folder_path)

    monkeypatch.setattr(import_dialog_module.QFileDialog, "getOpenFileName", staticmethod(fake_open_file))
    monkeypatch.setattr(import_dialog_module.QFileDialog, "getExistingDirectory", staticmethod(fake_open_dir))

    def idle():
        return dialog._open_worker is None and dialog._browse_btn.isEnabled()

    dialog._browse_btn.click()
    qtbot.waitUntil(lambda: opened == [zip_path] and idle(), timeout=30000)
    assert starts == [str(saved)]
    assert settings.load_import_dir() == picked

    # nothing saved: the dialog starts in the Downloads folder
    settings.get_settings().remove("import/last_dir")
    dialog._browse_btn.click()
    qtbot.waitUntil(lambda: len(opened) == 2 and idle(), timeout=30000)
    assert starts[-1] == str(downloads)

    # Browse folder... saves the picked folder's parent and opens the folder
    settings.get_settings().remove("import/last_dir")
    dialog._browse_folder_btn.click()
    qtbot.waitUntil(lambda: len(opened) == 3 and idle(), timeout=30000)
    assert opened[-1] == folder_path
    assert settings.load_import_dir() == picked


def test_start_page_browse_falls_back_to_home(qtbot, make_start_dialog, monkeypatch):
    dialog = make_start_dialog(downloads_dir=lambda: None, **nothing_found_core())
    starts: list[str] = []

    def fake_open_file(parent, caption, directory, file_filter):
        starts.append(directory)
        return "", ""

    monkeypatch.setattr(import_dialog_module.QFileDialog, "getOpenFileName", staticmethod(fake_open_file))
    dialog._browse_btn.click()
    assert starts == [str(Path.home())]
    assert dialog._open_worker is None  # cancelling opens nothing


def test_start_page_refused_zip_lists_issues(qtbot, make_start_dialog, tmp_path):
    from zipfixtures import LEGACY_DCM_BYTES, LEGACY_LIB_BYTES, LEGACY_MOD_BYTES, make_zip

    legacy = make_zip(
        tmp_path / "kicad5_only.zip",
        [("part.lib", LEGACY_LIB_BYTES), ("part.dcm", LEGACY_DCM_BYTES), ("part.mod", LEGACY_MOD_BYTES)],
    )
    packages: list[Package] = []

    def capturing_open(path, repo_root, progress=None):
        package = real_open_package(path, repo_root, progress)
        packages.append(package)
        return package

    dialog = make_start_dialog(open_package=capturing_open)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    dialog.open_path(legacy)
    wait_issue_box(qtbot, dialog)

    assert dialog._stack.currentWidget() is dialog._start_page
    assert dialog._issue_heading.text() == "This package can't be imported"
    rows = issue_rows(dialog)
    assert rows and all(row.startswith("✖ ") for row in rows)
    assert any("re-download as KiCad v6+" in row for row in rows)
    assert dialog._issue_closing.text() == "Pick another file."
    assert [f"✖ {i.text}" for i in logged if i.severity is Severity.ERROR] == rows
    assert dialog._issue_list.item(0).foreground().color().name().lower() == ERROR.lower()
    assert dialog._package is None
    assert packages and packages[0].staging_dir is None  # the package was closed


def test_nothing_found_shows_package_warnings(qtbot, make_start_dialog):
    warning = Issue(Severity.WARNING, "intake.test_warning", "Skipped 2 unreadable files")
    dialog = make_start_dialog(**nothing_found_core([warning]))
    logged = []
    dialog.issues_logged.connect(logged.extend)
    dialog.open_path(Path("some_package.zip"))
    wait_issue_box(qtbot, dialog)
    assert issue_rows(dialog) == ["⚠ Skipped 2 unreadable files"]
    assert dialog._issue_list.item(0).foreground().color().name().lower() == AMBER.lower()
    assert dialog._issue_closing.text() == (
        "Check that you downloaded the KiCad format, then pick another file."
    )
    assert logged == [warning]


def test_nothing_found_merges_package_and_detection_issues_once(qtbot, make_start_dialog):
    shared = Issue(Severity.WARNING, "intake.shared", "Shared note")
    detect_only = Issue(Severity.WARNING, "intake.detect", "Detection note")
    dialog = make_start_dialog(
        **nothing_found_core([shared], detect_candidate=lambda package: (None, [shared, detect_only]))
    )
    logged = []
    dialog.issues_logged.connect(logged.extend)
    dialog.open_path(Path("some_package.zip"))
    wait_issue_box(qtbot, dialog)
    assert issue_rows(dialog) == ["⚠ Shared note", "⚠ Detection note"]
    assert logged == [shared, detect_only]


def test_nothing_found_no_issues_message(qtbot, make_start_dialog):
    dialog = make_start_dialog(**nothing_found_core())
    dialog.open_path(Path("some_package.zip"))
    wait_issue_box(qtbot, dialog)
    assert issue_rows(dialog) == ["No KiCad symbol or footprint was found in this package."]
    assert dialog._issue_closing.text() == (
        "Check that you downloaded the KiCad format, then pick another file."
    )


def test_issue_text_is_plain(qtbot, make_start_dialog):
    markup = Issue(Severity.WARNING, "intake.markup", "<b>bold</b> <a href='http://x'>link</a>")
    dialog = make_start_dialog(**nothing_found_core([markup]))
    dialog.open_path(Path("some_package.zip"))
    wait_issue_box(qtbot, dialog)
    assert issue_rows(dialog) == ["⚠ <b>bold</b> <a href='http://x'>link</a>"]
    assert dialog._issue_closing.textFormat() == Qt.TextFormat.PlainText


def test_start_page_list_hidden_and_cleared(qtbot, make_start_dialog, gates):
    calls = {"n": 0}
    warning = Issue(Severity.WARNING, "intake.test_warning", "First package warning")

    def open_second_gated(path, repo_root, progress=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return fake_package(path, [warning])
        gate = threading.Event()
        gates.append(gate)
        progress("Reading member 3 of 9", 3, 9)
        assert gate.wait(30)
        return fake_package(path)

    dialog = make_start_dialog(
        open_package=open_second_gated, detect_candidate=lambda package: (None, [])
    )
    assert not dialog._issue_box.isVisible()  # hidden before any package is read
    dialog.open_path(Path("first.zip"))
    wait_issue_box(qtbot, dialog)
    assert issue_rows(dialog) == ["⚠ First package warning"]

    dialog.open_path(Path("second.zip"))
    qtbot.waitUntil(lambda: len(gates) == 1, timeout=30000)
    qtbot.waitUntil(lambda: dialog._reading_label.text() == "Reading member 3 of 9", timeout=30000)
    assert not dialog._issue_box.isVisible()
    assert dialog._issue_list.count() == 0
    assert dialog._reading_box.isVisible()
    assert not dialog._offer_row.isVisible()
    assert not dialog._browse_btn.isEnabled()
    assert not dialog._browse_folder_btn.isEnabled()
    gates[0].set()
    wait_issue_box(qtbot, dialog)
    assert dialog._browse_btn.isEnabled()
    assert not dialog._reading_box.isVisible()


def test_issue_list_caps_height_and_wraps(qtbot, make_start_dialog):
    many = [Issue(Severity.WARNING, f"intake.w{i}", f"Warning number {i} " + "word " * 40) for i in range(20)]
    dialog = make_start_dialog(**nothing_found_core(many))
    dialog.open_path(Path("some_package.zip"))
    wait_issue_box(qtbot, dialog)
    assert dialog._issue_list.count() == 20
    assert dialog._issue_list.maximumHeight() == 160
    assert dialog._issue_list.wordWrap()
    assert dialog._issue_list.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_change_returns_to_start_and_closes_package(qtbot, make_start_dialog):
    closed: list[str] = []

    def recording_open(path, repo_root, progress=None):
        package = real_open_package(path, repo_root, progress)
        original = package.close

        def close():
            closed.append("close")
            original()

        package.close = close
        return package

    dialog = make_start_dialog(open_package=recording_open)
    dialog.open_path(UL_ZIP)
    wait_plan(qtbot, dialog)
    assert dialog._stack.currentWidget() is dialog._edit_page
    assert dialog._package_label.text() == "Package: ul_CSD85301Q2.zip"
    assert dialog._vendor_label.text() == "Ultra Librarian"
    assert dialog.windowTitle() == "Import Part - ul_CSD85301Q2.zip"
    assert closed == []

    dialog._change_btn.click()
    assert dialog._stack.currentWidget() is dialog._start_page
    assert dialog.windowTitle() == "Import Part"
    assert dialog._building is None and dialog._queued is None
    assert dialog._plan is None and dialog._candidate is None
    assert closed == ["close"]
    assert dialog._browse_btn.isEnabled()
    assert not dialog._issue_box.isVisible()


@pytest.mark.parametrize(
    ("vendor", "label"),
    [("UltraLibrarian", "Ultra Librarian"), ("Loose", "Loose files"), ("Unknown", "Unknown vendor"), ("Odd", "Odd")],
)
def test_vendor_labels(vendor, label):
    assert import_dialog_module.vendor_label(vendor) == label


# -- Item picker (plan 05-07 task 1): synthetic Custom layout and synthetic zips, so these run without
# the Custom submodule ----------------------------------------------------------------------------

from kicad_lib_manager.importer.candidate import ImportCandidate  # noqa: E402
from kicad_lib_manager.importer.plan import InstallOptions  # noqa: E402
from kicad_lib_manager.widgets.theme import MUTED  # noqa: E402

_DATASHEET = {"Datasheet": "https://example.com/part"}


@pytest.fixture
def item_layout(tmp_path):
    from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS, write_custom_layout

    repo = write_custom_layout(tmp_path / "item_repo", CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(repo)


@pytest.fixture
def recorded():
    """Every InstallOptions the dialog handed to build_plan, in call order."""
    return []


def recording_build(recorded: list, inner=None):
    def build(candidate, options, layout, tools=ToolContext(), **kwargs):
        recorded.append(options)
        return (inner or real_build_plan)(candidate, options, layout, tools, **kwargs)

    return build


@pytest.fixture
def make_item_dialog(qtbot, item_layout, gates, recorded):
    def make(package: Path = UL_ZIP, show: bool = False, **changes) -> ImportDialog:
        fields = {
            "detect_tools": lambda kicad_fp_dir: ToolContext(),
            "downloads_dir": lambda: None,
            "build_plan": recording_build(recorded),
            **changes,
        }
        dialog = ImportDialog(item_layout.repo_root, item_layout, core=replace(ImportCore(), **fields))
        qtbot.addWidget(dialog)
        if show:
            dialog.show()
        dialog.open_path(package)
        return dialog

    return make


def wait_current(qtbot, dialog: ImportDialog, timeout: int = 30000) -> None:
    """Wait until the newest request has been built and accepted and nothing is pending."""
    qtbot.waitUntil(
        lambda: dialog._plan is not None
        and dialog._plan_gen == dialog._gen
        and dialog._building is None
        and dialog._queued is None
        and not dialog._dirty,
        timeout=timeout,
    )


def multi_zip(tmp_path: Path, *, symbols=("S1", "S2"), footprints=("F1", "F2", "F3"), models=("a.step", "b.step")) -> Path:
    from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib

    members = [("part.kicad_sym", symbol_lib(symbols, props=_DATASHEET))]
    members += [(f"{name}.kicad_mod", footprint(name)) for name in footprints]
    members += [(name, STEP_BYTES) for name in models]
    return make_zip(tmp_path / "multi.zip", members)


def assert_vendor_choices(options: InstallOptions, candidate: ImportCandidate) -> None:
    """IN-04: the UI passes vendor item names or nothing, never a blank choice."""
    assert options.symbol is None or options.symbol in {s.name for s in candidate.symbols}
    assert options.model is None or options.model in {m.filename for m in candidate.models}
    assert set(options.footprints) <= {f.name for f in candidate.footprints}
    assert "" not in (options.symbol, options.model, *options.footprints)


def test_picker_several_items_build_options(qtbot, make_item_dialog, recorded, tmp_path):
    dialog = make_item_dialog(multi_zip(tmp_path), show=True)
    wait_current(qtbot, dialog)
    first = recorded[-1]
    assert first.symbol == "S1"
    assert first.footprints == ("F1", "F2", "F3")
    assert first.model == "a.step"
    assert first.no_model is False

    # a combo for the symbols, a checklist for the footprints, a combo ending in "No model" for the models
    assert dialog._symbol_combo is not None and dialog._symbol_combo.count() == 2
    assert dialog._fp_list is not None and dialog._fp_list.count() == 3
    assert dialog._model_combo is not None and dialog._model_combo.count() == 3
    assert dialog._model_combo.itemText(2) == "No model"

    dialog._symbol_combo.setCurrentIndex(1)
    wait_current(qtbot, dialog)
    assert recorded[-1].symbol == "S2"

    dialog._model_combo.setCurrentIndex(2)
    wait_current(qtbot, dialog)
    assert recorded[-1].no_model is True and recorded[-1].model is None
    dialog._model_combo.setCurrentIndex(1)
    wait_current(qtbot, dialog)
    assert recorded[-1].model == "b.step" and recorded[-1].no_model is False

    # F1 is linked at first; unchecking it moves "linked" to F2
    assert dialog._fp_list.item(0).text().endswith("(linked)")
    dialog._fp_list.item(0).setCheckState(Qt.CheckState.Unchecked)
    wait_current(qtbot, dialog)
    assert recorded[-1].footprints == ("F2", "F3")
    assert dialog._fp_list.item(1).text().endswith("(linked)")
    assert not dialog._fp_list.item(0).text().endswith("(linked)")

    # Make linked on F3 puts it first
    dialog._fp_list.setCurrentRow(2)
    assert dialog._make_linked_btn.isEnabled()
    dialog._make_linked_btn.click()
    wait_current(qtbot, dialog)
    assert recorded[-1].footprints == ("F3", "F2")
    row = dialog._fp_list.item(2)
    assert row.text().endswith("(linked)")
    assert row.font().bold()
    assert not dialog._fp_list.item(1).font().bold()
    assert not dialog._make_linked_btn.isEnabled()  # the current row is the linked one now

    # re-checking F1 keeps the linked footprint and lists the others in list order
    dialog._fp_list.item(0).setCheckState(Qt.CheckState.Checked)
    wait_current(qtbot, dialog)
    assert recorded[-1].footprints == ("F3", "F1", "F2")


def test_picker_checklist_shows_six_rows_then_scrolls(qtbot, make_item_dialog, tmp_path):
    names = tuple(f"F{n}" for n in range(1, 9))
    dialog = make_item_dialog(multi_zip(tmp_path, footprints=names), show=True)
    wait_current(qtbot, dialog)
    fp_list = dialog._fp_list
    assert fp_list.count() == 8
    row = fp_list.sizeHintForRow(0)
    assert fp_list.maximumHeight() == row * 6 + 2 * fp_list.frameWidth()
    assert fp_list.verticalScrollBar().maximum() > 0
    assert fp_list.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_picker_single_items_are_labels(qtbot, make_item_dialog, recorded):
    dialog = make_item_dialog()
    wait_current(qtbot, dialog)
    candidate = dialog._candidate
    assert dialog._symbol_combo is None and dialog._fp_list is None and dialog._model_combo is None
    assert dialog._symbol_label.full_text() == candidate.symbols[0].name
    assert dialog._fp_label.full_text() == "DQK0006B"
    assert dialog._model_label.full_text() == candidate.models[0].filename
    first = recorded[-1]
    assert first.symbol == candidate.symbols[0].name
    assert first.footprints == ("DQK0006B",)
    assert first.model == candidate.models[0].filename
    assert dialog._extends_note.isHidden()


def test_picker_labels_elide_with_full_name_tooltip(qtbot, make_item_dialog, tmp_path):
    long_name = "L" * 60
    dialog = make_item_dialog(
        multi_zip(tmp_path, symbols=(long_name,), footprints=("FP",), models=("m.step",)), show=True
    )
    wait_current(qtbot, dialog)
    assert dialog._symbol_label.full_text() == long_name
    assert dialog._symbol_label.toolTip() == long_name


def test_picker_no_model_and_no_footprint_labels(qtbot, make_item_dialog, recorded, tmp_path):
    from zipfixtures import footprint, make_zip, symbol_lib

    no_model = make_zip(
        tmp_path / "no_model.zip",
        [("part.kicad_sym", symbol_lib(("S1",), props=_DATASHEET)), ("FP.kicad_mod", footprint("FP"))],
    )
    dialog = make_item_dialog(no_model)
    wait_current(qtbot, dialog)
    assert dialog._model_label.full_text() == "No 3D model in this package"
    assert AMBER.lower() in dialog._model_label.styleSheet().lower()
    assert recorded[-1].model is None and recorded[-1].no_model is False
    assert "intake.no_model" in [i.code for i in dialog._plan.issues]  # the package-level WARNING

    no_footprint = make_zip(
        tmp_path / "no_footprint.zip", [("part.kicad_sym", symbol_lib(("S1",), props=_DATASHEET))]
    )
    second = make_item_dialog(no_footprint)
    wait_current(qtbot, second)
    assert second._fp_label.full_text() == "No footprint in this package"
    assert AMBER.lower() in second._fp_label.styleSheet().lower()
    assert recorded[-1].footprints == ()


def test_picker_extends_note(qtbot, make_item_dialog, tmp_path):
    from installfixtures import extends_pair, vendor_footprint
    from zipfixtures import make_zip

    zip_path = make_zip(
        tmp_path / "extends.zip",
        [("pair.kicad_sym", extends_pair("PARENT_X", "CHILD_Y")), ("FP.kicad_mod", vendor_footprint("FP"))],
    )
    dialog = make_item_dialog(zip_path, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    names = [dialog._symbol_combo.itemText(i) for i in range(dialog._symbol_combo.count())]
    assert names == ["PARENT_X", "CHILD_Y"]
    assert dialog._extends_note.isHidden()  # a parent has no parent of its own

    dialog._symbol_combo.setCurrentIndex(1)
    wait_current(qtbot, dialog)
    assert dialog._plan.symbol_names == ("PARENT_X", "CHILD_Y")
    assert not dialog._extends_note.isHidden()
    assert dialog._extends_note.text() == "extends parent PARENT_X is included automatically"

    dialog._symbol_combo.setCurrentIndex(0)
    wait_current(qtbot, dialog)
    assert dialog._extends_note.isHidden()


def test_picker_never_passes_blank(qtbot, make_item_dialog, recorded, tmp_path):
    dialog = make_item_dialog(multi_zip(tmp_path))
    wait_current(qtbot, dialog)
    dialog._symbol_combo.setCurrentIndex(1)
    wait_current(qtbot, dialog)
    dialog._model_combo.setCurrentIndex(2)
    wait_current(qtbot, dialog)
    dialog._fp_list.item(0).setCheckState(Qt.CheckState.Unchecked)
    wait_current(qtbot, dialog)
    for row in (1, 2):
        dialog._fp_list.item(row).setCheckState(Qt.CheckState.Unchecked)
    wait_current(qtbot, dialog)
    assert recorded[-1].footprints == ()
    assert len(recorded) >= 5
    for options in recorded:
        assert_vendor_choices(options, dialog._candidate)

    single = make_item_dialog()
    wait_current(qtbot, single)
    assert_vendor_choices(recorded[-1], single._candidate)


def test_left_pane_disabled_until_first_plan(qtbot, make_item_dialog, gates):
    started = threading.Event()

    def gated_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = make_item_dialog(build_plan=gated_build)
    qtbot.waitUntil(started.is_set, timeout=30000)
    assert not dialog._left_scroll.isEnabled()
    assert dialog._preview_stack.currentWidget() is dialog._building_page
    assert not dialog._install_btn.isEnabled()
    gates[0].set()
    wait_current(qtbot, dialog)
    assert dialog._left_scroll.isEnabled()
    assert dialog._preview_stack.currentWidget() is dialog._preview


# -- Footprint name and the five fields (plan 05-07 task 2) ----------------------------------------

import dataclasses  # noqa: E402

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QToolButton, QWidget  # noqa: E402

FIELD_KEYS = ("value", "datasheet", "description", "manufacturer", "mpn")
UL_DEFAULTS = {
    "value": "CSD85301Q2",
    "datasheet": "https://www.ti.com/lit/gpn/csd85301q2",
    "description": "",
    "manufacturer": "TI",
    "mpn": "CSD85301Q2",
}


def type_text(qtbot, edit, text: str) -> None:
    """Type like a user: select everything, then key presses, so textEdited fires (not setText)."""
    edit.setFocus()
    edit.selectAll()
    if text == "":
        qtbot.keyClick(edit, Qt.Key.Key_Backspace)
    else:
        qtbot.keyClicks(edit, text)


def ul_dialog(make_item_dialog, qtbot, **changes) -> ImportDialog:
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, **changes)
    wait_current(qtbot, dialog)
    return dialog


def test_footprint_name_default_and_vendor_hint(qtbot, make_item_dialog, tmp_path):
    dialog = ul_dialog(make_item_dialog, qtbot)
    assert dialog._fp_name_edit.text() == "DQK0006B"
    assert dialog._fp_name_hint.isHidden()  # the vendor name is already clean
    assert not dialog._fp_name_restore.isEnabled()
    assert dialog._fp_name_edit.accessibleName() == "Footprint name"

    from zipfixtures import footprint, make_zip, symbol_lib

    odd = make_zip(
        tmp_path / "odd.zip",
        [("part.kicad_sym", symbol_lib(("S1",), props=_DATASHEET)), ("FP_1.kicad_mod", footprint("FP/1"))],
    )
    second = make_item_dialog(odd, show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, second)
    assert second._fp_name_edit.text() == "FP_1"
    assert not second._fp_name_hint.isHidden()
    assert second._fp_name_hint.text() == "Vendor name: FP/1"
    assert MUTED.lower() in second._fp_name_hint.styleSheet().lower()


def test_footprint_name_edit_and_restore(qtbot, make_item_dialog, recorded):
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._fp_name_edit, "MYFP")
    assert dialog._dirty and not dialog._install_btn.isEnabled()
    assert dialog._strip.text() == "Updating preview..."
    wait_current(qtbot, dialog)
    assert dict(recorded[-1].footprint_names) == {"DQK0006B": "MYFP"}
    assert dialog._fp_name_restore.isEnabled()
    dialog._fp_name_restore.click()
    assert dialog._fp_name_edit.text() == "DQK0006B"
    assert not dialog._fp_name_restore.isEnabled()
    wait_current(qtbot, dialog)
    assert dict(recorded[-1].footprint_names) == {}


def test_footprint_field_follows_library_and_name(qtbot, make_item_dialog, recorded, gates):
    state = {"gate": None}

    def maybe_gated(candidate, options, layout, tools=ToolContext(), **kwargs):
        gate = state["gate"]
        if gate is not None:
            assert gate.wait(30)
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = make_item_dialog(UL_ZIP, show=True, build_plan=recording_build(recorded, maybe_gated))
    wait_current(qtbot, dialog)
    # the suggested library still holds a placeholder, so the plan is refused and nothing is linked
    assert dialog._fp_field.text() == "(none)"
    assert dialog._fp_field.isReadOnly()

    set_library(dialog, LIB)
    wait_current(qtbot, dialog)
    assert dialog._fp_field.text() == f"{LIB}:DQK0006B"
    assert MUTED.lower() not in dialog._fp_field.styleSheet().lower()
    assert dialog._install_btn.isEnabled()

    state["gate"] = gate = threading.Event()
    gates.append(gate)
    type_text(qtbot, dialog._fp_name_edit, "DQK/0006B")
    assert not dialog._install_btn.isEnabled()
    qtbot.waitUntil(lambda: dialog._building is not None, timeout=30000)
    # the rebuild is running: the field keeps the previous plan's value and Install stays off
    assert dialog._fp_field.text() == f"{LIB}:DQK0006B"
    assert not dialog._install_btn.isEnabled()
    gate.set()
    wait_current(qtbot, dialog)
    assert dialog._plan.footprint_names == ("DQK_0006B",)
    assert dialog._fp_field.text() == f"{LIB}:DQK_0006B"
    assert dialog._fp_name_edit.text() == "DQK/0006B"  # the box keeps what was typed

    set_library(dialog, "IC_IMU_TDK")
    wait_current(qtbot, dialog)
    assert dialog._fp_field.text() == "IC_IMU_TDK:DQK_0006B"


def test_footprint_field_none_when_unlinked(qtbot, make_item_dialog):
    def unlinked(candidate, options, layout, tools=ToolContext(), **kwargs):
        plan = real_build_plan(candidate, options, layout, tools, **kwargs)
        return dataclasses.replace(plan, linked_footprint=None)

    dialog = ul_dialog(make_item_dialog, qtbot, build_plan=unlinked)
    assert dialog._plan.linked_footprint is None
    assert dialog._fp_field.text() == "(none)"
    assert MUTED.lower() in dialog._fp_field.styleSheet().lower()


def test_empty_footprint_name_blocks(qtbot, make_item_dialog, recorded):
    dialog = ul_dialog(make_item_dialog, qtbot)
    assert dialog._install_btn.isEnabled()
    type_text(qtbot, dialog._fp_name_edit, "")
    wait_current(qtbot, dialog)
    assert dict(recorded[-1].footprint_names) == {"DQK0006B": ""}
    assert dialog._plan.blocked
    assert "install.invalid_name" in [i.code for i in dialog._plan.issues]
    assert not dialog._install_btn.isEnabled()
    assert dialog._fp_field.text() == "(none)"


def test_fields_start_with_what_the_plan_writes(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    assert {name: dialog._field_edits[name].text() for name in FIELD_KEYS} == UL_DEFAULTS
    assert dialog._symbol_name_label.full_text() == "CSD85301Q2"
    for name in FIELD_KEYS:
        assert not dialog._field_restore[name].isEnabled()
    assert dialog._defaults.manufacturer == "TI"


def test_fields_symbol_label_shows_rename(qtbot, make_item_dialog, tmp_path):
    from zipfixtures import footprint, make_zip, symbol_lib

    zip_path = make_zip(
        tmp_path / "renamed.zip",
        [("part.kicad_sym", symbol_lib(("PART/1",), props=_DATASHEET)), ("FP.kicad_mod", footprint("FP"))],
    )
    dialog = make_item_dialog(zip_path, show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    assert dialog._symbol_name_label.full_text() == "PART/1 → PART_1"
    assert dialog._field_edits["value"].text() == "PART_1"


def test_fields_clear_and_restore(qtbot, make_item_dialog, recorded):
    dialog = ul_dialog(make_item_dialog, qtbot)
    datasheet = dialog._field_edits["datasheet"]
    assert datasheet.placeholderText() == "Empty - the field will be written blank"
    assert not dialog._field_restore["datasheet"].isEnabled()

    type_text(qtbot, datasheet, "")
    assert dialog._dirty and not dialog._install_btn.isEnabled()
    wait_current(qtbot, dialog)
    assert recorded[-1].datasheet == "" and "datasheet" in recorded[-1].cleared
    assert dialog._install_btn.isEnabled()  # a blank Datasheet installs
    assert dialog._field_restore["datasheet"].isEnabled()
    assert dialog._field_restore["datasheet"].toolTip() == f"Restore default: {UL_DEFAULTS['datasheet']}"

    dialog._field_restore["datasheet"].click()
    assert datasheet.text() == UL_DEFAULTS["datasheet"]
    assert not dialog._field_restore["datasheet"].isEnabled()
    wait_current(qtbot, dialog)
    assert recorded[-1].datasheet is None and recorded[-1].cleared == frozenset()

    # an emptied field whose default is already empty passes nothing
    type_text(qtbot, dialog._field_edits["description"], "x")
    wait_current(qtbot, dialog)
    assert recorded[-1].description == "x"
    type_text(qtbot, dialog._field_edits["description"], "")
    wait_current(qtbot, dialog)
    assert recorded[-1].description is None and "description" not in recorded[-1].cleared

    # Value cannot be emptied: the plan carries install.empty_required and Install stays off
    type_text(qtbot, dialog._field_edits["value"], "")
    wait_current(qtbot, dialog)
    assert dialog._plan.blocked
    assert "install.empty_required" in [i.code for i in dialog._plan.issues]
    assert not dialog._install_btn.isEnabled()
    dialog._field_restore["value"].click()
    wait_current(qtbot, dialog)
    assert dialog._install_btn.isEnabled()

    for name in ("datasheet", "description", "manufacturer"):
        assert dialog._field_edits[name].placeholderText() == "Empty - the field will be written blank"
    for name in ("value", "mpn"):
        assert dialog._field_edits[name].placeholderText() == ""


def test_fields_reset_on_symbol_change_kept_on_library_change(qtbot, make_item_dialog, tmp_path):
    dialog = make_item_dialog(multi_zip(tmp_path), show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    assert dialog._field_edits["value"].text() == "S1"
    type_text(qtbot, dialog._field_edits["manufacturer"], "Acme")
    wait_current(qtbot, dialog)
    assert dialog._edited == {"manufacturer"}

    set_library(dialog, "IC_IMU_TDK")
    wait_current(qtbot, dialog)
    assert dialog._field_edits["manufacturer"].text() == "Acme"  # a library change keeps every edit
    assert dialog._edited == {"manufacturer"}

    dialog._symbol_combo.setCurrentIndex(1)
    wait_current(qtbot, dialog)
    assert dialog._edited == set()
    assert dialog._field_edits["manufacturer"].text() != "Acme"
    assert dialog._field_edits["manufacturer"].text() == dialog._defaults.manufacturer
    assert dialog._field_edits["value"].text() == "S2"

    # the footprint name resets when the linked footprint changes
    type_text(qtbot, dialog._fp_name_edit, "MYFP")
    wait_current(qtbot, dialog)
    assert dialog._fp_name_edit.text() == "MYFP"
    dialog._fp_list.item(0).setCheckState(Qt.CheckState.Unchecked)  # F1 was linked, F2 is now
    wait_current(qtbot, dialog)
    assert dialog._linked_fp == "F2"
    assert dialog._fp_name_edit.text() == "F2"
    assert dialog._fp_name_edited is False
    assert dialog._fp_field.text().endswith(":F2")


def test_edit_state_cleared_by_change(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._field_edits["datasheet"], "x")
    assert dialog._debounce.isActive() and dialog._dirty
    dialog._change_btn.click()
    assert not dialog._debounce.isActive()
    assert not dialog._dirty
    assert dialog._edited == set() and dialog._fp_name_edited is False
    assert dialog._linked_fp is None and dialog._plan is None
    assert dialog._fp_field.text() == ""


def test_debounce_single_rebuild(qtbot, make_item_dialog, recorded, tmp_path):
    dialog = make_item_dialog(multi_zip(tmp_path), show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    before = len(recorded)
    datasheet = dialog._field_edits["datasheet"]
    datasheet.setFocus()
    datasheet.selectAll()
    qtbot.keyClicks(datasheet, "abc")  # three textEdited events within a few milliseconds
    assert dialog._dirty and dialog._debounce.isActive()
    assert dialog._debounce.interval() == 300
    assert len(recorded) == before  # nothing built yet
    assert not dialog._install_btn.isEnabled()
    qtbot.waitUntil(lambda: len(recorded) == before + 1, timeout=30000)
    assert recorded[-1].datasheet == "abc"
    wait_current(qtbot, dialog)
    qtbot.wait(450)
    assert len(recorded) == before + 1  # one rebuild for three keystrokes

    # a combo change during a pending debounce stops the timer and rebuilds at once, with the typed text
    type_text(qtbot, dialog._field_edits["mpn"], "ZZ9")
    assert dialog._debounce.isActive()
    dialog._model_combo.setCurrentIndex(1)
    assert not dialog._debounce.isActive() and not dialog._dirty
    qtbot.waitUntil(lambda: len(recorded) == before + 2, timeout=30000)
    assert recorded[-1].mpn == "ZZ9" and recorded[-1].model == "b.step"
    wait_current(qtbot, dialog)
    qtbot.wait(450)
    assert len(recorded) == before + 2


def test_restore_buttons_accessible(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    assert isinstance(dialog._fp_name_restore, QToolButton)
    assert dialog._fp_name_restore.accessibleName() == "Restore default footprint name"
    assert (dialog._fp_name_restore.width(), dialog._fp_name_restore.height()) == (24, 24)
    labels = {"value": "Value", "datasheet": "Datasheet", "description": "Description", "manufacturer": "Manufacturer", "mpn": "MPN"}
    for name, label in labels.items():
        button = dialog._field_restore[name]
        assert isinstance(button, QToolButton)
        assert (button.width(), button.height()) == (24, 24)
        assert button.accessibleName() == f"Restore default {label}"
        assert dialog._field_edits[name].accessibleName() == label
    assert dialog._field_edits["mpn"].toolTip() == "MPN names the 3D model file"
    assert dialog._fp_field.accessibleName() == "Footprint"


def test_fields_long_text_geometry(qtbot, make_item_dialog, tmp_path):
    """Backstop (UI E5/E7 long-text): a 60-character name and a 120-character Description fit the left pane."""
    long_name = "L" * 60
    package = multi_zip(
        tmp_path,
        symbols=(long_name, "S2"),
        footprints=(long_name + "a", "F2"),
        models=(long_name + ".step", "b.step"),
    )
    dialog = make_item_dialog(package, show=True, suggest_library=_good_suggestion)
    dialog.resize(900, 600)
    wait_current(qtbot, dialog)
    type_text(qtbot, dialog._field_edits["description"], "D" * 120)
    qtbot.wait(50)
    scroll = dialog._left_scroll
    viewport = scroll.viewport()
    left = scroll.widget()
    assert not scroll.horizontalScrollBar().isVisible()
    assert left.width() <= viewport.width()
    for widget in left.findChildren(QWidget):
        if widget.isVisible():
            right = widget.mapTo(left, QPoint(widget.width(), 0)).x()
            assert right <= viewport.width(), (widget, right, viewport.width())
    # a line edit never overlaps its restore button
    for name, edit in dialog._field_edits.items():
        assert edit.mapTo(left, QPoint(edit.width(), 0)).x() <= dialog._field_restore[name].mapTo(left, QPoint(0, 0)).x()
    assert dialog._field_edits["description"].text() == "D" * 120


def test_footprint_field_and_filters_follow_checked_order(qtbot, make_item_dialog, tmp_path):
    """Edge PREV-03/ordering: the field names the linked footprint, ki_fp_filters lists the checked ones in order."""
    from kicad_lib_manager.kicad_files import find_property, find_symbol, parse_bytes

    dialog = make_item_dialog(multi_zip(tmp_path), show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)

    def filters() -> str:
        op = next(op for op in dialog._plan.ops if op.kind == "symbol_lib")
        symbol = find_symbol(parse_bytes(op.data, "lib").root, dialog._plan.symbol_name)
        return find_property(symbol.node, "ki_fp_filters").value

    assert dialog._fp_field.text() == f"{LIB}:F1"
    assert filters() == "F1 F2 F3"
    dialog._fp_list.setCurrentRow(2)
    dialog._make_linked_btn.click()
    wait_current(qtbot, dialog)
    assert dialog._fp_field.text() == f"{LIB}:F3"
    assert filters() == "F3 F1 F2"
    dialog._fp_list.item(1).setCheckState(Qt.CheckState.Unchecked)  # F2 out
    wait_current(qtbot, dialog)
    assert dialog._fp_field.text() == f"{LIB}:F3"
    assert filters() == "F3 F1"


def test_emptied_mpn_blocks_install(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._field_edits["mpn"], "")
    wait_current(qtbot, dialog)
    assert "install.empty_required" in [i.code for i in dialog._plan.issues]
    assert not dialog._install_btn.isEnabled()
    dialog._field_restore["mpn"].click()
    wait_current(qtbot, dialog)
    assert dialog._install_btn.isEnabled()


# -- plan 05-09 Task 1: Target library combo, badge, token line and the Updating indicators ---------

from PySide6.QtWidgets import QProgressBar  # noqa: E402

from kicad_lib_manager.importer.candidate import ExistingLibrary  # noqa: E402
from kicad_lib_manager.importer.suggest import RankedLibrary  # noqa: E402
from kicad_lib_manager.widgets.theme import SUCCESS  # noqa: E402

NEW_BADGE = "new - creates .kicad_sym + .pretty"
TOKEN_HINT = "Amber parts are guesses or placeholders. Pick an existing library or type a real name."


def _with_alternatives(meta, existing=()):
    base = real_suggest_library(meta, existing)
    return replace(
        base,
        alternatives=(
            RankedLibrary("IC_IMU_TDK", 5, (), True, False),
            RankedLibrary("Connector_USB_GCT", 3, (), True, True),
        ),
    )


def combo_items(dialog: ImportDialog) -> list[str]:
    """The library combo's entries, a separator shown as '---'."""
    combo = dialog._library_combo
    return [
        "---" if combo.itemData(i, Qt.ItemDataRole.AccessibleDescriptionRole) == "separator" else combo.itemText(i)
        for i in range(combo.count())
    ]


def test_library_combo_lists_alternatives_then_existing(qtbot, make_item_dialog):
    reads = {"n": 0}
    existing = [ExistingLibrary("Zed_Part_X", True, True), ExistingLibrary("Alpha_Part_X", True, False)]

    def read_libraries(layout):
        reads["n"] += 1
        return list(existing)

    dialog = make_item_dialog(
        UL_ZIP, show=True, suggest_library=_with_alternatives, list_existing_libraries=read_libraries
    )
    wait_current(qtbot, dialog)
    # pre-filled with the suggestion; the dropdown holds the alternatives in rank order, a separator, then every library
    assert dialog._library_combo.currentText() == dialog._suggestion.name
    assert combo_items(dialog) == ["IC_IMU_TDK", "Connector_USB_GCT", "---", "Zed_Part_X", "Alpha_Part_X"]
    assert reads["n"] == 1

    # the list is read again each time a package is opened
    dialog._on_change()
    dialog.open_path(UL_ZIP)
    wait_current(qtbot, dialog)
    assert reads["n"] == 2


def test_library_typing_debounced_pick_immediate(qtbot, make_item_dialog, recorded):
    dialog = ul_dialog(make_item_dialog, qtbot)
    edit = dialog._library_combo.lineEdit()
    before = len(recorded)

    type_text(qtbot, edit, "IC_Typed_TI")  # several textEdited events within a few milliseconds
    assert dialog._dirty and dialog._debounce.isActive()
    assert len(recorded) == before
    assert not dialog._install_btn.isEnabled()
    qtbot.waitUntil(lambda: len(recorded) == before + 1, timeout=30000)
    assert recorded[-1].library == "IC_Typed_TI"
    wait_current(qtbot, dialog)
    qtbot.wait(450)
    assert len(recorded) == before + 1  # one rebuild for the whole word

    # picking from the list builds at once and cancels a pending timer
    type_text(qtbot, edit, "X")
    assert dialog._debounce.isActive()
    dialog._library_combo.setEditText("IC_Battery_Charger_TI")
    dialog._library_combo.textActivated.emit("IC_Battery_Charger_TI")
    assert not dialog._debounce.isActive() and not dialog._dirty
    qtbot.waitUntil(lambda: len(recorded) == before + 2, timeout=30000)
    assert recorded[-1].library == "IC_Battery_Charger_TI"
    wait_current(qtbot, dialog)
    qtbot.wait(450)
    assert len(recorded) == before + 2


def test_library_badge_and_token_line(qtbot, make_item_dialog):
    dialog = make_item_dialog(UL_ZIP, show=True)  # the real suggestion: a placeholder name
    wait_current(qtbot, dialog)
    name = dialog._suggestion.name
    assert "SubCategory" in name
    assert dialog._library_combo.currentText() == name
    # the token line shows the name with the placeholder in bold amber, and the hint explains why
    html_text = dialog._token_line.text()
    assert f'<span style="color:{AMBER};font-weight:bold">SubCategory</span>' in html_text
    assert not dialog._token_hint.isHidden()
    assert dialog._token_hint.text() == TOKEN_HINT
    assert dialog._token_hint.textFormat() == Qt.TextFormat.PlainText
    assert dialog._library_badge.text() == NEW_BADGE

    edit = dialog._library_combo.lineEdit()
    type_text(qtbot, edit, "IC_Battery_Charger_TI")
    assert dialog._library_badge.text() == "existing"  # follows the keystrokes at once, before any rebuild
    assert SUCCESS in dialog._library_badge.styleSheet()
    assert "SubCategory" not in dialog._token_line.text()
    assert dialog._token_hint.isHidden()
    type_text(qtbot, edit, "IC_New_TI")
    assert dialog._library_badge.text() == NEW_BADGE
    type_text(qtbot, edit, "ic_battery_charger_ti")  # a case twin is not the existing library
    assert dialog._library_badge.text() == NEW_BADGE
    type_text(qtbot, edit, "")
    assert dialog._library_badge.isHidden()
    assert dialog._token_hint.isHidden()


def test_library_token_line_escapes_markup(qtbot, make_item_dialog):
    dialog = make_item_dialog(UL_ZIP, show=True)
    wait_current(qtbot, dialog)
    type_text(qtbot, dialog._library_combo.lineEdit(), "<b>x</b>_&")
    text = dialog._token_line.text()
    assert "&lt;b&gt;x&lt;/b&gt;" in text and "&amp;" in text
    assert "<b>" not in text


def test_updating_label_and_busy_strip(qtbot, make_item_dialog, gates):
    """Edge E9/loading: Updating... at once, the busy strip only after 150 ms, both gone with the result."""
    state = {"n": 0}

    def gated_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        state["n"] += 1
        if state["n"] >= 2:
            gate = threading.Event()
            gates.append(gate)
            assert gate.wait(30)
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = ul_dialog(make_item_dialog, qtbot, build_plan=gated_build)
    assert dialog._updating_label.isHidden() and dialog._busy_bar.isHidden()
    assert isinstance(dialog._busy_bar, QProgressBar) and dialog._busy_bar.maximumHeight() == 4
    first_tree = files_rows(dialog)

    dialog._request_rebuild()
    qtbot.waitUntil(lambda: len(gates) == 1, timeout=30000)
    assert dialog._updating_label.isVisible()
    assert dialog._updating_label.text() == "Updating..."
    assert AMBER.lower() in dialog._updating_label.styleSheet().lower()
    assert dialog._busy_bar.isHidden()  # not before 150 ms
    assert files_rows(dialog) == first_tree  # the previous tree stays
    qtbot.wait(250)
    assert dialog._busy_bar.isVisible()
    gates[0].set()
    wait_current(qtbot, dialog)
    assert dialog._updating_label.isHidden() and dialog._busy_bar.isHidden()

    # a quick text edit shows the label from the first keystroke
    type_text(qtbot, dialog._fp_name_edit, "Q")
    assert dialog._updating_label.isVisible()
    qtbot.waitUntil(lambda: len(gates) == 2, timeout=30000)
    gates[1].set()
    wait_current(qtbot, dialog)
    assert dialog._updating_label.isHidden() and dialog._busy_bar.isHidden()


def test_library_long_name_geometry(qtbot, make_item_dialog):
    """Backstop (UI E6/long-text): a 60-character library name keeps the badge and token line inside the pane."""
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion)
    dialog.resize(900, 600)
    wait_current(qtbot, dialog)
    long_name = ("IC_" + "Averylongtokenabc_" * 3 + "Zlast_TI")[:60]
    assert len(long_name) == 60 and not long_name.endswith("_")
    type_text(qtbot, dialog._library_combo.lineEdit(), long_name)
    qtbot.wait(50)
    scroll = dialog._left_scroll
    viewport = scroll.viewport()
    left = scroll.widget()
    assert not scroll.horizontalScrollBar().isVisible()
    assert left.width() <= viewport.width()
    for widget in (dialog._library_combo, dialog._library_badge, dialog._token_line, dialog._token_hint):
        if widget.isVisible():
            right = widget.mapTo(left, QPoint(widget.width(), 0)).x()
            assert right <= viewport.width(), (widget, right, viewport.width())
    assert dialog._library_badge.isVisible()
    assert dialog._token_line.toolTip() == long_name
    # the token line wraps instead of widening the pane
    assert dialog._token_line.height() >= dialog._token_line.fontMetrics().height()


# -- plan 05-09 Task 2: the clickable blocking-reason strip, amber frames, ready and no-op lines ----

import html as html_module  # noqa: E402
import re  # noqa: E402

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from kicad_lib_manager.widgets.theme import AMBER_TINT, LINK, SP_SM  # noqa: E402

PLACEHOLDER_REASON = "Library name still contains a placeholder (SubCategory). Pick an existing library or type a real name."


def strip_links(dialog: ImportDialog) -> dict[str, str]:
    """reason text (unescaped) -> href, read from the strip's rich text."""
    found = re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>', dialog._strip.text())
    return {html_module.unescape(text): href for href, text in found}


def frame_blocked(dialog: ImportDialog, key: str) -> bool:
    return bool(dialog._field_frames[key].property("blocked"))


def with_issues(*issues):
    """A build_plan fake that adds ERROR Issues to the real plan."""

    def build(candidate, options, layout, tools=ToolContext(), **kwargs):
        plan = real_build_plan(candidate, options, layout, tools, **kwargs)
        return replace(plan, issues=(*plan.issues, *issues))

    return build


def test_placeholder_blocks_install(qtbot, make_item_dialog):
    """Phase 3 D-04: the UL sample opens blocked on its placeholder library name until a real one is picked."""
    dialog = make_item_dialog(UL_ZIP, show=True)
    wait_current(qtbot, dialog)
    assert "SubCategory" in dialog._library_combo.currentText()
    assert not dialog._install_btn.isEnabled()
    assert PLACEHOLDER_REASON in strip_links(dialog)
    assert dialog._strip.text().startswith("⚠ Install is blocked: ")
    assert frame_blocked(dialog, "library")
    # the planner's own refusal is not repeated as a second reason
    assert not any(text.startswith("Error:") for text in strip_links(dialog))

    set_library(dialog, LIB)
    wait_current(qtbot, dialog)
    assert dialog._strip.text() == "✓ Ready to install: 2 new, 1 modified, 0 unchanged files"
    assert dialog._install_btn.isEnabled()
    assert not frame_blocked(dialog, "library")


def test_empty_library_name_blocks(qtbot, make_item_dialog):
    """UI E6/empty: an empty name shows the amber frame and 'Library name is empty'."""
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._library_combo.lineEdit(), "")
    assert frame_blocked(dialog, "library")  # from the first keystroke, while the rebuild waits
    wait_current(qtbot, dialog)
    assert "Library name is empty" in strip_links(dialog)
    assert not any(text.startswith("Error:") for text in strip_links(dialog))
    assert frame_blocked(dialog, "library")
    assert not dialog._install_btn.isEnabled()


def test_case_twin_and_invalid_name_show_the_plan_issue(qtbot, make_item_dialog):
    """UI E6/error: a case twin and a name sanitize_name changes show the plan's Issue and the amber frame."""
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._library_combo.lineEdit(), "ic_battery_charger_ti")
    wait_current(qtbot, dialog)
    codes = [i.code for i in dialog._plan.issues]
    assert "install.library_case_clash" in codes
    errors = [text for text in strip_links(dialog) if text.startswith("Error:")]
    assert len(errors) == 1 and "letter case" in errors[0]
    assert frame_blocked(dialog, "library")
    assert not dialog._install_btn.isEnabled()
    assert any("letter case" in dialog._preview.topLevelItem(i).child(j).text(0)
               for i in range(dialog._preview.topLevelItemCount())
               for j in range(dialog._preview.topLevelItem(i).childCount()))

    type_text(qtbot, dialog._library_combo.lineEdit(), "IC New TI")
    wait_current(qtbot, dialog)
    assert "install.invalid_library" in [i.code for i in dialog._plan.issues]
    assert any(text.startswith("Error:") and "not a valid library name" in text for text in strip_links(dialog))
    assert frame_blocked(dialog, "library")


def test_strip_link_focuses_field(qtbot, make_item_dialog):
    """UI E7/error: the reason is a link; activating it puts the cursor in the field."""
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._field_edits["value"], "")
    wait_current(qtbot, dialog)
    assert frame_blocked(dialog, "value") and not frame_blocked(dialog, "mpn")
    links = strip_links(dialog)
    assert "Value is empty" in links and "MPN is empty - it names the 3D model file" not in links
    dialog._library_combo.setFocus()
    dialog._strip.linkActivated.emit(links["Value is empty"])
    assert dialog.focusWidget() is dialog._field_edits["value"]

    type_text(qtbot, dialog._field_edits["mpn"], "")
    wait_current(qtbot, dialog)
    assert frame_blocked(dialog, "value") and frame_blocked(dialog, "mpn")
    links = strip_links(dialog)
    dialog._strip.linkActivated.emit(links["MPN is empty - it names the 3D model file"])
    assert dialog.focusWidget() is dialog._field_edits["mpn"]
    # a restored field unblocks its frame
    dialog._field_restore["value"].click()
    dialog._field_restore["mpn"].click()
    wait_current(qtbot, dialog)
    assert not frame_blocked(dialog, "value") and not frame_blocked(dialog, "mpn")
    assert dialog._install_btn.isEnabled()


def test_strip_link_focuses_library_and_footprint_list(qtbot, make_item_dialog, tmp_path):
    dialog = make_item_dialog(multi_zip(tmp_path), show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    for row in range(dialog._fp_list.count()):
        dialog._fp_list.item(row).setCheckState(Qt.CheckState.Unchecked)
    wait_current(qtbot, dialog)
    # UI E5/error: the last footprint unchecked adds the reason and the amber frame, once
    links = strip_links(dialog)
    assert "Select at least one footprint" in links
    assert not any(text.startswith("Error:") for text in links)
    assert frame_blocked(dialog, "footprints")
    assert not dialog._install_btn.isEnabled()
    dialog._library_combo.setFocus()
    dialog._strip.linkActivated.emit(links["Select at least one footprint"])
    assert dialog.focusWidget() is dialog._fp_list
    dialog._fp_list.item(0).setCheckState(Qt.CheckState.Checked)
    wait_current(qtbot, dialog)
    assert not frame_blocked(dialog, "footprints")
    assert dialog._install_btn.isEnabled()

    set_library(dialog, "IC_SubCategory_TI")
    wait_current(qtbot, dialog)
    dialog._fp_name_edit.setFocus()
    dialog._strip.linkActivated.emit(strip_links(dialog)[PLACEHOLDER_REASON])
    assert dialog.focusWidget() is dialog._library_combo  # its line edit takes the cursor through the focus proxy


def test_strip_link_ignores_unknown_href(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    dialog._library_combo.setFocus()
    for href in ("reason:99", "reason:x", "http://evil.example/", "reason:-1", ""):
        dialog._strip.linkActivated.emit(href)  # nothing is opened, nothing breaks
    assert dialog.focusWidget() is dialog._library_combo


def test_strip_escapes_markup(qtbot, make_item_dialog):
    """T-05-27: every interpolated string is escaped and only internal reason: links exist."""
    evil = Issue(Severity.ERROR, "install.test_markup", "<b>x</b><a href='http://evil.example/'>y</a>")
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, build_plan=with_issues(evil))
    wait_current(qtbot, dialog)
    text = dialog._strip.text()
    assert "&lt;b&gt;x&lt;/b&gt;" in text
    assert "<b>" not in text and "<a href='http" not in text and 'href="http' not in text
    hrefs = re.findall(r'href="([^"]*)"', text)
    assert hrefs and all(h.startswith("reason:") for h in hrefs)
    assert dialog._strip.openExternalLinks() is False
    assert LINK in text  # the links are LINK-coloured


def test_strip_look(qtbot, make_item_dialog):
    """The blocked strip: AMBER_TINT, 8 px padding, rich text, a leading warning and ' · ' between reasons."""
    one = Issue(Severity.ERROR, "install.test_a", "First problem")
    two = Issue(Severity.ERROR, "install.test_b", "Second problem")
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, build_plan=with_issues(one, two))
    wait_current(qtbot, dialog)
    strip = dialog._strip
    assert strip.textFormat() == Qt.TextFormat.RichText and strip.wordWrap()
    assert AMBER_TINT.lower() in strip.styleSheet().lower()
    margins = strip.contentsMargins()
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (SP_SM, SP_SM, SP_SM, SP_SM)
    assert strip.text().startswith("⚠ Install is blocked: ")
    assert list(strip_links(dialog)) == ["Error: First problem", "Error: Second problem"]
    assert " · " in strip.text()
    assert not dialog._install_btn.isEnabled()


def test_strip_caps_three_lines_with_tooltip(qtbot, make_item_dialog):
    """UI E11/overflow and long-text: at most 3 lines, the tooltip lists every reason."""
    issues = [Issue(Severity.ERROR, f"install.test_{n}", f"Reason number {n} " + "with a rather long explanation " * 4) for n in range(10)]
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, build_plan=with_issues(*issues))
    dialog.resize(900, 600)
    wait_current(qtbot, dialog)
    strip = dialog._strip
    limit = 3 * strip.fontMetrics().lineSpacing() + 2 * SP_SM
    assert strip.maximumHeight() <= limit + 2
    assert strip.height() <= strip.maximumHeight()
    tooltip = strip.toolTip()
    for n in range(10):
        assert f"Reason number {n} " in tooltip


def test_ready_line_and_install_enabled(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    counts = file_counts(dialog._plan, dialog._candidate, dialog._plan_options)
    assert dialog._strip.text() == (
        f"✓ Ready to install: {counts.new} new, {counts.modified} modified, {counts.unchanged} unchanged files"
    )
    assert SUCCESS in dialog._strip.styleSheet()
    assert dialog._strip.textFormat() == Qt.TextFormat.PlainText
    assert dialog._install_btn.isEnabled()
    assert all(not frame.property("blocked") for frame in dialog._field_frames.values())


def test_noop_strip(qtbot, make_item_dialog):
    """A plan with nothing to write reads 'Nothing to install' in MUTED and keeps Install off."""

    def noop_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        return replace(real_build_plan(candidate, options, layout, tools, **kwargs), ops=())

    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, build_plan=noop_build)
    wait_current(qtbot, dialog)
    assert dialog._plan.is_noop
    assert dialog._strip.text() == f"Nothing to install: this part is already in {LIB}."
    assert MUTED.lower() in dialog._strip.styleSheet().lower()
    assert not dialog._install_btn.isEnabled()


def test_updating_reason_replaces_the_others(qtbot, make_item_dialog, gates):
    """UI E11/loading: while a rebuild is pending the single reason 'Updating preview...' stands alone."""
    state = {"n": 0}

    def gated_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        state["n"] += 1
        if state["n"] >= 3:
            gate = threading.Event()
            gates.append(gate)
            assert gate.wait(30)
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = ul_dialog(make_item_dialog, qtbot, build_plan=gated_build)
    type_text(qtbot, dialog._field_edits["value"], "")
    wait_current(qtbot, dialog)
    assert "Value is empty" in strip_links(dialog)
    type_text(qtbot, dialog._field_edits["mpn"], "")  # a rebuild starts and is held
    qtbot.waitUntil(lambda: len(gates) == 1, timeout=30000)
    assert dialog._strip.text() == "Updating preview..."
    assert not dialog._install_btn.isEnabled()
    assert strip_links(dialog) == {}
    assert frame_blocked(dialog, "value") and frame_blocked(dialog, "mpn")  # the frames follow the live text
    gates[0].set()
    wait_current(qtbot, dialog)
    assert "MPN is empty - it names the 3D model file" in strip_links(dialog)


def test_build_failure_reason_and_retry(qtbot, make_item_dialog):
    """UI E9/error: the previous tree stays, the strip says why, the next edit retries."""
    count = {"n": 0}

    def flaky_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        count["n"] += 1
        if count["n"] == 2:
            raise RuntimeError("boom")
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    dialog = ul_dialog(make_item_dialog, qtbot, build_plan=flaky_build)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    first_tree = files_rows(dialog)
    dialog._request_rebuild()
    qtbot.waitUntil(lambda: count["n"] == 2 and dialog._building is None, timeout=30000)
    assert files_rows(dialog) == first_tree
    assert "Error: Preview could not be built - see the log" in strip_links(dialog)
    assert not dialog._install_btn.isEnabled()
    assert dialog._updating_label.isHidden()
    assert any(i.text.startswith("Import step failed: RuntimeError: boom") for i in logged)
    dialog._request_rebuild()
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    assert dialog._strip.text().startswith("✓ Ready to install")


def test_field_frames_reserve_their_border(qtbot, make_item_dialog):
    """The frame always holds its 2 px border, so turning the amber highlight on does not move anything."""
    dialog = ul_dialog(make_item_dialog, qtbot)
    frame = dialog._field_frames["value"]
    assert frame.objectName() == "fieldFrame"
    assert "2px solid transparent" in frame.styleSheet()
    assert dialog._field_edits["value"].parentWidget() is frame
    assert dialog._library_combo.parentWidget() is dialog._field_frames["library"]
    assert dialog._fp_name_edit.parentWidget() is dialog._field_frames["footprint_name"]
    before = (frame.geometry(), dialog._field_edits["value"].geometry())
    type_text(qtbot, dialog._field_edits["value"], "")
    assert frame_blocked(dialog, "value")
    qtbot.wait(20)
    assert (frame.geometry(), dialog._field_edits["value"].geometry()) == before


def test_ctrl_return_and_no_default_buttons(qtbot, make_item_dialog):
    """T-05-29: Enter in a line edit never installs; Ctrl+Return installs only when Install is enabled."""
    applied = []

    def recording_apply(plan, *, backup_root=None, progress=None):
        applied.append(plan)
        return real_apply_plan(plan, backup_root=backup_root, progress=progress)

    dialog = ul_dialog(make_item_dialog, qtbot, apply_plan=recording_apply)
    dialog.activateWindow()
    qtbot.waitUntil(dialog.isActiveWindow, timeout=5000)
    for button in dialog.findChildren(QPushButton):
        assert not button.autoDefault() and not button.isDefault(), button.text()
    assert dialog._install_btn.isEnabled()

    qtbot.keyClick(dialog._field_edits["value"], Qt.Key.Key_Return)
    qtbot.keyClick(dialog._library_combo.lineEdit(), Qt.Key.Key_Return)
    qtbot.wait(100)
    assert applied == [] and dialog._stack.currentWidget() is dialog._edit_page

    # not enabled (a rebuild is pending): Ctrl+Return does nothing
    type_text(qtbot, dialog._field_edits["datasheet"], "https://example.com/x")
    assert not dialog._install_btn.isEnabled()
    qtbot.keyClick(dialog, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    qtbot.wait(100)
    assert applied == []

    wait_current(qtbot, dialog)
    assert dialog._install_btn.isEnabled()
    with qtbot.waitSignal(dialog.installed, timeout=60000):
        qtbot.keyClick(dialog, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert len(applied) == 1 and applied[0] is dialog._plan


def test_ctrl_return_shortcut_is_registered(qtbot, make_item_dialog):
    from PySide6.QtGui import QKeySequence, QShortcut

    dialog = ul_dialog(make_item_dialog, qtbot)
    keys = [s.key().toString() for s in dialog.findChildren(QShortcut)]
    assert QKeySequence("Ctrl+Return").toString() in keys


def test_one_build_at_a_time(qtbot, make_item_dialog, gates):
    """Edge PREV-06/concurrency: edits during a running build queue; two builds never overlap."""
    running = {"now": 0, "max": 0, "calls": 0}
    lock = threading.Lock()

    def counting_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        with lock:
            running["now"] += 1
            running["calls"] += 1
            running["max"] = max(running["max"], running["now"])
        try:
            if running["calls"] == 2:
                gate = threading.Event()
                gates.append(gate)
                assert gate.wait(30)
            return real_build_plan(candidate, options, layout, tools, **kwargs)
        finally:
            with lock:
                running["now"] -= 1

    dialog = ul_dialog(make_item_dialog, qtbot, build_plan=counting_build)
    dialog._request_rebuild()
    qtbot.waitUntil(lambda: len(gates) == 1, timeout=30000)
    for name in ("A_x_TI", "B_x_TI", "C_x_TI"):
        set_library(dialog, name)
    gates[0].set()
    wait_current(qtbot, dialog)
    assert running["max"] == 1
    assert dialog._plan.library == "C_x_TI"
