"""add_library_entries adds one library's managed entries and keeps every other byte (POST-02, D-17)."""

import os
import stat

from kicad_lib_manager import table_generator as tg
from kicad_lib_manager.models import Severity

NICK = "IC_New_TI"
SYM_REL = "Custom/Symbols/IC_New_TI.kicad_sym"
FP_REL = "Custom/Footprints/IC_New_TI.pretty"

SYM_CRLF = (
    b"(sym_lib_table\r\n"
    b"  (version 7)\r\n"
    b'  (lib (name "Ext")(type "KiCad")(uri "C:/ext/Ext.kicad_sym")(options "")(descr ""))\r\n'
    b'  (lib (name "Mgd")(type "KiCad")(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/Mgd.kicad_sym")'
    b'(options "")(descr "")(disabled))\r\n'
    b'  (unknown_item "kept")\r\n'
    b")\r\n"
)
FP_LF = (
    b"(fp_lib_table\n"
    b"  (version 7)\n"
    b'  (lib (name "Mgd")(type "KiCad")(uri "${KICAD_LIB_GITHUB}/Custom/Footprints/Mgd.pretty")'
    b'(options "")(descr ""))\n'
    b")\n"
)


def _entry(rel: str, eol: bytes) -> bytes:
    line = (
        f'  (lib (name "{NICK}")(type "KiCad")(uri "${{KICAD_LIB_GITHUB}}/{rel}")'
        f'(options "")(descr ""))'
    )
    return line.encode("utf-8") + eol


def _seed(folder, sym=SYM_CRLF, fp=FP_LF):
    (folder / "sym-lib-table").write_bytes(sym)
    (folder / "fp-lib-table").write_bytes(fp)


def _backups(folder):
    return sorted(p.name for p in folder.glob("*_backup_*"))


def test_add_entries_keeps_every_other_byte(tmp_path):
    _seed(tmp_path)

    issues = tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)

    assert not [i for i in issues if i.severity is Severity.ERROR]
    sym_new = (tmp_path / "sym-lib-table").read_bytes()
    fp_new = (tmp_path / "fp-lib-table").read_bytes()
    sym_line = _entry(SYM_REL, b"\r\n")
    fp_line = _entry(FP_REL, b"\n")
    # exactly one inserted line, before the closing paren, in the table's own EOL
    assert sym_new == SYM_CRLF[: -len(b")\r\n")] + sym_line + b")\r\n"
    assert fp_new == FP_LF[: -len(b")\n")] + fp_line + b")\n"
    assert sym_new.replace(sym_line, b"", 1) == SYM_CRLF
    assert fp_new.replace(fp_line, b"", 1) == FP_LF


def test_add_entries_idempotent(tmp_path):
    _seed(tmp_path)
    tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)
    sym_once = (tmp_path / "sym-lib-table").read_bytes()
    fp_once = (tmp_path / "fp-lib-table").read_bytes()
    backups_once = _backups(tmp_path)

    issues = tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)

    assert (tmp_path / "sym-lib-table").read_bytes() == sym_once
    assert (tmp_path / "fp-lib-table").read_bytes() == fp_once
    assert _backups(tmp_path) == backups_once
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (Severity.INFO, "table.already_listed",
         "Library tables not changed: IC_New_TI was already listed"),
    ]


def test_add_entries_summary_added(tmp_path):
    _seed(tmp_path)

    issues = tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)

    summary = [i for i in issues if i.code == "table.entries_added"]
    assert [(i.severity, i.text) for i in summary] == [
        (Severity.SUCCESS, "Added IC_New_TI to sym-lib-table and fp-lib-table"),
    ]
    backed_up = [i for i in issues if i.code == "table.backed_up"]
    assert [i.severity for i in backed_up] == [Severity.INFO, Severity.INFO]
    assert _backups(tmp_path) == ["fp-lib-table_backup_1", "sym-lib-table_backup_1"]
    assert (tmp_path / "sym-lib-table_backup_1").read_bytes() == SYM_CRLF
    assert (tmp_path / "fp-lib-table_backup_1").read_bytes() == FP_LF


