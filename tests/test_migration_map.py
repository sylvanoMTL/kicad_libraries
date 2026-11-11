"""Custom/MIGRATION-ATOMIC.md: sections, empty wording, backtick safety and the earlier-migrations
append (Phase 13, D-16, MIG-05).
"""

from kicad_lib_manager.importer.migration.mapfile import (
    EARLIER_HEADING,
    NONE_TEXT,
    RECOVERY_NOTE,
    RELINK_STEPS,
    map_text,
)
from kicad_lib_manager.importer.plan import Rename

TODAY = "2026-11-11"


def test_map_sections_and_relink_steps():
    text = map_text(
        library_map=[("LibB", "Atomic_Connector"), ("LibA", "Atomic_Connector")],
        symbol_renames=[
            Rename("symbol", "LibA:PART1", "Atomic_Connector:PART1"),
            Rename("symbol", "LibB:PART3", "Atomic_Connector:PART3"),
            Rename("symbol", "LibA:PART2", "Atomic_Connector:PART2"),
        ],
        footprint_links=[
            ("LibB:FP2", "Atomic_Footprints:FP2"),
            ("LibA:FP1", "Atomic_Footprints:FP1"),
        ],
        model_renames=[Rename("model", "FP1.step", "PART1.step")],
        today=TODAY,
    )

    heading_index = text.index(f"# Atomic_ migration — {TODAY}")
    libraries_index = text.index("## Libraries")
    symbols_index = text.index("## Symbols")
    footprints_index = text.index("## Footprint links")
    models_index = text.index("## 3D models")
    recovery_index = text.index(RECOVERY_NOTE)
    relink_index = text.index("## Relink existing KiCad projects")
    assert (
        heading_index
        < libraries_index
        < symbols_index
        < footprints_index
        < models_index
        < recovery_index
        < relink_index
    )

    assert "pre-atomic" in RECOVERY_NOTE
    assert "LibA -> Atomic_Connector" in text
    assert "LibB -> Atomic_Connector" in text
    assert "FP1.step -> PART1.step" in text
    assert "LibA:PART1 -> Atomic_Connector:PART1" in text

    # Sorted case-insensitively within a section.
    assert text.index("LibA -> Atomic_Connector") < text.index("LibB -> Atomic_Connector")

    step_positions = [text.index(step) for step in RELINK_STEPS]
    assert step_positions == sorted(step_positions)
    assert all(step_positions[i] < step_positions[i + 1] for i in range(len(step_positions) - 1))

    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_empty_sections_say_none():
    text = map_text(library_map=[], symbol_renames=[], footprint_links=[], model_renames=[], today=TODAY)

    lines = text.splitlines()
    assert lines[lines.index("## Libraries") + 1] == NONE_TEXT
    assert lines[lines.index("## Symbols") + 1] == NONE_TEXT
    assert lines[lines.index("## Footprint links") + 1] == NONE_TEXT
    assert lines[lines.index("## 3D models") + 1] == NONE_TEXT
    assert text.count(NONE_TEXT) == 4


def test_earlier_text_kept_below():
    previous = "# Atomic_ migration — 2026-01-01\n\nOld content\n"
    text = map_text(
        library_map=[], symbol_renames=[], footprint_links=[], model_renames=[], today=TODAY, previous=previous
    )

    assert text.index(f"# Atomic_ migration — {TODAY}") < text.index(f"## {EARLIER_HEADING}")
    assert text.index(f"## {EARLIER_HEADING}") < text.index("Old content")
    assert text.endswith("Old content\n")
    assert not text.endswith("\n\n")


def test_names_with_backticks_are_safe():
    text = map_text(
        library_map=[("Weird`Lib", "Atomic_Weird")],
        symbol_renames=[],
        footprint_links=[],
        model_renames=[],
        today=TODAY,
    )

    assert "Weird`Lib" not in text
    assert "Weird'Lib -> Atomic_Weird" in text

    encoded = text.encode("utf-8")
    assert b"\r" not in encoded
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_map_is_plain():
    text = map_text(
        library_map=[("LibA", "Atomic_Connector")],
        symbol_renames=[Rename("symbol", "LibA:PART1", "Atomic_Connector:PART1")],
        footprint_links=[("LibA:FP1", "Atomic_Footprints:FP1")],
        model_renames=[Rename("model", "FP1.step", "PART1.step")],
        today=TODAY,
    )

    assert "ki_" not in text
    assert "migration." not in text
