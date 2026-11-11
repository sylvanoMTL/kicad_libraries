"""The migration draft: save, restore and changed-since-draft detection (D-14, Phase 13 Plan 08)."""

from pathlib import Path

import pytest
from migrationfixtures import write_v1_custom
from PySide6.QtCore import QSettings

from kicad_lib_manager import settings
from kicad_lib_manager.importer.migration.draft import (
    DRAFT_FORMAT,
    MAX_DRAFT_BYTES,
    LoadedDraft,
    changed_parts,
    clear_draft,
    fingerprints,
    load_draft,
    save_draft,
)
from kicad_lib_manager.importer.migration.inventory import read_inventory
from kicad_lib_manager.importer.migration.plan import MigrationChoices, PartChoice
from kicad_lib_manager.importer.plan import Resolution
from kicad_lib_manager.models import Severity


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )


# ── Round trip ───────────────────────────────────────────────────────

def test_draft_round_trip_keeps_every_choice(tmp_path):
    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    choice = PartChoice(
        library="Atomic_Foo",
        symbol_name="FOO1-REV2",
        mpn="FOO1-MPN",
        manufacturer="ACME",
        datasheet="https://acme.example/foo.pdf",
        description="Foo widget",
        keywords="foo widget",
        fp_description="Foo footprint",
        fp_tags="foo smd",
        footprint_target="official",
        official_footprint="Package_SO:SOIC-8",
        footprint_name="FOO-FP",
        model_name="foo.step",
        model_source="added_separately.step",
        derive=False,
    )
    choices = MigrationChoices(
        parts={key: choice},
        leftovers={"Custom/Footprints/Bar.pretty/Bar.kicad_mod": True},
        resolutions={"atomic_footprints::Bar": Resolution(action="rename", rename_to="Bar2")},
    )
    prints = {key: "abc123"}
    path = tmp_path / "draft.json"

    assert save_draft(path, tmp_path, choices, prints) is None
    loaded = load_draft(path, tmp_path)

    assert isinstance(loaded, LoadedDraft)
    assert loaded.choices == choices
    assert loaded.fingerprints == prints


def test_draft_round_trip_with_no_choices(tmp_path):
    """A part with a fingerprint but no owner choice round-trips with an empty MigrationChoices.parts entry."""
    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    choices = MigrationChoices()
    prints = {key: "deadbeef"}
    path = tmp_path / "draft.json"

    assert save_draft(path, tmp_path, choices, prints) is None
    loaded = load_draft(path, tmp_path)

    assert isinstance(loaded, LoadedDraft)
    assert loaded.choices.parts == {}
    assert loaded.fingerprints == prints


# ── Changed since draft ──────────────────────────────────────────────

def test_changed_part_is_flagged(tmp_path):
    layout = write_v1_custom(tmp_path)
    before = fingerprints(read_inventory(layout))
    path = tmp_path / "draft.json"
    assert save_draft(path, tmp_path, MigrationChoices(), before) is None
    loaded = load_draft(path, tmp_path)
    assert isinstance(loaded, LoadedDraft)

    # Edit one symbol's block (the Datasheet text of the single symbol in a single-symbol
    # library, so only its own block changes), one footprint's bytes (linked by one part here)
    # and one model's bytes (shared by two parts, via one footprint linking both model files) -
    # each should flag exactly the parts linked to what changed, and no others.
    osc_sym = layout.symbols_dir / "Oscillator_TCXO_Abracon.kicad_sym"
    original = osc_sym.read_bytes()
    edited = original.replace(b"ATXK-H14.pdf", b"ATXK-H14-edited.pdf")
    assert edited != original
    osc_sym.write_bytes(edited)

    linked_fp = layout.footprints_dir / "Atomic_Footprints.pretty" / "CM315.kicad_mod"
    fp_original = linked_fp.read_bytes()
    fp_edited = fp_original.replace(b"(size 0.9 0.6)", b"(size 0.95 0.6)", 1)
    assert fp_edited != fp_original
    linked_fp.write_bytes(fp_edited)

    model_path = layout.models_dir / "NORA-W106-00B.step"
    model_original = model_path.read_bytes()
    model_path.write_bytes(model_original + b"EXTRA")

    after_inventory = read_inventory(layout)
    after = fingerprints(after_inventory)
    flagged = changed_parts(loaded, after)

    edited_part = next(
        p for p in after_inventory.parts
        if p.rel_path.endswith("Oscillator_TCXO_Abracon.kicad_sym")
    )
    cm315_part = next(
        p for p in after_inventory.parts
        if p.rel_path.endswith("Atomic_Oscillator.kicad_sym")
    )
    nora_parts = {
        p.key for p in after_inventory.parts
        if p.rel_path.endswith("IC_Wireless_BLE_uBlox.kicad_sym")
    }

    expected = {edited_part.key, cm315_part.key} | nora_parts
    assert flagged == expected

    untouched = set(before) - expected
    assert flagged.isdisjoint(untouched)