def test_add_entries_backup_number_continues_past_existing(tmp_path):
    _seed(tmp_path)
    (tmp_path / "sym-lib-table_backup_4").write_bytes(b"old")

    tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)

    assert (tmp_path / "sym-lib-table_backup_5").read_bytes() == SYM_CRLF
    assert (tmp_path / "fp-lib-table_backup_5").read_bytes() == FP_LF


def test_add_entries_creates_missing_tables(tmp_path):
    issues = tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)

    sym_text = (tmp_path / "sym-lib-table").read_text(encoding="utf-8")
    fp_text = (tmp_path / "fp-lib-table").read_text(encoding="utf-8")
    assert sym_text.startswith("(sym_lib_table\n")
    assert fp_text.startswith("(fp_lib_table\n")
    assert sym_text.count("(lib ") == 1 and f'"${{KICAD_LIB_GITHUB}}/{SYM_REL}"' in sym_text
    assert fp_text.count("(lib ") == 1 and f'"${{KICAD_LIB_GITHUB}}/{FP_REL}"' in fp_text
    assert not _backups(tmp_path)
    assert not [i for i in issues if i.severity is Severity.ERROR]
    assert [i.text for i in issues if i.code == "table.entries_added"] == [
        "Added IC_New_TI to sym-lib-table and fp-lib-table",
    ]


def test_add_entries_external_clash(tmp_path):
    sym = (
        b"(sym_lib_table\n"
        b"  (version 7)\n"
        b'  (lib (name "IC_New_TI")(type "KiCad")(uri "D:/elsewhere/IC_New_TI.kicad_sym")'
        b'(options "")(descr ""))\n'
        b")\n"
    )
    _seed(tmp_path, sym=sym)

    issues = tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)

    assert (tmp_path / "sym-lib-table").read_bytes() == sym
    assert "sym-lib-table_backup_1" not in _backups(tmp_path)
    warnings = [i for i in issues if i.severity is Severity.WARNING]
    assert len(warnings) == 1
    assert "D:/elsewhere/IC_New_TI.kicad_sym" in warnings[0].text
    assert "sym-lib-table" in warnings[0].text
    # the other table is still updated
    assert _entry(FP_REL, b"\n") in (tmp_path / "fp-lib-table").read_bytes()
    assert [i.text for i in issues if i.code == "table.entries_added"] == []
    assert "Added IC_New_TI to fp-lib-table" in [i.text for i in issues]


def test_add_entries_missing_destination(tmp_path):
    dest = tmp_path / "nope"

    issues = tg.add_library_entries(dest, NICK, SYM_REL, FP_REL)

    assert len(issues) == 1
    assert issues[0].severity is Severity.ERROR
    assert issues[0].text.startswith("Destination folder does not exist:")
    assert not dest.exists()


def test_add_entries_read_only_table(tmp_path):
    _seed(tmp_path)
    sym_path = tmp_path / "sym-lib-table"
    os.chmod(sym_path, stat.S_IREAD)
    try:
        issues = tg.add_library_entries(tmp_path, NICK, SYM_REL, FP_REL)
        assert sym_path.read_bytes() == SYM_CRLF
        errors = [i for i in issues if i.severity is Severity.ERROR]
        assert len(errors) == 1
        assert _entry(FP_REL, b"\n") in (tmp_path / "fp-lib-table").read_bytes()
        assert "Added IC_New_TI to fp-lib-table" in [i.text for i in issues]
        assert not [i for i in issues if i.code == "table.entries_added"]
    finally:
        for f in tmp_path.iterdir():
            os.chmod(f, stat.S_IREAD | stat.S_IWRITE)


def test_add_entries_quotes_values(tmp_path):
    _seed(tmp_path)
    sym_rel = 'Custom/Symbols/we"ird.kicad_sym'
    fp_rel = 'Custom/Footprints/we"ird.pretty'

    issues = tg.add_library_entries(tmp_path, "we_ird", sym_rel, fp_rel)

    assert not [i for i in issues if i.severity is Severity.ERROR]
    sym_info = tg.table_info(tmp_path / "sym-lib-table")
    fp_info = tg.table_info(tmp_path / "fp-lib-table")
    assert sym_rel in sym_info.managed
    assert fp_rel in fp_info.managed
    assert b'we\\"ird' in (tmp_path / "sym-lib-table").read_bytes()
