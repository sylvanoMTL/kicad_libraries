from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ..models import ScanResult, SymbolLibrary, FootprintLibrary


class LibraryTableWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels([
            "Library Name", "Type", "Source", "Linked Footprints", "Status"
        ])
        self.setColumnWidth(0, 300)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 150)
        self.setColumnWidth(3, 350)
        self.setColumnWidth(4, 60)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.itemChanged.connect(self._on_item_changed)

        self._sym_libs: list[SymbolLibrary] = []
        self._fp_libs: list[FootprintLibrary] = []
        self._updating = False

    def populate(self, scan_result: ScanResult):
        self._updating = True
        self.clear()
        self._sym_libs = scan_result.symbol_libs
        self._fp_libs = scan_result.footprint_libs

        # Group by source
        sources = sorted(set(
            [lib.source for lib in self._sym_libs] +
            [lib.source for lib in self._fp_libs]
        ))

        warn_icon = self.style().standardIcon(
            self.style().StandardPixmap.SP_MessageBoxWarning
        )

        for source in sources:
            # Symbols group
            sym_group = QTreeWidgetItem([f"{source} - Symbols", "", source])
            sym_group.setFlags(sym_group.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            sym_group.setCheckState(0, Qt.CheckState.Checked)
            font = sym_group.font(0)
            font.setBold(True)
            sym_group.setFont(0, font)
            self.addTopLevelItem(sym_group)

            source_syms = [lib for lib in self._sym_libs if lib.source == source]
            for lib in source_syms:
                fp_text = ", ".join(
                    f"{r.library_name}:{r.footprint_name}" for r in lib.footprint_refs
                )
                has_missing = any(not r.found_in_repo for r in lib.footprint_refs)

                item = QTreeWidgetItem([
                    lib.nickname, "Symbol", source, fp_text,
                    "Missing FP" if has_missing else "OK"
                ])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked)
                item.setData(0, Qt.ItemDataRole.UserRole, ("sym", lib))
                if has_missing:
                    item.setIcon(4, warn_icon)
                sym_group.addChild(item)

            sym_group.setExpanded(True)

            # Footprints group
            fp_group = QTreeWidgetItem([f"{source} - Footprints", "", source])
            fp_group.setFlags(fp_group.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            fp_group.setCheckState(0, Qt.CheckState.Checked)
            fp_group.setFont(0, font)
            self.addTopLevelItem(fp_group)

            source_fps = [lib for lib in self._fp_libs if lib.source == source]
            for lib in source_fps:
                item = QTreeWidgetItem([
                    lib.nickname, "Footprint", source, "", "OK"
                ])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked)
                item.setData(0, Qt.ItemDataRole.UserRole, ("fp", lib))
                fp_group.addChild(item)

            fp_group.setExpanded(True)

        self._updating = False

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            lib_type, lib = data
            lib.selected = item.checkState(0) == Qt.CheckState.Checked

    def select_all(self):
        self._set_all_check_state(Qt.CheckState.Checked)

    def deselect_all(self):
        self._set_all_check_state(Qt.CheckState.Unchecked)

    def _set_all_check_state(self, state: Qt.CheckState):
        self._updating = True
        for i in range(self.topLevelItemCount()):
            group = self.topLevelItem(i)
            group.setCheckState(0, state)
            for j in range(group.childCount()):
                child = group.child(j)
                child.setCheckState(0, state)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data:
                    _, lib = data
                    lib.selected = state == Qt.CheckState.Checked
        self._updating = False
