"""Find the newest .zip in a folder (the Downloads offer, UX-02); stdlib only, no Qt.

Read-only: the zip is only listed, never opened. Opening a package stays an explicit user action.
"""

import os
from pathlib import Path


def newest_zip(folder: Path) -> tuple[Path, float] | None:
    """Return the newest .zip file directly in folder and its mtime, or None when there is none.

    Not recursive; the extension match ignores case and folders named like a zip do not count.
    A missing or unreadable folder, and an entry that cannot be inspected, give None or are skipped.
    """
    best: tuple[Path, float] | None = None
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                try:
                    if not entry.name.casefold().endswith(".zip") or not entry.is_file():
                        continue
                    mtime = entry.stat().st_mtime
                except OSError:
                    continue
                if best is None or mtime > best[1]:
                    best = (Path(entry.path), mtime)
    except OSError:
        return None
    return best


def _plural(count: int, unit: str) -> str:
    return f"{count} {unit} ago" if count == 1 else f"{count} {unit}s ago"


def age_text(seconds: float) -> str:
    """Describe an age in whole units: "just now" below a minute (or in the future), then minutes, hours, days."""
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return _plural(int(seconds // 60), "minute")
    if seconds < 86400:
        return _plural(int(seconds // 3600), "hour")
    return _plural(int(seconds // 86400), "day")
