"""Content view builders and dialog (plan 05-06, D-08): new text, unified diff, binary summary, caps."""

import difflib
import hashlib
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPlainTextEdit

from kicad_lib_manager.importer.content import (
    MAX_BYTES,
    MAX_LINES,
    ContentText,
    cap_lines,
    op_content,
    unchanged_content,
)
from kicad_lib_manager.importer.package import PackageFile
from kicad_lib_manager.importer.plan import FileOp
from kicad_lib_manager.widgets import theme
from kicad_lib_manager.widgets.content_view import ContentViewDialog, DiffHighlighter

FP_REL = "Custom/Footprints/IC_Test_TI.pretty/FP.kicad_mod"
SYM_REL = "Custom/Symbols/IC_Test_TI.kicad_sym"
MODEL_REL = "Custom/3DModels/PART.stp"


def _write(root: Path, rel: str, data: bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _lines(prefix: str, count: int, width: int = 0) -> str:
    return "\n".join(f"{prefix}{i}".ljust(width, "x") for i in range(count)) + "\n"


def _model_file(size: int, digest: str) -> PackageFile:
    return PackageFile(member="DLV.stp", path=Path("staged.stp"), kind="model", size=size, sha256=digest, staged=True)


# -- text and diff -----------------------------------------------------------------------------


def test_new_text_content(tmp_path):
    text = '(footprint "FP"\n  (layer "F.Cu")\n)\n'
    op = FileOp("footprint", tmp_path / FP_REL, data=text.encode())
    content = op_content(op, tmp_path)
    assert (content.kind, content.title, content.header) == ("text", f"{FP_REL} - new file", FP_REL)
    assert content.body == text.rstrip("\n")


def test_new_text_strips_a_bom(tmp_path):
    op = FileOp("footprint", tmp_path / FP_REL, data=b"\xef\xbb\xbf(footprint)\n")
    assert op_content(op, tmp_path).body == "(footprint)"


def test_mkdir_content(tmp_path):
    content = op_content(FileOp("mkdir", tmp_path / "Custom" / "Footprints" / "L.pretty"), tmp_path)
    assert content.body == "Custom/Footprints/L.pretty/ is a new folder created by the install."


def test_modified_diff_shows_only_hunk(tmp_path):
    old = _lines("line ", 60)
    new = old.replace("line 30\n", "line 30\n(symbol added)\n")
    _write(tmp_path, SYM_REL, old.encode())
    op = FileOp("symbol_lib", tmp_path / SYM_REL, data=new.encode(), base_sha256="abc")
    content = op_content(op, tmp_path)
    assert (content.kind, content.title) == ("diff", f"{SYM_REL} - changes")
    lines = content.body.split("\n")
    assert lines[0] == f"--- {SYM_REL} (current)" and lines[1] == f"+++ {SYM_REL} (planned)"
    assert sum(1 for line in lines if line.startswith("@@")) == 1
    assert [line for line in lines if line.startswith("+") and not line.startswith("+++")] == ["+(symbol added)"]
    assert not [line for line in lines if line.startswith("-") and not line.startswith("---")]
    assert " line 27" in lines and " line 33" in lines  # 3 lines of context each side
    assert " line 5" not in lines and " line 55" not in lines


def test_modified_equal_content_is_unchanged(tmp_path):
    _write(tmp_path, SYM_REL, b"same\n")
    op = FileOp("symbol_lib", tmp_path / SYM_REL, data=b"same\n", base_sha256="abc")
    content = op_content(op, tmp_path)
    assert (content.kind, content.body) == ("unchanged", "This file is unchanged by the install.")


def test_diff_truncated_at_5000_lines(tmp_path):
    old, new = _lines("a", 12000), _lines("b", 12000)
    _write(tmp_path, SYM_REL, old.encode())
    op = FileOp("symbol_lib", tmp_path / SYM_REL, data=new.encode(), base_sha256="abc")
    total = sum(1 for _ in difflib.unified_diff(
        old.splitlines(), new.splitlines(), f"{SYM_REL} (current)", f"{SYM_REL} (planned)", lineterm="", n=3
    ))
    lines = op_content(op, tmp_path).body.split("\n")
    assert len(lines) == MAX_LINES + 1
    assert lines[-1] == f"Diff truncated: showing the first {MAX_LINES} of {total} lines."


def test_diff_truncated_at_512_kib(tmp_path):
    old, new = _lines("a", 800, 1000), _lines("b", 800, 1000)
    _write(tmp_path, SYM_REL, old.encode())
    op = FileOp("symbol_lib", tmp_path / SYM_REL, data=new.encode(), base_sha256="abc")
    total = sum(1 for _ in difflib.unified_diff(
        old.splitlines(), new.splitlines(), f"{SYM_REL} (current)", f"{SYM_REL} (planned)", lineterm="", n=3
    ))
    lines = op_content(op, tmp_path).body.split("\n")
    kept = len(lines) - 1
    assert 0 < kept < MAX_LINES
    assert lines[-1] == f"Diff truncated: showing the first {kept} of {total} lines."
    assert sum(len(line.encode()) + 1 for line in lines[:-1]) <= MAX_BYTES


def test_cap_lines_leaves_a_small_text_alone():
    assert cap_lines(["a", "b"]) == ["a", "b"]
    assert cap_lines([]) == []


def test_cap_lines_counts_utf8_bytes():
    wide = "é" * 1000  # two bytes per character
    lines = [wide] * 600
    capped = cap_lines(lines)
    assert capped[-1].startswith("Diff truncated: showing the first ")
    assert sum(len(line.encode()) + 1 for line in capped[:-1]) <= MAX_BYTES


def test_a_large_new_text_file_is_capped_too(tmp_path):
    op = FileOp("footprint", tmp_path / FP_REL, data=_lines("row ", 9000).encode())
    lines = op_content(op, tmp_path).body.split("\n")
    assert len(lines) == MAX_LINES + 1
    assert lines[-1] == f"Diff truncated: showing the first {MAX_LINES} of 9000 lines."


# -- binary ---------------------------------------------------------------------------------------


def test_binary_summary_new_and_modified(tmp_path):
    planned = _model_file(2048, "ab" * 32)
    new_op = FileOp("model", tmp_path / MODEL_REL, source=planned)
    new = op_content(new_op, tmp_path)
    assert (new.kind, new.title) == ("binary", f"{MODEL_REL} - new file")
    assert new.body.split("\n")[:3] == ["PART.stp", "Size: 2.0 KiB", f"SHA-256: {'ab' * 32}"]

    existing = b"old model bytes" * 100
    _write(tmp_path, MODEL_REL, existing)
    modified_op = FileOp("model", tmp_path / MODEL_REL, source=planned, base_sha256="x")
    modified = op_content(modified_op, tmp_path)
    assert modified.title == f"{MODEL_REL} - changes"
    assert hashlib.sha256(existing).hexdigest() in modified.body
    assert f"Size: {len(existing) / 1024:.1f} KiB" in modified.body
    assert "ab" * 32 in modified.body


def test_binary_content_is_never_decoded(tmp_path):
    # Bytes that are not valid UTF-8 must not appear in or break the summary
    _write(tmp_path, MODEL_REL, bytes(range(256)) * 4)
    op = FileOp("model", tmp_path / MODEL_REL, source=_model_file(1, "cd" * 32), base_sha256="x")
    body = op_content(op, tmp_path).body
    assert "�" not in body


# -- error, unchanged, conflict -----------------------------------------------------------------------


def test_unreadable_existing_file(tmp_path):
    op = FileOp("symbol_lib", tmp_path / SYM_REL, data=b"new\n", base_sha256="abc")
    content = op_content(op, tmp_path)
    assert content.kind == "error"
    assert content.body.startswith(f"Could not read {SYM_REL}: ") and content.body.endswith(".")


def test_unreadable_existing_model(tmp_path):
    op = FileOp("model", tmp_path / MODEL_REL, source=_model_file(1, "cd" * 32), base_sha256="x")
    content = op_content(op, tmp_path)
    assert content.kind == "error" and content.body.startswith(f"Could not read {MODEL_REL}: ")


def test_existing_file_over_the_read_cap_is_refused(tmp_path):
    import kicad_lib_manager.importer.content as content_module

    _write(tmp_path, SYM_REL, b"x" * 64)
    op = FileOp("symbol_lib", tmp_path / SYM_REL, data=b"y\n", base_sha256="abc")
    original = content_module.MAX_READ
    content_module.MAX_READ = 16
    try:
        content = op_content(op, tmp_path)
    finally:
        content_module.MAX_READ = original
    assert content.kind == "error" and content.body.startswith(f"Could not read {SYM_REL}: ")


def test_unchanged_content(tmp_path):
    content = unchanged_content(tmp_path / SYM_REL, tmp_path)
    assert content == ContentText(
        title=f"{SYM_REL} - unchanged",
        header=SYM_REL,
        body="This file is unchanged by the install.",
        kind="unchanged",
    )


def test_conflict_content_title(tmp_path):
    _write(tmp_path, FP_REL, b'(footprint "FP"\n  (layer "F.Cu")\n)\n')
    op = FileOp("footprint", tmp_path / FP_REL, data=b'(footprint "FP"\n  (layer "B.Cu")\n)\n', base_sha256="abc")
    content = op_content(op, tmp_path, conflict=True)
    assert content.title == f"{FP_REL} - existing vs incoming"
    assert content.kind == "diff"
    assert f"--- {FP_REL} (existing)" in content.body and f"+++ {FP_REL} (incoming)" in content.body
    assert '-  (layer "F.Cu")' in content.body and '+  (layer "B.Cu")' in content.body


# -- dialog ------------------------------------------------------------------------------------------------


def _dialog(qtbot, kind="text", body="alpha\n+added\n-removed\n@@ hunk\n"):
    dialog = ContentViewDialog(ContentText(title="T - changes", header="Custom/x.kicad_sym", body=body, kind=kind))
    qtbot.addWidget(dialog)
    return dialog


def test_content_view_dialog(qtbot):
    dialog = _dialog(qtbot, "diff")
    assert dialog.windowTitle() == "T - changes"
    assert dialog.windowModality() == Qt.WindowModality.WindowModal
    assert (dialog.width(), dialog.height()) == (800, 560)
    assert (dialog.minimumWidth(), dialog.minimumHeight()) == (600, 400)
    edit = dialog.findChild(QPlainTextEdit)
    assert edit.isReadOnly()
    assert edit.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    assert edit.font().family() == theme.MONO_FAMILY and edit.font().pointSize() == theme.MONO_PT
    assert edit.toPlainText().startswith("alpha")
    assert dialog._header.text() == "Custom/x.kicad_sym"
    assert dialog._header.textFormat() == Qt.TextFormat.PlainText
    assert isinstance(dialog._highlighter, DiffHighlighter)

    dialog.show()
    qtbot.waitExposed(dialog)
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()


def test_content_view_dialog_close_button(qtbot):
    dialog = _dialog(qtbot)
    dialog.show()
    qtbot.waitExposed(dialog)
    dialog._close_btn.click()
    assert not dialog.isVisible()


def test_highlighter_only_for_diffs(qtbot):
    for kind in ("text", "binary", "unchanged", "error"):
        assert _dialog(qtbot, kind)._highlighter is None


def test_diff_highlighter_colours_whole_lines(qtbot):
    dialog = _dialog(qtbot, "diff", "--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n context")
    dialog._highlighter.rehighlight()
    document = dialog.findChild(QPlainTextEdit).document()

    def formats(index):
        return document.findBlockByNumber(index).layout().formats()

    for index in (0, 1, 5):  # file headers and context are not coloured
        assert formats(index) == []
    hunk, removed, added = (formats(i)[0] for i in (2, 3, 4))
    assert hunk.format.fontWeight() == 700
    assert hunk.format.foreground().color().name().upper() == theme.MUTED
    assert removed.format.background().color().name().upper() == QColor(theme.ERROR_TINT).name().upper()
    assert added.format.background().color().name().upper() == QColor(theme.SUCCESS_TINT).name().upper()
    # The +/- characters stay in the text
    assert document.findBlockByNumber(3).text() == "-old"
    assert (added.start, added.length) == (0, len("+new"))
