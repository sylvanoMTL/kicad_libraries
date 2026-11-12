"""write_tables and restore_backup_pair report through Issue lists and never raise."""

import errno
import os
import stat

import pytest

from kicad_lib_manager import fsutil
from kicad_lib_manager import table_generator as tg
from kicad_lib_manager.models import FootprintLibrary, Issue, Severity, SymbolLibrary


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


# -- per-table failure matrix (HARD-02) -------------------------------------------------

SYM_TABLE = b"(sym_lib_table\n  (version 7)\n)\n"
FP_TABLE = b"(fp_lib_table\n  (version 7)\n)\n"


def _seed(folder, sym=SYM_TABLE, fp=FP_TABLE):
    (folder / "sym-lib-table").write_bytes(sym)
    (folder / "fp-lib-table").write_bytes(fp)


def _fail_replace_for(monkeypatch, target_name, exc):
    """Make os.replace fail for one table and skip the real 1 s lock-retry wait."""
    real_replace = os.replace
    real_write = fsutil.atomic_write_bytes

    def replace(src, dst):
        if os.path.basename(dst) == target_name:
            raise exc
        return real_replace(src, dst)

    def quick_write(path, data, *, retry_delays=(), sleep=None):
        return real_write(path, data, retry_delays=(0.0,), sleep=lambda s: None)

    monkeypatch.setattr(fsutil.os, "replace", replace)
    monkeypatch.setattr(fsutil, "atomic_write_bytes", quick_write)


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


def test_read_only_sym_table_gives_one_error_and_fp_table_is_still_written(tmp_path):
    _seed(tmp_path)
    sym = tmp_path / "sym-lib-table"
    os.chmod(sym, stat.S_IREAD)
    try:
        issues = tg.write_tables(tmp_path, [_sym()], [_fp()])
        (error,) = _errors(issues)
        assert error.code == "fs.read_only" and "sym-lib-table" in error.text
        assert sym.read_bytes() == SYM_TABLE
        assert (tmp_path / "fp-lib-table").read_bytes() != FP_TABLE
        assert [i.code for i in issues if i.severity is Severity.SUCCESS] == ["table.written"]
    finally:
        os.chmod(sym, stat.S_IREAD | stat.S_IWRITE)


def test_locked_fp_table_gives_one_error_and_sym_table_is_still_written(tmp_path, monkeypatch):
    _seed(tmp_path)
    _fail_replace_for(monkeypatch, "fp-lib-table", PermissionError(errno.EACCES, "in use"))

    issues = tg.write_tables(tmp_path, [_sym()], [_fp()])

    (error,) = _errors(issues)
    assert error.code == "fs.locked" and "fp-lib-table" in error.text
    assert (tmp_path / "fp-lib-table").read_bytes() == FP_TABLE
    assert (tmp_path / "sym-lib-table").read_bytes() != SYM_TABLE
    assert [i.code for i in issues if i.severity is Severity.SUCCESS] == ["table.written"]
    assert not list(tmp_path.glob(".*.tmp"))


def test_backup_failure_blocks_only_that_table(tmp_path, monkeypatch):
    _seed(tmp_path)
    real_backup = fsutil.backup_file
    failure = Issue(Severity.ERROR, "fs.backup_failed", "Could not back up sym-lib-table: disk full")

    def backup(path, backup_dir, **kwargs):
        return failure if path.name == "sym-lib-table" else real_backup(path, backup_dir, **kwargs)

    monkeypatch.setattr(fsutil, "backup_file", backup)

    issues = tg.write_tables(tmp_path, [_sym()], [_fp()])

    assert _errors(issues) == [failure]
    assert (tmp_path / "sym-lib-table").read_bytes() == SYM_TABLE
    assert (tmp_path / "fp-lib-table").read_bytes() != FP_TABLE


def test_interrupted_replace_keeps_the_table_and_the_backup_made_before_it(tmp_path, monkeypatch):
    _seed(tmp_path)
    _fail_replace_for(monkeypatch, "sym-lib-table", OSError(errno.EIO, "I/O error"))

    issues = tg.write_tables(tmp_path, [_sym()], [_fp()])

    (error,) = _errors(issues)
    assert error.code == "fs.write_failed"
    assert (tmp_path / "sym-lib-table").read_bytes() == SYM_TABLE
    assert (tmp_path / "sym-lib-table_backup_1").read_bytes() == SYM_TABLE


