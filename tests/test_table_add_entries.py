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
    descr = tg.library_description(NICK, rel, {})
    line = (
        f'  (lib (name "{NICK}")(type "KiCad")(uri "${{KICAD_LIB_GITHUB}}/{rel}")'
        f'(options "")(descr "{descr}"))'
    )
    return line.encode("utf-8") + eol


def _add_both(folder):
    return tg.add_library_entries(folder, symbol=(NICK, SYM_REL), footprint=(NICK, FP_REL), repo_root=folder)


def _seed(folder, sym=SYM_CRLF, fp=FP_LF):
    (folder / "sym-lib-table").write_bytes(sym)
    (folder / "fp-lib-table").write_bytes(fp)


def _backups(folder):
    return sorted(p.name for p in folder.glob("*_backup_*"))


def test_add_entries_keeps_every_other_byte(tmp_path):
    _seed(tmp_path)

    issues = _add_both(tmp_path)

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
    _add_both(tmp_path)
    sym_once = (tmp_path / "sym-lib-table").read_bytes()
    fp_once = (tmp_path / "fp-lib-table").read_bytes()
    backups_once = _backups(tmp_path)

    issues = _add_both(tmp_path)

    assert (tmp_path / "sym-lib-table").read_bytes() == sym_once
    assert (tmp_path / "fp-lib-table").read_bytes() == fp_once
    assert _backups(tmp_path) == backups_once
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (Severity.INFO, "table.already_listed", "sym-lib-table already lists IC_New_TI; not changed"),
        (Severity.INFO, "table.already_listed", "fp-lib-table already lists IC_New_TI; not changed"),
    ]


def test_add_entries_summary_added(tmp_path):
    _seed(tmp_path)

    issues = _add_both(tmp_path)

    summary = [i for i in issues if i.code == "table.entries_added"]
    assert [(i.severity, i.text) for i in summary] == [
        (Severity.SUCCESS, "Added IC_New_TI to sym-lib-table and IC_New_TI to fp-lib-table"),
    ]
    backed_up = [i for i in issues if i.code == "table.backed_up"]
    assert [i.severity for i in backed_up] == [Severity.INFO, Severity.INFO]
    assert _backups(tmp_path) == ["fp-lib-table_backup_1", "sym-lib-table_backup_1"]
    assert (tmp_path / "sym-lib-table_backup_1").read_bytes() == SYM_CRLF
    assert (tmp_path / "fp-lib-table_backup_1").read_bytes() == FP_LF


def test_add_entries_backup_number_continues_past_existing(tmp_path):
    _seed(tmp_path)
    (tmp_path / "sym-lib-table_backup_4").write_bytes(b"old")

    _add_both(tmp_path)

    assert (tmp_path / "sym-lib-table_backup_5").read_bytes() == SYM_CRLF
    assert (tmp_path / "fp-lib-table_backup_5").read_bytes() == FP_LF


