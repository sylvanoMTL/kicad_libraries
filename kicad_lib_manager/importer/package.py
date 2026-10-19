"""Open a vendor package (zip or folder) for intake; staged copies live in a temp folder outside the repo."""

import hashlib
import tempfile
import zipfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ..models import Issue, Severity

MAX_MEMBERS = 1000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024
MAX_RATIO = 200
RATIO_MIN_SIZE = 1024 * 1024
STAGING_PREFIX = "kicad_import_"
STAGE_KINDS = {
    ".kicad_sym": "symbol",
    ".kicad_mod": "footprint",
    ".step": "model",
    ".stp": "model",
    ".wrl": "model",
}
LEGACY_EXTENSIONS = (".lib", ".dcm", ".mod")

_COPY_CHUNK = 65536
_STAGED_PREFIX = {"symbol": "sym", "footprint": "fp", "model": "model"}
_IGNORED_LISTED = 20


@dataclass(frozen=True)
class PackageFile:
    member: str
    path: Path
    kind: str
    size: int
    sha256: str
    staged: bool


@dataclass(eq=False)
class Package:
    """An opened vendor package.

    Staged files stay valid until close(). Use the Package as a with block, or hold it
    and call close() yourself (idempotent); both lifetimes are part of the contract.
    """

    source: Path
    kind: str  # "zip" | "folder"
    names: list[str] = field(default_factory=list)
    files: list[PackageFile] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    legacy: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    staging_dir: Path | None = None
    _tmp: tempfile.TemporaryDirectory | None = field(default=None, repr=False)

    @property
    def refused(self) -> bool:
        return any(i.severity is Severity.ERROR for i in self.issues)

    def close(self) -> None:
        """Remove the staging folder; safe to call more than once."""
        tmp, self._tmp = self._tmp, None
        self.staging_dir = None
        if tmp is not None:
            tmp.cleanup()

    def __enter__(self) -> "Package":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
        return None


def _refuse(package: Package, issue: Issue) -> Package:
    package.issues.append(issue)
    package.close()
    package.files.clear()
    return package


def _copy_capped(src, dst, limit: int, sha=None) -> int | None:
    """Copy src to dst in chunks; return bytes copied, or None once more than limit bytes were read."""
    total = 0
    while chunk := src.read(_COPY_CHUNK):
        total += len(chunk)
        if total > limit:
            return None
        if sha is not None:
            sha.update(chunk)
        dst.write(chunk)
    return total


def open_package(path: Path, repo_root: Path, progress: Callable | None = None) -> Package:
    """Open a vendor zip for intake; expected failures come back as ERROR Issues, never raised."""
    path = Path(path)
    if not path.exists():
        package = Package(path, "zip")
        package.issues.append(
            Issue(Severity.ERROR, "intake.not_found", f"Could not open {path}: no such file or folder")
        )
        return package
    if path.is_file() and path.suffix.casefold() == ".zip":
        return _open_zip(path, repo_root, progress)
    package = Package(path, "zip")
    package.issues.append(
        Issue(Severity.ERROR, "intake.unsupported", f"Could not open {path.name}: not a .zip file or a folder")
    )
    return package


def _classify(name: str) -> tuple[str, str]:
    """Return (class, lowercase extension) for a member name: stage, legacy or ignored."""
    last = PurePosixPath(name).name
    ext = PurePosixPath(last).suffix.casefold()
    if ext in STAGE_KINDS:
        return "stage", ext
    if ext in LEGACY_EXTENSIONS:
        return "legacy", ext
    return "ignored", ext


def _open_zip(path: Path, repo_root: Path, progress: Callable | None) -> Package:
    package = Package(path, "zip")
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError, EOFError, NotImplementedError, ValueError) as e:
        return _refuse(
            package, Issue(Severity.ERROR, "intake.corrupt", f"Could not read {path.name}: {e}")
        )
    with zf:
        staged_members: list[tuple[zipfile.ZipInfo, str, str]] = []
        try:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                package.names.append(name)
                what, ext = _classify(name)
                if what == "stage":
                    staged_members.append((info, name, ext))
                elif what == "legacy":
                    package.legacy.append(name)
                else:
                    package.ignored.append(name)
        except (zipfile.BadZipFile, OSError, EOFError, NotImplementedError, ValueError) as e:
            return _refuse(
                package, Issue(Severity.ERROR, "intake.corrupt", f"Could not read {path.name}: {e}")
            )

        tmp = tempfile.TemporaryDirectory(prefix=STAGING_PREFIX, ignore_cleanup_errors=True)
        package._tmp = tmp
        staging = Path(tmp.name).resolve()
        if staging.is_relative_to(Path(repo_root).resolve()):
            return _refuse(
                package,
                Issue(
                    Severity.ERROR,
                    "intake.staging_in_repo",
                    f"Could not stage {path.name}: the temp folder {staging} is inside the repository",
                ),
            )
        package.staging_dir = staging

        total_so_far = 0
        total = len(staged_members)
        for i, (info, name, ext) in enumerate(staged_members):
            if progress:
                progress(f"Staging {name}", i, total)
            kind = STAGE_KINDS[ext]
            target = staging / f"{_STAGED_PREFIX[kind]}_{i:03d}{ext}"
            limit = min(MAX_MEMBER_BYTES, MAX_TOTAL_BYTES - total_so_far)
            sha = hashlib.sha256()
            try:
                with zf.open(info) as src, open(target, "xb") as dst:
                    copied = _copy_capped(src, dst, limit, sha)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, EOFError, OSError) as e:
                return _refuse(
                    package,
                    Issue(Severity.ERROR, "intake.corrupt", f"Could not read member {name!r} of {path.name}: {e}"),
                )
            if copied is None:
                return _refuse(
                    package,
                    Issue(
                        Severity.ERROR,
                        "intake.too_large",
                        f"Could not stage member {name!r} of {path.name}: it is larger than the size limit",
                    ),
                )
            total_so_far += copied
            package.files.append(PackageFile(name, target, kind, copied, sha.hexdigest(), True))

    if package.ignored:
        shown = package.ignored[:_IGNORED_LISTED]
        listed = ", ".join(shown)
        extra = len(package.ignored) - len(shown)
        if extra > 0:
            listed += f", and {extra} more"
        package.issues.append(
            Issue(Severity.INFO, "intake.ignored_members", f"Not imported from {path.name}: {listed}")
        )
    return package
