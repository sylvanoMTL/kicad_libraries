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
    # kicad_running is faked: the real one lists the machine's processes
    fields = {
        "detect_tools": lambda kicad_fp_dir: ToolContext(),
        "kicad_running": lambda: [],
        "probe_commit": no_git_probe,
        "run_commit": no_git_commit,
        **changes,
    }
    return replace(ImportCore(), **fields)


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
    assert dialog._result_view._banner.text() == "✓ Installed CSD85301Q2 into IC_Battery_Charger_TI"
    assert dialog.result is result
    files = dialog._result_view._files_list
    listed = [files.item(i).text() for i in range(files.count())]
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
    qtbot.waitUntil(lambda: not dialog.is_installing() and not dialog.is_committing(), timeout=30000)
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
    [
        ("UltraLibrarian", "Ultra Librarian"),
        ("Loose", "Loose files"),
        ("Unknown", "Unknown vendor"),
        ("SnapEDA", "SnapEDA"),
        ("SamacSys", "SamacSys"),
        ("Odd", "Odd"),
    ],
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
            "kicad_running": lambda: [],
            "probe_commit": no_git_probe,
            "run_commit": no_git_commit,
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


# -- plan 05-10 Task 1: one conflict row per conflict (PREV-05, D-12, D-14a) --------------------------

from PySide6.QtGui import QAction  # noqa: E402

from kicad_lib_manager.importer.plan import Conflict, Resolution  # noqa: E402
from kicad_lib_manager.widgets.theme import ACCENT  # noqa: E402

OTHER_LIB = "IC_Battery_Fuel_Gauge_ADI"
SYMBOL_KEY = f"symbol:{LIB}:CSD85301Q2"
FP_KEY = f"footprint:{LIB}:dqk0006b"
MODEL_KEY = "model:csd85301q2.stp"
NEEDS_CHOICE = "Needs a choice"


def write_clashes(layout, *, symbol=False, footprint=True, model=True, lower_fp=False, library=LIB) -> None:
    """Put items that differ from the UL sample's into the target, so each becomes a conflict."""
    from zipfixtures import STEP_BYTES, symbol_lib
    from zipfixtures import footprint as fp_bytes

    if footprint:
        name = "dqk0006b.kicad_mod" if lower_fp else "DQK0006B.kicad_mod"
        (layout.footprints_dir / f"{library}.pretty" / name).write_bytes(fp_bytes("DQK0006B", model="other.step"))
    if model:
        (layout.models_dir / "CSD85301Q2.stp").write_bytes(STEP_BYTES + b"\n")
    if symbol:
        (layout.symbols_dir / f"{library}.kicad_sym").write_bytes(symbol_lib((library, "CSD85301Q2")))


def clash_dialog(make_item_dialog, qtbot, item_layout, core=None, **kinds) -> ImportDialog:
    write_clashes(item_layout, **kinds)
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, **(core or {}))
    wait_current(qtbot, dialog)
    return dialog


def toggles(row) -> list[bool]:
    return [b.isChecked() for b in (row._overwrite_btn, row._rename_btn, row._skip_btn)]


def test_conflict_rows_no_bulk_and_none_selected(qtbot, make_item_dialog, item_layout, recorded):
    """T-05-30: one row per conflict, nothing pre-selected, no bulk control, Install blocked."""
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout)
    assert set(dialog._conflict_rows) == {FP_KEY, MODEL_KEY}
    assert dialog._conflicts_box.isVisible()
    for row in dialog._conflict_rows.values():
        assert toggles(row) == [False, False, False]
        assert row._needs_label.text() == NEEDS_CHOICE and row._needs_label.isVisible()
        assert row.property("resolved") is False
        assert row.current_resolution() is None
    assert dialog._resolutions == {}
    assert recorded[-1].resolutions == {}
    texts = [b.text() for b in dialog.findChildren(QPushButton)] + [a.text() for a in dialog.findChildren(QAction)]
    assert [t for t in texts if "all" in t.lower() and t != "Install Part"] == []
    assert not dialog._install_btn.isEnabled()


def test_conflict_choice_rebuilds_and_resolves(qtbot, make_item_dialog, item_layout, recorded):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout)
    fp_row = dialog._conflict_rows[FP_KEY]
    before = len(recorded)
    fp_row._skip_btn.click()
    wait_current(qtbot, dialog)
    assert len(recorded) == before + 1
    assert recorded[-1].resolutions == {FP_KEY: Resolution("skip")}
    assert toggles(fp_row) == [False, False, True]
    assert fp_row.property("resolved") is True
    assert fp_row._hint_label.text() == "Skip - keep the existing footprint and link it"
    assert not fp_row._needs_label.isVisible()
    # clicking the checked button again changes nothing
    fp_row._skip_btn.click()
    qtbot.wait(100)
    assert len(recorded) == before + 1 and toggles(fp_row) == [False, False, True]
    # a kept footprint does not link the incoming model, so that conflict leaves the plan
    assert set(dialog._conflict_rows) == {FP_KEY}
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    assert dialog._strip.text().startswith("✓ Ready to install")
    # Overwrite brings the model conflict back, unresolved
    fp_row._overwrite_btn.click()
    wait_current(qtbot, dialog)
    assert set(dialog._conflict_rows) == {FP_KEY, MODEL_KEY}
    assert not dialog._install_btn.isEnabled()
    model_row = dialog._conflict_rows[MODEL_KEY]
    assert model_row.current_resolution() is None
    model_row._overwrite_btn.click()
    wait_current(qtbot, dialog)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    assert dialog._strip.text().startswith("✓ Ready to install")
    assert recorded[-1].resolutions == {FP_KEY: Resolution("overwrite"), MODEL_KEY: Resolution("overwrite")}


def test_conflict_rename_field_and_empty_reason(qtbot, make_item_dialog, item_layout, recorded):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False)
    row = dialog._conflict_rows[FP_KEY]
    assert not row._rename_edit.isVisible()
    row._rename_btn.click()
    wait_current(qtbot, dialog)
    suggested = dialog._plan.conflicts[0].suggested_name
    assert suggested == "DQK0006B_2"
    assert row._rename_edit.isVisible() and row._rename_edit.text() == suggested
    assert row._rename_edit.minimumWidth() >= 160
    assert row._hint_label.text() == f"Rename - install as {suggested} and leave the existing footprint untouched"
    assert recorded[-1].resolutions == {FP_KEY: Resolution("rename", suggested)}

    type_text(qtbot, row._rename_edit, "")
    assert not dialog._install_btn.isEnabled()
    wait_current(qtbot, dialog)
    assert list(strip_links(dialog)) == ["Enter a new name for footprint DQK0006B"]
    assert frame_blocked(dialog, f"rename:{FP_KEY}")
    assert recorded[-1].resolutions[FP_KEY] == Resolution("rename", "")
    dialog._on_reason_link("reason:0")
    assert dialog.focusWidget() is row._rename_edit

    type_text(qtbot, row._rename_edit, "FP_X")
    wait_current(qtbot, dialog)
    assert recorded[-1].resolutions[FP_KEY] == Resolution("rename", "FP_X")
    renames = next(s for s in dialog._preview.sections if s.name == "Renames")
    assert "DQK0006B → FP_X" in [r.text for r in renames.rows]
    assert not frame_blocked(dialog, f"rename:{FP_KEY}")
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)


def test_conflict_choice_carried_by_key(qtbot, make_item_dialog, item_layout):
    """T-05-31 / D-14a: a choice never moves to another item."""
    write_clashes(item_layout, model=False, library=OTHER_LIB)
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False)
    row = dialog._conflict_rows[FP_KEY]
    row._overwrite_btn.click()
    wait_current(qtbot, dialog)
    # an unrelated edit keeps the same key, so the choice stays
    type_text(qtbot, dialog._field_edits["description"], "Edited")
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows[FP_KEY] is row
    assert row.current_resolution() == Resolution("overwrite")
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)

    # another library has the same clash, but its key is another item
    other_key = f"footprint:{OTHER_LIB}:dqk0006b"
    set_library(dialog, OTHER_LIB)
    wait_current(qtbot, dialog)
    assert set(dialog._conflict_rows) == {other_key}
    assert dialog._resolutions == {}
    assert dialog._conflict_rows[other_key].current_resolution() is None
    assert not dialog._install_btn.isEnabled()

    # coming back does not bring the old choice back
    set_library(dialog, LIB)
    wait_current(qtbot, dialog)
    row = dialog._conflict_rows[FP_KEY]
    assert row.current_resolution() is None and dialog._resolutions == {}

    # a free footprint name removes the row and its choice
    row._overwrite_btn.click()
    wait_current(qtbot, dialog)
    type_text(qtbot, dialog._fp_name_edit, "OTHER_FP")
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows == {} and dialog._resolutions == {}
    assert not dialog._conflicts_box.isVisible()
    assert f"conflict:{FP_KEY}" not in dialog._reason_targets
    assert f"rename:{FP_KEY}" not in dialog._reason_targets and f"rename:{FP_KEY}" not in dialog._field_frames
    dialog._fp_name_restore.click()
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows[FP_KEY].current_resolution() is None
    assert dialog._conflicts_box.isVisible()


def test_conflict_rows_update_in_place(qtbot, make_item_dialog, item_layout):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False)
    row = dialog._conflict_rows[FP_KEY]
    row._rename_btn.click()
    wait_current(qtbot, dialog)
    edit = row._rename_edit
    type_text(qtbot, edit, "Abc_1X")
    qtbot.keyClick(edit, Qt.Key.Key_Home)
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows[FP_KEY] is row
    assert row._rename_edit is edit and edit.text() == "Abc_1X"
    assert dialog.focusWidget() is edit
    assert edit.cursorPosition() == 0


def test_conflict_case_twin_row(qtbot, make_item_dialog, item_layout):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False, lower_fp=True)
    row = dialog._conflict_rows[FP_KEY]
    assert "only by letter case" in row._title_label.toolTip()
    assert row._kind_label.text() == "footprint"
    assert not dialog._install_btn.isEnabled()


def test_identical_existing_item_has_no_row(qtbot, make_item_dialog, item_layout):
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows == {}
    op = next(op for op in dialog._plan.ops if op.kind == "footprint")
    op.path.write_bytes(op.data)
    dialog._request_rebuild()
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows == {} and not dialog._conflicts_box.isVisible()


def test_conflict_rows_order(qtbot, make_item_dialog, item_layout):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, symbol=True)
    keys = [c.key for c in dialog._plan.conflicts]
    assert keys == [SYMBOL_KEY, FP_KEY, MODEL_KEY]
    layout = dialog._conflicts_layout
    assert [layout.itemAt(i).widget() for i in range(layout.count())] == [dialog._conflict_rows[k] for k in keys]
    prefix = "Choose Overwrite, Rename or Skip for "
    assert list(strip_links(dialog)) == [
        prefix + "symbol CSD85301Q2",
        prefix + "footprint DQK0006B",
        prefix + "3D model CSD85301Q2.stp",
    ]


def test_conflict_row_overwrite_style_and_hint(qtbot, make_item_dialog, item_layout):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, footprint=False)
    row = dialog._conflict_rows[MODEL_KEY]
    row._overwrite_btn.click()
    wait_current(qtbot, dialog)
    assert row._overwrite_btn.isChecked()
    assert ERROR in row._overwrite_btn.styleSheet()
    assert ACCENT in row._rename_btn.styleSheet() and ACCENT in row._skip_btn.styleSheet()
    assert row._hint_label.text() == "Overwrite - replace the existing 3D model with the incoming one (a backup is kept)"
    assert ERROR in row._hint_label.styleSheet()
    row._skip_btn.click()
    assert MUTED in row._hint_label.styleSheet()
    assert row._hint_label.text() == "Skip - keep the existing 3D model and link it"
    assert toggles(row) == [False, False, True]


def test_conflict_section_hidden_without_conflicts(qtbot, make_item_dialog):
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    assert dialog._conflict_rows == {}
    assert not dialog._conflicts_box.isVisible()


def test_conflict_row_exclusive_toggles_and_line_one(qtbot):
    from kicad_lib_manager.widgets.conflict_row import ConflictRow

    long_name, long_existing = "N" * 80, "where " * 40
    conflict = Conflict("footprint:L:n", "footprint", long_name, long_existing, suggested_name="N_2")
    row = ConflictRow(conflict)
    qtbot.addWidget(row)
    events = []
    row.choice_changed.connect(lambda key, res: events.append((key, res)))
    row.resize(420, 120)
    row.show()
    full = f"{long_name} — {long_existing}"
    assert row._title_label.toolTip() == full
    assert row._title_label.text() != full and "…" in row._title_label.text()
    assert row._rename_edit.minimumWidth() >= 160
    row._overwrite_btn.click()
    row._rename_btn.click()
    assert toggles(row) == [False, True, False]
    row._rename_btn.click()  # again: stays checked, no event
    assert toggles(row) == [False, True, False]
    assert [res for _, res in events] == [Resolution("overwrite"), Resolution("rename", "N_2")]
    row.set_resolution(Resolution("skip"))
    assert toggles(row) == [False, False, True] and len(events) == 2  # programmatic: no signal
    row.set_resolution(None)
    assert toggles(row) == [False, False, False] and row.current_resolution() is None


