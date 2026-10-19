"""write_tables and restore_backup_pair report through Issue lists and never raise."""

import os
import stat

import pytest

from kicad_lib_manager import table_generator as tg
from kicad_lib_manager.models import FootprintLibrary, Severity, SymbolLibrary


def _sym(name="New"):
    return SymbolLibrary(name, f"Custom/Symbols/{name}.kicad_sym", "Custom", selected=True)


def _fp(name="NewFP"):
    return FootprintLibrary(name, f"Custom/Footprints/{name}.pretty", "Custom", selected=True)


def test_write_tables_into_empty_folder_writes_both(tmp_path):
    issues = tg.write_tables(tmp_path, [_sym()], [_fp()])
    assert [(i.code, i.severity) for i in issues] == [
        ("table.written", Severity.SUCCESS),
        ("table.written", Severity.SUCCESS),
    ]
    assert (tmp_path / "sym-lib-table").read_text(encoding="utf-8").startswith("(sym_lib_table")
    assert (tmp_path / "fp-lib-table").read_text(encoding="utf-8").startswith("(fp_lib_table")
    assert not list(tmp_path.glob("*_backup_*"))


def test_unparseable_table_is_not_backed_up_or_written_and_other_table_still_is(tmp_path):
    broken = b"(sym_lib_table\n  (version 7)\n"
    (tmp_path / "sym-lib-table").write_bytes(broken)

    issues = tg.write_tables(tmp_path, [_sym()], [_fp()])

    errors = [i for i in issues if i.severity is Severity.ERROR]
    assert len(errors) == 1
    assert "line" in errors[0].text and "col" in errors[0].text
    assert (tmp_path / "sym-lib-table").read_bytes() == broken
    assert not list(tmp_path.glob("sym-lib-table_backup_*"))
    assert (tmp_path / "fp-lib-table").read_text(encoding="utf-8").startswith("(fp_lib_table")
    assert [i.code for i in issues if i.severity is Severity.SUCCESS] == ["table.written"]


def test_restore_pair_restores_both_after_backing_up_current(tmp_path):
    (tmp_path / "sym-lib-table").write_bytes(b"cur-sym")
    (tmp_path / "fp-lib-table").write_bytes(b"cur-fp")
    (tmp_path / "sym-lib-table_backup_2").write_bytes(b"old-sym")
    (tmp_path / "fp-lib-table_backup_2").write_bytes(b"old-fp")

    issues = tg.restore_backup_pair(tmp_path, 2)

    assert (tmp_path / "sym-lib-table").read_bytes() == b"old-sym"
    assert (tmp_path / "fp-lib-table").read_bytes() == b"old-fp"
    assert (tmp_path / "sym-lib-table_backup_3").read_bytes() == b"cur-sym"
    assert (tmp_path / "fp-lib-table_backup_3").read_bytes() == b"cur-fp"
    assert [i.code for i in issues] == [
        "table.backed_up", "table.restored", "table.backed_up", "table.restored",
    ]
    restored = [i for i in issues if i.code == "table.restored"]
    assert [i.severity for i in restored] == [Severity.SUCCESS, Severity.SUCCESS]


def test_restore_pair_with_missing_fp_backup_restores_only_sym(tmp_path):
    (tmp_path / "sym-lib-table").write_bytes(b"cur-sym")
    (tmp_path / "fp-lib-table").write_bytes(b"cur-fp")
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"old-sym")

    issues = tg.restore_backup_pair(tmp_path, 1)

    assert (tmp_path / "sym-lib-table").read_bytes() == b"old-sym"
    assert (tmp_path / "fp-lib-table").read_bytes() == b"cur-fp"
    assert [i.code for i in issues].count("table.restored") == 1


def test_restore_pair_without_current_table_skips_the_safety_backup(tmp_path):
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"old-sym")

    issues = tg.restore_backup_pair(tmp_path, 1)

    assert (tmp_path / "sym-lib-table").read_bytes() == b"old-sym"
    assert [i.code for i in issues] == ["table.restored"]


def test_restore_pair_read_only_current_table_is_an_error_issue_not_an_exception(tmp_path):
    current = tmp_path / "sym-lib-table"
    current.write_bytes(b"cur-sym")
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"old-sym")
    os.chmod(current, stat.S_IREAD)
    try:
        issues = tg.restore_backup_pair(tmp_path, 1)
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert [i.code for i in errors] == ["fs.read_only"]
        assert not [i for i in issues if i.code == "table.restored"]
        assert current.read_bytes() == b"cur-sym"
    finally:
        for f in tmp_path.iterdir():
            os.chmod(f, stat.S_IREAD | stat.S_IWRITE)
