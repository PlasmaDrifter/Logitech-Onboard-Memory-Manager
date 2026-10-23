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


def run_daemon():
    """Runs the ProfileWatcher in headless background mode."""
    import time
    import signal
    from core.profile_watcher import ProfileWatcher

    watcher = ProfileWatcher()
    watcher.start()

    running = True

    def sig_handler(signum, frame):
        nonlocal running
        running = False
        watcher.stop()

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    try:
        while running:
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        watcher.stop()


def main():
    if "--daemon" in sys.argv:
        run_daemon()
        return

    try:
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
    except ImportError:
        from PyQt6.QtNetwork import QLocalServer, QLocalSocket

    server_name = f"logitech-omm-single-{os.getuid()}"

    # Single-instance check: check if an existing GUI instance is already running
    test_socket = QLocalSocket()
    test_socket.connectToServer(server_name)
    if test_socket.waitForConnected(300):
        # Existing instance is running: signal it to restore/focus its window, then exit
        test_socket.write(b"ACTIVATE\n")
        test_socket.flush()
        test_socket.waitForBytesWritten(300)
        test_socket.disconnectFromServer()
        sys.exit(0)

    # Clean up any stale server socket and listen for subsequent launches
    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    server.listen(server_name)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Logitech Onboard Memory Manager")
    app.setOrganizationName("LogitechLinux")

    window = MainWindow()
    window.show()

    def handle_client():
        client = server.nextPendingConnection()
        if client:
            client.waitForReadyRead(300)
            client.readAll()
            client.disconnectFromServer()
            window.present_to_user()

    server.newConnection.connect(handle_client)

    exit_code = app.exec()
    server.close()
    QLocalServer.removeServer(server_name)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
