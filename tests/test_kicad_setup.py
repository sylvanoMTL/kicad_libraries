"""The chooser setup of TBL-02 (kicad_setup.py) on synthetic trees.

Nothing here touches the owner's real %APPDATA% KiCad config or the real app-data
backup folder: every call passes config_base and backup_root.
"""

import copy
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

import pytest

from kicad_lib_manager import fsutil, kicad_setup, library_scanner
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.models import Issue, Severity


# -- fixtures (own copies; never import from another test module) ----------------


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "my repo"
    path.mkdir()
    return path


@pytest.fixture
def cfg(tmp_path):
    base = tmp_path / "kicad_cfg"
    base.mkdir()
    return base


@pytest.fixture
def backups(tmp_path):
    return tmp_path / "backups"


@pytest.fixture
def dest(tmp_path):
    return tmp_path / "dest"


def _dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _write_json(cfg, version, name, obj, *, crlf=False, bom=False):
    folder = cfg / version
    folder.mkdir(parents=True, exist_ok=True)
    text = _dump(obj)
    if crlf:
        text = text.replace("\n", "\r\n")
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path = folder / name
    path.write_bytes(data)
    return path


def _write_common(cfg, version, obj, **kw):
    return _write_json(cfg, version, "kicad_common.json", obj, **kw)


def _write_eeschema(cfg, version, obj, **kw):
    return _write_json(cfg, version, "eeschema.json", obj, **kw)


def _write_tables(dest, sym_entries, fp_entries):
    dest.mkdir(parents=True, exist_ok=True)

    def _lines(entries):
        return "\n".join(
            f'  (lib (name "{n}")(type "KiCad")(uri "u")(options "")(descr ""))'
            for n in entries
        )

    (dest / "sym-lib-table").write_text(
        f"(sym_lib_table\n{_lines(sym_entries)}\n)\n", encoding="utf-8"
    )
    (dest / "fp-lib-table").write_text(
        f"(fp_lib_table\n{_lines(fp_entries)}\n)\n", encoding="utf-8"
    )


def _recorder(answer=True):
    calls = []

    def confirm(changes):
        calls.append(list(changes))
        return answer

    confirm.calls = calls
    return confirm


def _by_code(issues, code):
    return [i for i in issues if i.code == code]


def _owner_lib_tree():
    return {
        "column_widths": {
            "Capacitance": 98, "Description": 445, "Item": 225,
            "MANUFACTURER": 339, "R": 110, "Value": 300, "Voltage": 73,
        },
        "columns": ["Item", "Description", "Capacitance", "R", "Voltage", "Value", "MANUFACTURER"],
        "open_libs": ["power"],
    }


def _owner_session():
    return {
        "pinned_design_block_libs": [],
        "pinned_fp_libs": [],
        "pinned_symbol_libs": [],
        "remember_open_files": False,
    }


# -- Task 1: pins, columns, confirmed write (D-17, D-18, D-19) --------------------


def test_owner_columns_become_atomic_columns():
    columns, widths = kicad_setup.plan_columns(_owner_lib_tree())
    assert columns == [
        "Item", "Description", "MPN", "Manufacturer", "Capacitance", "R", "Voltage", "Value",
    ]
    assert widths == {
        "Capacitance": 98, "Description": 445, "Item": 225, "R": 110,
        "Value": 300, "Voltage": 73, "Manufacturer": 339, "MPN": 200,
    }


def test_pins_from_tables(dest):
    _write_tables(dest, ["Atomic_Connector", "Atomic_Oscillator", "power"], ["Atomic_Footprints"])
    sym_names, fp_names, issues = kicad_setup.chooser_tables(dest)
    assert sym_names == ["Atomic_Connector", "Atomic_Oscillator"]
    assert fp_names == ["Atomic_Footprints"]
    (read,) = _by_code(issues, "chooser.tables_read")
    assert read.severity is Severity.INFO
    assert str(dest) in read.text


