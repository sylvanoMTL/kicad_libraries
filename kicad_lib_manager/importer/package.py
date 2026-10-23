"""Open a vendor package (zip or folder) for intake; staged copies live in a temp folder outside the repo."""

import hashlib
import os
import stat
import tempfile
import zipfile
import zlib
from collections import deque
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ..models import Issue, Severity

MAX_MEMBERS = 1000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024
MAX_RATIO = 200
RATIO_MIN_SIZE = 1024 * 1024
# Most parser nodes one symbol or footprint file may produce (CR-01)
MAX_KICAD_TEXT_NODES = 1_000_000
# Most bytes of one symbol or footprint file handed to the parser, apart from the model cap above (CR-01)
MAX_KICAD_TEXT_BYTES = 8 * 1024 * 1024
MAX_FOLDER_DEPTH = 8
# D-13: small non-staged text files read in memory so a vendor adapter can score them; never written to disk.
# Real markers are 194 to 445 bytes. A larger file only loses its detection points (an INFO note, not a refusal).
MAX_MARKER_BYTES = 64 * 1024
MAX_MARKERS = 16
MARKER_NAMES = frozenset({"part_info.txt", "license.txt", "how-to-import.htm", "how-to-import.html"})
STAGING_PREFIX = "kicad_import_"
STAGE_KINDS = {
    ".kicad_sym": "symbol",
    ".kicad_mod": "footprint",
    ".step": "model",
    ".stp": "model",
    ".wrl": "model",
}
LEGACY_EXTENSIONS = (".lib", ".dcm", ".mod")
# open_model_source stages only these kinds of file (a separately downloaded 3D model, G-07-2)
MODEL_SOURCE_KINDS = frozenset({"model"})

_COPY_CHUNK = 65536
# The only caller is open_model_source; tests patch this name, never the os module, so a stub reaches nothing else
_lstat = os.lstat
_STAGED_PREFIX = {"symbol": "sym", "footprint": "fp", "model": "model"}
_IGNORED_LISTED = 20
_WINDOWS_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_SHOWN_MAX = 200

try:  # lzma is optional in some Linux builds; zipfile then raises RuntimeError, which is already caught
    import lzma

    _LZMA_ERRORS: tuple[type[Exception], ...] = (lzma.LZMAError,)
except ImportError:
    _LZMA_ERRORS = ()

try:  # Zstandard members are readable from Python 3.14; a damaged one raises ZstdError, which is not an OSError
    from compression.zstd import ZstdError

    _ZSTD_ERRORS: tuple[type[Exception], ...] = (ZstdError,)
except ImportError:
    _ZSTD_ERRORS = ()

# The errors a damaged member raises while it is read and decompressed (CR-02); returned as ERROR intake.corrupt, never raised
_READ_ERRORS = (
    zipfile.BadZipFile,
    RuntimeError,
    NotImplementedError,
    zlib.error,
    EOFError,
    OSError,
    *_LZMA_ERRORS,
    *_ZSTD_ERRORS,
)


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
    kind: str  # "zip" | "folder" | "file" (one bare 3D model read in place)
    names: list[str] = field(default_factory=list)
    files: list[PackageFile] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    legacy: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    # Member name to its bounded bytes (MAX_MARKER_BYTES, MAX_MARKERS); held in memory, never written to disk (D-13)
    markers: dict[str, bytes] = field(default_factory=dict)
    staging_dir: Path | None = None
    _tmp: tempfile.TemporaryDirectory | None = field(default=None, repr=False)

    def marker_text(self, basename: str) -> str | None:
        """The shallowest marker whose file name is basename (case-insensitive), decoded as UTF-8; None when absent."""
        want = basename.casefold()
        matches = [k for k in self.markers if k.replace("\\", "/").rsplit("/", 1)[-1].casefold() == want]
        if not matches:
            return None
        key = min(matches, key=lambda k: (k.count("/"), k))
        return self.markers[key].decode("utf-8-sig", errors="replace")

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


