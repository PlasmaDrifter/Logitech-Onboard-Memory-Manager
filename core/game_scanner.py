from __future__ import annotations
import os
import re
import sqlite3
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class ScannedGame:
    title: str
    launcher: str  # 'Steam', 'Lutris', 'Heroic (Epic)', 'Heroic (GOG)', 'Custom'
    app_id: str
    executable: str
    window_class_hint: str

class GameScanner:
    """Scans local systems for games installed via Steam, Lutris, and Heroic."""

    @staticmethod
    def get_all_games() -> List[ScannedGame]:
        games: List[ScannedGame] = []
        games.extend(GameScanner.scan_steam())
        games.extend(GameScanner.scan_lutris())
        games.extend(GameScanner.scan_heroic())
        return games

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
