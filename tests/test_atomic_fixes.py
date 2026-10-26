"""The fix engine behind the check dialog: previewed, backed up, written atomically, gone on the next scan (SCAN-03).

Every test writes only into tmp_path trees; none touches the real Custom/.
"""

import hashlib
import os
from pathlib import Path

import pytest

from customfixtures import atomic_lib, atomic_part, digest_tree, write_atomic_custom, write_fake_kicad
from installfixtures import V6_VERSION, target_lib
from kicad_lib_manager import atomic_fixes, kicad_files
from kicad_lib_manager.atomic_fixes import apply_preview, build_preview, preview_text
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import FixSpec, Issue, Severity
from zipfixtures import STEP_BYTES, VRML_BYTES, make_zip

SYMBOL_REL = "Custom/Symbols/Atomic_Connector.kicad_sym"
FOOTPRINT_DIR = "Custom/Footprints/Atomic_Footprints.pretty"


def _no_kicad() -> list[str]:
    return []


def _setup(tmp_path):
    """Write the atomic inventory and a fake KiCad install; return (repo root, KiCad footprints folder)."""
    root = tmp_path / "repo"
    write_atomic_custom(root)
    footprints, _ = write_fake_kicad(tmp_path)
    return root, footprints


def _entries(root, footprints, library="Atomic_Connector"):
    """Scan and return {symbol name: SymbolEntry} of one library."""
    result = scan_all(root, kicad_fp_dir=footprints)
    lib = next(lib for lib in result.symbol_libs if lib.nickname == library)
    return {entry.name: entry for entry in lib.symbols}


def _fixes(entry):
    """Every one-click FixSpec of a symbol: violation fixes and finding fixes."""
    specs = [spec for violation in entry.violations for spec in violation.fixes]
    specs += [finding.fix for finding in entry.findings if finding.fix is not None]
    return specs


def _fill(entry, kind):
    return next(v.fill for v in entry.violations if v.fill is not None and v.fill.kind == kind)


def _preview(root, specs):
    return build_preview(root, specs, running=_no_kicad)


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


def test_value_to_mpn_is_previewed_backed_up_written_and_gone_on_the_next_scan(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    before = path.read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])
    assert [s.kind for s in specs] == ["value_to_mpn"]

    preview = _preview(root, specs)

    assert preview.issues == []
    assert len(preview.changes) == 1
    change = preview.changes[0]
    shown = preview_text(change).splitlines()
    assert any(line.startswith("-") and '"FFC20"' in line for line in shown)
    assert any(line.startswith("+") and '"FH12-20S-0.5SH"' in line for line in shown)
    assert shown[0] == f"--- before: {SYMBOL_REL}" and shown[1] == f"+++ after: {SYMBOL_REL}"
    # Only that one value token differs from the file as it was
    assert change.old_text == before
    assert change.new_text == before.replace('(property "Value" "FFC20"', '(property "Value" "FH12-20S-0.5SH"')
    assert path.read_text(encoding="utf-8") == before

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is True
    assert [i.code for i in result.issues] == ["atomic.fixed"]
    backups = list((tmp_path / "bk" / "atomic_fixes").rglob("Atomic_Connector.kicad_sym_backup_1"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == before
    assert path.read_text(encoding="utf-8") == change.new_text
    assert "value" not in {v.rule for v in _entries(root, footprints)["FFC-0.5-20"].violations}


def test_the_bytes_outside_the_edited_token_are_unchanged_line_endings_included(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    before = path.read_bytes()
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])

    result = apply_preview(_preview(root, specs), backup_root=tmp_path / "bk")

    assert result.ok is True
    expected = before.replace(b'(property "Value" "FFC20"', b'(property "Value" "FH12-20S-0.5SH"')
    assert path.read_bytes() == expected


def test_default_fix_backup_dir_sits_under_atomic_fixes_and_never_repeats(tmp_path):
    from datetime import datetime

    stamp = datetime(2026, 10, 26, 14, 30, 5)
    first = atomic_fixes.default_fix_backup_dir(tmp_path, now=stamp)
    assert first == tmp_path / "atomic_fixes" / "20261026-143005"

    first.mkdir(parents=True)
    second = atomic_fixes.default_fix_backup_dir(tmp_path, now=stamp)

    assert second == tmp_path / "atomic_fixes" / "20261026-143005-2"
    assert atomic_fixes.default_fix_backup_dir(tmp_path, now=stamp) != first
    assert not second.exists()


# ── Every property fix and fill-in ───────────────────────────────────────────────────────────


def _span(text, name):
    loaded = kicad_files.parse_bytes(text.encode("utf-8"), "x.kicad_sym")
    ref = kicad_files.find_symbol(loaded.root, name)
    return ref.node.start, ref.node.end


def _replace_in_symbol(text, name, old, new):
    """The file text with old replaced by new, inside the one symbol called name only."""
    start, end = _span(text, name)
    block = text[start:end]
    assert block.count(old) == 1, old
    return text[:start] + block.replace(old, new) + text[end:]


def _drop_property(text, name):
    """The file text without the first property block called name (a tab-indented v10 block of its own lines)."""
    lines = text.split("\n")
    index = next(i for i, line in enumerate(lines) if line.lstrip().startswith(f'(property "{name}"'))
    indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
    end = next(i for i in range(index, len(lines)) if lines[i] == indent + ")")
    del lines[index : end + 1]
    return "\n".join(lines)


def _write_library(root, name, symbols, *, eol="\n", bom=False):
    path = root / "Custom" / "Symbols" / f"{name}.kicad_sym"
    data = atomic_lib(symbols, eol=eol)
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
    return path


def _apply(tmp_path, root, specs):
    preview = _preview(root, specs)
    result = apply_preview(preview, backup_root=tmp_path / "bk")
    assert result.ok is True, result.issues
    return preview


def _properties(path, symbol):
    loaded = kicad_files.parse_bytes(path.read_bytes(), path.name)
    return [(p.name, p.value) for p in kicad_files.list_properties(kicad_files.find_symbol(loaded.root, symbol).node)]


def test_rename_alias_and_canonical_spelling_apply_together_on_one_property(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    before = path.read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["MFR-AS-MF"])
    assert sorted(s.kind for s in specs) == ["canonical_manufacturer", "rename_alias"]

    preview = _preview(root, specs)

    assert preview.issues == []
    (change,) = preview.changes
    expected = _replace_in_symbol(
        before, "MFR-AS-MF", '(property "MF" "GCT"', '(property "Manufacturer" "Global Connector Technology"'
    )
    assert change.new_text == expected
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    assert "MF" not in dict(_properties(path, "MFR-AS-MF"))
    assert _entries(root, footprints)["MFR-AS-MF"].violations == []


def test_canonical_spelling_of_a_short_manufacturer_is_written(tmp_path):
    root, footprints = _setup(tmp_path)
    before = (root / SYMBOL_REL).read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["MFR-SHORT"])

    (change,) = _preview(root, specs).changes

    assert change.new_text == _replace_in_symbol(
        before, "MFR-SHORT", '(property "Manufacturer" "TI"', '(property "Manufacturer" "Texas Instruments"'
    )