@dataclass
class _Budget:
    """Running totals shared by the outer zip and any nested zip (D-08)."""

    members: int = 0
    declared: int = 0
    actual: int = 0


def _shown(name: str) -> str:
    """repr(name) for an Issue text, cut so a hostile 500-character name stays readable."""
    text = repr(name)
    return text if len(text) <= _SHOWN_MAX else text[:_SHOWN_MAX] + "..."


def _hostile_reason(name: str, info: zipfile.ZipInfo) -> str | None:
    """Why a member must refuse the whole package, or None when the member is acceptable (D-05, D-19, A8)."""
    n = name.replace("\\", "/")
    if not n:
        return "an empty name"
    if n.startswith("/"):
        return "an absolute or UNC path"
    if len(n) >= 2 and n[1] == ":" and n[0].isalpha():
        return "a drive-letter path"
    if any(ord(c) < 32 or ord(c) == 127 for c in n):
        return "a name with a control character"
    if ":" in n:
        return "a name containing ':' (drive or alternate data stream)"
    for segment in n.split("/"):
        if segment.strip(" .") == "" and segment.count(".") >= 2:
            return "a path traversal ('..')"
    mode = info.external_attr >> 16
    if mode and stat.S_ISLNK(mode):
        return "a symbolic link"
    if info.external_attr & _WINDOWS_REPARSE:
        return "a Windows reparse point"
    return None


def _ratio_exceeded(file_size: int, compress_size: int) -> bool:
    """True for a member above RATIO_MIN_SIZE that expands past MAX_RATIO:1; integer maths, safe for size 0."""
    return file_size > RATIO_MIN_SIZE and file_size > MAX_RATIO * max(compress_size, 1)


def _prescan(infos: list[zipfile.ZipInfo], label: str, budget: _Budget, prefix: str = "") -> Issue | None:
    """Return the first reason to refuse the whole archive, judged on headers alone, before any byte is read.

    Caps are read from the module globals at call time and cover every member, ignored ones included
    (D-06, D-07). prefix is the nested zip's member name, so an inner member is shown as 'inner.zip/x'.
    """
    seen: set[str] = set()
    for info in infos:
        name = info.filename
        shown = _shown(prefix + name)
        reason = _hostile_reason(name, info)
        if reason is not None:
            return Issue(Severity.ERROR, "intake.hostile_member", f"Refused {label}: member {shown} is {reason}")
        if not info.is_dir():
            key = name.replace("\\", "/").casefold()
            if key in seen:
                return Issue(
                    Severity.ERROR,
                    "intake.duplicate_member",
                    f"Refused {label}: member {shown} appears more than once (names compared ignoring case)",
                )
            seen.add(key)
        if info.flag_bits & 0x1:
            return Issue(Severity.ERROR, "intake.encrypted", f"Refused {label}: member {shown} is encrypted")
        budget.members += 1
        if budget.members > MAX_MEMBERS:
            return Issue(Severity.ERROR, "intake.too_many_members", f"Refused {label}: more than {MAX_MEMBERS} members")
        if info.is_dir():
            continue
        if info.file_size > MAX_MEMBER_BYTES:
            return Issue(
                Severity.ERROR,
                "intake.too_large",
                f"Refused {label}: member {shown} declares {info.file_size} bytes, over the {MAX_MEMBER_BYTES} byte limit",
            )
        budget.declared += info.file_size
        if budget.declared > MAX_TOTAL_BYTES:
            return Issue(
                Severity.ERROR,
                "intake.too_large",
                f"Refused {label}: members declare {budget.declared} bytes in total, over the {MAX_TOTAL_BYTES} byte limit",
            )
        if _ratio_exceeded(info.file_size, info.compress_size):
            ratio = info.file_size // max(info.compress_size, 1)
            return Issue(
                Severity.ERROR,
                "intake.high_ratio",
                f"Refused {label}: member {shown} expands about {ratio}:1, over the {MAX_RATIO}:1 limit",
            )
    return None


