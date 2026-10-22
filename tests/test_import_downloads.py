"""Newest-zip lookup and age text for the Import dialog's Start page (plan 05-05, UX-02)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from kicad_lib_manager.importer.downloads import age_text, newest_zip

REPO_ROOT = Path(__file__).resolve().parent.parent


def _touch(path: Path, mtime: float) -> Path:
    path.write_bytes(b"x")
    os.utime(path, (mtime, mtime))
    return path


def test_newest_zip_picks_latest(tmp_path):
    t = 1_700_000_000.0
    _touch(tmp_path / "a.zip", t)
    _touch(tmp_path / "B.ZIP", t + 60)
    _touch(tmp_path / "c.txt", t + 600)
    (tmp_path / "d.zip").mkdir()
    os.utime(tmp_path / "d.zip", (t + 900, t + 900))
    nested = tmp_path / "sub"
    nested.mkdir()
    _touch(nested / "e.zip", t + 1200)

    found = newest_zip(tmp_path)
    assert found is not None
    path, mtime = found
    assert path == tmp_path / "B.ZIP"
    assert mtime == pytest.approx(t + 60)


def test_newest_zip_empty_and_missing(tmp_path):
    assert newest_zip(tmp_path) is None
    (tmp_path / "notes.txt").write_text("x", encoding="utf-8")
    assert newest_zip(tmp_path) is None
    assert newest_zip(tmp_path / "does_not_exist") is None


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "just now"),
        (59, "just now"),
        (60, "1 minute ago"),
        (125, "2 minutes ago"),
        (3599, "59 minutes ago"),
        (3600, "1 hour ago"),
        (7300, "2 hours ago"),
        (86399, "23 hours ago"),
        (86400, "1 day ago"),
        (3 * 86400, "3 days ago"),
        (-5, "just now"),
    ],
)
def test_age_text_buckets(seconds, expected):
    assert age_text(seconds) == expected


def test_downloads_module_is_qt_free():
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "import kicad_lib_manager.importer.downloads; "
        "print([m for m in sys.modules if m.split('.')[0] in ('PySide6', 'shiboken6')])"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-c", code, str(REPO_ROOT)],
        capture_output=True, text=True, check=True,
    )
    assert out.stdout.strip() == "[]"
