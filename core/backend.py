"""Backend communication module for Logitech Onboard Memory."""

import os
import sys
import yaml
import shutil
import datetime
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from .models import ButtonAction, Profile, OnboardConfig
from .keycodes import HID_KEYCODES
from .native_hidpp import NativeHIDPP

KNOWN_MACROS = {}

# Standard factory raw hardware chunks for new profiles (Left, Right, Middle, Wheel Tilt active; others blank)
FACTORY_RAW_CHUNKS = [
    bytes([0x80, 0x01, 0x00, 0x01]),  # Chunk 0: Left Click (B1)
    bytes([0x80, 0x01, 0x00, 0x02]),  # Chunk 1: Right Click (B2)
    bytes([0x80, 0x01, 0x00, 0x04]),  # Chunk 2: Middle Click (B3)
    b"\xff\xff\xff\xff",              # Chunk 3: Blank (B4)
    b"\xff\xff\xff\xff",              # Chunk 4: Blank (B6)
    b"\xff\xff\xff\xff",              # Chunk 5: Blank (B5)
    b"\xff\xff\xff\xff",              # Chunk 6: Blank (B7)
    b"\xff\xff\xff\xff",              # Chunk 7: Blank (B8)
    bytes([0x90, 0x4A, 0xFF, 0x00]),  # Chunk 8: Scroll Wheel Tilt Left (B9)
    bytes([0x90, 0x4B, 0xFF, 0x00]),  # Chunk 9: Scroll Wheel Tilt Right (B10)
    b"\xff\xff\xff\xff",              # Chunk 10: Blank (B11)
]

def decode_logitech_macro(bytes_chunk: bytes) -> str:
    i = 0
    keys_pressed = []
    modifiers = []

    MOD_MAP = {
        0x01E0: "Ctrl", 0x01E4: "Ctrl",
        0x01E1: "Shift", 0x01E5: "Shift", 0x20E5: "Shift",
        0x01E2: "Alt", 0x01E6: "Alt",
        0x01E3: "Super", 0x01E7: "Super",
    }

    while i < len(bytes_chunk):
        b = bytes_chunk[i]
        if b == 0xFF:
            break
        elif b == 0x43:  # Key Down
            if i + 2 < len(bytes_chunk):
                code = (bytes_chunk[i + 1] << 8) | bytes_chunk[i + 2]
                if code in MOD_MAP:
                    mod = MOD_MAP[code]
                    if mod not in modifiers:
                        modifiers.append(mod)
                else:
                    hid = code & 0xFF
                    kname = HID_KEYCODES.get(hid, f"Key 0x{hid:02X}")
                    if kname not in keys_pressed:
                        keys_pressed.append(kname)
                i += 3
            else:
                break
        elif b == 0x44:  # Key Up
            i += 3
        elif b == 0x40:  # Delay
            i += 3
        else:
            i += 1

    parts = modifiers + keys_pressed
    if parts:
        return " + ".join(parts)
    return ""


class ButtonYaml:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return f"Button({self.__dict__})"


class OnboardProfileYaml:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class OnboardProfilesYaml:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class LEDEffectSettingYaml:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _setup_yaml():
    yaml.SafeLoader.add_constructor("!Button", lambda l, n: ButtonYaml(**l.construct_mapping(n)))
    yaml.SafeLoader.add_constructor("!OnboardProfile", lambda l, n: OnboardProfileYaml(**l.construct_mapping(n)))
    yaml.SafeLoader.add_constructor("!OnboardProfiles", lambda l, n: OnboardProfilesYaml(**l.construct_mapping(n)))
    yaml.SafeLoader.add_constructor("!LEDEffectSetting", lambda l, n: LEDEffectSettingYaml(**l.construct_mapping(n)))

    yaml.Dumper.add_representer(ButtonYaml, lambda d, data: d.represent_mapping("!Button", data.__dict__))
    yaml.Dumper.add_representer(OnboardProfileYaml, lambda d, data: d.represent_mapping("!OnboardProfile", data.__dict__))
    yaml.Dumper.add_representer(OnboardProfilesYaml, lambda d, data: d.represent_mapping("!OnboardProfiles", data.__dict__))
    yaml.Dumper.add_representer(LEDEffectSettingYaml, lambda d, data: d.represent_mapping("!LEDEffectSetting", data.__dict__))