def _is_junk_name(name: str) -> bool:
    """True for macOS resource-fork debris: anything under __MACOSX/ or a last segment starting with '._'."""
    parts = name.replace("\\", "/").split("/")
    return any(p.casefold() == "__macosx" for p in parts) or parts[-1].startswith("._")


def _is_marker(name: str) -> bool:
    """True for a non-junk member whose last path segment is one of MARKER_NAMES (case-insensitive)."""
    if _is_junk_name(name):
        return False
    return name.replace("\\", "/").rsplit("/", 1)[-1].casefold() in MARKER_NAMES


def _keep_marker(package: Package, name: str, label: str, data: bytes) -> bool:
    """Store data as a marker unless it is over MAX_MARKER_BYTES; True when kept."""
    if len(data) > MAX_MARKER_BYTES:
        package.issues.append(
            Issue(Severity.INFO, "intake.marker_skipped", f"Skipped {name} of {label}: larger than {MAX_MARKER_BYTES} bytes")
        )
        return False
    package.markers[name] = data
    return True


def _refuse(package: Package, issue: Issue) -> Package:
    package.issues.append(issue)
    package.close()
    package.files.clear()
    package.markers.clear()
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


def _ignored_issue(label: str, ignored: list[str]) -> Issue | None:
    """The one INFO Issue listing members that are not imported, or None when there are none."""
    if not ignored:
        return None
    shown = ignored[:_IGNORED_LISTED]
    listed = ", ".join(shown)
    extra = len(ignored) - len(shown)
    if extra > 0:
        listed += f", and {extra} more"
    return Issue(Severity.INFO, "intake.ignored_members", f"Not imported from {label}: {listed}")


def open_package(path: Path, repo_root: Path, progress: Callable | None = None) -> Package:
    """Open a vendor zip or a folder of loose files for intake; expected failures come back as ERROR Issues, never raised."""
    path = Path(path)
    if not path.exists():
        package = Package(path, "zip")
        package.issues.append(
            Issue(Severity.ERROR, "intake.not_found", f"Could not open {path}: no such file or folder")
        )
        return package
    if path.is_dir():
        return _open_folder(path, repo_root, progress)
    if path.is_file() and path.suffix.casefold() == ".zip":
        return _open_zip(path, repo_root, progress)
    package = Package(path, "zip")
    package.issues.append(
        Issue(Severity.ERROR, "intake.unsupported", f"Could not open {path.name}: not a .zip file or a folder")
    )
    return package


def open_model_source(path: Path, repo_root: Path, progress: Callable | None = None) -> Package:
    """Open a second intake source that holds 3D models only: a .zip, or one bare .step/.stp/.wrl.

    A zip stages only its model members under the same hostile-zip refusals and caps as open_package
    (D-05, D-06, D-07, D-08, D-19); every other member is listed in one "Not imported from ..." note and
    never written. A zip without a model is refused with intake.no_model_in_source. Expected failures come
    back as ERROR Issues on the returned Package and are never raised.
    """
    path = Path(path)
    try:
        st = _lstat(path)
    except FileNotFoundError:
        package = Package(path, "file")
        package.issues.append(
            Issue(Severity.ERROR, "intake.not_found", f"Could not open {path}: no such file or folder")
        )
        return package
    except OSError as e:
        package = Package(path, "file")
        package.issues.append(
            Issue(Severity.ERROR, "intake.unreadable_source", f"Could not read {path.name}: {e.strerror or e}")
        )
        return package
    if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & _WINDOWS_REPARSE:
        package = Package(path, "file")
        package.issues.append(
            Issue(Severity.ERROR, "intake.link_refused", f"Refused {path.name}: it is a link or junction; pick the file itself")
        )
        return package
    suffix = path.suffix.casefold()
    if stat.S_ISREG(st.st_mode) and STAGE_KINDS.get(suffix) == "model":
        return _open_model_file(path, st)
    if stat.S_ISREG(st.st_mode) and suffix == ".zip":
        package = _open_zip(path, repo_root, progress, kinds=MODEL_SOURCE_KINDS)
        if not package.refused and not any(f.kind == "model" for f in package.files):
            return _refuse(
                package,
                Issue(Severity.ERROR, "intake.no_model_in_source", f"{path.name} holds no 3D model (.step, .stp or .wrl)"),
            )
        return package
    package = Package(path, "file")
    package.issues.append(
        Issue(
            Severity.ERROR,
            "intake.unsupported",
            f"Could not open {path.name}: pick a .step, .stp or .wrl file, or a .zip holding one",
        )
    )
    return package


