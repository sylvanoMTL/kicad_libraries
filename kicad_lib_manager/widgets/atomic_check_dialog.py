"""Check Atomic Parts dialog: lists the problems of the last scan, fixes the safe ones after a preview (SCAN-03).

The dialog works only from the ScanResult it is given; it never scans and never runs the check (D-12).
Files are written by apply_preview alone, called from the Apply button of the preview page (D-13).
"""

from collections.abc import Callable, Iterator
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QStackedWidget,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..atomic_fixes import FixPreview, apply_preview, build_preview, preview_text
from ..models import FixSpec, ScanResult, SymbolEntry
from .theme import AMBER, MONO_FAMILY, MONO_PT, PRIMARY_BUTTON_QSS, SP_MD, SP_SM

_PAGE_PROBLEMS = 0
_PAGE_PREVIEW = 1
NO_ONE_CLICK_FIX = "No one-click fix"


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


class AtomicCheckDialog(QDialog):
    applied = Signal(object)        # list[Issue], after a successful apply
    issues_logged = Signal(object)  # list[Issue], for a refused apply

    def __init__(
        self,
        scan_result: ScanResult,
        repo_root: Path,
        *,
        focus: tuple[str, str] | None = None,
        backup_root: Path | None = None,
        running: Callable[[], list[str]] | None = None,
        pick_model: Callable[[QWidget], Path | None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Check Atomic Parts")
        self.resize(900, 620)
        self._repo_root = Path(repo_root)
        self._backup_root = backup_root
        self._running = running
        self._pick_model = pick_model
        self._preview: FixPreview | None = None

        layout = QVBoxLayout(self)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)
        self._stack.addWidget(self._build_problems_page(scan_result))
        self._stack.addWidget(self._build_preview_page())
        self._refresh_count()

    # ── Page 0: problems and fixes ──────────────────────────────────────────

    def _build_problems_page(self, scan_result: ScanResult) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._summary = QLabel()
        self._summary.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self._summary)

        self._problems = QTreeWidget()
        self._problems.setColumnCount(2)
        self._problems.setHeaderLabels(["Problem", "Fix"])
        self._problems.setColumnWidth(0, 520)
        layout.addWidget(self._problems, stretch=1)

        buttons = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        buttons.addWidget(self._select_all_btn)
        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.clicked.connect(lambda: self._set_all_checked(False))
        buttons.addWidget(self._deselect_all_btn)
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        self._preview_btn = QPushButton()
        self._preview_btn.setStyleSheet(PRIMARY_BUTTON_QSS)
        self._preview_btn.clicked.connect(self._on_preview)
        buttons.addWidget(self._preview_btn)
        layout.addLayout(buttons)

        self._populate(scan_result)
        self._problems.itemChanged.connect(lambda *_: self._refresh_count())
        return page

    def _populate(self, scan_result: ScanResult):
        problems = 0
        symbols = 0
        self._problems.blockSignals(True)
        try:
            for lib in scan_result.symbol_libs:
                for entry in lib.symbols:
                    if not entry.violations and not entry.findings:
                        continue
                    symbols += 1
                    problems += len(entry.violations) + len(entry.findings)
                    self._problems.addTopLevelItem(self._symbol_row(lib.nickname, lib.rel_path, entry))
        finally:
            self._problems.blockSignals(False)
        self._problems.expandAll()
        self._summary.setText(
            f"{_plural(problems, 'problem', 'problems')} in "
            f"{_plural(symbols, 'symbol', 'symbols')}, from the last scan"
        )

    def _symbol_row(self, nickname: str, rel_path: str, entry: SymbolEntry) -> QTreeWidgetItem:
        row = QTreeWidgetItem([f"{nickname} / {entry.name}", ""])
        row.setData(0, Qt.ItemDataRole.UserRole, (rel_path, entry.name))
        if entry.failing:
            row.setForeground(0, QBrush(QColor(AMBER)))
        for violation in entry.violations:
            item = QTreeWidgetItem([violation.text, ""])
            item.setForeground(0, QBrush(QColor(AMBER)))
            row.addChild(item)
            for spec in violation.fixes:
                item.addChild(self._fix_row(spec))
            if not violation.fixes and violation.fill is None:
                item.setText(1, NO_ONE_CLICK_FIX)
        for finding in entry.findings:
            item = QTreeWidgetItem([finding.text, ""])
            row.addChild(item)
            if finding.fix is not None:
                item.addChild(self._fix_row(finding.fix))
        return row

    @staticmethod
    def _fix_row(spec: FixSpec) -> QTreeWidgetItem:
        item = QTreeWidgetItem([spec.label, ""])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setData(0, Qt.ItemDataRole.UserRole, spec)
        return item

    def _fix_items(self) -> Iterator[QTreeWidgetItem]:
        """Every checkable fix row, in tree order."""
        for i in range(self._problems.topLevelItemCount()):
            symbol = self._problems.topLevelItem(i)
            for j in range(symbol.childCount()):
                problem = symbol.child(j)
                for k in range(problem.childCount()):
                    item = problem.child(k)
                    if isinstance(item.data(0, Qt.ItemDataRole.UserRole), FixSpec):
                        yield item

    def checked_specs(self) -> list[FixSpec]:
        """The ticked fixes, in tree order."""
        return [
            item.data(0, Qt.ItemDataRole.UserRole)
            for item in self._fix_items()
            if item.checkState(0) == Qt.CheckState.Checked
        ]

    def _set_all_checked(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._problems.blockSignals(True)
        try:
            for item in self._fix_items():
                item.setCheckState(0, state)
        finally:
            self._problems.blockSignals(False)
        self._refresh_count()

    def _refresh_count(self):
        count = len(self.checked_specs())
        self._preview_btn.setText(f"Preview & apply {_plural(count, 'fix', 'fixes')}")
        self._preview_btn.setEnabled(count > 0)

    # ── Page 1: preview and apply ───────────────────────────────────────────

    def _build_preview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(SP_SM)

        layout.addWidget(QLabel("This is exactly what Apply will change:"))

        self._preview_text = QPlainTextEdit()
        self._preview_text.setReadOnly(True)
        font = self._preview_text.font()
        font.setFamily(MONO_FAMILY)
        font.setPointSize(MONO_PT)
        self._preview_text.setFont(font)
        layout.addWidget(self._preview_text, stretch=1)

        self._running_label = QLabel()
        self._running_label.setTextFormat(Qt.TextFormat.PlainText)
        self._running_label.setWordWrap(True)
        self._running_label.setStyleSheet(f"color: {AMBER}; font-weight: bold;")
        self._running_label.hide()
        layout.addWidget(self._running_label)

        self._issues_label = QLabel()
        self._issues_label.setTextFormat(Qt.TextFormat.PlainText)
        self._issues_label.setWordWrap(True)
        self._issues_label.hide()
        layout.addWidget(self._issues_label)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, SP_MD, 0, 0)
        buttons.addStretch()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self._on_back)
        buttons.addWidget(back_btn)
        self._apply_btn = QPushButton()
        self._apply_btn.setStyleSheet(PRIMARY_BUTTON_QSS)
        self._apply_btn.clicked.connect(self._on_apply)
        buttons.addWidget(self._apply_btn)
        layout.addLayout(buttons)
        return page

    def _on_preview(self):
        preview = build_preview(self._repo_root, self.checked_specs(), running=self._running)
        self._preview = preview
        if preview.changes:
            self._preview_text.setPlainText("\n\n".join(preview_text(change) for change in preview.changes))
        else:
            self._preview_text.setPlainText("Nothing would change.")
        if preview.kicad_running:
            self._running_label.setText(
                f"KiCad is running ({', '.join(preview.kicad_running)}). If a library these fixes change "
                "is open in the Symbol or Footprint Editor, close it without saving or reload it after "
                "the fixes, or KiCad may overwrite them."
            )
            self._running_label.show()
        else:
            self._running_label.hide()
        self._show_issues([issue.text for issue in preview.issues])
        count = len(preview.changes)
        self._apply_btn.setText(f"Apply {_plural(count, 'file change', 'file changes')}")
        self._apply_btn.setEnabled(count > 0)
        self._stack.setCurrentIndex(_PAGE_PREVIEW)

    def _show_issues(self, texts: list[str]):
        self._issues_label.setText("\n".join(texts))
        self._issues_label.setVisible(bool(texts))

    def _on_back(self):
        self._preview = None
        self._stack.setCurrentIndex(_PAGE_PROBLEMS)

    def _on_apply(self):
        preview = self._preview
        if preview is None:
            return
        result = apply_preview(preview, backup_root=self._backup_root)
        if result.ok:
            self.applied.emit(result.issues)
            self.accept()
            return
        self._show_issues([issue.text for issue in result.issues])
        self._apply_btn.setEnabled(False)
        self.issues_logged.emit(result.issues)
