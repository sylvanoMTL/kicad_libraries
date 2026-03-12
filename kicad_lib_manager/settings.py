"""Persistent application settings stored in the platform's standard location.

Windows: %APPDATA%/KiCadExtLibManager/settings.ini
Linux:   ~/.config/KiCadExtLibManager/settings.ini
macOS:   ~/Library/Preferences/KiCadExtLibManager/settings.ini
"""

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
