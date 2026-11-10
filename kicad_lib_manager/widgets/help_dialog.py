import html
import re
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QSplitter, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)
from PySide6.QtCore import Qt, QTimer

from ..settings import load_help_topic, save_help_topic
from .import_dialog import (
    ADD_MODEL_TEXT, CHANGE_PACKAGE_TEXT, FINISHING_TEXT, HELP_ACTION_TEXT, OFFICIAL_FOOTPRINT_TEXT,
    REMOVE_MODEL_TEXT, VENDOR_FOOTPRINT_TEXT, fit_window,
)
from .theme import (
    ACCENT, AMBER, AMBER_TINT, BORDER, DISPLAY_PT, HEADING_PT, LINK, MONO_FAMILY, MONO_PT,
    SP_MD, SP_SM, SP_XS, SURFACE, SURFACE_HEADER,
)

# Every colour, size and gap comes from theme.py (UI-01); the body takes the application font and palette
CSS = "\n".join([
    f'body {{ font-family: "Segoe UI", Arial, sans-serif; margin: {SP_MD}px {SP_MD}px {SP_MD}px {SP_MD}px; '
    "line-height: 1.55; }",
    f"h2 {{ color: {LINK}; border-bottom: 2px solid {ACCENT}; padding-bottom: {SP_XS}px; "
    f"margin-top: {SP_SM}px; font-size: {DISPLAY_PT}pt; }}",
    f"h3 {{ margin-top: {SP_MD}px; font-size: {HEADING_PT}pt; }}",
    f"code {{ background: {SURFACE_HEADER}; padding: 0px {SP_XS}px; font-family: {MONO_FAMILY}; "
    f"font-size: {MONO_PT}pt; }}",
    f"pre {{ background: {SURFACE}; border-left: 3px solid {ACCENT}; padding: {SP_SM}px {SP_MD}px; "
    f"font-family: {MONO_FAMILY}; font-size: {MONO_PT}pt; }}",
    f"ul, ol {{ margin-left: {SP_SM}px; }}",
    f"li {{ margin-bottom: {SP_XS}px; }}",
    f"table {{ border-collapse: collapse; margin: {SP_SM}px 0px; }}",
    f"th, td {{ border: 1px solid {BORDER}; padding: {SP_XS}px {SP_SM}px; text-align: left; }}",
    f"th {{ background: {SURFACE_HEADER}; }}",
    f"a {{ color: {ACCENT}; }}",
    f".hint {{ background: {AMBER_TINT}; border-left: 3px solid {AMBER}; padding: {SP_SM}px {SP_MD}px; "
    f"margin: {SP_SM}px 0px; }}",
])


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
    "<p>Every scan is saved. At start the tool shows the last saved scan when no "
    "library file changed since it was saved, and the log says so. <b>Rescan</b> "
    "always runs the whole scan.</p>"
    "<p>While the libraries load, the <b>Loading Libraries</b> window shows a "
    "<b>Skip</b> button during the 3D model path check. It names the library source "
    "being checked, for example <b>Skip WurthElektronik</b>. Skip stops checking the "
    "3D model paths of that source only: its libraries are still listed and its "
    "symbols' footprint links are still read, so Generate Tables keeps them. The log "
    "says which source was skipped. The scan is saved with that note, and the next "
    "start says so until a Rescan checks everything again.</p>"
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
    "<li><b>Status</b> &mdash; <i>OK</i>, <i>Missing FP</i> or <i>Collision</i> "
    "(same nickname as another library; only one can be selected)</li>"
    "</ul>"
    "<p>Libraries with missing footprint references are highlighted in "
    f"<span style='color:{AMBER};font-weight:bold'>amber</span>.</p>"
    "<h3>Atomic parts</h3>"
    "<p>Libraries whose name starts with <code>Atomic_</code> show one row for each part. "
    f"A part that breaks an atomic rule is shown in <span style='color:{AMBER};font-weight:bold'>"
    "amber</span> with a warning icon, and its Status counts the rules it breaks, "
    "for example <i>Changed &middot; 2 rules</i>. "
    "The library row counts the parts that fail, for example <i>1 of 3 fail</i>.</p>"
    "<p>Parts start collapsed. Expand a part to see one row for each problem, in "
    f"<span style='color:{AMBER};font-weight:bold'>amber</span> with a warning icon, and "
    "one row for each note, such as leftover price or stock data, in plain text with an "
    "information icon. The tooltip of the part lists the same lines.</p>"
    "<p>Parts added or edited since the last Custom commit are marked "
    f"<span style='color:{ACCENT};font-weight:bold'>New</span> or "
    f"<span style='color:{ACCENT};font-weight:bold'>Changed</span> in the Status column. "
    "This works for every library in Custom, not only the atomic ones.</p>"
    "<p>To fix a marked part, double-click the part or one of its problem rows, or press "
    "<code>Ctrl+Shift+A</code>. "
    "<b>Check Atomic Parts</b> lists every problem and offers the safe fixes as ticked rows. "
    "You can type in a missing datasheet or description, or pick a missing 3D model. "
    "You see the exact changes before anything is written, and the libraries are scanned "
    "again afterwards.</p>"
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
    "<li>If <code>KICAD_LIB_GITHUB</code> or <code>CUSTOM_3DMODEL_DIR</code> in KiCad's "
    "settings needs to change, the app first checks whether KiCad is open, then shows the "
    "old and new values and asks. When KiCad is open, the question names the open KiCad "
    "programs and offers <b>Retry</b> (close KiCad first, then press it), "
    "<b>Change anyway</b> or <b>Not now</b>. After you answer, the app reads KiCad's "
    "settings again and changes only these two paths, so anything KiCad saved in the "
    "meantime is kept. Answering No or <b>Not now</b> leaves KiCad's settings unchanged "
    "while the tables are still written. "
    "When the app runs from a git worktree, or from a checkout other than the one "
    "<code>KICAD_LIB_GITHUB</code> points at, it never changes them and the log says "
    "why</li>"
    "<li>With an empty Destination box nothing is written, and the log says so</li>"
    "</ul>"
    "<p>The log panel at the bottom confirms what was written.</p>"
)