def test_conflicts_overflow_geometry(qtbot, make_item_dialog, item_layout, tmp_path):
    """Backstop (UI E8/overflow): 3 conflicts and 6 footprints at 900x600 scroll vertically only."""
    from zipfixtures import STEP_BYTES, make_zip, symbol_lib
    from zipfixtures import footprint as fp_bytes

    members = [("part.kicad_sym", symbol_lib(("S1",), props=_DATASHEET))]
    members += [(f"F{i}.kicad_mod", fp_bytes(f"F{i}")) for i in range(1, 7)]
    members += [("a.step", STEP_BYTES)]
    package = make_zip(tmp_path / "six.zip", members)
    for i in (1, 2, 3):
        (item_layout.footprints_dir / f"{LIB}.pretty" / f"F{i}.kicad_mod").write_bytes(fp_bytes(f"F{i}", model="other.step"))
    dialog = make_item_dialog(package, show=True, suggest_library=_good_suggestion)
    dialog.resize(900, 600)
    wait_current(qtbot, dialog)
    assert len(dialog._conflict_rows) == 3
    rows = [dialog._conflicts_layout.itemAt(i).widget() for i in range(3)]
    rows[0]._rename_btn.click()
    wait_current(qtbot, dialog)
    type_text(qtbot, rows[0]._rename_edit, "R" * 60)
    qtbot.wait(50)
    scroll = dialog._left_scroll
    viewport = scroll.viewport()
    left = scroll.widget()
    assert scroll.verticalScrollBar().maximum() > 0
    assert not scroll.horizontalScrollBar().isVisible()
    assert left.width() <= viewport.width()
    for widget in dialog._conflicts_box.findChildren(QWidget):
        if widget.isVisible():
            right = widget.mapTo(left, QPoint(widget.width(), 0)).x()
            assert right <= viewport.width(), (widget, right, viewport.width())
    assert rows[0]._rename_edit.text() == "R" * 60
    for above, below in zip(rows, rows[1:]):
        assert below.y() - (above.y() + above.height()) == 8


# -- plan 05-10 Task 2: the content view from file rows and conflicts (D-08, Pitfall 2) ---------------

from kicad_lib_manager.importer.content import op_content as real_op_content  # noqa: E402
from kicad_lib_manager.importer.content import unchanged_content as real_unchanged_content  # noqa: E402
from kicad_lib_manager.widgets.content_view import ContentViewDialog  # noqa: E402

FP_PATH = "Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod"


def preview_row(dialog: ImportDialog, section: str, ends_with: str):
    rows = next(s for s in dialog._preview.sections if s.name == section).rows
    return next(r for r in rows if r.text.endswith(ends_with))


def open_views(dialog: ImportDialog) -> list:
    return dialog.findChildren(ContentViewDialog)


def wait_view(qtbot, dialog: ImportDialog) -> ContentViewDialog:
    qtbot.waitUntil(lambda: bool(open_views(dialog)), timeout=30000)
    return open_views(dialog)[-1]


def view_lines(view: ContentViewDialog) -> list[str]:
    return view._text.toPlainText().splitlines()


def test_content_view_new_footprint_row(qtbot, make_item_dialog):
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    dialog._preview.row_activated.emit(preview_row(dialog, "Files", "DQK0006B.kicad_mod"))
    view = wait_view(qtbot, dialog)
    assert view.windowTitle() == f"{FP_PATH} - new file"
    assert view._content.kind == "text"
    text = view._text.toPlainText()
    assert "(footprint" in text and "DQK0006B" in text


def test_content_view_modified_library_diff(qtbot, make_item_dialog):
    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion)
    wait_current(qtbot, dialog)
    dialog._preview.row_activated.emit(preview_row(dialog, "Files", "IC_Battery_Charger_TI.kicad_sym"))
    view = wait_view(qtbot, dialog)
    assert view._content.kind == "diff"
    assert view.windowTitle().endswith(" - changes")
    assert any(line.startswith("+") and "CSD85301Q2" in line for line in view_lines(view))


def test_content_view_model_row_hash_on_worker(qtbot, make_item_dialog):
    main = threading.get_ident()
    seen: list[int] = []

    def spy(op, repo_root, *, conflict=False):
        seen.append(threading.get_ident())
        return real_op_content(op, repo_root, conflict=conflict)

    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, op_content=spy)
    wait_current(qtbot, dialog)
    dialog._preview.row_activated.emit(preview_row(dialog, "Files", "CSD85301Q2.stp"))
    view = wait_view(qtbot, dialog)
    text = view._text.toPlainText()
    assert "Size: " in text and "SHA-256: " in text
    assert view._content.kind == "binary"
    assert len(seen) == 1 and seen[0] != main


def test_content_view_unchanged_row(qtbot, make_item_dialog):
    main = threading.get_ident()
    seen: list[int] = []

    def spy(path, repo_root):
        seen.append(threading.get_ident())
        return real_unchanged_content(path, repo_root)

    dialog = make_item_dialog(UL_ZIP, show=True, suggest_library=_good_suggestion, unchanged_content=spy)
    wait_current(qtbot, dialog)
    # put the planned files on disk, so the next plan has nothing left to write
    for op in dialog._plan.ops:
        op.path.write_bytes(op.source.path.read_bytes() if op.kind == "model" else op.data)
    dialog._request_rebuild()
    wait_current(qtbot, dialog)
    assert dialog._plan.is_noop
    dialog._preview.row_activated.emit(preview_row(dialog, "Files", "DQK0006B.kicad_mod"))
    view = wait_view(qtbot, dialog)
    assert view._content.kind == "unchanged"
    assert view._text.toPlainText() == "This file is unchanged by the install."
    assert len(seen) == 1 and seen[0] != main


def test_conflict_view_unresolved_uses_one_off_build(qtbot, make_item_dialog, item_layout, recorded):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False)
    plan, gen, before = dialog._plan, dialog._gen, len(recorded)
    row = dialog._conflict_rows[FP_KEY]
    qtbot.mouseDClick(row, Qt.MouseButton.LeftButton, pos=QPoint(6, 6))
    view = wait_view(qtbot, dialog)
    assert len(recorded) == before + 1
    assert recorded[-1].resolutions == {FP_KEY: Resolution("overwrite")}
    assert view.windowTitle() == f"{FP_PATH} - existing vs incoming"
    lines = view_lines(view)
    assert any(line.startswith("-") and not line.startswith("---") for line in lines)
    assert any(line.startswith("+") and not line.startswith("+++") for line in lines)
    # the one-off plan never replaces the plan on screen
    assert dialog._plan is plan and dialog._gen == gen
    assert dialog._conflict_rows[FP_KEY].current_resolution() is None
    assert not dialog._install_btn.isEnabled()


def test_conflict_view_resolved_overwrite_no_extra_build(qtbot, make_item_dialog, item_layout, recorded):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False)
    dialog._conflict_rows[FP_KEY]._overwrite_btn.click()
    wait_current(qtbot, dialog)
    before = len(recorded)
    dialog._conflict_rows[FP_KEY].activated.emit(FP_KEY)
    view = wait_view(qtbot, dialog)
    assert len(recorded) == before
    assert view.windowTitle().endswith(" - existing vs incoming")
    assert view._content.kind == "diff"


def test_conflict_view_from_preview_section(qtbot, make_item_dialog, item_layout):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, model=False)
    row = next(r for s in dialog._preview.sections if s.name == "Conflicts" for r in s.rows)
    assert row.kind == "conflict" and row.key == FP_KEY
    dialog._preview.row_activated.emit(row)
    view = wait_view(qtbot, dialog)
    assert view.windowTitle() == f"{FP_PATH} - existing vs incoming"
    assert view._content.kind == "diff"


def test_conflict_view_model_and_symbol(qtbot, make_item_dialog, item_layout):
    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, symbol=True, footprint=False)
    dialog._conflict_rows[MODEL_KEY].activated.emit(MODEL_KEY)
    model_view = wait_view(qtbot, dialog)
    assert model_view.windowTitle() == "Custom/3DModels/CSD85301Q2.stp - existing vs incoming"
    assert "Existing" in model_view._text.toPlainText() and "Planned" in model_view._text.toPlainText()
    model_view.close()
    qtbot.waitUntil(lambda: not open_views(dialog), timeout=5000)
    dialog._conflict_rows[SYMBOL_KEY].activated.emit(SYMBOL_KEY)
    symbol_view = wait_view(qtbot, dialog)
    assert symbol_view.windowTitle() == "Custom/Symbols/IC_Battery_Charger_TI.kicad_sym - existing vs incoming"
    assert symbol_view._content.kind == "diff"


def test_conflict_view_refused_one_off_shows_the_error(qtbot, make_item_dialog, item_layout):
    def refusing(candidate, options, layout, tools=ToolContext(), **kwargs):
        plan = real_build_plan(candidate, options, layout, tools, **kwargs)
        if options.resolutions.get(FP_KEY) == Resolution("overwrite"):
            return replace(plan, ops=(), issues=(Issue(Severity.ERROR, "install.test", "The incoming item is refused"),))
        return plan

    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, core={"build_plan": refusing}, model=False)
    dialog._conflict_rows[FP_KEY].activated.emit(FP_KEY)
    view = wait_view(qtbot, dialog)
    assert view._content.kind == "error"
    assert view._text.toPlainText() == "The incoming item is refused"


def test_builds_never_overlap(qtbot, make_item_dialog, item_layout, gates):
    running = {"now": 0, "max": 0, "calls": 0}
    lock = threading.Lock()

    def counting_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        with lock:
            running["now"] += 1
            running["calls"] += 1
            running["max"] = max(running["max"], running["now"])
            gated = running["calls"] == 2
        try:
            if gated:
                gate = threading.Event()
                gates.append(gate)
                assert gate.wait(30)
            return real_build_plan(candidate, options, layout, tools, **kwargs)
        finally:
            with lock:
                running["now"] -= 1

    dialog = clash_dialog(make_item_dialog, qtbot, item_layout, core={"build_plan": counting_build}, model=False)
    assert running["calls"] == 1
    dialog._request_rebuild()
    qtbot.waitUntil(lambda: len(gates) == 1, timeout=30000)
    dialog._conflict_rows[FP_KEY].activated.emit(FP_KEY)
    qtbot.wait(150)
    assert running["calls"] == 2 and not open_views(dialog)  # the one-off waits for the running build
    gates[0].set()
    wait_view(qtbot, dialog)
    assert running["calls"] == 3
    assert running["max"] == 1


# -- plan 05-11 Task 1: install progress, locked inputs, failure banner (D-10, D-15) ---------------------

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from kicad_lib_manager.widgets.theme import ERROR_TINT  # noqa: E402

CLOSING_RETRY = "Fix the problem and click Install Part again."
TITLE_RESTORED = "Install failed. Every file was restored."
TITLE_NOT_RESTORED = "Install failed and some files could not be restored."


@pytest.fixture
def make_install_dialog(qtbot, item_layout, gates, recorded, tmp_path):
    """A shown dialog on a synthetic Custom layout with the UL sample planned; backups go to tmp_path."""

    def make(package: Path = UL_ZIP, **changes) -> ImportDialog:
        fields = {
            "detect_tools": lambda kicad_fp_dir: ToolContext(),
            "downloads_dir": lambda: None,
            "build_plan": recording_build(recorded),
            "suggest_library": _good_suggestion,
            "kicad_running": lambda: [],
            "probe_commit": no_git_probe,
            "run_commit": no_git_commit,
            **changes,
        }
        dialog = ImportDialog(
            item_layout.repo_root, item_layout, core=replace(ImportCore(), **fields), backup_root=tmp_path / "backups"
        )
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.open_path(package)
        wait_current(qtbot, dialog)
        return dialog

    return make


def failing_apply(*issues, backup_dir=None):
    """An apply_plan fake that reports a rolled-back install with these issues."""

    def apply(plan, *, backup_root=None, progress=None):
        return InstallResult(
            ok=False, library=plan.library, new_library=False, touched=(), issues=tuple(issues), backup_dir=backup_dir
        )

    return apply