def test_saved_keys_missing_now_are_flagged(tmp_path):
    layout = write_v1_custom(tmp_path)
    before = fingerprints(read_inventory(layout))
    path = tmp_path / "draft.json"
    assert save_draft(path, tmp_path, MigrationChoices(), before) is None
    loaded = load_draft(path, tmp_path)
    assert isinstance(loaded, LoadedDraft)

    current = dict(before)
    removed_key = next(iter(current))
    del current[removed_key]

    assert removed_key in changed_parts(loaded, current)


def test_unreadable_model_contributes_unreadable_text_not_a_crash(tmp_path):
    """A model a footprint links but that cannot be read never raises; it contributes the text "unreadable"."""
    import hashlib

    from kicad_lib_manager.importer.layout import RepoLayout
    from kicad_lib_manager.importer.migration.inventory import Inventory, InventoryFootprint, InventoryPart

    layout = RepoLayout.for_repo(tmp_path)
    layout.models_dir.mkdir(parents=True)
    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    part = InventoryPart(
        key=key, library="Foo", rel_path=key[0], name="FOO1", extends=None,
        fields={}, footprint="Foo:FOO1", version=None, block_sha256="abc", atomic=False,
    )
    footprint = InventoryFootprint(
        library="Foo", name="FOO1", rel_path="Custom/Footprints/Foo.pretty/FOO1.kicad_mod",
        internal_name="FOO1", models=("missing.step",), sha256="def", linked_by=(key,),
    )
    inventory = Inventory(
        layout=layout, parts=(part,), footprints=(footprint,), models=(), model_linkers={},
        bak_files=(), symbol_libraries=("Foo",), footprint_libraries=("Foo",), issues=(),
    )

    prints = fingerprints(inventory)

    expected = hashlib.sha256()
    expected.update(b"abc")
    expected.update(b"def")
    expected.update(b"unreadable")
    assert prints[key] == expected.hexdigest()


# ── Draft file location ──────────────────────────────────────────────