def _open_model_file(path: Path, st) -> Package:
    """Read one bare 3D model in place, read-only: no copy, no staging, no write (G-07-2).

    st is the no-follow lstat result of path. The opened handle must be the same regular file, and the
    real bytes are counted against MAX_MEMBER_BYTES, read from the module global at call time.
    """
    package = Package(path, "file")

    def refuse(code: str, text: str) -> Package:
        package.issues.append(Issue(Severity.ERROR, code, text))
        return package

    if st.st_size > MAX_MEMBER_BYTES:
        return refuse(
            "intake.too_large",
            f"Refused {path.name}: {st.st_size} bytes, over the {MAX_MEMBER_BYTES} byte limit",
        )
    try:
        with open(path, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino) or not stat.S_ISREG(opened.st_mode):
                return refuse("intake.link_refused", f"Refused {path.name}: the file changed while it was opened")
            sha = hashlib.sha256()
            total = 0
            while chunk := handle.read(_COPY_CHUNK):
                total += len(chunk)
                if total > MAX_MEMBER_BYTES:
                    return refuse("intake.too_large", f"Refused {path.name}: it is larger than it was listed")
                sha.update(chunk)
    except OSError as e:
        return refuse("intake.unreadable_source", f"Could not read {path.name}: {e.strerror or e}")
    package.names.append(path.name)
    package.files.append(PackageFile(path.name, path, "model", total, sha.hexdigest(), False))
    return package


def _classify(name: str) -> tuple[str, str]:
    """Return (class, lowercase extension) for a member name: stage, nested, legacy or ignored."""
    last = PurePosixPath(name).name
    ext = PurePosixPath(last).suffix.casefold()
    if _is_junk_name(name):
        return "ignored", ext
    if ext == ".zip":
        return "nested", ext
    if ext in STAGE_KINDS:
        return "stage", ext
    if ext in LEGACY_EXTENSIONS:
        return "legacy", ext
    return "ignored", ext


def _copy_member(
    zf: zipfile.ZipFile, info: zipfile.ZipInfo, name: str, target: Path, label: str, budget: _Budget, sha=None
) -> tuple[int | None, Issue | None]:
    """Copy one member to target counting real bytes against the remaining budget (D-06).

    Returns (size, None), or (None, refusal Issue). Caps are read from the module globals at call time.
    """
    limit = min(MAX_MEMBER_BYTES, MAX_TOTAL_BYTES - budget.actual)
    try:
        with zf.open(info) as src, open(target, "xb") as dst:
            copied = _copy_capped(src, dst, limit, sha)
    except _READ_ERRORS as e:
        return None, Issue(Severity.ERROR, "intake.corrupt", f"Could not read member {_shown(name)} of {label}: {e}")
    if copied is None:
        return None, Issue(
            Severity.ERROR, "intake.too_large", f"Refused {label}: member {_shown(name)} is larger than it declared"
        )
    budget.actual += copied
    return copied, None


def _narrow(what: str, ext: str, kinds: frozenset[str] | None) -> str:
    """Apply a kinds filter to a member class: other staged kinds and legacy files become 'skipped' (ignored)."""
    if kinds is None:
        return what
    if what == "stage" and STAGE_KINDS[ext] not in kinds:
        return "skipped"
    if what == "legacy":
        return "skipped"
    return what