def test_confirmed_setup_writes_both_files(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector", "Atomic_Oscillator"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")

    common_obj = {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    }
    _write_common(cfg, "10.0", common_obj)

    eeschema_obj = {
        "lib_tree": _owner_lib_tree(),
        "symbol_chooser": {"show_pin_electrical_type": True},
        "lib_view": {"cur_lib": ""},
    }
    _write_eeschema(cfg, "10.0", eeschema_obj)

    confirm = _recorder(True)
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups, running=lambda: [], confirm=confirm,
    )

    common_path = cfg / "10.0" / "kicad_common.json"
    written_common = json.loads(common_path.read_text(encoding="utf-8"))
    assert written_common["session"]["pinned_symbol_libs"] == ["Atomic_Connector", "Atomic_Oscillator"]
    assert written_common["session"]["pinned_fp_libs"] == ["Atomic_Footprints"]
    common_check = copy.deepcopy(written_common)
    del common_check["session"]["pinned_symbol_libs"]
    del common_check["session"]["pinned_fp_libs"]
    original_check = copy.deepcopy(common_obj)
    del original_check["session"]["pinned_symbol_libs"]
    del original_check["session"]["pinned_fp_libs"]
    assert common_check == original_check

    eeschema_path = cfg / "10.0" / "eeschema.json"
    written_eeschema = json.loads(eeschema_path.read_text(encoding="utf-8"))
    assert written_eeschema["lib_tree"]["columns"] == [
        "Item", "Description", "MPN", "Manufacturer", "Capacitance", "R", "Voltage", "Value",
    ]
    assert written_eeschema["lib_tree"]["column_widths"] == {
        "Capacitance": 98, "Description": 445, "Item": 225, "R": 110,
        "Value": 300, "Voltage": 73, "Manufacturer": 339, "MPN": 200,
    }
    assert written_eeschema["symbol_chooser"] == eeschema_obj["symbol_chooser"]
    assert written_eeschema["lib_view"] == eeschema_obj["lib_view"]

    assert (backups / "kicad_common" / "10.0" / "kicad_common.json_backup_1").exists()
    assert (backups / "eeschema" / "10.0" / "eeschema.json_backup_1").exists()

    assert len(confirm.calls) == 1
    labels = {c.label for c in confirm.calls[0]}
    assert {"Pinned symbol libraries", "Pinned footprint libraries", "Symbol chooser columns"} <= labels

    (read,) = _by_code(issues, "chooser.tables_read")
    assert str(dest) in read.text
    assert len(_by_code(issues, "chooser.written")) == 2


# -- Task 2: refusals (D-26), KiCad open, re-read merge, idempotence, failures,
# restore (D-17, D-18, D-19, D-26) ------------------------------------------------


def test_already_set_up_writes_nothing(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()})

    kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(True),
    )

    confirm2 = _recorder(True)
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm2,
    )

    assert confirm2.calls == []
    (ok,) = _by_code(issues, "chooser.ok")
    assert ok.severity is Severity.INFO
    assert len(list((backups / "kicad_common" / "10.0").iterdir())) == 1
    assert len(list((backups / "eeschema" / "10.0").iterdir())) == 1


def test_hand_pins_kept_and_stale_atomic_pins_removed(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector", "Atomic_LED"], [])
    repo_str = str(repo).replace("\\", "/")
    session = _owner_session()
    session["pinned_symbol_libs"] = ["MyFavs", "Atomic_Gone", "Atomic_Connector"]
    _write_common(cfg, "10.0", {
        "session": session,
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })

    confirm = _recorder(True)
    kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )

    written = json.loads((cfg / "10.0" / "kicad_common.json").read_text(encoding="utf-8"))
    assert written["session"]["pinned_symbol_libs"] == ["MyFavs", "Atomic_Connector", "Atomic_LED"]

    (change,) = [c for c in confirm.calls[0] if c.label == "Pinned symbol libraries"]
    assert change.old == "MyFavs, Atomic_Gone, Atomic_Connector"
    assert change.new == "MyFavs, Atomic_Connector, Atomic_LED"


def test_columns_edges():
    columns, widths = kicad_setup.plan_columns({"columns": [], "column_widths": {}})
    assert columns == ["Item", "Description", "MPN", "Manufacturer"]

    columns2, widths2 = kicad_setup.plan_columns({
        "columns": ["Item", "Description", "MANUFACTURER", "Manufacturer"],
        "column_widths": {"MANUFACTURER": 100, "Manufacturer": 50},
    })
    assert columns2.count("Manufacturer") == 1
    assert "MANUFACTURER" not in columns2
    assert widths2["Manufacturer"] == 50

    columns3, widths3 = kicad_setup.plan_columns({"columns": ["Item", "Value"], "column_widths": {}})
    assert columns3 == ["Item", "MPN", "Manufacturer", "Value"]

    columns4, widths4 = kicad_setup.plan_columns({
        "columns": [], "column_widths": {"Foo": -5, "Bar": "baz"},
    })
    assert "Foo" not in widths4 and "Bar" not in widths4


