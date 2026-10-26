"""The fix engine behind the check dialog: previewed, backed up, written atomically, gone on the next scan (SCAN-03).

Every test writes only into tmp_path trees; none touches the real Custom/.
"""

import hashlib
import os
from pathlib import Path

import pytest

from customfixtures import atomic_lib, atomic_part, write_atomic_custom, write_fake_kicad
from installfixtures import V6_VERSION, target_lib
from kicad_lib_manager import atomic_fixes, kicad_files
from kicad_lib_manager.atomic_fixes import apply_preview, build_preview, preview_text
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import FixSpec, Severity

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