def test_rename_alias_gives_the_mpn_property_its_canonical_name(tmp_path):
    root, footprints = _setup(tmp_path)
    before = (root / SYMBOL_REL).read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["MPN-AS-MP"])
    assert [s.kind for s in specs] == ["rename_alias"]

    preview = _preview(root, specs)

    assert preview.changes[0].new_text == _replace_in_symbol(
        before, "MPN-AS-MP", '(property "MP" "MPN-AS-MP"', '(property "MPN" "MPN-AS-MP"'
    )
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    assert _entries(root, footprints)["MPN-AS-MP"].violations == []


def test_a_rename_that_is_not_an_mpn_or_manufacturer_alias_rename_is_refused(tmp_path):
    root, footprints = _setup(tmp_path)
    spec = FixSpec(
        "rename_alias", SYMBOL_REL, "MFR-DUP-OK", "Rename MF", {"property": "MF", "new_name": "MANUFACTURER"}
    )

    preview = _preview(root, [spec])

    # MANUFACTURER is not the canonical name of the group
    assert preview.changes == []
    assert [i.code for i in preview.issues] == ["atomic.fix_unknown"]


def test_rename_alias_is_skipped_when_the_symbol_already_has_the_canonical_name(tmp_path):
    root, footprints = _setup(tmp_path)
    _write_library(root, "Atomic_Both", (atomic_part("BOTH-1", extra=(("MF", "GCT"),)),))
    spec = FixSpec(
        "rename_alias", "Custom/Symbols/Atomic_Both.kicad_sym", "BOTH-1", "Rename MF",
        {"property": "MF", "new_name": "Manufacturer"},
    )

    preview = _preview(root, [spec])

    assert preview.changes == []
    assert [(i.severity, i.code) for i in preview.issues] == [(Severity.INFO, "atomic.fix_skipped")]


def test_merge_alias_keeps_one_canonical_field_and_removes_the_others(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    before = path.read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["MFR-DUP-OK"])
    assert [s.kind for s in specs] == ["merge_alias"]

    preview = _preview(root, specs)

    expected = _drop_property(
        _replace_in_symbol(
            before, "MFR-DUP-OK", '(property "MF" "GCT"', '(property "Manufacturer" "Global Connector Technology"'
        ),
        "MANUFACTURER",
    )
    assert preview.changes[0].new_text == expected
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    props = _properties(path, "MFR-DUP-OK")
    assert [value for name, value in props if name in ("Manufacturer", "MF", "MANUFACTURER")] == [
        "Global Connector Technology"
    ]
    assert _entries(root, footprints)["MFR-DUP-OK"].violations == []


