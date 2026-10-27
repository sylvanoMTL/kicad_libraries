"""Qt-free preview rows for an InstallPlan (Phase 5, PREV-01, PREV-06, PREV-07).

The dialog renders these rows and installs the very plan they were derived from, so the
preview can never describe something other than what apply_plan writes. Everything here is a
pure function of (plan, candidate, options); the only disk access is an existence check for a file
the plan leaves unchanged.

Seven sections in a fixed order: Files, Renames, Path rewrites, Field changes, Format, Conflicts,
Issues. An empty section is hidden, except Files. Field changes lists each incoming property the
plan drops, cleans or renames, as a pure function of plan.field_changes. Values the plan does not
carry (the old side of a path rewrite, the vendor model file name, the kicad-cli action) come from
the candidate, the options and the plan's Issue codes (RESEARCH Pitfall 1); the new side of every
rewrite is the text the planner wrote into the planned bytes.
"""

from dataclasses import dataclass
from pathlib import Path

from ..models import Severity
from .candidate import FootprintItem, ImportCandidate, ModelItem, SymbolItem
from .plan import MODEL_DIR_VAR, FileOp, InstallOptions, InstallPlan


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


_NONE = "(none)"
_KIND_LABEL = {"symbol": "symbol", "footprint": "footprint", "model": "3D model"}
_RENAME_DETAIL = {"symbol": "symbol", "footprint": "footprint", "model": "model file"}
_NEWER_CODE = "install.version_newer_than_target"
_SEVERITY_ROW = {
    Severity.ERROR: ("✖", "error"),
    Severity.WARNING: ("⚠", "warning"),
    Severity.SUCCESS: ("✓", "success"),
    Severity.INFO: ("", "default"),
}


# -- what the user chose ----------------------------------------------------------------


def _chosen_symbol(candidate: ImportCandidate, options: InstallOptions) -> SymbolItem | None:
    if options.symbol is not None:
        return next((s for s in candidate.symbols if s.name == options.symbol), None)
    return candidate.symbols[0] if len(candidate.symbols) == 1 else None


def _linked_footprint_item(candidate: ImportCandidate, options: InstallOptions) -> FootprintItem | None:
    if options.footprints:
        return next((f for f in candidate.footprints if f.name == options.footprints[0]), None)
    return candidate.footprints[0] if len(candidate.footprints) == 1 else None


def _chosen_model(candidate: ImportCandidate, options: InstallOptions) -> ModelItem | None:
    if options.no_model:
        return None
    if options.model is not None:
        return next((m for m in candidate.models if m.filename == options.model), None)
    return candidate.models[0] if len(candidate.models) == 1 else None


