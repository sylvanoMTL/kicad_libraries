import hashlib
import os
import zipfile
from pathlib import Path

import pytest

from kicad_lib_manager.fsutil import (
    atomic_write_bytes,
    decode_source,
    encode_source,
    normalize_eol,
    read_source,
)
from kicad_lib_manager.kicad_files import (
    find_models,
    find_property,
    find_symbols,
    footprint_name,
    lib_table_entries,
)
from kicad_lib_manager import kicad_files
from kicad_lib_manager.models import Issue
from kicad_lib_manager.sexpr import Edit, apply_edits, parse, quote

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CUSTOM_SYMBOL = REPO_ROOT / "Custom" / "Symbols" / "Connector_USB_GCT.kicad_sym"
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
UL_SYMBOL_MEMBER = "KiCADv6/2026-10-18_09-12-49.kicad_sym"
MAX_ZIP_MEMBER = 5 * 1024 * 1024
CUSTOM_SKIP = "Custom submodule not checked out (git submodule update --init Custom)"

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


def _assert_tracer_span_changed(old: bytes, new: bytes, start: int, end: int) -> None:
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
    _assert_tracer_span_changed(old, new, start, end)

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

    _assert_tracer_span_changed(old, new, start, end)
    assert os.listdir(tmp_path) == [CUSTOM_SYMBOL.name]
    assert hashlib.sha256(CUSTOM_SYMBOL.read_bytes()).hexdigest() == before


# -- FOUND-04 full suite -------------------------------------------------------


def _eol_counts(text: str) -> tuple[int, int, int]:
    """Return (CRLF, bare LF, bare CR) counts."""
    crlf = text.count("\r\n")
    return crlf, text.count("\n") - crlf, text.count("\r") - crlf


def _assert_only_span_changed(
    old: str, new: str, start: int, old_end: int, replacement: str
) -> None:
    assert new[:start] == old[:start]
    assert new[start:start + len(replacement)] == replacement
    assert new[start + len(replacement):] == old[old_end:]
    # Line endings outside the replaced span are untouched: counts match once the span is removed
    outside_old = _eol_counts(old[:start] + old[old_end:])
    outside_new = _eol_counts(new[:start] + new[start + len(replacement):])
    assert outside_new == outside_old


def _first_value_edit(text: str, index: int = 0) -> tuple[int, int, str]:
    """Locate the Value token of the index-th top-level symbol; return (start, end, replacement)."""
    symbols = find_symbols(parse(text))
    prop = find_property(symbols[index].node, "Value")
    assert prop is not None
    return prop.value_node.start, prop.value_node.end, quote("EDITED (1)")


def _fixture_bytes(rel: str) -> bytes:
    return (FIXTURES_DIR / rel).read_bytes()


def _ul_symbol_bytes() -> bytes:
    with zipfile.ZipFile(UL_ZIP) as z:
        assert z.getinfo(UL_SYMBOL_MEMBER).file_size < MAX_ZIP_MEMBER
        return z.read(UL_SYMBOL_MEMBER)


def _symbol_inputs() -> list:
    params = [
        pytest.param("fixture", name, id=name)
        for name in ("lf", "crlf", "bom", "mixed_eol", "escapes")
    ]
    custom = REPO_ROOT / "Custom"
    live = sorted(custom.rglob("*.kicad_sym")) if custom.is_dir() else []
    if live:
        params += [
            pytest.param("live", path, id=f"custom-{path.relative_to(custom).as_posix()}")
            for path in live
        ]
    else:
        params.append(pytest.param("skip", None, id="custom-absent"))
    params.append(pytest.param("zip", None, id="ul-zip-member"))
    return params


@pytest.mark.parametrize(("kind", "ref"), _symbol_inputs())
def test_value_edit_changes_only_its_span(kind, ref):
    if kind == "skip":
        pytest.skip(CUSTOM_SKIP)
    if kind == "fixture":
        name, data = f"{ref}.kicad_sym", _fixture_bytes(f"sexpr/{ref}.kicad_sym")
    elif kind == "live":
        name, data = ref.name, ref.read_bytes()
    else:
        name, data = "ul.kicad_sym", _ul_symbol_bytes()

    src = decode_source(data, name)
    assert not isinstance(src, Issue)
    start, end, replacement = _first_value_edit(src.text)
    new = apply_edits(src.text, [Edit(start, end, replacement)])

    _assert_only_span_changed(src.text, new, start, end, replacement)
    assert _eol_counts(new) == _eol_counts(src.text)
    encoded = encode_source(new, src.bom)
    assert encoded.startswith(b"\xef\xbb\xbf") == data.startswith(b"\xef\xbb\xbf")
    # Round trip: an unedited re-encode reproduces the input exactly (inputs are never written)
    assert encode_source(src.text, src.bom) == data


