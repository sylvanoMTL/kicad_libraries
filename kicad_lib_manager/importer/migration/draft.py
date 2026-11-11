"""The migration draft: save, restore and changed-since-draft detection, in app data only (D-14).

save_draft/load_draft never touch the repository: the file lives beside settings.ini, at the path
settings.migration_draft_file returns (see RESEARCH P-15). A missing, oversized, malformed,
wrong-format or other-repository draft always means "start without a draft", reported as one INFO
Issue, never an exception and never a partial MigrationChoices (T-13-20). This module is Qt-free
and imports only its ALLOWED set (tests/test_importer_layering.py): it takes the path as an
argument instead of importing settings.
"""

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ... import fsutil
from ...models import Issue, Severity
from ..plan import Resolution
from .inventory import Inventory
from .plan import FOOTPRINT_TARGETS, MigrationChoices, PartChoice, PartKey

DRAFT_FORMAT = 1
MAX_DRAFT_BYTES = 4 * 1024 * 1024

_RESOLUTION_ACTIONS = ("overwrite", "rename", "skip")
# Every PartChoice text field that is None by default; serialized only when the owner set it.
_TEXT_FIELDS = (
    "library",
    "symbol_name",
    "mpn",
    "manufacturer",
    "datasheet",
    "description",
    "keywords",
    "fp_description",
    "fp_tags",
    "official_footprint",
    "footprint_name",
    "model_name",
    "model_source",
)
_MODEL_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class LoadedDraft:
    """A draft successfully read back: the choices it held and the fingerprints they were saved against."""

    choices: MigrationChoices
    fingerprints: Mapping[PartKey, str]
    saved_at: str


def _info(code: str, text: str) -> Issue:
    return Issue(Severity.INFO, code, text)


