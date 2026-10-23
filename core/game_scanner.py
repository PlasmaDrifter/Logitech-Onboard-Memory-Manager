from __future__ import annotations
import os
import re
import sqlite3
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class ScannedApp:
    title: str
    launcher: str  # 'Steam', 'Lutris', 'Heroic (Epic)', 'Heroic (GOG)', 'System', 'Flatpak', 'Snap', 'User App'
    app_id: str
    executable: str
    window_class_hint: str
    item_type: str = "game"  # 'game' or 'app'
    category: str = "Game"   # 'Game', 'Web Browser', 'Development', 'Audio/Video', 'Graphics', 'Office', 'Utility', 'System', 'Application'


# Backward compatibility alias
ScannedGame = ScannedApp


class GameScanner:
    """Scans local system for games and desktop applications across FreeDesktop, GNOME, and KDE Plasma."""

    @staticmethod
    def get_scanned_items() -> Tuple[List[ScannedApp], List[ScannedApp]]:
        """Returns (games, applications) discovered on the local system."""
        games: List[ScannedApp] = []
        apps: List[ScannedApp] = []

        seen_game_titles = set()
        seen_game_hints = set()

        # 1. Steam, Lutris, Heroic games (Highest accuracy for game launchers)
        for g in GameScanner.scan_steam():
            games.append(g)
            seen_game_titles.add(g.title.lower())
            if g.window_class_hint:
                seen_game_hints.add(g.window_class_hint.lower())

        for g in GameScanner.scan_lutris():
            if g.title.lower() not in seen_game_titles:
                games.append(g)
                seen_game_titles.add(g.title.lower())
                if g.window_class_hint:
                    seen_game_hints.add(g.window_class_hint.lower())

        for g in GameScanner.scan_heroic():
            if g.title.lower() not in seen_game_titles:
                games.append(g)
                seen_game_titles.add(g.title.lower())
                if g.window_class_hint:
                    seen_game_hints.add(g.window_class_hint.lower())

        # 2. Desktop applications from FreeDesktop .desktop files (GNOME, KDE Plasma, XFCE, etc.)
        d_games, d_apps = GameScanner.scan_desktop_apps()

        for g in d_games:
            t_low = g.title.lower()
            h_low = g.window_class_hint.lower()
            if t_low not in seen_game_titles and h_low not in seen_game_hints:
                games.append(g)
                seen_game_titles.add(t_low)
                if h_low:
                    seen_game_hints.add(h_low)

        apps.extend(d_apps)

        games.sort(key=lambda x: x.title.lower())
        apps.sort(key=lambda x: x.title.lower())
        return games, apps

    @staticmethod
    def get_all_games() -> List[ScannedApp]:
        games, _ = GameScanner.get_scanned_items()
        return games

    @staticmethod
    def get_all_apps() -> List[ScannedApp]:
        _, apps = GameScanner.get_scanned_items()
        return apps

    @staticmethod
    def scan_desktop_apps() -> Tuple[List[ScannedApp], List[ScannedApp]]:
        """Scans standard FreeDesktop .desktop directories for applications and games."""
        games: List[ScannedApp] = []
        apps: List[ScannedApp] = []

        home = Path.home()
        desktop_dirs: List[Path] = [
            home / ".local/share/applications",
            Path("/usr/local/share/applications"),
            Path("/usr/share/applications"),
            Path("/var/lib/flatpak/exports/share/applications"),
            home / ".local/share/flatpak/exports/share/applications",
            Path("/var/lib/snapd/desktop/applications"),
            Path("/snap/share/applications"),
        ]

        # Include custom directories from XDG_DATA_DIRS
        xdg_dirs = os.environ.get("XDG_DATA_DIRS", "")
        if xdg_dirs:
            for xd in xdg_dirs.split(":"):
                p = Path(xd.strip()) / "applications"
                if p not in desktop_dirs:
                    desktop_dirs.append(p)

        seen_keys = set()

        for d in desktop_dirs:
            if not d.is_dir():
                continue

            for desktop_file in d.glob("**/*.desktop"):
                try:
                    txt = desktop_file.read_text(encoding="utf-8", errors="ignore")
                    entry_dict = GameScanner._parse_desktop_entry(txt)
                    if not entry_dict:
                        continue

                    # Skip non-applications or hidden entries
                    if entry_dict.get("Type", "Application") != "Application":
                        continue
                    if entry_dict.get("NoDisplay", "false").lower() == "true":
                        continue
                    if entry_dict.get("Hidden", "false").lower() == "true":
                        continue

                    name = entry_dict.get("Name", "").strip()
                    if not name:
                        continue

                    exec_val = entry_dict.get("Exec", "").strip()
                    wmclass = entry_dict.get("StartupWMClass", "").strip()
                    cats = entry_dict.get("Categories", "").strip()

                    # Resolve window class hint
                    if not wmclass:
                        if exec_val:
                            bin_part = re.split(r"\s+", exec_val)[0].strip("'\"")
                            bin_name = Path(bin_part).name
                            if bin_name and not bin_name.endswith((".sh", ".py")) and bin_name not in ["python", "python3", "bash", "sh", "flatpak", "bwrap"]:
                                wmclass = bin_name
                        if not wmclass:
                            wmclass = desktop_file.stem

                    key = (name.lower(), wmclass.lower())
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    category = GameScanner._categorize(cats)
                    is_game = category == "Game" or "game" in cats.lower()

                    # Determine source launcher / package type
                    f_str = str(desktop_file)
                    txt_low = txt.lower()
                    exec_low = exec_val.lower()

                    if is_game:
                        if "flatpak" in f_str:
                            source = "Flatpak"
                        elif "snap" in f_str:
                            source = "Snap"
                        elif str(home) in f_str:
                            source = "User App"
                        else:
                            source = "System"
                    else:
                        # Desktop Applications: Repo, Flatpak, AppImage, User, Snap
                        if "x-appimage" in txt_low or ".appimage" in txt_low or "/applications/" in exec_low:
                            source = "AppImage"
                        elif "flatpak" in f_str or "flatpak run" in exec_low:
                            source = "Flatpak"
                        elif "snap" in f_str:
                            source = "Snap"
                        elif str(home) in f_str:
                            source = "User"
                        else:
                            source = "Repo"

                    item = ScannedApp(
                        title=name,
                        launcher=source,
                        app_id=desktop_file.stem,
                        executable=exec_val,
                        window_class_hint=wmclass,
                        item_type="game" if is_game else "app",
                        category=category,
                    )

                    if is_game:
                        games.append(item)
                    else:
                        apps.append(item)

                except Exception:
                    pass

        return games, apps

    @staticmethod
    def _parse_desktop_entry(text: str) -> Dict[str, str]:
        """Parses a FreeDesktop .desktop file text into key-value pairs for the [Desktop Entry] section."""
        data = {}
        in_entry = False
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("[") and s.endswith("]"):
                in_entry = s == "[Desktop Entry]"
                continue
            if in_entry and "=" in s:
                k, v = s.split("=", 1)
                k = k.strip()
                if k not in data:
                    data[k] = v.strip()
        return data

    @staticmethod
    def _categorize(cats: str) -> str:
        """Determines user-friendly category string from desktop Categories line."""
        c = cats.lower()
        if "game" in c:
            return "Game"
        elif "webbrowser" in c or "browser" in c:
            return "Web Browser"
        elif any(k in c for k in ["development", "ide", "texteditor", "programming"]):
            return "Development"
        elif any(k in c for k in ["audiovideo", "audio", "video", "player", "recorder", "music"]):
            return "Audio / Video"
        elif any(k in c for k in ["graphics", "photography", "2dgraphics", "vectorgraphics", "rastergraphics"]):
            return "Graphics"
        elif any(k in c for k in ["office", "wordprocessor", "spreadsheet", "presentation", "document"]):
            return "Office"
        elif any(k in c for k in ["terminalemulator", "system", "settings", "hardware"]):
            return "System"
        elif any(k in c for k in ["utility", "accessories", "filemanager"]):
            return "Utility"
        elif "network" in c:
            return "Network / Internet"
        return "Application"

    @staticmethod
    def scan_steam() -> List[ScannedGame]:
        games: List[ScannedGame] = []
        home = Path.home()
        steam_vdfs = [
            home / ".local/share/Steam/steamapps/libraryfolders.vdf",
            home / ".steam/steam/steamapps/libraryfolders.vdf",
            home / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/libraryfolders.vdf",
        ]

        seen_appids = set()
        library_paths = set()

        for vdf in steam_vdfs:
            if vdf.is_file():
                try:
                    text = vdf.read_text(encoding="utf-8", errors="ignore")
                    paths = re.findall(r'"path"\s+"([^"]+)"', text)
                    for p in paths:
                        library_paths.add(Path(p) / "steamapps")
                except Exception:
                    pass

        # Also add default paths
        for r in [home / ".local/share/Steam/steamapps", home / ".steam/steam/steamapps"]:
            if r.is_dir():
                library_paths.add(r)

        for lib in library_paths:
            if not lib.is_dir():
                continue
            for acf in lib.glob("appmanifest_*.acf"):
                try:
                    content = acf.read_text(encoding="utf-8", errors="ignore")
                    name_m = re.search(r'"name"\s+"([^"]+)"', content)
                    appid_m = re.search(r'"appid"\s+"([^"]+)"', content)
                    if name_m and appid_m:
                        title = name_m.group(1).strip()
                        appid = appid_m.group(1).strip()
                        # Ignore runtimes, proton, redistributables
                        if any(x in title.lower() for x in ["proton", "steam linux runtime", "steamworks common", "anti-cheat", "battleye"]):
                            continue
                        if appid in seen_appids:
                            continue
                        seen_appids.add(appid)
                        games.append(ScannedGame(
                            title=title,
                            launcher="Steam",
                            app_id=appid,
                            executable="",
                            window_class_hint=f"steam_app_{appid}"
                        ))
                except Exception:
                    pass

        return sorted(games, key=lambda g: g.title.lower())

    @staticmethod
    def scan_lutris() -> List[ScannedGame]:
        games: List[ScannedGame] = []
        home = Path.home()
        pga_paths = [
            home / ".local/share/lutris/pga.db",
            home / ".var/app/net.lutris.Lutris/data/lutris/pga.db",
        ]

        for pga in pga_paths:
            if pga.is_file():
                try:
                    conn = sqlite3.connect(pga)
                    c = conn.cursor()
                    c.execute("SELECT name, slug, runner, executable FROM games WHERE installed = 1")
                    for name, slug, runner, exe in c.fetchall():
                        # Exclude store launchers
                        if name in ["Epic Games Store", "Rockstar Games Launcher", "Ubisoft Connect", "EA App"]:
                            continue
                        games.append(ScannedGame(
                            title=name,
                            launcher="Lutris",
                            app_id=slug or "",
                            executable=exe or "",
                            window_class_hint=slug or ""
                        ))
                    conn.close()
                except Exception:
                    pass

        return sorted(games, key=lambda g: g.title.lower())

    @staticmethod
    def scan_heroic() -> List[ScannedGame]:
        games: List[ScannedGame] = []
        home = Path.home()
        heroic_dirs = [
            home / ".config/heroic",
            home / ".var/app/com.heroicgameslauncher.hgl/config/heroic",
        ]

        for hdir in heroic_dirs:
            if not hdir.is_dir():
                continue

            # Check store_cache/legendary_library.json (Epic Games)
            legendary = hdir / "store_cache/legendary_library.json"
            if legendary.is_file():
                try:
                    data = json.loads(legendary.read_text(encoding="utf-8", errors="ignore"))
                    items = data if isinstance(data, list) else data.get("library", [])
                    for item in items:
                        if not item.get("install", {}).get("is_dlc", False) and not item.get("is_dlc", False):
                            title = item.get("title")
                            app_name = item.get("app_name")
                            if title and app_name:
                                games.append(ScannedGame(
                                    title=title,
                                    launcher="Heroic (Epic)",
                                    app_id=app_name,
                                    executable=item.get("folder_name", ""),
                                    window_class_hint=item.get("folder_name", "")
                                ))
                except Exception:
                    pass

            # Check store_cache/gog_library.json (GOG)
            gog = hdir / "store_cache/gog_library.json"
            if gog.is_file():
                try:
                    data = json.loads(gog.read_text(encoding="utf-8", errors="ignore"))
                    items = data if isinstance(data, list) else data.get("games", [])
                    for item in items:
                        title = item.get("title")
                        app_name = item.get("app_name") or str(item.get("id", ""))
                        if title:
                            games.append(ScannedGame(
                                title=title,
                                launcher="Heroic (GOG)",
                                app_id=app_name,
                                executable="",
                                window_class_hint=""
                            ))
                except Exception:
                    pass

        return sorted(games, key=lambda g: g.title.lower())