def test_worktree_refused_before_asking(repo, cfg, backups, dest):
    (repo / ".git").write_text("gitdir: elsewhere\n")
    _write_tables(dest, ["Atomic_Connector"], [])
    repo_str = str(repo).replace("\\", "/")
    common_path = _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    before = common_path.read_bytes()
    confirm = _recorder()

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )

    (refused,) = _by_code(issues, "chooser.worktree_refused")
    assert refused.severity is Severity.WARNING
    assert confirm.calls == []
    assert common_path.read_bytes() == before


def test_other_checkout_refused_before_asking(repo, cfg, backups, dest, tmp_path):
    _write_tables(dest, ["Atomic_Connector"], [])
    other = str(tmp_path / "other checkout").replace("\\", "/")
    common_path = _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": other}},
    })
    before = common_path.read_bytes()
    confirm = _recorder()

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )

    (refused,) = _by_code(issues, "chooser.other_checkout_refused")
    assert refused.severity is Severity.WARNING
    mismatch = kicad_setup.wrong_checkout(repo, other)
    assert refused.text == kicad_setup.wrong_checkout_refusal(mismatch, kicad_setup.PIN_REFUSAL_TEXT)
    assert confirm.calls == []
    assert common_path.read_bytes() == before


def test_pin_texts_never_name_the_chooser_alone(repo, cfg, backups, dest, tmp_path):
    """No log line of the pin action says "chooser" on its own (gap G-13-1-c); the worktree
    and wrong-checkout refusals start with PIN_REFUSAL_TEXT and still name both folders."""
    repo_str = str(repo).replace("\\", "/")
    texts = []

    def run(repo_root, *, confirm, running=lambda: [], kicad_lib=None, session=None):
        _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
        _write_common(cfg, "10.0", {
            "session": session or _owner_session(),
            "environment": {"vars": {"KICAD_LIB_GITHUB": kicad_lib or repo_str}},
        })
        _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()})
        issues = kicad_setup.sync_kicad_chooser(
            repo_root, dest, config_base=cfg, backup_root=backups,
            running=running, confirm=confirm,
        )
        texts.extend(i.text for i in issues)
        return issues

    # worktree refusal
    (repo / ".git").write_text("gitdir: elsewhere\n")
    (worktree,) = _by_code(run(repo, confirm=_recorder()), "chooser.worktree_refused")
    assert worktree.text.startswith(kicad_setup.PIN_REFUSAL_TEXT)
    (repo / ".git").unlink()

    # wrong-checkout refusal names both folders
    other = str(tmp_path / "other checkout").replace("\\", "/")
    (wrong,) = _by_code(run(repo, confirm=_recorder(), kicad_lib=other), "chooser.other_checkout_refused")
    assert wrong.text.startswith(kicad_setup.PIN_REFUSAL_TEXT)
    assert repo_str in wrong.text and other in wrong.text

    # no confirmation step, declined, KiCad open (then written), already pinned
    run(repo, confirm=None)
    run(repo, confirm=_recorder(False))
    run(repo, confirm=_recorder(True), running=lambda: ["eeschema", "kicad"])
    run(repo, confirm=_recorder(True))

    # settings that keep changing while asked
    calls = []

    def churn(changes):
        calls.append(1)
        session = _owner_session()
        session["pinned_symbol_libs"] = [f"Hand{len(calls)}"]
        _write_common(cfg, "10.0", {
            "session": session,
            "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
        })
        return True

    shutil.rmtree(backups, ignore_errors=True)
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    texts.extend(
        i.text for i in kicad_setup.sync_kicad_chooser(
            repo, dest, config_base=cfg, backup_root=backups,
            running=lambda: [], confirm=churn,
        )
    )

    assert len(texts) >= 6
    for text in texts:
        bare = re.sub(r"symbol chooser", "", text, flags=re.IGNORECASE)
        assert "chooser" not in bare.lower(), text