HELP_PAGES["importing"] = _wrap(
    "<h2>Importing Parts</h2>"
    "<p>Import a vendor package (Ultra Librarian, SnapEDA, SamacSys) into a "
    "<code>Custom/</code> library without editing any KiCad file by hand.</p>"
    "<h3>Start</h3>"
    "<p>Open <b>File &rarr; Import Part...</b> (<code>Ctrl+I</code>) or click the "
    "<b>Import Part...</b> toolbar button. You can also drop one <b>.zip</b> file or "
    "one <b>folder</b> onto the main window; the dialog then opens with that package "
    "loaded. The newest zip in your Downloads folder is offered, but it is never "
    "opened by itself.</p>"
    "<p><b>Cancel</b>, next to <b>Browse zip...</b> and <b>Browse folder...</b>, closes the import window "
    "without importing anything, and nothing is written. On the editing step <b>Cancel</b> sits at the "
    "bottom right, to the right of <b>Install Part</b>.</p>"
    "<p>The import window opens small for this step and grows to show the part once a package is open. "
    "It is sized to fit your screen and stays above the taskbar.</p>"
    "<p>Once a package is open, the button <b>" + CHANGE_PACKAGE_TEXT + "</b> at the top right "
    "closes it and goes back to this start step so you can pick another package. "
    "Your edits to the open package are dropped and nothing has been written.</p>"
    "<p>The import window has a toolbar at the top with <b>" + HELP_ACTION_TEXT + "</b>. Click it, or press "
    "<code>F1</code>, at every step (choosing a package, editing the part, the result) to open this page of "
    "the User Guide. The User Guide is its own window. It stays open beside the main window and the "
    "import window, so you can use either one while you read it, and it stays open when the import "
    "window closes.</p>"
    "<h3>Items</h3>"
    "<p>Pick the symbol, one footprint and the 3D model to import. When the package "
    "holds several footprints, only the one you pick is installed; the others are "
    "listed under <b>Not used</b> in the preview.</p>"
    "<p>SnapEDA ships the 3D model as a separate download. Click <b>" + ADD_MODEL_TEXT + "</b> "
    "on the 3D model row and pick the <code>.step</code>, <code>.stp</code> or "
    "<code>.wrl</code> file, or the <code>.zip</code> that holds it. The added model is "
    "checked like a package, and it shows in the preview before anything is written. "
    "If the file is not a usable 3D model, or a <code>.zip</code> holds any file that is not, "
    "nothing from it is added: the 3D model row shows why in red and <b>Install Part</b> "
    "stays blocked. Click <b>" + REMOVE_MODEL_TEXT + "</b> to clear it, or <b>" + ADD_MODEL_TEXT
    + "</b> to pick another file.</p>"
    "<h3>Target library</h3>"
    "<p>Every part goes into a library named <code>Atomic_</code> followed by the name of "
    "a KiCad library, for example <code>Atomic_Transistor_FET</code>. The name says what "
    "kind of part it is, so a part is easy to find next to KiCad's own.</p>"
    "<p>The app suggests a name. It looks first at similar parts in your own "
    "<code>Atomic_</code> libraries, then at similar parts in KiCad's libraries, and then "
    "at the vendor's category and the part's description. Hover the field: the tooltip "
    "says which of these gave the suggestion. When nothing fits, the field starts empty "
    "and waits for you.</p>"
    "<ul>"
    "<li>The list shows your <code>Atomic_</code> libraries first, then every other name "
    "that is allowed. Typing filters it.</li>"
    "<li>A KiCad library name on its own, such as <code>Transistor_FET</code>, is refused. "
    "So is a name that holds a maker, such as <code>Atomic_TI</code>, and so are the old "
    "library names. The strip under the field gives the reason and, where it can, the "
    "name to use instead.</li>"
    "<li>A wrong letter case is corrected when you leave the field, and a grey note "
    "says so.</li>"
    "<li>A new library creates only its <code>.kicad_sym</code> file. Its footprints go "
    "into the shared library described below.</li>"
    "</ul>"
    "<h3>Footprint</h3>"
    "<p>By default the vendor's footprint is installed into one shared library, "
    "<code>Atomic_Footprints</code>, and the symbol links to it as "
    "<code>Atomic_Footprints:</code> followed by the footprint name.</p>"
    "<p>To use a footprint that KiCad already ships, choose <b>" + OFFICIAL_FOOTPRINT_TEXT
    + "</b>. A list of KiCad's footprints appears, with the best matches for this part "
    "first, and typing filters it. The symbol then links to that official footprint. "
    "The vendor footprint and the vendor 3D model are not installed (the preview lists "
    "them under <b>Not used</b>), and KiCad's own 3D model is used. KiCad's own "
    "footprints are never changed. If the pads of the official footprint differ from the "
    "vendor's, a warning says so. Choose <b>" + VENDOR_FOOTPRINT_TEXT + "</b> to go back. "
    "When the official choice is greyed out, KiCad's footprints were not found; "
    "<b>Set KiCad Footprint Path</b> in the File menu fixes that.</p>"
    "<p>When <code>Atomic_Footprints</code> already holds a footprint of the same name:</p>"
    "<ul>"
    "<li>If the content is the same, it is reused and nothing is written.</li>"
    "<li>If the content differs, the <b>Conflicts</b> section asks you to choose "
    "<b>Overwrite</b>, <b>Rename</b> or <b>Skip</b> (see below). <b>Rename</b> suggests "
    "the footprint name followed by the MPN. <b>Overwrite</b> names the other parts that "
    "use that footprint, so you see what changes for them.</li>"
    "</ul>"
    "<h3>Fields</h3>"
    "<p>Edit the footprint name and the Datasheet, Description, Manufacturer "
    "and MPN fields. The Datasheet, Description and Manufacturer are required: while "
    "one is empty, its box says what to type and <b>Install Part</b> stays blocked "
    "(see Atomic check). The MPN cannot "
    "be empty. Value always equals the MPN, so it is shown but cannot be "
    "edited.</p>"
    "<p>The Manufacturer is written in its standard spelling: <i>TI</i> becomes "
    "<i>Texas Instruments</i>, and the preview lists the correction under the field "
    "changes. When the vendor gave no Manufacturer, it is taken from the Datasheet link "
    "if the company is known.</p>"
    "<p>Three texts are filled in for you: <b>Keywords</b>, <b>Footprint description</b> "
    "and <b>Footprint tags</b>. They are what KiCad's symbol and footprint choosers "
    "search and show. You can edit each one. The small button next to it, whose tooltip "
    "starts with <i>Regenerate</i>, writes it again from the part's details and drops "
    "your edit.</p>"
    "<h3>Atomic check</h3>"
    "<p><b>Install Part</b> stays blocked until the part passes the atomic check. The part "
    "needs an MPN, a Manufacturer, a footprint that exists, a Value equal to the MPN, a "
    "Datasheet link, a Description and a 3D model.</p>"
    "<p>The amber strip lists each problem on its own line. Click a problem to jump to the "
    "field that fixes it. A problem clears as soon as you type a valid value. "
    "A missing 3D model is fixed with <b>" + ADD_MODEL_TEXT + "</b> or by choosing <b>"
    + OFFICIAL_FOOTPRINT_TEXT + "</b>, which brings KiCad's own 3D model.</p>"
    "<h3>Conflicts</h3>"
    "<p>When an item already exists in the library, each conflict is its own row in "
    "the <b>Conflicts</b> section, with <b>Overwrite</b>, <b>Rename</b> and "
    "<b>Skip</b>. None is chosen at first, and <b>Install Part</b> stays blocked "
    "until every row has a choice. There is no overwrite-all.</p>"
    "<ul>"
    "<li><b>Overwrite</b> replaces the existing item and keeps a backup of the "
    "replaced file.</li>"
    "<li><b>Rename</b> installs the new item under the name you type in the row.</li>"
    "<li><b>Skip</b> keeps the existing item and links it instead.</li>"
    "</ul>"
    "<p>Double-click a conflict row to compare the existing file with the incoming "
    "one. While that comparison is being prepared, <b>Install Part</b> waits, and it "
    "becomes available again when the comparison is ready.</p>"
    "<h3>Install and result</h3>"
    "<p>Nothing is written until you click <b>Install Part</b>. <b>Cancel</b>, to its "
    "right, closes the dialog without installing anything, the same as the window's "
    "close button. While it installs, your choices are locked, a progress bar shows "
    "each step, <b>Cancel</b> is greyed out, and the dialog cannot be closed or "
    "cancelled.</p>"
    "<p>The preview is rebuilt in the background when you edit a field. If you press "
    "<b>" + CHANGE_PACKAGE_TEXT + "</b>, pick another package or close the dialog while it is still being "
    "built, the dialog greys out and a strip at the bottom reads <b>" + FINISHING_TEXT
    + "</b> The window stays live. The dialog then carries on by itself once the preview "
    "is ready: it returns to the start page, opens the other package, or closes. Press "
    "<b>Cancel</b> to stay where you are. After 10 seconds the strip adds that "
    "the KiCad command-line tool is slow to respond; it gives up after 60 seconds.</p>"
    "<p>If the install fails, the dialog returns to the preview with a red banner "
    "that lists the reasons. Every file is restored; if a restore itself fails, the "
    "banner names the backup folder that holds the original files. Fix the problem "
    "and click <b>Install Part</b> again.</p>"
    "<p>A successful install shows the result: <b>Warnings</b> (or <i>No warnings.</i>), "
    "the <b>Library list</b> and <b>Library tables</b> rows, "
    "<b>Files written</b> (double-click a file to view it) and the "
    "<b>Backup folder</b> with an <b>Open folder</b> button. "
    "When KiCad is running, a notice asks you to reopen KiCad's "
    "Symbol and Footprint editors to see the library.</p>"
    "<h3>Commit</h3>"
    "<p>After a successful install, the result also shows a Commit step. It names the "
    "Custom branch, the parent repo and its branch, and lists <b>Files to commit</b>: "
    "exactly the files the install wrote. None can be left out. The commit message is "
    "editable and already records the vendor, the package file name and the date.</p>"
    "<ul>"
    "<li><b>Also commit the Custom ref in the parent repo</b> is ticked by default. The "
    "message for the parent commit is generated and shown.</li>"
    "<li>Amber files also contain uncommitted changes made before this import. They are "
    "committed too. Double-click one to see what it held.</li>"
    "<li>Other changes in Custom stay uncommitted.</li>"
    "<li>A part that breaks the atomic rule stops the commit. The panel names the part "
    "and the rule, and <b>Commit</b> stays off. <b>Open Check Atomic Parts…</b> opens the "
    "check on that part so you can fix it. <b>Check again</b> then takes the files as they "
    "are now: a file changed after the install is marked \"changed since install\", and a "
    "footprint or 3D model that a committed part links but that is not committed yet is "
    "added and marked \"added: linked by a committed part\". Parts "
    "that already failed before the import are listed but do not stop the commit. Check "
    "again never commits; you still click <b>Commit</b>.</li>"
    "<li>When Custom is on a detached HEAD that sits on the history of main, "
    "<b>Switch to main</b> is offered. Any other detached HEAD is refused, and so is a "
    "local main that is behind origin/main.</li>"
    "<li>The hooks of both repos always run.</li>"
    "<li>Your work is never pushed. The result says how many commits each branch is "
    "ahead of its remote.</li>"
    "</ul>"
    "<p>Click <b>Commit</b> to commit. While Commit or Switch to main runs, the dialog "
    "and the main window cannot be closed; they can be closed while the first check "
    "runs. If you close the dialog without committing, the files stay "
    "uncommitted and the log says so.</p>"
    "<h3>Library tables</h3>"
    "<p>After installing, the library list rescans and selects the library. A new "
    "library is added to <code>sym-lib-table</code> and <code>fp-lib-table</code> "
    "without changing any other entry. An existing library that is missing from the "
    "tables shows a hint to press <b>Generate Tables</b>.</p>"
    "<p>If an entry the app added earlier under the same name points at a library that "
    "no longer exists, it is pointed at the installed library, after a backup of the "
    "table. A name that already points at another library that exists, or at an entry "
    "you added by hand, is left alone and a warning says so. With an empty Destination "
    "box no table is written.</p>"
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
    "<tr><td><code>Ctrl+I</code></td><td>Import Part</td></tr>"
    "<tr><td><code>Ctrl+G</code></td><td>Generate Tables</td></tr>"
    "<tr><td><code>Ctrl+R</code></td><td>Restore Backup</td></tr>"
    "<tr><td><code>Ctrl+Shift+R</code></td><td>Rescan Libraries</td></tr>"
    "<tr><td><code>Ctrl+Shift+A</code></td><td>Check Atomic Parts</td></tr>"
    "<tr><td><code>Ctrl+K</code></td><td>Set KiCad Footprint Path</td></tr>"
    "<tr><td><code>Ctrl+Q</code></td><td>Exit</td></tr>"
    "<tr><td><code>F1</code></td><td>Open the User Guide in its own window, which stays open beside the other windows. "
    "In the import window it opens on Importing Parts, the same as <b>" + HELP_ACTION_TEXT
    + "</b> on that window's toolbar.</td></tr>"
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
        ("importing", "Importing Parts"),
        ("restoring", "Restoring Backups"),
    ]),
    ("filter", "Footprint Filter", []),
    ("shortcuts", "Keyboard Shortcuts", []),
    ("roadmap", "Roadmap", []),
]


