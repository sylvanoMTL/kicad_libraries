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
    assert "not a .zip file" in dialog._start_issues.text()
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
    (files,) = preview_sections(plan, candidate, options)
    assert files.title == "Files (3)"
    assert [r.text for r in files.rows] == [
        "+ Custom/3DModels/CSD85301Q2.stp",
        "+ Custom/Footprints/IC_Battery_Charger_TI.pretty/DQK0006B.kicad_mod",
        "~ Custom/Symbols/IC_Battery_Charger_TI.kicad_sym",
    ]
    assert [r.detail for r in files.rows] == ["new", "new", "modified"]
    assert [r.op_index for r in files.rows] == [0, 1, 2]
    counts = file_counts(plan, candidate, options)
    assert (counts.new, counts.modified, counts.unchanged) == (2, 1, 0)

    fresh = real_build_plan(candidate, replace(options, library="A_x_TI"), custom_copy)
    (fresh_files,) = preview_sections(fresh, candidate, options)
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
