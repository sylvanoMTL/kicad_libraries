"""Docs consistency checks for DOC-01: CLAUDE.md and research/LIBRARY-NAMING.md describe the
Atomic_ scheme and the two new menu actions, so the project docs and the shipped code cannot
drift apart. Reads only the tracked Markdown files and the two main_window text constants --
never the owner's live Custom/ (threat T-13-42; the session guard `_live_custom_untouched`
stays in force).
"""

from pathlib import Path

from kicad_lib_manager.main_window import MIGRATE_TEXT, SETUP_CHOOSER_TEXT

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _section(text: str, heading: str, *other_headings: str) -> str:
    """The text between `heading` and the next of `other_headings` (or end of file)."""
    start = text.index(heading) + len(heading)
    rest = text[start:]
    cut = len(rest)
    for other in other_headings:
        idx = rest.find(other)
        if idx != -1:
            cut = min(cut, idx)
    return rest[:cut]


def test_claude_md_describes_atomic_scheme():
    text = _read("CLAUDE.md")
    for token in (
        "Atomic_<",
        "Atomic_Footprints.pretty",
        "${CUSTOM_3DMODEL_DIR}",
        "atomic rule",
        "MPN",
        "Datasheet",
        "Description",
    ):
        assert token in text, f"CLAUDE.md is missing {token!r}"
    assert "<Type>_<SubCategory>_<Manufacturer>" not in text
    assert "Symbol and footprint folder names must match" not in text


def test_claude_md_names_the_new_actions():
    text = _read("CLAUDE.md")

    migrate_text = MIGRATE_TEXT.replace("&", "")
    setup_chooser_text = SETUP_CHOOSER_TEXT.replace("&", "")
    assert migrate_text in text
    assert setup_chooser_text in text
    assert "Ctrl+Shift+M" in text
    assert "Ctrl+Shift+K" in text

    gui_behavior = _section(text, "### GUI Behavior", "### Menu Shortcuts")
    assert "KICAD_LIB_GITHUB" in gui_behavior
    assert "another folder" in gui_behavior

    path_vars = _section(text, "## KiCad Path Variables", "## Library Naming Convention")
    assert "C:/Git_Repo_Clones/Kicad_Libraries/Custom/3DModels" in path_vars
    assert "C:/Git_Repo_Clones/Kicad_Libraries" in path_vars
    assert "KICAD_LIB_GITHUB" in path_vars
    assert "worktree" in path_vars


def test_library_naming_has_update_note():
    text = _read(".planning/research/LIBRARY-NAMING.md")
    assert "Atomic_Footprints.pretty" in text
    assert "Update 2026-11" in text
    assert "_MecaFrog" in text

    section_5 = _section(
        text,
        "## 5. Target libraries for the current Custom parts",
        "## 6.",
    )
    assert "Atomic_" in section_5
    assert "_MecaFrog" not in section_5


def test_project_md_marks_migration_delivered():
    text = _read(".planning/PROJECT.md")
    for line in text.splitlines():
        if "Own symbol libraries named `Atomic_" in line:
            assert not line.strip().startswith("- [ ]"), (
                f"requirement still unchecked: {line!r}"
            )
            break
    else:
        raise AssertionError("expected to find the Atomic_ naming requirement line in PROJECT.md")