def blocking_apply(gates, steps=(), started=None):
    """An apply_plan fake that emits the given progress steps, then waits for a gate and installs for real."""

    def apply(plan, *, backup_root=None, progress=None):
        for step in steps:
            progress(*step)
        gate = threading.Event()
        gates.append(gate)
        if started is not None:
            started.set()
        assert gate.wait(30)
        return real_apply_plan(plan, backup_root=backup_root, progress=progress)

    return apply


def stale(text: str = "X appeared") -> Issue:
    return Issue(Severity.ERROR, "install.stale_plan", text)


def banner_lines(dialog: ImportDialog) -> list[str]:
    return dialog._failure_body.toPlainText().splitlines()


def test_install_progress_and_lock(qtbot, make_install_dialog, gates):
    steps = [("Writing a", 0, 4), ("Writing b", 1, 4)]
    dialog = make_install_dialog(apply_plan=blocking_apply(gates, steps))
    assert dialog._install_btn.isEnabled()
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._install_step.full_text() == "Writing b", timeout=30000)

    assert dialog.is_installing()
    assert dialog._install_bar.value() == 25
    assert (dialog._install_bar.minimum(), dialog._install_bar.maximum()) == (0, 100)
    assert dialog._install_bar.minimumSize() == QSize(240, 16) == dialog._install_bar.maximumSize()
    assert dialog._install_btn.text() == "Installing..."
    assert not dialog._install_btn.isEnabled()
    assert not dialog._left_scroll.isEnabled()
    assert not dialog._change_btn.isEnabled()
    assert not dialog._header_row.isEnabled()
    assert dialog._preview.isEnabled()  # the tree stays scrollable and its rows can be opened
    assert dialog._install_row.isVisible() and not dialog._strip.isVisible()
    assert MUTED.lower() in dialog._install_step.styleSheet().lower()
    assert not [b for b in dialog.findChildren(QPushButton) if b.text() == "Cancel"]

    gates[0].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)
    assert dialog._install_bar.value() == 100  # apply_plan's index never reaches total


def test_install_rows_can_be_opened_while_installing(qtbot, make_install_dialog, gates):
    dialog = make_install_dialog(apply_plan=blocking_apply(gates))
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog.is_installing() and bool(gates), timeout=30000)
    dialog._preview.row_activated.emit(preview_row(dialog, "Files", "DQK0006B.kicad_mod"))
    wait_view(qtbot, dialog)
    gates[0].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)


def test_install_close_esc_reject_ignored(qtbot, make_install_dialog, gates):
    started = threading.Event()
    dialog = make_install_dialog(apply_plan=blocking_apply(gates, started=started))
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: started.is_set() and dialog.is_installing(), timeout=30000)

    dialog.close()
    dialog.reject()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert dialog.isVisible()
    assert dialog.is_installing()

    gates[0].set()
    qtbot.waitUntil(lambda: dialog.result is not None and not dialog.is_installing() and not dialog.is_committing(), timeout=60000)
    assert dialog.isVisible()
    dialog.close()
    assert not dialog.isVisible()


def test_install_failure_banner_and_rebuild(qtbot, make_install_dialog, recorded):
    dialog = make_install_dialog(apply_plan=failing_apply(stale("X appeared")))
    builds = len(recorded)
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)

    assert dialog._stack.currentWidget() is dialog._edit_page
    assert dialog._edit_page.layout().itemAt(0).widget() is dialog._failure_banner  # above the package row
    assert dialog._failure_title.text() == TITLE_RESTORED
    assert banner_lines(dialog) == ["X appeared", CLOSING_RETRY]
    banner_style = dialog._failure_banner.styleSheet().lower()
    assert ERROR_TINT.lower() in banner_style and f"2px solid {ERROR}".lower() in banner_style
    assert ERROR.lower() in dialog._failure_title.styleSheet().lower()
    assert dialog._failure_title.font().bold() and dialog._failure_title.font().pointSize() == 12
    wait_current(qtbot, dialog)
    assert len(recorded) == builds + 1  # the plan was rebuilt at once, so a retry cannot hit the stale-plan guard
    assert dialog._left_scroll.isEnabled() and dialog._header_row.isEnabled() and dialog._change_btn.isEnabled()
    assert dialog._install_btn.text() == "Install Part" and dialog._install_btn.isEnabled()
    assert dialog._strip.isVisible() and not dialog._install_row.isVisible()
    assert dialog.result is None


def test_install_failure_restore_failed_variant(qtbot, make_install_dialog, tmp_path):
    kept = tmp_path / "bk"
    restore = Issue(Severity.ERROR, "install.rollback_failed", "Foo.kicad_sym could not be restored (denied)")
    dialog = make_install_dialog(apply_plan=failing_apply(stale("Y changed"), restore, backup_dir=kept))
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)
    assert dialog._failure_title.text() == TITLE_NOT_RESTORED
    assert banner_lines(dialog) == [
        "Y changed", "Foo.kicad_sym could not be restored (denied)", f"The original files are in {kept}.",
    ]
    wait_current(qtbot, dialog)


def test_install_failure_without_backup_dir_keeps_retry_line(qtbot, make_install_dialog):
    restore = Issue(Severity.ERROR, "install.rollback_failed", "a.stp could not be removed (denied)")
    dialog = make_install_dialog(apply_plan=failing_apply(restore))
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)
    assert dialog._failure_title.text() == TITLE_NOT_RESTORED
    assert banner_lines(dialog)[-1] == CLOSING_RETRY
    wait_current(qtbot, dialog)


def test_install_failure_ignores_non_error_issues(qtbot, make_install_dialog):
    warn = Issue(Severity.WARNING, "verify.name_elsewhere", "a warning")
    dialog = make_install_dialog(apply_plan=failing_apply(warn, stale("only this")))
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)
    assert banner_lines(dialog) == ["only this", CLOSING_RETRY]
    wait_current(qtbot, dialog)


def test_install_worker_exception_shows_banner(qtbot, make_install_dialog, recorded):
    def boom(plan, *, backup_root=None, progress=None):
        raise RuntimeError("worker died")

    dialog = make_install_dialog(apply_plan=boom)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    builds = len(recorded)
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)
    assert dialog._failure_title.text() == "Install failed."
    assert "Import step failed: RuntimeError: worker died" in banner_lines(dialog)
    assert any(i.text.startswith("Import step failed: RuntimeError: worker died") for i in logged)
    wait_current(qtbot, dialog)
    assert len(recorded) == builds + 1
    assert dialog._install_btn.isEnabled()


def test_failure_banner_dismiss_and_cap(qtbot, make_install_dialog, gates):
    reasons = [stale(f"Reason number {n} " + "wrapping words " * 6) for n in range(10)]
    calls = {"n": 0}
    second = blocking_apply(gates)

    def apply(plan, *, backup_root=None, progress=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return failing_apply(*reasons)(plan)
        return second(plan, backup_root=backup_root, progress=progress)

    dialog = make_install_dialog(apply_plan=apply)
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)
    wait_current(qtbot, dialog)

    body = dialog._failure_body
    assert body.isReadOnly()
    margins = 2 * body.frameWidth() + 2 * int(body.document().documentMargin())
    limit = 6 * body.fontMetrics().lineSpacing() + margins + 2
    qtbot.waitUntil(lambda: body.verticalScrollBar().maximum() > 0, timeout=5000)  # more than 6 lines: it scrolls
    assert body.height() <= limit
    assert len(banner_lines(dialog)) == 11

    dismiss = dialog._failure_banner.findChild(QToolButton)
    assert dismiss.accessibleName() == "Dismiss failure message"
    assert dismiss.text() == "✕"
    dismiss.click()
    assert not dialog._failure_banner.isVisible()

    # a failure shown again is dismissed by the next Install click
    dialog._show_failure([stale("again")], None)
    assert dialog._failure_banner.isVisible()
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog.is_installing() and bool(gates), timeout=30000)
    assert not dialog._failure_banner.isVisible()
    gates[0].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)


def test_progress_stall_holds_value(qtbot, make_install_dialog, gates):
    dialog = make_install_dialog(apply_plan=blocking_apply(gates, [("Writing a", 0, 4), ("Writing b", 2, 4)]))
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._install_step.full_text() == "Writing b", timeout=30000)
    qtbot.wait(300)
    assert dialog._install_bar.value() == 50
    assert dialog._install_step.full_text() == "Writing b"
    gates[0].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)


# -- plan 05-11 Task 2: the Result view, KiCad notice, status rows and the Phase 6 slot (D-15 to D-18) ----

import ast  # noqa: E402
import subprocess  # noqa: E402
import types  # noqa: E402

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QDesktopServices  # noqa: E402

from kicad_lib_manager.widgets.import_result import ImportResultView  # noqa: E402
from kicad_lib_manager.widgets.theme import MONO_FAMILY  # noqa: E402

KICAD_NOTICE = f"KiCad is running. Reopen KiCad's Symbol and Footprint editors to see {LIB}."
PACKAGE_ROOT = REPO_ROOT / "kicad_lib_manager"
UL_REL = [
    "Custom/3DModels/CSD85301Q2.stp",
    "Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
    "Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
]


def install_ul(qtbot, dialog: ImportDialog) -> InstallResult:
    """Click Install and wait for the Result view."""
    with qtbot.waitSignal(dialog.installed, timeout=60000) as blocker:
        dialog._install_btn.click()
    return blocker.args[0]


def finish_workers(qtbot, dialog: ImportDialog) -> None:
    """Wait until every worker thread ended and its queued result signal was delivered."""
    qtbot.waitUntil(lambda: not any(w.isRunning() for w in dialog._workers), timeout=30000)
    qtbot.wait(50)


def fake_result(tmp_path: Path, issues=(), touched=2, backup=True) -> InstallResult:
    paths = tuple(tmp_path / "Custom" / "Symbols" / f"f{n}.kicad_sym" for n in range(touched))
    return InstallResult(
        ok=True, library=LIB, new_library=False, touched=paths, issues=tuple(issues),
        backup_dir=(tmp_path / "bk") if backup else None,
    )


def result_view(qtbot, tmp_path: Path, **kwargs) -> tuple[ImportResultView, InstallResult]:
    view = ImportResultView()
    qtbot.addWidget(view)
    result = fake_result(tmp_path, **kwargs)
    plan = types.SimpleNamespace(symbol_name="CSD85301Q2", library=LIB)
    view.show_result(result, plan, tmp_path)
    return view, result


def warning_lines(view: ImportResultView) -> list[str]:
    return [label.text() for label in view._warning_labels]


def test_result_view_success_ul(qtbot, make_install_dialog):
    dialog = make_install_dialog()
    result = install_ul(qtbot, dialog)
    finish_workers(qtbot, dialog)
    view = dialog._result_view

    assert dialog._stack.currentWidget() is view is dialog._result_page
    assert view._banner.text() == "✓ Installed CSD85301Q2 into IC_Battery_Charger_TI"
    assert view._banner.font().bold() and view._banner.font().pointSize() == 12
    assert SUCCESS.lower() in view._banner.styleSheet().lower()
    assert view._files_heading.text() == "Files written (3)"
    shown = [view._files_list.item(i).text() for i in range(view._files_list.count())]
    assert sorted(shown) == UL_REL
    assert result.backup_dir is not None  # the .kicad_sym was modified
    assert view._backup_row.isVisible()
    assert view._backup_label.full_text() == f"Backup folder: {result.backup_dir}"
    assert view._backup_label.font().family() == MONO_FAMILY
    assert view._backup_label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
    assert not view._kicad_notice.isVisible()
    slot = view.findChild(QWidget, "commitSlot")
    assert slot is view.commit_slot and slot.isVisible() and slot.maximumHeight() > 0  # Phase 6: the commit panel
    assert dialog.result is result
    assert dialog.result_plan is dialog._plan
    assert view.close_button.isDefault() and dialog.focusWidget() is view.close_button
    assert not dialog._install_btn.isDefault()


def test_result_view_warnings_and_none(qtbot, tmp_path):
    warn = Issue(Severity.WARNING, "verify.pin_pad_mismatch", "Pin 3 has no pad")
    info = Issue(Severity.INFO, "install.nothing_to_do", "Nothing to do for the model")
    boom = Issue(Severity.ERROR, "verify.name_elsewhere", "Name is also used in Wurth")
    ok = Issue(Severity.SUCCESS, "table.entries_added", "Added")
    view, _ = result_view(qtbot, tmp_path, issues=(info, warn, boom, ok))
    assert warning_lines(view) == ["⚠ Pin 3 has no pad", "✖ Name is also used in Wurth"]
    assert AMBER.lower() in view._warning_labels[0].styleSheet().lower()
    assert ERROR.lower() in view._warning_labels[1].styleSheet().lower()
    assert all(label.wordWrap() and label.textFormat() == Qt.TextFormat.PlainText for label in view._warning_labels)
    assert view._warnings_heading.text() == "Warnings"

    view, _ = result_view(qtbot, tmp_path, issues=(info,))
    assert warning_lines(view) == ["No warnings."]
    assert MUTED.lower() in view._warning_labels[0].styleSheet().lower()

    view, _ = result_view(qtbot, tmp_path)
    assert warning_lines(view) == ["No warnings."]