# ── Menu outline ──────────────────────────────────────────────────────

_H2_RE = re.compile(r"<h2>")
_H3_RE = re.compile(r"<h3>(.*?)</h3>", re.DOTALL)


@dataclass(frozen=True)
class HelpEntry:
    """One row of the User Guide menu: a group, a page, or a section of a page."""

    key: str
    number: str
    label: str
    parent: str | None  # the parent entry's key, None at top level
    page: str | None  # the HELP_PAGES key this entry shows, None for a group
    anchor: str | None = None  # set for sections only

    @property
    def text(self) -> str:
        return f"{self.number} {self.label}"


def section_anchor(label: str) -> str:
    """The anchor name of a heading: lower case, every run of other characters one hyphen, ends trimmed."""
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def page_sections(key: str) -> list[tuple[str, str]]:
    """The (anchor, label) pairs of a page's <h3> headings, in page order. The page text is the only source."""
    sections = []
    for inner in _H3_RE.findall(HELP_PAGES[key]):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", inner))).strip()
        sections.append((section_anchor(label), label))
    return sections


def help_outline() -> list[HelpEntry]:
    """Every menu row in menu order, numbered from its place: 1, 4.4, 4.4.7."""
    outline: list[HelpEntry] = []

    def add(key: str, number: str, label: str, parent: str | None, is_page: bool) -> None:
        outline.append(HelpEntry(key, number, label, parent, key if is_page else None))
        if is_page:
            for n, (anchor, section) in enumerate(page_sections(key), 1):
                outline.append(HelpEntry(f"{key}#{anchor}", f"{number}.{n}", section, key, key, anchor))

    for i, (key, label, children) in enumerate(TOC_STRUCTURE, 1):
        add(key, str(i), label, None, key in HELP_PAGES)
        for j, (child_key, child_label) in enumerate(children, 1):
            add(child_key, f"{i}.{j}", child_label, key, child_key in HELP_PAGES)
    return outline


