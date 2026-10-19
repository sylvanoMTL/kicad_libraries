"""Span-splice merge of lib tables over the frozen table fixtures, plus the lossless table reader."""

from pathlib import Path

import pytest

from kicad_lib_manager import kicad_files
from kicad_lib_manager import table_generator as tg
from kicad_lib_manager.models import FootprintLibrary, Issue, Severity, SymbolLibrary

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tables"


def _load(name: str) -> kicad_files.LoadedFile:
    loaded = kicad_files.parse_bytes((FIXTURES / name).read_bytes(), name)
    assert not isinstance(loaded, Issue)
    return loaded


def _sym(name: str, selected: bool = True) -> SymbolLibrary:
    return SymbolLibrary(name, f"Custom/Symbols/{name}.kicad_sym", "Custom", selected=selected)


def _fp(name: str, selected: bool = True) -> FootprintLibrary:
    return FootprintLibrary(name, f"Custom/Footprints/{name}.pretty", "Custom", selected=selected)


def _sym_entry(name: str) -> str:
    return (
        f'(lib (name "{name}")(type "KiCad")'
        f'(uri "${{KICAD_LIB_GITHUB}}/Custom/Symbols/{name}.kicad_sym")(options "")(descr ""))'
    )


def _fp_entry(name: str) -> str:
    return (
        f'(lib (name "{name}")(type "KiCad")'
        f'(uri "${{KICAD_LIB_GITHUB}}/Custom/Footprints/{name}.pretty")(options "")(descr ""))'
    )


def test_basic_places_block_where_first_managed_entry_was():
    loaded = _load("basic.sym-lib-table")
    result = tg.generate_sym_lib_table(
        [_sym("Fixture_A"), _sym("New"), _sym("Fixture_B", selected=False)], loaded
    )
    assert result.content == (
        "(sym_lib_table\n"
        "  (version 7)\n"
        f"  {_sym_entry('Fixture_A')}\n"
        f"  {_sym_entry('New')}\n"
        ")\n"
    )
    assert (result.preserved, result.added, result.removed) == (0, 2, ["Fixture_B"])


def test_flags_fixture_keeps_crlf_and_regenerates_managed_entries():
    loaded = _load("flags.fp-lib-table")
    result = tg.generate_fp_lib_table(
        [_fp("Disabled_Lib"), _fp("Hidden_Lib", selected=False),
         _fp("Future_Lib", selected=False)],
        loaded,
    )
    assert result.content == (
        "(fp_lib_table\r\n"
        "  (version 7)\r\n"
        f"  {_fp_entry('Disabled_Lib')}\r\n"
        ")\r\n"
    )
    assert result.removed == ["Hidden_Lib", "Future_Lib"]


def test_reordered_fixture_replaces_two_line_managed_entry_and_keeps_external_bytes():
    loaded = _load("reordered.fp-lib-table")
    result = tg.generate_fp_lib_table([_fp("Reordered")], loaded)
    assert result.content == (
        "(fp_lib_table\n"
        "  (version 7)\n"
        f"  {_fp_entry('Reordered')}\n"
        '  (lib (name "Minimal")(type "KiCad")(uri "/abs/path/Minimal.pretty"))\n'
        ")\n"
    )
    assert (result.preserved, result.added, result.removed) == (1, 1, [])


def test_escaped_fixture_inserts_on_own_line_before_closing_paren():
    loaded = _load("escaped.sym-lib-table")
    original = loaded.source.text
    result = tg.generate_sym_lib_table([_sym("New")], loaded)
    assert result.content == original[: -len(")\r\n")] + f"  {_sym_entry('New')}\r\n" + ")\r\n"
    assert "\n" not in result.content.replace("\r\n", "")
    # The external descr (escaped quotes and parens) is kept once, byte for byte
    descr = r'(descr "Has \"quotes\" and (parens)")'
    assert original.count(descr) == 1
    assert result.content.count(descr) == 1
    assert result.preserved == 1