def test_result_view_warnings_are_plain_text(qtbot, tmp_path):
    hostile = Issue(Severity.WARNING, "verify.name_elsewhere", "<b>bold</b> & <a href='x'>link</a>")
    view, _ = result_view(qtbot, tmp_path, issues=(hostile,))
    assert warning_lines(view) == ["⚠ <b>bold</b> & <a href='x'>link</a>"]
    assert view._warning_labels[0].textFormat() == Qt.TextFormat.PlainText


def test_result_view_show_result_twice_replaces_content(qtbot, tmp_path):
    view, _ = result_view(qtbot, tmp_path, issues=(Issue(Severity.WARNING, "a.b", "one"),))
    view.show_result(fake_result(tmp_path, touched=1), types.SimpleNamespace(symbol_name="S", library=LIB), tmp_path)
    assert warning_lines(view) == ["No warnings."]
    assert view._files_list.count() == 1 and view._files_heading.text() == "Files written (1)"


def test_kicad_running_notice(qtbot, make_install_dialog):
    seen = {}

    def running():
        seen["thread"] = threading.get_ident()
        return ["eeschema"]

    dialog = make_install_dialog(kicad_running=running)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    install_ul(qtbot, dialog)
    view = dialog._result_view
    qtbot.waitUntil(lambda: view._kicad_notice.isVisible(), timeout=30000)
    assert view._kicad_notice.text() == f"⚠ {KICAD_NOTICE}"
    assert view._kicad_notice.textFormat() == Qt.TextFormat.PlainText
    assert AMBER_TINT.lower() in view._kicad_notice.styleSheet().lower()
    assert seen["thread"] != threading.get_ident()
    notices = [i for i in logged if i.code == "import.kicad_running"]
    assert [(i.severity, i.text) for i in notices] == [(Severity.WARNING, KICAD_NOTICE)]


def test_kicad_running_empty_or_failing_shows_nothing(qtbot, make_install_dialog):
    called = threading.Event()

    def empty():
        called.set()
        return []

    dialog = make_install_dialog(kicad_running=empty)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    install_ul(qtbot, dialog)
    assert called.wait(30)
    finish_workers(qtbot, dialog)
    assert not dialog._result_view._kicad_notice.isVisible()
    assert [i for i in logged if i.code.startswith("import.")] == []


def test_kicad_running_failure_shows_nothing_and_logs_nothing(qtbot, make_install_dialog):
    called = threading.Event()

    def broken():
        called.set()
        raise OSError("tasklist is gone")

    dialog = make_install_dialog(kicad_running=broken)
    logged = []
    dialog.issues_logged.connect(logged.extend)
    install_ul(qtbot, dialog)
    assert called.wait(30)
    finish_workers(qtbot, dialog)
    assert not dialog._result_view._kicad_notice.isVisible()
    assert [i for i in logged if i.code.startswith("import.")] == []


def test_post_install_status_rows(qtbot, tmp_path):
    view, _ = result_view(qtbot, tmp_path)
    assert view.status_text("library_list").startswith("Library list")
    assert view.status_text("tables").startswith("Library tables")
    assert view._status_labels["generate_hint"].isHidden()

    view.set_status("library_list", "Rescanning...", Severity.INFO)
    view.set_status("tables", "Added X to sym-lib-table and fp-lib-table", Severity.SUCCESS)
    assert view.status_text("library_list") == "Library list: Rescanning..."
    assert view.status_text("tables") == "Library tables: Added X to sym-lib-table and fp-lib-table"
    assert SUCCESS.lower() in view._status_labels["tables"].styleSheet().lower()
    view.set_status("library_list", "Rescan failed - see the log", Severity.ERROR)
    assert ERROR.lower() in view._status_labels["library_list"].styleSheet().lower()
    view.set_status("library_list", "Updated", Severity.WARNING)
    assert AMBER.lower() in view._status_labels["library_list"].styleSheet().lower()
    view.set_status("generate_hint", "⚠ X is not in the library tables. Press Generate Tables to add it.", Severity.WARNING)
    assert not view._status_labels["generate_hint"].isHidden()
    assert view.status_text("generate_hint") == "⚠ X is not in the library tables. Press Generate Tables to add it."
    assert all(label.textFormat() == Qt.TextFormat.PlainText for label in view._status_labels.values())


def test_dialog_forwards_post_install_status(qtbot, make_install_dialog):
    dialog = make_install_dialog()
    install_ul(qtbot, dialog)
    finish_workers(qtbot, dialog)
    dialog.set_post_install_status("tables", "Updating...", Severity.INFO)
    assert dialog._result_view.status_text("tables") == "Library tables: Updating..."


def test_result_backup_hidden_without_backup_dir(qtbot, tmp_path):
    view, _ = result_view(qtbot, tmp_path, backup=False)
    view.show()
    assert view._backup_row.isHidden()
    assert not view.open_folder_button.isVisible()


def test_open_folder_only_backup_dir(qtbot, make_install_dialog, monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url) or True))
    dialog = make_install_dialog()
    result = install_ul(qtbot, dialog)
    finish_workers(qtbot, dialog)
    view = dialog._result_view
    assert view.open_folder_button.text() == "Open folder"

    view.open_folder_button.click()
    assert opened == [QUrl.fromLocalFile(str(result.backup_dir))]

    # a written file opens in the read-only content view, never in the operating system
    row = next(i for i in range(view._files_list.count()) if view._files_list.item(i).text().endswith(".kicad_mod"))
    item = view._files_list.item(row)
    # Enter and a double click both end in the list's activated signal; the offscreen platform sends no
    # synthetic double click, so the key is used here
    view._files_list.setCurrentItem(item)
    view._files_list.setFocus()
    QTest.keyClick(view._files_list, Qt.Key.Key_Return)
    shown = wait_view(qtbot, dialog)
    assert shown.windowTitle() == f"{item.text()} - written"
    assert "(footprint" in shown._text.toPlainText()
    assert opened == [QUrl.fromLocalFile(str(result.backup_dir))]
    assert dialog.isVisible() and not dialog._closing  # Enter on a row must not reach the Close button


def test_result_files_list_caps_and_elides(qtbot, tmp_path):
    view, _ = result_view(qtbot, tmp_path, touched=12)
    view.resize(500, 700)
    view.show()
    qtbot.waitExposed(view)
    files = view._files_list
    row = files.sizeHintForRow(0)
    assert files.height() == files.maximumHeight() == files.minimumHeight() == 8 * row + 2 * files.frameWidth()
    assert files.verticalScrollBar().maximum() > 0
    assert files.textElideMode() == Qt.TextElideMode.ElideMiddle
    assert files.editTriggers() == files.EditTrigger.NoEditTriggers
    assert [files.item(i).toolTip() for i in (0, 11)] == [files.item(0).text(), files.item(11).text()]
    assert files.item(0).text() == "Custom/Symbols/f0.kicad_sym"

    few, _ = result_view(qtbot, tmp_path, touched=3)
    few.show()
    assert few._files_list.height() == 3 * row + 2 * few._files_list.frameWidth()


def test_backup_path_elides_with_tooltip(qtbot, tmp_path):
    view, result = result_view(qtbot, tmp_path)
    view._backup_label.set_full_text("Backup folder: " + "x" * 400)
    view.resize(500, 600)
    view.show()
    qtbot.waitExposed(view)
    assert "…" in view._backup_label.text()
    assert view._backup_label.toolTip() == "Backup folder: " + "x" * 400


def test_file_activated_signal_carries_absolute_path(qtbot, tmp_path):
    view, result = result_view(qtbot, tmp_path)
    view.show()
    qtbot.waitExposed(view)
    with qtbot.waitSignal(view.file_activated, timeout=2000) as blocker:
        view._files_list.itemActivated.emit(view._files_list.item(1))
    assert blocker.args == [result.touched[1]]


def source_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def test_import_flow_modules_do_not_import_subprocess():
    modules = (
        "widgets/import_dialog.py", "widgets/import_result.py", "widgets/conflict_row.py",
        "importer/preview.py", "importer/form.py", "importer/content.py", "importer/downloads.py",
        "widgets/commit_panel.py", "importer/commit_plan.py", "importer/commit_step.py",
    )
    for module in modules:
        assert "subprocess" not in source_imports(PACKAGE_ROOT / module), module


def test_import_flow_never_runs_git(qtbot, make_install_dialog, monkeypatch):
    calls = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def run(args, *a, **kw):
        calls.append(args)
        return real_run(args, *a, **kw)

    class Popen(real_popen):
        def __init__(self, args, *a, **kw):
            calls.append(args)
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "Popen", Popen)
    dialog = make_install_dialog()
    install_ul(qtbot, dialog)
    finish_workers(qtbot, dialog)
    names = [Path(str(a[0] if isinstance(a, (list, tuple)) else a).split()[0]).name.lower() for a in calls]
    assert not [n for n in names if "git" in n], names


# -- Phase 6 commit step (plan 06-01): the Result view's commit panel --------------------------

from datetime import date  # noqa: E402

from gitfixtures import make_superproject, remote_refs, requires_git  # noqa: E402


def no_git_probe(cplan, **kwargs):
    """A probe_commit fake: the commit step is unavailable, so no test but the tracer starts git."""
    from kicad_lib_manager.importer.commit_step import CommitProbe

    return CommitProbe(state="unavailable", reason="git is not used by this test")


def no_git_commit(*args, **kwargs):
    """A run_commit fake that fails loudly if a test clicks Commit without meaning to."""
    from kicad_lib_manager.importer.commit_step import CommitOutcome

    issue = Issue(Severity.ERROR, "commit.step_failed", "run_commit must not run in this test")
    return CommitOutcome(issues=(issue,))


def commit_panel_of(dialog: ImportDialog):
    from kicad_lib_manager.widgets.commit_panel import CommitPanel

    return dialog._result_view.commit_slot.findChildren(CommitPanel)


def panel_files(panel) -> list[str]:
    return [panel._files_list.item(i).text() for i in range(panel._files_list.count())]


CUSTOM_REL = sorted(path.removeprefix("Custom/") for path in UL_REL)


@requires_git
def test_tracer_commit_end_to_end(qtbot, tmp_path):
    repos = make_superproject(tmp_path / "git")
    core = replace(
        ImportCore(),
        detect_tools=lambda kicad_fp_dir: ToolContext(),
        downloads_dir=lambda: None,
        suggest_library=_good_suggestion,
        kicad_running=lambda: [],
    )
    dialog = ImportDialog(
        repos.parent, RepoLayout.for_repo(repos.parent), core=core, backup_root=tmp_path / "backups"
    )
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.open_path(UL_ZIP)
    wait_current(qtbot, dialog)
    install_ul(qtbot, dialog)

    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    assert panel._branch_label.text() == "Custom branch: main"
    assert panel_files(panel) == UL_REL
    lines = panel.message().splitlines()
    assert lines[0] == "Add CSD85301Q2 to IC_Battery_Charger_TI"
    assert "Import-Vendor: Ultra Librarian" in lines
    assert "Import-Package: ul_CSD85301Q2.zip" in lines
    assert f"Import-Date: {date.today().isoformat()}" in lines
    assert panel._parent_check.isChecked()
    assert panel._parent_check.text() == "Also commit the Custom ref in the parent repo (main)"

    refs = remote_refs(repos)
    panel.commit_button.click()
    qtbot.waitUntil(lambda: panel.state() == "done", timeout=60000)

    in_custom = repos.git(repos.custom, "show", "--name-only", "--format=", "HEAD").split()
    assert sorted(in_custom) == CUSTOM_REL
    assert repos.git(repos.custom, "status", "--porcelain").strip() == ""
    assert repos.git(repos.parent, "show", "--name-only", "--format=", "HEAD").split() == ["Custom"]
    gitlink = repos.git(repos.parent, "ls-tree", "HEAD", "Custom").split()[2]
    assert gitlink == repos.git(repos.custom, "rev-parse", "HEAD").strip()
    assert remote_refs(repos) == refs
    assert "Not pushed — Custom is 1 commit ahead of origin/main (as last fetched)" in panel.outcome_lines()
    trailers = repos.git(repos.custom, "log", "-1", "--format=%(trailers:only,unfold)").split("\n")
    assert [t for t in trailers if t] == [
        "Import-Vendor: Ultra Librarian",
        "Import-Package: ul_CSD85301Q2.zip",
        f"Import-Date: {date.today().isoformat()}",
    ]


