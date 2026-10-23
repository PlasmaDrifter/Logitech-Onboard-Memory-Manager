from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class GameRule:
    name: str                           # Display title (e.g. "Counter-Strike 2")
    pattern: str                        # Window class or process name substring / regex (e.g. "steam_app_730", "cs2")
    target_slot: int                    # Target hardware slot: 2, 3, 4 (resident), or 5 (dynamic staging)
    profile_name: str                   # Profile name in library (e.g. "CS2 Competitive.json")
    enabled: bool = True
    match_type: str = "window_class"    # "window_class" or "process"

@dataclass
class WatcherSettings:
    enabled: bool = True
    poll_interval_ms: int = 1000
    default_slot: int = 1               # Default desktop / alt-tab slot (1-4)
    staged_slot5_profile: str = ""      # Last profile flashed into slot 5

class ProfileLibraryManager:
    """Manages the disk-based profile library, game rules, and watcher settings."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base_dir = Path.home() / ".config" / "logitech-onboard"
        else:
            self.base_dir = Path(base_dir)

        self.library_dir = self.base_dir / "library"
        self.rules_file = self.base_dir / "game_rules.json"
        self.settings_file = self.base_dir / "watcher_settings.json"

        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.library_dir.mkdir(parents=True, exist_ok=True)

    def get_settings(self) -> WatcherSettings:
        if self.settings_file.is_file():
            try:
                data = json.loads(self.settings_file.read_text(encoding="utf-8"))
                return WatcherSettings(**data)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        return WatcherSettings()

    def save_settings(self, settings: WatcherSettings) -> None:
        try:
            self.settings_file.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get_rules(self) -> List[GameRule]:
        if self.rules_file.is_file():
            try:
                data = json.loads(self.rules_file.read_text(encoding="utf-8"))
                return [GameRule(**item) for item in data]
            except Exception as e:
                logger.error(f"Failed to load game rules: {e}")
        return []

    def save_rules(self, rules: List[GameRule]) -> None:
        try:
            data = [asdict(r) for r in rules]
            self.rules_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save game rules: {e}")

    def list_profiles(self) -> List[str]:
        """Returns sorted list of profile file names in the library."""
        return sorted([f.name for f in self.library_dir.glob("*.json")])

    def save_profile_to_library(self, name: str, profile_dict: Dict[str, Any]) -> Path:
        """Saves a profile JSON object to the library directory."""
        if not name.endswith(".json"):
            filename = f"{name}.json"
        else:
            filename = name
        target = self.library_dir / filename
        target.write_text(json.dumps(profile_dict, indent=2), encoding="utf-8")
        return target

    def load_profile_from_library(self, filename: str) -> Optional[Dict[str, Any]]:
        """Loads profile dict from the library by filename."""
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        target = self.library_dir / filename
        if target.is_file():
            try:
                return json.loads(target.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load profile {filename}: {e}")
        return None
