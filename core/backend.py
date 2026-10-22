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

KNOWN_MACROS = {
    0: "Ctrl + R",
    22: "Ctrl + PageUp",
    44: "Ctrl + PageDown",
    66: "Ctrl + R",
    88: "Ctrl + PageUp",
    110: "Ctrl + PageDown",
    132: "Ctrl + X",
    154: "Shift + /",
    176: "Ctrl + X",
    198: "Shift + /",
}

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


def get_backup_dir() -> Path:
    config_dir = Path.home() / ".config" / "logitech-onboard" / "backups"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


class MouseBackend:
    def __init__(self, device_name: str = "G502"):
        self.device_name = device_name
        self.raw_yaml_cache: Optional[OnboardProfilesYaml] = None

    def _get_solaar_cmd(self) -> list:
        """Determines whether Solaar is native or in Flatpak."""
        if shutil.which("solaar"):
            return ["solaar"]
        # Check flatpak
        res = subprocess.run(["which", "flatpak"], capture_output=True, text=True)
        if res.returncode == 0:
            config_dir = Path.home() / ".config" / "logitech-onboard"
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
        # Fallback to Solaar
        cmd = self._get_solaar_cmd() + ["config", self.device_name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if "onboard_profiles =" in line:
                    val = line.split("=")[-1].strip()
                    if "Profile" in val:
                        parts = val.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            return int(parts[1])
        except Exception:
            pass
        return 1

    def set_active_profile(self, profile_num: int) -> Tuple[bool, str]:
        """Switches the mouse's active onboard profile."""
        try:
            drv = NativeHIDPP()
            if drv.open():
                ok = drv.set_active_profile(profile_num)
                drv.close()
                if ok:
                    return True, f"Active profile set to Profile {profile_num}"
        except Exception:
            pass
        # Fallback to Solaar
        cmd = self._get_solaar_cmd() + ["config", self.device_name, "onboard_profiles", f"Profile {profile_num}"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if res.returncode == 0:
                return True, f"Active profile set to Profile {profile_num}"
            return False, res.stderr or res.stdout
        except Exception as e:
            return False, str(e)

    def turn_off_lighting(self) -> Tuple[bool, str]:
        """Completely disables and shuts off all RGB LED zones on the mouse."""
        try:
            drv = NativeHIDPP()
            if drv.open():
                drv.turn_off_rgb()
                drv.close()
                return True, "Mouse lighting turned completely off."
        except Exception:
            pass
        # Fallback to Solaar
        py_code = (
            "from solaar.cli import _receivers_and_devices\n"
            "from logitech_receiver import rgb_power\n"
            "from logitech_receiver.hidpp20_constants import SupportedFeature\n"
            "for r in _receivers_and_devices():\n"
            "    devices = [r] if getattr(r, 'isDevice', False) else list(r)\n"
            "    for d in devices:\n"
            "        if d.online and 'G502' in d.name:\n"
            "            rgb_power.push_artanis_perkey_prep(d)\n"
            "            for z in range(1, 9):\n"
            "                d.feature_request(SupportedFeature.PER_KEY_LIGHTING_V2, 0x60, z, 0, 0, 0, 1)\n"
            "            d.feature_request(SupportedFeature.PER_KEY_LIGHTING_V2, 0x70, 0x00)\n"
            "            d.feature_request(SupportedFeature.RGB_EFFECTS, 0x10, 0x00, 0x00, 0x00, 0x00)\n"
            "            print('LED_OFF_DONE')\n"
        )
        cmd = ["flatpak", "run", "--command=python3", "io.github.pwr_solaar.solaar", "-c", py_code]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if "LED_OFF_DONE" in res.stdout:
                return True, "Mouse lighting turned completely off."
            return False, res.stderr or res.stdout
        except Exception as e:
            return False, str(e)

    def read_macros(self) -> Dict[int, str]:
        """Reads and disassembles macros from mouse memory sector 6."""
        macro_dict = dict(KNOWN_MACROS)
        cmd = ["flatpak", "run", "--command=python3", "io.github.pwr_solaar.solaar", "-c",
               "from solaar.cli import _receivers_and_devices; "
               "from logitech_receiver.hidpp20 import OnboardProfiles; "
               "for r in _receivers_and_devices():\n"
               " devices = [r] if getattr(r, 'isDevice', False) else list(r)\n"
               " for d in devices:\n"
               "  if d.online and 'G502' in d.name:\n"
               "   s = OnboardProfiles.read_sector(d, 6, 224)\n"
               "   print('SEC6:' + s.hex())\n"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                if line.startswith("SEC6:"):
                    sec_hex = line[5:].strip()
                    sec_bytes = bytes.fromhex(sec_hex)
                    for addr in range(0, len(sec_bytes) - 22, 22):
                        txt = decode_logitech_macro(sec_bytes[addr:addr+22])
                        if txt:
                            macro_dict[addr] = txt
        except Exception:
            pass
        return macro_dict

    def read_profiles(self) -> Tuple[Optional[OnboardConfig], str]:
        """Reads all profiles from the mouse onboard memory."""
        cmd = self._get_solaar_cmd() + ["profiles", self.device_name]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if res.returncode != 0:
                return None, f"Command failed: {res.stderr or res.stdout}"

            yaml_lines = []
            capture = False
            for line in res.stdout.splitlines():
                if line.startswith("!OnboardProfiles"):
                    capture = True
                if capture:
                    yaml_lines.append(line)

            yaml_text = "\n".join(yaml_lines)
            if not yaml_text.strip():
                return None, f"No valid profile data received from device:\n{res.stdout}\n{res.stderr}"

            data = yaml.safe_load(yaml_text)
            self.raw_yaml_cache = data

            # Save initial backup if needed
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = get_backup_dir() / f"initial_{ts}.yaml"
            with open(backup_path, "w") as bf:
                bf.write(yaml_text)

            active_id = self.query_active_profile()
            macros = self.read_macros()
            config = self._convert_from_yaml_obj(data, active_id, macros)
            return config, "Success"
        except subprocess.TimeoutExpired:
            return None, "Device query timed out. Check that the mouse is powered on and within wireless range."
        except Exception as e:
            return None, f"Failed to read profiles: {str(e)}"

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

    def write_profiles(self, config: OnboardConfig) -> Tuple[bool, str]:
        """Saves a timestamped backup and burns the updated configuration to mouse flash memory."""
        if not self.raw_yaml_cache:
            # Re-read if we don't have base cache
            _, err = self.read_profiles()
            if not self.raw_yaml_cache:
                return False, f"Cannot write without base device read: {err}"

        # Update cache from config model
        for pid, prof in config.profiles.items():
            if pid in self.raw_yaml_cache.profiles:
                p_yaml = self.raw_yaml_cache.profiles[pid]
                p_yaml.enabled = prof.enabled
                p_yaml.name = prof.name
                p_yaml.report_rate = prof.report_rate
                p_yaml.resolutions = prof.resolutions
                p_yaml.resolution_default_index = prof.resolution_default_index
                p_yaml.resolution_shift_index = prof.resolution_shift_index

                # Update buttons
                p_yaml.buttons = [ButtonYaml(**b.to_yaml_dict()) for b in prof.buttons]
                p_yaml.gbuttons = [ButtonYaml(**b.to_yaml_dict()) for b in prof.gbuttons]

        # 1. Save timestamped backup
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = get_backup_dir() / f"pre_write_{ts}.yaml"
        yaml_text = yaml.dump(self.raw_yaml_cache, sort_keys=True)
        with open(backup_file, "w") as f:
            f.write(yaml_text)

        # 2. Write to temp file for flashing
        temp_file = Path.home() / ".config" / "logitech-onboard" / "temp_write.yaml"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file, "w") as f:
            f.write(yaml_text)

        # 3. Flash to mouse
        cmd = self._get_solaar_cmd() + ["profiles", self.device_name, str(temp_file)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            # Remove temporary write file
            if temp_file.exists():
                temp_file.unlink()

            output = (res.stdout + "\n" + res.stderr).strip()
            if "Profiles not written" in output or "FileNotFoundError" in output:
                return False, f"Failed to write to device:\n{output}"
            elif "Wrote" in output or res.returncode == 0:
                # Flashing temporarily leaves onboard mode in Disabled; immediately re-engage active profile
                self.set_active_profile(config.active_profile_id or 1)
                return True, f"Successfully saved to mouse memory!\nBackup saved to {backup_file.name}"
            else:
                return False, f"Failed to write to device:\n{output}"
        except Exception as e:
            return False, f"Write error: {str(e)}"
