from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QSplitter, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)
from PySide6.QtCore import Qt

CSS = """
body {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    color: #222;
    margin: 16px 20px;
    line-height: 1.55;
}
h2 {
    color: #0057A0;
    border-bottom: 2px solid #0078D4;
    padding-bottom: 6px;
    margin-top: 8px;
}
h3 {
    color: #333;
    margin-top: 18px;
}
code {
    background: #EEF1F5;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 13px;
}
pre {
    background: #F5F7FA;
    border-left: 3px solid #0078D4;
    padding: 10px 14px;
    font-size: 13px;
    overflow-x: auto;
}
ul, ol { margin-left: 8px; }
li { margin-bottom: 6px; }
table {
    border-collapse: collapse;
    margin: 10px 0;
}
th, td {
    border: 1px solid #CCC;
    padding: 6px 12px;
    text-align: left;
}
th { background: #EEF1F5; }
a { color: #0078D4; }
.hint {
    background: #FFF8E1;
    border-left: 3px solid #F9A825;
    padding: 8px 12px;
    margin: 10px 0;
}
"""


def _wrap(body: str) -> str:
    return f"<html><head><style>{CSS}</style></head><body>{body}</body></html>"


# ── Help pages ────────────────────────────────────────────────────────

HELP_PAGES: dict[str, str] = {}

HELP_PAGES["overview"] = _wrap(
    "<h2>Overview</h2>"
    "<p>KiCad uses <b>sym-lib-table</b> and <b>fp-lib-table</b> files to locate "
    "symbol and footprint libraries. When you maintain custom parts alongside "
    "third-party libraries (e.g.&nbsp;W&uuml;rth Elektronik), keeping those "
    "tables in sync manually is tedious and error-prone.</p>"
    "<p><b>KiCad External Lib Manager</b> automates the process:</p>"
    "<ul>"
    "<li>Scans your repository and discovers every library automatically</li>"
    "<li>Cross-references symbol&rarr;footprint links to detect broken references</li>"
    "<li>Checks 3D model paths for common issues</li>"
    "<li>Generates the table files in one click, with automatic backups</li>"
    "</ul>"
    "<p>No library paths are hard-coded &mdash; everything is discovered dynamically "
    "from the repository structure.</p>"
)

HELP_PAGES["requirements"] = _wrap(
    "<h2>Requirements</h2>"
    "<ul>"
    "<li><b>Python 3.10</b> or newer</li>"
    "<li><b>PySide6</b> &mdash; install with: <code>pip install PySide6</code></li>"
    "</ul>"
    '<p class="hint"><b>Tip:</b> Use a virtual environment to keep dependencies '
    "isolated:<br>"
    "<code>python -m venv env &amp;&amp; env\\Scripts\\activate &amp;&amp; "
    "pip install PySide6</code></p>"
)

HELP_PAGES["how_to_run"] = _wrap(
    "<h2>How to Run</h2>"
    "<p>From the repository root directory:</p>"
    "<pre>python kicad_lib_manager.py</pre>"
    "<p>The main window opens and immediately starts scanning the repository.</p>"
)

HELP_PAGES["kicad_detection"] = _wrap(
    "<h2>KiCad Detection</h2>"
    "<p>On startup the tool tries to <b>auto-detect</b> your KiCad installation "
    "to locate the default footprint libraries.</p>"
    "<h3>Why it matters</h3>"
    "<p>Many symbols reference KiCad's built-in footprints "
    "(e.g.&nbsp;<code>Resistor_SMD:R_0402_1005Metric</code>). Without knowing "
    "the install path, those perfectly valid references would show up as "
    "<b>false warnings</b>.</p>"
    "<h3>Auto-detection</h3>"
    "<p>The tool looks in standard locations:</p>"
    "<ul>"
    "<li><b>Windows:</b> <code>C:\\Program Files\\KiCad\\&lt;version&gt;"
    "\\share\\kicad\\footprints</code></li>"
    "<li><b>macOS:</b> <code>/Applications/KiCad/footprints</code></li>"
    "<li><b>Linux:</b> <code>/usr/share/kicad/footprints</code></li>"
    "</ul>"
    "<p>If multiple versions are installed, the latest is selected.</p>"
    "<h3>Manual selection</h3>"
    "<p>If auto-detection fails, a folder picker dialog appears. You can also "
    "change the path later via <b>File &rarr; Set KiCad Footprint Path</b> "
    "(<code>Ctrl+K</code>), which triggers a rescan.</p>"
)