def render_page(key: str) -> str:
    """A page's HTML with its menu number before the title and each section heading, and an anchor per section.

    The anchor is an empty named anchor before the heading text, never a wrapper around it: a wrapper would
    take the stylesheet's link colour. HELP_PAGES itself stays unnumbered.
    """
    numbers = {entry.key: entry.number for entry in help_outline()}
    page = HELP_PAGES[key]
    page = _H2_RE.sub(f"<h2>{numbers[key]} ", page, count=1)
    sections = iter(enumerate(page_sections(key), 1))

    def number_section(match: re.Match) -> str:
        n, (anchor, _label) = next(sections)
        return f'<h3><a name="{anchor}"></a>{numbers[key]}.{n} {match.group(1)}</h3>'

    return _H3_RE.sub(number_section, page)


class HelpDialog(QDialog):
    def __init__(self, parent=None, *, topic: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("User Guide — KiCad External Lib Manager")
        self.resize(860, 620)
        self._page_key: str | None = None  # the page the browser shows
        self._quiet = 0  # above 0 while the code, not the owner, moves the selection; such moves are not saved
        self._on_asked_topic = False  # True while a caller's topic is shown and the owner has not chosen since
        self._entries = {entry.key: entry for entry in help_outline()}

        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: TOC tree
        self._toc = QTreeWidget()
        self._toc.setHeaderHidden(True)
        self._toc.setMinimumWidth(200)
        self._toc.setMaximumWidth(300)
        self._build_toc()
        self._toc.currentItemChanged.connect(self._on_topic_selected)
        self._toc.itemClicked.connect(self._on_item_clicked)
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

        # Open on the asked topic, else where the owner left off; the first topic when neither is known
        if topic is None:
            self.show_remembered()
        else:
            self._quiet += 1
            try:
                if not self.show_topic(topic):
                    self._toc.setCurrentItem(self._toc.topLevelItem(0))
            finally:
                self._quiet -= 1

    def showEvent(self, event):
        super().showEvent(event)
        # Bounded by the screen's free area and moved fully inside it, however the guide is opened
        fit_window(self, self.size())
        # The browser applies a pending anchor in its own show, before this showEvent, and fit_window can then
        # narrow the guide and reflow the page under that scroll; a reused guide also keeps its old scroll.
        # A spontaneous show (restored from the taskbar) is skipped, so a page being read does not jump.
        if not event.spontaneous():
            self._show_current_heading()
            QTimer.singleShot(0, self, self._show_current_heading)

    def show_remembered(self) -> None:
        """Show the place the owner last chose, quietly: the saved key, else its page, else the first menu item."""
        saved = load_help_topic()
        self._quiet += 1
        try:
            if saved is None or not (self.show_topic(saved) or self.show_topic(saved.partition("#")[0])):
                self._toc.setCurrentItem(self._toc.topLevelItem(0))
        finally:
            self._quiet -= 1
        self._on_asked_topic = False

    def shows_asked_topic(self) -> bool:
        """True while the guide shows a topic a caller asked for and the owner has not chosen a place since."""
        return self._on_asked_topic

    def _show_current_heading(self) -> None:
        """Bring the current menu entry's heading into view: a section to its anchor, a page to its title."""
        current = self._toc.currentItem()
        if current is None:
            return
        entry = self._entries.get(current.data(0, Qt.ItemDataRole.UserRole))
        if entry is None or entry.page is None:
            return
        if entry.anchor is not None:
            self._browser.scrollToAnchor(entry.anchor)
        else:
            self._browser.verticalScrollBar().setValue(0)

    def show_topic(self, key: str) -> bool:
        """Select the topic with this key and show its page; False (nothing changes) when there is none.

        A topic shown this way is not remembered; only the owner's own moves in the menu are.
        """
        self._quiet += 1
        try:
            stack = [self._toc.topLevelItem(i) for i in range(self._toc.topLevelItemCount())]
            while stack:
                item = stack.pop(0)
                if item.data(0, Qt.ItemDataRole.UserRole) == key:
                    self._toc.setCurrentItem(item)
                    self._sync_expansion()
                    self._toc.scrollToItem(item)
                    # The item may already be current, so no currentItemChanged runs _on_topic_selected; this is
                    # the path of show_remembered on a reused guide
                    self._show_current_heading()
                    self._on_asked_topic = True
                    return True
                stack.extend(item.child(i) for i in range(item.childCount()))
            return False
        finally:
            self._quiet -= 1

    def _build_toc(self):
        bold_font = self._toc.font()
        bold_font.setBold(True)

        items = self._items = {}
        for entry in self._entries.values():
            item = QTreeWidgetItem([entry.text])
            item.setData(0, Qt.ItemDataRole.UserRole, entry.key)
            items[entry.key] = item
            if entry.parent is None:
                item.setFont(0, bold_font)
                self._toc.addTopLevelItem(item)
            else:
                items[entry.parent].addChild(item)
        for entry in self._entries.values():
            if entry.page is None:
                items[entry.key].setExpanded(True)

    def _on_topic_selected(self, current: QTreeWidgetItem | None, _previous):
        if current is None:
            return
        entry = self._entries.get(current.data(0, Qt.ItemDataRole.UserRole))
        if entry is None:
            return
        if entry.page is None:
            # Group header without own page: show its first child
            if current.childCount() > 0:
                self._toc.setCurrentItem(current.child(0))
            return
        if entry.anchor is None or entry.page != self._page_key:
            self._browser.setHtml(render_page(entry.page))
            self._page_key = entry.page
        if entry.anchor is not None:
            self._browser.scrollToAnchor(entry.anchor)
        # Saved on every owner move, not on close: Escape and a deleted parent fire no close event
        if not self._quiet:
            save_help_topic(entry.key)
            self._on_asked_topic = False
        # Folding rows under a pressed mouse button clears the selection, so a click waits for the event loop
        QTimer.singleShot(0, self, self._sync_expansion)

    def _sync_expansion(self):
        """Open the sections of the page shown and fold the other pages' sections, so the menu stays short.

        Groups keep their state.
        """
        for entry in self._entries.values():
            if entry.page == entry.key and self._items[entry.key].childCount() > 0:
                self._items[entry.key].setExpanded(entry.key == self._page_key)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int):
        # A click on the current item emits no currentItemChanged, so scroll back to the section here
        entry = self._entries.get(item.data(0, Qt.ItemDataRole.UserRole))
        if entry is not None and entry.anchor is not None and item is self._toc.currentItem():
            self._browser.scrollToAnchor(entry.anchor)