def test_add_entries_creates_missing_tables(tmp_path):
    issues = _add_both(tmp_path)

    sym_text = (tmp_path / "sym-lib-table").read_text(encoding="utf-8")
    fp_text = (tmp_path / "fp-lib-table").read_text(encoding="utf-8")
    assert sym_text.startswith("(sym_lib_table\n")
    assert fp_text.startswith("(fp_lib_table\n")
    assert sym_text.count("(lib ") == 1 and f'"${{KICAD_LIB_GITHUB}}/{SYM_REL}"' in sym_text
    assert fp_text.count("(lib ") == 1 and f'"${{KICAD_LIB_GITHUB}}/{FP_REL}"' in fp_text
    assert not _backups(tmp_path)
    assert not [i for i in issues if i.severity is Severity.ERROR]
    assert [i.text for i in issues if i.code == "table.entries_added"] == [
        "Added IC_New_TI to sym-lib-table and IC_New_TI to fp-lib-table",
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

    issues = _add_both(tmp_path)

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

    issues = _add_both(dest)

    assert len(issues) == 1
    assert issues[0].severity is Severity.ERROR
    assert issues[0].text.startswith("Destination folder does not exist:")
    assert not dest.exists()


def test_add_entries_read_only_table(tmp_path):
    _seed(tmp_path)
    sym_path = tmp_path / "sym-lib-table"
    os.chmod(sym_path, stat.S_IREAD)
    try:
        issues = _add_both(tmp_path)
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

    issues = tg.add_library_entries(tmp_path, symbol=("we_ird", sym_rel), footprint=("we_ird", fp_rel), repo_root=tmp_path)

    assert not [i for i in issues if i.severity is Severity.ERROR]
    sym_info = tg.table_info(tmp_path / "sym-lib-table")
    fp_info = tg.table_info(tmp_path / "fp-lib-table")
    assert sym_rel in sym_info.managed
    assert fp_rel in fp_info.managed
    assert b'we\\"ird' in (tmp_path / "sym-lib-table").read_bytes()


# -- Two nicknames (plan 10-11, D-15) ---------------------------------------------------------------

SHARED = "Atomic_Footprints"
SHARED_REL = "Custom/Footprints/Atomic_Footprints.pretty"


def test_symbol_only_leaves_the_footprint_table_alone(tmp_path):
    _seed(tmp_path)

    issues = tg.add_library_entries(tmp_path, symbol=(NICK, SYM_REL), repo_root=tmp_path)

    sym_line = _entry(SYM_REL, b"\r\n")
    assert (tmp_path / "sym-lib-table").read_bytes() == SYM_CRLF[: -len(b")\r\n")] + sym_line + b")\r\n"
    assert (tmp_path / "fp-lib-table").read_bytes() == FP_LF
    assert _backups(tmp_path) == ["sym-lib-table_backup_1"]
    assert [(i.severity, i.code, i.text) for i in issues if i.code != "table.backed_up"] == [
        (Severity.SUCCESS, "table.entry_added", "Added IC_New_TI to sym-lib-table"),
    ]


def test_footprint_only_leaves_the_symbol_table_alone(tmp_path):
    _seed(tmp_path)

    issues = tg.add_library_entries(tmp_path, footprint=(SHARED, SHARED_REL), repo_root=tmp_path)

    descr = tg.library_description(SHARED, SHARED_REL, {})
    fp_line = (
        f'  (lib (name "{SHARED}")(type "KiCad")(uri "${{KICAD_LIB_GITHUB}}/{SHARED_REL}")'
        f'(options "")(descr "{descr}"))\n'
    ).encode()
    assert (tmp_path / "fp-lib-table").read_bytes() == FP_LF[: -len(b")\n")] + fp_line + b")\n"
    assert (tmp_path / "sym-lib-table").read_bytes() == SYM_CRLF
    assert _backups(tmp_path) == ["fp-lib-table_backup_1"]
    assert [i.text for i in issues if i.code == "table.entry_added"] == ["Added Atomic_Footprints to fp-lib-table"]


def test_nothing_requested_changes_nothing(tmp_path):
    _seed(tmp_path)

    assert tg.add_library_entries(tmp_path, repo_root=tmp_path) == []

    assert (tmp_path / "sym-lib-table").read_bytes() == SYM_CRLF
    assert (tmp_path / "fp-lib-table").read_bytes() == FP_LF
    assert not _backups(tmp_path)


def test_two_nicknames_added_give_the_combined_message(tmp_path):
    _seed(tmp_path)

    issues = tg.add_library_entries(tmp_path, symbol=(NICK, SYM_REL), footprint=(SHARED, SHARED_REL), repo_root=tmp_path)

    assert [i.text for i in issues if i.code == "table.entries_added"] == [
        "Added IC_New_TI to sym-lib-table and Atomic_Footprints to fp-lib-table",
    ]
    assert not [i for i in issues if i.code == "table.entry_added"]
    assert f'(name "{NICK}")'.encode() in (tmp_path / "sym-lib-table").read_bytes()
    assert f'(name "{SHARED}")'.encode() in (tmp_path / "fp-lib-table").read_bytes()
    assert b'(name "Atomic_Footprints")' not in (tmp_path / "sym-lib-table").read_bytes()


def test_a_listed_footprint_entry_is_kept_while_the_new_symbol_entry_is_added(tmp_path):
    fp = (
        b"(fp_lib_table\n"
        b"  (version 7)\n"
        b'  (lib (name "Atomic_Footprints")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Footprints/Atomic_Footprints.pretty")(options "")(descr ""))\n'
        b")\n"
    )
    _seed(tmp_path, fp=fp)

    issues = tg.add_library_entries(tmp_path, symbol=(NICK, SYM_REL), footprint=(SHARED, SHARED_REL), repo_root=tmp_path)

    assert (tmp_path / "fp-lib-table").read_bytes() == fp
    assert _entry(SYM_REL, b"\r\n") in (tmp_path / "sym-lib-table").read_bytes()
    texts = [i.text for i in issues]
    assert "Added IC_New_TI to sym-lib-table" in texts
    assert "fp-lib-table already lists Atomic_Footprints; not changed" in texts
    assert not [i for i in issues if i.code == "table.entries_added"]


# -- Stale and clashing entries (phase 12, REV-01, D-01..D-05) --------------------------------------

def _sym_table(*entries: str, eol: str = "\r\n") -> bytes:
    body = "".join(f"  {entry}{eol}" for entry in entries)
    return f"(sym_lib_table{eol}  (version 7){eol}{body}){eol}".encode("utf-8")


def _lib_line(nick: str, uri: str) -> str:
    return f'(lib (name "{nick}")(type "KiCad")(uri "{uri}")(options "")(descr ""))'


def _managed_line(rel: str, nick: str = NICK) -> str:
    return _lib_line(nick, f"${{KICAD_LIB_GITHUB}}/{rel}")


def _add_sym(folder, *, fold=None):
    return tg.add_library_entries(folder, symbol=(NICK, SYM_REL), repo_root=folder, fold=fold)


def test_stale_managed_entry_is_repointed(tmp_path):
    original = _sym_table(_managed_line("Custom/Symbols/Old_Name.kicad_sym"))
    (tmp_path / "sym-lib-table").write_bytes(original)

    issues = _add_sym(tmp_path)

    updated = [i for i in issues if i.code == "table.entry_updated"]
    assert [(i.severity, i.text) for i in updated] == [
        (Severity.SUCCESS, f"Updated: {NICK} in sym-lib-table now points at {SYM_REL}"),
    ]
    assert [i.severity for i in issues if i.code == "table.backed_up"] == [Severity.INFO]
    assert (tmp_path / "sym-lib-table_backup_1").read_bytes() == original
    assert (tmp_path / "sym-lib-table").read_bytes() == original.replace(
        b"Old_Name.kicad_sym", b"IC_New_TI.kicad_sym"
    )
    assert (tmp_path / "sym-lib-table").read_bytes().count(b'(name "IC_New_TI")') == 1


def test_live_managed_entry_warns_and_keeps_table(tmp_path):
    other = "WurthElektronik/KiCad-Library/Symbols/IC_New_TI.kicad_sym"
    (tmp_path / "WurthElektronik/KiCad-Library/Symbols").mkdir(parents=True)
    (tmp_path / other).write_text("(kicad_symbol_lib)", encoding="utf-8")
    original = _sym_table(_managed_line(other))
    (tmp_path / "sym-lib-table").write_bytes(original)

    issues = _add_sym(tmp_path)

    assert (tmp_path / "sym-lib-table").read_bytes() == original
    assert not _backups(tmp_path)
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (
            Severity.WARNING,
            "table.path_clash",
            f"Not added to sym-lib-table: the name {NICK} already points at {other}; "
            "KiCad still loads that library. Rename one of them.",
        ),
    ]