def _rel(plan: InstallPlan, path: Path) -> str:
    try:
        return path.relative_to(plan.layout.repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _size_kib(size: int) -> str:
    return f"{size / 1024:.1f} KiB"


# -- Files -----------------------------------------------------------------------------------


def _op_row(plan: InstallPlan, index: int, op: FileOp) -> tuple[PreviewRow, str]:
    """The row for one planned write and its category: mkdir, new or modified."""
    rel = _rel(plan, op.path)
    if op.kind == "mkdir":
        row = PreviewRow(
            text=f"+ {rel}/", detail="new", glyph="+", tone="success", kind="file",
            path=op.path, op_index=index,
        )
        return row, "mkdir"
    new = op.base_sha256 is None
    word = "new" if new else "modified"
    detail = f"{word}, {_size_kib(op.source.size)}" if op.kind == "model" and op.source is not None else word
    row = PreviewRow(
        text=f"{'+' if new else '~'} {rel}",
        detail=detail,
        glyph="+" if new else "~",
        tone="success" if new else "default",
        kind="file",
        path=op.path,
        op_index=index,
    )
    return row, word


def _unchanged_row(plan: InstallPlan, path: Path, kept: bool) -> PreviewRow:
    return PreviewRow(
        text=f"= {_rel(plan, path)}",
        detail="unchanged (kept existing)" if kept else "unchanged",
        glyph="=",
        tone="muted",
        kind="file",
        path=path,
    )


def _file_rows(plan: InstallPlan) -> list[tuple[PreviewRow, str]]:
    """Files rows in slot order with their category: mkdir ops, model, footprints, symbol library."""
    by_path: dict[str, int] = {}
    for index, op in enumerate(plan.ops):
        by_path[op.path.as_posix()] = index
        if op.listed_path is not None:
            by_path.setdefault(op.listed_path.as_posix(), index)

    rows: list[tuple[PreviewRow, str]] = []
    used: set[int] = set()

    def add_op(index: int) -> None:
        used.add(index)
        rows.append(_op_row(plan, index, plan.ops[index]))

    for index, op in enumerate(plan.ops):
        if op.kind == "mkdir":
            add_op(index)

    def add_slot(path: Path, conflicts: list) -> None:
        index = by_path.get(path.as_posix())
        if index is not None:
            if index not in used:
                add_op(index)
            return
        # An unresolved conflict leaves the file out until it is settled; a settled one that needs no write is unchanged
        if any(c.resolution is None for c in conflicts) or not path.exists():
            return
        kept = any(c.resolution is not None and c.resolution.action == "skip" for c in conflicts)
        rows.append((_unchanged_row(plan, path, kept), "unchanged"))

    if plan.model_file:
        wanted = plan.model_file.casefold()
        add_slot(
            plan.layout.models_dir / plan.model_file,
            [c for c in plan.conflicts if c.kind == "model" and c.name.casefold() == wanted],
        )
    for name in plan.footprint_names:
        wanted = name.casefold()
        add_slot(
            plan.pretty_path / f"{name}.kicad_mod",
            [c for c in plan.conflicts if c.kind == "footprint" and c.name.casefold() == wanted],
        )
    if plan.symbol_names:
        add_slot(plan.symbol_lib_path, [c for c in plan.conflicts if c.kind == "symbol"])
    # Never hide a write: an op that fits no slot still gets its row
    for index in range(len(plan.ops)):
        if index not in used:
            add_op(index)
    return rows


def _files_section(plan: InstallPlan) -> PreviewSection:
    return PreviewSection("Files", tuple(row for row, _ in _file_rows(plan)))


# -- Renames -----------------------------------------------------------------------------------


def _renames_section(plan: InstallPlan, candidate: ImportCandidate, options: InstallOptions) -> PreviewSection:
    rows: list[PreviewRow] = []
    model = _chosen_model(candidate, options) if plan.model_file else None
    if model is not None:
        model_rename = next((r for r in plan.renames if r.kind == "model"), None)
        kept = any(c.kind == "model" and c.resolution is not None and c.resolution.action == "skip" for c in plan.conflicts)
        default = model_rename.old if model_rename is not None else plan.model_file
        # The vendor file name becomes the planned one (<MPN>.<ext>); plan.renames only knows conflict renames
        if not kept and model.filename != default:
            rows.append(PreviewRow(
                text=f"{model.filename} → {default}", detail=_RENAME_DETAIL["model"], kind="rename",
            ))
    for rename in plan.renames:
        rows.append(PreviewRow(
            text=f"{rename.old} → {rename.new}", detail=_RENAME_DETAIL.get(rename.kind, rename.kind), kind="rename",
        ))
    return PreviewSection("Renames", tuple(rows))


# -- Path rewrites -------------------------------------------------------------------------------


def _rewrites_section(plan: InstallPlan, candidate: ImportCandidate, options: InstallOptions) -> PreviewSection:
    if not plan.symbol_names:
        return PreviewSection("Path rewrites", ())
    symbol = _chosen_symbol(candidate, options)
    linked = _linked_footprint_item(candidate, options)
    meta = symbol.meta if symbol is not None else None

    def row(field: str, old: str, new: str) -> PreviewRow:
        return PreviewRow(text=field, detail=f"{old or _NONE} → {new or _NONE}", kind="rewrite")

    rows: list[PreviewRow] = []
    # A kept symbol is not edited, so its Footprint field and filters are not rewritten
    if plan.linked_footprint is not None:
        rows.append(row("Footprint", meta.footprint_field if meta else "", plan.footprint_link or ""))
    if plan.model_file:
        old_model = linked.model_paths[0] if linked is not None and linked.model_paths else ""
        rows.append(row("Model", old_model, f"{MODEL_DIR_VAR}/{plan.model_file}"))
    if plan.linked_footprint is not None:
        rows.append(row("Footprint Filter", meta.fp_filters if meta else "", " ".join(plan.footprint_names)))
    return PreviewSection("Path rewrites", tuple(rows))


# -- Field changes ---------------------------------------------------------------------------------


_DROP_REASON = {
    "volatile": "price or stock data goes stale",
    "placeholder": "empty or placeholder value",
    "duplicate": "duplicate Manufacturer/MPN alias",
}
_SHOWN_LIMIT = 60
_SHOWN_KEPT = 57


def _shown(value: str) -> str:
    """A property value on one line: CR, LF and TAB as escapes, cut to 57 characters plus "..." past 60."""
    if not value:
        return "(empty)"
    text = value.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return text if len(text) <= _SHOWN_LIMIT else text[:_SHOWN_KEPT] + "..."


def _field_changes_section(plan: InstallPlan) -> PreviewSection:
    several = len({change.symbol for change in plan.field_changes}) > 1
    rows: list[PreviewRow] = []
    for change in plan.field_changes:
        if change.action == "drop":
            label = "Drop"
            reason = _DROP_REASON.get(change.reason, change.reason)
            detail = f"{_shown(change.old)} → (removed): {reason}"
        elif change.action == "clean":
            label = "Clean"
            detail = f"{_shown(change.old)} → {_shown(change.new)}"
        else:
            label = "Rename"
            detail = f"→ {change.new}"
        prefix = f"{change.symbol}: " if several else ""
        rows.append(PreviewRow(text=f"{prefix}{label} {change.field}", detail=detail, kind="rewrite"))
    return PreviewSection("Field changes", tuple(rows))


# -- Format ---------------------------------------------------------------------------------------


def _format_section(plan: InstallPlan) -> PreviewSection:
    newer = any(i.code == _NEWER_CODE for i in plan.issues)
    if not plan.symbol_names and not newer:
        return PreviewSection("Format", ())
    rows: list[PreviewRow] = []
    if plan.symbol_names:
        source = plan.source_version if plan.source_version is not None else "unknown"
        target = plan.target_version if plan.target_version is not None else "unknown"
        rows.append(PreviewRow(text=f"Symbol format {source} → {target}", kind="format"))
    if newer:
        action = ("✖", "error", "Incoming file is newer than the library - refused")
    elif plan.normalised:
        action = ("", "default", "kicad-cli will normalise the incoming symbol")
    elif plan.source_version is not None and plan.source_version == plan.target_version:
        action = ("", "default", "Already in the target format")
    elif plan.tools.kicad_cli is None:
        action = ("⚠", "warning", "kicad-cli not found - symbol merged as-is")
    else:
        action = ("⚠", "warning", "Symbol merged as-is - see Issues")
    glyph, tone, text = action
    rows.append(PreviewRow(text=f"{glyph} {text}" if glyph else text, glyph=glyph, tone=tone, kind="format"))
    return PreviewSection("Format", tuple(rows))


# -- Conflicts and Issues ----------------------------------------------------------------------------


def _conflicts_section(plan: InstallPlan) -> PreviewSection:
    rows: list[PreviewRow] = []
    for conflict in plan.conflicts:
        resolution = conflict.resolution
        tone = "default"
        if resolution is None:
            detail, tone = "Needs a choice", "warning"
        elif resolution.action == "overwrite":
            detail = "Overwrite"
        elif resolution.action == "rename":
            detail = f"Rename → {resolution.rename_to or conflict.suggested_name}"
        elif resolution.action == "skip":
            detail = "Skip - keep & link"
        else:
            detail = resolution.action
        rows.append(PreviewRow(
            text=f"{_KIND_LABEL.get(conflict.kind, conflict.kind)} {conflict.name}",
            detail=detail,
            tone=tone,
            kind="conflict",
            key=conflict.key,
        ))
    return PreviewSection("Conflicts", tuple(rows))


def _issues_section(plan: InstallPlan) -> PreviewSection:
    rows: list[PreviewRow] = []
    for issue in plan.issues:
        glyph, tone = _SEVERITY_ROW[issue.severity]
        rows.append(PreviewRow(
            text=f"{glyph} {issue.text}" if glyph else issue.text, glyph=glyph, tone=tone, kind="issue",
        ))
    return PreviewSection("Issues", tuple(rows))


# -- entry points -------------------------------------------------------------------------------------


def preview_sections(
    plan: InstallPlan, candidate: ImportCandidate, options: InstallOptions
) -> tuple[PreviewSection, ...]:
    """The preview sections for a plan, in the fixed display order; only Files is shown when empty."""
    sections = (
        _files_section(plan),
        _renames_section(plan, candidate, options),
        _rewrites_section(plan, candidate, options),
        _field_changes_section(plan),
        _format_section(plan),
        _conflicts_section(plan),
        _issues_section(plan),
    )
    return tuple(s for i, s in enumerate(sections) if i == 0 or s.rows)


def file_counts(plan: InstallPlan, candidate: ImportCandidate, options: InstallOptions) -> FileCounts:
    """Count the new, modified and unchanged files of the Files section; folders are not files."""
    categories = [category for _, category in _file_rows(plan)]
    return FileCounts(
        new=categories.count("new"),
        modified=categories.count("modified"),
        unchanged=categories.count("unchanged"),
    )
