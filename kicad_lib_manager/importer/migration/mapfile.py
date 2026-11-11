"""Custom/MIGRATION-ATOMIC.md: the one write that tells the owner what moved and how to relink KiCad (D-16, MIG-05).

13-12 hardens the wording and the empty-section handling; this plan fixes the headings and the
three relink steps every later plan writes under.
"""

from collections.abc import Sequence

from ..plan import Rename

RELINK_STEPS: tuple[str, str, str] = (
    "In the Schematic Editor: Tools > Edit Symbol Library Links..., then pick each old library "
    "and choose its new Atomic_ library",
    "Tools > Update Symbols from Library..., to take the renamed symbols and their fields",
    "Tools > Update PCB from Schematic... (F8), to relink the footprints on the board",
)


def _pair_lines(pairs: Sequence[tuple[str, str]]) -> list[str]:
    return [f"- {old} -> {new}" for old, new in pairs] or ["- (none)"]


def _rename_lines(renames: Sequence[Rename]) -> list[str]:
    return [f"- {rename.old} -> {rename.new}" for rename in renames] or ["- (none)"]


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
    lines = [f"# Atomic_ migration — {today}", ""]
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
    lines.append("## Relink existing KiCad projects")
    lines.extend(f"{index}. {step}" for index, step in enumerate(RELINK_STEPS, start=1))
    text = "\n".join(lines) + "\n"
    if previous:
        text += "\n## Earlier migrations\n\n" + previous
    return text
