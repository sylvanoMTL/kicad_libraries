import html

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu, QHeaderView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont

from ..models import (
    STATUS_CHANGED, STATUS_NEW, ChangedFootprint, Finding, ScanResult, SymbolEntry,
    SymbolLibrary, FootprintLibrary, Violation,
)
from .theme import ACCENT, AMBER, HEADING_PT

_STATUS_WORD = {STATUS_NEW: "New", STATUS_CHANGED: "Changed"}
_STATUS_TIP = {
    STATUS_NEW: "New since the last Custom commit",
    STATUS_CHANGED: "Changed since the last Custom commit",
}


def _rich_tip(lines: list[str]) -> str:
    """Tooltip with one escaped line per entry, so vendor text is never read as markup."""
    return "<qt>" + "<br>".join(html.escape(line) for line in lines) + "</qt>"


class LibraryTableWidget(QWidget):
    # (library rel_path, symbol name) of a marked symbol row the user double-clicked
    symbol_activated = Signal(str, str)
    # (kind, library rel_path) of a library row the user asked to rescan; kind is "symbol" or "footprint"
    library_rescan_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._library_rescan_enabled = True
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Left: Symbols
        sym_col = QVBoxLayout()
        sym_label = QLabel("Symbols")
        sym_label.setFont(self._heading_font())
        sym_col.addWidget(sym_label)
        self._sym_tree = QTreeWidget()
        self._sym_tree.setHeaderLabels(["Library Name", "Source", "Linked Footprints", "Status"])
        sym_header = self._sym_tree.header()
        sym_header.setStretchLastSection(False)
        sym_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        sym_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        sym_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        sym_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._sym_tree.setColumnWidth(0, 240)
        self._sym_tree.setColumnWidth(1, 100)
        self._sym_tree.setAlternatingRowColors(True)
        self._sym_tree.setRootIsDecorated(True)
        self._sym_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._sym_tree.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self._sym_tree, pos)
        )
        sym_col.addWidget(self._sym_tree)
        layout.addLayout(sym_col, stretch=1)

        # Right: Footprints
        fp_col = QVBoxLayout()
        fp_label = QLabel("Footprints")
        fp_label.setFont(self._heading_font())
        fp_col.addWidget(fp_label)
        self._fp_tree = QTreeWidget()
        self._fp_tree.setHeaderLabels(["Library Name", "Source", "Status"])
        fp_header = self._fp_tree.header()
        fp_header.setStretchLastSection(False)
        fp_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        fp_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        fp_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._fp_tree.setColumnWidth(0, 240)
        self._fp_tree.setColumnWidth(1, 100)
        self._fp_tree.setAlternatingRowColors(True)
        self._fp_tree.setRootIsDecorated(True)
        self._fp_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._fp_tree.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(self._fp_tree, pos)
        )
        fp_col.addWidget(self._fp_tree)
        layout.addLayout(fp_col, stretch=1)

        self._sym_libs: list[SymbolLibrary] = []
        self._fp_libs: list[FootprintLibrary] = []
        self._sym_items: dict[str, QTreeWidgetItem] = {}  # rel_path -> item
        self._fp_items: dict[str, QTreeWidgetItem] = {}  # rel_path -> item
        self._updating = False

        self._sym_tree.itemChanged.connect(self._on_sym_item_changed)
        self._sym_tree.itemDoubleClicked.connect(self._on_sym_item_double_clicked)
        self._fp_tree.itemChanged.connect(self._on_fp_item_changed)

    @staticmethod
    def _heading_font() -> QFont:
        font = QFont()
        font.setPointSize(HEADING_PT)
        font.setBold(True)
        return font

    def populate(self, scan_result: ScanResult):
        previous = self._updating
        self._updating = True
        try:
            self._populate_trees(scan_result)
        finally:
            self._updating = previous

    def _populate_trees(self, scan_result: ScanResult):
        self._sym_tree.clear()
        self._fp_tree.clear()
        self._sym_items.clear()
        self._fp_items.clear()
        self._sym_libs = scan_result.symbol_libs
        self._fp_libs = scan_result.footprint_libs

        sources = sorted(set(
            [lib.source for lib in self._sym_libs] +
            [lib.source for lib in self._fp_libs]
        ))

        warn_icon = self.style().standardIcon(
            self.style().StandardPixmap.SP_MessageBoxWarning
        )
        info_icon = self.style().standardIcon(
            self.style().StandardPixmap.SP_MessageBoxInformation
        )

        bold_font = self._sym_tree.font()
        bold_font.setBold(True)

        # Populate symbols
        for source in sources:
            group = QTreeWidgetItem([source])
            group.setFlags(group.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            group.setCheckState(0, Qt.CheckState.Unchecked)
            group.setFont(0, bold_font)
            self._sym_tree.addTopLevelItem(group)

            for lib in self._sym_libs:
                if lib.source != source:
                    continue
                fp_text = ", ".join(
                    f"{r.library_name}:{r.footprint_name}" for r in lib.footprint_refs
                )
                has_missing = any(not r.found_in_repo for r in lib.footprint_refs)
                state = Qt.CheckState.Checked if lib.selected else Qt.CheckState.Unchecked
                failing = sum(1 for e in lib.symbols if e.failing) if lib.atomic else 0
                count_text = f"{failing} of {len(lib.symbols)} fail"
                count_tip = f"{failing} of {len(lib.symbols)} symbols fail the atomic check"
                if lib.collision_peers:
                    status = "Collision"
                elif lib.check_problem:
                    status = "Could not check"
                elif failing:
                    status = count_text
                elif has_missing:
                    status = "Missing FP"
                elif lib.atomic and not lib.symbols:
                    status = "No symbols"
                else:
                    status = "OK"

                item = QTreeWidgetItem([lib.nickname, source, fp_text, status])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, state)
                item.setData(0, Qt.ItemDataRole.UserRole, lib)
                if lib.collision_peers or has_missing or failing or lib.check_problem:
                    item.setIcon(3, warn_icon)
                    orange = QBrush(QColor(AMBER))
                    for col in range(item.columnCount()):
                        item.setForeground(col, orange)
                if lib.collision_peers:
                    tip = self._collision_tip(lib)
                    if has_missing:
                        tip += "; Missing FP"
                    if failing:
                        tip += "; " + count_tip
                    item.setToolTip(0, tip)
                    item.setToolTip(3, tip)
                elif lib.check_problem:
                    item.setToolTip(3, _rich_tip([lib.check_problem]))
                elif failing:
                    item.setToolTip(3, count_tip)
                else:
                    item.setToolTip(3, status)
                for entry in lib.symbols:
                    item.addChild(self._make_symbol_row(entry, warn_icon, info_icon))
                group.addChild(item)
                # Spanning only takes effect once the row is in the tree
                self._span_problem_rows(item)
                self._sym_items[lib.rel_path] = item
                # Open only libraries that have something to look at (the item must be in the tree first);
                # symbol rows stay collapsed so the library shows its component list
                if any(e.failing or e.status for e in lib.symbols):
                    item.setExpanded(True)

            group.setExpanded(True)

        # Populate footprints
        for source in sources:
            group = QTreeWidgetItem([source])
            group.setFlags(group.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            group.setCheckState(0, Qt.CheckState.Unchecked)
            group.setFont(0, bold_font)
            self._fp_tree.addTopLevelItem(group)

            for lib in self._fp_libs:
                if lib.source != source:
                    continue
                state = Qt.CheckState.Checked if lib.selected else Qt.CheckState.Unchecked
                item = QTreeWidgetItem([
                    lib.nickname, source, "Collision" if lib.collision_peers else "OK"
                ])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, state)
                item.setData(0, Qt.ItemDataRole.UserRole, lib)
                if lib.collision_peers:
                    item.setIcon(2, warn_icon)
                    orange = QBrush(QColor(AMBER))
                    for col in range(item.columnCount()):
                        item.setForeground(col, orange)
                    tip = self._collision_tip(lib)
                    item.setToolTip(0, tip)
                    item.setToolTip(2, tip)
                else:
                    item.setToolTip(2, "OK")
                for fp in lib.changed:
                    item.addChild(self._make_footprint_row(fp))
                group.addChild(item)
                self._fp_items[lib.rel_path] = item
                if lib.changed:
                    item.setExpanded(True)

            group.setExpanded(True)

        # Render the selected flags as given; footprint selection is never recomputed here

    @staticmethod
    def _make_symbol_row(entry: SymbolEntry, warn_icon, info_icon) -> QTreeWidgetItem:
        """Child row for one symbol: inert for selection, marked when new, changed or failing."""
        count = len(entry.violations)
        parts = []
        if entry.status in _STATUS_WORD:
            parts.append(_STATUS_WORD[entry.status])
        if count:
            parts.append("1 rule" if count == 1 else f"{count} rules")
        child = QTreeWidgetItem([entry.name, "", "", " · ".join(parts) or "OK"])
        child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        child.setData(0, Qt.ItemDataRole.UserRole, entry)
        # A failing symbol keeps the warning styling even when it is also new or changed
        if entry.failing:
            child.setIcon(3, warn_icon)
            LibraryTableWidget._colour_row(child, AMBER)
        elif entry.status in _STATUS_WORD:
            LibraryTableWidget._colour_row(child, ACCENT)
        lines = [v.text for v in entry.violations] + [f.text for f in entry.findings]
        if entry.status in _STATUS_TIP:
            lines.append(_STATUS_TIP[entry.status])
        if lines:
            tip = _rich_tip(lines)
            child.setToolTip(0, tip)
            child.setToolTip(3, tip)
        # One display-only row per broken rule, texts unchanged (G-09-1, D-01)
        for violation in entry.violations:
            child.addChild(LibraryTableWidget._make_problem_row(
                violation.text, violation, warn_icon, AMBER))
        # Then one plain row per note (leftover data, unknown manufacturer, ...)
        for finding in entry.findings:
            child.addChild(LibraryTableWidget._make_problem_row(
                finding.text, finding, info_icon, None))
        return child

    @staticmethod
    def _span_problem_rows(lib_item: QTreeWidgetItem) -> None:
        """Let problem and note rows use the full row width instead of the name column."""
        for i in range(lib_item.childCount()):
            symbol_row = lib_item.child(i)
            for j in range(symbol_row.childCount()):
                symbol_row.child(j).setFirstColumnSpanned(True)

    @staticmethod
    def _make_problem_row(text: str, data, icon, colour: str | None) -> QTreeWidgetItem:
        """Row for one broken rule or note under a symbol: display only, never checkable."""
        row = QTreeWidgetItem([text])
        row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        row.setData(0, Qt.ItemDataRole.UserRole, data)
        row.setIcon(0, icon)
        if colour is not None:
            LibraryTableWidget._colour_row(row, colour)
        row.setToolTip(0, _rich_tip([text]))
        return row

    @staticmethod
    def _make_footprint_row(fp: ChangedFootprint) -> QTreeWidgetItem:
        """Child row for one new or changed footprint: highlighted, inert for selection."""
        child = QTreeWidgetItem([fp.name, "", _STATUS_WORD.get(fp.status, "")])
        child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        child.setData(0, Qt.ItemDataRole.UserRole, fp)
        LibraryTableWidget._colour_row(child, ACCENT)
        if fp.status in _STATUS_TIP:
            tip = _rich_tip([_STATUS_TIP[fp.status]])
            child.setToolTip(0, tip)
            child.setToolTip(2, tip)
        return child

    @staticmethod
    def _colour_row(item: QTreeWidgetItem, colour: str) -> None:
        brush = QBrush(QColor(colour))
        for col in range(item.columnCount()):
            item.setForeground(col, brush)

    def reveal(self, sym_rel_path: str | None, fp_rel_path: str | None) -> None:
        """Expand, make current and scroll to the rows of one library in both trees; check states are not touched (D-16)"""
        previous = self._updating
        self._updating = True
        try:
            for tree, items, rel_path in (
                (self._sym_tree, self._sym_items, sym_rel_path),
                (self._fp_tree, self._fp_items, fp_rel_path),
            ):
                item = items.get(rel_path) if rel_path is not None else None
                if item is None:
                    continue
                parent = item.parent()
                if parent is not None:
                    parent.setExpanded(True)
                tree.setCurrentItem(item)
                tree.scrollToItem(item)
        finally:
            self._updating = previous

    def _on_sym_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return

        # Update selected state for the changed item (and children if group)
        lib = item.data(0, Qt.ItemDataRole.UserRole)
        # Symbol rows and their problem and note rows are display only; only library
        # rows and top-level group headers may change what gets selected
        if not isinstance(lib, SymbolLibrary) and item.parent() is not None:
            return
        checked_libs: list[SymbolLibrary] = []
        if isinstance(lib, SymbolLibrary):
            lib.selected = item.checkState(0) == Qt.CheckState.Checked
            source = lib.source
            checked_libs = [lib] if lib.selected else []
        else:
            # Group header changed — update all children
            source = item.text(0)  # Group header text is the source name
            for i in range(item.childCount()):
                child = item.child(i)
                child_lib = child.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(child_lib, SymbolLibrary):
                    child_lib.selected = child.checkState(0) == Qt.CheckState.Checked
                    if child_lib.selected:
                        checked_libs.append(child_lib)

        # A checked library displaces every same-nickname peer (an earlier
        # library of this change may already have displaced a later one)
        peer_sources: set[str] = set()
        for checked in checked_libs:
            if checked.selected:
                peer_sources |= self._uncheck_peers(checked, self._sym_items)

        # Recalculate footprints for the changed source and for sources that lost a
        # peer; the displaced sources go first so the footprints the new library
        # wants are no longer held back by a peer that is about to be released
        for peer_source in sorted(peer_sources - {source}):
            self._sync_footprint_selection(peer_source)
        self._sync_footprint_selection(source)

    def _on_sym_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Hand a symbol row, or one of its problem and note rows, to the check dialog."""
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(entry, (Violation, Finding)):
            # A problem or note row stands for its parent symbol (D-12)
            item = item.parent()
            if item is None:
                return
            entry = item.data(0, Qt.ItemDataRole.UserRole)
        parent = item.parent()
        if not isinstance(entry, SymbolEntry) or parent is None:
            return
        lib = parent.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(lib, SymbolLibrary):
            return
        if entry.violations or entry.findings:
            self.symbol_activated.emit(lib.rel_path, entry.name)

    def _collision_tip(self, lib) -> str:
        return f"Same nickname as {', '.join(lib.collision_peers)}; only one can be selected"

    def _peer_selected(self, lib, items: dict[str, QTreeWidgetItem]) -> bool:
        """True when any same-nickname peer of lib is currently selected."""
        for peer_path in lib.collision_peers:
            peer_item = items.get(peer_path)
            if peer_item is None:
                continue
            peer_lib = peer_item.data(0, Qt.ItemDataRole.UserRole)
            if peer_lib is not None and peer_lib.selected:
                return True
        return False

    def _uncheck_peers(self, lib, items: dict[str, QTreeWidgetItem]) -> set[str]:
        """Uncheck every selected peer of lib (item and model flag).

        Returns the sources of the peers that were unchecked.
        """
        sources: set[str] = set()
        previous = self._updating
        self._updating = True
        try:
            for peer_path in lib.collision_peers:
                peer_item = items.get(peer_path)
                if peer_item is None:
                    continue
                peer_lib = peer_item.data(0, Qt.ItemDataRole.UserRole)
                if peer_lib is None:
                    continue
                if peer_lib.selected or peer_item.checkState(0) != Qt.CheckState.Unchecked:
                    peer_item.setCheckState(0, Qt.CheckState.Unchecked)
                    peer_lib.selected = False
                    sources.add(peer_lib.source)
        finally:
            self._updating = previous
        return sources

    def _sync_footprint_selection(self, source: str):
        """Recalculate footprint check states for a given source.

        Only footprints belonging to the affected source are updated.
        A footprint is selected if at least one selected symbol of the same
        source references it and no same-nickname peer footprint is selected.
        """
        needed = set()
        for lib in self._sym_libs:
            if lib.source == source and lib.selected:
                for ref in lib.footprint_refs:
                    needed.add(ref.library_name)

        previous = self._updating
        self._updating = True
        try:
            for fp_item in self._fp_items.values():
                fp_lib = fp_item.data(0, Qt.ItemDataRole.UserRole)
                if not fp_lib or fp_lib.source != source:
                    continue  # Only manage footprints from the affected source
                should_check = (
                    fp_lib.nickname in needed
                    and not self._peer_selected(fp_lib, self._fp_items)
                )
                state = Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
                fp_item.setCheckState(0, state)
                fp_lib.selected = should_check
        finally:
            self._updating = previous

    def _on_fp_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return
        lib = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(lib, FootprintLibrary):
            lib.selected = item.checkState(0) == Qt.CheckState.Checked
            if lib.selected:
                self._uncheck_peers(lib, self._fp_items)

    def set_library_rescan_enabled(self, enabled: bool):
        """Enable or disable "Rescan this library" (off while a scan runs)."""
        self._library_rescan_enabled = enabled

    def _build_context_menu(self, tree: QTreeWidget, item: QTreeWidgetItem | None) -> QMenu:
        menu = QMenu(self)
        menu.addAction("Expand All", tree.expandAll)
        menu.addAction("Collapse All", tree.collapseAll)
        lib = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        # Library rows only: source group rows, symbol rows and problem rows hold other data
        if isinstance(lib, (SymbolLibrary, FootprintLibrary)):
            kind = "symbol" if isinstance(lib, SymbolLibrary) else "footprint"
            rel_path = lib.rel_path
            menu.addSeparator()
            action = menu.addAction("Rescan this library")
            action.setEnabled(self._library_rescan_enabled)
            action.triggered.connect(
                lambda _checked=False: self.library_rescan_requested.emit(kind, rel_path)
            )
        return menu

    def _show_context_menu(self, tree: QTreeWidget, pos):
        menu = self._build_context_menu(tree, tree.itemAt(pos))
        menu.exec(tree.viewport().mapToGlobal(pos))

    def select_all(self):
        self._set_all_check_state(Qt.CheckState.Checked)

    def deselect_all(self):
        self._set_all_check_state(Qt.CheckState.Unchecked)

    def _set_all_check_state(self, state: Qt.CheckState):
        selected = state == Qt.CheckState.Checked

        # Block signals to prevent stray itemChanged
        self._sym_tree.blockSignals(True)
        self._fp_tree.blockSignals(True)

        try:
            # Start from a clean slate so the outcome never depends on the old selection
            for i in range(self._sym_tree.topLevelItemCount()):
                group = self._sym_tree.topLevelItem(i)
                group.setCheckState(0, Qt.CheckState.Unchecked)
                for j in range(group.childCount()):
                    child = group.child(j)
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    lib = child.data(0, Qt.ItemDataRole.UserRole)
                    if lib:
                        lib.selected = False
            for fp_item in self._fp_items.values():
                fp_item.setCheckState(0, Qt.CheckState.Unchecked)
                fp_lib = fp_item.data(0, Qt.ItemDataRole.UserRole)
                if fp_lib:
                    fp_lib.selected = False

            # Check symbols in tree order (sources sorted, Custom first); a collided
            # library is only checked while none of its peers is selected
            if selected:
                for i in range(self._sym_tree.topLevelItemCount()):
                    group = self._sym_tree.topLevelItem(i)
                    for j in range(group.childCount()):
                        child = group.child(j)
                        lib = child.data(0, Qt.ItemDataRole.UserRole)
                        if lib and not self._peer_selected(lib, self._sym_items):
                            child.setCheckState(0, Qt.CheckState.Checked)
                            lib.selected = True
        finally:
            self._sym_tree.blockSignals(False)
            self._fp_tree.blockSignals(False)

        # Footprints are driven by the symbol filter
        sources = sorted(set(lib.source for lib in self._fp_libs))
        for source in sources:
            self._sync_footprint_selection(source)