def test_commit_slot_holds_panel_after_install(qtbot, make_install_dialog):
    dialog = make_install_dialog(probe_commit=no_git_probe, run_commit=no_git_commit)
    install_ul(qtbot, dialog)
    finish_workers(qtbot, dialog)
    view = dialog._result_view
    slot = view.findChild(QWidget, "commitSlot")

    assert slot is view.commit_slot and slot.isVisible() and slot.maximumHeight() > 0
    (panel,) = commit_panel_of(dialog)
    assert panel.state() == "unavailable"
    assert panel_files(panel) == UL_REL


def test_commit_close_refused_while_git_runs(qtbot, make_install_dialog, gates):
    from kicad_lib_manager.importer.commit_step import CommitOutcome, CommitProbe

    started = threading.Event()

    def ready_probe(cplan, **kwargs):
        return CommitProbe(state="ready", branch="main", parent_dir=cplan.repo_root, parent_ok=True, parent_branch="main")

    def blocking_commit(cplan, message, bump, **kwargs):
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        done = Issue(Severity.SUCCESS, "commit.custom_done", "Committed abc1234 on main in Custom")
        return CommitOutcome(custom_commit="abc1234", custom_branch="main", issues=(done,))

    dialog = make_install_dialog(probe_commit=ready_probe, run_commit=blocking_commit)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    panel.commit_button.click()
    qtbot.waitUntil(lambda: started.is_set() and dialog.is_committing(), timeout=30000)
    assert panel.state() == "committing"

    dialog.reject()
    dialog.close()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert dialog.isVisible()
    assert dialog.is_committing()

    gates[-1].set()
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    assert panel.state() == "done"
    dialog._result_view.close_button.click()
    assert not dialog.isVisible()


def test_no_commit_step_after_failed_or_empty_install(qtbot, make_install_dialog):
    dialog = make_install_dialog(
        apply_plan=failing_apply(stale()), probe_commit=no_git_probe, run_commit=no_git_commit
    )
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: dialog._failure_banner.isVisible(), timeout=30000)
    slot = dialog._result_view.commit_slot
    assert slot.isHidden() and slot.maximumHeight() == 0
    assert commit_panel_of(dialog) == []
    wait_current(qtbot, dialog)

    def empty_apply(plan, *, backup_root=None, progress=None):
        return InstallResult(ok=True, library=plan.library, new_library=False, touched=(), issues=())

    other = make_install_dialog(apply_plan=empty_apply, probe_commit=no_git_probe, run_commit=no_git_commit)
    other._install_btn.click()
    qtbot.waitUntil(lambda: other.result is not None, timeout=30000)
    slot = other._result_view.commit_slot
    assert other._stack.currentWidget() is other._result_view
    assert slot.isHidden() and slot.maximumHeight() == 0
    assert commit_panel_of(other) == []


# -- Phase 6 plan 06-08 Task 1: the dialog drives the whole commit step ---------------------------------

from PySide6.QtWidgets import QMessageBox, QScrollArea  # noqa: E402

from kicad_lib_manager.importer.commit_step import CommitOutcome, CommitProbe, SwitchOutcome  # noqa: E402
from kicad_lib_manager.importer.content import ContentText  # noqa: E402

D02_TEXT = "Not committed — commit manually: the imported files stay as uncommitted changes in Custom."


def fake_ready_probe(branch: str = "main", **fields):
    """A probe_commit fake that reports a ready Custom on `branch` and a ready parent."""

    def probe(cplan, **kwargs):
        return CommitProbe(
            state="ready", branch=branch, not_main=branch != "main",
            parent_dir=cplan.repo_root, parent_ok=True, parent_branch="main", **fields,
        )

    return probe


def fake_committed(text: str = "Committed abc1234 on main in Custom") -> CommitOutcome:
    done = Issue(Severity.SUCCESS, "commit.custom_done", text)
    return CommitOutcome(custom_commit="abc1234", custom_branch="main", issues=(done,))


def watch_logged(dialog: ImportDialog) -> list:
    """Every Issue the dialog sends to the log, in order."""
    logged: list = []
    dialog.issues_logged.connect(lambda issues: logged.extend(issues))
    return logged


def logged_codes(logged: list, code: str) -> list:
    return [issue for issue in logged if issue.code == code]


def gated(gates, started: threading.Event, make_value):
    """A fake that signals `started`, waits for a gate from the gates fixture, then returns make_value()."""

    def run(*args, **kwargs):
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        return make_value()

    return run


def test_commit_switch_flow(qtbot, make_install_dialog, gates):
    probes: list[int] = []
    started = threading.Event()

    def probe(cplan, **kwargs):
        probes.append(1)
        if len(probes) == 1:
            return CommitProbe(
                state="offer_switch", reason="Custom is on a detached HEAD at abc1234.", head="abc1234" + "0" * 33,
                parent_dir=cplan.repo_root, parent_ok=True, parent_branch="main",
            )
        return fake_ready_probe()(cplan)

    switched = SwitchOutcome(ok=True, issues=(Issue(Severity.SUCCESS, "commit.switched", "Switched Custom to main"),))
    dialog = make_install_dialog(probe_commit=probe, switch_to_main=gated(gates, started, lambda: switched))
    logged = watch_logged(dialog)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "offer_switch", timeout=30000)

    panel._switch_button.click()
    qtbot.waitUntil(lambda: started.is_set(), timeout=30000)
    assert panel.state() == "switching"
    assert dialog.is_committing()
    assert not dialog._result_view.close_button.isEnabled()

    gates[-1].set()
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    assert len(probes) == 2
    assert panel._branch_label.text() == "Custom branch: main"
    assert [i.text for i in logged_codes(logged, "commit.switched")] == ["Switched Custom to main"]
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    assert dialog._result_view.close_button.isEnabled()


def test_commit_switch_failure_shows_reason(qtbot, make_install_dialog):
    probes: list[int] = []
    commits: list[int] = []
    reason = "git refused to switch Custom to main; nothing was committed\nerror: Your local changes would be overwritten"

    def probe(cplan, **kwargs):
        probes.append(1)
        return CommitProbe(
            state="offer_switch", reason="Custom is on a detached HEAD at abc1234.", head="abc1234" + "0" * 33,
            parent_dir=cplan.repo_root, parent_ok=True, parent_branch="main",
        )

    def refuse(cplan, **kwargs):
        return SwitchOutcome(ok=False, issues=(Issue(Severity.ERROR, "commit.switch_failed", reason),), output="error")

    def count_commit(*args, **kwargs):
        commits.append(1)
        return fake_committed()

    dialog = make_install_dialog(probe_commit=probe, switch_to_main=refuse, run_commit=count_commit)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "offer_switch", timeout=30000)
    panel._switch_button.click()
    qtbot.waitUntil(lambda: bool(panel.outcome_lines()), timeout=30000)
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)

    assert panel.state() == "offer_switch"
    assert panel.outcome_lines()[0] == "✖ git refused to switch Custom to main; nothing was committed"
    assert len(probes) == 1
    assert commits == []
    assert not panel.committed()


def test_commit_unavailable_logged_once(qtbot, make_install_dialog):
    issue = Issue(Severity.WARNING, "commit.unavailable", "Commit unavailable: git was not found on PATH")

    def probe(cplan, **kwargs):
        return CommitProbe(state="unavailable", reason="git was not found on PATH", issues=(issue,))

    dialog = make_install_dialog(probe_commit=probe)
    logged = watch_logged(dialog)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "unavailable", timeout=30000)
    finish_workers(qtbot, dialog)

    found = logged_codes(logged, "commit.unavailable")
    assert [(i.severity, i.text) for i in found] == [(Severity.WARNING, "Commit unavailable: git was not found on PATH")]
    view = dialog._result_view
    assert view._banner.text() == "✓ Installed CSD85301Q2 into IC_Battery_Charger_TI"
    assert view._files_heading.text() == "Files written (3)"
    assert logged_codes(logged, "commit.not_committed") == []  # nothing closed yet


def test_commit_close_button_disabled_while_git_runs(qtbot, make_install_dialog, gates):
    started = threading.Event()
    calls: list[int] = []
    release = gated(gates, started, fake_committed)

    def counting_commit(*args, **kwargs):
        calls.append(1)
        return release()

    dialog = make_install_dialog(probe_commit=fake_ready_probe(), run_commit=counting_commit)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    assert dialog._result_view.close_button.isEnabled()

    panel.commit_button.click()
    qtbot.waitUntil(lambda: started.is_set() and dialog.is_committing(), timeout=30000)
    close_button = dialog._result_view.close_button
    assert not close_button.isEnabled()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    dialog.reject()
    dialog.close()
    assert dialog.isVisible()
    panel.commit_requested.emit("a second message", True)  # a second request while git runs is dropped
    qtbot.wait(100)
    assert calls == [1]

    gates[-1].set()
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    assert close_button.isEnabled()
    close_button.click()
    assert not dialog.isVisible()


def test_commit_passes_expected_branch(qtbot, make_install_dialog):
    seen: list[tuple] = []

    def record(cplan, message, bump, *, expected_branch=None, progress=None, git=None):
        seen.append((message, bump, expected_branch))
        return fake_committed()

    dialog = make_install_dialog(probe_commit=fake_ready_probe("feature/x"), run_commit=record)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    panel._message.setPlainText("My own message")
    panel._parent_check.setChecked(False)
    panel.commit_button.click()
    qtbot.waitUntil(lambda: panel.state() == "done", timeout=30000)
    assert seen == [("My own message", False, "feature/x")]


def test_commit_step_texts_shown(qtbot, make_install_dialog, gates):
    started = threading.Event()
    block = gated(gates, started, fake_committed)

    def stepping(cplan, message, bump, *, expected_branch=None, progress=None, git=None):
        progress("Committing in Custom...", 0, 2)
        return block()

    dialog = make_install_dialog(probe_commit=fake_ready_probe(), run_commit=stepping)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    panel.commit_button.click()
    qtbot.waitUntil(lambda: started.is_set(), timeout=30000)
    qtbot.waitUntil(lambda: panel._step.text() == "Committing in Custom...", timeout=30000)
    gates[-1].set()
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)


def forbid_message_boxes(monkeypatch):
    def refuse(*args, **kwargs):
        pytest.fail("a message box was opened")

    for name in ("exec", "exec_", "question", "warning", "information", "critical", "open", "show"):
        monkeypatch.setattr(QMessageBox, name, refuse, raising=False)


def test_commit_not_committed_logged_on_close(qtbot, make_install_dialog, monkeypatch):
    forbid_message_boxes(monkeypatch)
    dialog = make_install_dialog(probe_commit=fake_ready_probe())
    logged = watch_logged(dialog)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    assert logged_codes(logged, "commit.not_committed") == []

    dialog.close()
    dialog.reject()  # a second close path must not log it a second time
    assert not dialog.isVisible()
    found = logged_codes(logged, "commit.not_committed")
    assert [(i.severity, i.text) for i in found] == [(Severity.WARNING, D02_TEXT)]


def test_commit_not_logged_after_a_commit(qtbot, make_install_dialog, monkeypatch):
    forbid_message_boxes(monkeypatch)
    dialog = make_install_dialog(probe_commit=fake_ready_probe(), run_commit=lambda *a, **k: fake_committed())
    logged = watch_logged(dialog)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    panel.commit_button.click()
    qtbot.waitUntil(lambda: panel.state() == "done" and not dialog.is_committing(), timeout=30000)

    dialog._result_view.close_button.click()
    assert not dialog.isVisible()
    assert logged_codes(logged, "commit.not_committed") == []


def test_no_commit_step_for_noop_plan(qtbot, make_install_dialog, tmp_path):
    dialog = make_install_dialog()
    dialog._start_commit_step(types.SimpleNamespace(is_noop=True), fake_result(tmp_path))
    assert dialog._commit_panel is None
    assert commit_panel_of(dialog) == []
    assert dialog._result_view.commit_slot.isHidden()
    assert not dialog.is_committing()


def test_dirty_file_double_click_opens_diff(qtbot, make_install_dialog):
    rel = "Symbols/IC_Battery_Charger_TI.kicad_sym"
    title = f"Custom/{rel} - HEAD vs before this import"
    main_thread = threading.get_ident()
    seen: list[tuple] = []

    def diff(cplan, path, **kwargs):
        seen.append((path, threading.get_ident()))
        return ContentText(title=title, header="", body="-old\n+new", kind="diff")

    dialog = make_install_dialog(probe_commit=fake_ready_probe(dirty_before=frozenset({rel})), pre_import_diff=diff)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    files = panel._files_list
    item = next(files.item(i) for i in range(files.count()) if files.item(i).data(Qt.ItemDataRole.UserRole) == rel)
    files.itemActivated.emit(item)

    view = wait_view(qtbot, dialog)
    assert view.windowTitle() == title
    assert [path for path, _ in seen] == [rel]
    assert seen[0][1] != main_thread