def test_matching_entry_ignores_case_when_folding(tmp_path):
    original = _sym_table(_managed_line(SYM_REL.lower()))
    (tmp_path / "sym-lib-table").write_bytes(original)

    issues = _add_sym(tmp_path, fold=True)

    assert (tmp_path / "sym-lib-table").read_bytes() == original
    assert not _backups(tmp_path)
    assert [(i.severity, i.code) for i in issues] == [(Severity.INFO, "table.already_listed")]


def test_case_differs_without_folding_is_not_listed(tmp_path):
    (tmp_path / "sym-lib-table").write_bytes(_sym_table(_managed_line(SYM_REL.lower())))

    issues = _add_sym(tmp_path, fold=False)

    assert [i.code for i in issues if i.severity is Severity.SUCCESS] == ["table.entry_updated"]
    assert f"${{KICAD_LIB_GITHUB}}/{SYM_REL}".encode() in (tmp_path / "sym-lib-table").read_bytes()
    assert _backups(tmp_path) == ["sym-lib-table_backup_1"]


def test_hand_entry_is_never_edited_even_when_stale(tmp_path):
    original = _sym_table(_lib_line(NICK, "D:/gone/IC_New_TI.kicad_sym"))
    (tmp_path / "sym-lib-table").write_bytes(original)

    issues = _add_sym(tmp_path)

    assert (tmp_path / "sym-lib-table").read_bytes() == original
    assert not _backups(tmp_path)
    assert [(i.severity, i.code, i.text) for i in issues] == [
        (
            Severity.WARNING,
            "table.external_clash",
            f"Not added to sym-lib-table: {NICK} is already used by an entry you added by hand "
            "(D:/gone/IC_New_TI.kicad_sym); KiCad keeps loading that one.",
        ),
    ]