def _stage_zip(
    zf: zipfile.ZipFile,
    path: Path,
    repo_root: Path,
    progress: Callable | None,
    package: Package,
    *,
    kinds: frozenset[str] | None = None,
) -> Issue | None:
    """Pre-scan, classify and stage an opened zip into package; return the refusal Issue, or None on success.

    kinds None stages every kind (full intake). A set of kinds stages only those; every other staged
    kind and every legacy file is listed as ignored, and no marker is read.
    """
    budget = _Budget()
    refusal = _prescan(zf.infolist(), path.name, budget)
    if refusal is not None:
        return refusal

    # (archive, header, member name shown to callers, lowercase extension)
    staged: list[tuple[zipfile.ZipFile, zipfile.ZipInfo, str, str]] = []
    nested: list[tuple[zipfile.ZipInfo, str]] = []
    # (archive, header, member name) of marker members; read in memory after staging (D-13)
    markers: list[tuple[zipfile.ZipFile, zipfile.ZipInfo, str]] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename.replace("\\", "/")
        package.names.append(name)
        what, ext = _classify(name)
        what = _narrow(what, ext, kinds)
        if what == "stage":
            staged.append((zf, info, name, ext))
        elif what == "nested":
            nested.append((info, name))
        elif what == "legacy":
            package.legacy.append(name)
        else:
            package.ignored.append(name)
            if kinds is None and _is_marker(name):
                markers.append((zf, info, name))

    try:
        tmp = tempfile.TemporaryDirectory(prefix=STAGING_PREFIX, ignore_cleanup_errors=True)
    except OSError as e:
        return Issue(
            Severity.ERROR,
            "intake.staging_failed",
            f"Could not create a temp folder to stage {path.name}: {e.strerror or e}",
        )
    package._tmp = tmp
    try:
        staging = Path(tmp.name).resolve()
    except OSError as e:
        return Issue(
            Severity.ERROR,
            "intake.staging_failed",
            f"Could not resolve the temp folder to stage {path.name}: {e.strerror or e}",
        )
    if staging.is_relative_to(Path(repo_root).resolve()):
        return Issue(
            Severity.ERROR,
            "intake.staging_in_repo",
            f"Could not stage {path.name}: the temp folder {staging} is inside the repository",
        )
    package.staging_dir = staging

    with ExitStack() as stack:
        for j, (info, member) in enumerate(nested):
            label = f"{path.name}/{member}"
            copy = staging / f"nested_{j:03d}.zip"
            _, issue = _copy_member(zf, info, member, copy, path.name, budget)
            if issue is not None:
                return issue
            try:
                inner = stack.enter_context(zipfile.ZipFile(copy))
            except (zipfile.BadZipFile, OSError, EOFError, NotImplementedError, ValueError) as e:
                return Issue(Severity.ERROR, "intake.corrupt", f"Could not read {label}: {e}")
            issue = _prescan(inner.infolist(), label, budget, prefix=f"{member}/")
            if issue is not None:
                return issue
            for inner_info in inner.infolist():
                if inner_info.is_dir():
                    continue
                inner_name = inner_info.filename.replace("\\", "/")
                full = f"{member}/{inner_name}"
                package.names.append(full)
                what, ext = _classify(inner_name)
                what = _narrow(what, ext, kinds)
                if what == "nested":
                    return Issue(
                        Severity.ERROR,
                        "intake.nested_too_deep",
                        f"Refused {path.name}: {full} is a zip inside a nested zip; only one level is opened",
                    )
                if what == "stage":
                    staged.append((inner, inner_info, full, ext))
                elif what == "legacy":
                    package.legacy.append(full)
                else:
                    package.ignored.append(full)
                    if kinds is None and _is_marker(full):
                        markers.append((inner, inner_info, full))

        total = len(staged)
        for i, (source, info, name, ext) in enumerate(staged):
            if progress:
                progress(f"Staging {name}", i, total)
            kind = STAGE_KINDS[ext]
            target = staging / f"{_STAGED_PREFIX[kind]}_{i:03d}{ext}"
            sha = hashlib.sha256()
            copied, issue = _copy_member(source, info, name, target, path.name, budget, sha)
            if issue is not None:
                return issue
            package.files.append(PackageFile(name, target, kind, copied, sha.hexdigest(), True))

        # D-13: marker members already passed _prescan and the unchanged hostile-zip refusals and caps (D-05,
        # D-06, D-19); this adds a smaller per-member cap and relaxes none. Bytes stay in memory, never extracted.
        for source, info, name in markers[:MAX_MARKERS]:
            try:
                with source.open(info) as handle:
                    data = handle.read(MAX_MARKER_BYTES + 1)
            except _READ_ERRORS as e:
                package.issues.append(
                    Issue(Severity.INFO, "intake.marker_skipped", f"Could not read {name} of {path.name}: {e}")
                )
                continue
            if _keep_marker(package, name, path.name, data):
                budget.actual += len(data)

    for j in range(len(nested)):
        try:
            (staging / f"nested_{j:03d}.zip").unlink()
        except OSError:
            pass  # removed with the staging folder anyway
    return None