def test_merge_fill_with_a_picked_value_keeps_only_that_value(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    entry = _entries(root, footprints)["MFR-DUP-BAD"]
    fill = _fill(entry, "merge_alias")

    assert atomic_fixes.complete_fill(fill, "") == "Pick the value to keep first"
    assert atomic_fixes.complete_fill(fill, "   ") == "Pick the value to keep first"
    done = atomic_fixes.complete_fill(fill, "Molex")
    assert done.label == 'Keep "Molex" as the only manufacturer value'
    assert done.params["value"] == "Molex" and fill.params["value"] == ""

    _apply(tmp_path, root, [done])

    props = _properties(path, "MFR-DUP-BAD")
    assert [value for name, value in props if name in ("Manufacturer", "MF", "MANUFACTURER")] == ["Molex"]
    assert [name for name, _ in props if name in ("MF", "MANUFACTURER")] == []
    assert _entries(root, footprints)["MFR-DUP-BAD"].violations == []


def test_a_merge_fill_whose_value_is_still_empty_is_refused(tmp_path):
    root, footprints = _setup(tmp_path)
    fill = _fill(_entries(root, footprints)["MFR-DUP-BAD"], "merge_alias")

    preview = _preview(root, [fill])

    assert preview.changes == []
    assert [i.code for i in _errors(preview.issues)] == ["atomic.fix_incomplete"]


def test_leftover_removal_leaves_no_blank_line_and_no_other_byte_changed(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / SYMBOL_REL
    before = path.read_text(encoding="utf-8")
    specs = _fixes(_entries(root, footprints)["LEFTOVER-1"])
    assert sorted(s.params["property"] for s in specs) == ["Availability", "Check_prices", "Price"]

    preview = _preview(root, specs)

    expected = before
    for name in ("Price", "Availability", "Check_prices"):
        expected = _drop_property(expected, name)
    assert preview.changes[0].new_text == expected
    assert "\n\n" not in preview.changes[0].new_text
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    assert _entries(root, footprints)["LEFTOVER-1"].findings == []


def test_fill_datasheet_accepts_only_a_link_or_path_and_writes_it_into_the_existing_field(tmp_path):
    root, footprints = _setup(tmp_path)
    before = (root / SYMBOL_REL).read_text(encoding="utf-8")
    fill = _fill(_entries(root, footprints)["DS-EMPTY"], "fill_datasheet")

    assert atomic_fixes.complete_fill(fill, "see website") == "Datasheet is not a link or file path"
    done = atomic_fixes.complete_fill(fill, "  https://example.com/ds.pdf ")
    assert done.label == 'Datasheet → "https://example.com/ds.pdf"'

    preview = _apply(tmp_path, root, [done])

    assert preview.changes[0].new_text == _replace_in_symbol(
        before, "DS-EMPTY", '(property "Datasheet" "~"', '(property "Datasheet" "https://example.com/ds.pdf"'
    )
    assert _entries(root, footprints)["DS-EMPTY"].violations == []


def test_a_datasheet_fill_with_a_bad_value_never_reaches_the_file(tmp_path):
    root, footprints = _setup(tmp_path)
    fill = _fill(_entries(root, footprints)["DS-EMPTY"], "fill_datasheet")
    forced = FixSpec(fill.kind, fill.rel_path, fill.symbol, "forced", {**fill.params, "value": "see website"})

    for spec in (fill, forced):
        preview = _preview(root, [spec])
        assert preview.changes == []
        assert [i.code for i in _errors(preview.issues)] == ["atomic.fix_incomplete"]


def test_fill_description_cleans_the_text_and_writes_it_into_the_existing_field(tmp_path):
    root, footprints = _setup(tmp_path)
    before = (root / SYMBOL_REL).read_text(encoding="utf-8")
    fill = _fill(_entries(root, footprints)["DESC-EMPTY"], "fill_description")

    assert atomic_fixes.complete_fill(fill, "   ") == "Type a description first"
    done = atomic_fixes.complete_fill(fill, "  two   words ")
    assert done.label == 'Description → "two words"'

    preview = _apply(tmp_path, root, [done])

    assert preview.changes[0].new_text == _replace_in_symbol(
        before, "DESC-EMPTY", '(property "Description" ""', '(property "Description" "two words"'
    )
    assert _entries(root, footprints)["DESC-EMPTY"].violations == []


def test_fill_description_adds_a_hidden_field_when_the_symbol_has_none(tmp_path):
    root, footprints = _setup(tmp_path)
    path = _write_library(root, "Atomic_NoDesc", (atomic_part("NODESC-1", drop=("Description",)),))
    fill = _fill(_entries(root, footprints, "Atomic_NoDesc")["NODESC-1"], "fill_description")

    _apply(tmp_path, root, [atomic_fixes.complete_fill(fill, "A new part")])

    props = _properties(path, "NODESC-1")
    assert props[-1] == ("Description", "A new part")
    loaded = kicad_files.parse_bytes(path.read_bytes(), path.name)
    added = kicad_files.find_property(kicad_files.find_symbol(loaded.root, "NODESC-1").node, "Description")
    assert kicad_files.property_is_hidden(added)
    assert _entries(root, footprints, "Atomic_NoDesc")["NODESC-1"].violations == []


def test_fill_in_an_old_format_file_takes_the_next_id_and_keeps_its_line_endings(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / "Custom" / "Symbols" / "Atomic_Old.kicad_sym"
    path.write_bytes(target_lib(V6_VERSION, ("OLD-1",)))
    fill = _fill(_entries(root, footprints, "Atomic_Old")["OLD-1"], "fill_description")

    _apply(tmp_path, root, [atomic_fixes.complete_fill(fill, "Old part")])

    data = path.read_bytes()
    assert b'(property "ki_description" "Old part" (id 4)' in data
    assert data.count(b"\n") == data.count(b"\r\n")


def test_two_inserted_fields_in_one_symbol_get_distinct_ids(tmp_path):
    root, footprints = _setup(tmp_path)
    path = root / "Custom" / "Symbols" / "Atomic_Old.kicad_sym"
    lines = target_lib(V6_VERSION, ("OLD-1",)).decode("utf-8").split("\r\n")
    index = next(i for i, line in enumerate(lines) if '"Datasheet"' in line)
    del lines[index : index + 3]
    path.write_bytes("\r\n".join(lines).encode("utf-8"))
    entry = _entries(root, footprints, "Atomic_Old")["OLD-1"]
    specs = [
        atomic_fixes.complete_fill(_fill(entry, "fill_datasheet"), "https://example.com/old.pdf"),
        atomic_fixes.complete_fill(_fill(entry, "fill_description"), "Old part"),
    ]

    _apply(tmp_path, root, specs)

    loaded = kicad_files.parse_bytes(path.read_bytes(), path.name)
    ids = []
    for prop in kicad_files.list_properties(kicad_files.find_symbol(loaded.root, "OLD-1").node):
        ids.extend(part.children[1].text for part in prop.node.children if part.head == "id")
    assert sorted(ids) == ["0", "1", "2", "3", "4"]
    assert {name for name, _ in _properties(path, "OLD-1")} >= {"Datasheet", "ki_description"}


def test_an_inherited_fix_asked_by_two_children_applies_once_to_the_parent(tmp_path):
    root, footprints = _setup(tmp_path)
    path = _write_library(
        root,
        "Atomic_Variants",
        (
            atomic_part("VAR-P", replace={"Manufacturer": "TI"}),
            atomic_part("VAR-C1", drop=("Manufacturer",), extends="VAR-P"),
            atomic_part("VAR-C2", drop=("Manufacturer",), extends="VAR-P"),
        ),
    )
    entries = _entries(root, footprints, "Atomic_Variants")
    specs = [spec for name in ("VAR-P", "VAR-C1", "VAR-C2") for spec in _fixes(entries[name])]
    assert len(specs) == 3 and {s.symbol for s in specs} == {"VAR-P"}

    preview = _apply(tmp_path, root, specs)

    assert len(preview.changes) == 1
    assert preview.changes[0].new_text.count('"Texas Instruments"') == 1
    assert dict(_properties(path, "VAR-P"))["Manufacturer"] == "Texas Instruments"
    assert all(e.violations == [] for e in _entries(root, footprints, "Atomic_Variants").values())


def test_two_different_fixes_on_one_field_refuse_the_file_with_a_plain_conflict(tmp_path):
    root, footprints = _setup(tmp_path)
    before = (root / SYMBOL_REL).read_bytes()
    one = FixSpec("canonical_manufacturer", SYMBOL_REL, "MFR-SHORT", "a", {"property": "Manufacturer", "value": "Texas Instruments"})
    other = FixSpec("canonical_manufacturer", SYMBOL_REL, "MFR-SHORT", "b", {"property": "Manufacturer", "value": "Molex"})
    unrelated = _fixes(_entries(root, footprints)["FFC-0.5-20"])

    preview = _preview(root, [one, other, *unrelated])

    assert preview.changes == []
    (issue,) = _errors(preview.issues)
    assert issue.code == "atomic.fix_conflict"
    assert "two of the ticked fixes change the same field" in issue.text
    assert (root / SYMBOL_REL).read_bytes() == before


def test_a_fix_already_on_disk_is_skipped_with_a_note_and_changes_nothing(tmp_path):
    root, footprints = _setup(tmp_path)
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])
    _apply(tmp_path, root, specs)

    preview = _preview(root, specs)

    assert preview.changes == []
    (issue,) = preview.issues
    assert issue.severity is Severity.INFO and issue.code == "atomic.fix_skipped"
    assert "FFC-0.5-20" in issue.text


def test_a_fix_for_a_symbol_that_is_gone_is_skipped_with_a_note(tmp_path):
    root, footprints = _setup(tmp_path)
    spec = FixSpec("value_to_mpn", SYMBOL_REL, "NOT-THERE", "x", {"property": "Value", "value": "A"})

    preview = _preview(root, [spec])

    assert preview.changes == []
    assert [(i.severity, i.code) for i in preview.issues] == [(Severity.INFO, "atomic.fix_skipped")]
    assert "NOT-THERE" in preview.issues[0].text


def test_a_value_fix_is_skipped_when_the_mpn_changed_since_the_check(tmp_path):
    root, footprints = _setup(tmp_path)
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])
    path = root / SYMBOL_REL
    path.write_text(path.read_text(encoding="utf-8").replace('"FH12-20S-0.5SH"', '"FH12-OTHER"'), encoding="utf-8")

    preview = _preview(root, specs)

    assert preview.changes == []
    assert [i.code for i in preview.issues] == ["atomic.fix_skipped"]