HELP_PAGES["repo_scan"] = _wrap(
    "<h2>Repository Scan</h2>"
    "<p>After KiCad detection, the tool scans the entire repository:</p>"
    "<ol>"
    "<li><b>Footprint libraries</b> &mdash; every <code>.pretty</code> folder</li>"
    "<li><b>Symbol libraries</b> &mdash; every <code>.kicad_sym</code> file; each "
    "symbol's <code>Footprint</code> property is parsed to extract references</li>"
    "<li><b>Cross-reference</b> &mdash; each footprint reference is checked against "
    "both the repository and KiCad defaults. Missing links become warnings</li>"
    "<li><b>3D model check</b> &mdash; <code>.kicad_mod</code> files are scanned "
    "for absolute or broken model paths (paths should use "
    "<code>${VARIABLE}</code> notation)</li>"
    "</ol>"
    "<p>Results appear in the library tree. Warnings are logged in the bottom panel "
    "and flagged with an orange icon in the tree.</p>"
)

HELP_PAGES["library_tree"] = _wrap(
    "<h2>Library Tree</h2>"
    "<p>The main area is split into two side-by-side panels:</p>"
    "<table>"
    "<tr><th>Left panel</th><th>Right panel</th></tr>"
    "<tr><td>Symbol libraries</td><td>Footprint libraries</td></tr>"
    "</table>"
    "<p>Each panel groups libraries by <b>source</b> (Custom, WurthElektronik, "
    "etc.). Source headers are bold and collapsible.</p>"
    "<h3>Columns</h3>"
    "<ul>"
    "<li><b>Library Name</b> &mdash; the nickname used in the table file</li>"
    "<li><b>Source</b> &mdash; which top-level folder the library comes from</li>"
    "<li><b>Linked Footprints</b> (symbols only) &mdash; the footprint references "
    "found in the symbol file</li>"
    "<li><b>Status</b> &mdash; <i>OK</i> or <i>Missing FP</i> with a warning icon</li>"
    "</ul>"
    "<p>Libraries with missing footprint references are highlighted in "
    "<span style='color:#CC7700;font-weight:bold'>orange</span>.</p>"
)

HELP_PAGES["selecting"] = _wrap(
    "<h2>Selecting Libraries</h2>"
    "<p>Checkboxes control which libraries are included when generating tables.</p>"
    "<ul>"
    "<li><b>Source group checkbox</b> &mdash; toggles all libraries in that source "
    "(tri-state: checked, unchecked, partial)</li>"
    "<li><b>Individual checkbox</b> &mdash; toggles a single library</li>"
    "<li><b>Select All / Deselect All</b> &mdash; toolbar buttons that affect "
    "everything</li>"
    "</ul>"
    "<h3>Right-click menu</h3>"
    "<p>Right-click on either tree for <b>Expand All</b> / <b>Collapse All</b>.</p>"
    '<p class="hint"><b>Note:</b> Footprint checkboxes are managed automatically '
    "by the footprint filter (see <i>Footprint Filter</i> section). You can still "
    "override them manually after the filter runs.</p>"
)

HELP_PAGES["generating"] = _wrap(
    "<h2>Generating Tables</h2>"
    "<ol>"
    "<li>Select the libraries you want to include</li>"
    "<li>Set the <b>Destination</b> folder (defaults to the repository root)</li>"
    "<li>Click <b>Generate Tables</b> (blue button) or press <code>Ctrl+G</code></li>"
    "</ol>"
    "<h3>What happens</h3>"
    "<ul>"
    "<li>Existing <code>sym-lib-table</code> and <code>fp-lib-table</code> are "
    "automatically backed up (e.g.&nbsp;<code>sym-lib-table_backup_1</code>)</li>"
    "<li>New table files are written with only the selected libraries</li>"
    "<li>Backup numbers increment automatically "
    "(<code>_backup_1</code>, <code>_backup_2</code>, ...)</li>"
    "</ul>"
    "<p>The log panel at the bottom confirms what was written.</p>"
)

HELP_PAGES["restoring"] = _wrap(
    "<h2>Restoring Backups</h2>"
    "<p>Open via <b>File &rarr; Restore Backup</b> or <code>Ctrl+R</code>.</p>"
    "<p>The restore dialog shows all available backup pairs. Each entry restores "
    "<b>both</b> the sym-lib-table and fp-lib-table together to ensure consistency.</p>"
    "<h3>Restore process</h3>"
    "<ol>"
    "<li>Select the folder containing your tables (defaults to the destination)</li>"
    "<li>The dialog lists all backup pairs found (e.g.&nbsp;<i>Backup #1</i>, "
    "<i>Backup #2</i>)</li>"
    "<li>Select a backup and click <b>Restore</b></li>"
    "<li>The current tables are backed up first, then the selected backup is "
    "restored</li>"
    "</ol>"
)

