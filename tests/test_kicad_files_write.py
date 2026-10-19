"""Write-side helpers of kicad_files: every KiCad change is one exact span edit (INST-01, INST-02, INST-03, INST-05)."""

import pytest

from kicad_lib_manager import kicad_files as kf
from kicad_lib_manager.kicad_files import LoadedFile, find_symbol, find_symbols, parse_bytes
from kicad_lib_manager.sexpr import Edit, apply_edits, unquote
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


# -- property primitives -----------------------------------------------------------


def _symbol(loaded: LoadedFile, name: str):
    ref = find_symbol(loaded.root, name)
    assert ref is not None
    return ref


def _prop(loaded: LoadedFile, symbol: str, prop: str):
    found = kf.find_property(_symbol(loaded, symbol).node, prop)
    assert found is not None, prop
    return found


def _prop_names(loaded: LoadedFile, symbol: str) -> list[str]:
    return [unquote(c.children[1].text) for c in _symbol(loaded, symbol).node.children if c.head == "property"]


def _parsed_property(text: str):
    """Parse one property block and return it as a PropertyRef."""
    root = _load(f'(symbol "S" {text})'.encode()).root
    name = unquote(root.children[0].children[2].children[1].text)
    return kf.find_property(root.children[0], name)


def _bare_symbol(*props: str) -> LoadedFile:
    body = "\n".join(props)
    return _load(f'(kicad_symbol_lib (version 20211014) (generator x)\n  (symbol "S"\n{body}\n  )\n)\n'.encode())


def _visible(name: str) -> str:
    return f'    (property "{name}" "v" (at 0 0 0) (effects (font (size 1 1))))'


def _hidden(name: str) -> str:
    return f'    (property "{name}" "v" (at 0 0 0) (effects (font (size 1 1)) hide))'


def test_property_rename_changes_only_name_token():
    loaded = _load(vendor_symbol_lib("PART", props={"MF": "Texas Instruments"}))
    prop = _prop(loaded, "PART", "MF")
    out = _apply(loaded, [kf.rename_property_edit(prop, "Manufacturer")])
    assert out == loaded.source.text.replace('(property "MF"', '(property "Manufacturer"')
    renamed = _prop(_reparse(out), "PART", "Manufacturer")
    assert renamed.value == "Texas Instruments"


def test_property_rename_quotes_the_new_name():
    loaded = _load(vendor_symbol_lib("PART", props={"MF": "x"}))
    out = _apply(loaded, [kf.rename_property_edit(_prop(loaded, "PART", "MF"), 'A"B)')])
    assert _prop(_reparse(out), "PART", 'A"B)').value == "x"


@pytest.mark.parametrize("version", [V6, V8, V9])
def test_property_is_hidden_follows_target_style(version):
    loaded = _load(target_lib(version))
    assert kf.property_is_hidden(_prop(loaded, "EXISTING_A", "Footprint")) is True
    assert kf.property_is_hidden(_prop(loaded, "EXISTING_A", "Reference")) is False


def test_property_is_hidden_false_for_hide_no_and_no_effects():
    loaded = _bare_symbol(
        '    (property "A" "v" (at 0 0 0) (effects (font (size 1 1)) (hide no)))',
        '    (property "B" "v" (at 0 0 0))',
        '    (property "C" "v" (at 0 0 0) (effects (font (size 1 1)) (hide yes)))',
    )
    assert kf.property_is_hidden(_prop(loaded, "S", "A")) is False
    assert kf.property_is_hidden(_prop(loaded, "S", "B")) is False
    assert kf.property_is_hidden(_prop(loaded, "S", "C")) is True


def test_hidden_template_prefers_datasheet_then_footprint():
    loaded = _bare_symbol(_visible("Reference"), _hidden("Footprint"), _hidden("Datasheet"), _hidden("zzz"))
    assert kf.hidden_template(_symbol(loaded, "S").node).name == "Datasheet"
    loaded = _bare_symbol(_visible("Datasheet"), _hidden("ki_keywords"), _hidden("Footprint"), _hidden("zzz"))
    assert kf.hidden_template(_symbol(loaded, "S").node).name == "Footprint"
    loaded = _bare_symbol(_hidden("zzz"), _hidden("ki_keywords"), _hidden("ki_fp_filters"))
    assert kf.hidden_template(_symbol(loaded, "S").node).name == "ki_fp_filters"
    loaded = _bare_symbol(_hidden("zzz"), _hidden("ki_keywords"))
    assert kf.hidden_template(_symbol(loaded, "S").node).name == "ki_keywords"


def test_hidden_template_falls_back_to_any_hidden_property():
    loaded = _bare_symbol(_visible("Reference"), _hidden("Other"), _hidden("Another"))
    assert kf.hidden_template(_symbol(loaded, "S").node).name == "Other"


def test_hidden_template_none_when_nothing_is_hidden():
    loaded = _bare_symbol(_visible("Reference"), _visible("Value"))
    assert kf.hidden_template(_symbol(loaded, "S").node) is None


def test_property_new_text_from_v6_template_has_next_id_and_bare_hide():
    loaded = _load(target_lib(V6))
    template = _prop(loaded, "EXISTING_A", "Footprint")
    block = kf.new_property_text(loaded.source.text, template, "MPN", "X1", 4, version=V6)
    assert "(id 4)" in block
    assert "(id 2)" not in block
    new = _parsed_property(block)
    assert (new.name, new.value) == ("MPN", "X1")
    assert kf.property_is_hidden(new)
    assert "(hide yes)" not in block


