from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout

from ..importer.content import ContentText
from . import theme


class DiffHighlighter(QSyntaxHighlighter):
    """Colours whole diff lines: added on SUCCESS_TINT, removed on ERROR_TINT, hunk headers bold MUTED.

    The + and - characters stay in the text, so colour is never the only cue.
    """

    def __init__(self, document):
        super().__init__(document)
        self._added = QTextCharFormat()
        self._added.setBackground(QBrush(QColor(theme.SUCCESS_TINT)))
        self._removed = QTextCharFormat()
        self._removed.setBackground(QBrush(QColor(theme.ERROR_TINT)))
        self._hunk = QTextCharFormat()
        self._hunk.setFontWeight(QFont.Weight.Bold)
        self._hunk.setForeground(QBrush(QColor(theme.MUTED)))

    def highlightBlock(self, text: str) -> None:
        # The first two lines are the --- and +++ file headers, not removed and added lines
        if self.currentBlock().blockNumber() < 2 and text.startswith(("---", "+++")):
            return
        if text.startswith("@@"):
            self.setFormat(0, len(text), self._hunk)
        elif text.startswith("+"):
            self.setFormat(0, len(text), self._added)
        elif text.startswith("-"):
            self.setFormat(0, len(text), self._removed)


class ContentViewDialog(QDialog):
    """Read-only view of one ContentText: a header strip, the text in a monospace editor, a Close button."""

    def __init__(self, content: ContentText, parent=None):
        super().__init__(parent)
        self.setWindowTitle(content.title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(800, 560)
        self.setMinimumSize(600, 400)
        self._content = content

        layout = QVBoxLayout(self)
        layout.setSpacing(theme.SP_SM)

        self._header = QLabel(content.header)
        self._header.setTextFormat(Qt.TextFormat.PlainText)
        self._header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._header.setStyleSheet(f"QLabel {{ background-color: {theme.SURFACE}; padding: {theme.SP_SM}px; }}")
        layout.addWidget(self._header)

        # Plain text only: a vendor file is never interpreted as markup
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont(theme.MONO_FAMILY, theme.MONO_PT))
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text.setPlainText(content.body)
        layout.addWidget(self._text, 1)

        self._highlighter: DiffHighlighter | None = None
        if content.kind == "diff":
            self._highlighter = DiffHighlighter(self._text.document())
            self._highlighter.rehighlight()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self._close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(buttons)