HELP_PAGES["filter"] = _wrap(
    "<h2>Footprint Filter</h2>"
    "<p>Footprint selection is <b>driven by symbols</b> &mdash; you don't need to "
    "manually check footprint libraries.</p>"
    "<h3>How it works</h3>"
    "<ol>"
    "<li>When you select or deselect symbols, the tool reads their footprint "
    "references</li>"
    "<li>It checks which footprint libraries are needed and automatically "
    "checks/unchecks them</li>"
    "<li>A footprint stays selected if <b>any</b> selected symbol from <b>any</b> "
    "source references it</li>"
    "</ol>"
    "<h3>Per-source scoping</h3>"
    "<p>The filter is <b>scoped per source</b>:</p>"
    "<ul>"
    "<li>Deselecting all <i>Custom</i> symbols only affects <i>Custom</i> "
    "footprints</li>"
    "<li>W&uuml;rth footprints remain untouched (and vice versa)</li>"
    "<li>This prevents cross-source interference</li>"
    "</ul>"
    '<p class="hint"><b>Tip:</b> You can manually override any footprint checkbox '
    "after the automatic filter runs. The override persists until the next symbol "
    "change triggers a re-filter.</p>"
)

HELP_PAGES["shortcuts"] = _wrap(
    "<h2>Keyboard Shortcuts</h2>"
    "<table>"
    "<tr><th>Shortcut</th><th>Action</th></tr>"
    "<tr><td><code>Ctrl+G</code></td><td>Generate Tables</td></tr>"
    "<tr><td><code>Ctrl+R</code></td><td>Restore Backup</td></tr>"
    "<tr><td><code>Ctrl+K</code></td><td>Set KiCad Footprint Path</td></tr>"
    "<tr><td><code>Ctrl+Q</code></td><td>Exit</td></tr>"
    "<tr><td><code>F1</code></td><td>Open this User Guide</td></tr>"
    "</table>"
)

HELP_PAGES["roadmap"] = _wrap(
    "<h2>Roadmap</h2>"
    "<ul>"
    "<li><b>Grow the library collection</b> &mdash; continue adding custom symbols "
    "and footprints for new components</li>"
    "<li><b>Standalone executable</b> &mdash; package with PyInstaller or Nuitka "
    "so no Python install is required</li>"
    "<li><b>KiCad plugin</b> &mdash; explore an Action Plugin launcher for "
    "seamless integration inside the KiCad PCB editor</li>"
    "</ul>"
    '<p>Contributions welcome on '
    '<a href="https://github.com/sylvanoMTL/kicad_libraries">'
    "GitHub</a>.</p>"
)


# ── TOC structure ─────────────────────────────────────────────────────

TOC_STRUCTURE: list[tuple[str, str, list[tuple[str, str]]]] = [
    # (key, label, children)
    ("overview", "Overview", []),
    ("_getting_started", "Getting Started", [
        ("requirements", "Requirements"),
        ("how_to_run", "How to Run"),
    ]),
    ("_on_launch", "On Launch", [
        ("kicad_detection", "KiCad Detection"),
        ("repo_scan", "Repository Scan"),
    ]),
    ("_how_to_use", "How to Use", [
        ("library_tree", "Library Tree"),
        ("selecting", "Selecting Libraries"),
        ("generating", "Generating Tables"),
        ("restoring", "Restoring Backups"),
    ]),
    ("filter", "Footprint Filter", []),
    ("shortcuts", "Keyboard Shortcuts", []),
    ("roadmap", "Roadmap", []),
]


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Guide — KiCad External Lib Manager")
        self.resize(860, 620)

        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: TOC tree
        self._toc = QTreeWidget()
        self._toc.setHeaderHidden(True)
        self._toc.setMinimumWidth(200)
        self._toc.setMaximumWidth(300)
        self._build_toc()
        self._toc.currentItemChanged.connect(self._on_topic_selected)
        splitter.addWidget(self._toc)

        # Right: content browser
        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        splitter.addWidget(self._browser)

        splitter.setSizes([240, 600])
        layout.addWidget(splitter)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        # Select first topic
        self._toc.setCurrentItem(self._toc.topLevelItem(0))

    def _build_toc(self):
        bold_font = self._toc.font()
        bold_font.setBold(True)

        for key, label, children in TOC_STRUCTURE:
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, key)
            if children:
                item.setFont(0, bold_font)
                for child_key, child_label in children:
                    child = QTreeWidgetItem([child_label])
                    child.setData(0, Qt.ItemDataRole.UserRole, child_key)
                    item.addChild(child)
                item.setExpanded(True)
            else:
                item.setFont(0, bold_font)
            self._toc.addTopLevelItem(item)

    def _on_topic_selected(self, current: QTreeWidgetItem | None, _previous):
        if current is None:
            return
        key = current.data(0, Qt.ItemDataRole.UserRole)
        if key in HELP_PAGES:
            self._browser.setHtml(HELP_PAGES[key])
        elif current.childCount() > 0:
            # Group header without own page — show first child
            first_child = current.child(0)
            child_key = first_child.data(0, Qt.ItemDataRole.UserRole)
            if child_key in HELP_PAGES:
                self._browser.setHtml(HELP_PAGES[child_key])
                self._toc.setCurrentItem(first_child)
