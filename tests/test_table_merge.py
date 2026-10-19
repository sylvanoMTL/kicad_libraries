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


# -- classification of every table child (D-03, D-06..D-10) ----------------------------

EXT_DUP = '(lib (name "Dup")(type "KiCad")(uri "/ext/Dup.kicad_sym")(options "")(descr ""))'
EXT_ONE = '(lib (name "Ext")(type "KiCad")(uri "/e/Ext.kicad_sym"))'


def _parse(text: str) -> kicad_files.LoadedFile:
    loaded = kicad_files.parse_bytes(text.encode("utf-8"), "t")
    assert not isinstance(loaded, Issue)
    return loaded


def _codes(result) -> list[str]:
    return [i.code for i in result.issues]


def test_unclassifiable_children_are_kept_byte_identical_and_each_warned():
    text = (
        "(sym_lib_table\n"
        "  (version 7)\n"
        '  (lib (type "KiCad")(uri "/x"))\n'
        "  stray\n"
        "  (future_top 1)\n"
        f"  {_sym_entry('Fixture_A')}\n"
        ")\n"
    )
    result = tg.generate_sym_lib_table(
        [_sym("Fixture_A", selected=False), _sym("New")], _parse(text)
    )
    assert result.content == text.replace(_sym_entry("Fixture_A"), _sym_entry("New"))
    assert _codes(result) == ["table.unclassified"] * 3
    assert all(i.severity is Severity.WARNING for i in result.issues)
    for line, issue in zip((3, 4, 5), result.issues):
        assert f"line {line}" in issue.text
    # (version 7) is neither warned about nor counted
    assert result.preserved == 3


def test_version_child_is_not_warned_about_and_not_counted():
    result = tg.generate_sym_lib_table(
        [_sym("Fixture_A"), _sym("Fixture_B")], _load("basic.sym-lib-table")
    )
    assert result.issues == []
    assert result.preserved == 0


def test_lib_entry_with_a_non_token_value_is_kept_and_warned():
    entry = '(lib (name (x y))(type "KiCad")(uri "/x/Bad.kicad_sym"))'
    text = f"(sym_lib_table\n  (version 7)\n  {entry}\n)\n"
    result = tg.generate_sym_lib_table([_sym("New")], _parse(text))
    assert entry in result.content
    assert _codes(result) == ["table.unclassified"]
    assert result.preserved == 1


def test_selected_nickname_clashing_with_an_external_entry_is_not_written():
    text = f"(sym_lib_table\n  (version 7)\n  {EXT_DUP}\n)\n"
    result = tg.generate_sym_lib_table([_sym("Dup")], _parse(text))
    assert result.content == text
    assert (result.preserved, result.added) == (1, 0)
    (issue,) = result.issues
    assert (issue.severity, issue.code) == (Severity.WARNING, "table.external_clash")
    assert "/ext/Dup.kicad_sym" in issue.text
    assert "${KICAD_LIB_GITHUB}/" in issue.text


def test_clash_does_not_stop_other_selected_libraries_from_being_written():
    text = f"(sym_lib_table\n  (version 7)\n  {EXT_DUP}\n)\n"
    result = tg.generate_sym_lib_table([_sym("Dup"), _sym("New")], _parse(text))
    assert result.content == text[: -len(")\n")] + f"  {_sym_entry('New')}\n)\n"
    assert result.added == 1


def test_stale_managed_entry_warns_and_deselected_one_is_listed_as_removed():
    result = tg.generate_sym_lib_table(
        [_sym("Fixture_A", selected=False)], _load("basic.sym-lib-table")
    )
    assert result.content == "(sym_lib_table\n  (version 7)\n)\n"
    assert result.removed == ["Fixture_A"]
    (issue,) = result.issues
    assert (issue.severity, issue.code) == (Severity.WARNING, "table.stale_managed")
    assert "Fixture_B" in issue.text
    assert "Fixture_A" not in issue.text


def test_regenerated_managed_entries_that_carried_flags_warn_naming_them():
    result = tg.generate_fp_lib_table(
        [_fp("Disabled_Lib"), _fp("Hidden_Lib"), _fp("Future_Lib")],
        _load("flags.fp-lib-table"),
    )
    assert _codes(result) == ["table.managed_flags_dropped"] * 3
    assert all(i.severity is Severity.WARNING for i in result.issues)
    texts = [i.text for i in result.issues]
    assert "Disabled_Lib" in texts[0] and "disabled" in texts[0]
    assert "Hidden_Lib" in texts[1] and "hidden" in texts[1]
    assert "Future_Lib" in texts[2] and "future_field" in texts[2]
    assert "(disabled)" not in result.content and "future_field" not in result.content