_MATRIX_LINES = [
    '(kicad_symbol_lib (version 20241209) (generator "test")',
    '\t(symbol "ONE" (in_bom yes) (on_board yes)',
    '\t\t(property "Value" "ONE_VAL" (at 0 0 0))',
    '\t\t(property "Footprint" "Lib:ONE" (at 0 0 0))',
    "\t)",
    '\t(symbol "TWO" (in_bom yes) (on_board yes)',
    '\t\t(property "Value" "TWO_VAL" (at 0 0 0))',
    '\t\t(property "Footprint" "Lib:TWO" (at 0 0 0))',
    "\t)",
    ")",
]


def _matrix_bytes(eol_variant: str, bom: bool) -> bytes:
    n = len(_MATRIX_LINES)
    if eol_variant == "lf":
        endings = ["\n"] * n
    elif eol_variant == "crlf":
        endings = ["\r\n"] * n
    else:
        # CRLF majority (8 vs 2); the second symbol's header and Value lines are LF
        endings = ["\n" if i in (5, 6) else "\r\n" for i in range(n)]
    text = "".join(line + e for line, e in zip(_MATRIX_LINES, endings))
    data = text.encode("utf-8")
    return b"\xef\xbb\xbf" + data if bom else data


@pytest.mark.parametrize("which", [0, 1])
@pytest.mark.parametrize("bom", [False, True], ids=["nobom", "bom"])
@pytest.mark.parametrize("variant", ["lf", "crlf", "mixed"])
def test_eol_bom_matrix_roundtrip(tmp_path, variant, bom, which):
    target = tmp_path / f"{variant}.kicad_sym"
    original = _matrix_bytes(variant, bom)
    target.write_bytes(original)

    src = read_source(target)
    assert not isinstance(src, Issue)
    assert src.bom is bom
    start, end, replacement = _first_value_edit(src.text, which)
    new_text = apply_edits(src.text, [Edit(start, end, replacement)])
    assert atomic_write_bytes(target, encode_source(new_text, src.bom)) is None

    written = target.read_bytes()
    bom_len = 3 if bom else 0
    byte_start = bom_len + len(src.text[:start].encode("utf-8"))
    byte_end = bom_len + len(src.text[:end].encode("utf-8"))
    encoded = replacement.encode("utf-8")
    assert written[:byte_start] == original[:byte_start]
    assert written[byte_start:byte_start + len(encoded)] == encoded
    assert written[byte_start + len(encoded):] == original[byte_end:]
    assert written.startswith(b"\xef\xbb\xbf") is bom
    assert _eol_counts(written.decode("utf-8")) == _eol_counts(original.decode("utf-8"))
    assert os.listdir(tmp_path) == [target.name]

    if variant == "mixed":
        codes = [i.code for i in src.issues]
        assert codes == ["fs.mixed_eol"]
        assert target.name in src.issues[0].text
        assert src.eol == "\r\n"
        # D-10: nothing normalised; the LF lines are still LF where they were
        assert written.count(b"\n") - written.count(b"\r\n") > 0
    else:
        assert src.issues == ()


@pytest.mark.parametrize("fixture", ["crlf", "lf"])
def test_inserted_property_uses_file_eol(tmp_path, fixture):
    target = tmp_path / f"{fixture}.kicad_sym"
    original = _fixture_bytes(f"sexpr/{fixture}.kicad_sym")
    target.write_bytes(original)

    src = read_source(target)
    assert not isinstance(src, Issue)
    fix_r = next(s for s in find_symbols(parse(src.text)) if s.name == "FIX_R")
    inserted = normalize_eol(
        '\n\t(property "MPN" "X-1" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        src.eol,
    )
    at = fix_r.node.end - 1
    new_text = apply_edits(src.text, [Edit(at, at, inserted)])
    assert atomic_write_bytes(target, encode_source(new_text, src.bom)) is None

    written = target.read_bytes()
    if fixture == "crlf":
        assert written.count(b"\n") == written.count(b"\r\n")
    else:
        assert b"\r" not in written
    assert written.count(b"\r\n") - original.count(b"\r\n") == (1 if fixture == "crlf" else 0)

    after = read_source(target)
    assert not isinstance(after, Issue)
    _assert_only_span_changed(src.text, after.text, at, at, inserted)
    byte_at = len(src.text[:at].encode("utf-8"))
    assert written[:byte_at] == original[:byte_at]
    assert written[byte_at + len(inserted.encode("utf-8")):] == original[byte_at:]

    reparsed = next(s for s in find_symbols(parse(after.text)) if s.name == "FIX_R")
    assert find_property(reparsed.node, "MPN").value == "X-1"
    assert find_property(reparsed.node, "Footprint").value == "Fixture_Lib:FIX_FP"