def _repo_key(repo_root: Path) -> str:
    return os.path.normcase(str(Path(repo_root).resolve()))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _model_hash(models_dir: Path, name: str) -> str:
    """sha256 of models_dir/name, read in 1 MiB chunks; "unreadable" on any failure instead of raising."""
    digest = hashlib.sha256()
    try:
        with open(models_dir / name, "rb") as handle:
            while True:
                chunk = handle.read(_MODEL_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return "unreadable"
    return digest.hexdigest()


def fingerprints(inventory: Inventory) -> dict[PartKey, str]:
    """One sha256 per part: its own block, the footprint it links and that footprint's models (D-14, P-15).

    A part that links no Custom footprint is fingerprinted from its block alone. Intended to run on
    a worker thread in the window: every model file is re-read here, same as the importer's own
    content hashing.
    """
    footprint_by_part: dict[PartKey, object] = {}
    for fp in inventory.footprints:
        for key in fp.linked_by:
            footprint_by_part[key] = fp

    result: dict[PartKey, str] = {}
    for part in inventory.parts:
        digest = hashlib.sha256()
        digest.update(part.block_sha256.encode("ascii"))
        footprint = footprint_by_part.get(part.key)
        if footprint is not None:
            digest.update(footprint.sha256.encode("ascii"))
            for model in footprint.models:
                digest.update(_model_hash(inventory.layout.models_dir, model).encode("utf-8"))
        result[part.key] = digest.hexdigest()
    return result


def changed_parts(loaded: LoadedDraft, current: Mapping[PartKey, str]) -> frozenset[PartKey]:
    """Saved keys whose print differs from current, or that no longer exist at all (D-14, P-15)."""
    return frozenset(key for key, saved in loaded.fingerprints.items() if current.get(key) != saved)


# ── Choice encoding ──────────────────────────────────────────────────

def _encode_choice(choice: PartChoice) -> dict:
    data: dict = {"footprint_target": choice.footprint_target, "derive": choice.derive}
    for name in _TEXT_FIELDS:
        value = getattr(choice, name)
        if value is not None:
            data[name] = value
    return data


def _text(value) -> str:
    if not isinstance(value, str):
        raise TypeError("expected text")
    return value


def _flag(value) -> bool:
    if not isinstance(value, bool):
        raise TypeError("expected true or false")
    return value


def _decode_choice(data) -> PartChoice:
    if not isinstance(data, dict):
        raise TypeError("a part choice must be an object")
    footprint_target = data.get("footprint_target", "shared")
    if footprint_target not in FOOTPRINT_TARGETS:
        raise ValueError("unknown footprint_target")
    derive = _flag(data.get("derive", True))
    fields = {name: _text(data[name]) for name in _TEXT_FIELDS if name in data}
    return PartChoice(footprint_target=footprint_target, derive=derive, **fields)


def _decode_key(raw) -> PartKey:
    if not (isinstance(raw, list) and len(raw) == 2):
        raise ValueError("a part key needs exactly a path and a name")
    rel, name = raw
    return _text(rel), _text(name)


def _decode_part_entry(entry) -> tuple[PartKey, PartChoice | None, str]:
    if not isinstance(entry, dict):
        raise TypeError("a part entry must be an object")
    key = _decode_key(entry["key"])
    print_value = _text(entry.get("print", ""))
    choice_data = entry.get("choice")
    choice = _decode_choice(choice_data) if choice_data is not None else None
    return key, choice, print_value


def _decode_leftover(entry) -> tuple[str, bool]:
    if not (isinstance(entry, list) and len(entry) == 2):
        raise ValueError("a leftover needs exactly a path and a keep flag")
    rel, keep = entry
    return _text(rel), _flag(keep)


def _decode_resolution(entry) -> tuple[str, Resolution]:
    if not (isinstance(entry, list) and len(entry) == 3):
        raise ValueError("a resolution needs exactly a key, an action and a rename target")
    key, action, rename_to = entry
    key = _text(key)
    if action not in _RESOLUTION_ACTIONS:
        raise ValueError("unknown resolution action")
    if rename_to is not None:
        rename_to = _text(rename_to)
    return key, Resolution(action=action, rename_to=rename_to)


# ── Saving and loading ───────────────────────────────────────────────

def save_draft(
    path: Path,
    repo_root: Path,
    choices: MigrationChoices,
    prints: Mapping[PartKey, str],
    *,
    saved_at: str | None = None,
) -> Issue | None:
    """Write the draft atomically; any failure is one WARNING, and this never raises (D-14)."""

    def failed(reason: str) -> Issue:
        return Issue(Severity.WARNING, "draft.save_failed", f"Could not save the migration draft: {reason}")

    try:
        keys = sorted(set(prints) | set(choices.parts))
        parts_payload = []
        for key in keys:
            entry: dict = {"key": [key[0], key[1]], "print": prints.get(key, "")}
            choice = choices.parts.get(key)
            if choice is not None:
                entry["choice"] = _encode_choice(choice)
            parts_payload.append(entry)
        leftover_items = sorted(choices.leftovers.items(), key=lambda item: item[0])
        resolution_items = sorted(choices.resolutions.items(), key=lambda item: item[0])
        payload = {
            "format": DRAFT_FORMAT,
            "repo_root": _repo_key(repo_root),
            "saved_at": saved_at or _now(),
            "parts": parts_payload,
            "leftovers": [[rel, keep] for rel, keep in leftover_items],
            "resolutions": [[key, res.action, res.rename_to] for key, res in resolution_items],
        }
        text = json.dumps(payload, separators=(",", ":"))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    except (OSError, TypeError, ValueError) as e:
        return failed(getattr(e, "strerror", None) or str(e))
    failure = fsutil.atomic_write_text(Path(path), text)
    if failure is not None:
        return failed(failure.text)
    return None


def load_draft(path: Path, repo_root: Path) -> "LoadedDraft | Issue":
    """Read the draft back, or the one INFO note saying why it is unavailable (D-14, T-13-20).

    Never raises: anything short of a well-typed payload saved for this exact repository is
    reported as one INFO Issue and never produces a partial MigrationChoices.
    """
    unreadable = _info("draft.unreadable", "The saved migration draft could not be read; starting without it")
    try:
        size = Path(path).stat().st_size
    except FileNotFoundError:
        return _info("draft.none", "No saved migration draft yet.")
    except OSError:
        return unreadable
    if size > MAX_DRAFT_BYTES:
        return unreadable
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("a draft must be an object")
        if payload.get("format") != DRAFT_FORMAT:
            raise ValueError("unknown draft format")
        repo_value = _text(payload["repo_root"])
        saved_at = _text(payload["saved_at"])
        datetime.fromisoformat(saved_at)
        parts_raw = payload["parts"]
        leftovers_raw = payload["leftovers"]
        resolutions_raw = payload["resolutions"]
        if not (isinstance(parts_raw, list) and isinstance(leftovers_raw, list) and isinstance(resolutions_raw, list)):
            raise TypeError("expected a list")

        parts: dict[PartKey, PartChoice] = {}
        prints: dict[PartKey, str] = {}
        for entry in parts_raw:
            key, choice, print_value = _decode_part_entry(entry)
            if choice is not None:
                parts[key] = choice
            prints[key] = print_value
        leftovers = dict(_decode_leftover(entry) for entry in leftovers_raw)
        resolutions = dict(_decode_resolution(entry) for entry in resolutions_raw)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return unreadable

    if repo_value != _repo_key(repo_root):
        return _info(
            "draft.other_repo", "The saved migration draft belongs to another repository; starting without it"
        )

    return LoadedDraft(
        choices=MigrationChoices(parts=parts, leftovers=leftovers, resolutions=resolutions),
        fingerprints=prints,
        saved_at=saved_at,
    )


def clear_draft(path: Path) -> Issue | None:
    """Remove the draft after a successful Run; a missing file is fine, any other failure is one WARNING."""
    try:
        Path(path).unlink()
    except FileNotFoundError:
        return None
    except OSError as e:
        return Issue(Severity.WARNING, "draft.clear_failed", f"Could not clear the migration draft: {e.strerror or e}")
    return None