@pytest.mark.parametrize(
    "spell",
    [
        pytest.param(lambda s: s.replace("/", "\\"), id="backslashes"),
        pytest.param(lambda s: s + "/", id="trailing-slash"),
    ],
)
def test_same_folder_rules_equal_spellings(tmp_path, spell):
    folder = tmp_path / "Repo" / "Lib"
    folder.mkdir(parents=True)
    a = str(folder)
    assert kicad_setup.same_folder(a, spell(a))


@pytest.mark.skipif(sys.platform != "win32", reason="case is only ignored on Windows")
def test_same_folder_rules_case_insensitive_on_windows(tmp_path):
    folder = tmp_path / "Repo" / "Lib"
    folder.mkdir(parents=True)
    assert kicad_setup.same_folder(str(folder), str(folder).upper())


def test_same_folder_rules_relative_path_resolves(tmp_path, monkeypatch):
    folder = tmp_path / "Repo" / "Lib"
    folder.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert kicad_setup.same_folder(str(folder), "Repo/Lib")


def test_same_folder_rules_different_folders(tmp_path):
    a = tmp_path / "Repo"
    b = tmp_path / "Other"
    a.mkdir()
    b.mkdir()
    assert not kicad_setup.same_folder(str(a), str(b))


def test_declined_and_missing_confirm_write_nothing(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], [])
    repo_str = str(repo).replace("\\", "/")
    common_path = _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    before = common_path.read_bytes()

    confirm = _recorder(answer=False)
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )
    (declined,) = _by_code(issues, "chooser.declined")
    assert declined.severity is Severity.INFO
    assert common_path.read_bytes() == before

    issues2 = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=None,
    )
    (warn,) = _by_code(issues2, "chooser.confirm_required")
    assert warn.severity is Severity.WARNING
    assert common_path.read_bytes() == before


def test_retry_writes_nothing(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], [])
    repo_str = str(repo).replace("\\", "/")
    common_path = _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    before = common_path.read_bytes()

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=lambda changes: ConfirmAnswer.RETRY,
    )
    (retry,) = _by_code(issues, "chooser.retry")
    assert retry.severity is Severity.INFO
    assert common_path.read_bytes() == before
    assert not backups.exists()


def test_running_kicad_warns_after_confirm(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()})

    order = []

    def running():
        order.append("running")
        return ["eeschema", "kicad"]

    def confirm(changes):
        order.append("confirm")
        return True

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=running, confirm=confirm,
    )
    assert order == ["running", "confirm"]
    (warn,) = _by_code(issues, "chooser.kicad_running")
    assert warn.severity is Severity.WARNING
    assert "eeschema" in warn.text and "kicad" in warn.text
    assert len(_by_code(issues, "chooser.written")) == 2


def test_confirmed_write_keeps_settings_saved_meanwhile(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()})

    def confirm(changes):
        common = {
            "session": _owner_session(),
            "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
            "saved_while_asked": True,
        }
        _write_common(cfg, "10.0", common)
        eeschema = {"lib_tree": _owner_lib_tree(), "saved_while_asked": True}
        _write_eeschema(cfg, "10.0", eeschema)
        return True

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )

    written_common = json.loads((cfg / "10.0" / "kicad_common.json").read_text(encoding="utf-8"))
    written_eeschema = json.loads((cfg / "10.0" / "eeschema.json").read_text(encoding="utf-8"))
    assert written_common["saved_while_asked"] is True
    assert written_common["session"]["pinned_symbol_libs"] == ["Atomic_Connector"]
    assert written_eeschema["saved_while_asked"] is True
    assert written_eeschema["lib_tree"]["columns"][2:4] == ["MPN", "Manufacturer"]
    assert len(_by_code(issues, "chooser.written")) == 2


def test_changed_list_asks_again(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector", "Atomic_LED"], [])
    repo_str = str(repo).replace("\\", "/")
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    calls = []

    def confirm(changes):
        calls.append(list(changes))
        if len(calls) == 1:
            session = _owner_session()
            session["pinned_symbol_libs"] = ["Atomic_Connector"]
            _write_common(cfg, "10.0", {
                "session": session,
                "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
            })
        return True

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )

    assert len(calls) == 2
    written = json.loads((cfg / "10.0" / "kicad_common.json").read_text(encoding="utf-8"))
    assert written["session"]["pinned_symbol_libs"] == ["Atomic_Connector", "Atomic_LED"]
    assert len(_by_code(issues, "chooser.written")) >= 1