def test_nothing_to_preview_gives_no_changes_no_issues_and_nothing_to_apply(tmp_path):
    root, _ = _setup(tmp_path)

    preview = _preview(root, [])
    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert preview.changes == [] and preview.issues == []
    assert result.ok is False
    assert [(i.severity, i.code) for i in result.issues] == [(Severity.INFO, "atomic.nothing_to_apply")]
    assert not (tmp_path / "bk").exists()


def test_the_same_specs_in_any_order_give_byte_identical_new_text(tmp_path):
    root, footprints = _setup(tmp_path)
    old_path = root / "Custom" / "Symbols" / "Atomic_Old.kicad_sym"
    lines = target_lib(V6_VERSION, ("OLD-1",)).decode("utf-8").split("\r\n")
    index = next(i for i, line in enumerate(lines) if '"Datasheet"' in line)
    del lines[index : index + 3]
    old_path.write_bytes("\r\n".join(lines).encode("utf-8"))
    entries = _entries(root, footprints)
    old_entry = _entries(root, footprints, "Atomic_Old")["OLD-1"]
    specs = [
        *_fixes(entries["MFR-AS-MF"]),
        *_fixes(entries["MFR-SHORT"]),
        *_fixes(entries["MFR-DUP-OK"]),
        *_fixes(entries["LEFTOVER-1"]),
        *_fixes(entries["FFC-0.5-20"]),
        atomic_fixes.complete_fill(_fill(entries["DS-EMPTY"], "fill_datasheet"), "https://example.com/ds.pdf"),
        atomic_fixes.complete_fill(_fill(entries["DESC-EMPTY"], "fill_description"), "some text"),
        atomic_fixes.complete_fill(_fill(old_entry, "fill_datasheet"), "https://example.com/old.pdf"),
        atomic_fixes.complete_fill(_fill(old_entry, "fill_description"), "Old part"),
    ]

    def texts(ordered):
        return {c.rel_path: c.new_text for c in _preview(root, ordered).changes}

    forward = texts(specs)
    assert len(forward) == 2
    assert texts(list(reversed(specs))) == forward
    assert texts(specs[3:] + specs[:3]) == forward
    assert texts(specs[::2] + specs[1::2]) == forward