_setup_yaml()


def get_config_dir() -> Path:
    """Returns the base configuration directory, migrating ~/.config/logitech-onboard if needed."""
    new_dir = Path.home() / ".config" / "omm-linux"
    old_dir = Path.home() / ".config" / "logitech-onboard"
    if not new_dir.exists() and old_dir.exists():
        try:
            import shutil
            shutil.copytree(old_dir, new_dir)
        except Exception:
            return old_dir
    new_dir.mkdir(parents=True, exist_ok=True)
    return new_dir


def get_backup_dir() -> Path:
    config_dir = get_config_dir() / "backups"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def prune_backups(max_keep: int = 50) -> int:
    """Prunes timestamped backup YAML files to retain only the newest `max_keep` files."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return 0
    try:
        yaml_files = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and f.suffix.lower() in (".yaml", ".yml")],
            key=lambda p: p.stat().st_mtime
        )
        excess = len(yaml_files) - max_keep
        if excess <= 0:
            return 0
        pruned_count = 0
        for f in yaml_files[:excess]:
            try:
                f.unlink()
                pruned_count += 1
            except Exception:
                pass
        return pruned_count
    except Exception:
        return 0


class MouseBackend:
    def __init__(self, device_name: str = "G502"):
        self.device_name = device_name
        self.raw_yaml_cache: Optional[OnboardProfilesYaml] = None

    def _save_backup(self, config: OnboardConfig) -> Optional[Path]:
        """Saves a timestamped backup before writing changes."""
        import datetime
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = get_backup_dir() / f"pre_write_{ts}.yaml"

            profiles_yaml = {}
            for pid, prof in config.profiles.items():
                raw_b = MouseBackend._translate_ui_to_raw_buttons(prof.buttons)
                raw_gb = MouseBackend._translate_ui_to_raw_buttons(prof.gbuttons)
                p_yaml = OnboardProfileYaml(
                    angle_snap=getattr(prof, "angle_snap", 0),
                    blue=getattr(prof, "blue", 255),
                    buttons=[ButtonYaml(**b.to_yaml_dict()) for b in raw_b],
                    gbuttons=[ButtonYaml(**b.to_yaml_dict()) for b in raw_gb],
                    enabled=getattr(prof, "enabled", 1),
                    green=getattr(prof, "green", 255),
                    name=getattr(prof, "name", f"Profile {pid}"),
                    power_mode=getattr(prof, "power_mode", 255),
                    red=getattr(prof, "red", 255),
                    report_rate=getattr(prof, "report_rate", 1),
                    resolution_default_index=getattr(prof, "resolution_default_index", 0),
                    resolution_shift_index=getattr(prof, "resolution_shift_index", 0),
                    resolutions=list(getattr(prof, "resolutions", [800, 1200, 1600, 2400, 3200])),
                    sector=getattr(prof, "sector", pid),
                )
                profiles_yaml[pid] = p_yaml

            root_yaml = OnboardProfilesYaml(
                name=config.device_name,
                count=config.count,
                buttons=config.buttons_count,
                gbuttons=config.gbuttons_count,
                sectors=config.sectors,
                size=config.size,
                version=config.version,
                profiles=profiles_yaml,
            )

            yaml_text = yaml.dump(root_yaml, sort_keys=True)
            with open(backup_file, "w") as f:
                f.write(yaml_text)
            return backup_file
        except Exception:
            return None

    @staticmethod
    def _translate_raw_to_ui_buttons(raw_btns: list) -> list:
        """Translates raw G502 hardware memory chunk order to logical UI button order.
        In G502 hardware flash:
          chunk 3 = G4 (Back)
          chunk 4 = G6 (DPI Shift / Sniper)
          chunk 5 = G5 (Forward)
        In the UI / logical button numbering:
          button 4 (idx 3) = G4 (Thumb Back)
          button 5 (idx 4) = G5 (Thumb Forward)
          button 6 (idx 5) = G6 (Thumb DPI Shift / Sniper)
        """
        btns = list(raw_btns)
        if len(btns) >= 6:
            btns[4], btns[5] = btns[5], btns[4]
        return btns

    @staticmethod
    def _translate_ui_to_raw_buttons(ui_btns: list) -> list:
        """Translates logical UI button order to raw G502 hardware memory chunk order."""
        btns = list(ui_btns)
        if len(btns) >= 6:
            btns[4], btns[5] = btns[5], btns[4]
        return btns

    def _get_solaar_cmd(self) -> list:
        """Determines whether Solaar is native or in Flatpak."""
        if shutil.which("solaar"):
            return ["solaar"]
        # Check flatpak
        res = subprocess.run(["which", "flatpak"], capture_output=True, text=True)
        if res.returncode == 0:
            config_dir = get_config_dir()
            return ["flatpak", "run", f"--filesystem={config_dir}", "--command=solaar", "io.github.pwr_solaar.solaar"]
        return ["solaar"]

    def query_active_profile(self) -> int:
        """Finds out which profile (1..5) is currently active on the device."""
        try:
            drv = NativeHIDPP()
            if drv.open():
                pid = drv.query_active_profile()
                drv.close()
                return pid
        except Exception:
            pass
        return 1

    def enforce_lighting_state(self, drv: Optional[NativeHIDPP] = None, force_auto_off: Optional[bool] = None) -> bool:
        """Enforces the user's configured RGB lighting preference (e.g. keeping RGB off or applying active effect)."""
        import configparser
        conf_path = Path.home() / ".config" / "OMMLinux" / "OMMLinux.conf"
        if not conf_path.exists():
            conf_path = Path.home() / ".config" / "LogitechLinux" / "OnboardMemoryManager.conf"
        auto_off = False
        effect_mode = "off"
        color_hex = "#00aeef"
        brightness = 100
        speed_ms = 5000
        waveform = 6

        if conf_path.exists():
            cp = configparser.ConfigParser()
            try:
                cp.read(str(conf_path))
                section = "General" if "General" in cp else (cp.sections()[0] if cp.sections() else None)
                if section:
                    sec = cp[section]
                    if "auto_turn_off_rgb" in sec:
                        auto_off = sec.getboolean("auto_turn_off_rgb")
                    if "rgb_effect_mode" in sec:
                        effect_mode = sec.get("rgb_effect_mode", "off").lower()
                    if "rgb_color_hex" in sec:
                        color_hex = sec.get("rgb_color_hex", "#00aeef")
                    if "rgb_brightness" in sec:
                        brightness = sec.getint("rgb_brightness", 100)
                    if "rgb_speed_ms" in sec:
                        speed_ms = sec.getint("rgb_speed_ms", 5000)
                    if "rgb_waveform" in sec:
                        waveform = sec.getint("rgb_waveform", 6)
            except Exception:
                pass

        if force_auto_off is not None:
            auto_off = force_auto_off

        needs_close = False
        if drv is None:
            drv = NativeHIDPP()
            if not drv.open():
                return False
            needs_close = True

        try:
            if auto_off or effect_mode == "off":
                return drv.turn_off_rgb()
            elif effect_mode in ("static", "breathing", "cycle"):
                c_hex = color_hex.lstrip("#")
                try:
                    r = int(c_hex[0:2], 16) if len(c_hex) >= 2 else 0
                    g = int(c_hex[2:4], 16) if len(c_hex) >= 4 else 174
                    b = int(c_hex[4:6], 16) if len(c_hex) >= 6 else 239
                except Exception:
                    r, g, b = 0, 174, 239
                return drv.set_rgb_effect(
                    effect_type=effect_mode,
                    r=r, g=g, b=b,
                    brightness=brightness,
                    period_ms=speed_ms,
                    waveform=waveform,
                    persistent=False
                )
            return True
        finally:
            if needs_close:
                drv.close()

    def set_active_profile(self, profile_num: int) -> Tuple[bool, str]:
        """Switches the mouse's active onboard profile."""
        try:
            drv = NativeHIDPP()
            if drv.open():
                ok = drv.set_active_profile(profile_num)
                if ok:
                    self.enforce_lighting_state(drv)
                drv.close()
                if ok:
                    return True, f"Active profile set to Profile {profile_num}"
        except Exception as e:
            return False, str(e)
        return False, "Failed to connect to mouse"

    def turn_off_lighting(self) -> Tuple[bool, str]:
        """Completely disables and shuts off all RGB LED zones on the mouse and saves config."""
        try:
            drv = NativeHIDPP()
            if drv.open():
                drv.turn_off_rgb()
                drv.close()
                return True, "Mouse lighting turned completely off."
        except Exception as e:
            return False, str(e)
        return False, "Could not access mouse"

    def set_lighting_effect(
        self,
        effect_type: str,
        r: int = 255,
        g: int = 255,
        b: int = 255,
        brightness: int = 100,
        period_ms: int = 3000,
        waveform: int = 1,
        persistent: bool = True
    ) -> Tuple[bool, str]:
        """Sets hardware RGB lighting effect directly on mouse EEPROM and RAM."""
        try:
            drv = NativeHIDPP()
            if drv.open():
                ok = drv.set_rgb_effect(
                    effect_type=effect_type,
                    r=r, g=g, b=b,
                    brightness=brightness,
                    period_ms=period_ms,
                    waveform=waveform,
                    persistent=persistent
                )
                drv.close()
                if ok:
                    return True, "Lighting effect applied to mouse hardware."
                return False, "Mouse rejected lighting effect parameters."
        except Exception as e:
            return False, str(e)
        return False, "Could not access mouse"

    def read_macros(self) -> Dict[int, str]:
        """Reads and disassembles macros from mouse memory sector 6."""
        macro_dict = dict(KNOWN_MACROS)
        try:
            drv = NativeHIDPP()
            if drv.open():
                sec6 = drv.read_sector(6, 224)
                drv.close()
                if sec6:
                    for addr in range(0, len(sec6) - 22, 22):
                        txt = decode_logitech_macro(sec6[addr : addr + 22])
                        if txt:
                            macro_dict[addr] = txt
        except Exception:
            pass
        return macro_dict

    def read_profiles(self) -> Tuple[Optional[OnboardConfig], str]:
        """Reads all profiles directly from the mouse onboard memory."""
        import struct
        try:
            drv = NativeHIDPP()
            if not drv.open():
                return None, "Could not open Logitech mouse device on /dev/hidraw. Check permissions and USB connection."

            device_name = drv.get_device_name() or self.device_name
            active_id = drv.query_active_profile()
            macros = self.read_macros()

            # Read sector 0 for profile metadata / enabled status
            sec0 = drv.read_sector(0, 32)
            enabled_flags = {}
            for i in range(5):
                chunk = sec0[i*4 : (i+1)*4] if len(sec0) >= (i+1)*4 else b"\x00"*4
                pid = (chunk[0] << 8) | chunk[1] if chunk[0] != 0xFF else (i + 1)
                enabled = chunk[2] if len(chunk) > 2 else 1
                enabled_flags[pid if pid in range(1, 6) else (i + 1)] = enabled

            config = OnboardConfig(
                device_name=device_name,
                count=5,
                buttons_count=11,
                gbuttons_count=11,
                sectors=16,
                size=255,
                version=3,
                active_profile_id=active_id,
            )

            def decode_btn(chunk: bytes, chunk_idx: int = 0):
                if chunk == b"\x00\x00\x00\x00":
                    if chunk_idx < len(FACTORY_RAW_CHUNKS):
                        chunk = FACTORY_RAW_CHUNKS[chunk_idx]
                    else:
                        chunk = b"\xff\xff\xff\xff"
                if chunk == b"\xff\xff\xff\xff":
                    return ButtonAction(behavior=15, action_type=4, value=0)
                beh = chunk[0]
                if beh == 0x80:
                    return ButtonAction(behavior=8, action_type=chunk[1], modifiers=chunk[2], value=chunk[3])
                elif beh == 0x90:
                    return ButtonAction(behavior=9, action_type=0, value=chunk[1], data=chunk[3])
                elif beh == 0x00:
                    sec = chunk[1]
                    addr = (chunk[2] << 8) | chunk[3]
                    mtxt = macros.get(addr)
                    return ButtonAction(behavior=0, action_type=0, value=0, sector=sec, address=addr, macro_text=mtxt)
                return ButtonAction(behavior=beh, action_type=chunk[1], modifiers=chunk[2], value=chunk[3])

            for slot_num in range(1, 6):
                raw = drv.read_sector(slot_num, 240)
                if not raw or len(raw) < 208:
                    continue

                report_rate = raw[0]
                def_dpi = raw[1]
                shift_dpi = raw[2]
                dpis = [struct.unpack("<H", raw[3+i*2 : 5+i*2])[0] for i in range(5)]
                r, g, b = raw[13], raw[14], raw[15]
                power_mode = raw[16]
                angle_snap = raw[17]

                raw_buttons = [decode_btn(raw[32+i*4 : 36+i*4], i) for i in range(11)]
                raw_gbuttons = [decode_btn(raw[96+i*4 : 100+i*4], i) for i in range(11)]
                buttons = self._translate_raw_to_ui_buttons(raw_buttons)
                gbuttons = self._translate_raw_to_ui_buttons(raw_gbuttons)

                raw_name = raw[160:208].decode("utf-16le", errors="ignore").rstrip("\x00").strip("\uffff").strip()
                if not raw_name or raw_name == "PROFILE_NAME_DEFAULT":
                    prof_name = f"Profile {slot_num}"
                else:
                    prof_name = raw_name

                prof = Profile(
                    profile_id=slot_num,
                    sector=slot_num,
                    enabled=enabled_flags.get(slot_num, 1),
                    name=prof_name,
                    report_rate=report_rate,
                    resolutions=dpis,
                    resolution_default_index=def_dpi,
                    resolution_shift_index=shift_dpi,
                    buttons=buttons,
                    gbuttons=gbuttons,
                    angle_snap=angle_snap,
                    red=r, green=g, blue=b,
                    power_mode=power_mode,
                    reserved=raw[20:28] if len(raw) >= 28 else b"\xff"*8
                )
                config.profiles[slot_num] = prof

            drv.close()
            return config, "Success"
        except Exception as e:
            return None, f"Failed to read profiles natively: {str(e)}"

    def _convert_from_yaml_obj(self, yaml_obj: Any, active_id: int, macro_map: Optional[Dict[int, str]] = None) -> OnboardConfig:
        if macro_map is None:
            macro_map = KNOWN_MACROS

        config = OnboardConfig(
            device_name=getattr(yaml_obj, "name", self.device_name),
            count=getattr(yaml_obj, "count", 5),
            buttons_count=getattr(yaml_obj, "buttons", 11),
            gbuttons_count=getattr(yaml_obj, "gbuttons", 11),
            sectors=getattr(yaml_obj, "sectors", 16),
            size=getattr(yaml_obj, "size", 255),
            version=getattr(yaml_obj, "version", 3),
            active_profile_id=active_id,
        )

        profiles_raw = getattr(yaml_obj, "profiles", {})
        for pid, p_raw in profiles_raw.items():
            btn_actions = []
            for b in getattr(p_raw, "buttons", []):
                beh = getattr(b, "behavior", 8)
                addr = getattr(b, "address", None)
                macro_txt = macro_map.get(addr) if beh == 0 and addr is not None else None
                btn_actions.append(
                    ButtonAction(
                        behavior=beh,
                        action_type=getattr(b, "type", 1),
                        value=getattr(b, "value", 1),
                        modifiers=getattr(b, "modifiers", 0),
                        data=getattr(b, "data", 0),
                        sector=getattr(b, "sector", None),
                        address=addr,
                        raw_bytes=getattr(b, "bytes", None),
                        macro_text=macro_txt,
                    )
                )

            gbtn_actions = []
            for b in getattr(p_raw, "gbuttons", []):
                beh = getattr(b, "behavior", 8)
                addr = getattr(b, "address", None)
                macro_txt = macro_map.get(addr) if beh == 0 and addr is not None else None
                gbtn_actions.append(
                    ButtonAction(
                        behavior=beh,
                        action_type=getattr(b, "type", 1),
                        value=getattr(b, "value", 1),
                        modifiers=getattr(b, "modifiers", 0),
                        data=getattr(b, "data", 0),
                        sector=getattr(b, "sector", None),
                        address=addr,
                        raw_bytes=getattr(b, "bytes", None),
                        macro_text=macro_txt,
                    )
                )

            btn_actions = self._translate_raw_to_ui_buttons(btn_actions)
            gbtn_actions = self._translate_raw_to_ui_buttons(gbtn_actions)

            prof = Profile(
                profile_id=pid,
                sector=getattr(p_raw, "sector", pid),
                enabled=getattr(p_raw, "enabled", 1),
                name=getattr(p_raw, "name", f"Profile {pid}"),
                report_rate=getattr(p_raw, "report_rate", 1),
                resolutions=list(getattr(p_raw, "resolutions", [800, 1200, 1600, 2400, 3200])),
                resolution_default_index=getattr(p_raw, "resolution_default_index", 0),
                resolution_shift_index=getattr(p_raw, "resolution_shift_index", 0),
                buttons=btn_actions,
                gbuttons=gbtn_actions,
                angle_snap=getattr(p_raw, "angle_snap", 0),
                red=getattr(p_raw, "red", 255),
                green=getattr(p_raw, "green", 255),
                blue=getattr(p_raw, "blue", 255),
                power_mode=getattr(p_raw, "power_mode", 255),
                ps_timeout=getattr(p_raw, "ps_timeout", 60),
                po_timeout=getattr(p_raw, "po_timeout", 300),
                write_count=getattr(p_raw, "write_count", 65535),
                reserved=getattr(p_raw, "reserved", b"\xff" * 8),
                lighting=getattr(p_raw, "lighting", []),
            )
            config.profiles[pid] = prof

        return config

    @staticmethod
    def _build_profile_sector(prof: Profile, base_bytes: Optional[bytes] = None) -> bytes:
        import struct
        b = bytearray(base_bytes if base_bytes and len(base_bytes) >= 240 else b"\x00" * 240)
        b[0] = prof.report_rate & 0xFF
        b[1] = prof.resolution_default_index & 0xFF
        b[2] = prof.resolution_shift_index & 0xFF
        for i in range(5):
            val = prof.resolutions[i] if i < len(prof.resolutions) else 0
            b[3 + i*2 : 5 + i*2] = struct.pack("<H", val)
        # Permanent hardware RGB shutoff
        b[13] = 0
        b[14] = 0
        b[15] = 0
        b[16] = prof.power_mode & 0xFF
        b[17] = prof.angle_snap & 0xFF
        raw_buttons = MouseBackend._translate_ui_to_raw_buttons(prof.buttons)
        raw_gbuttons = MouseBackend._translate_ui_to_raw_buttons(prof.gbuttons)
        for i in range(11):
            if i < len(raw_buttons):
                btn = raw_buttons[i]
                if btn.behavior == 8:
                    chunk = bytes([0x80, btn.action_type & 0xFF, btn.modifiers & 0xFF, btn.value & 0xFF])
                elif btn.behavior == 9:
                    chunk = bytes([0x90, btn.value & 0xFF, 0xFF, btn.data & 0xFF])
                elif btn.behavior == 0:
                    sec = btn.sector if btn.sector is not None else 6
                    addr = btn.address if btn.address is not None else 0
                    chunk = bytes([0x00, sec & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
                elif btn.behavior == 15 or btn.action_type == 4:
                    chunk = b"\xff\xff\xff\xff"
                else:
                    chunk = bytes([btn.behavior & 0xFF, btn.action_type & 0xFF, btn.modifiers & 0xFF, btn.value & 0xFF])
            else:
                chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else b"\xff\xff\xff\xff"
            if chunk == b"\x00\x00\x00\x00":
                chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else bytes([0x80, 0x01, 0x00, 0x01])
            b[32 + i*4 : 36 + i*4] = chunk
        for i in range(11):
            if i < len(raw_gbuttons):
                btn = raw_gbuttons[i]
                if btn.behavior == 8:
                    chunk = bytes([0x80, btn.action_type & 0xFF, btn.modifiers & 0xFF, btn.value & 0xFF])
                elif btn.behavior == 9:
                    chunk = bytes([0x90, btn.value & 0xFF, 0xFF, btn.data & 0xFF])
                elif btn.behavior == 0:
                    sec = btn.sector if btn.sector is not None else 6
                    addr = btn.address if btn.address is not None else 0
                    chunk = bytes([0x00, sec & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
                elif btn.behavior == 15 or btn.action_type == 4:
                    chunk = b"\xff\xff\xff\xff"
                else:
                    chunk = bytes([btn.behavior & 0xFF, btn.action_type & 0xFF, btn.modifiers & 0xFF, btn.value & 0xFF])
            else:
                chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else b"\xff\xff\xff\xff"
            if chunk == b"\x00\x00\x00\x00":
                chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else bytes([0x80, 0x01, 0x00, 0x01])
            b[96 + i*4 : 100 + i*4] = chunk
        raw_name = prof.name.encode("utf-16le")[:48].ljust(48, b"\x00")
        b[160:208] = raw_name
        b[208:240] = b"\x00" * 32
        return bytes(b[:240])

    def write_profiles(self, config: OnboardConfig, auto_turn_off_rgb: bool = False) -> Tuple[bool, str]:
        """Saves a timestamped backup and burns the updated configuration to mouse flash memory."""
        try:
            self._save_backup(config)
            prune_backups(50)
        except Exception:
            pass

        try:
            drv = NativeHIDPP()
            if not drv.open():
                return False, "Could not open mouse on /dev/hidraw"

            for pid, prof in config.profiles.items():
                cur_sector = drv.read_sector(pid, 240)
                sec_bytes = self._build_profile_sector(prof, cur_sector)
                drv.write_sector(pid, sec_bytes)

            drv.set_active_profile(config.active_profile_id or 1)
            self.enforce_lighting_state(drv, force_auto_off=auto_turn_off_rgb)
            drv.close()
            return True, "Successfully saved to mouse hardware memory!"
        except Exception as e:
            return False, f"Write error: {str(e)}"

    def flash_single_profile(self, slot_num: int, profile_data: dict) -> Tuple[bool, str]:
        """Flashes a single profile into the designated slot natively without Solaar."""
        import struct
        try:
            drv = NativeHIDPP()
            if not drv.open():
                return False, "Could not open mouse on /dev/hidraw"

            base = drv.read_sector(slot_num, 240)
            b = bytearray(base if base and len(base) >= 240 else b"\x00" * 240)

            rate_ms = 1
            rr = profile_data.get("report_rate", 1000)
            if rr == 500: rate_ms = 2
            elif rr == 250: rate_ms = 4
            elif rr == 125: rate_ms = 8
            b[0] = rate_ms & 0xFF
            b[1] = profile_data.get("resolution_default_index", 0) & 0xFF
            b[2] = profile_data.get("resolution_shift_index", 0) & 0xFF

            resolutions = profile_data.get("resolutions", [800, 1200, 1600, 2400, 3200])
            for i in range(5):
                val = resolutions[i] if i < len(resolutions) else 0
                b[3 + i*2 : 5 + i*2] = struct.pack("<H", val)

            # RGB = 0
            b[13] = 0
            b[14] = 0
            b[15] = 0
            b[16] = 255
            b[17] = 0

            buttons = self._translate_ui_to_raw_buttons(profile_data.get("buttons", []))
            for i in range(11):
                if i < len(buttons):
                    b_item = buttons[i]
                    if isinstance(b_item, dict):
                        beh = b_item.get("behavior", 8)
                        atype = b_item.get("action_type", b_item.get("type", 1))
                        mods = b_item.get("modifiers", 0)
                        val = b_item.get("value", 1)
                        data = b_item.get("data", 0)
                        sec = b_item.get("sector", 6)
                        addr = b_item.get("address", 0)
                    elif hasattr(b_item, "behavior"):
                        beh = b_item.behavior
                        atype = b_item.action_type
                        mods = b_item.modifiers
                        val = b_item.value
                        data = b_item.data
                        sec = b_item.sector if b_item.sector is not None else 6
                        addr = b_item.address if b_item.address is not None else 0
                    else:
                        beh, atype, mods, val, data, sec, addr = 15, 4, 0, 0, 0, 6, 0

                    if beh == 15 or atype == 4:
                        chunk = b"\xff\xff\xff\xff"
                    elif beh == 8:
                        chunk = bytes([0x80, atype & 0xFF, mods & 0xFF, val & 0xFF])
                    elif beh == 9:
                        chunk = bytes([0x90, val & 0xFF, 0xFF, data & 0xFF])
                    elif beh == 0:
                        chunk = bytes([0x00, sec & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
                    else:
                        chunk = bytes([beh & 0xFF, atype & 0xFF, mods & 0xFF, val & 0xFF])
                else:
                    chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else b"\xff\xff\xff\xff"
                if chunk == b"\x00\x00\x00\x00":
                    chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else bytes([0x80, 0x01, 0x00, 0x01])
                b[32 + i*4 : 36 + i*4] = chunk

            gbuttons = self._translate_ui_to_raw_buttons(profile_data.get("gbuttons", []))
            for i in range(11):
                if i < len(gbuttons):
                    b_item = gbuttons[i]
                    if isinstance(b_item, dict):
                        beh = b_item.get("behavior", 15)
                        atype = b_item.get("action_type", b_item.get("type", 4))
                        mods = b_item.get("modifiers", 0)
                        val = b_item.get("value", 0)
                        data = b_item.get("data", 0)
                        sec = b_item.get("sector", 6)
                        addr = b_item.get("address", 0)
                    elif hasattr(b_item, "behavior"):
                        beh = b_item.behavior
                        atype = b_item.action_type
                        mods = b_item.modifiers
                        val = b_item.value
                        data = b_item.data
                        sec = b_item.sector if b_item.sector is not None else 6
                        addr = b_item.address if b_item.address is not None else 0
                    else:
                        beh, atype, mods, val, data, sec, addr = 15, 4, 0, 0, 0, 6, 0

                    if beh == 15 or atype == 4:
                        chunk = b"\xff\xff\xff\xff"
                    elif beh == 8:
                        chunk = bytes([0x80, atype & 0xFF, mods & 0xFF, val & 0xFF])
                    elif beh == 9:
                        chunk = bytes([0x90, val & 0xFF, 0xFF, data & 0xFF])
                    elif beh == 0:
                        chunk = bytes([0x00, sec & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF])
                    else:
                        chunk = bytes([beh & 0xFF, atype & 0xFF, mods & 0xFF, val & 0xFF])
                else:
                    chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else b"\xff\xff\xff\xff"
                if chunk == b"\x00\x00\x00\x00":
                    chunk = FACTORY_RAW_CHUNKS[i] if i < len(FACTORY_RAW_CHUNKS) else bytes([0x80, 0x01, 0x00, 0x01])
                b[96 + i*4 : 100 + i*4] = chunk

            name = profile_data.get("name", f"Profile {slot_num}")
            raw_name = name.encode("utf-16le")[:48].ljust(48, b"\x00")
            b[160:208] = raw_name
            b[208:240] = b"\x00" * 32

            sec_bytes = bytes(b[:240])
            ok = drv.write_sector(slot_num, sec_bytes)
            if ok:
                drv.set_active_profile(slot_num)
                self.enforce_lighting_state(drv)
                drv.close()
                return True, f"Successfully staged Profile to Slot {slot_num}"
            drv.close()
            return False, f"Failed writing Profile to Slot {slot_num}"
        except Exception as e:
            return False, f"Flash error: {str(e)}"
