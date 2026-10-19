"""Write-side helpers of kicad_files: every KiCad change is one exact span edit (INST-01, INST-02, INST-03, INST-05)."""

import pytest

from kicad_lib_manager import kicad_files as kf
from kicad_lib_manager.kicad_files import LoadedFile, find_symbol, find_symbols, parse_bytes
from kicad_lib_manager.sexpr import Edit, apply_edits
from installfixtures import extends_pair, target_lib, vendor_footprint, vendor_symbol_lib

V6 = 20211014
V8 = 20231120
V9 = 20241209


def _load(data: bytes) -> LoadedFile:
    loaded = parse_bytes(data, "fixture")
    assert isinstance(loaded, LoadedFile), loaded
    return loaded


def _apply(loaded: LoadedFile, edits: list[Edit]) -> str:
    return apply_edits(loaded.source.text, edits)


def _reparse(text: str) -> LoadedFile:
    return _load(text.encode("utf-8"))


def _names(loaded: LoadedFile) -> list[str]:
    return [ref.name for ref in find_symbols(loaded.root)]


def _sub_names(loaded: LoadedFile, name: str) -> list[str]:
    from kicad_lib_manager.sexpr import unquote

    ref = find_symbol(loaded.root, name)
    return [unquote(c.children[1].text) for c in ref.node.children if c.head == "symbol"]


def _combine(first: bytes, second: bytes, eol: str = "\r\n") -> bytes:
    """Join two single-symbol vendor libraries into one library holding both symbols."""
    a = first.decode("utf-8")
    b = second.decode("utf-8")
    body = b.split(eol, 1)[1]
    assert a.endswith(")" + eol) and body.endswith(")" + eol)
    return (a[: -len(")" + eol)] + body).encode("utf-8")


# -- rename ---------------------------------------------------------------------


def test_rename_follows_sub_symbols():
    loaded = _load(vendor_symbol_lib("PART", units=2))
    edits = kf.rename_symbol_edits(loaded.root, "PART", "NEW")
    out = _apply(loaded, edits)
    expected = vendor_symbol_lib("NEW", units=2, value="PART").decode("utf-8")
    assert out == expected
    after = _reparse(out)
    assert _names(after) == ["NEW"]
    assert _sub_names(after, "NEW") == ["NEW_1_1", "NEW_2_1"]


def test_rename_follows_extends():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    out = _apply(loaded, kf.rename_symbol_edits(loaded.root, "PARENT_X", "P2"))
    before = loaded.source.text
    expected = (
        before.replace('(symbol "PARENT_X"', '(symbol "P2"')
        .replace('"PARENT_X_1_1"', '"P2_1_1"')
        .replace('(extends "PARENT_X")', '(extends "P2")')
    )
    assert out == expected
    after = _reparse(out)
    assert _names(after) == ["P2", "CHILD_Y"]
    child = find_symbol(after.root, "CHILD_Y")
    assert kf.extends_name(child.node) == "P2"


def test_rename_child_touches_only_child_name():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    out = _apply(loaded, kf.rename_symbol_edits(loaded.root, "CHILD_Y", "KID"))
    assert out == loaded.source.text.replace('(symbol "CHILD_Y"', '(symbol "KID"')
    assert _names(_reparse(out)) == ["PARENT_X", "KID"]


def test_rename_never_by_substring():
    data = _combine(
        vendor_symbol_lib("PART", datasheet="https://example.com/PART/PART.pdf"),
        vendor_symbol_lib("PARTX", datasheet="https://example.com/PARTX.pdf"),
    )
    loaded = _load(data)
    out = _apply(loaded, kf.rename_symbol_edits(loaded.root, "PART", "NEW"))
    after = _reparse(out)
    assert _names(after) == ["NEW", "PARTX"]
    assert _sub_names(after, "PARTX") == ["PARTX_1_1"]
    assert _sub_names(after, "NEW") == ["NEW_1_1"]
    assert "https://example.com/PART/PART.pdf" in out
    assert "https://example.com/PARTX.pdf" in out


