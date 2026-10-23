from __future__ import annotations
import os
import re
import subprocess
import time
from typing import Optional, List, Dict, Any
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from core.game_scanner import GameScanner, ScannedApp, ScannedGame
from core.profile_library import ProfileLibraryManager, GameRule, WatcherSettings
from core.profile_watcher import ProfileWatcher
from core.service_manager import BackgroundServiceManager


class RuleEditDialog(QtWidgets.QDialog):
    """Dialog to create or edit a game auto-switching rule."""

    def __init__(self, parent=None, mgr: Optional[ProfileLibraryManager] = None, rule: Optional[GameRule] = None, is_new: bool = True):
        super().__init__(parent)
        self.mgr = mgr
        self.is_new = is_new if rule is None else is_new
        self.setWindowTitle("Add Game Rule" if self.is_new else "Edit Game Rule")
        self.resize(580, 360)
        self.setMinimumSize(540, 340)
        self._custom_profile_edited = False
        self._init_ui(rule)

    def _init_ui(self, rule: Optional[GameRule]):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.edit_name = QtWidgets.QLineEdit()
        self.edit_name.setPlaceholderText("e.g. Counter-Strike 2")
        self.edit_name.setMinimumHeight(32)

        pattern_layout = QtWidgets.QHBoxLayout()
        self.edit_pattern = QtWidgets.QLineEdit()
        self.edit_pattern.setPlaceholderText("Window class or binary (e.g. cs2, steam_app_730)")
        self.edit_pattern.setMinimumHeight(32)
        self.btn_capture = QtWidgets.QPushButton("Capture Window")
        self.btn_capture.setObjectName("secondaryBtn")
        self.btn_capture.setMinimumHeight(32)
        self.btn_capture.setToolTip("Click here, then switch to the game within 3 seconds to capture its window class")
        self.btn_capture.clicked.connect(self._on_capture_window)
        pattern_layout.addWidget(self.edit_pattern, stretch=1)
        pattern_layout.addWidget(self.btn_capture)

        self.combo_slot = QtWidgets.QComboBox()
        self.combo_slot.setMinimumHeight(32)
        self.combo_slot.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.combo_slot.addItem("Slot 2 (Resident Game Profile)", 2)
        self.combo_slot.addItem("Slot 3 (Resident Game Profile)", 3)
        self.combo_slot.addItem("Slot 4 (Resident Game Profile)", 4)
        self.combo_slot.addItem("Slot 5 (Dynamic Staging - Unlimited Library)", 5)
        self.combo_slot.currentIndexChanged.connect(self._on_slot_changed)

        profile_layout = QtWidgets.QHBoxLayout()
        self.edit_profile = QtWidgets.QLineEdit()
        self.edit_profile.setMinimumHeight(32)
        self.edit_profile.setPlaceholderText("Profile filename (e.g. Counter-Strike 2.json)")
        self.edit_profile.textEdited.connect(self._on_profile_edited_by_user)
        profile_layout.addWidget(self.edit_profile, stretch=1)

        self.lbl_profile = QtWidgets.QLabel("Library Profile:")
        self.lbl_profile_hint = QtWidgets.QLabel()
        self.lbl_profile_hint.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.lbl_profile_hint.setWordWrap(True)

        self.chk_enabled = QtWidgets.QCheckBox("Rule Enabled")
        self.chk_enabled.setChecked(True)

        if rule and not self.is_new:
            self.edit_name.setText(rule.name)
            self.edit_pattern.setText(rule.pattern)
            idx = self.combo_slot.findData(rule.target_slot)
            if idx != -1:
                self.combo_slot.setCurrentIndex(idx)
            self.edit_profile.setText(rule.profile_name)
            self.chk_enabled.setChecked(rule.enabled)
            self._custom_profile_edited = True
        elif rule and self.is_new:
            self.edit_name.setText(rule.name)
            self.edit_pattern.setText(rule.pattern)
            idx = self.combo_slot.findData(rule.target_slot)
            if idx != -1:
                self.combo_slot.setCurrentIndex(idx)
            self.edit_profile.setText(rule.profile_name)
            self.chk_enabled.setChecked(rule.enabled)
            self.edit_name.textChanged.connect(self._on_name_changed)
        else:
            idx = self.combo_slot.findData(5)
            if idx != -1:
                self.combo_slot.setCurrentIndex(idx)
            self.edit_name.textChanged.connect(self._on_name_changed)
            self.edit_profile.setText("New Profile.json")

        form.addRow("Game Name:", self.edit_name)
        form.addRow("Match Pattern:", pattern_layout)
        form.addRow("Target Slot:", self.combo_slot)
        form.addRow(self.lbl_profile, profile_layout)
        form.addRow("", self.lbl_profile_hint)
        form.addRow("", self.chk_enabled)

        layout.addLayout(form)

        # Trigger slot visibility adjustment
        self._on_slot_changed()

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_slot_changed(self):
        target_slot = self.combo_slot.currentData()
        if target_slot in (2, 3, 4):
            # Resident slot
            self.edit_profile.setEnabled(False)
            self.edit_profile.setToolTip(f"Slot {target_slot} uses the hardware settings already flashed into Slot {target_slot} on the mouse.")
            self.lbl_profile_hint.setText(f"Uses the hardware settings already flashed into Slot {target_slot} on the mouse.")
        else:
            # Slot 5 dynamic
            self.edit_profile.setEnabled(True)
            self.edit_profile.setToolTip("Dedicated profile JSON in ~/.config/omm-linux/library/ staged into Slot 5.")
            if self.is_new:
                self.lbl_profile_hint.setText("A dedicated, new profile JSON will be created in your library for this rule.")
            else:
                self.lbl_profile_hint.setText("Stages this profile from disk into Slot 5 when this game is focused.")

    def _on_capture_window(self):
        self.btn_capture.setEnabled(False)
        self.btn_capture.setText("Switch to game (3s)...")
        QtWidgets.QApplication.processEvents()

        QtCore.QTimer.singleShot(3000, self._do_capture)

    def _do_capture(self):
        win_class = ""
        try:
            res = subprocess.run(["kdotool", "getactivewindow", "getwindowclassname"], capture_output=True, text=True, timeout=1)
            if res.returncode == 0 and res.stdout.strip():
                win_class = res.stdout.strip()
        except Exception:
            pass

        if not win_class:
            try:
                res = subprocess.run(["xdotool", "getactivewindow", "getwindowclassname"], capture_output=True, text=True, timeout=1)
                if res.returncode == 0 and res.stdout.strip():
                    win_class = res.stdout.strip()
            except Exception:
                pass

        if win_class:
            self.edit_pattern.setText(win_class)
            if not self.edit_name.text():
                self.edit_name.setText(win_class.replace("_", " ").title())
            QtWidgets.QMessageBox.information(self, "Captured", f"Captured window class: {win_class}")
        else:
            QtWidgets.QMessageBox.warning(self, "Capture Failed", "Could not detect active window class.")

        self.btn_capture.setEnabled(True)
        self.btn_capture.setText("Capture Window")

    def _on_profile_edited_by_user(self):
        self._custom_profile_edited = True

    def _on_name_changed(self, text: str):
        t = text.strip()
        if self.is_new and not self._custom_profile_edited:
            clean = re.sub(r'[\\/*?:"<>|]', "", t).strip()
            self.edit_profile.setText(f"{clean or 'New Profile'}.json")

    def get_rule(self) -> GameRule:
        name = self.edit_name.text().strip() or "Unnamed Game"
        prof_name = self.edit_profile.text().strip()
        if not prof_name:
            clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
            prof_name = f"{clean or 'New Profile'}.json"
        if not prof_name.endswith(".json"):
            prof_name += ".json"
        return GameRule(
            name=name,
            pattern=self.edit_pattern.text().strip(),
            target_slot=self.combo_slot.currentData(),
            profile_name=prof_name,
            enabled=self.chk_enabled.isChecked()
        )