def test_a_bom_and_crlf_file_keeps_both_after_every_kind_of_fix(tmp_path):
    root, footprints = _setup(tmp_path)
    path = _write_library(
        root,
        "Atomic_Crlf",
        (atomic_part("CRLF-1", drop=("Description",), replace={"Value": "X", "Manufacturer": "TI"}, extra=(("Price", "9"),)),),
        eol="\r\n",
        bom=True,
    )
    entry = _entries(root, footprints, "Atomic_Crlf")["CRLF-1"]
    specs = [*_fixes(entry), atomic_fixes.complete_fill(_fill(entry, "fill_description"), "A part")]
    assert {s.kind for s in specs} == {"value_to_mpn", "canonical_manufacturer", "remove_leftover", "fill_description"}

    _apply(tmp_path, root, specs)

    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf") and data.count(b"\xef\xbb\xbf") == 1
    assert data.count(b"\n") == data.count(b"\r\n")
    assert _entries(root, footprints, "Atomic_Crlf")["CRLF-1"].violations == []


# ── Stale refusal, rollback, containment, KiCad notice and the 3D model intake ──────────────


def _model_source(tmp_path, name="NEW-MODEL.step", data=STEP_BYTES):
    folder = tmp_path / "src"
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


def _attach(entries, symbol, source):
    return atomic_fixes.complete_fill(_fill(entries[symbol], "attach_model"), str(source))


def _footprint_text(root, name):
    return (root / FOOTPRINT_DIR / f"{name}.kicad_mod").read_bytes().decode("utf-8")


@pytest.mark.parametrize("change", [lambda d: d + b" ", lambda d: d.replace(b"USB4105-GF-A", b"USB4105-GF-B", 1)])
def test_a_one_byte_change_after_the_preview_refuses_the_whole_batch(tmp_path, change):
    root, footprints = _setup(tmp_path)
    preview = _preview(root, _fixes(_entries(root, footprints)["FFC-0.5-20"]))
    path = root / SYMBOL_REL
    changed = change(path.read_bytes())
    path.write_bytes(changed)

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is False
    assert [(i.severity, i.code) for i in result.issues] == [(Severity.ERROR, "atomic.stale_file")]
    assert result.issues[0].text == f"{SYMBOL_REL} changed after the preview was built; preview again"
    assert path.read_bytes() == changed
    assert not (tmp_path / "bk").exists()


def test_a_file_that_vanished_after_the_preview_refuses_the_batch(tmp_path):
    root, footprints = _setup(tmp_path)
    preview = _preview(root, _fixes(_entries(root, footprints)["FFC-0.5-20"]))
    (root / SYMBOL_REL).unlink()

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert [i.code for i in result.issues] == ["atomic.stale_file"]
    assert not (tmp_path / "bk").exists()


def test_a_new_model_name_that_appeared_after_the_preview_refuses_the_batch(tmp_path):
    root, footprints = _setup(tmp_path)
    source = _model_source(tmp_path)
    preview = _preview(root, [_attach(_entries(root, footprints), "MODEL-MISSING", source)])
    appeared = root / "Custom" / "3DModels" / "new-model.STEP"
    appeared.write_bytes(b"someone else's file")
    before = digest_tree(root)

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert [i.code for i in result.issues] == ["atomic.stale_file"]
    assert digest_tree(root) == before
    assert not (tmp_path / "bk").exists()


def _flaky_second_text_write(monkeypatch):
    real = atomic_fixes.fsutil.atomic_write_text
    calls = []

    def flaky(path, text, **kwargs):
        calls.append(path)
        if len(calls) == 2:
            return Issue(Severity.ERROR, "fs.write_failed", f"Could not write {path.name}: disk full")
        return real(path, text, **kwargs)

    monkeypatch.setattr(atomic_fixes.fsutil, "atomic_write_text", flaky)
    return calls


def _two_files_and_a_model(tmp_path):
    root, footprints = _setup(tmp_path)
    _write_library(root, "Atomic_Second", (atomic_part("SECOND-1", replace={"Value": "X"}),))
    entries = _entries(root, footprints)
    second = _entries(root, footprints, "Atomic_Second")
    source = _model_source(tmp_path)
    specs = [
        *_fixes(entries["FFC-0.5-20"]),
        *_fixes(second["SECOND-1"]),
        _attach(entries, "MODEL-MISSING", source),
    ]
    return root, specs


def test_a_failed_write_restores_every_earlier_file_and_removes_the_copied_model(tmp_path, monkeypatch):
    root, specs = _two_files_and_a_model(tmp_path)
    preview = _preview(root, specs)
    assert len(preview.changes) == 4 and preview.changes[0].new_bytes is not None
    before = digest_tree(root)
    calls = _flaky_second_text_write(monkeypatch)

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is False
    assert [i.code for i in result.issues] == ["atomic.write_failed"]
    assert "disk full" in result.issues[0].text and result.issues[0].text.endswith("; no fix was kept")
    assert len(calls) == 2
    assert digest_tree(root) == before
    assert not (root / "Custom" / "3DModels" / "NEW-MODEL.step").exists()


