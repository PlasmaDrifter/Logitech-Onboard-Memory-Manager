from __future__ import annotations
import os
import subprocess
import time
from typing import Optional, List, Dict, Any
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from core.game_scanner import GameScanner, ScannedGame
from core.profile_library import ProfileLibraryManager, GameRule, WatcherSettings
from core.profile_watcher import ProfileWatcher
from core.service_manager import BackgroundServiceManager

class RuleEditDialog(QtWidgets.QDialog):
    """Dialog to create or edit a game auto-switching rule."""

    def __init__(self, parent=None, rule: Optional[GameRule] = None, available_profiles: List[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Game Rule" if rule else "Add Game Rule")
        self.resize(580, 360)
        self.setMinimumSize(540, 340)
        self.available_profiles = available_profiles or []
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

        self.combo_profile = QtWidgets.QComboBox()
        self.combo_profile.setMinimumHeight(32)
        self.combo_profile.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.combo_profile.setEditable(True)
        for p in self.available_profiles:
            self.combo_profile.addItem(p)

        self.lbl_profile = QtWidgets.QLabel("Library Profile:")
        self.lbl_profile_hint = QtWidgets.QLabel("Select a JSON profile from your disk library to stage into Slot 5 when this game runs.")
        self.lbl_profile_hint.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.lbl_profile_hint.setWordWrap(True)

        self.chk_enabled = QtWidgets.QCheckBox("Rule Enabled")
        self.chk_enabled.setChecked(True)

        if rule:
            self.edit_name.setText(rule.name)
            self.edit_pattern.setText(rule.pattern)
            idx = self.combo_slot.findData(rule.target_slot)
            if idx != -1:
                self.combo_slot.setCurrentIndex(idx)
            p_idx = self.combo_profile.findText(rule.profile_name)
            if p_idx != -1:
                self.combo_profile.setCurrentIndex(p_idx)
            else:
                self.combo_profile.setEditText(rule.profile_name)
            self.chk_enabled.setChecked(rule.enabled)

        form.addRow("Game Name:", self.edit_name)
        form.addRow("Match Pattern:", pattern_layout)
        form.addRow("Target Slot:", self.combo_slot)
        form.addRow(self.lbl_profile, self.combo_profile)
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
            self.combo_profile.setEnabled(False)
            self.combo_profile.setToolTip("Slot 2-4 use the settings already saved directly in that hardware slot on the mouse.")
            self.lbl_profile_hint.setText(f"Uses the hardware settings already flashed into Slot {target_slot} on the mouse.")
        else:
            # Slot 5 dynamic
            self.combo_profile.setEnabled(True)
            self.combo_profile.setToolTip("Profile from ~/.config/logitech-onboard/library/ to flash into Slot 5.")
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

    def get_rule(self) -> GameRule:
        return GameRule(
            name=self.edit_name.text().strip() or "Unnamed Game",
            pattern=self.edit_pattern.text().strip(),
            target_slot=self.combo_slot.currentData(),
            profile_name=self.combo_profile.currentText().strip(),
            enabled=self.chk_enabled.isChecked()
        )


class GamesTab(QtWidgets.QWidget):
    """Tab for managing Game Profile Auto-Switching, game library scanner, and rules."""

    def __init__(self, watcher: ProfileWatcher, parent=None):
        super().__init__(parent)
        self.watcher = watcher
        self.mgr = watcher.mgr
        self._init_ui()
        self.reload_data()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Top Control Bar: Master Auto-Switching Toggle & Default Profile
        top_bar = QtWidgets.QHBoxLayout()
        
        self.chk_enable_autoswitch = QtWidgets.QCheckBox("Enable Automatic Profile Switching (Game Lock Active)")
        self.chk_enable_autoswitch.setStyleSheet("font-weight: bold; font-size: 13px; color: #38bdf8;")
        self.chk_enable_autoswitch.toggled.connect(self._on_toggle_autoswitch)
        top_bar.addWidget(self.chk_enable_autoswitch)

        top_bar.addSpacing(20)

        lbl_def = QtWidgets.QLabel("Default Desktop Slot (Alt-Tab):")
        lbl_def.setStyleSheet("color: #9ca3af;")
        self.combo_default_slot = QtWidgets.QComboBox()
        self.combo_default_slot.addItem("Slot 1 (Recommended)", 1)
        self.combo_default_slot.addItem("Slot 2", 2)
        self.combo_default_slot.addItem("Slot 3", 3)
        self.combo_default_slot.addItem("Slot 4", 4)
        self.combo_default_slot.currentIndexChanged.connect(self._on_default_slot_changed)
        top_bar.addWidget(lbl_def)
        top_bar.addWidget(self.combo_default_slot)

        top_bar.addStretch()

        self.lbl_status = QtWidgets.QLabel("Active: Slot 1 (Desktop)")
        self.lbl_status.setStyleSheet("color: #4ade80; font-weight: bold; padding: 4px 8px; background: #1f2937; border-radius: 4px;")
        top_bar.addWidget(self.lbl_status)

        layout.addLayout(top_bar)

        # Background Service Control Panel
        svc_box = QtWidgets.QGroupBox("Background Service (Runs even when this app is closed)")
        svc_layout = QtWidgets.QHBoxLayout(svc_box)
        svc_layout.setContentsMargins(12, 10, 12, 10)

        self.lbl_svc_indicator = QtWidgets.QLabel("● Stopped")
        self.lbl_svc_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px; padding: 2px 6px; background: #18181c; border-radius: 4px;")
        svc_layout.addWidget(self.lbl_svc_indicator)

        self.btn_svc_start = QtWidgets.QPushButton("Start Service")
        self.btn_svc_start.clicked.connect(self._on_start_service)
        svc_layout.addWidget(self.btn_svc_start)

        self.btn_svc_stop = QtWidgets.QPushButton("Stop Service")
        self.btn_svc_stop.setObjectName("secondaryBtn")
        self.btn_svc_stop.clicked.connect(self._on_stop_service)
        svc_layout.addWidget(self.btn_svc_stop)

        svc_layout.addSpacing(15)

        self.chk_svc_autostart = QtWidgets.QCheckBox("Automatically start service on boot / login")
        self.chk_svc_autostart.toggled.connect(self._on_toggle_svc_autostart)
        svc_layout.addWidget(self.chk_svc_autostart)

        svc_layout.addStretch()
        layout.addWidget(svc_box)

        # Splitter: Rules Table on Top/Left, Scanned Installed Games on Bottom/Right
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        # 1. Rules Group
        rules_box = QtWidgets.QGroupBox("Game Auto-Switching Rules")
        rules_layout = QtWidgets.QVBoxLayout(rules_box)

        # Table
        self.table_rules = QtWidgets.QTableWidget(0, 5)
        self.table_rules.setHorizontalHeaderLabels(["Active", "Game Name", "Match Pattern", "Assigned Slot", "Library Profile"])
        self.table_rules.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_rules.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        rules_layout.addWidget(self.table_rules)

        # Rules Buttons
        r_btns = QtWidgets.QHBoxLayout()
        self.btn_add_rule = QtWidgets.QPushButton("+ Add Rule Manually")
        self.btn_add_rule.clicked.connect(self._on_add_rule)
        self.btn_capture_rule = QtWidgets.QPushButton("Capture Active Window")
        self.btn_capture_rule.setObjectName("secondaryBtn")
        self.btn_capture_rule.clicked.connect(self._on_capture_quick)
        self.btn_edit_buttons = QtWidgets.QPushButton("Edit Buttons")
        self.btn_edit_buttons.setToolTip("Customize mouse buttons for the selected game rule")
        self.btn_edit_buttons.clicked.connect(self._on_edit_buttons_for_rule)
        self.btn_edit_rule = QtWidgets.QPushButton("Edit Rule")
        self.btn_edit_rule.setObjectName("secondaryBtn")
        self.btn_edit_rule.clicked.connect(self._on_edit_rule)
        self.btn_delete_rule = QtWidgets.QPushButton("Delete Rule")
        self.btn_delete_rule.setObjectName("secondaryBtn")
        self.btn_delete_rule.clicked.connect(self._on_delete_rule)

        r_btns.addWidget(self.btn_edit_buttons)
        r_btns.addWidget(self.btn_add_rule)
        r_btns.addWidget(self.btn_capture_rule)
        r_btns.addWidget(self.btn_edit_rule)
        r_btns.addWidget(self.btn_delete_rule)
        r_btns.addStretch()
        rules_layout.addLayout(r_btns)

        # Allow double click to edit buttons directly
        self.table_rules.doubleClicked.connect(self._on_edit_buttons_for_rule)

        splitter.addWidget(rules_box)

        # 2. Installed Games Scanner Group
        scanner_box = QtWidgets.QGroupBox("Installed Games (Steam / Lutris / Heroic / Epic / GOG)")
        scanner_layout = QtWidgets.QVBoxLayout(scanner_box)

        filter_row = QtWidgets.QHBoxLayout()
        self.edit_search_games = QtWidgets.QLineEdit()
        self.edit_search_games.setPlaceholderText("Filter games by title or launcher...")
        self.edit_search_games.textChanged.connect(self._filter_scanned_games)
        self.btn_rescan = QtWidgets.QPushButton("Scan Games")
        self.btn_rescan.setObjectName("secondaryBtn")
        self.btn_rescan.clicked.connect(self._scan_installed_games)
        self.lbl_scan_status = QtWidgets.QLabel("Ready")
        self.lbl_scan_status.setStyleSheet("color: #9ca3af; font-size: 12px; margin-left: 8px;")
        filter_row.addWidget(self.edit_search_games)
        filter_row.addWidget(self.btn_rescan)
        filter_row.addWidget(self.lbl_scan_status)
        scanner_layout.addLayout(filter_row)

        self.table_scanned = QtWidgets.QTableWidget(0, 4)
        self.table_scanned.setHorizontalHeaderLabels(["Launcher", "Game Title", "App ID / Hint", "Action"])
        self.table_scanned.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_scanned.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table_scanned.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_scanned.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.table_scanned.setColumnWidth(3, 110)
        self.table_scanned.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        scanner_layout.addWidget(self.table_scanned)

        splitter.addWidget(scanner_box)
        layout.addWidget(splitter)

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

        self._populate_rules()
        self._scan_installed_games()
        self.refresh_service_status()

    def refresh_service_status(self):
        running = BackgroundServiceManager.is_running()
        enabled = BackgroundServiceManager.is_enabled()

        if running:
            self.lbl_svc_indicator.setText("● Running in Background")
            self.lbl_svc_indicator.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 13px; padding: 2px 6px; background: #14532d; border-radius: 4px;")
            self.btn_svc_start.setEnabled(False)
            self.btn_svc_stop.setEnabled(True)
        else:
            self.lbl_svc_indicator.setText("● Stopped")
            self.lbl_svc_indicator.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px; padding: 2px 6px; background: #450a0a; border-radius: 4px;")
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

    def _scan_installed_games(self):
        self.btn_rescan.setEnabled(False)
        self.lbl_scan_status.setText("Scanning Steam, Lutris, and Heroic...")
        self.lbl_scan_status.setStyleSheet("color: #3b82f6; font-size: 12px; font-weight: bold; margin-left: 8px;")
        QtWidgets.QApplication.processEvents()

        def do_scan():
            games = GameScanner.get_all_games()
            self._all_scanned_games = games
            self._display_scanned_games(games)
            self.lbl_scan_status.setText(f"Found {len(games)} games")
            self.lbl_scan_status.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: bold; margin-left: 8px;")
            self.btn_rescan.setEnabled(True)

        QtCore.QTimer.singleShot(50, do_scan)

    def _filter_scanned_games(self, text: str):
        if not hasattr(self, "_all_scanned_games"):
            return
        query = text.strip().lower()
        filtered = [
            g for g in self._all_scanned_games
            if query in g.title.lower() or query in g.launcher.lower() or query in g.window_class_hint.lower()
        ]
        self._display_scanned_games(filtered)

    def _display_scanned_games(self, games: List[ScannedGame]):
        self.table_scanned.setRowCount(0)
        for row, g in enumerate(games):
            self.table_scanned.insertRow(row)
            self.table_scanned.setItem(row, 0, QtWidgets.QTableWidgetItem(g.launcher))
            self.table_scanned.setItem(row, 1, QtWidgets.QTableWidgetItem(g.title))
            self.table_scanned.setItem(row, 2, QtWidgets.QTableWidgetItem(g.window_class_hint or g.app_id))

            btn_add = QtWidgets.QPushButton("+ Add Rule")
            btn_add.setStyleSheet("padding: 2px 8px; font-size: 11px;")
            btn_add.clicked.connect(lambda _, game=g: self._on_add_rule_from_game(game))
            self.table_scanned.setCellWidget(row, 3, btn_add)

    def _on_add_rule_from_game(self, game: ScannedGame):
        profiles = self.mgr.list_profiles()
        rule = GameRule(
            name=game.title,
            pattern=game.window_class_hint or game.title.lower(),
            target_slot=5,
            profile_name=profiles[0] if profiles else f"{game.title}.json"
        )
        dlg = RuleEditDialog(self, rule=rule, available_profiles=profiles)
        if dlg.exec():
            new_rule = dlg.get_rule()
            rules = self.mgr.get_rules()
            rules.append(new_rule)
            self.mgr.save_rules(rules)
            self._populate_rules()
            self.watcher.reload()

    def _on_add_rule(self):
        profiles = self.mgr.list_profiles()
        dlg = RuleEditDialog(self, available_profiles=profiles)
        if dlg.exec():
            new_rule = dlg.get_rule()
            rules = self.mgr.get_rules()
            rules.append(new_rule)
            self.mgr.save_rules(rules)
            self._populate_rules()
            self.watcher.reload()

    def _on_capture_quick(self):
        dlg = RuleEditDialog(self, available_profiles=self.mgr.list_profiles())
        dlg._on_capture_window()
        if dlg.exec():
            new_rule = dlg.get_rule()
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
                QtWidgets.QMessageBox.information(
                    self,
                    f"Editing {rule.name}",
                    f"Switched to 'Profile {rule.target_slot}' tab for {rule.name}.\n\n"
                    "Customize buttons or DPI stages, then click 'Apply to Mouse' in the top right to save."
                )
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
            # If no library file exists yet for this game, initialize it using current Slot 5
            p5 = main_win.config.profiles.get(5)
            if p5:
                p5.name = rule.name

        # Switch to Profile 5 tab
        slot5_idx = 4
        if 0 <= slot5_idx < main_win.tab_widget.count():
            main_win._rebuild_tabs(target_index=slot5_idx)
            QtWidgets.QMessageBox.information(
                self,
                f"Editing {rule.name}",
                f"Loaded profile for '{rule.name}' into Profile 5.\n\n"
                "Customize buttons or DPI stages, then click 'Apply to Mouse' to save and flash it."
            )

    def _on_edit_rule(self):
        row = self.table_rules.currentRow()
        rules = self.mgr.get_rules()
        if 0 <= row < len(rules):
            dlg = RuleEditDialog(self, rule=rules[row], available_profiles=self.mgr.list_profiles())
            if dlg.exec():
                rules[row] = dlg.get_rule()
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
