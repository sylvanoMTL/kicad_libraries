"""Custom/MIGRATION-ATOMIC.md: the one write that tells the owner what moved and how to relink KiCad (D-16, MIG-05).

Markdown, UTF-8, LF line endings, one trailing newline. Every old/new name has any backtick
replaced by an apostrophe before it is written, so a name can never open or break a Markdown code
span elsewhere in the file (T-13-29). Names are written as plain "old -> new" text rather than
wrapped in their own code span: tests/test_migration_e2e.py#test_map_file_lists_the_changes (frozen;
from plan 13-06, not editable here) asserts the exact substrings "LibA -> Atomic_Connector" and
"LibA:PARTA1 -> Atomic_Connector:PARTA1", which a code-span wrapper would break by inserting a
backtick between the name and the arrow. An empty section says NONE_TEXT instead of an empty list.
previous, when given, is this run's own text followed by an "Earlier migrations" section holding
the previous file's text unchanged, so a second migration's map keeps the first one's history.
"""

from collections.abc import Sequence

from ..plan import Rename

RELINK_STEPS: tuple[str, str, str] = (
    "In the Schematic Editor: Tools > Edit Symbol Library Links..., then pick each old library "
    "and choose its new Atomic_ library",
    "Tools > Update Symbols from Library..., to take the renamed symbols and their fields",
    "Tools > Update PCB from Schematic... (F8), to relink the footprints on the board",
)

NONE_TEXT = "None"
EARLIER_HEADING = "Earlier migrations"
RECOVERY_NOTE = (
    "Everything before this migration is kept in the tag pre-atomic of the Custom repository "
    "(git -C Custom log pre-atomic)."
)
# REQUIREMENTS Out of Scope: the app never edits a KiCad project file itself.
_NEVER_EDITS_NOTE = (
    "This app does not edit any KiCad project file itself; apply the three steps above by hand in "
    "every project that still references an old library."
)
_INTRO = "What this migration moved or renamed, and how to relink an existing KiCad project."


def _safe(name: str) -> str:
    """name with any backtick replaced by an apostrophe, so it can never open or break a code span elsewhere."""
    return name.replace(chr(96), chr(39))


def _pair_lines(pairs: Sequence[tuple[str, str]]) -> list[str]:
    ordered = sorted(pairs, key=lambda pair: (pair[0].casefold(), pair[1].casefold()))
    return [f"- {_safe(old)} -> {_safe(new)}" for old, new in ordered] or [NONE_TEXT]


def _rename_lines(renames: Sequence[Rename]) -> list[str]:
    ordered = sorted(renames, key=lambda rename: (rename.old.casefold(), rename.new.casefold()))
    return [f"- {_safe(rename.old)} -> {_safe(rename.new)}" for rename in ordered] or [NONE_TEXT]


def map_text(
    *,
    library_map: Sequence[tuple[str, str]],
    symbol_renames: Sequence[Rename],
    footprint_links: Sequence[tuple[str, str]],
    model_renames: Sequence[Rename],
    today: str,
    previous: str | None = None,
) -> str:
    """Build the Markdown MIGRATION-ATOMIC.md section for one run; previous, when given, follows it."""
    lines = [f"# Atomic_ migration — {today}", "", _INTRO, ""]
    lines.append("## Libraries")
    lines.extend(_pair_lines(library_map))
    lines.append("")
    lines.append("## Symbols")
    lines.extend(_rename_lines(symbol_renames))
    lines.append("")
    lines.append("## Footprint links")
    lines.extend(_pair_lines(footprint_links))
    lines.append("")
    lines.append("## 3D models")
    lines.extend(_rename_lines(model_renames))
    lines.append("")
    lines.append(RECOVERY_NOTE)
    lines.append("")
    lines.append("## Relink existing KiCad projects")
    lines.extend(f"{index}. {step}" for index, step in enumerate(RELINK_STEPS, start=1))
    lines.append("")
    lines.append(_NEVER_EDITS_NOTE)
    text = "\n".join(lines) + "\n"
    if previous:
        text = f"{text}\n## {EARLIER_HEADING}\n\n" + previous.removesuffix("\n") + "\n"
    return text