def test_a_restore_that_fails_is_reported_with_the_backup_folder(tmp_path, monkeypatch):
    root, footprints = _setup(tmp_path)
    _write_library(root, "Atomic_Second", (atomic_part("SECOND-1", replace={"Value": "X"}),))
    specs = [
        *_fixes(_entries(root, footprints)["FFC-0.5-20"]),
        *_fixes(_entries(root, footprints, "Atomic_Second")["SECOND-1"]),
    ]
    preview = _preview(root, specs)
    real = atomic_fixes.fsutil.atomic_write_text
    calls = []

    def fail_then_lock(path, text, **kwargs):
        calls.append(path)
        if len(calls) == 2:
            # From here on nothing can be written, so the restore of the first file fails too
            monkeypatch.setattr(
                atomic_fixes.fsutil, "atomic_write_bytes",
                lambda p, data, **kw: Issue(Severity.ERROR, "fs.locked", "Could not write: in use"),
            )
            return Issue(Severity.ERROR, "fs.write_failed", f"Could not write {path.name}: disk full")
        return real(path, text, **kwargs)

    monkeypatch.setattr(atomic_fixes.fsutil, "atomic_write_text", fail_then_lock)

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is False
    assert [i.code for i in result.issues] == ["atomic.write_failed", "atomic.rollback_failed"]
    assert result.issues[1].text == (
        f"{SYMBOL_REL} could not be restored; the original is in {result.backup_dir}"
    )
    assert (result.backup_dir / "Atomic_Connector.kicad_sym_backup_1").exists()


def test_a_write_that_raises_is_a_failed_write_not_a_crash(tmp_path, monkeypatch):
    root, footprints = _setup(tmp_path)
    preview = _preview(root, _fixes(_entries(root, footprints)["FFC-0.5-20"]))
    before = digest_tree(root)

    def explode(path, text, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(atomic_fixes.fsutil, "atomic_write_text", explode)

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is False and result.issues[0].code == "atomic.write_failed"
    assert digest_tree(root) == before


def test_a_backup_that_cannot_be_made_refuses_the_batch_before_any_write(tmp_path, monkeypatch):
    root, footprints = _setup(tmp_path)
    preview = _preview(root, _fixes(_entries(root, footprints)["FFC-0.5-20"]))
    before = digest_tree(root)
    monkeypatch.setattr(
        atomic_fixes.fsutil, "backup_file", lambda path, folder: Issue(Severity.ERROR, "fs.backup_failed", "no space")
    )

    result = apply_preview(preview, backup_root=tmp_path / "bk")

    assert result.ok is False and [i.code for i in result.issues] == ["fs.backup_failed"]
    assert digest_tree(root) == before


def test_a_path_outside_custom_is_refused_and_nothing_is_changed(tmp_path):
    root, footprints = _setup(tmp_path)
    (root / "outside.kicad_sym").write_bytes(b"(kicad_symbol_lib)")
    before = digest_tree(root)
    outside = [
        "WurthElektronik/KiCad-Library/symbols/WE-Connectors.kicad_sym",
        "Custom/../outside.kicad_sym",
        "Custom\\..\\outside.kicad_sym",
        str(tmp_path / "x.kicad_sym"),
        "Other/Symbols/Atomic_Elsewhere.kicad_sym",
        "outside.kicad_sym",
        "Custom",
        "",
    ]
    specs = [FixSpec("value_to_mpn", rel, "A", "x", {"property": "Value", "value": "A"}) for rel in outside]
    # A symbol fix may not name a footprint file, and an attach_model may not leave Custom/Footprints
    specs.append(FixSpec("value_to_mpn", f"{FOOTPRINT_DIR}/NO-MODEL.kicad_mod", "A", "x", {"property": "Value", "value": "A"}))
    source = str(_model_source(tmp_path))
    for footprint in (
        "Other/Footprints/Dup_Footprints.pretty/DUP-1.kicad_mod",
        "Custom/Symbols/Atomic_Connector.kicad_sym",
        "Custom/../outside.kicad_mod",
        str(tmp_path / "x.kicad_mod"),
    ):
        specs.append(FixSpec("attach_model", footprint, "A", "x", {"footprint": footprint, "source": source}))
    # rel_path inside, params.footprint outside
    specs.append(FixSpec(
        "attach_model", f"{FOOTPRINT_DIR}/NO-MODEL.kicad_mod", "A", "x",
        {"footprint": "Other/Footprints/Dup_Footprints.pretty/DUP-1.kicad_mod", "source": source},
    ))

    preview = _preview(root, specs)

    assert preview.changes == []
    assert [i.code for i in preview.issues] == ["atomic.path_outside_custom"] * len(specs)
    assert preview.issues[0].text == "Not changed: WurthElektronik/KiCad-Library/symbols/WE-Connectors.kicad_sym is outside Custom/"
    assert digest_tree(root) == before


def test_a_fix_kind_outside_the_safe_and_fill_lists_is_refused(tmp_path):
    root, footprints = _setup(tmp_path)
    spec = FixSpec("delete_symbol", SYMBOL_REL, "FFC-0.5-20", "Delete it", {})

    preview = _preview(root, [spec])

    assert preview.changes == []
    assert [(i.severity, i.code) for i in preview.issues] == [(Severity.ERROR, "atomic.fix_unknown")]


def test_a_hand_built_preview_pointing_outside_custom_is_never_written(tmp_path):
    root, _ = _setup(tmp_path)
    target = root / "outside.kicad_sym"
    target.write_bytes(b"old")
    change = atomic_fixes.FileChange(
        target, "outside.kicad_sym", "old", "new", None, hashlib.sha256(b"old").hexdigest(), False
    )

    result = apply_preview(atomic_fixes.FixPreview(root, [change]), backup_root=tmp_path / "bk")

    assert result.ok is False and [i.code for i in result.issues] == ["atomic.path_outside_custom"]
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("names", [["kicad.exe"], []])
def test_the_running_kicad_processes_are_recorded_on_the_preview(tmp_path, names):
    root, footprints = _setup(tmp_path)
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])

    preview = build_preview(root, specs, running=lambda: list(names))

    assert preview.kicad_running == names