def test_rename_same_name_no_edits():
    loaded = _load(vendor_symbol_lib("PART"))
    assert kf.rename_symbol_edits(loaded.root, "PART", "PART") == []


def test_rename_without_subs():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    edits = kf.rename_symbol_edits(loaded.root, "CHILD_Y", "KID")
    assert len(edits) == 1
    assert loaded.source.text[edits[0].start : edits[0].end] == '"CHILD_Y"'


def test_rename_missing_symbol_no_edits():
    loaded = _load(vendor_symbol_lib("PART"))
    assert kf.rename_symbol_edits(loaded.root, "OTHER", "NEW") == []


def test_rename_quoted_name_round_trip():
    odd = 'A"B\\C'
    loaded = _load(vendor_symbol_lib(odd))
    assert _names(loaded) == [odd]
    out = _apply(loaded, kf.rename_symbol_edits(loaded.root, odd, 'N"1'))
    after = _reparse(out)
    assert _names(after) == ['N"1']
    assert _sub_names(after, 'N"1') == ['N"1_1_1']


def test_rename_is_case_sensitive():
    loaded = _load(vendor_symbol_lib("part"))
    assert kf.rename_symbol_edits(loaded.root, "PART", "NEW") == []


def test_rename_sub_symbol_pattern_is_anchored():
    # PART_A_1 and PART_1_1_X are not unit symbols of PART
    text = (
        '(kicad_symbol_lib (version 20211014) (generator x)\n'
        '  (symbol "PART" (in_bom yes)\n'
        '    (symbol "PART_1_1")\n'
        '    (symbol "PART_A_1")\n'
        '    (symbol "PART_1_1_X")\n'
        '    (symbol "XPART_1_1")\n'
        '  )\n'
        ')\n'
    )
    loaded = _load(text.encode())
    out = _apply(loaded, kf.rename_symbol_edits(loaded.root, "PART", "NEW"))
    assert _sub_names(_reparse(out), "NEW") == ["NEW_1_1", "PART_A_1", "PART_1_1_X", "XPART_1_1"]


def test_replace_exact_tokens():
    assert kf.replace_exact_tokens("PART power PARTX", "PART", "NEW") == "NEW power PARTX"
    assert kf.replace_exact_tokens("PART", "PART", "NEW") == "NEW"
    assert kf.replace_exact_tokens("a  PART   b", "PART", "NEW") == "a  NEW   b"
    assert kf.replace_exact_tokens("part PARTS", "PART", "NEW") == "part PARTS"
    assert kf.replace_exact_tokens("", "PART", "NEW") == ""


# -- unit extraction --------------------------------------------------------------


def test_unit_follows_extends_parent_first():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    unit = kf.symbol_unit(loaded.root, "CHILD_Y")
    assert [ref.name for ref in unit] == ["PARENT_X", "CHILD_Y"]


def test_unit_child_first_in_file_still_parent_first():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y", child_first=True))
    unit = kf.symbol_unit(loaded.root, "CHILD_Y")
    assert [ref.name for ref in unit] == ["PARENT_X", "CHILD_Y"]


def test_unit_of_lone_symbol_and_of_parent():
    loaded = _load(vendor_symbol_lib("PART"))
    assert [ref.name for ref in kf.symbol_unit(loaded.root, "PART")] == ["PART"]
    pair = _load(extends_pair("PARENT_X", "CHILD_Y"))
    assert [ref.name for ref in kf.symbol_unit(pair.root, "PARENT_X")] == ["PARENT_X"]


def test_unit_unknown_name_is_none():
    loaded = _load(vendor_symbol_lib("PART"))
    assert kf.symbol_unit(loaded.root, "NOPE") is None


def test_unit_missing_parent_is_none():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    # Drop the parent from the file, keeping only the child
    text = kf.unit_library_text(loaded, {"CHILD_Y"})
    assert kf.symbol_unit(_reparse(text).root, "CHILD_Y") is None


