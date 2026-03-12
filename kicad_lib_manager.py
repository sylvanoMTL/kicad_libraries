#!/usr/bin/env python3
"""KiCad Library Manager - PySide6 GUI for managing KiCad library tables."""

import sys
from PySide6.QtWidgets import QApplication
from kicad_lib_manager.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
