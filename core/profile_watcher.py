from __future__ import annotations
import os
import time
import subprocess
import logging
import threading
from typing import Optional, Callable
from pathlib import Path
from .profile_library import ProfileLibraryManager, GameRule, WatcherSettings
from .backend import MouseBackend, prune_backups

logger = logging.getLogger(__name__)

class ProfileWatcher:
    """Monitors the active window / processes and dynamically engages mouse profile slots."""

    def __init__(self, backend: Optional[MouseBackend] = None, mgr: Optional[ProfileLibraryManager] = None):
        self.mgr = mgr or ProfileLibraryManager()
        self.backend = backend or MouseBackend("G502")
        self.settings: WatcherSettings = self.mgr.get_settings()
        self.rules = self.mgr.get_rules()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_active_slot: Optional[int] = None
        self._current_matched_rule: Optional[GameRule] = None
        self._last_prune_time: float = 0.0
        self._prune_interval_sec: float = 3600.0  # Hourly scheduled pruning

        # Battery / charging state tracking
        self._last_battery_status: Optional[str] = None
        self._charging_enforce_countdown: int = 0
        self._last_charging_check: float = 0.0

        # Automatic file modification tracking
        self._last_rules_mtime: float = self.mgr.rules_file.stat().st_mtime if self.mgr.rules_file.exists() else 0.0
        self._last_settings_mtime: float = self.mgr.settings_file.stat().st_mtime if self.mgr.settings_file.exists() else 0.0
        self._staged_slot5_mtime: float = 0.0

        # Callbacks for GUI updates
        self.on_profile_switched: Optional[Callable[[int, Optional[str]], None]] = None

    def start(self) -> None:
        if self._running:
            return
        self.settings = self.mgr.get_settings()
        self.rules = self.mgr.get_rules()
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("ProfileWatcher started.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("ProfileWatcher stopped.")

    def reload(self) -> None:
        """Reloads settings and rules from disk without stopping the thread."""
        self.settings = self.mgr.get_settings()
        self.rules = self.mgr.get_rules()

    def _check_config_mtime(self) -> None:
        """Automatically detects on-disk changes to rules and settings and reloads them."""
        try:
            r_mtime = self.mgr.rules_file.stat().st_mtime if self.mgr.rules_file.exists() else 0.0
            s_mtime = self.mgr.settings_file.stat().st_mtime if self.mgr.settings_file.exists() else 0.0
            if r_mtime != self._last_rules_mtime or s_mtime != self._last_settings_mtime:
                self._last_rules_mtime = r_mtime
                self._last_settings_mtime = s_mtime
                self.reload()
                logger.info(f"Auto-reloaded rules & settings from disk ({len(self.rules)} rules active)")
        except Exception as e:
            logger.debug(f"Config mtime check error: {e}")

    def get_active_window_info(self) -> tuple[str, str]:
        """Retrieves (window_class, window_title) on KDE Wayland or X11."""
        win_class = ""
        win_title = ""
        try:
            res_c = subprocess.run(
                ["kdotool", "getactivewindow", "getwindowclassname"],
                capture_output=True, text=True, timeout=0.25
            )
            if res_c.returncode == 0:
                win_class = res_c.stdout.strip()
            res_n = subprocess.run(
                ["kdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=0.25
            )
            if res_n.returncode == 0:
                win_title = res_n.stdout.strip()
            if win_class or win_title:
                return win_class, win_title
        except Exception:
            pass

        try:
            res_c = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowclassname"],
                capture_output=True, text=True, timeout=0.25
            )
            if res_c.returncode == 0:
                win_class = res_c.stdout.strip()
            res_n = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=0.25
            )
            if res_n.returncode == 0:
                win_title = res_n.stdout.strip()
            if win_class or win_title:
                return win_class, win_title
        except Exception:
            pass

        return "", ""

    def _match_active_rule(self, win_class: str, win_title: str = "") -> Optional[GameRule]:
        wc_lower = win_class.lower() if win_class else ""
        wt_lower = win_title.lower() if win_title else ""
        if not wc_lower and not wt_lower:
            return None

        # Classify if window is a generic desktop app / browser / utility
        NON_GAME_EXACT = {
            "steam", "steamwebhelper", "lutris", "heroic", "com.heroicgameslauncher.hgl",
            "epicgameslauncher", "gog-galaxy", "itch",
            "xwaylandvideobridge", "krunner", "plasmashell", "gnome-shell",
            "logitech-onboard-gui", "omm-linux", "omm"
        }
        NON_GAME_SUBSTRINGS = {
            "chrome", "firefox", "chromium", "brave", "edge", "opera", "vivaldi", "zen",
            "antigravity", "code", "cursor", "vscodium", "sublime",
            "gedit", "kate", "kwrite", "konsole", "terminal", "alacritty",
            "kitty", "foot", "wezterm", "ptyxis", "xterm",
            "dolphin", "nautilus", "thunar", "nemo", "pcmanfm"
        }
        is_non_game_app = False
        if not wc_lower.startswith("steam_app_"):
            if wc_lower in NON_GAME_EXACT or any(sub in wc_lower for sub in NON_GAME_SUBSTRINGS):
                is_non_game_app = True

        for rule in self.rules:
            if not rule.enabled:
                continue
            p = rule.pattern.lower().strip()
            if not p:
                continue

            # 1. Exact or substring match on window class always takes precedence (allows adding Chrome, Kate, etc.)
            if p in wc_lower:
                return rule

            # 2. Window title matching is allowed only for actual games, never for browsers/editors/utilities
            if not is_non_game_app and p in wt_lower:
                return rule

        return None

    @staticmethod
    def _get_battery_status() -> Optional[str]:
        """Reads kernel power supply status for connected Logitech mouse."""
        ps = Path("/sys/class/power_supply")
        if not ps.exists():
            return None
        try:
            for p in sorted(ps.glob("hidpp_battery_*")):
                sf = p / "status"
                if sf.exists():
                    return sf.read_text().strip()
            for p in ps.glob("*"):
                mfg = p / "manufacturer"
                if mfg.exists() and "logitech" in mfg.read_text().lower():
                    sf = p / "status"
                    if sf.exists():
                        return sf.read_text().strip()
        except Exception:
            pass
        return None

    def _watch_loop(self) -> None:
        try:
            self.backend.enforce_lighting_state()
        except Exception as le:
            logger.debug(f"Initial lighting enforcement error: {le}")

        while self._running:
            self._check_config_mtime()
            if not self.settings.enabled:
                time.sleep(1.0)
                continue

            try:
                now = time.time()

                # Scheduled backup pruning (runs on startup and every hour)
                if now - self._last_prune_time >= self._prune_interval_sec:
                    self._last_prune_time = now
                    try:
                        prune_backups(50)
                    except Exception as pe:
                        logger.debug(f"Periodic backup pruning error: {pe}")

                # Battery charging status monitoring & RGB enforcement
                b_status = self._get_battery_status()
                if b_status is not None:
                    if b_status != self._last_battery_status:
                        logger.info(f"Mouse battery status changed: {self._last_battery_status} -> {b_status}")
                        self._last_battery_status = b_status
                        self.backend.enforce_lighting_state()
                        if b_status == "Charging":
                            self._charging_enforce_countdown = 3
                    elif b_status == "Charging":
                        if self._charging_enforce_countdown > 0:
                            self._charging_enforce_countdown -= 1
                            self.backend.enforce_lighting_state()
                        elif now - self._last_charging_check >= 10.0:
                            self._last_charging_check = now
                            self.backend.enforce_lighting_state()
                else:
                    self._last_battery_status = None

                win_class, win_title = self.get_active_window_info()
                rule = self._match_active_rule(win_class, win_title)

                if rule:
                    # Mapped game window is active (Game Lock enforced)
                    self._handle_game_rule(rule)
                else:
                    # Unmapped window / desktop / browser (Alt-Tab) -> Restore default slot
                    self._handle_default_slot()

            except Exception as e:
                logger.debug(f"Watcher loop exception: {e}")

            poll_sec = max(0.05, self.settings.poll_interval_ms / 1000.0)
            time.sleep(poll_sec)

    def _handle_game_rule(self, rule: GameRule) -> None:
        target_slot = rule.target_slot

        if target_slot in (2, 3, 4):
            # Resident hardware slot: instant HID++ switch (<5ms, 0 flash writes)
            if self._last_active_slot != target_slot:
                logger.info(f"Switching to Resident Slot {target_slot} for {rule.name}")
                self.backend.set_active_profile(target_slot)
                self._last_active_slot = target_slot
                self._current_matched_rule = rule
                if self.on_profile_switched:
                    self.on_profile_switched(target_slot, rule.name)

        elif target_slot == 5:
            # Dynamic staging slot
            staged = self.settings.staged_slot5_profile
            req_profile = rule.profile_name
            p_file = self.mgr.library_dir / req_profile
            file_mtime = p_file.stat().st_mtime if p_file.exists() else 0.0

            if staged == req_profile and file_mtime <= self._staged_slot5_mtime:
                # Already staged and up-to-date! Instant switch (<5ms, 0 flash writes)
                if self._last_active_slot != 5:
                    logger.info(f"Switching to already staged Slot 5 for {rule.name} ({req_profile})")
                    self.backend.set_active_profile(5)
                    self._last_active_slot = 5
                    self._current_matched_rule = rule
                    if self.on_profile_switched:
                        self.on_profile_switched(5, rule.name)
            else:
                # Different overflow game or profile modified on disk! Flash profile to Slot 5
                logger.info(f"Staging profile '{req_profile}' into Slot 5 for {rule.name}")
                p_data = self.mgr.load_profile_from_library(req_profile)
                if p_data:
                    ok, msg = self.backend.flash_single_profile(5, p_data)
                    if ok:
                        self.settings.staged_slot5_profile = req_profile
                        self._staged_slot5_mtime = file_mtime
                        self.mgr.save_settings(self.settings)
                        self._last_settings_mtime = self.mgr.settings_file.stat().st_mtime if self.mgr.settings_file.exists() else 0.0
                        self._last_active_slot = 5
                        self._current_matched_rule = rule
                        if self.on_profile_switched:
                            self.on_profile_switched(5, rule.name)
                    else:
                        logger.error(f"Failed to flash Slot 5: {msg}")
                else:
                    # Fallback switch to slot 5 directly
                    self.backend.set_active_profile(5)
                    self._last_active_slot = 5

    def _handle_default_slot(self) -> None:
        def_slot = self.settings.default_slot or 1
        if self._last_active_slot != def_slot:
            logger.info(f"Alt-Tab detected: Restoring default Slot {def_slot}")
            self.backend.set_active_profile(def_slot)
            self._last_active_slot = def_slot
            self._current_matched_rule = None
            if self.on_profile_switched:
                self.on_profile_switched(def_slot, "Desktop / Default")