def _copy_fixture(tmp_path: Path, rel: str) -> tuple[Path, bytes]:
    target = tmp_path / Path(rel).name
    data = _fixture_bytes(rel)
    target.write_bytes(data)
    return target, data


def _apply_span_edit(target: Path, node, replacement: str):
    """Replace one node's span in target on disk; return (old text, new text, written bytes)."""
    src = read_source(target)
    assert not isinstance(src, Issue)
    new_text = apply_edits(src.text, [Edit(node.start, node.end, replacement)])
    assert atomic_write_bytes(target, encode_source(new_text, src.bom)) is None
    return src.text, new_text, target.read_bytes()


def _locate_footprint_name(target: Path):
    src = read_source(target)
    return footprint_name(parse(src.text)).name_node


@pytest.mark.parametrize(
    ("rel", "replacement", "expected"),
    [
        ("sexpr/bare_atoms.kicad_mod", quote("FIX_RENAMED"), "FIX_RENAMED"),
        ("sexpr/legacy_module.kicad_mod", "FIX_LEGACY_2", "FIX_LEGACY_2"),
        ("sexpr/two_models.kicad_mod", quote("FIX_TWO_RENAMED"), "FIX_TWO_RENAMED"),
    ],
    ids=["quoted-name", "legacy-atom-name", "crlf-two-models"],
)
def test_footprint_name_edit(tmp_path, rel, replacement, expected):
    target, original = _copy_fixture(tmp_path, rel)
    old_text, new_text, written = _apply_span_edit(
        target, _locate_footprint_name(target), replacement
    )
    node = footprint_name(parse(old_text)).name_node
    _assert_only_span_changed(old_text, new_text, node.start, node.end, replacement)
    assert _eol_counts(new_text) == _eol_counts(old_text)
    assert len(written) - len(original) == len(replacement) - (node.end - node.start)
    reread = read_source(target)
    assert footprint_name(parse(reread.text)).name == expected
    assert os.listdir(tmp_path) == [target.name]


def test_model_path_edit_second_of_two(tmp_path):
    target, original = _copy_fixture(tmp_path, "sexpr/two_models.kicad_mod")
    src = read_source(target)
    models = find_models(footprint_name(parse(src.text)).node)
    replacement = quote("${CUSTOM_3DMODEL_DIR}/FIX_C.step")
    old_text, new_text, written = _apply_span_edit(target, models[1].path_node, replacement)

    node = models[1].path_node
    _assert_only_span_changed(old_text, new_text, node.start, node.end, replacement)
    assert _eol_counts(new_text) == _eol_counts(old_text)
    assert written.count(b"\n") == written.count(b"\r\n")  # CRLF fixture gains no bare LF
    reread = read_source(target)
    after = find_models(footprint_name(parse(reread.text)).node)
    assert [m.path for m in after] == [
        "${CUSTOM_3DMODEL_DIR}/FIX_A.step",
        "${CUSTOM_3DMODEL_DIR}/FIX_C.step",
    ]


def test_lib_table_descr_edit_keeps_flags_and_unknown_children(tmp_path):
    target, original = _copy_fixture(tmp_path, "tables/flags.fp-lib-table")
    src = read_source(target)
    entries = lib_table_entries(parse(src.text))
    replacement = quote("edited")
    node = entries[0].value_nodes["descr"]
    old_text, new_text, written = _apply_span_edit(target, node, replacement)

    _assert_only_span_changed(old_text, new_text, node.start, node.end, replacement)
    assert _eol_counts(new_text) == _eol_counts(old_text)
    assert b"(disabled)" in written and b"(hidden)" in written
    assert b'(future_field "x")' in written
    reread = lib_table_entries(parse(read_source(target).text))
    assert reread[0].descr == "edited" and reread[0].flags == ("disabled",)
    assert reread[1].flags == ("hidden",)
    assert len(reread[2].extras) == 1 and reread[2].extras[0].head == "future_field"
    assert written.count(b"\n") == written.count(b"\r\n")