@requires_git
def test_git_state_changes_only_after_click(qtbot, tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    before_install: list[list] = []
    before_click: list[list] = []
    after_click: list[list] = []
    state = {"installed": False, "clicked": False}
    real_run = subprocess.run

    def run(args, *a, **kw):
        argv = [str(part) for part in args] if isinstance(args, (list, tuple)) else [str(args)]
        if "git" in Path(argv[0]).name.lower():
            bucket = after_click if state["clicked"] else before_click if state["installed"] else before_install
            bucket.append(argv)
        return real_run(args, *a, **kw)

    def apply_then_flag(plan, *, backup_root=None, progress=None):
        result = real_apply_plan(plan, backup_root=backup_root, progress=progress)
        state["installed"] = True  # git may only start after this point
        return result

    monkeypatch.setattr(subprocess, "run", run)
    core = replace(
        ImportCore(),
        detect_tools=lambda kicad_fp_dir: ToolContext(),
        downloads_dir=lambda: None,
        suggest_library=_good_suggestion,
        kicad_running=lambda: [],
        apply_plan=apply_then_flag,
    )
    dialog = ImportDialog(
        repos.parent, RepoLayout.for_repo(repos.parent), core=core, backup_root=tmp_path / "backups"
    )
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.open_path(UL_ZIP)
    wait_current(qtbot, dialog)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)

    read_only = {
        "--version", "rev-parse", "symbolic-ref", "status", "merge-base", "rev-list", "log", "ls-tree",
        "cat-file", "var", "ls-files",
    }
    assert before_install == []
    assert before_click, "the probe should have run git"
    assert {argv[6] for argv in before_click} <= read_only
    assert after_click == []

    state["clicked"] = True
    panel.commit_button.click()
    qtbot.waitUntil(lambda: panel.state() == "done", timeout=60000)
    subcommands = {argv[6] for argv in after_click}
    assert {"add", "commit"} <= subcommands
    assert not [argv for argv in before_click + after_click if "push" in argv]


def test_result_view_scrolls_at_minimum_size(qtbot, make_install_dialog):
    earlier = tuple((f"abc{n:04d}", f"Earlier Custom commit number {n}") for n in range(10))
    probe = fake_ready_probe(gitlink_old="485d530" + "0" * 33, earlier=earlier)
    dialog = make_install_dialog(probe_commit=probe)
    dialog.resize(900, 600)
    install_ul(qtbot, dialog)
    (panel,) = commit_panel_of(dialog)
    qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    dialog.resize(900, 600)
    qtbot.wait(100)

    view = dialog._result_view
    (scroll,) = view.findChildren(QScrollArea)
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.widgetResizable()
    body = scroll.widget()
    assert body.width() <= scroll.viewport().width()
    assert body.minimumSizeHint().width() <= scroll.viewport().width()
    assert body.height() > scroll.viewport().height()
    assert scroll.verticalScrollBar().maximum() > 0
    assert view.close_button.isVisible()
    assert not scroll.isAncestorOf(view.close_button)
    assert scroll.isAncestorOf(view.commit_slot)


# -- Phase 6 plan 06-08 Task 2: WR-04, no worker reads dialog state and no package opens under a job -----


@pytest.mark.parametrize("job", ["commit", "install"])
def test_open_path_refused_while_busy(qtbot, make_install_dialog, gates, job):
    started = threading.Event()
    if job == "commit":
        dialog = make_install_dialog(probe_commit=fake_ready_probe(), run_commit=gated(gates, started, fake_committed))
        install_ul(qtbot, dialog)
        (panel,) = commit_panel_of(dialog)
        qtbot.waitUntil(lambda: panel.state() == "ready", timeout=30000)
        qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
        panel.commit_button.click()
        qtbot.waitUntil(lambda: started.is_set() and dialog.is_committing(), timeout=30000)
        page = dialog._result_page
    else:
        dialog = make_install_dialog(apply_plan=blocking_apply(gates, started=started))
        dialog._install_btn.click()
        qtbot.waitUntil(lambda: started.is_set() and dialog.is_installing(), timeout=30000)
        page = dialog._edit_page

    dialog.open_path(UL_ZIP)  # a new package must not open under a running job
    assert dialog._open_worker is None
    assert dialog._stack.currentWidget() is page
    gates[-1].set()
    qtbot.waitUntil(lambda: not dialog.is_installing() and not dialog.is_committing(), timeout=60000)


def test_install_worker_uses_captured_plan(qtbot, make_install_dialog, gates, monkeypatch):
    main_thread = threading.get_ident()
    off_thread_reads: list[str] = []

    def get_plan(self):
        if threading.get_ident() != main_thread:
            off_thread_reads.append(threading.current_thread().name)
        return self.__dict__.get("_plan_slot")

    def set_plan(self, value):
        self.__dict__["_plan_slot"] = value

    monkeypatch.setattr(ImportDialog, "_plan", property(get_plan, set_plan), raising=False)
    seen: list = []
    started = threading.Event()

    def apply(plan, *, backup_root=None, progress=None):
        seen.append(plan)
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        return real_apply_plan(plan, backup_root=backup_root, progress=progress)

    dialog = make_install_dialog(apply_plan=apply)
    rendered = dialog._plan
    assert rendered is not None
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: started.is_set(), timeout=30000)
    dialog._plan = None  # the GUI may change its own state while the worker runs
    gates[-1].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)

    assert len(seen) == 1 and seen[0] is rendered
    assert off_thread_reads == []


# -- Add 3D model... (plan 07-07, G-07-2): a separately downloaded SnapEDA model joins an open import -----


