"""Build the migration's CommitPlan from a successful MigrationResult (MIG-04, D-16).

Pure: no git, no Qt. The migration's own CommitPlan reuses the Phase 11/13-04 CommitFile.deleted
and CommitPlan.message support rather than adding a parallel shape, so the unchanged commit_step
and commit_gate carry it through exactly as any install-produced plan.
"""

from datetime import date
from pathlib import Path

from ...models import Issue, Severity
from ..commit_plan import CommitFile, CommitPlan, sanitize_line
from .applier import MigrationResult
from .plan import MigrationPlan

MIGRATION_SUBJECT = "Migrate Custom parts to Atomic_ libraries"
MIGRATION_VENDOR = "Atomic_ migration"

_RELINK_NOTE = (
    "See MIGRATION-ATOMIC.md for the symbol renames, the footprint links and the KiCad relink steps."
)


def migration_message(plan: MigrationPlan, today: str | None = None) -> str:
    """The Custom commit message (D-16): subject, the library map, a pointer to the map file, the date trailer."""
    stamp = today if today is not None else date.today().isoformat()
    lib_lines = "\n".join(sanitize_line(f"{old} -> {new}") for old, new in plan.library_map)
    libraries_para = "Libraries:" + (f"\n{lib_lines}" if lib_lines else "")
    trailer_para = f"Migration-Date: {stamp}"
    return "\n\n".join((MIGRATION_SUBJECT, libraries_para, _RELINK_NOTE, trailer_para))


def _kind_of(rel: str) -> str:
    """The CommitFile.kind for a path relative to custom_dir, matching build_commit_plan's own kinds."""
    if rel.startswith("Symbols/") and rel.endswith(".kicad_sym"):
        return "symbol_lib"
    if ".pretty/" in rel and rel.endswith(".kicad_mod"):
        return "footprint"
    if rel.startswith("3DModels/"):
        return "model"
    return "doc"


def _custom_relative(path: Path, custom_real: Path, display: str) -> tuple[str | None, Issue | None]:
    """(rel, None) under custom_real's on-disk spelling, or (None, Issue) when path escapes it."""
    resolved = path.resolve()
    if not resolved.is_relative_to(custom_real):
        return None, Issue(Severity.ERROR, "commit.outside_custom", f"{display} is outside Custom; it is not committed")
    return resolved.relative_to(custom_real).as_posix(), None


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def build_migration_commit_plan(
    result: MigrationResult, plan: MigrationPlan, *, today: str | None = None
) -> CommitPlan:
    """The migration's written and deleted files as one CommitPlan, never a .bak (P-03)."""
    repo_root = plan.layout.repo_root
    custom_dir = plan.layout.custom_dir
    custom_real = custom_dir.resolve()
    bak_files = set(plan.bak_files)

    files: list[CommitFile] = []
    issues: list[Issue] = []
    for op in plan.ops:
        if op.kind == "write":
            rel, problem = _custom_relative(op.path, custom_real, op.rel)
            if problem is not None:
                issues.append(problem)
                continue
            expected = result.sha256.get(op.rel, "")
            files.append(CommitFile(rel, op.rel, op.path, _kind_of(rel), expected, op.base_sha256))
        elif op.kind == "delete":
            if op.rel in bak_files:
                continue
            rel, problem = _custom_relative(op.path, custom_real, op.rel)
            if problem is not None:
                issues.append(problem)
                continue
            files.append(CommitFile(rel, op.rel, op.path, _kind_of(rel), "", op.base_sha256, deleted=True))

    files.sort(key=lambda f: (f.display.casefold(), f.display))
    stamp = today if today is not None else date.today().isoformat()

    return CommitPlan(
        repo_root=repo_root,
        custom_dir=custom_dir,
        custom_rel=_repo_relative(custom_dir, repo_root),
        files=tuple(files),
        library="Atomic_ libraries",
        new_library=False,
        symbol="",
        footprint=None,
        model=None,
        vendor=MIGRATION_VENDOR,
        package=None,
        date=stamp,
        overwrite=False,
        backup_dir=result.backup_dir,
        issues=tuple(issues),
        message=migration_message(plan, today),
    )