def _open_zip(
    path: Path, repo_root: Path, progress: Callable | None, *, kinds: frozenset[str] | None = None
) -> Package:
    package = Package(path, "zip")
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError, EOFError, NotImplementedError, ValueError) as e:
        return _refuse(
            package, Issue(Severity.ERROR, "intake.corrupt", f"Could not read {path.name}: {e}")
        )
    with zf:
        issue = _stage_zip(zf, path, repo_root, progress, package, kinds=kinds)
    if issue is not None:
        # Every zip handle is closed by now, so the staging folder can be removed on Windows too.
        return _refuse(package, issue)

    note = _ignored_issue(path.name, package.ignored)
    if note is not None:
        package.issues.append(note)
    return package


def _hash_file(path: Path, limit: int) -> tuple[int, str] | None:
    """Read path (mode "rb" only) counting real bytes; return (size, sha256 hex), or None once more than limit were read."""
    sha = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while chunk := handle.read(_COPY_CHUNK):
            total += len(chunk)
            if total > limit:
                return None
            sha.update(chunk)
    return total, sha.hexdigest()


def _is_link(entry: os.DirEntry) -> bool:
    """True for a symlink or a Windows reparse point (junction); never follows the link."""
    if entry.is_symlink():
        return True
    return bool(getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & _WINDOWS_REPARSE)