class GamesTab(QtWidgets.QWidget):
    """Tab for managing Game Profile Auto-Switching, game library scanner, and rules."""

    def __init__(self, watcher: ProfileWatcher, parent=None):
        super().__init__(parent)
        self.watcher = watcher
        self.mgr = watcher.mgr
        self._current_view_mode = "games"  # 'games' or 'apps'
        self._all_scanned_games: List[ScannedApp] = []
        self._all_scanned_apps: List[ScannedApp] = []
        self._init_ui()
        self.reload_data()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        # Compact Unified Header Panel
        header_card = QtWidgets.QFrame()
        header_card.setObjectName("gamesHeaderCard")
        header_card.setStyleSheet("""
            #gamesHeaderCard {
                background-color: #1a1e28;
                border: 1px solid #2e3440;
                border-radius: 6px;
            }
        """)
        header_card.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        card_layout = QtWidgets.QVBoxLayout(header_card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(6)

        # Row 1: Profile Auto-Switching Controls & Active Status
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setSpacing(12)

        self.chk_enable_autoswitch = QtWidgets.QCheckBox("Enable Automatic Profile Switching (Game Lock Active)")
        self.chk_enable_autoswitch.setStyleSheet("font-weight: bold; font-size: 13px; color: #38bdf8;")
        self.chk_enable_autoswitch.toggled.connect(self._on_toggle_autoswitch)
        top_bar.addWidget(self.chk_enable_autoswitch)

        top_bar.addSpacing(10)

        lbl_def = QtWidgets.QLabel("Default Desktop Slot (Alt-Tab):")
        lbl_def.setStyleSheet("color: #9ca3af; font-size: 12px;")
        self.combo_default_slot = QtWidgets.QComboBox()
        self.combo_default_slot.setFixedHeight(26)
        self.combo_default_slot.addItem("Slot 1 (Recommended)", 1)
        self.combo_default_slot.addItem("Slot 2", 2)
        self.combo_default_slot.addItem("Slot 3", 3)
        self.combo_default_slot.addItem("Slot 4", 4)
        self.combo_default_slot.currentIndexChanged.connect(self._on_default_slot_changed)
        top_bar.addWidget(lbl_def)
        top_bar.addWidget(self.combo_default_slot)

        top_bar.addStretch()

        self.lbl_status = QtWidgets.QLabel("Active: Slot 1 (Desktop)")
        self.lbl_status.setFixedHeight(26)
        self.lbl_status.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 12px; padding: 2px 10px; background: #131720; border: 1px solid #1f2937; border-radius: 4px;")
        top_bar.addWidget(self.lbl_status)
        card_layout.addLayout(top_bar)

        # Row 2: Background Service Status & Controls
        svc_layout = QtWidgets.QHBoxLayout()
        svc_layout.setSpacing(8)

        lbl_svc_title = QtWidgets.QLabel("Background Daemon:")
        lbl_svc_title.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: bold;")
        svc_layout.addWidget(lbl_svc_title)

        self.lbl_svc_indicator = QtWidgets.QLabel("● Stopped")
        self.lbl_svc_indicator.setFixedHeight(24)
        self.lbl_svc_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 12px; padding: 2px 8px; background: #231215; border: 1px solid #451a1a; border-radius: 4px;")
        svc_layout.addWidget(self.lbl_svc_indicator)

        self.btn_svc_start = QtWidgets.QPushButton("Start Service")
        self.btn_svc_start.setFixedHeight(26)
        self.btn_svc_start.clicked.connect(self._on_start_service)
        svc_layout.addWidget(self.btn_svc_start)

        self.btn_svc_stop = QtWidgets.QPushButton("Stop Service")
        self.btn_svc_stop.setFixedHeight(26)
        self.btn_svc_stop.setObjectName("secondaryBtn")
        self.btn_svc_stop.clicked.connect(self._on_stop_service)
        svc_layout.addWidget(self.btn_svc_stop)

        svc_layout.addSpacing(14)

        lbl_poll = QtWidgets.QLabel("Polling Interval:")
        lbl_poll.setStyleSheet("color: #9ca3af; font-size: 12px;")
        svc_layout.addWidget(lbl_poll)

        self.combo_poll_interval = QtWidgets.QComboBox()
        self.combo_poll_interval.setFixedHeight(26)
        self.combo_poll_interval.addItem("100 ms (Fastest)", 100)
        self.combo_poll_interval.addItem("200 ms (Fast)", 200)
        self.combo_poll_interval.addItem("500 ms (Balanced)", 500)
        self.combo_poll_interval.addItem("1000 ms (1.0s Default)", 1000)
        self.combo_poll_interval.addItem("2000 ms (2.0s Low CPU)", 2000)
        self.combo_poll_interval.currentIndexChanged.connect(self._on_poll_interval_changed)
        svc_layout.addWidget(self.combo_poll_interval)

        svc_layout.addSpacing(14)

        self.chk_svc_autostart = QtWidgets.QCheckBox("Automatically start service on boot / login")
        self.chk_svc_autostart.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        self.chk_svc_autostart.toggled.connect(self._on_toggle_svc_autostart)
        svc_layout.addWidget(self.chk_svc_autostart)

        svc_layout.addStretch()
        card_layout.addLayout(svc_layout)

        layout.addWidget(header_card)

        # Splitter: Rules Table on Left, Scanned Installed Games on Right
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # 1. Rules Group (Left Column)
        rules_box = QtWidgets.QGroupBox("Game Auto-Switching Rules")
        rules_layout = QtWidgets.QVBoxLayout(rules_box)
        rules_layout.setContentsMargins(10, 12, 10, 10)
        rules_layout.setSpacing(8)

        # Table
        self.table_rules = QtWidgets.QTableWidget(0, 5)
        self.table_rules.setHorizontalHeaderLabels(["Active", "Game Name", "Match Pattern", "Slot", "Library Profile"])
        self.table_rules.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.table_rules.setColumnWidth(1, 140)
        self.table_rules.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.table_rules.setColumnWidth(2, 110)
        self.table_rules.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_rules.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        rules_layout.addWidget(self.table_rules)

        # Rules Buttons (2-Row Compact Layout for Column View)
        r_btns_layout = QtWidgets.QVBoxLayout()
        r_btns_layout.setSpacing(6)

        r_btns_row1 = QtWidgets.QHBoxLayout()
        self.btn_edit_buttons = QtWidgets.QPushButton("Edit Buttons")
        self.btn_edit_buttons.setToolTip("Customize mouse buttons for the selected game rule")
        self.btn_edit_buttons.clicked.connect(self._on_edit_buttons_for_rule)
        self.btn_add_rule = QtWidgets.QPushButton("+ Add Rule")
        self.btn_add_rule.clicked.connect(self._on_add_rule)
        self.btn_capture_rule = QtWidgets.QPushButton("Capture Active Window")
        self.btn_capture_rule.setObjectName("secondaryBtn")
        self.btn_capture_rule.clicked.connect(self._on_capture_quick)

        r_btns_row1.addWidget(self.btn_edit_buttons)
        r_btns_row1.addWidget(self.btn_add_rule)
        r_btns_row1.addWidget(self.btn_capture_rule)
        r_btns_row1.addStretch()

        r_btns_row2 = QtWidgets.QHBoxLayout()
        self.btn_edit_rule = QtWidgets.QPushButton("Edit Rule")
        self.btn_edit_rule.setObjectName("secondaryBtn")
        self.btn_edit_rule.clicked.connect(self._on_edit_rule)
        self.btn_delete_rule = QtWidgets.QPushButton("Delete Rule")
        self.btn_delete_rule.setObjectName("secondaryBtn")
        self.btn_delete_rule.clicked.connect(self._on_delete_rule)

        r_btns_row2.addWidget(self.btn_edit_rule)
        r_btns_row2.addWidget(self.btn_delete_rule)
        r_btns_row2.addStretch()

        r_btns_layout.addLayout(r_btns_row1)
        r_btns_layout.addLayout(r_btns_row2)
        rules_layout.addLayout(r_btns_layout)

        # Allow double click to edit buttons directly
        self.table_rules.doubleClicked.connect(self._on_edit_buttons_for_rule)

        splitter.addWidget(rules_box)

        # 2. Installed Software Scanner Group (Right Column)
        self.scanner_box = QtWidgets.QGroupBox("Installed Games & Applications")
        scanner_layout = QtWidgets.QVBoxLayout(self.scanner_box)
        scanner_layout.setContentsMargins(10, 12, 10, 10)
        scanner_layout.setSpacing(8)

        # View Switcher Row: Games vs Applications
        view_toggle_row = QtWidgets.QHBoxLayout()
        view_toggle_row.setSpacing(6)

        self.btn_view_games = QtWidgets.QPushButton("Games (0)")
        self.btn_view_games.setCheckable(True)
        self.btn_view_games.setChecked(True)
        self.btn_view_games.setFixedHeight(28)
        self.btn_view_games.clicked.connect(self._on_switch_to_games_view)

        self.btn_view_apps = QtWidgets.QPushButton("Applications (0)")
        self.btn_view_apps.setCheckable(True)
        self.btn_view_apps.setChecked(False)
        self.btn_view_apps.setFixedHeight(28)
        self.btn_view_apps.clicked.connect(self._on_switch_to_apps_view)

        view_toggle_row.addWidget(self.btn_view_games)
        view_toggle_row.addWidget(self.btn_view_apps)
        view_toggle_row.addStretch()
        scanner_layout.addLayout(view_toggle_row)

        # Filter and Rescan Row
        filter_row = QtWidgets.QHBoxLayout()
        self.edit_search_items = QtWidgets.QLineEdit()
        self.edit_search_items.setPlaceholderText("Filter by name, launcher, or window class...")
        self.edit_search_items.textChanged.connect(self._filter_scanned_items)
        self.btn_rescan = QtWidgets.QPushButton("Scan Software")
        self.btn_rescan.setObjectName("secondaryBtn")
        self.btn_rescan.clicked.connect(self._scan_installed_software)
        self.lbl_scan_status = QtWidgets.QLabel("Ready")
        self.lbl_scan_status.setStyleSheet("color: #9ca3af; font-size: 12px; margin-left: 8px;")
        filter_row.addWidget(self.edit_search_items)
        filter_row.addWidget(self.btn_rescan)
        filter_row.addWidget(self.lbl_scan_status)
        scanner_layout.addLayout(filter_row)

        self.table_scanned = QtWidgets.QTableWidget(0, 4)
        self.table_scanned.setHorizontalHeaderLabels(["Type / Launcher", "Title / Name", "Window Class / ID", "Action"])
        self.table_scanned.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_scanned.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_scanned.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.table_scanned.setColumnWidth(2, 130)
        self.table_scanned.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table_scanned.setColumnWidth(3, 100)
        self.table_scanned.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        scanner_layout.addWidget(self.table_scanned)

        splitter.addWidget(self.scanner_box)

        # Style toggle buttons
        self._update_view_toggle_styles()

        # Set initial balanced column proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([580, 560])

        layout.addWidget(splitter, stretch=1)

        # Connect watcher callback
        self.watcher.on_profile_switched = self._on_profile_switched_callback

        # Periodic timer to check background service status
        self.svc_timer = QtCore.QTimer(self)
        self.svc_timer.setInterval(3000)
        self.svc_timer.timeout.connect(self.refresh_service_status)
        self.svc_timer.start()

    def reload_data(self):
        settings = self.mgr.get_settings()
        self.chk_enable_autoswitch.blockSignals(True)
        self.chk_enable_autoswitch.setChecked(settings.enabled)
        self.chk_enable_autoswitch.blockSignals(False)

        idx = self.combo_default_slot.findData(settings.default_slot)
        if idx != -1:
            self.combo_default_slot.blockSignals(True)
            self.combo_default_slot.setCurrentIndex(idx)
            self.combo_default_slot.blockSignals(False)

        p_idx = self.combo_poll_interval.findData(settings.poll_interval_ms)
        if p_idx != -1:
            self.combo_poll_interval.blockSignals(True)
            self.combo_poll_interval.setCurrentIndex(p_idx)
            self.combo_poll_interval.blockSignals(False)

        self._populate_rules()
        self._scan_installed_software()
        self.refresh_service_status()

    def refresh_service_status(self):
        running = BackgroundServiceManager.is_running()
        enabled = BackgroundServiceManager.is_enabled()

        if running:
            self.lbl_svc_indicator.setText("● Running in Background")
            self.lbl_svc_indicator.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 12px; padding: 2px 8px; background: #14532d; border-radius: 4px;")
            self.btn_svc_start.setEnabled(False)
            self.btn_svc_stop.setEnabled(True)
        else:
            self.lbl_svc_indicator.setText("● Stopped")
            self.lbl_svc_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 12px; padding: 2px 8px; background: #450a0a; border-radius: 4px;")
            self.btn_svc_start.setEnabled(True)
            self.btn_svc_stop.setEnabled(False)

        self.chk_svc_autostart.blockSignals(True)
        self.chk_svc_autostart.setChecked(enabled)
        self.chk_svc_autostart.blockSignals(False)

    def _on_start_service(self):
        ok, msg = BackgroundServiceManager.start()
        self.refresh_service_status()
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Service Error", f"Could not start background service:\n{msg}")

    def _on_stop_service(self):
        ok, msg = BackgroundServiceManager.stop()
        self.refresh_service_status()
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Service Error", f"Could not stop background service:\n{msg}")

    def _on_toggle_svc_autostart(self, enabled: bool):
        ok, msg = BackgroundServiceManager.set_autostart(enabled)
        self.refresh_service_status()
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Autostart Error", f"Could not change autostart setting:\n{msg}")

    def _populate_rules(self):
        rules = self.mgr.get_rules()
        self.table_rules.setRowCount(0)
        for row, r in enumerate(rules):
            self.table_rules.insertRow(row)
            
            chk = QtWidgets.QCheckBox()
            chk.setChecked(r.enabled)
            chk.toggled.connect(lambda val, idx=row: self._on_rule_toggle(idx, val))
            chk_widget = QtWidgets.QWidget()
            chk_lay = QtWidgets.QHBoxLayout(chk_widget)
            chk_lay.addWidget(chk)
            chk_lay.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            chk_lay.setContentsMargins(0, 0, 0, 0)
            self.table_rules.setCellWidget(row, 0, chk_widget)

            self.table_rules.setItem(row, 1, QtWidgets.QTableWidgetItem(r.name))
            self.table_rules.setItem(row, 2, QtWidgets.QTableWidgetItem(r.pattern))
            
            slot_str = f"Slot {r.target_slot}" + (" (Dynamic Staging)" if r.target_slot == 5 else " (Resident)")
            self.table_rules.setItem(row, 3, QtWidgets.QTableWidgetItem(slot_str))
            self.table_rules.setItem(row, 4, QtWidgets.QTableWidgetItem(r.profile_name))

    def _on_rule_toggle(self, row: int, enabled: bool):
        rules = self.mgr.get_rules()
        if 0 <= row < len(rules):
            rules[row].enabled = enabled
            self.mgr.save_rules(rules)
            self.watcher.reload()

    def _update_view_toggle_styles(self):
        active_style = (
            "QPushButton {"
            "   background-color: #0284c7;"
            "   color: #ffffff;"
            "   font-weight: bold;"
            "   border: 1px solid #38bdf8;"
            "   border-radius: 4px;"
            "   padding: 4px 12px;"
            "}"
        )
        inactive_style = (
            "QPushButton {"
            "   background-color: #1e293b;"
            "   color: #94a3b8;"
            "   border: 1px solid #334155;"
            "   border-radius: 4px;"
            "   padding: 4px 12px;"
            "}"
            "QPushButton:hover {"
            "   background-color: #334155;"
            "   color: #f1f5f9;"
            "}"
        )
        if self._current_view_mode == "games":
            self.btn_view_games.setChecked(True)
            self.btn_view_games.setStyleSheet(active_style)
            self.btn_view_apps.setChecked(False)
            self.btn_view_apps.setStyleSheet(inactive_style)
            self.scanner_box.setTitle("Installed Games (Steam / Lutris / Heroic / Desktop Games)")
            self.edit_search_items.setPlaceholderText("Filter games by title, launcher, or window class...")
        else:
            self.btn_view_games.setChecked(False)
            self.btn_view_games.setStyleSheet(inactive_style)
            self.btn_view_apps.setChecked(True)
            self.btn_view_apps.setStyleSheet(active_style)
            self.scanner_box.setTitle("Installed Desktop Applications (FreeDesktop / Flatpak / Snap)")
            self.edit_search_items.setPlaceholderText("Filter applications by name, category, or window class...")

    def _on_switch_to_games_view(self):
        self._current_view_mode = "games"
        self._update_view_toggle_styles()
        self._filter_scanned_items(self.edit_search_items.text())

    def _on_switch_to_apps_view(self):
        self._current_view_mode = "apps"
        self._update_view_toggle_styles()
        self._filter_scanned_items(self.edit_search_items.text())

    def _scan_installed_software(self):
        self.btn_rescan.setEnabled(False)
        self.lbl_scan_status.setText("Scanning system for games and applications...")
        self.lbl_scan_status.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: bold; margin-left: 8px;")
        QtWidgets.QApplication.processEvents()

        def do_scan():
            games, apps = GameScanner.get_scanned_items()
            self._all_scanned_games = games
            self._all_scanned_apps = apps

            self.btn_view_games.setText(f"Games ({len(games)})")
            self.btn_view_apps.setText(f"Applications ({len(apps)})")

            self._filter_scanned_items(self.edit_search_items.text())
            self.lbl_scan_status.setText(f"Discovered {len(games)} games and {len(apps)} apps")
            self.lbl_scan_status.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: bold; margin-left: 8px;")
            self.btn_rescan.setEnabled(True)

        QtCore.QTimer.singleShot(50, do_scan)

    def _filter_scanned_items(self, text: str = ""):
        current_list = self._all_scanned_games if self._current_view_mode == "games" else self._all_scanned_apps
        query = text.strip().lower()
        if not query:
            self._display_scanned_items(current_list)
            return

        filtered = [
            item for item in current_list
            if (query in item.title.lower() or
                query in item.launcher.lower() or
                query in (item.window_class_hint or "").lower() or
                query in (item.category or "").lower() or
                query in item.app_id.lower())
        ]
        self._display_scanned_items(filtered)

    def _display_scanned_items(self, items: List[ScannedApp]):
        self.table_scanned.setRowCount(0)
        for row, item in enumerate(items):
            self.table_scanned.insertRow(row)
            
            # Column 0: Launcher / Type / Category
            type_label = f"{item.launcher}"
            if item.item_type == "app" and item.category and item.category != "Application":
                type_label = f"{item.launcher} • {item.category}"
            self.table_scanned.setItem(row, 0, QtWidgets.QTableWidgetItem(type_label))
            
            # Column 1: Title / Name
            self.table_scanned.setItem(row, 1, QtWidgets.QTableWidgetItem(item.title))
            
            # Column 2: Window class hint or app ID
            self.table_scanned.setItem(row, 2, QtWidgets.QTableWidgetItem(item.window_class_hint or item.app_id))

            # Column 3: Add Rule Button
            btn_add = QtWidgets.QPushButton("+ Add Rule")
            btn_add.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            btn_add.clicked.connect(lambda _, it=item: self._on_add_rule_from_scanned_item(it))
            self.table_scanned.setCellWidget(row, 3, btn_add)

    def _on_add_rule_from_scanned_item(self, item: ScannedApp):
        unique_prof = self.mgr.get_unique_profile_filename(item.title)
        rule = GameRule(
            name=item.title,
            pattern=item.window_class_hint or item.title.lower(),
            target_slot=5,
            profile_name=unique_prof,
            enabled=True,
        )
        dlg = RuleEditDialog(self, mgr=self.mgr, rule=rule, is_new=True)
        if dlg.exec():
            new_rule = dlg.get_rule()
            new_rule = self._create_and_save_rule_profile(new_rule, is_new=True)
            rules = self.mgr.get_rules()
            rules.append(new_rule)
            self.mgr.save_rules(rules)
            self._populate_rules()
            self.watcher.reload()

    def _create_and_save_rule_profile(self, rule: GameRule, is_new: bool = True) -> GameRule:
        """Ensures that for Slot 5, a dedicated, new profile JSON is created on disk and never reuses other profiles."""
        if rule.target_slot == 5:
            if is_new:
                unique_filename = self.mgr.get_unique_profile_filename(rule.profile_name or rule.name)
            else:
                unique_filename = rule.profile_name or f"{rule.name}.json"
                if not unique_filename.endswith(".json"):
                    unique_filename += ".json"

            rule.profile_name = unique_filename
            if not (self.mgr.library_dir / unique_filename).exists():
                p_dict = self.mgr.create_default_profile_dict(unique_filename)
                self.mgr.save_profile_to_library(unique_filename, p_dict)
        return rule

    def _on_add_rule_from_game(self, game: ScannedApp):
        self._on_add_rule_from_scanned_item(game)

    def _on_add_rule(self):
        dlg = RuleEditDialog(self, mgr=self.mgr, is_new=True)
        if dlg.exec():
            new_rule = dlg.get_rule()
            new_rule = self._create_and_save_rule_profile(new_rule, is_new=True)
            rules = self.mgr.get_rules()
            rules.append(new_rule)
            self.mgr.save_rules(rules)
            self._populate_rules()
            self.watcher.reload()

    def _on_capture_quick(self):
        dlg = RuleEditDialog(self, mgr=self.mgr, is_new=True)
        dlg._on_capture_window()
        if dlg.exec():
            new_rule = dlg.get_rule()
            new_rule = self._create_and_save_rule_profile(new_rule, is_new=True)
            rules = self.mgr.get_rules()
            rules.append(new_rule)
            self.mgr.save_rules(rules)
            self._populate_rules()
            self.watcher.reload()

    def _on_edit_buttons_for_rule(self):
        row = self.table_rules.currentRow()
        rules = self.mgr.get_rules()
        if not (0 <= row < len(rules)):
            QtWidgets.QMessageBox.information(self, "Select Rule", "Please select a game rule from the table first.")
            return

        rule = rules[row]
        main_win = self.window()
        if not hasattr(main_win, "tab_widget") or not hasattr(main_win, "config"):
            return

        # Case 1: Resident Slot (Slots 2, 3, or 4)
        if rule.target_slot in (2, 3, 4):
            # Target slot directly corresponds to hardware tab index (0=Slot 1, 1=Slot 2, 2=Slot 3, 3=Slot 4)
            slot_idx = rule.target_slot - 1
            if 0 <= slot_idx < main_win.tab_widget.count():
                main_win.tab_widget.setCurrentIndex(slot_idx)
                if hasattr(main_win, "device_status"):
                    main_win.device_status.setText(f"Editing buttons for '{rule.name}' (Slot {rule.target_slot}). Click 'Apply to Mouse' to save.")
            return

        # Case 2: Dynamic Staging (Slot 5)
        # Record this game profile as the active staged profile for Slot 5
        settings = self.mgr.get_settings()
        settings.staged_slot5_profile = rule.profile_name
        self.mgr.save_settings(settings)
        self.watcher.reload()

        # Load rule.profile_name into Slot 5 tab so the user can edit its bindings
        profile_data = self.mgr.load_profile_from_library(rule.profile_name)
        if profile_data:
            # Staging data exists, apply to Profile 5 model in memory
            p5 = main_win.config.profiles.get(5)
            if p5:
                p5.name = profile_data.get("name", rule.name)
                p5.report_rate = profile_data.get("report_rate", p5.report_rate)
                p5.resolutions = profile_data.get("resolutions", p5.resolutions)
                p5.resolution_default_index = profile_data.get("resolution_default_index", p5.resolution_default_index)
                p5.resolution_shift_index = profile_data.get("resolution_shift_index", p5.resolution_shift_index)
                # Buttons
                if "buttons" in profile_data:
                    from core.models import ButtonAction
                    p5.buttons = [ButtonAction.from_dict(b) if isinstance(b, dict) else b for b in profile_data["buttons"]]
                if "gbuttons" in profile_data:
                    from core.models import ButtonAction
                    p5.gbuttons = [ButtonAction.from_dict(b) if isinstance(b, dict) else b for b in profile_data["gbuttons"]]
        else:
            # If no library file exists yet for this game, initialize it with fresh default buttons
            profile_data = self.mgr.create_default_profile_dict(rule.profile_name or rule.name)
            self.mgr.save_profile_to_library(rule.profile_name or rule.name, profile_data)
            p5 = main_win.config.profiles.get(5)
            if p5:
                p5.name = rule.name
                from core.models import create_default_buttons
                p5.buttons = create_default_buttons()
                p5.gbuttons = create_default_buttons()

        # Switch to Profile 5 tab
        slot5_idx = 4
        if 0 <= slot5_idx < main_win.tab_widget.count():
            main_win._rebuild_tabs(target_index=slot5_idx)
            if hasattr(main_win, "device_status"):
                main_win.device_status.setText(f"Loaded '{rule.name}' into Slot 5 (Dynamic Staging). Click 'Apply to Mouse' to save.")

    def _on_edit_rule(self):
        row = self.table_rules.currentRow()
        rules = self.mgr.get_rules()
        if 0 <= row < len(rules):
            dlg = RuleEditDialog(self, mgr=self.mgr, rule=rules[row], is_new=False)
            if dlg.exec():
                updated_rule = dlg.get_rule()
                updated_rule = self._create_and_save_rule_profile(updated_rule, is_new=False)
                rules[row] = updated_rule
                self.mgr.save_rules(rules)
                self._populate_rules()
                self.watcher.reload()

    def _on_delete_rule(self):
        row = self.table_rules.currentRow()
        rules = self.mgr.get_rules()
        if 0 <= row < len(rules):
            r = rules[row]
            if QtWidgets.QMessageBox.question(self, "Delete Rule", f"Delete rule for '{r.name}'?") == QtWidgets.QMessageBox.StandardButton.Yes:
                rules.pop(row)
                self.mgr.save_rules(rules)
                self._populate_rules()
                self.watcher.reload()

    def _on_toggle_autoswitch(self, enabled: bool):
        settings = self.mgr.get_settings()
        settings.enabled = enabled
        self.mgr.save_settings(settings)
        self.watcher.reload()
        if enabled:
            self.lbl_status.setText("Auto-Switching: Active")
            self.lbl_status.setStyleSheet("color: #4ade80; font-weight: bold; padding: 4px 8px; background: #1f2937; border-radius: 4px;")
        else:
            self.lbl_status.setText("Auto-Switching: Disabled (Manual Mode)")
            self.lbl_status.setStyleSheet("color: #f87171; font-weight: bold; padding: 4px 8px; background: #1f2937; border-radius: 4px;")

    def _on_default_slot_changed(self):
        slot = self.combo_default_slot.currentData()
        settings = self.mgr.get_settings()
        settings.default_slot = slot
        self.mgr.save_settings(settings)
        self.watcher.reload()

    def _on_poll_interval_changed(self):
        val = self.combo_poll_interval.currentData()
        if val:
            settings = self.mgr.get_settings()
            settings.poll_interval_ms = val
            self.mgr.save_settings(settings)
            self.watcher.reload()

    def _on_profile_switched_callback(self, slot: int, label: Optional[str]):
        QtCore.QMetaObject.invokeMethod(
            self,
            "_update_status_ui",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(int, slot),
            QtCore.Q_ARG(str, label or "")
        )

    @QtCore.Slot(int, str)
    def _update_status_ui(self, slot: int, label: str):
        self.lbl_status.setText(f"Active: Slot {slot} ({label})")
        # Refresh Active Staged Game badge on Profile 5 tab if it exists
        main_win = self.window()
        if hasattr(main_win, "tab_widget"):
            for i in range(main_win.tab_widget.count()):
                tab = main_win.tab_widget.widget(i)
                if getattr(tab, "profile_id", None) == 5 and hasattr(tab, "lbl_staged_game"):
                    staged_name = self.mgr.get_settings().staged_slot5_profile
                    if staged_name:
                        clean_name = staged_name.replace(".json", "")
                        tab.lbl_staged_game.setText(f"Active Staged Game: {clean_name}")
                    else:
                        tab.lbl_staged_game.setText("Active Staged Game: None (Default Slot 5)")
