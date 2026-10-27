"""Persistent application settings stored in the platform's standard location.

Windows: %APPDATA%/KiCadExtLibManager/settings.ini
Linux:   ~/.config/KiCadExtLibManager/settings.ini
macOS:   ~/Library/Preferences/KiCadExtLibManager/settings.ini
"""

import hashlib
import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

_MAX_DEST_HISTORY = 10

APP_ORG = "KiCadExtLibManager"
APP_NAME = "settings"


def get_settings() -> QSettings:
    return QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        APP_ORG,
        APP_NAME,
    )


# ── KiCad footprint directory ────────────────────────────────────────

def load_kicad_fp_dir() -> Path | None:
    s = get_settings()
    val = s.value("kicad_fp_dir", "")
    if val:
        p = Path(val)
        if p.is_dir():
            return p
    return None


def save_kicad_fp_dir(path: Path) -> None:
    s = get_settings()
    s.setValue("kicad_fp_dir", str(path))


# ── Scan cache ───────────────────────────────────────────────────────

def scan_cache_file(repo_root: Path) -> Path:
    """The saved scan of one repository folder: scan_cache/<hash>.json beside settings.ini, never in the repo."""
    key = hashlib.sha256(os.path.normcase(str(Path(repo_root).resolve())).encode("utf-8")).hexdigest()[:16]
    return Path(get_settings().fileName()).parent / "scan_cache" / f"{key}.json"


# ── Import folder ────────────────────────────────────────────────────

def load_import_dir() -> Path | None:
    """The folder the last import was picked from; the stored value is untrusted, so re-check it."""
    s = get_settings()
    val = s.value("import/last_dir", "")
    if val:
        p = Path(str(val))
        if p.is_dir():
            return p
    return None


def save_import_dir(path: Path) -> None:
    s = get_settings()
    s.setValue("import/last_dir", str(path))


# ── Destination folder history ────────────────────────────────────────

def load_dest_history() -> list[str]:
    s = get_settings()
    val = s.value("dest_history", [])
    if isinstance(val, str):
        return [val] if val else []
    return list(val) if val else []


def add_dest_to_history(path: str) -> list[str]:
    history = load_dest_history()
    # Move to front if already present, otherwise prepend
    if path in history:
        history.remove(path)
    history.insert(0, path)
    history = history[:_MAX_DEST_HISTORY]
    s = get_settings()
    s.setValue("dest_history", history)
    return history


# ── Window geometry ───────────────────────────────────────────────────

def load_window_geometry() -> QByteArray | None:
    s = get_settings()
    val = s.value("window/geometry")
    if isinstance(val, QByteArray) and not val.isEmpty():
        return val
    return None


def save_window_geometry(geometry: QByteArray) -> None:
    s = get_settings()
    s.setValue("window/geometry", geometry)