def test_file_without_a_lib_table_is_refused():
    result = tg.generate_sym_lib_table([_sym("New")], _parse("(something_else)\n"))
    assert isinstance(result, Issue)
    assert (result.severity, result.code) == (Severity.ERROR, "table.unrecognised")


def test_two_selected_libraries_with_one_nickname_are_refused_naming_both_paths():
    a = SymbolLibrary("Same", "Custom/Symbols/Same.kicad_sym", "Custom", selected=True)
    b = SymbolLibrary("Same", "WurthElektronik/Symbols/Same.kicad_sym", "WurthElektronik",
                      selected=True)
    for existing in (None, _load("basic.sym-lib-table")):
        result = tg.generate_sym_lib_table([a, b], existing)
        assert isinstance(result, Issue)
        assert (result.severity, result.code) == (Severity.ERROR, "table.duplicate_nickname")
        assert a.rel_path in result.text and b.rel_path in result.text


def test_two_unselected_libraries_with_one_nickname_are_not_a_duplicate():
    a = SymbolLibrary("Same", "Custom/Symbols/Same.kicad_sym", "Custom", selected=True)
    b = SymbolLibrary("Same", "Other/Symbols/Same.kicad_sym", "Other", selected=False)
    assert not isinstance(tg.generate_sym_lib_table([a, b], None), Issue)


def test_generated_values_with_quote_and_backslash_round_trip_and_external_bytes_stay():
    name = 'We"ird' + "\\"
    lib = SymbolLibrary(name, f'Custom/Symbols/{name}.kicad_sym', "Custom", selected=True)
    loaded = _load("escaped.sym-lib-table")
    result = tg.generate_sym_lib_table([lib], loaded)
    entries = kicad_files.lib_table_entries(_parse(result.content).root)
    assert [e.name for e in entries] == ["Escaped_Lib", name]
    assert entries[1].uri == f"${{KICAD_LIB_GITHUB}}/{lib.rel_path}"
    external = (
        r'(lib (name "Escaped_Lib")(type "KiCad")(uri "C:\\KiCad\\libs\\Escaped.kicad_sym")'
        r'(options "")(descr "Has \"quotes\" and (parens)"))'
    )
    assert result.content.count(external) == 1


def test_managed_entry_sharing_its_line_with_an_external_one_loses_only_its_own_span():
    text = f"(sym_lib_table\n  (version 7)\n  {_sym_entry('Old')}{EXT_ONE}\n)\n"
    gone = tg.generate_sym_lib_table([_sym("Old", selected=False)], _parse(text))
    assert gone.content == f"(sym_lib_table\n  (version 7)\n  {EXT_ONE}\n)\n"
    kept = tg.generate_sym_lib_table([_sym("Old")], _parse(text))
    assert kept.content == (
        f"(sym_lib_table\n  (version 7)\n  {EXT_ONE}\n  {_sym_entry('Old')}\n)\n"
    )


def test_managed_entry_sharing_its_line_with_the_closing_paren_keeps_both_neighbours():
    text = f"(sym_lib_table\n  (version 7)\n  {EXT_ONE} {_sym_entry('Old')})\n"
    gone = tg.generate_sym_lib_table([_sym("Old", selected=False)], _parse(text))
    assert gone.content == f"(sym_lib_table\n  (version 7)\n  {EXT_ONE} )\n"
    new = tg.generate_sym_lib_table([_sym("New")], _parse(text))
    assert f"  {EXT_ONE} \n" in new.content
    assert new.content.endswith(f"  {_sym_entry('New')}\n)\n")


def test_block_lists_libraries_in_input_order_and_regeneration_is_byte_stable():
    libs = [_sym("Zed"), _sym("Alpha"), _sym("Mid")]
    first = tg.generate_sym_lib_table(libs, _load("basic.sym-lib-table"))
    names = [e.name for e in kicad_files.lib_table_entries(_parse(first.content).root)]
    assert names == ["Zed", "Alpha", "Mid"]
    second = tg.generate_sym_lib_table(libs, _parse(first.content))
    assert second.content == first.content
    assert second.issues == []
