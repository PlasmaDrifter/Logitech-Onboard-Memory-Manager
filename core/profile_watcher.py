from __future__ import annotations
import os
import time
import subprocess
import logging
import threading
from typing import Optional, Callable
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
        combined = f"{wc_lower} {wt_lower}".strip()
        if not combined:
            return None

        # Do not match launcher client windows (Steam store/library, Lutris, Heroic)
        LAUNCHER_CLASSES = {"steam", "lutris", "heroic", "com.heroicgameslauncher.hgl"}
        if wc_lower in LAUNCHER_CLASSES:
            return None

        for rule in self.rules:
            if not rule.enabled:
                continue
            p = rule.pattern.lower().strip()
            name_p = rule.name.lower().strip()
            # Match on pattern in window class or title (pattern must be part of window, NOT reverse)
            if p and (p in wc_lower or p in wt_lower):
                return rule
            if name_p and len(name_p) >= 3 and (name_p in wt_lower or name_p in wc_lower):
                return rule
        return None

    def _watch_loop(self) -> None:
        while self._running:
            if not self.settings.enabled:
                time.sleep(1.0)
                continue

            try:
                # Scheduled backup pruning (runs on startup and every hour)
                now = time.time()
                if now - self._last_prune_time >= self._prune_interval_sec:
                    self._last_prune_time = now
                    try:
                        prune_backups(50)
                    except Exception as pe:
                        logger.debug(f"Periodic backup pruning error: {pe}")

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

            poll_sec = max(0.1, self.settings.poll_interval_ms / 1000.0)
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

            if staged == req_profile:
                # Already staged! Instant switch (<5ms, 0 flash writes)
                if self._last_active_slot != 5:
                    logger.info(f"Switching to already staged Slot 5 for {rule.name} ({req_profile})")
                    self.backend.set_active_profile(5)
                    self._last_active_slot = 5
                    self._current_matched_rule = rule
                    if self.on_profile_switched:
                        self.on_profile_switched(5, rule.name)
            else:
                # Different overflow game! Flash profile to Slot 5
                logger.info(f"Staging new profile '{req_profile}' into Slot 5 for {rule.name}")
                p_data = self.mgr.load_profile_from_library(req_profile)
                if p_data:
                    ok, msg = self.backend.flash_single_profile(5, p_data)
                    if ok:
                        self.settings.staged_slot5_profile = req_profile
                        self.mgr.save_settings(self.settings)
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
