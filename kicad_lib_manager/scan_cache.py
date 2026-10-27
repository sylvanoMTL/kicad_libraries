"""The saved scan: reuse the last ScanResult at startup when no library file changed (O-01 to O-06).

Qt-free and stdlib only. The saved scan is plain JSON (never pickle) in a folder beside the app's
settings, written atomically, and untrusted when read back: any wrong type, missing key or odd value
gives a plain note and a full scan. Freshness is a cheap stat walk (mtime and size, no file is
parsed) plus the Custom git HEAD, the KiCad footprint folder and a hash of the app's own code.
"""

import functools
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import fsutil
from .library_scanner import SKIP_DIRS, find_kicad_footprint_dir
from .models import (
    STATUS_CHANGED,
    STATUS_NEW,
    ChangedFootprint,
    Finding,
    FixSpec,
    FootprintLibrary,
    FootprintRef,
    Issue,
    ScanResult,
    Severity,
    SymbolEntry,
    SymbolLibrary,
    Violation,
)

FORMAT = 1
MAX_CACHE_BYTES = 64 * 1024 * 1024
KIND_SYMBOL = "symbol"
KIND_FOOTPRINT = "footprint"

_CUSTOM_MODELS_PREFIX = "Custom/3DModels/"
_CUSTOM_PREFIX = "Custom/"
_STATUSES = (None, STATUS_NEW, STATUS_CHANGED)
_FALLBACK = "scanning the whole repository."


def _info(code: str, text: str) -> Issue:
    return Issue(Severity.INFO, code, text)


# ── Fingerprint ──────────────────────────────────────────────────────