def test_property_new_text_from_v9_template_has_no_id_and_hide_yes():
    loaded = _load(target_lib(V9))
    template = _prop(loaded, "EXISTING_A", "Footprint")
    block = kf.new_property_text(loaded.source.text, template, "MPN", "X1", None, version=V9)
    assert "(id" not in block
    assert "(hide yes)" in block
    assert kf.property_is_hidden(_parsed_property(block))


@pytest.mark.parametrize("version,marker", [(V6, " hide)"), (V8, "(hide yes)"), (V9, "(hide yes)")])
def test_property_new_text_always_hidden_from_visible_template(version, marker):
    loaded = _load(target_lib(version))
    template = _prop(loaded, "EXISTING_A", "Reference")
    assert not kf.property_is_hidden(template)
    block = kf.new_property_text(loaded.source.text, template, "MPN", "X1", 7 if version == V6 else None, version=version)
    new = _parsed_property(block)
    assert kf.property_is_hidden(new)
    assert marker in block
    assert block.count("hide") == 1


def test_property_new_text_without_version_keeps_template_style():
    loaded = _load(target_lib(V6))
    template = _prop(loaded, "EXISTING_A", "Footprint")
    plain = kf.new_property_text(loaded.source.text, template, "MPN", "X1", 4)
    assert "(id 4)" in plain and kf.property_is_hidden(_parsed_property(plain))
    visible = kf.new_property_text(loaded.source.text, _prop(loaded, "EXISTING_A", "Value"), "MPN", "X1", 4)
    assert kf.property_is_hidden(_parsed_property(visible))
    assert "(hide yes)" not in visible


def test_property_new_text_turns_hide_no_into_hidden():
    loaded = _bare_symbol('    (property "A" "v" (at 0 0 0) (effects (font (size 1 1)) (hide no)))')
    block = kf.new_property_text(loaded.source.text, _prop(loaded, "S", "A"), "MPN", "X", None, version=V9)
    assert kf.property_is_hidden(_parsed_property(block))
    assert block.count("hide") == 1


def test_property_synth_v6_has_id_and_bare_hide():
    text = kf.synth_property_text("MPN", "X", version=V6, next_id=7)
    assert "(id 7)" in text
    assert " hide)" in text
    assert "(hide yes)" not in text
    new = _parsed_property(text)
    assert (new.name, new.value) == ("MPN", "X")
    assert kf.property_is_hidden(new)


def test_property_synth_v9_has_hide_yes_and_no_id():
    text = kf.synth_property_text("MPN", "X", version=V9, next_id=7)
    assert "(hide yes)" in text
    assert "(id" not in text
    assert kf.property_is_hidden(_parsed_property(text))


def test_property_synth_boundary_versions():
    assert "hide yes" not in kf.synth_property_text("N", "v", version=20231119, next_id=None)
    assert "(hide yes)" in kf.synth_property_text("N", "v", version=20231120, next_id=None)
    assert "(id 3)" in kf.synth_property_text("N", "v", version=20220913, next_id=3)
    assert "(id" not in kf.synth_property_text("N", "v", version=20220914, next_id=3)
    assert "(id" not in kf.synth_property_text("N", "v", version=V6, next_id=None)


def test_property_synth_escapes_quotes_in_name_and_value():
    text = kf.synth_property_text('N"x', 'a"b)\\(c', version=V9, next_id=None)
    new = _parsed_property(text)
    assert (new.name, new.value) == ('N"x', 'a"b)\\(c')


def test_description_name_keeps_existing_property():
    loaded = _load(target_lib(V8))
    assert kf.description_field_name(_symbol(loaded, "EXISTING_A").node, V6) == "Description"
    loaded = _bare_symbol(_hidden("ki_description"))
    assert kf.description_field_name(_symbol(loaded, "S").node, V9) == "ki_description"


@pytest.mark.parametrize(
    "version,expected",
    [(V6, "ki_description"), (20230619, "ki_description"), (20230620, "Description"), (V8, "Description"), (None, "Description")],
)
def test_description_name_by_version_when_absent(version, expected):
    loaded = _bare_symbol(_hidden("Footprint"))
    assert kf.description_field_name(_symbol(loaded, "S").node, version) == expected


@pytest.mark.parametrize("version", [V6, V8])
def test_property_two_inserts_in_one_apply_keep_order(version):
    target = _load(target_lib(version))
    symbol = _symbol(target, "EXISTING_A")
    template = kf.hidden_template(symbol.node)
    next_id = kf.next_property_id(symbol.node)
    text, eol = target.source.text, target.source.eol
    first = kf.new_property_text(text, template, "Manufacturer", "TI", next_id, version=version)
    second = kf.new_property_text(text, template, "MPN", "X1", None if next_id is None else next_id + 1, version=version)
    edits = [
        kf.property_insert_edit(text, symbol.node, first, eol),
        kf.property_insert_edit(text, symbol.node, second, eol),
    ]
    out = _apply(target, edits)
    after = _reparse(out)
    names = _prop_names(after, "EXISTING_A")
    assert names[-2:] == ["Manufacturer", "MPN"]
    assert names[-3] in ("Datasheet", "Description")
    assert _prop_names(after, "EXISTING_B") == _prop_names(target, "EXISTING_B")
    assert _prop(after, "EXISTING_A", "MPN").value == "X1"