def test_attach_model_copies_the_model_and_repoints_the_one_broken_line(tmp_path):
    root, footprints = _setup(tmp_path)
    source = _model_source(tmp_path)
    before = _footprint_text(root, "MISSING-MODEL")
    spec = _attach(_entries(root, footprints), "MODEL-MISSING", source)
    assert spec.label == '3D model → "NEW-MODEL.step"'

    preview = _preview(root, [spec])

    assert preview.issues == []
    assert [c.rel_path for c in preview.changes] == [
        "Custom/3DModels/NEW-MODEL.step", f"{FOOTPRINT_DIR}/MISSING-MODEL.kicad_mod",
    ]
    assert preview_text(preview.changes[0]) == f"New file Custom/3DModels/NEW-MODEL.step ({len(STEP_BYTES)} bytes)"
    assert preview.changes[1].new_text == before.replace(
        "${CUSTOM_3DMODEL_DIR}/MISSING-MODEL.step", "${CUSTOM_3DMODEL_DIR}/NEW-MODEL.step"
    )
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    assert (root / "Custom" / "3DModels" / "NEW-MODEL.step").read_bytes() == STEP_BYTES
    assert _footprint_text(root, "MISSING-MODEL").count("(model") == 1
    assert _entries(root, footprints)["MODEL-MISSING"].violations == []


def test_attach_model_adds_a_model_line_to_a_footprint_that_has_none(tmp_path):
    root, footprints = _setup(tmp_path)
    source = _model_source(tmp_path)
    before = _footprint_text(root, "NO-MODEL")
    assert "(model" not in before

    preview = _preview(root, [_attach(_entries(root, footprints), "MODEL-NONE", source)])
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True

    after = _footprint_text(root, "NO-MODEL")
    assert after.count("(model") == 1
    assert '(model "${CUSTOM_3DMODEL_DIR}/NEW-MODEL.step"' in after
    block = (
        '\r\n  (model "${CUSTOM_3DMODEL_DIR}/NEW-MODEL.step"\r\n    (offset (xyz 0 0 0))\r\n'
        "    (scale (xyz 1 1 1))\r\n    (rotate (xyz 0 0 0))\r\n  )"
    )
    assert after == before.replace("\r\n)\r\n", block + "\r\n)\r\n")
    assert after.count("\n") == after.count("\r\n")
    assert _entries(root, footprints)["MODEL-NONE"].violations == []


def test_one_picked_model_is_copied_once_for_two_footprints(tmp_path):
    root, footprints = _setup(tmp_path)
    source = _model_source(tmp_path)
    entries = _entries(root, footprints)
    specs = [_attach(entries, "MODEL-MISSING", source), _attach(entries, "MODEL-NONE", source)]

    preview = _preview(root, specs)

    assert [c.new_bytes is not None for c in preview.changes] == [True, False, False]
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    after = _entries(root, footprints)
    assert after["MODEL-MISSING"].violations == [] and after["MODEL-NONE"].violations == []


def test_a_model_already_in_custom_with_the_same_bytes_is_reused_not_copied(tmp_path):
    root, footprints = _setup(tmp_path)
    # The folder holds WRONG-CASE.step; a file of that name in any case and the same bytes is the same model
    source = _model_source(tmp_path, "wrong-case.step", STEP_BYTES)
    spec = _attach(_entries(root, footprints), "MODEL-WRONG-CASE", source)

    preview = _preview(root, [spec])

    assert [c.rel_path for c in preview.changes] == [f"{FOOTPRINT_DIR}/WRONG-CASE-MODEL.kicad_mod"]
    assert '"${CUSTOM_3DMODEL_DIR}/WRONG-CASE.step"' in preview.changes[0].new_text
    assert apply_preview(preview, backup_root=tmp_path / "bk").ok is True
    assert _entries(root, footprints)["MODEL-WRONG-CASE"].violations == []


@pytest.mark.parametrize("name", ["wrong-case.step", "WRONG-CASE.step"])
def test_a_different_model_with_a_taken_name_is_refused_compared_casefolded(tmp_path, name):
    root, footprints = _setup(tmp_path)
    source = _model_source(tmp_path, name, b"different bytes")
    before = digest_tree(root)

    preview = _preview(root, [_attach(_entries(root, footprints), "MODEL-WRONG-CASE", source)])

    assert preview.changes == []
    (issue,) = preview.issues
    assert issue.code == "atomic.model_name_taken"
    assert issue.text == (
        f'A different 3D model named "{name}" is already in Custom/3DModels; rename the file and choose it again'
    )
    assert digest_tree(root) == before


def test_a_source_that_is_not_a_model_is_refused_with_the_intake_reason(tmp_path):
    root, footprints = _setup(tmp_path)
    entries = _entries(root, footprints)
    notes = tmp_path / "src" / "notes.txt"
    notes.parent.mkdir()
    notes.write_text("not a model", encoding="utf-8")

    preview = _preview(root, [_attach(entries, "MODEL-MISSING", notes)])

    assert preview.changes == []
    assert [i.code for i in preview.issues] == ["intake.unsupported"]
    assert "pick a .step, .stp or .wrl file" in preview.issues[0].text

    missing = _preview(root, [_attach(entries, "MODEL-MISSING", tmp_path / "src" / "gone.step")])
    assert [i.code for i in missing.issues] == ["intake.not_found"]


