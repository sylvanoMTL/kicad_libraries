import hashlib
import os
from pathlib import Path

import pytest

from kicad_lib_manager.fsutil import atomic_write_bytes, encode_source, read_source
from kicad_lib_manager.kicad_files import find_property, find_symbols
from kicad_lib_manager.models import Issue
from kicad_lib_manager.sexpr import Edit, apply_edits, parse, quote

REPO_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_SYMBOL = REPO_ROOT / "Custom" / "Symbols" / "Connector_USB_GCT.kicad_sym"

NEW_VALUE = "NEW (VAL)"


def _generated_crlf_bytes() -> bytes:
    lines = [
        '(kicad_symbol_lib (version 20211014) (generator "test")',
        '  (symbol "ONE" (in_bom yes) (on_board yes)',
        '    (property "Reference" "U" (id 0) (at 0 0 0))',
        '    (property "Value" "ONE_VAL" (id 1) (at 0 0 0))',
        '  )',
        '  (symbol "TWO" (in_bom yes) (on_board yes)',
        '    (property "Reference" "U" (id 0) (at 0 0 0))',
        '    (property "Value" "A (1) \\"q\\"" (id 1) (at 0 0 0))',
        '  )',
        ')',
        '',
    ]
    return b"\r\n".join(line.encode("utf-8") for line in lines)


def _edit_value(path: Path, symbol_index: int) -> tuple[bytes, bytes, int, int, str]:
    """Edit one symbol's Value in place; return (old bytes, new bytes, byte start, byte end, old value)."""
    old_bytes = path.read_bytes()

    src = read_source(path)
    assert not isinstance(src, Issue)
    root = parse(src.text)
    symbols = find_symbols(root)
    prop = find_property(symbols[symbol_index].node, "Value")
    assert prop is not None

    edit = Edit(prop.value_node.start, prop.value_node.end, quote(NEW_VALUE))
    new_text = apply_edits(src.text, [edit])
    issue = atomic_write_bytes(path, encode_source(new_text, src.bom))
    assert issue is None

    bom_len = 3 if src.bom else 0
    byte_start = bom_len + len(src.text[:prop.value_node.start].encode("utf-8"))
    byte_end = bom_len + len(src.text[:prop.value_node.end].encode("utf-8"))
    return old_bytes, path.read_bytes(), byte_start, byte_end, prop.value


def _assert_only_span_changed(old: bytes, new: bytes, start: int, end: int) -> None:
    encoded = quote(NEW_VALUE).encode("utf-8")
    assert new[:start] == old[:start]
    assert new[start:start + len(encoded)] == encoded
    assert new[start + len(encoded):] == old[end:]
    assert new.count(b"\r\n") == old.count(b"\r\n")
    # Bare LF and bare CR counts are unchanged too (zero for a pure-CRLF file)
    assert new.count(b"\n") - new.count(b"\r\n") == old.count(b"\n") - old.count(b"\r\n")
    assert new.count(b"\r") - new.count(b"\r\n") == old.count(b"\r") - old.count(b"\r\n")


def test_tracer_value_edit_generated_crlf(tmp_path):
    target = tmp_path / "gen.kicad_sym"
    target.write_bytes(_generated_crlf_bytes())

    old, new, start, end, old_value = _edit_value(target, 1)

    assert old_value == 'A (1) "q"'
    _assert_only_span_changed(old, new, start, end)

    src = read_source(target)
    assert not isinstance(src, Issue)
    first, second = find_symbols(parse(src.text))
    assert find_property(second.node, "Value").value == NEW_VALUE
    assert find_property(first.node, "Value").value == "ONE_VAL"
    assert os.listdir(tmp_path) == ["gen.kicad_sym"]


def test_tracer_value_edit_real_custom_symbol(tmp_path):
    if not CUSTOM_SYMBOL.exists():
        pytest.skip("Custom submodule not checked out (git submodule update --init Custom)")
    before = hashlib.sha256(CUSTOM_SYMBOL.read_bytes()).hexdigest()

    target = tmp_path / CUSTOM_SYMBOL.name
    target.write_bytes(CUSTOM_SYMBOL.read_bytes())

    old, new, start, end, _ = _edit_value(target, 0)

    _assert_only_span_changed(old, new, start, end)
    assert os.listdir(tmp_path) == [CUSTOM_SYMBOL.name]
    assert hashlib.sha256(CUSTOM_SYMBOL.read_bytes()).hexdigest() == before