def _open_folder(path: Path, repo_root: Path, progress: Callable | None) -> Package:
    """Read a user-picked folder in place and read-only (INTK-01, A9).

    Nothing is staged or written: every PackageFile points into the folder. Links and junctions are
    never followed, folders deeper than MAX_FOLDER_DEPTH are not read, and the zip caps apply.
    Caps are read from the module globals at call time.
    """
    package = Package(path, "folder")
    budget = _Budget()
    queue: deque[tuple[Path, int]] = deque([(path, 0)])
    # (rel, kind, file path, listed size) of whitelisted files, in walk order
    wanted: list[tuple[str, str, Path, int]] = []
    links: list[str] = []
    too_deep: list[str] = []
    marker_files: list[tuple[str, Path]] = []
    while queue:
        folder, depth = queue.popleft()
        try:
            with os.scandir(folder) as it:
                entries = sorted(it, key=lambda e: (e.name.casefold(), e.name))
        except OSError as e:
            rel = folder.relative_to(path).as_posix()
            package.issues.append(
                Issue(Severity.WARNING, "intake.unreadable_folder", f"Could not read folder {rel}: {e.strerror or e}")
            )
            continue
        for entry in entries:
            budget.members += 1
            if budget.members > MAX_MEMBERS:
                return _refuse(
                    package,
                    Issue(Severity.ERROR, "intake.too_many_members", f"Refused {path.name}: more than {MAX_MEMBERS} files and folders"),
                )
            rel = Path(entry.path).relative_to(path).as_posix()
            try:
                if _is_link(entry):
                    links.append(rel)
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
                size = entry.stat(follow_symlinks=False).st_size if is_file else 0
            except OSError as e:
                package.issues.append(
                    Issue(Severity.WARNING, "intake.unreadable_file", f"Could not read {rel}: {e.strerror or e}")
                )
                continue
            if is_dir:
                if depth + 1 <= MAX_FOLDER_DEPTH:
                    queue.append((Path(entry.path), depth + 1))
                else:
                    too_deep.append(rel)
                continue
            if not is_file:
                continue  # a socket, device or other special file
            package.names.append(rel)
            what, ext = _classify(rel)
            if what == "legacy":
                package.legacy.append(rel)
            elif what != "stage":
                package.ignored.append(rel)  # junk, a nested .zip (never opened here) or any other file
                if _is_marker(rel):
                    marker_files.append((rel, Path(entry.path)))
            else:
                if size > MAX_MEMBER_BYTES:
                    return _refuse(
                        package,
                        Issue(
                            Severity.ERROR,
                            "intake.too_large",
                            f"Refused {path.name}: {_shown(rel)} is {size} bytes, over the {MAX_MEMBER_BYTES} byte limit",
                        ),
                    )
                budget.declared += size
                if budget.declared > MAX_TOTAL_BYTES:
                    return _refuse(
                        package,
                        Issue(
                            Severity.ERROR,
                            "intake.too_large",
                            f"Refused {path.name}: files total {budget.declared} bytes, over the {MAX_TOTAL_BYTES} byte limit",
                        ),
                    )
                wanted.append((rel, STAGE_KINDS[ext], Path(entry.path), size))

    total = len(wanted)
    for i, (rel, kind, file_path, _size) in enumerate(wanted):
        if progress:
            progress(f"Reading {rel}", i, total)
        limit = min(MAX_MEMBER_BYTES, MAX_TOTAL_BYTES - budget.actual)
        try:
            counted = _hash_file(file_path, limit)
        except OSError as e:
            package.issues.append(
                Issue(Severity.WARNING, "intake.unreadable_file", f"Could not read {rel}: {e.strerror or e}")
            )
            continue
        if counted is None:
            return _refuse(
                package,
                Issue(Severity.ERROR, "intake.too_large", f"Refused {path.name}: {_shown(rel)} is larger than it was listed"),
            )
        size, digest = counted
        budget.actual += size
        package.files.append(PackageFile(rel, file_path, kind, size, digest, False))

    # D-13: bounded in-memory read of marker files; a failure is an INFO note, never a refusal
    for rel, file_path in marker_files[:MAX_MARKERS]:
        try:
            with open(file_path, "rb") as handle:
                data = handle.read(MAX_MARKER_BYTES + 1)
        except OSError as e:
            package.issues.append(
                Issue(Severity.INFO, "intake.marker_skipped", f"Could not read {rel} of {path.name}: {e.strerror or e}")
            )
            continue
        if _keep_marker(package, rel, path.name, data):
            budget.actual += len(data)

    if links:
        package.issues.append(
            Issue(
                Severity.INFO,
                "intake.link_skipped",
                f"Skipped links and junctions (not followed): {', '.join(links[:_IGNORED_LISTED])}"
                + (f", and {len(links) - _IGNORED_LISTED} more" if len(links) > _IGNORED_LISTED else ""),
            )
        )
    if too_deep:
        package.issues.append(
            Issue(
                Severity.WARNING,
                "intake.depth_limit",
                f"Did not read folders more than {MAX_FOLDER_DEPTH} levels deep: {', '.join(too_deep[:_IGNORED_LISTED])}"
                + (f", and {len(too_deep) - _IGNORED_LISTED} more" if len(too_deep) > _IGNORED_LISTED else ""),
            )
        )
    note = _ignored_issue(path.name, package.ignored)
    if note is not None:
        package.issues.append(note)
    return package
