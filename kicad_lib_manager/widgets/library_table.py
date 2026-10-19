from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor

from ..models import ScanResult, SymbolLibrary, FootprintLibrary


class LibraryTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Left: Symbols
        sym_col = QVBoxLayout()
        sym_label = QLabel("Symbols")
        sym_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        sym_col.addWidget(sym_label)
        self._sym_tree = QTreeWidget()
        self._sym_tree.setHeaderLabels(["Library Name", "Source", "Linked Footprints", "Status"])
        self._sym_tree.setColumnWidth(0, 280)
        self._sym_tree.setColumnWidth(1, 130)
        self._sym_tree.setColumnWidth(2, 300)
        self._sym_tree.setColumnWidth(3, 60)
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
        fp_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        fp_col.addWidget(fp_label)
        self._fp_tree = QTreeWidget()
        self._fp_tree.setHeaderLabels(["Library Name", "Source", "Status"])
        self._fp_tree.setColumnWidth(0, 280)
        self._fp_tree.setColumnWidth(1, 130)
        self._fp_tree.setColumnWidth(2, 60)
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
        self._fp_tree.itemChanged.connect(self._on_fp_item_changed)

    def populate(self, scan_result: ScanResult):
        self._updating = True
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
                if lib.collision_peers:
                    status = "Collision"
                elif has_missing:
                    status = "Missing FP"
                else:
                    status = "OK"

                item = QTreeWidgetItem([lib.nickname, source, fp_text, status])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, state)
                item.setData(0, Qt.ItemDataRole.UserRole, lib)
                if lib.collision_peers or has_missing:
                    item.setIcon(3, warn_icon)
                    orange = QBrush(QColor("#CC7700"))
                    for col in range(item.columnCount()):
                        item.setForeground(col, orange)
                if lib.collision_peers:
                    tip = self._collision_tip(lib)
                    if has_missing:
                        tip += "; Missing FP"
                    item.setToolTip(0, tip)
                group.addChild(item)
                self._sym_items[lib.rel_path] = item

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
                    orange = QBrush(QColor("#CC7700"))
                    for col in range(item.columnCount()):
                        item.setForeground(col, orange)
                    item.setToolTip(0, self._collision_tip(lib))
                group.addChild(item)
                self._fp_items[lib.rel_path] = item

            group.setExpanded(True)

        # Render the selected flags as given; footprint selection is never recomputed here
        self._updating = False

    def _on_sym_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return

        # Update selected state for the changed item (and children if group)
        lib = item.data(0, Qt.ItemDataRole.UserRole)
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

    def _show_context_menu(self, tree: QTreeWidget, pos):
        menu = QMenu(self)
        menu.addAction("Expand All", tree.expandAll)
        menu.addAction("Collapse All", tree.collapseAll)
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
