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
        self._fp_items: dict[str, QTreeWidgetItem] = {}  # nickname -> item
        self._updating = False

        self._sym_tree.itemChanged.connect(self._on_sym_item_changed)
        self._fp_tree.itemChanged.connect(self._on_fp_item_changed)

    def populate(self, scan_result: ScanResult):
        self._updating = True
        self._sym_tree.clear()
        self._fp_tree.clear()
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

                item = QTreeWidgetItem([
                    lib.nickname, source, fp_text,
                    "Missing FP" if has_missing else "OK"
                ])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, state)
                item.setData(0, Qt.ItemDataRole.UserRole, lib)
                if has_missing:
                    item.setIcon(3, warn_icon)
                    orange = QBrush(QColor("#CC7700"))
                    for col in range(item.columnCount()):
                        item.setForeground(col, orange)
                group.addChild(item)

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
                item = QTreeWidgetItem([lib.nickname, source, "OK"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, state)
                item.setData(0, Qt.ItemDataRole.UserRole, lib)
                group.addChild(item)
                self._fp_items[lib.nickname] = item

            group.setExpanded(True)

        self._updating = False

        # Apply footprint filter based on selected symbols
        sources = sorted(set(lib.source for lib in self._fp_libs))
        for source in sources:
            self._sync_footprint_selection(source)

    def _on_sym_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return

        # Update selected state for the changed item (and children if group)
        lib = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(lib, SymbolLibrary):
            lib.selected = item.checkState(0) == Qt.CheckState.Checked
        else:
            # Group header changed — update all children
            for i in range(item.childCount()):
                child = item.child(i)
                child_lib = child.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(child_lib, SymbolLibrary):
                    child_lib.selected = child.checkState(0) == Qt.CheckState.Checked

        # Determine which source was changed
        lib = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(lib, SymbolLibrary):
            source = lib.source
        else:
            source = item.text(0)  # Group header text is the source name

        # Recalculate footprints for that source only
        self._sync_footprint_selection(source)

    def _sync_footprint_selection(self, source: str):
        """Recalculate footprint check states for a given source.

        Only footprints belonging to the affected source are updated.
        A footprint is selected if at least one selected symbol references it.
        """
        needed = set()
        for lib in self._sym_libs:
            if lib.selected:
                for ref in lib.footprint_refs:
                    needed.add(ref.library_name)

        self._updating = True
        for nickname, fp_item in self._fp_items.items():
            fp_lib = fp_item.data(0, Qt.ItemDataRole.UserRole)
            if not fp_lib or fp_lib.source != source:
                continue  # Only manage footprints from the affected source
            should_check = nickname in needed
            state = Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
            fp_item.setCheckState(0, state)
            fp_lib.selected = should_check
        self._updating = False

    def _on_fp_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return
        lib = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(lib, FootprintLibrary):
            lib.selected = item.checkState(0) == Qt.CheckState.Checked

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

        # Set all symbols to the requested state
        for i in range(self._sym_tree.topLevelItemCount()):
            group = self._sym_tree.topLevelItem(i)
            group.setCheckState(0, state)
            for j in range(group.childCount()):
                child = group.child(j)
                child.setCheckState(0, state)
                lib = child.data(0, Qt.ItemDataRole.UserRole)
                if lib:
                    lib.selected = selected

        self._sym_tree.blockSignals(False)
        self._fp_tree.blockSignals(False)

        # Footprints are driven by the symbol filter
        sources = sorted(set(lib.source for lib in self._fp_libs))
        for source in sources:
            self._sync_footprint_selection(source)