def test_add_model_tracer_snapeda_end_to_end(qtbot, make_item_dialog, item_layout, recorded, tmp_path, monkeypatch):
    from vendorfixtures import (
        SNAPEDA_FOOTPRINT,
        SNAPEDA_MODEL_STEM,
        SNAPEDA_MODEL_ZIP_NAME,
        SNAPEDA_MPN,
        SNAPEDA_SYMBOL,
        snapeda_model_zip,
        snapeda_zip,
    )
    from zipfixtures import STEP_BYTES

    from kicad_lib_manager.importer.plan import MODEL_DIR_VAR
    from kicad_lib_manager.kicad_files import find_models, footprint_name, load

    dialog = make_item_dialog(snapeda_zip(tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip"), show=True)
    wait_current(qtbot, dialog)
    assert dialog._model_label.full_text() == "No 3D model in this package"
    assert dialog._add_model_btn.text() == "Add 3D model..."

    model_zip = snapeda_model_zip(tmp_path / "dl" / SNAPEDA_MODEL_ZIP_NAME)
    filters: list[str] = []

    def fake_open_file(parent, caption, directory, file_filter):
        filters.append(file_filter)
        return str(model_zip), ""

    monkeypatch.setattr(import_dialog_module.QFileDialog, "getOpenFileName", staticmethod(fake_open_file))
    dialog._add_model_btn.click()
    qtbot.waitUntil(lambda: dialog._model_worker is None and len(dialog._candidate.models) == 1, timeout=30000)
    wait_current(qtbot, dialog)

    filename = f"{SNAPEDA_MODEL_STEM}.stp"
    assert dialog._model_label.full_text() == filename
    assert recorded[-1].model == filename
    assert dialog._plan.model_file == f"{SNAPEDA_MPN}.stp"
    codes = [i.code for i in dialog._plan.issues]
    assert "intake.model_attached" in codes
    assert "intake.no_model" not in codes and "install.no_model" not in codes
    _title, rows = files_rows(dialog)
    assert any(row.endswith(f"{SNAPEDA_MPN}.stp") for row in rows), rows
    for suffix in ("*.step", "*.stp", "*.wrl", "*.zip"):
        assert suffix in filters[-1]

    set_library(dialog, "Connector_USB_GCT")
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    staging = dialog._model_packages[-1].staging_dir
    assert staging is not None and staging.is_dir()
    with qtbot.waitSignal(dialog.installed, timeout=60000):
        dialog._install_btn.click()
    assert dialog.result.ok
    assert (item_layout.models_dir / f"{SNAPEDA_MPN}.stp").read_bytes() == STEP_BYTES
    installed = item_layout.footprints_dir / "Connector_USB_GCT.pretty" / f"{SNAPEDA_FOOTPRINT}.kicad_mod"
    loaded = load(installed)
    ref = footprint_name(loaded.root)
    assert ref is not None
    assert [m.path for m in find_models(ref.node)] == [f"{MODEL_DIR_VAR}/{SNAPEDA_MPN}.stp"]

    qtbot.waitUntil(lambda: not dialog.is_committing(), timeout=30000)
    dialog.reject()
    assert not staging.exists()


# -- Add 3D model... from every row state (plan 07-08, G-07-2) ------------------------------------------


def pick_model(monkeypatch, *paths) -> None:
    """Make the file dialog return these paths in order."""
    queue = list(paths)

    def fake_open_file(parent, caption, directory, file_filter):
        return str(queue.pop(0)), ""

    monkeypatch.setattr(import_dialog_module.QFileDialog, "getOpenFileName", staticmethod(fake_open_file))


def attach_model(qtbot, dialog: ImportDialog, monkeypatch, path: Path) -> None:
    """Click Add 3D model..., pick path, wait for the worker and for the plan that follows."""
    pick_model(monkeypatch, path)
    dialog._add_model_btn.click()
    qtbot.waitUntil(lambda: dialog._model_worker is None, timeout=30000)
    wait_current(qtbot, dialog)


def bare_model(folder: Path, name: str, data: bytes | None = None) -> Path:
    from zipfixtures import STEP_BYTES

    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(STEP_BYTES if data is None else data)
    return path


def model_names(dialog: ImportDialog) -> list[str]:
    combo = dialog._model_combo
    return [combo.itemText(i) for i in range(combo.count())]


def test_add_model_button_on_every_row_state(qtbot, make_item_dialog, tmp_path):
    one = ul_dialog(make_item_dialog, qtbot)
    assert one._model_label is not None and one._model_combo is None
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    several = make_item_dialog(multi_zip(tmp_path / "a"), show=True)
    wait_current(qtbot, several)
    assert several._model_combo is not None and model_names(several)[-1] == "No model"
    none = make_item_dialog(multi_zip(tmp_path / "b", models=()), show=True)
    wait_current(qtbot, none)
    assert none._model_label is not None and none._model_label.full_text() == "No 3D model in this package"
    for dialog in (one, several, none):
        assert dialog._add_model_btn is not None
        assert dialog._add_model_btn.isEnabled()
        assert dialog._add_model_btn.text() == import_dialog_module.ADD_MODEL_TEXT


def test_add_model_to_part_with_model_selects_it(qtbot, make_item_dialog, recorded, tmp_path, monkeypatch):
    dialog = ul_dialog(make_item_dialog, qtbot)
    before = len(recorded)
    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl", "other.stp"))
    assert dialog._model_combo is not None
    assert model_names(dialog) == ["DLV0006A.stp", "other.stp", "No model"]
    assert dialog._model_combo.currentIndex() == 1
    assert recorded[-1].model == "other.stp"
    assert len(recorded) == before + 1  # exactly one rebuild for the attach
    assert dialog._plan.model_file == "CSD85301Q2.stp"
    assert dialog._model_note.isHidden()

    # a third model joins the combo and is selected in turn
    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl2", "third.step", b"ISO-10303-21;\nthird\n"))
    assert model_names(dialog) == ["DLV0006A.stp", "other.stp", "third.step", "No model"]
    assert dialog._model_combo.currentIndex() == 2
    assert recorded[-1].model == "third.step"


def test_add_model_clash_listed_with_suffix(qtbot, make_item_dialog, tmp_path, monkeypatch):
    from zipfixtures import STEP_BYTES

    dialog = ul_dialog(make_item_dialog, qtbot)
    clash = bare_model(tmp_path / "dl", "dlv0006a.STP", STEP_BYTES.replace(b"test", b"nope"))
    attach_model(qtbot, dialog, monkeypatch, clash)
    assert "dlv0006a_2.STP" in model_names(dialog)
    assert dialog._model_combo.currentText() == "dlv0006a_2.STP"


def test_add_model_keeps_edits(qtbot, make_item_dialog, recorded, tmp_path, monkeypatch):
    dialog = ul_dialog(make_item_dialog, qtbot)
    type_text(qtbot, dialog._field_edits["value"], "MyValue")
    type_text(qtbot, dialog._field_edits["description"], "My description")
    type_text(qtbot, dialog._fp_name_edit, "MYFP")
    type_text(qtbot, dialog._library_combo.lineEdit(), "Typed_Lib_X")
    wait_current(qtbot, dialog)
    texts = {
        "value": dialog._field_edits["value"].text(),
        "description": dialog._field_edits["description"].text(),
        "fp_name": dialog._fp_name_edit.text(),
        "library": dialog._library_combo.currentText(),
    }
    assert texts["library"] == "Typed_Lib_X"
    edited, fp_edited, resolutions = set(dialog._edited), dialog._fp_name_edited, dict(dialog._resolutions)
    assert fp_edited and {"value", "description"} <= edited

    calls: list[str] = []
    for name in ("_populate_items", "_reload_symbol_defaults", "_clear_items", "_clear_form", "_reset_fp_name"):
        original = getattr(dialog, name)

        def counting(*args, _original=original, _name=name, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        setattr(dialog, name, counting)

    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl", "other.stp"))
    assert calls == []
    assert dialog._field_edits["value"].text() == texts["value"]
    assert dialog._field_edits["description"].text() == texts["description"]
    assert dialog._fp_name_edit.text() == texts["fp_name"]
    assert dialog._library_combo.currentText() == texts["library"]
    assert dialog._edited == edited
    assert dialog._fp_name_edited is fp_edited
    assert dialog._resolutions == resolutions
    last = recorded[-1]
    assert last.value == "MyValue" and last.description == "My description"
    assert dict(last.footprint_names) == {"DQK0006B": "MYFP"}
    assert last.library == "Typed_Lib_X"
    assert last.model == "other.stp"


def test_add_model_rejection_blocks_install(qtbot, make_item_dialog, tmp_path, monkeypatch):
    """G-07-5 tracer: an unusable bare model file is a red error that blocks Install until Remove."""
    dialog = ul_dialog(make_item_dialog, qtbot)
    assert dialog._install_btn.isEnabled()
    candidate, gen = dialog._candidate, dialog._gen
    text = "dummy_CAD_FILE.step holds no usable 3D model"

    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl", "dummy_CAD_FILE.step", b""))
    assert dialog._candidate is candidate and dialog._model_packages == []
    assert dialog._gen == gen
    note = dialog._model_note
    assert note.isVisible() and note.textFormat() == Qt.TextFormat.PlainText
    assert ERROR.lower() in note.styleSheet().lower()
    assert note.text() == text
    links = strip_links(dialog)
    assert f"Error: {text}" in links
    assert not dialog._install_btn.isEnabled()
    rejection = dialog._model_rejection
    assert rejection is not None and rejection.source == "dummy_CAD_FILE.step"
    assert rejection.issue.code == "intake.no_model_in_source"
    remove = dialog._remove_model_btn
    assert remove.isVisible() and remove.isEnabled()
    assert remove.text() == import_dialog_module.REMOVE_MODEL_TEXT
    assert dialog._add_model_btn.isEnabled()
    dialog._strip.linkActivated.emit(links[f"Error: {text}"])
    assert dialog.focusWidget() is remove

    remove.click()
    assert note.isHidden() and remove.isHidden()
    assert not any(reason.startswith("Error:") for reason in strip_links(dialog))
    assert dialog._model_rejection is None
    # Moving the focus off the editable library combo re-activates it, which rebuilds the plan once
    wait_current(qtbot, dialog)
    assert dialog._install_btn.isEnabled()
    assert dialog._strip.text().startswith("✓ Ready to install")


def test_add_model_refusal_shows_note(qtbot, make_item_dialog, tmp_path, monkeypatch):
    from zipfixtures import make_zip

    opened: list = []

    def open_recording(path, repo_root, progress=None):
        package = import_dialog_module.open_model_source(path, repo_root, progress)
        opened.append((package, package.staging_dir))
        return package

    dialog = make_item_dialog(
        multi_zip(tmp_path, symbols=("S1",), footprints=("F1",), models=()), show=True, open_model_source=open_recording
    )
    wait_current(qtbot, dialog)
    candidate = dialog._candidate
    logged: list = []
    dialog.issues_logged.connect(logged.append)
    assert dialog._model_note.isHidden()

    def assert_refused(source: Path) -> str:
        attach_model(qtbot, dialog, monkeypatch, source)
        assert dialog._candidate is candidate
        assert dialog._model_label.full_text() == "No 3D model in this package"
        assert dialog._model_combo is None and dialog._model_packages == []
        note = dialog._model_note
        assert note.isVisible()
        assert note.textFormat() == Qt.TextFormat.PlainText
        assert ERROR.lower() in note.styleSheet().lower()
        errors = [i for i in logged[-1] if i.severity is Severity.ERROR]
        assert errors and "intake.no_model_in_source" in {i.code for i in errors}
        assert note.text() == errors[0].text
        # G-07-5: the rejection blocks Install and is listed in the strip
        assert strip_links(dialog).get(f"Error: {note.text()}", "").startswith("reason:")
        assert not dialog._install_btn.isEnabled()
        assert dialog._model_rejection is not None
        return note.text()

    # a zip with no model at all: refused at intake
    assert_refused(make_zip(tmp_path / "notes.zip", [("readme.txt", b"hello")]))
    # a renamed non-STEP file in a zip: staged, then refused by the magic check; the staging folder goes
    first = assert_refused(make_zip(tmp_path / "fake.zip", [("fake.stp", b"this is not a STEP file")]))
    package, staging = opened[-1]
    assert staging is not None and not staging.exists() and package.staging_dir is None
    # a bare renamed file
    second = assert_refused(bare_model(tmp_path / "dl", "fake.stp", b"not a step file either"))
    assert "fake.stp" in second and first != second


def test_add_model_note_is_plain_text(qtbot, make_item_dialog, tmp_path, monkeypatch):
    from kicad_lib_manager.importer.package import Package

    hostile = "Refused <b>x</b>.stp &amp; <i>y</i>"

    def refusing(path, repo_root, progress=None):
        package = Package(Path(path), "file")
        package.issues.append(Issue(Severity.ERROR, "intake.unsupported", hostile))
        return package

    dialog = make_item_dialog(
        multi_zip(tmp_path, symbols=("S1",), footprints=("F1",), models=()), show=True, open_model_source=refusing
    )
    wait_current(qtbot, dialog)
    attach_model(qtbot, dialog, monkeypatch, tmp_path / "anything.stp")
    note = dialog._model_note
    assert note.isVisible() and note.textFormat() == Qt.TextFormat.PlainText
    assert note.text() == hostile
    assert note.wordWrap()
    # the strip shows the same text escaped, never as markup (T-05-27, T-07-34)
    assert "&lt;b&gt;x&lt;/b&gt;" in dialog._strip.text()
    assert "<b>x</b>" not in dialog._strip.text()


def test_add_model_duplicate_is_noted(qtbot, make_item_dialog, tmp_path, monkeypatch):
    dialog = make_item_dialog(
        multi_zip(tmp_path, symbols=("S1",), footprints=("F1",), models=()), show=True
    )
    wait_current(qtbot, dialog)
    model = bare_model(tmp_path / "dl", "same.stp")
    attach_model(qtbot, dialog, monkeypatch, model)
    assert len(dialog._candidate.models) == 1
    assert dialog._model_label.full_text() == "same.stp"
    candidate, gen = dialog._candidate, dialog._gen

    attach_model(qtbot, dialog, monkeypatch, model)
    note = dialog._model_note
    assert note.isVisible() and "already listed" in note.text()
    assert MUTED.lower() in note.styleSheet().lower()
    assert dialog._candidate is candidate and len(dialog._candidate.models) == 1
    assert dialog._gen == gen


# -- Add 3D model... is busy-safe and every model package lives as long as it must (plan 07-08) ---------


def model_zip(folder: Path, name: str = "model.zip", member: str = "extra.stp") -> Path:
    from zipfixtures import STEP_BYTES, make_zip

    folder.mkdir(parents=True, exist_ok=True)
    return make_zip(folder / name, [(member, STEP_BYTES)])


def gated_model_source(gates, started=None, events=None, packages=None):
    """An open_model_source fake that waits for a gate, opens the real package and spies on its close."""

    def open_source(path, repo_root, progress=None):
        gate = threading.Event()
        gates.append(gate)
        if started is not None:
            started.set()
        assert gate.wait(30)
        package = import_dialog_module.open_model_source(path, repo_root, progress)
        original = package.close
        package.staging_at_open = package.staging_dir
        if packages is not None:
            packages.append(package)

        def close():
            if events is not None:
                events.append("close")
            original()

        package.close = close
        return package

    return open_source


def test_add_model_blocks_install_while_reading(qtbot, make_item_dialog, gates, tmp_path, monkeypatch):
    from kicad_lib_manager.importer.form import UPDATING_REASON

    started = threading.Event()
    dialog = ul_dialog(make_item_dialog, qtbot, open_model_source=gated_model_source(gates, started))
    assert dialog._install_btn.isEnabled()
    pick_model(monkeypatch, model_zip(tmp_path / "dl"))
    dialog._add_model_btn.click()
    qtbot.waitUntil(started.is_set, timeout=30000)
    assert not dialog._add_model_btn.isEnabled()
    assert not dialog._install_btn.isEnabled()
    assert dialog._strip.text() == UPDATING_REASON
    assert dialog._model_note.isVisible() and dialog._model_note.text().startswith("Reading ")

    gates[-1].set()
    qtbot.waitUntil(lambda: dialog._model_worker is None, timeout=30000)
    wait_current(qtbot, dialog)
    assert dialog._add_model_btn.isEnabled()
    assert dialog._model_note.isHidden()
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    assert dialog._plan.model_file == "CSD85301Q2.stp"


def test_add_model_result_after_change_is_dropped(qtbot, make_item_dialog, gates, tmp_path, monkeypatch):
    started = threading.Event()
    events: list[str] = []
    packages: list = []
    dialog = ul_dialog(
        make_item_dialog, qtbot, open_model_source=gated_model_source(gates, started, events, packages)
    )
    pick_model(monkeypatch, model_zip(tmp_path / "dl"))
    dialog._add_model_btn.click()
    qtbot.waitUntil(started.is_set, timeout=30000)
    dialog._change_btn.click()
    assert dialog._stack.currentWidget() is dialog._start_page

    gates[-1].set()
    qtbot.waitUntil(lambda: dialog._model_worker is None, timeout=30000)
    assert events == ["close"]
    staging = packages[0].staging_at_open
    assert staging is not None and not staging.exists()
    assert dialog._model_packages == []
    assert dialog._candidate is None
    assert dialog._stack.currentWidget() is dialog._start_page


def test_add_model_close_while_reading_closes_package(qtbot, make_item_dialog, gates, tmp_path, monkeypatch):
    started = threading.Event()
    events: list[str] = []
    packages: list = []
    dialog = ul_dialog(
        make_item_dialog, qtbot, open_model_source=gated_model_source(gates, started, events, packages)
    )
    pick_model(monkeypatch, model_zip(tmp_path / "dl"))
    dialog._add_model_btn.click()
    qtbot.waitUntil(started.is_set, timeout=30000)
    threading.Timer(0.3, gates[-1].set).start()
    began = time.monotonic()
    dialog.reject()
    assert time.monotonic() - began >= 0.2
    qtbot.wait(100)  # a queued result must not close the package a second time
    assert events == ["close"]
    assert dialog._model_packages == []
    staging = packages[0].staging_at_open
    assert staging is not None and not staging.exists()


def test_add_model_package_open_until_install_ends(qtbot, make_install_dialog, gates, tmp_path, monkeypatch):
    events: list[str] = []
    packages: list = []
    seen: dict = {}
    started = threading.Event()

    def apply(plan, *, backup_root=None, progress=None):
        sources = [op.source.path for op in plan.ops if op.source is not None]
        seen["exist"] = [path.exists() for path in sources]
        seen["sources"] = sources
        events.append("apply_start")
        started.set()
        result = real_apply_plan(plan, backup_root=backup_root, progress=progress)
        events.append("apply_end")
        return result

    def open_source(path, repo_root, progress=None):
        package = import_dialog_module.open_model_source(path, repo_root, progress)
        original = package.close

        def close():
            events.append("close")
            original()

        package.close = close
        packages.append(package)
        return package

    dialog = make_install_dialog(apply_plan=apply, open_model_source=open_source)
    attach_model(qtbot, dialog, monkeypatch, model_zip(tmp_path / "dl"))
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    staging = packages[0].staging_dir
    assert staging is not None and staging.is_dir()
    with qtbot.waitSignal(dialog.installed, timeout=60000):
        dialog._install_btn.click()
    assert seen["exist"] and all(seen["exist"])
    assert any(staging in path.parents for path in seen["sources"])  # the install read the model package
    qtbot.waitUntil(lambda: not dialog.is_installing() and not dialog.is_committing(), timeout=30000)
    assert staging.is_dir() and "close" not in events  # still open after apply_plan returned

    dialog.reject()
    assert not staging.exists()
    assert events.index("apply_end") < events.index("close")
    assert events.count("close") == 1


def test_add_model_change_closes_model_package(qtbot, make_item_dialog, tmp_path, monkeypatch):
    dialog = ul_dialog(make_item_dialog, qtbot)
    attach_model(qtbot, dialog, monkeypatch, model_zip(tmp_path / "dl"))
    assert len(dialog._model_packages) == 1
    staging = dialog._model_packages[0].staging_dir
    assert staging is not None and staging.is_dir()
    dialog._change_btn.click()
    assert not staging.exists()
    assert dialog._model_packages == []


def test_add_model_disabled_while_installing(qtbot, make_install_dialog, gates):
    started = threading.Event()
    dialog = make_install_dialog(apply_plan=blocking_apply(gates, started=started))
    assert dialog._add_model_btn.isEnabled()
    dialog._install_btn.click()
    qtbot.waitUntil(lambda: started.is_set() and dialog.is_installing(), timeout=30000)
    assert not dialog._add_model_btn.isEnabled()
    assert dialog._model_busy()
    gates[-1].set()
    qtbot.waitUntil(lambda: dialog.result is not None, timeout=60000)
    qtbot.waitUntil(lambda: not dialog.is_installing() and not dialog.is_committing(), timeout=30000)


def test_add_model_runs_off_gui_thread(qtbot, make_item_dialog, tmp_path, monkeypatch):
    from kicad_lib_manager.importer.adapters.base import attach_models as real_attach_models

    main = threading.get_ident()
    seen: dict[str, int] = {}

    def spy(name, fn):
        def wrapper(*args, **kwargs):
            seen[name] = threading.get_ident()
            return fn(*args, **kwargs)

        return wrapper

    dialog = ul_dialog(
        make_item_dialog,
        qtbot,
        open_model_source=spy("open_model_source", import_dialog_module.open_model_source),
        attach_models=spy("attach_models", real_attach_models),
    )
    attach_model(qtbot, dialog, monkeypatch, model_zip(tmp_path / "dl"))
    assert set(seen) == {"open_model_source", "attach_models"}
    assert all(ident != main for ident in seen.values())


def test_add_model_worker_failure_logged(qtbot, make_item_dialog, tmp_path, monkeypatch):
    def broken(path, repo_root, progress=None):
        raise RuntimeError("disk on fire")

    dialog = ul_dialog(make_item_dialog, qtbot, open_model_source=broken)
    candidate = dialog._candidate
    logged: list = []
    dialog.issues_logged.connect(logged.append)
    attach_model(qtbot, dialog, monkeypatch, tmp_path / "anything.stp")
    assert [i.code for i in logged[-1]] == ["import.step_failed"]
    assert logged[-1][0].severity is Severity.ERROR
    note = dialog._model_note
    assert note.isVisible() and "disk on fire" in note.text()
    assert ERROR.lower() in note.styleSheet().lower()
    # G-07-5: a failed read is held as a rejected source and blocks Install like any other
    # the worker reports "RuntimeError: disk on fire"; the reason carries the logged Issue text unchanged
    assert f"Error: {logged[-1][0].text}" in strip_links(dialog)
    assert logged[-1][0].text == "Import step failed: RuntimeError: disk on fire"
    assert not dialog._install_btn.isEnabled()
    remove = dialog._remove_model_btn
    assert remove.isVisible() and remove.isEnabled()
    assert dialog._add_model_btn.isEnabled()
    assert dialog._candidate is candidate

    remove.click()
    wait_current(qtbot, dialog)
    assert dialog._model_rejection is None
    assert dialog._install_btn.isEnabled()


def test_add_model_partly_bad_zip_rejected(qtbot, make_item_dialog, tmp_path, monkeypatch):
    from zipfixtures import STEP_BYTES, make_zip

    opened: list = []

    def open_recording(path, repo_root, progress=None):
        package = import_dialog_module.open_model_source(path, repo_root, progress)
        opened.append((package, package.staging_dir))
        return package

    dialog = ul_dialog(make_item_dialog, qtbot, open_model_source=open_recording)
    candidate = dialog._candidate
    (tmp_path / "dl").mkdir()
    source = make_zip(tmp_path / "dl" / "two.zip", [("good.stp", STEP_BYTES), ("bad.step", b"MZ not a model")])
    attach_model(qtbot, dialog, monkeypatch, source)
    assert dialog._candidate is candidate
    assert dialog._model_label.full_text() == "DLV0006A.stp" and dialog._model_combo is None
    assert dialog._model_packages == []
    note = dialog._model_note
    assert note.isVisible() and "bad.step" in note.text()
    assert ERROR.lower() in note.styleSheet().lower()
    assert any(reason.startswith("Error:") and "bad.step" in reason for reason in strip_links(dialog))
    assert not dialog._install_btn.isEnabled()
    package, staging = opened[-1]
    assert staging is not None and not staging.exists() and package.staging_dir is None


def test_add_model_success_clears_rejection(qtbot, make_item_dialog, tmp_path, monkeypatch):
    dialog = ul_dialog(make_item_dialog, qtbot)
    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl", "dummy.step", b""))
    assert dialog._model_rejection is not None and not dialog._install_btn.isEnabled()

    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl2", "other.stp"))
    assert dialog._model_rejection is None
    assert dialog._model_note.isHidden() and dialog._remove_model_btn.isHidden()
    assert dialog._model_combo is not None and dialog._model_combo.currentText() == "other.stp"
    assert not any(reason.startswith("Error:") for reason in strip_links(dialog))
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)


def test_add_model_duplicate_keeps_rejection(qtbot, make_item_dialog, tmp_path, monkeypatch):
    dialog = make_item_dialog(multi_zip(tmp_path, symbols=("S1",), footprints=("F1",), models=()), show=True)
    wait_current(qtbot, dialog)
    same = bare_model(tmp_path / "dl", "same.stp")
    attach_model(qtbot, dialog, monkeypatch, same)
    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl2", "dummy.step", b""))
    rejection = dialog._model_rejection
    assert rejection is not None
    logged: list = []
    dialog.issues_logged.connect(logged.append)

    attach_model(qtbot, dialog, monkeypatch, same)
    assert any(i.code == "intake.model_already_present" and i.severity is Severity.INFO for i in logged[-1])
    assert dialog._model_rejection is rejection
    note = dialog._model_note
    assert note.isVisible() and note.text() == rejection.issue.text
    assert ERROR.lower() in note.styleSheet().lower()
    assert dialog._remove_model_btn.isVisible()
    assert f"Error: {rejection.issue.text}" in strip_links(dialog)


def test_add_model_rejection_reset_by_change(qtbot, make_item_dialog, tmp_path, monkeypatch):
    dialog = ul_dialog(make_item_dialog, qtbot)
    attach_model(qtbot, dialog, monkeypatch, bare_model(tmp_path / "dl", "dummy.step", b""))
    assert dialog._model_rejection is not None

    dialog._change_btn.click()
    assert dialog._model_rejection is None
    dialog.open_path(UL_ZIP)
    wait_current(qtbot, dialog)
    assert dialog._remove_model_btn.isHidden()
    assert not any(reason.startswith("Error:") for reason in strip_links(dialog))
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)


def test_add_model_stale_failure_does_not_block(qtbot, make_item_dialog, gates, tmp_path, monkeypatch):
    started = threading.Event()

    def failing_after_gate(path, repo_root, progress=None):
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        raise RuntimeError("late failure")

    dialog = ul_dialog(make_item_dialog, qtbot, open_model_source=failing_after_gate)
    logged: list = []
    dialog.issues_logged.connect(logged.append)
    pick_model(monkeypatch, tmp_path / "anything.stp")
    dialog._add_model_btn.click()
    qtbot.waitUntil(started.is_set, timeout=30000)
    dialog._change_btn.click()
    dialog.open_path(UL_ZIP)
    wait_current(qtbot, dialog)

    gates[-1].set()
    qtbot.waitUntil(lambda: dialog._model_worker is None, timeout=30000)
    wait_current(qtbot, dialog)
    assert [i.code for i in logged[-1]] == ["import.step_failed"]  # logged, nothing more
    assert dialog._model_rejection is None
    assert dialog._model_note.isHidden() and dialog._remove_model_btn.isHidden()
    assert not any(reason.startswith("Error:") for reason in strip_links(dialog))
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)