def test_unit_cycle_is_none():
    text = (
        '(kicad_symbol_lib (version 20211014) (generator x)\n'
        '  (symbol "A" (extends "B"))\n'
        '  (symbol "B" (extends "A"))\n'
        '  (symbol "S" (extends "S"))\n'
        ')\n'
    )
    loaded = _load(text.encode())
    assert kf.symbol_unit(loaded.root, "A") is None
    assert kf.symbol_unit(loaded.root, "B") is None
    assert kf.symbol_unit(loaded.root, "S") is None


def test_unit_extends_name_reads_unquoted_token():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    assert kf.extends_name(find_symbol(loaded.root, "CHILD_Y").node) == "PARENT_X"
    assert kf.extends_name(find_symbol(loaded.root, "PARENT_X").node) is None


def test_unit_library_text_keeps_only_named_symbols():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y"))
    assert kf.unit_library_text(loaded, {"PARENT_X"}) == vendor_symbol_lib("PARENT_X").decode("utf-8")
    both = kf.unit_library_text(loaded, {"PARENT_X", "CHILD_Y"})
    assert both == loaded.source.text


def test_unit_library_text_removes_symbol_before_kept_one_without_blank_line():
    loaded = _load(extends_pair("PARENT_X", "CHILD_Y", child_first=True))
    out = kf.unit_library_text(loaded, {"PARENT_X"})
    assert out == vendor_symbol_lib("PARENT_X").decode("utf-8")
    assert "\r\n\r\n" not in out


def test_unit_library_text_keeps_header_of_empty_keep():
    loaded = _load(target_lib(V8, names=("A", "B")))
    out = kf.unit_library_text(loaded, set())
    after = _reparse(out)
    assert _names(after) == []
    assert out.startswith("(kicad_symbol_lib")
    assert "(generator_version" in out


# -- replace and insert-before ------------------------------------------------------


def test_replace_swaps_exactly_the_old_block():
    target = _load(target_lib(V6, names=("EXISTING_A", "EXISTING_B")))
    ref = find_symbol(target.root, "EXISTING_A")
    vendor = _load(vendor_symbol_lib("NEW"))
    new_block = kf.block_text(vendor.source.text, find_symbol(vendor.root, "NEW").node)
    edit = kf.symbol_replace_edit(target, ref, new_block)
    out = _apply(target, [edit])
    text = target.source.text
    assert out.startswith(text[: ref.node.start])
    assert out.endswith(text[ref.node.end :])
    assert _names(_reparse(out)) == ["NEW", "EXISTING_B"]


def test_replace_normalises_block_eol_to_target():
    target = _load(target_lib(V6, names=("EXISTING_A",)))
    assert target.source.eol == "\r\n"
    ref = find_symbol(target.root, "EXISTING_A")
    out = _apply(target, [kf.symbol_replace_edit(target, ref, '(symbol "N"\n  (in_bom yes)\n)')])
    assert "\n" not in out.replace("\r\n", "")
    assert '(symbol "N"\r\n  (in_bom yes)\r\n)' in out


def test_insert_before_uses_indent_and_eol():
    target = _load(target_lib(V6, names=("EXISTING_A", "EXISTING_B")))
    before = find_symbol(target.root, "EXISTING_B")
    block = '(symbol "NEW" (in_bom yes))'
    out = _apply(target, [kf.symbol_insert_before_edit(target, before, block)])
    text = target.source.text
    assert out == text[: before.node.start] + block + "\r\n  " + text[before.node.start :]
    assert _names(_reparse(out)) == ["EXISTING_A", "NEW", "EXISTING_B"]


def test_insert_before_in_tab_indented_lf_library():
    target = _load(target_lib(V9, names=("EXISTING_A", "EXISTING_B")))
    before = find_symbol(target.root, "EXISTING_A")
    block = '(symbol "NEW"\r\n\t(in_bom yes)\r\n)'
    out = _apply(target, [kf.symbol_insert_before_edit(target, before, block)])
    assert '(symbol "NEW"\n\t(in_bom yes)\n)\n\t(symbol "EXISTING_A"' in out
    assert "\r" not in out
    assert _names(_reparse(out)) == ["NEW", "EXISTING_A", "EXISTING_B"]