def test_interrupted_write_leaves_original_intact(tmp_path, monkeypatch):
    target, original = _copy_fixture(tmp_path, "sexpr/crlf.kicad_sym")
    src = read_source(target)
    start, end, replacement = _first_value_edit(src.text)
    edited = encode_source(apply_edits(src.text, [Edit(start, end, replacement)]), src.bom)

    def _locked(*args, **kwargs):
        raise PermissionError("locked by another process")

    monkeypatch.setattr("kicad_lib_manager.fsutil.os.replace", _locked)
    result = atomic_write_bytes(target, edited, retry_delays=(0.0,), sleep=lambda s: None)

    assert isinstance(result, Issue)
    assert result.code == "fs.locked"
    assert target.read_bytes() == original
    assert os.listdir(tmp_path) == [target.name]


def _apply_edit_on_disk(target: Path, edit: Edit):
    """Apply one Edit to target on disk; return (old text, new text, written bytes)."""
    src = read_source(target)
    assert not isinstance(src, Issue)
    new_text = apply_edits(src.text, [edit])
    assert atomic_write_bytes(target, encode_source(new_text, src.bom)) is None
    return src.text, new_text, target.read_bytes()


def test_retarget_model_second_of_two_crlf(tmp_path):
    target, original = _copy_fixture(tmp_path, "sexpr/two_models.kicad_mod")
    src = read_source(target)
    models = find_models(footprint_name(parse(src.text)).node)
    new_path = "${CUSTOM_3DMODEL_DIR}/FIX_NEW.step"

    edit = kicad_files.retarget_model(models[1], new_path)
    assert (edit.start, edit.end) == (models[1].path_node.start, models[1].path_node.end)
    assert edit.text == quote(new_path)

    old_text, new_text, written = _apply_edit_on_disk(target, edit)
    _assert_only_span_changed(old_text, new_text, edit.start, edit.end, quote(new_path))
    assert _eol_counts(new_text) == _eol_counts(old_text)
    assert written.count(b"\n") == written.count(b"\r\n")
    after = find_models(footprint_name(parse(read_source(target).text)).node)
    assert [m.path for m in after] == ["${CUSTOM_3DMODEL_DIR}/FIX_A.step", new_path]


def test_retarget_model_bare_atom_becomes_quoted_string():
    text = "(footprint F\n  (model C:/abs/x.step\n    (scale (xyz 1 1 1))\n  )\n)\n"
    models = find_models(footprint_name(parse(text)).node)
    assert models[0].path == "C:/abs/x.step"

    edit = kicad_files.retarget_model(models[0], "${CUSTOM_3DMODEL_DIR}/x.step")
    new_text = apply_edits(text, [edit])

    assert '(model "${CUSTOM_3DMODEL_DIR}/x.step"' in new_text
    assert new_text.endswith("(scale (xyz 1 1 1))\n  )\n)\n")
    reparsed = find_models(footprint_name(parse(new_text)).node)
    assert reparsed[0].path == "${CUSTOM_3DMODEL_DIR}/x.step"


def test_retarget_model_keeps_bom(tmp_path):
    target = tmp_path / "bom.kicad_mod"
    target.write_bytes(b'\xef\xbb\xbf(footprint "b"\n  (model "C:/abs/b.step")\n)\n')
    src = read_source(target)
    assert src.bom
    models = find_models(footprint_name(parse(src.text)).node)

    edit = kicad_files.retarget_model(models[0], "${CUSTOM_3DMODEL_DIR}/b.step")
    _apply_edit_on_disk(target, edit)

    assert target.read_bytes() == (
        b'\xef\xbb\xbf(footprint "b"\n  (model "${CUSTOM_3DMODEL_DIR}/b.step")\n)\n'
    )


def test_retarget_model_does_not_mutate_input_text():
    text = '(footprint "m"\n  (model "C:/abs/m.step")\n)\n'
    snapshot = str(text)
    models = find_models(footprint_name(parse(text)).node)
    kicad_files.retarget_model(models[0], "${CUSTOM_3DMODEL_DIR}/m.step")
    assert text == snapshot


def test_retarget_model_path_with_double_quote_round_trips():
    text = '(footprint "m"\n  (model "C:/abs/m.step")\n)\n'
    models = find_models(footprint_name(parse(text)).node)
    awkward = 'dir/we"ird.step'

    new_text = apply_edits(text, [kicad_files.retarget_model(models[0], awkward)])

    assert find_models(footprint_name(parse(new_text)).node)[0].path == awkward