def test_both_tables_of_one_generate_share_the_next_backup_number(tmp_path):
    _seed(tmp_path)
    (tmp_path / "sym-lib-table_backup_3").write_bytes(b"old-sym")
    (tmp_path / "fp-lib-table_backup_1").write_bytes(b"old-fp")

    tg.write_tables(tmp_path, [_sym()], [_fp()])

    assert (tmp_path / "sym-lib-table_backup_4").read_bytes() == SYM_TABLE
    assert (tmp_path / "fp-lib-table_backup_4").read_bytes() == FP_TABLE
    assert tg.list_backup_pairs(tmp_path)[0] == (
        4, tmp_path / "sym-lib-table_backup_4", tmp_path / "fp-lib-table_backup_4",
    )


def test_refused_sym_table_still_leaves_the_fp_backup_on_the_shared_number(tmp_path):
    _seed(tmp_path, sym=b"(sym_lib_table\n  (version 7)\n")
    (tmp_path / "sym-lib-table_backup_3").write_bytes(b"old-sym")

    tg.write_tables(tmp_path, [_sym()], [_fp()])

    assert (tmp_path / "fp-lib-table_backup_4").read_bytes() == FP_TABLE
    assert not (tmp_path / "sym-lib-table_backup_4").exists()


def test_unchanged_table_is_neither_backed_up_nor_rewritten(tmp_path):
    tg.write_tables(tmp_path, [_sym()], [_fp()])
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}

    issues = tg.write_tables(tmp_path, [_sym()], [_fp()])

    assert [(i.code, i.severity) for i in issues] == [
        ("table.unchanged", Severity.INFO),
        ("table.unchanged", Severity.INFO),
    ]
    assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()} == before


def test_deselecting_a_library_is_reported_once_as_removed(tmp_path):
    tg.write_tables(tmp_path, [_sym()], [_fp()])

    deselected = SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom", selected=False)
    issues = tg.write_tables(tmp_path, [deselected], [])
    (removed,) = [i for i in issues if i.code == "table.removed"]
    assert removed.severity is Severity.INFO and "New" in removed.text


def test_restore_makes_both_safety_copies_on_one_shared_number(tmp_path):
    _seed(tmp_path, sym=b"cur-sym", fp=b"cur-fp")
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"old-sym")
    (tmp_path / "sym-lib-table_backup_5").write_bytes(b"newer-sym")
    (tmp_path / "fp-lib-table_backup_1").write_bytes(b"old-fp")

    tg.restore_backup_pair(tmp_path, 1)

    assert (tmp_path / "sym-lib-table_backup_6").read_bytes() == b"cur-sym"
    assert (tmp_path / "fp-lib-table_backup_6").read_bytes() == b"cur-fp"


def test_restore_with_a_locked_fp_table_gives_one_error_and_still_restores_sym(tmp_path, monkeypatch):
    _seed(tmp_path, sym=b"cur-sym", fp=b"cur-fp")
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"old-sym")
    (tmp_path / "fp-lib-table_backup_1").write_bytes(b"old-fp")
    _fail_replace_for(monkeypatch, "fp-lib-table", PermissionError(errno.EACCES, "in use"))

    issues = tg.restore_backup_pair(tmp_path, 1)

    (error,) = _errors(issues)
    assert error.code == "fs.locked" and "fp-lib-table" in error.text
    assert (tmp_path / "sym-lib-table").read_bytes() == b"old-sym"
    assert (tmp_path / "fp-lib-table").read_bytes() == b"cur-fp"


def test_destination_that_is_a_file_gives_one_error_and_no_exception(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_bytes(b"x")

    issues = tg.write_tables(blocker, [_sym()], [_fp()])

    assert len(issues) == 1 and issues[0].severity is Severity.ERROR


def test_table_generator_has_no_leftover_direct_file_writes():
    assert not hasattr(tg, "backup_existing")
    assert not hasattr(tg, "shutil")