def test_precedence_with_two_entries_under_one_name(tmp_path):
    stale = _managed_line("Custom/Symbols/Gone.kicad_sym")
    live_rel = "WurthElektronik/KiCad-Library/Symbols/IC_New_TI.kicad_sym"
    (tmp_path / "WurthElektronik/KiCad-Library/Symbols").mkdir(parents=True)
    (tmp_path / live_rel).write_text("(kicad_symbol_lib)", encoding="utf-8")
    cases = [
        ([stale, _managed_line(SYM_REL)], "table.already_listed"),
        ([stale, _managed_line(live_rel)], "table.path_clash"),
        ([stale, _lib_line(NICK, "D:/gone/IC_New_TI.kicad_sym")], "table.external_clash"),
    ]
    for entries, code in cases:
        original = _sym_table(*entries)
        (tmp_path / "sym-lib-table").write_bytes(original)

        issues = _add_sym(tmp_path)

        assert [i.code for i in issues] == [code]
        assert (tmp_path / "sym-lib-table").read_bytes() == original
        assert not _backups(tmp_path)


def test_existing_library_never_adds_an_entry(tmp_path):
    original = _sym_table(_lib_line("Ext", "C:/ext/Ext.kicad_sym"))
    (tmp_path / "sym-lib-table").write_bytes(original)

    issues = tg.add_library_entries(
        tmp_path, symbol=(NICK, SYM_REL), footprint=(NICK, FP_REL), repo_root=tmp_path, add_missing=False
    )

    assert [(i.severity, i.code, i.text) for i in issues] == [
        (Severity.INFO, "table.not_listed", f"sym-lib-table does not list {NICK}"),
        (Severity.INFO, "table.not_listed", f"fp-lib-table does not list {NICK}"),
    ]
    assert (tmp_path / "sym-lib-table").read_bytes() == original
    assert not (tmp_path / "fp-lib-table").exists()
    assert not _backups(tmp_path)


def test_shared_footprint_entry_repointed(tmp_path):
    original = (
        b"(fp_lib_table\n  (version 7)\n"
        b'  (lib (name "Atomic_Footprints")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Gone/Footprints/Atomic_Footprints.pretty")(options "")(descr ""))\n'
        b")\n"
    )
    (tmp_path / "fp-lib-table").write_bytes(original)

    issues = tg.add_library_entries(tmp_path, footprint=(SHARED, SHARED_REL), repo_root=tmp_path)

    assert [i.text for i in issues if i.code == "table.entry_updated"] == [
        f"Updated: {SHARED} in fp-lib-table now points at {SHARED_REL}",
    ]
    assert (tmp_path / "fp-lib-table").read_bytes() == original.replace(
        b"Gone/Footprints/Atomic_Footprints.pretty", SHARED_REL.encode()
    )
    assert _backups(tmp_path) == ["fp-lib-table_backup_1"]
