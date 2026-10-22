#!/usr/bin/env python3
"""Logitech Onboard Memory Manager for Linux.

Native GUI tool to view, edit, and flash button mappings and DPI settings
directly to the onboard flash memory of Logitech gaming mice.
"""

import sys
import os
from pathlib import Path

# Ensure local modules can be loaded when running standalone
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PyQt6 import QtWidgets, QtCore, QtGui
    except ImportError:
        print("Error: PySide6 or PyQt6 is required to run this application.")
        print("Install via: pip install PySide6 (or use your distribution package manager)")
        sys.exit(1)

from ui.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Logitech Onboard Memory Manager")
    app.setOrganizationName("LogitechLinux")


    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