def test_unstable_files_stop_after_three_passes(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], [])
    repo_str = str(repo).replace("\\", "/")
    common_path = _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    calls = []

    def confirm(changes):
        calls.append(list(changes))
        session = _owner_session()
        session["pinned_symbol_libs"] = [f"Hand{len(calls)}"]
        _write_common(cfg, "10.0", {
            "session": session,
            "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
        })
        return True

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=confirm,
    )

    assert len(calls) == 3
    (warn,) = _by_code(issues, "chooser.keeps_changing")
    assert warn.severity is Severity.WARNING
    assert not _by_code(issues, "chooser.written")
    assert not backups.exists()


def test_bad_json_and_bad_shape_write_nothing(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], [])
    repo_str = str(repo).replace("\\", "/")

    common_path = cfg / "10.0" / "kicad_common.json"
    common_path.parent.mkdir(parents=True, exist_ok=True)
    common_path.write_bytes(b'{"environment": ')
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(),
    )
    (bad,) = _by_code(issues, "config.bad_json")
    assert bad.severity is Severity.ERROR
    assert not backups.exists()

    _write_common(cfg, "10.0", {"environment": "not a dict"})
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(),
    )
    (bad,) = _by_code(issues, "config.bad_shape")
    assert bad.severity is Severity.ERROR

    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    eeschema_path = cfg / "10.0" / "eeschema.json"
    eeschema_path.write_bytes(b'{"lib_tree": ')
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(),
    )
    (bad,) = _by_code(issues, "chooser.bad_json")
    assert bad.severity is Severity.ERROR
    assert not backups.exists()

    _write_eeschema(cfg, "10.0", {"lib_tree": "not a dict"})
    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(),
    )
    (bad,) = _by_code(issues, "chooser.bad_shape")
    assert bad.severity is Severity.ERROR
    assert not backups.exists()


def test_verify_failure_aborts_before_backup(repo, cfg, backups, dest, monkeypatch):
    _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()})
    monkeypatch.setattr(kicad_setup, "_only_chooser_keys_changed", lambda *a: False)

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(True),
    )
    (bad,) = _by_code(issues, "chooser.verify_failed")
    assert bad.severity is Severity.ERROR
    assert not backups.exists()


def test_second_write_failure_restores_first(repo, cfg, backups, dest, monkeypatch):
    _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")
    common_path = _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })
    before = common_path.read_bytes()
    _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()})

    real_write = fsutil.atomic_write_text

    def flaky(path, text, **kw):
        if Path(path).name == "eeschema.json":
            return Issue(Severity.ERROR, "fs.write_failed", "Could not write eeschema.json: boom")
        return real_write(path, text, **kw)

    monkeypatch.setattr(kicad_setup.fsutil, "atomic_write_text", flaky)

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(True),
    )

    assert common_path.read_bytes() == before
    assert _by_code(issues, "fs.write_failed")
    assert _by_code(issues, "chooser.restored")


def test_missing_eeschema_still_pins(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], [])
    repo_str = str(repo).replace("\\", "/")
    _write_common(cfg, "10.0", {
        "session": _owner_session(),
        "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
    })

    issues = kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(True),
    )

    written = json.loads((cfg / "10.0" / "kicad_common.json").read_text(encoding="utf-8"))
    assert written["session"]["pinned_symbol_libs"] == ["Atomic_Connector"]
    (warn,) = _by_code(issues, "chooser.not_found")
    assert warn.severity is Severity.WARNING
    assert not (cfg / "10.0" / "eeschema.json").exists()


def test_crlf_and_bom_kept(repo, cfg, backups, dest):
    _write_tables(dest, ["Atomic_Connector"], ["Atomic_Footprints"])
    repo_str = str(repo).replace("\\", "/")
    _write_common(
        cfg, "10.0",
        {"session": _owner_session(), "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}}},
        crlf=True, bom=True,
    )
    _write_eeschema(cfg, "10.0", {"lib_tree": _owner_lib_tree()}, crlf=True, bom=True)

    kicad_setup.sync_kicad_chooser(
        repo, dest, config_base=cfg, backup_root=backups,
        running=lambda: [], confirm=_recorder(True),
    )

    common_data = (cfg / "10.0" / "kicad_common.json").read_bytes()
    assert common_data.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in common_data
    assert b"\n" not in common_data.replace(b"\r\n", b"")

    eeschema_data = (cfg / "10.0" / "eeschema.json").read_bytes()
    assert eeschema_data.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in eeschema_data
