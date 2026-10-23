"""Main Window for Logitech Onboard Memory GUI."""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from core.backend import MouseBackend, get_backup_dir, prune_backups
from core.models import OnboardConfig, Profile, ButtonAction
from core.keycodes import (
    G502_BUTTON_LABELS,
    SUPPORTED_MODELS,
    detect_mouse_model,
    get_button_labels,
)
from ui.button_editor_dialog import ButtonEditorDialog
from ui.mouse_canvas import MouseCanvas
from ui.games_tab import GamesTab
from ui.rgb_dialog import RGBLightingDialog
from core.profile_watcher import ProfileWatcher
from core.service_manager import BackgroundServiceManager


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


APP_VERSION = "v0.9.0"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.backend = MouseBackend("G502")
        self.config: Optional[OnboardConfig] = None
        self.current_gshift_mode = False
        self.current_model_key = "g502"

        self.qsettings = QtCore.QSettings("LogitechLinux", "OnboardMemoryManager")
        self.force_quit = False
        self.tray_icon: Optional[QtWidgets.QSystemTrayIcon] = None
        self.tray_profile_actions = {}

        self.watcher = ProfileWatcher(backend=self.backend)
        self.games_tab = GamesTab(self.watcher)
        if not BackgroundServiceManager.is_running():
            self.watcher.start()

        self.setWindowTitle(f"Logitech Onboard Memory Manager {APP_VERSION}")
        self.resize(1180, 760)

        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self._setup_styling()
        self._init_ui()
        self._init_tray()

        # Ensure backup folder is trimmed to the newest 50 files
        prune_backups(50)

        # Initial read from mouse
        QtCore.QTimer.singleShot(200, self.on_read_from_mouse)

    def closeEvent(self, event: QtGui.QCloseEvent):
        min_to_tray = True
        if hasattr(self, "chk_minimize_to_tray"):
            min_to_tray = self.chk_minimize_to_tray.isChecked()
        elif hasattr(self, "qsettings"):
            min_to_tray = self.qsettings.value("minimize_to_tray_on_close", True, type=bool)

        if self.tray_icon and self.tray_icon.isVisible() and min_to_tray and not self.force_quit:
            event.ignore()
            self.hide()
            if hasattr(self, "action_show_hide"):
                self.action_show_hide.setText("Show Logitech OMM")
            hint_shown = self.qsettings.value("tray_hint_shown", False, type=bool)
            if not hint_shown:
                self.tray_icon.showMessage(
                    "Logitech Onboard Memory Manager",
                    "Application is minimized to the system tray.",
                    QtWidgets.QSystemTrayIcon.MessageIcon.Information,
                    2500
                )
                self.qsettings.setValue("tray_hint_shown", True)
            return

        if self.tray_icon:
            self.tray_icon.hide()
        if hasattr(self, "watcher") and self.watcher:
            self.watcher.stop()
        super().closeEvent(event)

    def changeEvent(self, event: QtCore.QEvent):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            if hasattr(self, "action_show_hide"):
                if self.isMinimized() or not self.isVisible():
                    self.action_show_hide.setText("Show Logitech OMM")
                else:
                    self.action_show_hide.setText("Hide Logitech OMM")

    def hideEvent(self, event: QtGui.QHideEvent):
        super().hideEvent(event)
        if hasattr(self, "action_show_hide"):
            self.action_show_hide.setText("Show Logitech OMM")

    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        if hasattr(self, "action_show_hide"):
            self.action_show_hide.setText("Hide Logitech OMM")

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
        
        app_title_row = QtWidgets.QHBoxLayout()
        self.app_title_lbl = QtWidgets.QLabel("Logitech Onboard Memory Manager")
        self.app_title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        self.version_badge = QtWidgets.QLabel(f" {APP_VERSION} ")
        self.version_badge.setStyleSheet(
            "background-color: #2e3440; color: #8892b0; font-size: 12px; font-weight: bold; "
            "border: 1px solid #434c5e; border-radius: 4px; padding: 1px 4px;"
        )
        app_title_row.addWidget(self.app_title_lbl)
        app_title_row.addWidget(self.version_badge)
        app_title_row.addStretch()

        self.device_title = QtWidgets.QLabel("Detecting device...")
        self.device_title.setStyleSheet("font-size: 13px; color: #60a5fa; font-weight: bold;")
        self.device_status = QtWidgets.QLabel("Status: Checking device...")
        self.device_status.setStyleSheet("color: #9ca3af; font-size: 11px;")
        
        title_box.addLayout(app_title_row)
        title_box.addWidget(self.device_title)
        title_box.addWidget(self.device_status)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Mouse Model / Layout Template Selector
        model_selector_box = QtWidgets.QHBoxLayout()
        lbl_model = QtWidgets.QLabel("Model Layout:")
        lbl_model.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.combo_model = QtWidgets.QComboBox()
        for k, v in SUPPORTED_MODELS.items():
            self.combo_model.addItem(v["name"], k)
        self.combo_model.currentIndexChanged.connect(self._on_model_selector_changed)
        model_selector_box.addWidget(lbl_model)
        model_selector_box.addWidget(self.combo_model)
        header_layout.addLayout(model_selector_box)

        header_layout.addSpacing(12)

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

        self.btn_rgb_dialog = QtWidgets.QPushButton("Hardware Lighting...")
        self.btn_rgb_dialog.setObjectName("secondaryBtn")
        self.btn_rgb_dialog.clicked.connect(self.on_open_rgb_dialog)
        bottom_layout.addWidget(self.btn_rgb_dialog)

        self.btn_turn_off_rgb = QtWidgets.QPushButton("Turn Off RGB")
        self.btn_turn_off_rgb.setObjectName("secondaryBtn")
        self.btn_turn_off_rgb.clicked.connect(self.on_turn_off_lighting)
        bottom_layout.addWidget(self.btn_turn_off_rgb)

        auto_off_saved = self.qsettings.value("auto_turn_off_rgb", False, type=bool)
        self.chk_auto_turn_off_rgb = QtWidgets.QCheckBox("Auto-turn off RGB on save")
        self.chk_auto_turn_off_rgb.setChecked(auto_off_saved)
        self.chk_auto_turn_off_rgb.toggled.connect(
            lambda val: self.qsettings.setValue("auto_turn_off_rgb", val)
        )
        bottom_layout.addWidget(self.chk_auto_turn_off_rgb)

        min_tray_saved = self.qsettings.value("minimize_to_tray_on_close", True, type=bool)
        self.chk_minimize_to_tray = QtWidgets.QCheckBox("Minimize to tray on close")
        self.chk_minimize_to_tray.setChecked(min_tray_saved)
        self.chk_minimize_to_tray.toggled.connect(self._on_chk_minimize_toggled)
        bottom_layout.addWidget(self.chk_minimize_to_tray)

        bottom_layout.addStretch()

        self.lbl_active_info = QtWidgets.QLabel("Active Profile: -")
        self.lbl_active_info.setStyleSheet("color: #10b981; font-weight: bold;")
        bottom_layout.addWidget(self.lbl_active_info)

        main_layout.addLayout(bottom_layout)

    def _init_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return

        tray_icon_path = Path(__file__).resolve().parent.parent / "assets" / "tray_icon.svg"
        if not tray_icon_path.exists():
            tray_icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.svg"
        icon = QtGui.QIcon(str(tray_icon_path)) if tray_icon_path.exists() else self.windowIcon()

        self.tray_icon = QtWidgets.QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Logitech Onboard Memory Manager")

        tray_menu = QtWidgets.QMenu(self)

        self.action_show_hide = QtGui.QAction("Hide Logitech OMM", self)
        self.action_show_hide.triggered.connect(self._toggle_visibility)
        tray_menu.addAction(self.action_show_hide)

        tray_menu.addSeparator()

        profiles_menu = tray_menu.addMenu("Switch Profile")
        self.tray_profile_group = QtGui.QActionGroup(self)
        self.tray_profile_group.setExclusive(True)
        self.tray_profile_actions = {}

        for pid in range(1, 6):
            act = QtGui.QAction(f"Profile {pid}", self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, p=pid: self._on_tray_profile_selected(p))
            self.tray_profile_group.addAction(act)
            profiles_menu.addAction(act)
            self.tray_profile_actions[pid] = act

        tray_menu.addSeparator()

        action_rgb = QtGui.QAction("Hardware RGB Lighting...", self)
        action_rgb.triggered.connect(self.on_open_rgb_dialog)
        tray_menu.addAction(action_rgb)

        action_rgb_off = QtGui.QAction("Turn Off RGB", self)
        action_rgb_off.triggered.connect(self.on_turn_off_lighting)
        tray_menu.addAction(action_rgb_off)

        tray_menu.addSeparator()

        self.action_tray_minimize = QtGui.QAction("Minimize to Tray on Close", self)
        self.action_tray_minimize.setCheckable(True)
        min_saved = self.qsettings.value("minimize_to_tray_on_close", True, type=bool)
        self.action_tray_minimize.setChecked(min_saved)
        self.action_tray_minimize.toggled.connect(self._on_tray_minimize_toggled)
        tray_menu.addAction(self.action_tray_minimize)

        tray_menu.addSeparator()

        action_quit = QtGui.QAction("Quit", self)
        action_quit.triggered.connect(self.quit_app)
        tray_menu.addAction(action_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def present_to_user(self):
        """Restores the window from minimized/tray state and brings it to foreground."""
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if hasattr(self, "action_show_hide"):
            self.action_show_hide.setText("Hide Logitech OMM")

    def _toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
            if hasattr(self, "action_show_hide"):
                self.action_show_hide.setText("Show Logitech OMM")
        else:
            self.present_to_user()

    def _on_tray_activated(self, reason):
        if reason in (
            QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
            QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_visibility()

    def _on_tray_profile_selected(self, pid: int):
        self.device_status.setText(f"Switching active profile to Profile {pid}...")
        success, msg = self.backend.set_active_profile(pid)
        if success:
            if self.config:
                self.config.active_profile_id = pid
                self._rebuild_tabs()
            self.lbl_active_info.setText(f"Active Profile on Mouse: Profile {pid}")
            self.device_status.setText(f"Active Profile set to Profile {pid}.")
            self._update_tray_profile_checked(pid)
        else:
            QtWidgets.QMessageBox.warning(self, "Profile Switch", f"Could not switch to Profile {pid}:\n{msg}")

    def _on_tray_minimize_toggled(self, checked: bool):
        self.qsettings.setValue("minimize_to_tray_on_close", checked)
        if hasattr(self, "chk_minimize_to_tray") and self.chk_minimize_to_tray:
            self.chk_minimize_to_tray.blockSignals(True)
            self.chk_minimize_to_tray.setChecked(checked)
            self.chk_minimize_to_tray.blockSignals(False)

    def _on_chk_minimize_toggled(self, checked: bool):
        self.qsettings.setValue("minimize_to_tray_on_close", checked)
        if hasattr(self, "action_tray_minimize") and self.action_tray_minimize:
            self.action_tray_minimize.blockSignals(True)
            self.action_tray_minimize.setChecked(checked)
            self.action_tray_minimize.blockSignals(False)

    def _update_tray_profile_checked(self, active_pid: int):
        if hasattr(self, "tray_profile_actions"):
            for pid, act in self.tray_profile_actions.items():
                act.blockSignals(True)
                act.setChecked(pid == active_pid)
                act.blockSignals(False)
        if self.tray_icon:
            self.tray_icon.setToolTip(f"Logitech Onboard Memory Manager (Profile {active_pid})")

    def on_open_rgb_dialog(self):
        dlg = RGBLightingDialog(self.backend, self)
        dlg.exec()

    def quit_app(self):
        self.force_quit = True
        if self.tray_icon:
            self.tray_icon.hide()
        if hasattr(self, "watcher") and self.watcher:
            self.watcher.stop()
        QtWidgets.QApplication.quit()

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
        self._update_tray_profile_checked(config.active_profile_id)

        # Auto-detect mouse model and update combo selector
        p1 = config.profiles.get(1)
        btn_count = len(p1.buttons) if p1 else 11
        detected_model = detect_mouse_model(config.device_name, btn_count)
        self.current_model_key = detected_model

        idx = self.combo_model.findData(detected_model)
        if idx >= 0:
            self.combo_model.blockSignals(True)
            self.combo_model.setCurrentIndex(idx)
            self.combo_model.blockSignals(False)

        self._rebuild_tabs()

    def _on_model_selector_changed(self, idx: int):
        model_key = self.combo_model.currentData()
        if model_key and model_key != self.current_model_key:
            self.current_model_key = model_key
            # Update all active tabs
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if hasattr(tab, "mouse_canvas"):
                    tab.mouse_canvas.set_model(model_key)
                if hasattr(tab, "table_widget") and self.config:
                    pids = sorted(self.config.profiles.keys())
                    if i < len(pids):
                        prof = self.config.profiles[pids[i]]
                        self._populate_button_table(tab.table_widget, prof)

    def _get_tab_label(self, prof: Profile) -> str:
        label = f"Profile {prof.profile_id}"
        if self.config and prof.profile_id == self.config.active_profile_id:
            label += " (Active)"
        elif prof.enabled:
            label += " (Enabled)"
        else:
            label += " (Disabled)"
        return label

    def _rebuild_tabs(self, target_index: Optional[int] = None):
        if not self.config:
            return

        curr_tab = self.tab_widget.currentIndex() if target_index is None else target_index
        self.tab_widget.clear()

        for pid in sorted(self.config.profiles.keys()):
            prof = self.config.profiles[pid]
            tab = self._create_profile_tab(prof)
            tab.profile_id = pid
            label = self._get_tab_label(prof)
            self.tab_widget.addTab(tab, label)

        # Append Games / Auto-Switching Tab
        if hasattr(self, "games_tab") and self.games_tab:
            self.tab_widget.addTab(self.games_tab, "Game Profiles")

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

        # Main Body: Splitter with Mouse Canvas on the Left and DPI/Buttons on the Right
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: Interactive Mouse Visualizer
        canvas_container = QtWidgets.QFrame()
        canvas_container.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        canvas_container.setStyleSheet("background-color: #13151b; border: 1px solid #2e2e38; border-radius: 6px;")
        canvas_layout = QtWidgets.QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(6, 6, 6, 6)

        mouse_canvas = MouseCanvas(model_key=self.current_model_key)
        canvas_layout.addWidget(mouse_canvas)

        if prof.profile_id == 5:
            lbl_staged_game = QtWidgets.QLabel()
            lbl_staged_game.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl_staged_game.setStyleSheet(
                "background-color: #1e293b; color: #38bdf8; font-size: 13px; font-weight: bold; "
                "border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; margin-top: 4px;"
            )
            staged_name = ""
            if hasattr(self, "games_tab") and self.games_tab:
                staged_name = self.games_tab.mgr.get_settings().staged_slot5_profile
            if staged_name:
                clean_name = staged_name.replace(".json", "")
                lbl_staged_game.setText(f"Active Staged Game: {clean_name}")
            else:
                lbl_staged_game.setText("Active Staged Game: None (Default Slot 5)")
            canvas_layout.addWidget(lbl_staged_game)
            tab.lbl_staged_game = lbl_staged_game

        splitter.addWidget(canvas_container)

        # Right: DPI Stages + Button Table
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

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
        right_layout.addWidget(dpi_group)

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
        right_layout.addWidget(table, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)

        layout.addWidget(splitter, stretch=1)

        # Connect bidirectional signals between canvas and table
        def on_canvas_button_clicked(b_num: int):
            row = b_num - 1
            if 0 <= row < table.rowCount():
                table.selectRow(row)
                table.scrollToItem(table.item(row, 0))

        def on_canvas_button_double_clicked(b_num: int):
            row = b_num - 1
            if 0 <= row < table.rowCount():
                self.on_edit_button(prof, row, table)

        def on_table_selection_changed():
            selected_rows = table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                mouse_canvas.set_selected_button(row + 1)
            else:
                mouse_canvas.set_selected_button(None)

        mouse_canvas.button_clicked.connect(on_canvas_button_clicked)
        mouse_canvas.button_double_clicked.connect(on_canvas_button_double_clicked)
        table.itemSelectionChanged.connect(on_table_selection_changed)

        # Store references on tab
        table.tab_owner = tab
        tab.table_widget = table
        tab.mouse_canvas = mouse_canvas
        self._update_mouse_canvas_actions(tab, prof)

        return tab

    def _update_mouse_canvas_actions(self, tab: QtWidgets.QWidget, prof: Profile):
        if hasattr(tab, "mouse_canvas"):
            buttons = prof.gbuttons if self.current_gshift_mode else prof.buttons
            actions_map = {row + 1: action.display_name() for row, action in enumerate(buttons)}
            tab.mouse_canvas.set_button_actions(actions_map)

    def _populate_button_table(self, table: QtWidgets.QTableWidget, prof: Profile):
        buttons = prof.gbuttons if self.current_gshift_mode else prof.buttons
        table.setRowCount(len(buttons))

        device_name = self.config.device_name if self.config else "G502"
        labels = get_button_labels(device_name, len(buttons), self.current_model_key)

        for row, action in enumerate(buttons):
            b_num = row + 1
            label = labels.get(b_num, f"Button {b_num}")

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

        tab = getattr(table, "tab_owner", None)
        if tab:
            self._update_mouse_canvas_actions(tab, prof)

    def _on_mode_toggle(self, is_std: bool, tab: QtWidgets.QWidget, prof: Profile):
        self.current_gshift_mode = not is_std
        if hasattr(tab, "table_widget"):
            self._populate_button_table(tab.table_widget, prof)
        self._update_mouse_canvas_actions(tab, prof)

    def on_edit_button(self, prof: Profile, button_index: int, table: QtWidgets.QTableWidget):
        b_num = button_index + 1
        device_name = self.config.device_name if self.config else "G502"
        labels = get_button_labels(device_name, len(prof.buttons), self.current_model_key)
        b_label = labels.get(b_num, f"Button {b_num}")
        buttons_list = prof.gbuttons if self.current_gshift_mode else prof.buttons
        current_action = buttons_list[button_index]

        dialog = ButtonEditorDialog(b_num, b_label, current_action, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            buttons_list[button_index] = dialog.result_action
            self._populate_button_table(table, prof)
            tab = getattr(table, "tab_owner", None)
            if tab:
                self._update_mouse_canvas_actions(tab, prof)

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
        # Dynamically refresh Active Staged Game badge on Profile 5 tab whenever viewed
        if 0 <= idx < self.tab_widget.count():
            tab = self.tab_widget.widget(idx)
            if getattr(tab, "profile_id", None) == 5 and hasattr(tab, "lbl_staged_game"):
                staged_name = ""
                if hasattr(self, "games_tab") and self.games_tab:
                    staged_name = self.games_tab.mgr.get_settings().staged_slot5_profile
                if staged_name:
                    clean_name = staged_name.replace(".json", "")
                    tab.lbl_staged_game.setText(f"Active Staged Game: {clean_name}")
                else:
                    tab.lbl_staged_game.setText("Active Staged Game: None (Default Slot 5)")

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
            self._update_tray_profile_checked(target_pid)
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

        auto_off = self.chk_auto_turn_off_rgb.isChecked() if hasattr(self, "chk_auto_turn_off_rgb") else False
        self.worker = WorkerThread(self.backend.write_profiles, self.config, auto_off)
        self.worker.finished_signal.connect(self._on_write_finished)
        self.worker.start()

    def _on_write_finished(self, success: bool, msg: str):
        self.btn_apply.setEnabled(True)
        self.btn_read.setEnabled(True)

        if success:
            # If Profile 5 was written, sync it to the library profile if one is assigned
            if hasattr(self, "games_tab") and self.config and 5 in self.config.profiles:
                p5 = self.config.profiles[5]
                staged = self.games_tab.mgr.get_settings().staged_slot5_profile
                if staged:
                    p5_dict = {
                        "name": p5.name,
                        "enabled": p5.enabled,
                        "report_rate": p5.report_rate,
                        "resolutions": p5.resolutions,
                        "resolution_default_index": p5.resolution_default_index,
                        "resolution_shift_index": p5.resolution_shift_index,
                        "buttons": [b.to_dict() for b in p5.buttons],
                        "gbuttons": [b.to_dict() for b in p5.gbuttons],
                    }
                    self.games_tab.mgr.save_profile_to_library(staged, p5_dict)

            self.device_status.setText("Settings successfully burned to mouse memory.")
        else:
            self.device_status.setText("Failed to burn to memory.")
            QtWidgets.QMessageBox.critical(self, "Write Failed", f"Could not write to mouse:\n\n{msg}")

    def on_open_backups(self):
        prune_backups(50)
        bdir = str(get_backup_dir())
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(bdir))