def test_draft_file_is_beside_settings(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    draft_file = settings.migration_draft_file(repo)
    settings_dir = Path(settings.get_settings().fileName()).parent

    assert draft_file.parent == settings_dir / "migration_draft"
    assert draft_file.suffix == ".json"
    assert repo.resolve() not in draft_file.parents
    assert len(draft_file.stem) == 16


# ── Missing, oversized, malformed, wrong-format, other-repository ───

def test_missing_draft_is_none(tmp_path):
    result = load_draft(tmp_path / "missing.json", tmp_path)
    assert result.severity is Severity.INFO
    assert result.code == "draft.none"


@pytest.mark.parametrize(
    "text",
    [
        "{not json",
        "[]",
        "null",
        '{"format": 99}',
        "\x00\x01",
    ],
)
def test_bad_drafts_start_clean(tmp_path, text):
    path = tmp_path / "draft.json"
    path.write_text(text, encoding="utf-8")
    result = load_draft(path, tmp_path)
    assert result.severity is Severity.INFO
    assert result.code == "draft.unreadable"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p["parts"][0].update(key=["only-one"]),
        lambda p: p["parts"][0]["choice"].update(mpn=5),
        lambda p: p["parts"][0]["choice"].update(footprint_target="elsewhere"),
        lambda p: p["resolutions"].append(["k", "delete", None]),
        lambda p: p["leftovers"].append(["Custom/Footprints/X.pretty/X.kicad_mod", "yes"]),
        lambda p: p["leftovers"].append(["only-one-field"]),
        lambda p: p["resolutions"].append(["k", "rename", 5]),
        lambda p: p["parts"].append({"key": ["rel", "name"], "print": 5}),
    ],
)
def test_bad_draft_contents_start_clean(tmp_path, mutate):
    import json

    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    choices = MigrationChoices(parts={key: PartChoice(mpn="FOO1")})
    prints = {key: "abc"}
    path = tmp_path / "draft.json"
    assert save_draft(path, tmp_path, choices, prints) is None

    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = load_draft(path, tmp_path)
    assert result.severity is Severity.INFO
    assert result.code == "draft.unreadable"


def test_deeply_nested_draft_is_unreadable(tmp_path):
    path = tmp_path / "draft.json"
    nested = "[" * 100000 + "]" * 100000
    path.write_text(nested, encoding="utf-8")
    result = load_draft(path, tmp_path)
    assert result.severity is Severity.INFO
    assert result.code == "draft.unreadable"


def test_oversized_draft_is_unreadable(tmp_path, monkeypatch):
    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    choices = MigrationChoices(parts={key: PartChoice(mpn="FOO1")})
    path = tmp_path / "draft.json"
    assert save_draft(path, tmp_path, choices, {key: "abc"}) is None

    import kicad_lib_manager.importer.migration.draft as draft_mod
    monkeypatch.setattr(draft_mod, "MAX_DRAFT_BYTES", 4)

    result = load_draft(path, tmp_path)
    assert result.severity is Severity.INFO
    assert result.code == "draft.unreadable"


def test_other_repo_draft_is_ignored(tmp_path):
    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    choices = MigrationChoices(parts={key: PartChoice(mpn="FOO1")})
    path = tmp_path / "draft.json"
    other_repo = tmp_path / "other_repo"
    assert save_draft(path, other_repo, choices, {key: "abc"}) is None

    this_repo = tmp_path / "this_repo"
    this_repo.mkdir()
    result = load_draft(path, this_repo)
    assert result.severity is Severity.INFO
    assert result.code == "draft.other_repo"


def test_save_failure_is_one_warning(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"i am a file, not a directory")
    path = blocker / "sub" / "draft.json"

    issue = save_draft(path, tmp_path, MigrationChoices(), {})
    assert issue is not None
    assert issue.severity is Severity.WARNING
    assert issue.code == "draft.save_failed"
    assert issue.text.startswith("Could not save the migration draft: ")
    assert not path.exists()


def test_clear_draft(tmp_path):
    key = ("Custom/Symbols/Foo.kicad_sym", "FOO1")
    path = tmp_path / "draft.json"
    assert save_draft(path, tmp_path, MigrationChoices(), {key: "abc"}) is None
    assert path.exists()

    assert clear_draft(path) is None
    assert not path.exists()

    # Clearing an already-missing file is fine.
    assert clear_draft(path) is None


def test_clear_draft_failure_is_one_warning(tmp_path, monkeypatch):
    path = tmp_path / "draft.json"
    path.write_text("{}", encoding="utf-8")

    def _raise(self):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "unlink", _raise)
    issue = clear_draft(path)
    assert issue is not None
    assert issue.severity is Severity.WARNING
    assert issue.code == "draft.clear_failed"


def test_draft_format_and_max_bytes_constants():
    assert DRAFT_FORMAT == 1
    assert MAX_DRAFT_BYTES == 4 * 1024 * 1024