def test_add_model_remove_disabled_while_reading(qtbot, make_item_dialog, gates, tmp_path, monkeypatch):
    from kicad_lib_manager.importer.form import UPDATING_REASON

    started = threading.Event()
    dialog = ul_dialog(make_item_dialog, qtbot, open_model_source=gated_model_source(gates, started))
    pick_model(monkeypatch, bare_model(tmp_path / "dl", "dummy.step", b""))
    dialog._add_model_btn.click()
    qtbot.waitUntil(started.is_set, timeout=30000)
    gates[-1].set()
    qtbot.waitUntil(lambda: dialog._model_rejection is not None, timeout=30000)
    qtbot.waitUntil(lambda: dialog._model_worker is None, timeout=30000)

    started.clear()
    pick_model(monkeypatch, model_zip(tmp_path / "dl2"))
    dialog._add_model_btn.click()
    qtbot.waitUntil(started.is_set, timeout=30000)
    assert dialog._remove_model_btn.isVisible()
    assert not dialog._remove_model_btn.isEnabled() and not dialog._add_model_btn.isEnabled()
    assert dialog._strip.text() == UPDATING_REASON

    gates[-1].set()
    qtbot.waitUntil(lambda: dialog._model_worker is None, timeout=30000)
    wait_current(qtbot, dialog)
    assert dialog._model_rejection is None
    assert dialog._remove_model_btn.isHidden()
    assert dialog._add_model_btn.isEnabled()


# -- Preview columns (plan 07-11, G-07-7): Item is draggable, Detail fills the rest and elides ---------------


def test_preview_columns_fit_at_900_and_1400(qtbot, make_item_dialog, tmp_path):
    from PySide6.QtWidgets import QHeaderView
    from vendorfixtures import SNAPEDA_SYMBOL, snapeda_zip

    from kicad_lib_manager.widgets.preview_tree import MIN_COLUMN_WIDTH

    dialog = make_item_dialog(snapeda_zip(tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip"), show=True)
    wait_current(qtbot, dialog)
    assert "Field changes" in [s.name for s in dialog._preview.sections]
    tree = dialog._preview
    assert tree.header().sectionResizeMode(0) == QHeaderView.ResizeMode.Interactive
    assert tree.header().stretchLastSection()

    for width in (900, 1400):
        dialog.resize(width, 720)
        qtbot.waitUntil(lambda: dialog.width() == width)
        qtbot.wait(50)
        viewport = tree.viewport().width()
        if width == 900:
            # The UAT precondition: the Field changes Detail text is wider than the viewport
            assert tree.sizeHintForColumn(1) > viewport
        assert tree.columnWidth(0) >= MIN_COLUMN_WIDTH, (width, tree.columnWidth(0))
        assert tree.columnWidth(1) >= MIN_COLUMN_WIDTH, (width, tree.columnWidth(1))
        assert tree.columnWidth(0) + tree.columnWidth(1) <= viewport + 1, (width, viewport)


def drag_divider(header, dx):
    """Press on the Item|Detail divider, move by dx and release, like a user drag."""
    y = header.height() // 2
    x = header.sectionViewportPosition(0) + header.sectionSize(0) - 1
    viewport = header.viewport()
    no_modifier = Qt.KeyboardModifier.NoModifier
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, no_modifier, QPoint(x, y))
    QTest.mouseMove(viewport, QPoint(x + dx, y))
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, no_modifier, QPoint(x + dx, y))


def test_preview_column_drag_survives_rebuild(qtbot, make_item_dialog):
    dialog = ul_dialog(make_item_dialog, qtbot)
    tree = dialog._preview
    before = tree.columnWidth(0)
    drag_divider(tree.header(), -60)
    dragged = tree.columnWidth(0)
    assert abs(dragged - (before - 60)) <= 2, (before, dragged)

    gen = dialog._gen
    dialog._request_rebuild()
    wait_current(qtbot, dialog)
    assert dialog._gen > gen
    assert tree.columnWidth(0) == dragged

    type_text(qtbot, dialog._field_edits["value"], "Changed value")
    wait_current(qtbot, dialog)
    assert tree.columnWidth(0) == dragged

    detail = tree.columnWidth(1)
    dialog.resize(1400, 720)
    qtbot.waitUntil(lambda: dialog.width() == 1400)
    qtbot.wait(50)
    assert tree.columnWidth(0) == dragged
    assert tree.columnWidth(1) > detail