def test_a_zip_must_hold_exactly_one_model(tmp_path):
    root, footprints = _setup(tmp_path)
    entries = _entries(root, footprints)
    folder = tmp_path / "zips"
    folder.mkdir()
    two = make_zip(folder / "two.zip", [("a.step", STEP_BYTES), ("b.wrl", VRML_BYTES)])
    none = make_zip(folder / "none.zip", [("readme.txt", b"hello")])
    one = make_zip(folder / "one.zip", [("models/ONE.stp", STEP_BYTES), ("readme.txt", b"hello")])

    refused = _preview(root, [_attach(entries, "MODEL-MISSING", two)])
    empty = _preview(root, [_attach(entries, "MODEL-MISSING", none)])
    accepted = _preview(root, [_attach(entries, "MODEL-MISSING", one)])

    assert refused.changes == []
    assert [i.code for i in refused.issues] == ["atomic.fix_incomplete"]
    assert "pick a file or a zip holding exactly one 3D model" in refused.issues[0].text
    assert empty.changes == [] and "intake.no_model_in_source" in [i.code for i in empty.issues]
    assert [c.rel_path for c in accepted.changes][0] == "Custom/3DModels/ONE.stp"
    assert accepted.changes[0].new_bytes == STEP_BYTES


def test_an_attach_without_a_chosen_file_is_incomplete(tmp_path):
    root, footprints = _setup(tmp_path)
    fill = _fill(_entries(root, footprints)["MODEL-MISSING"], "attach_model")

    assert atomic_fixes.complete_fill(fill, "") == "Choose a 3D model file first"
    preview = _preview(root, [fill])

    assert preview.changes == []
    assert [i.code for i in preview.issues] == ["atomic.fix_incomplete"]


def test_a_footprint_whose_models_all_resolve_is_skipped(tmp_path):
    root, footprints = _setup(tmp_path)
    source = _model_source(tmp_path)
    spec = _attach(_entries(root, footprints), "MODEL-MISSING", source)
    (root / "Custom" / "3DModels" / "MISSING-MODEL.step").write_bytes(STEP_BYTES)

    preview = _preview(root, [spec])

    assert preview.changes == []
    assert [(i.severity, i.code) for i in preview.issues] == [(Severity.INFO, "atomic.fix_skipped")]


def test_the_model_size_boundary_is_exact(tmp_path, monkeypatch):
    root, footprints = _setup(tmp_path)
    spec = _attach(_entries(root, footprints), "MODEL-MISSING", _model_source(tmp_path))
    limit = "kicad_lib_manager.importer.package.MAX_MEMBER_BYTES"

    monkeypatch.setattr(limit, len(STEP_BYTES))
    assert [c.rel_path for c in _preview(root, [spec]).changes][0] == "Custom/3DModels/NEW-MODEL.step"

    monkeypatch.setattr(limit, len(STEP_BYTES) - 1)
    refused = _preview(root, [spec])
    assert refused.changes == []
    assert [i.code for i in refused.issues] == ["intake.too_large"]


def test_the_kicad_file_size_boundary_is_exact(tmp_path, monkeypatch):
    root, footprints = _setup(tmp_path)
    specs = _fixes(_entries(root, footprints)["FFC-0.5-20"])
    size = (root / SYMBOL_REL).stat().st_size

    monkeypatch.setattr(atomic_fixes, "MAX_KICAD_TEXT_BYTES", size)
    assert len(_preview(root, specs).changes) == 1

    monkeypatch.setattr(atomic_fixes, "MAX_KICAD_TEXT_BYTES", size - 1)
    refused = _preview(root, specs)
    assert refused.changes == []
    assert [i.code for i in refused.issues] == ["atomic.file_too_large"]


def test_reserved_and_odd_model_names_are_not_usable():
    assert atomic_fixes._model_name_problem("CON.step") is not None
    assert atomic_fixes._model_name_problem("a:b.step") is not None
    assert atomic_fixes._model_name_problem("model.txt") is not None
    assert atomic_fixes._model_name_problem("fine-name.STEP") is None


def test_only_apply_preview_changes_anything_on_disk(tmp_path):
    root, footprints = _setup(tmp_path)
    entries = _entries(root, footprints)
    source = _model_source(tmp_path)
    two = make_zip(tmp_path / "two.zip", [("a.step", STEP_BYTES), ("b.wrl", VRML_BYTES)])
    before = digest_tree(tmp_path)
    specs = [
        *_fixes(entries["FFC-0.5-20"]),
        _attach(entries, "MODEL-MISSING", source),
        _attach(entries, "MODEL-NONE", two),
        atomic_fixes.complete_fill(_fill(entries["DS-EMPTY"], "fill_datasheet"), "https://example.com/x.pdf"),
    ]

    preview = _preview(root, specs)
    for change in preview.changes:
        preview_text(change)
    atomic_fixes.default_fix_backup_dir(tmp_path / "bk")
    atomic_fixes.complete_fill(specs[-1], "https://example.com/y.pdf")

    assert preview.changes
    assert digest_tree(tmp_path) == before


def test_only_the_apply_helpers_reach_a_write_call():
    import ast

    tree = ast.parse(Path(atomic_fixes.__file__).read_text(encoding="utf-8"))
    writers = {"atomic_write_text", "atomic_write_bytes", "backup_file", "unlink", "mkdir", "write_bytes", "write_text"}
    found = {}
    for function in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for call in (n for n in ast.walk(function) if isinstance(n, ast.Call)):
            if isinstance(call.func, ast.Attribute) and call.func.attr in writers:
                found.setdefault(function.name, set()).add(call.func.attr)
    assert set(found) <= {"_write", "_roll_back", "apply_preview"}, found