def test_empty_fixture_inserts_before_closing_paren():
    loaded = _load("empty.sym-lib-table")
    result = tg.generate_sym_lib_table([_sym("New")], loaded)
    assert result.content == (
        "(sym_lib_table\n"
        "  (version 7)\n"
        f"  {_sym_entry('New')}\n"
        ")\n"
    )


def test_closing_paren_sharing_a_line_gets_its_own_line():
    loaded = kicad_files.parse_bytes(b"(sym_lib_table\n  (version 7))\n", "t")
    result = tg.generate_sym_lib_table([_sym("New")], loaded)
    assert result.content == (
        "(sym_lib_table\n"
        "  (version 7)\n"
        f"  {_sym_entry('New')}\n"
        ")\n"
    )


def test_no_selection_removes_managed_entries_and_inserts_nothing():
    loaded = _load("basic.sym-lib-table")
    result = tg.generate_sym_lib_table(
        [_sym("Fixture_A", selected=False), _sym("Fixture_B", selected=False)], loaded
    )
    assert result.content == "(sym_lib_table\n  (version 7)\n)\n"
    assert result.removed == ["Fixture_A", "Fixture_B"]


def test_missing_or_blank_table_gets_fresh_layout():
    fresh = "(sym_lib_table\n" f"  {_sym_entry('New')}\n" ")\n"
    assert tg.generate_sym_lib_table([_sym("New")], None).content == fresh
    blank = kicad_files.parse_bytes(b" \r\n\t\n", "t")
    assert tg.generate_sym_lib_table([_sym("New")], blank).content == fresh


def test_wrong_table_tag_is_refused_with_an_error_issue():
    loaded = _load("flags.fp-lib-table")
    result = tg.generate_sym_lib_table([_sym("New")], loaded)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "table.unrecognised"


def test_library_name_with_quote_and_backslash_round_trips():
    name = 'We"ird\\Lib'
    result = tg.generate_sym_lib_table([_sym(name)], _load("escaped.sym-lib-table"))
    parsed = kicad_files.parse_bytes(result.content.encode("utf-8"), "t")
    names = [e.name for e in kicad_files.lib_table_entries(parsed.root)]
    assert names == ["Escaped_Lib", name]


def test_lib_table_accessor_exposes_tag_entries_and_other_children():
    table = kicad_files.lib_table(_load("basic.sym-lib-table").root)
    assert table.tag == "sym_lib_table"
    assert [e.name for e in table.entries] == ["Fixture_A", "Fixture_B"]
    assert [n.head for n in table.others] == ["version"]
    assert kicad_files.lib_table(kicad_files.parse_bytes(b"(foo)", "t").root) is None


def test_table_info_reads_counts_and_managed_tails(tmp_path):
    path = tmp_path / "sym-lib-table"
    path.write_bytes((FIXTURES / "basic.sym-lib-table").read_bytes())
    info = tg.table_info(path)
    assert info == tg.TableInfo(
        entry_count=2,
        managed=frozenset({
            "Custom/Symbols/Fixture_A.kicad_sym",
            "Custom/Symbols/Fixture_B.kicad_sym",
        }),
    )


def test_table_info_missing_file_is_none(tmp_path):
    assert tg.table_info(tmp_path / "sym-lib-table") is None


def test_table_info_unbalanced_file_is_an_error_issue(tmp_path):
    path = tmp_path / "sym-lib-table"
    path.write_bytes(b"(sym_lib_table\n  (version 7)\n")
    info = tg.table_info(path)
    assert isinstance(info, Issue)
    assert info.severity is Severity.ERROR


def test_table_info_file_without_a_table_is_unrecognised(tmp_path):
    path = tmp_path / "sym-lib-table"
    path.write_bytes(b"(something_else)\n")
    info = tg.table_info(path)
    assert isinstance(info, Issue)
    assert info.code == "table.unrecognised"
