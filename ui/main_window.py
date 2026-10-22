"""Main Window for Logitech Onboard Memory GUI."""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from core.backend import MouseBackend, get_backup_dir
from core.models import OnboardConfig, Profile, ButtonAction
from core.keycodes import G502_BUTTON_LABELS
from ui.button_editor_dialog import ButtonEditorDialog


class WorkerThread(QtCore.QThread):
    finished_signal = QtCore.Signal(bool, str)

    def __init__(self, target_fn, *args):
        super().__init__()
        self.target_fn = target_fn
        self.args = args
        self.result_obj = None

    def run(self):
        try:
            res = self.target_fn(*self.args)
            if isinstance(res, tuple) and len(res) == 2:
                first, second = res
                if isinstance(first, bool):
                    success = first
                    msg = str(second)
                else:
                    self.result_obj = first
                    success = first is not None
                    msg = str(second)
                self.finished_signal.emit(success, msg)
            else:
                self.result_obj = res
                self.finished_signal.emit(True, "Success")
        except Exception as e:
            self.result_obj = None
            self.finished_signal.emit(False, str(e))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.backend = MouseBackend("G502")
        self.config: Optional[OnboardConfig] = None
        self.current_gshift_mode = False

        self.setWindowTitle("Logitech Onboard Memory Manager")
        self.resize(880, 680)

        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self._setup_styling()
        self._init_ui()

        # Initial read from mouse
        QtCore.QTimer.singleShot(200, self.on_read_from_mouse)

    def _setup_styling(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e24;
                color: #e0e0e0;
            }
            QWidget {
                color: #e0e0e0;
                font-family: 'Inter', 'Segoe UI', 'Noto Sans', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #33333e;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 16px;
                font-weight: bold;
                background-color: #24242c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #3b82f6;
            }
            QTabWidget::pane {
                border: 1px solid #33333e;
                border-radius: 6px;
                background-color: #24242c;
            }
            QTabBar::tab {
                background: #18181c;
                color: #9ca3af;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #24242c;
                color: #ffffff;
                font-weight: bold;
                border-bottom: 2px solid #3b82f6;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 7px 16px;
                font-weight: 5px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton#secondaryBtn {
                background-color: #33333e;
                color: #e0e0e0;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #3f3f4e;
            }
            QPushButton#dangerBtn {
                background-color: #dc2626;
            }
            QPushButton#dangerBtn:hover {
                background-color: #b91c1c;
            }
            QTableWidget {
                background-color: #1a1a20;
                gridline-color: #2e2e38;
                border: 1px solid #33333e;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #18181c;
                color: #9ca3af;
                padding: 6px;
                border: 1px solid #2e2e38;
                font-weight: bold;
            }
            QComboBox, QSpinBox {
                background-color: #1a1a20;
                border: 1px solid #3f3f4e;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
            }
        """)

    def _init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header bar
        header_layout = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        self.device_title = QtWidgets.QLabel("Logitech G502 X PLUS")
        self.device_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        self.device_status = QtWidgets.QLabel("Status: Checking device...")
        self.device_status.setStyleSheet("color: #9ca3af; font-size: 12px;")
        title_box.addWidget(self.device_title)
        title_box.addWidget(self.device_status)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Action Buttons in Header
        self.btn_read = QtWidgets.QPushButton("Read from Mouse")
        self.btn_read.setObjectName("secondaryBtn")
        self.btn_read.clicked.connect(self.on_read_from_mouse)
        header_layout.addWidget(self.btn_read)

        self.btn_apply = QtWidgets.QPushButton("Apply to Mouse")
        self.btn_apply.clicked.connect(self.on_apply_to_mouse)
        header_layout.addWidget(self.btn_apply)

        main_layout.addLayout(header_layout)

        # Profile Tabs
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget, stretch=1)

        # Bottom Bar: Mode, Backups & Status
        bottom_layout = QtWidgets.QHBoxLayout()

        self.btn_activate_profile = QtWidgets.QPushButton("Set Profile as Active on Mouse")
        self.btn_activate_profile.setObjectName("secondaryBtn")
        self.btn_activate_profile.clicked.connect(self.on_set_active_profile)
        bottom_layout.addWidget(self.btn_activate_profile)

        self.btn_open_backups = QtWidgets.QPushButton("Open Backups Folder")
        self.btn_open_backups.setObjectName("secondaryBtn")
        self.btn_open_backups.clicked.connect(self.on_open_backups)
        bottom_layout.addWidget(self.btn_open_backups)

        self.btn_turn_off_rgb = QtWidgets.QPushButton("Turn Off RGB Lighting")
        self.btn_turn_off_rgb.setObjectName("secondaryBtn")
        self.btn_turn_off_rgb.clicked.connect(self.on_turn_off_lighting)
        bottom_layout.addWidget(self.btn_turn_off_rgb)

        self.qsettings = QtCore.QSettings("LogitechLinux", "OnboardMemoryManager")
        auto_off_saved = self.qsettings.value("auto_turn_off_rgb", True, type=bool)
        self.chk_auto_turn_off_rgb = QtWidgets.QCheckBox("Auto-turn off RGB on save")
        self.chk_auto_turn_off_rgb.setChecked(auto_off_saved)
        self.chk_auto_turn_off_rgb.toggled.connect(
            lambda val: self.qsettings.setValue("auto_turn_off_rgb", val)
        )
        bottom_layout.addWidget(self.chk_auto_turn_off_rgb)

        bottom_layout.addStretch()

        self.lbl_active_info = QtWidgets.QLabel("Active Profile: -")
        self.lbl_active_info.setStyleSheet("color: #10b981; font-weight: bold;")
        bottom_layout.addWidget(self.lbl_active_info)

        main_layout.addLayout(bottom_layout)

    def on_turn_off_lighting(self):
        self.device_status.setText("Shutting off mouse RGB LEDs...")
        success, msg = self.backend.turn_off_lighting()
        if success:
            self.device_status.setText(msg)
            QtWidgets.QMessageBox.information(self, "Lighting Off", msg)
        else:
            QtWidgets.QMessageBox.warning(self, "Lighting", f"Could not turn off lighting:\n{msg}")

    def on_read_from_mouse(self):
        self.device_status.setText("Reading configuration from mouse...")
        self.btn_read.setEnabled(False)
        self.btn_apply.setEnabled(False)

        self.worker = WorkerThread(self.backend.read_profiles)
        self.worker.finished_signal.connect(self._on_read_finished)
        self.worker.start()

    def _on_read_finished(self, success: bool, msg: str):
        self.btn_read.setEnabled(True)
        self.btn_apply.setEnabled(True)

        config = getattr(self.worker, "result_obj", None)
        if not success or not config:
            self.device_status.setText(f"Error: {msg}")
            QtWidgets.QMessageBox.warning(self, "Read Error", f"Could not read from mouse:\n\n{msg}")
            return

        self.config = config
        self.device_title.setText(f"{config.device_name} (Onboard Memory)")
        self.device_status.setText("Connected and synchronized.")
        self.lbl_active_info.setText(f"Active Profile on Mouse: Profile {config.active_profile_id}")
        self._rebuild_tabs()

    def _get_tab_label(self, prof: Profile) -> str:
        label = f"Profile {prof.profile_id}"
        if self.config and prof.profile_id == self.config.active_profile_id:
            label += " (Active)"
        elif prof.enabled:
            label += " (Enabled)"
        else:
            label += " (Disabled)"
        return label

    def _rebuild_tabs(self):
        if not self.config:
            return

        curr_tab = self.tab_widget.currentIndex()
        self.tab_widget.clear()

        for pid in sorted(self.config.profiles.keys()):
            prof = self.config.profiles[pid]
            tab = self._create_profile_tab(prof)
            tab.profile_id = pid
            label = self._get_tab_label(prof)
            self.tab_widget.addTab(tab, label)

        if 0 <= curr_tab < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(curr_tab)

    def _create_profile_tab(self, prof: Profile) -> QtWidgets.QWidget:
        tab = QtWidgets.QWidget()
        tab.profile_id = prof.profile_id
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Profile Settings Header Row
        settings_box = QtWidgets.QHBoxLayout()

        chk_enabled = QtWidgets.QCheckBox("Enable Profile in Mouse Memory")
        chk_enabled.setChecked(bool(prof.enabled))
        chk_enabled.toggled.connect(lambda val, p=prof: self._on_profile_enabled_toggled(p, val))
        settings_box.addWidget(chk_enabled)

        settings_box.addSpacing(20)

        # Report Rate
        settings_box.addWidget(QtWidgets.QLabel("Report Rate:"))
        combo_rate = QtWidgets.QComboBox()
        rate_map = {1: "1000 Hz (1ms)", 2: "500 Hz (2ms)", 4: "250 Hz (4ms)", 8: "125 Hz (8ms)"}
        for code, text in rate_map.items():
            combo_rate.addItem(text, code)
        idx = combo_rate.findData(prof.report_rate)
        if idx >= 0:
            combo_rate.setCurrentIndex(idx)
        combo_rate.currentIndexChanged.connect(lambda idx, p=prof, cb=combo_rate: self._on_rate_changed(p, cb.currentData()))
        settings_box.addWidget(combo_rate)

        settings_box.addStretch()

        # G-Shift Mode Toggle for button view
        lbl_mode = QtWidgets.QLabel("Button Mode:")
        settings_box.addWidget(lbl_mode)
        btn_std = QtWidgets.QRadioButton("Standard")
        btn_gshift = QtWidgets.QRadioButton("G-Shift")
        btn_std.setChecked(not self.current_gshift_mode)
        btn_gshift.setChecked(self.current_gshift_mode)
        btn_std.toggled.connect(lambda val: self._on_mode_toggle(val, tab, prof))
        settings_box.addWidget(btn_std)
        settings_box.addWidget(btn_gshift)

        layout.addLayout(settings_box)

        # DPI Group Box
        dpi_group = QtWidgets.QGroupBox("DPI Sensitivity Stages")
        dpi_layout = QtWidgets.QHBoxLayout(dpi_group)
        for i in range(len(prof.resolutions)):
            stage_box = QtWidgets.QVBoxLayout()
            stage_lbl = QtWidgets.QLabel(f"Stage {i+1}:")
            spin_dpi = QtWidgets.QSpinBox()
            spin_dpi.setRange(100, 25600)
            spin_dpi.setSingleStep(50)
            spin_dpi.setValue(prof.resolutions[i])
            spin_dpi.valueChanged.connect(lambda val, p=prof, idx=i: self._on_dpi_changed(p, idx, val))

            radio_default = QtWidgets.QRadioButton("Default")
            radio_default.setChecked(prof.resolution_default_index == i)
            radio_default.toggled.connect(lambda val, p=prof, idx=i: self._on_default_dpi_toggled(p, idx, val))

            stage_box.addWidget(stage_lbl)
            stage_box.addWidget(spin_dpi)
            stage_box.addWidget(radio_default)
            dpi_layout.addLayout(stage_box)
        layout.addWidget(dpi_group)

        # Buttons Table
        table = QtWidgets.QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Physical Button", "Mapped Action", "Action"])
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self._populate_button_table(table, prof)
        layout.addWidget(table, stretch=1)

        # Store reference on tab
        tab.table_widget = table

        return tab

    def _populate_button_table(self, table: QtWidgets.QTableWidget, prof: Profile):
        buttons = prof.gbuttons if self.current_gshift_mode else prof.buttons
        table.setRowCount(len(buttons))

        for row, action in enumerate(buttons):
            b_num = row + 1
            label = G502_BUTTON_LABELS.get(b_num, f"Button {b_num}")

            item_label = QtWidgets.QTableWidgetItem(label)
            item_label.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
            table.setItem(row, 0, item_label)

            item_action = QtWidgets.QTableWidgetItem(action.display_name())
            item_action.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
            table.setItem(row, 1, item_action)

            btn_edit = QtWidgets.QPushButton("Edit")
            btn_edit.setObjectName("secondaryBtn")
            btn_edit.clicked.connect(lambda _, r=row, p=prof, tbl=table: self.on_edit_button(p, r, tbl))
            table.setCellWidget(row, 2, btn_edit)

    def _on_mode_toggle(self, is_std: bool, tab: QtWidgets.QWidget, prof: Profile):
        self.current_gshift_mode = not is_std
        if hasattr(tab, "table_widget"):
            self._populate_button_table(tab.table_widget, prof)

    def on_edit_button(self, prof: Profile, button_index: int, table: QtWidgets.QTableWidget):
        b_num = button_index + 1
        b_label = G502_BUTTON_LABELS.get(b_num, f"Button {b_num}")
        buttons_list = prof.gbuttons if self.current_gshift_mode else prof.buttons
        current_action = buttons_list[button_index]

        dialog = ButtonEditorDialog(b_num, b_label, current_action, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            buttons_list[button_index] = dialog.result_action
            self._populate_button_table(table, prof)

    def _on_profile_enabled_toggled(self, prof: Profile, val: bool):
        prof.enabled = 1 if val else 0
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if getattr(tab, "profile_id", None) == prof.profile_id:
                self.tab_widget.setTabText(i, self._get_tab_label(prof))
                break

    def _on_rate_changed(self, prof: Profile, rate: int):
        prof.report_rate = rate

    def _on_dpi_changed(self, prof: Profile, stage_idx: int, val: int):
        prof.resolutions[stage_idx] = val

    def _on_default_dpi_toggled(self, prof: Profile, stage_idx: int, checked: bool):
        if checked:
            prof.resolution_default_index = stage_idx

    def on_tab_changed(self, idx: int):
        pass

    def on_set_active_profile(self):
        tab_idx = self.tab_widget.currentIndex()
        if tab_idx < 0 or not self.config:
            return
        pids = sorted(self.config.profiles.keys())
        target_pid = pids[tab_idx]

        self.device_status.setText(f"Switching active profile to Profile {target_pid}...")
        success, msg = self.backend.set_active_profile(target_pid)
        if success:
            self.config.active_profile_id = target_pid
            self.lbl_active_info.setText(f"Active Profile on Mouse: Profile {target_pid}")
            self.device_status.setText(msg)
            self._rebuild_tabs()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to switch active profile:\n{msg}")

    def on_apply_to_mouse(self):
        if not self.config:
            return

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Apply Changes to Mouse",
            "This will flash the updated configuration directly to the mouse onboard memory.\n\n"
            "An automatic backup of your existing settings will be created first.\n\n"
            "Do you want to proceed?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self.device_status.setText("Saving and flashing to mouse memory...")
        self.btn_apply.setEnabled(False)
        self.btn_read.setEnabled(False)

        self.worker = WorkerThread(self.backend.write_profiles, self.config)
        self.worker.finished_signal.connect(self._on_write_finished)
        self.worker.start()

    def _on_write_finished(self, success: bool, msg: str):
        self.btn_apply.setEnabled(True)
        self.btn_read.setEnabled(True)

        if success:
            if self.chk_auto_turn_off_rgb.isChecked():
                self.backend.turn_off_lighting()
            self.device_status.setText("Settings successfully burned to mouse memory.")
            QtWidgets.QMessageBox.information(self, "Success", msg)
        else:
            self.device_status.setText("Failed to burn to memory.")
            QtWidgets.QMessageBox.critical(self, "Write Failed", f"Could not write to mouse:\n\n{msg}")

    def on_open_backups(self):
        bdir = str(get_backup_dir())
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(bdir))
