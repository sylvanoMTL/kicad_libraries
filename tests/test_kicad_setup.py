"""The chooser setup of TBL-02 (kicad_setup.py) on synthetic trees.

Nothing here touches the owner's real %APPDATA% KiCad config or the real app-data
backup folder: every call passes config_base and backup_root.
"""

import copy
import json
import os
import stat
from pathlib import Path

import pytest

from kicad_lib_manager import fsutil, kicad_setup, library_scanner
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.models import Severity


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