def _mtime(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _walk(start: str, rel_dir: str, *, skip_top: bool) -> tuple[dict[str, list[int]], list[str], bool]:
    """Stat the files and folders the scan reads below start; rel_dir is start's repo-relative prefix.

    Returns (files, folders, complete). Directory symlinks are listed but not followed, like the scan.
    """
    files: dict[str, list[int]] = {}
    folders: list[str] = []
    complete = True
    stack = [(start, rel_dir)]
    while stack:
        directory, prefix = stack.pop()
        try:
            iterator = os.scandir(directory)
        except OSError:
            complete = False
            continue
        with iterator:
            for entry in iterator:
                name = entry.name
                rel = prefix + name
                try:
                    is_dir = entry.is_dir()
                    is_link = entry.is_symlink()
                except OSError:
                    complete = False
                    continue
                if is_dir:
                    if skip_top and not prefix and name in SKIP_DIRS:
                        continue
                    if name.lower().endswith(".pretty"):
                        folders.append(rel)
                    if not is_link:
                        stack.append((entry.path, rel + "/"))
                    continue
                if not (
                    name.lower().endswith((".kicad_sym", ".kicad_mod"))
                    or rel.startswith(_CUSTOM_MODELS_PREFIX)
                    or (name == ".gitignore" and rel.startswith(_CUSTOM_PREFIX))
                ):
                    continue
                try:
                    info = entry.stat()
                except OSError:
                    complete = False
                    continue
                files[rel] = [info.st_mtime_ns, info.st_size]
    return files, sorted(folders), complete


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _custom_git_state(custom_dir: Path) -> str | None:
    """The Custom HEAD and the commit it names, read from the git files with no subprocess.

    "none" when Custom is not a git checkout; None when the state cannot be read.
    """
    dot_git = custom_dir / ".git"
    try:
        if not dot_git.exists():
            return "none"
        if dot_git.is_dir():
            git_dir = dot_git
        else:
            line = _read_text(dot_git)
            if not line.startswith("gitdir:"):
                return None
            git_dir = custom_dir / line[len("gitdir:"):].strip()
        head = _read_text(git_dir / "HEAD")
        if not head.startswith("ref:"):
            return head
        ref = head[len("ref:"):].strip()
        if not ref.startswith("refs/") or ".." in ref.split("/"):
            return None
        common = git_dir
        pointer = git_dir / "commondir"
        if pointer.is_file():
            common = git_dir / _read_text(pointer)
        value = None
        for base in (git_dir, common):
            loose = base / ref
            if loose.is_file():
                value = _read_text(loose)
                break
        if value is None:
            for base in (common, git_dir):
                packed = base / "packed-refs"
                if not packed.is_file():
                    continue
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line[:1] not in ("#", "^") and line.endswith(" " + ref):
                        value = line.split(" ", 1)[0]
                        break
                if value is not None:
                    break
        return f"{head}|{value if value is not None else ''}"
    except (OSError, UnicodeDecodeError):
        return None


def _kicad_part(kicad_fp_dir: Path | None) -> list:
    """The folder the scan would use for KiCad's footprints, with its own and its 3dmodels sibling's mtime."""
    folder = kicad_fp_dir if kicad_fp_dir is not None else find_kicad_footprint_dir()
    if folder is None:
        return ["", None, None]
    return [str(folder), _mtime(folder), _mtime(folder.parent / "3dmodels")]


def fingerprint(repo_root: Path, kicad_fp_dir: Path | None) -> dict:
    """Everything the scan reads, as JSON types; not complete when any file could not be listed."""
    files, folders, complete = _walk(str(repo_root), "", skip_top=True)
    custom_git = _custom_git_state(Path(repo_root) / "Custom")
    return {
        "files": files,
        "folders": folders,
        "custom_git": custom_git,
        "kicad": _kicad_part(kicad_fp_dir),
        "complete": complete and custom_git is not None,
    }


def library_entries(repo_root: Path, kind: str, rel_path: str) -> dict:
    """The fingerprint keys of one library: its symbol file, or its .pretty folder and the files in it."""
    target = Path(repo_root) / rel_path
    if kind == KIND_SYMBOL:
        try:
            info = target.stat()
        except OSError:
            return {"files": {}, "folders": [], "complete": False}
        return {"files": {rel_path: [info.st_mtime_ns, info.st_size]}, "folders": [], "complete": True}
    files, folders, complete = _walk(str(target), rel_path + "/", skip_top=False)
    return {"files": files, "folders": sorted({rel_path, *folders}), "complete": complete}


@functools.lru_cache(maxsize=None)
def _code_signature() -> str:
    """Hash of the app's own .py files, so saved verdicts never outlive a rule change; "" when unreadable."""
    package = Path(__file__).parent
    digest = hashlib.sha256()
    try:
        names = sorted(
            p.relative_to(package).as_posix()
            for p in package.rglob("*.py")
            if "__pycache__" not in p.parts
        )
        for name in names:
            digest.update(name.encode("utf-8") + b"\0")
            digest.update((package / name).read_bytes() + b"\0")
    except OSError:
        return ""
    return digest.hexdigest()


# ── Encoding ─────────────────────────────────────────────────────────

def _text(value) -> str:
    if not isinstance(value, str):
        raise TypeError("expected text")
    return value


def _opt_text(value) -> str | None:
    return None if value is None else _text(value)


def _flag(value) -> bool:
    if not isinstance(value, bool):
        raise TypeError("expected true or false")
    return value


def _list(value) -> list:
    if not isinstance(value, list):
        raise TypeError("expected a list")
    return value


def _dict(value) -> dict:
    if not isinstance(value, dict):
        raise TypeError("expected an object")
    return value


def _status(value) -> str | None:
    if value not in _STATUSES:
        raise ValueError("unknown status")
    return value


def _enc_fix(fix: FixSpec | None) -> dict | None:
    if fix is None:
        return None
    return {"kind": fix.kind, "rel_path": fix.rel_path, "symbol": fix.symbol,
            "label": fix.label, "params": dict(fix.params)}


def _dec_fix(data) -> FixSpec | None:
    if data is None:
        return None
    data = _dict(data)
    params = _dict(data["params"])
    return FixSpec(
        kind=_text(data["kind"]), rel_path=_text(data["rel_path"]), symbol=_text(data["symbol"]),
        label=_text(data["label"]),
        params={_text(k): _text(v) for k, v in params.items()},
    )


def _enc_violation(v: Violation) -> dict:
    return {"rule": v.rule, "text": v.text, "fixes": [_enc_fix(f) for f in v.fixes],
            "fill": _enc_fix(v.fill), "choices": list(v.choices)}


def _dec_violation(data) -> Violation:
    data = _dict(data)
    return Violation(
        rule=_text(data["rule"]), text=_text(data["text"]),
        fixes=tuple(_dec_fix(f) for f in _list(data["fixes"])),
        fill=_dec_fix(data["fill"]),
        choices=tuple(_text(c) for c in _list(data["choices"])),
    )


def _enc_finding(f: Finding) -> dict:
    return {"kind": f.kind, "text": f.text, "fix": _enc_fix(f.fix)}


def _dec_finding(data) -> Finding:
    data = _dict(data)
    return Finding(kind=_text(data["kind"]), text=_text(data["text"]), fix=_dec_fix(data["fix"]))


def _enc_entry(e: SymbolEntry) -> dict:
    return {"name": e.name, "extends": e.extends, "status": e.status,
            "violations": [_enc_violation(v) for v in e.violations],
            "findings": [_enc_finding(f) for f in e.findings]}


def _dec_entry(data) -> SymbolEntry:
    data = _dict(data)
    return SymbolEntry(
        name=_text(data["name"]), extends=_opt_text(data["extends"]), status=_status(data["status"]),
        violations=[_dec_violation(v) for v in _list(data["violations"])],
        findings=[_dec_finding(f) for f in _list(data["findings"])],
    )


def _enc_symbol_lib(lib: SymbolLibrary) -> dict:
    return {
        "nickname": lib.nickname, "rel_path": lib.rel_path, "source": lib.source,
        "refs": [[r.library_name, r.footprint_name, r.found_in_repo] for r in lib.footprint_refs],
        "peers": list(lib.collision_peers), "atomic": lib.atomic,
        "symbols": [_enc_entry(e) for e in lib.symbols], "check_problem": lib.check_problem,
    }


def _dec_ref(data) -> FootprintRef:
    data = _list(data)
    if len(data) != 3:
        raise ValueError("a footprint link has three parts")
    return FootprintRef(_text(data[0]), _text(data[1]), _flag(data[2]))


def _dec_symbol_lib(data) -> SymbolLibrary:
    data = _dict(data)
    return SymbolLibrary(
        nickname=_text(data["nickname"]), rel_path=_text(data["rel_path"]), source=_text(data["source"]),
        footprint_refs=[_dec_ref(r) for r in _list(data["refs"])],
        selected=False,
        collision_peers=[_text(p) for p in _list(data["peers"])],
        atomic=_flag(data["atomic"]),
        symbols=[_dec_entry(e) for e in _list(data["symbols"])],
        check_problem=_opt_text(data["check_problem"]),
    )


def _enc_footprint_lib(lib: FootprintLibrary) -> dict:
    return {
        "nickname": lib.nickname, "rel_path": lib.rel_path, "source": lib.source,
        "peers": list(lib.collision_peers),
        "changed": [[c.name, c.status] for c in lib.changed],
    }


def _dec_changed(data) -> ChangedFootprint:
    data = _list(data)
    if len(data) != 2 or data[1] not in (STATUS_NEW, STATUS_CHANGED):
        raise ValueError("a changed footprint has a name and a status")
    return ChangedFootprint(_text(data[0]), data[1])


def _dec_footprint_lib(data) -> FootprintLibrary:
    data = _dict(data)
    return FootprintLibrary(
        nickname=_text(data["nickname"]), rel_path=_text(data["rel_path"]), source=_text(data["source"]),
        selected=False,
        collision_peers=[_text(p) for p in _list(data["peers"])],
        changed=[_dec_changed(c) for c in _list(data["changed"])],
    )


def _enc_issue(issue: Issue) -> list:
    return [issue.severity.value, issue.code, issue.text]


def _dec_issue(data) -> Issue:
    data = _list(data)
    if len(data) != 3:
        raise ValueError("an issue has three parts")
    return Issue(Severity(_text(data[0])), _text(data[1]), _text(data[2]))


def encode_result(result: ScanResult) -> dict:
    """JSON types only; the selection is never saved, the GUI derives it again."""
    return {
        "symbol_libs": [_enc_symbol_lib(lib) for lib in result.symbol_libs],
        "footprint_libs": [_enc_footprint_lib(lib) for lib in result.footprint_libs],
        "issues": [_enc_issue(i) for i in result.issues],
    }


def decode_result(data) -> ScanResult:
    """Strict inverse of encode_result; raises ValueError, TypeError or KeyError on anything unexpected."""
    data = _dict(data)
    return ScanResult(
        symbol_libs=[_dec_symbol_lib(lib) for lib in _list(data["symbol_libs"])],
        footprint_libs=[_dec_footprint_lib(lib) for lib in _list(data["footprint_libs"])],
        issues=[_dec_issue(i) for i in _list(data["issues"])],
    )


# ── Saving and loading ───────────────────────────────────────────────

def _repo_key(repo_root: Path) -> str:
    return os.path.normcase(str(Path(repo_root).resolve()))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save(
    cache_file: Path,
    repo_root: Path,
    kicad_fp_dir: Path | None,
    fp: dict | None,
    result: ScanResult,
    *,
    saved_at: str | None = None,
) -> Issue | None:
    """Write the saved scan atomically; a failure is one WARNING and never raises.

    fp is the fingerprint taken before the scan read any file. kicad_fp_dir is accepted so the
    call matches load_fresh; the folder it names is already part of fp.
    """
    def failed(reason: str) -> Issue:
        return Issue(Severity.WARNING, "cache.save_failed",
                     f"Could not save this scan for the next start: {reason}")

    if fp is None:
        return failed("the library files could not be listed")
    try:
        payload = {
            "format": FORMAT,
            "code": _code_signature(),
            "repo_root": _repo_key(repo_root),
            "saved_at": saved_at or _now(),
            "fingerprint": fp,
            "result": encode_result(result),
        }
        text = json.dumps(payload, separators=(",", ":"))
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
    except (OSError, TypeError, ValueError) as e:
        return failed(getattr(e, "strerror", None) or str(e))
    failure = fsutil.atomic_write_text(Path(cache_file), text)
    if failure is not None:
        return failed(failure.text)
    return None


@dataclass
class CacheCheck:
    """The outcome of load_fresh: the reusable result or None, the one note to log, the current fingerprint."""
    result: ScanResult | None
    note: Issue
    fingerprint: dict | None = None


def _read_payload(cache_file: Path) -> dict | Issue:
    """The parsed saved scan, or the note saying why it cannot be used."""
    unreadable = _info("cache.unreadable", f"The saved scan could not be read; {_FALLBACK}")
    try:
        size = Path(cache_file).stat().st_size
    except FileNotFoundError:
        return _info("cache.missing", f"No saved scan yet; {_FALLBACK}")
    except OSError:
        return unreadable
    if size > MAX_CACHE_BYTES:
        return unreadable
    try:
        payload = json.loads(Path(cache_file).read_text(encoding="utf-8"))
        fp = payload["fingerprint"]
        if not (
            isinstance(payload["format"], int) and isinstance(payload["code"], str)
            and isinstance(payload["repo_root"], str) and isinstance(payload["result"], dict)
            and isinstance(fp["files"], dict) and isinstance(fp["folders"], list)
            and isinstance(fp["kicad"], list) and len(fp["kicad"]) == 3
            and isinstance(fp["complete"], bool)
            and (fp["custom_git"] is None or isinstance(fp["custom_git"], str))
        ):
            return unreadable
        datetime.fromisoformat(_text(payload["saved_at"]))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return unreadable
    return payload


def load_fresh(cache_file: Path, repo_root: Path, kicad_fp_dir: Path | None) -> CacheCheck:
    """Return the saved result when nothing it was built from changed, else None and the reason (O-04)."""
    payload = _read_payload(cache_file)
    if isinstance(payload, Issue):
        return CacheCheck(None, payload)
    other_version = _info(
        "cache.other_version",
        f"The saved scan was made by a different version of this app; {_FALLBACK}",
    )
    code = _code_signature()
    if payload["format"] != FORMAT or not code or payload["code"] != code:
        return CacheCheck(None, other_version)
    if payload["repo_root"] != _repo_key(repo_root):
        return CacheCheck(None, _info(
            "cache.other_copy", f"The saved scan belongs to another copy of the repository; {_FALLBACK}"
        ))

    saved = payload["fingerprint"]
    current = fingerprint(repo_root, kicad_fp_dir)
    if saved["complete"] is not True or current["complete"] is not True:
        return CacheCheck(None, _info(
            "cache.incomplete", f"Could not check every library file for changes; {_FALLBACK}"
        ), current)
    if saved["kicad"] != current["kicad"]:
        return CacheCheck(None, _info(
            "cache.kicad_changed", f"The KiCad footprint folder changed since the saved scan; {_FALLBACK}"
        ), current)
    if saved["custom_git"] != current["custom_git"]:
        return CacheCheck(None, _info(
            "cache.custom_commit",
            f"The Custom library was committed or switched to another version since the saved scan; {_FALLBACK}",
        ), current)
    saved_files, current_files = saved["files"], current["files"]
    changed = sum(1 for key in saved_files.keys() | current_files.keys()
                  if saved_files.get(key) != current_files.get(key))
    changed += len(set(saved["folders"]) ^ set(current["folders"]))
    if changed:
        noun = "1 library file changed" if changed == 1 else f"{changed} library files changed"
        return CacheCheck(None, _info("cache.stale", f"{noun} since the saved scan; {_FALLBACK}"), current)

    unreadable = _info("cache.unreadable", f"The saved scan could not be read; {_FALLBACK}")
    try:
        result = decode_result(payload["result"])
    except (ValueError, TypeError, KeyError, AttributeError):
        return CacheCheck(None, unreadable, current)
    seen_folders = set(current["folders"])
    known = set(current_files) | seen_folders
    if (
        any(lib.rel_path not in current_files for lib in result.symbol_libs)
        or any(lib.rel_path not in seen_folders for lib in result.footprint_libs)
        or any(peer not in known
               for lib in (*result.symbol_libs, *result.footprint_libs) for peer in lib.collision_peers)
    ):
        return CacheCheck(None, unreadable, current)
    when = datetime.fromisoformat(payload["saved_at"]).strftime("%Y-%m-%d %H:%M")
    return CacheCheck(result, _info(
        "cache.reused",
        f"Showing the saved scan from {when}: no library file changed since then. "
        "Use Rescan for a full scan.",
    ), current)


def update_library(
    cache_file: Path,
    repo_root: Path,
    kicad_fp_dir: Path | None,
    result: ScanResult,
    kind: str,
    rel_path: str,
    entries: dict | None,
) -> Issue | None:
    """Store result in the saved scan and refresh only this library's keys of its fingerprint.

    Every other key, the Custom git part and the KiCad part stay as saved, so any other change
    still forces a full scan at the next start.
    """
    not_updated = _info(
        "cache.not_updated",
        "The saved scan was not updated, so the next start scans the whole repository.",
    )
    payload = _read_payload(cache_file)
    code = _code_signature()
    if (
        isinstance(payload, Issue) or entries is None or entries.get("complete") is not True
        or payload["format"] != FORMAT or not code or payload["code"] != code
        or payload["repo_root"] != _repo_key(repo_root)
        or payload["fingerprint"]["complete"] is not True
        or payload["fingerprint"]["kicad"][0] != _kicad_part(kicad_fp_dir)[0]
    ):
        return not_updated
    fp = payload["fingerprint"]
    files = fp["files"]
    folders = set(fp["folders"])
    if kind == KIND_SYMBOL:
        files.pop(rel_path, None)
    else:
        prefix = rel_path + "/"
        for key in [k for k in files if k.startswith(prefix)]:
            del files[key]
        folders = {f for f in folders if f != rel_path and not f.startswith(prefix)}
    files.update(entries["files"])
    folders.update(entries["folders"])
    fp["folders"] = sorted(folders)
    return save(cache_file, repo_root, kicad_fp_dir, fp, result)
