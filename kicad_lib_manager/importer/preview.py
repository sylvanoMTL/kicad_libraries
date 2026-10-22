"""Qt-free preview rows for an InstallPlan (Phase 5, PREV-01, PREV-07).

The dialog renders these rows and installs the very plan they were derived from, so the
preview can never describe something other than what apply_plan writes. Everything here is a
pure function of (plan, candidate, options); nothing reads or writes the disk.

Plan 05-01 produces the Files section only. Later plans add Renames, Path rewrites, Format,
Conflicts and Issues sections and the unchanged-file rows behind the same two entry points.
"""

from dataclasses import dataclass
from pathlib import Path

from .candidate import ImportCandidate
from .plan import FileOp, InstallOptions, InstallPlan


@dataclass(frozen=True)
class PreviewRow:
    """One line of the preview tree.

    tone: default | success | muted | warning | error.
    kind: file | rename | rewrite | format | conflict | issue.
    op_index points back at plan.ops for file rows, so a content view can find the bytes.
    """

    text: str
    detail: str = ""
    glyph: str = ""
    tone: str = "default"
    kind: str = ""
    path: Path | None = None
    key: str = ""
    op_index: int | None = None


@dataclass(frozen=True)
class PreviewSection:
    name: str
    rows: tuple[PreviewRow, ...]

    @property
    def title(self) -> str:
        return f"{self.name} ({len(self.rows)})"


@dataclass(frozen=True)
class FileCounts:
    new: int
    modified: int
    unchanged: int


def _relative(plan: InstallPlan, op: FileOp) -> str:
    try:
        return op.path.relative_to(plan.layout.repo_root).as_posix()
    except ValueError:
        return op.path.as_posix()


def _file_row(plan: InstallPlan, index: int, op: FileOp) -> PreviewRow:
    rel = _relative(plan, op)
    if op.kind == "mkdir":
        return PreviewRow(
            text=f"+ {rel}/", detail="new", glyph="+", tone="success", kind="file",
            path=op.path, op_index=index,
        )
    if op.base_sha256 is None:
        return PreviewRow(
            text=f"+ {rel}", detail="new", glyph="+", tone="success", kind="file",
            path=op.path, op_index=index,
        )
    return PreviewRow(
        text=f"~ {rel}", detail="modified", glyph="~", tone="default", kind="file",
        path=op.path, op_index=index,
    )


def preview_sections(
    plan: InstallPlan, candidate: ImportCandidate, options: InstallOptions
) -> tuple[PreviewSection, ...]:
    """The preview sections for a plan, in display order; plan.ops order is kept."""
    files = tuple(_file_row(plan, index, op) for index, op in enumerate(plan.ops))
    return (PreviewSection("Files", files),)


def file_counts(plan: InstallPlan, candidate: ImportCandidate, options: InstallOptions) -> FileCounts:
    """Count the files the plan writes; unchanged files are derived by a later plan from the same signature."""
    writes = [op for op in plan.ops if op.kind != "mkdir"]
    new = sum(1 for op in writes if op.base_sha256 is None)
    return FileCounts(new=new, modified=len(writes) - new, unchanged=0)
