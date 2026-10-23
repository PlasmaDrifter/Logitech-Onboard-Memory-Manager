"""Pure native Linux HID++ 2.0 driver over /dev/hidraw (Zero dependencies).

Speaks directly to the Linux kernel character device without Solaar,
Piper, or ratbagd.
"""

import os
import glob
import select
import struct
from typing import Optional, Tuple, Dict, List, Any

from .models import ButtonAction, Profile, OnboardConfig
from .keycodes import HID_KEYCODES

FEATURE_ROOT = 0x0000
FEATURE_FEATURE_SET = 0x0001
FEATURE_DEVICE_FW_VERSION = 0x0003
FEATURE_DEVICE_NAME = 0x0005
FEATURE_ONBOARD_PROFILES = 0x8100
FEATURE_RGB_EFFECTS = 0x8071
FEATURE_PER_KEY_LIGHTING_V2 = 0x8081


class NativeHIDPP:
    def __init__(self, dev_path: Optional[str] = None):
        self.dev_path = dev_path or self.find_device()
        self.fd: Optional[int] = None
        self.device_index = 0x01  # Paired mouse on receiver is index 1
        self.features: Dict[int, int] = {}  # feature_id -> feature_index
        self.device_name = "Logitech Gaming Mouse"

    @staticmethod
    def crc16(data: bytes) -> int:
        """Computes Logitech HID++ 2.0 CRC-16 CCITT lookup checksum."""
        table = [
            0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
            0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
            0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
            0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
            0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
            0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
            0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
            0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
            0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
            0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
            0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
            0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
            0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
            0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
            0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
            0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
            0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
            0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
            0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
            0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
            0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
            0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
            0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
            0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
            0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
            0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
            0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
            0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
            0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
            0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
            0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
            0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
        ]
        crc = 0xFFFF
        for byte in data:
            crc = (crc << 8) ^ table[(crc >> 8) ^ byte]
            crc &= 0xFFFF
        return crc

    @staticmethod
    def find_device() -> Optional[str]:
        """Auto-detects active Logitech HID++ 2.0 mouse hidraw node."""
        candidates = []
        for p in sorted(glob.glob("/dev/hidraw*")):
            idx = p.replace("/dev/hidraw", "")
            uevent = f"/sys/class/hidraw/hidraw{idx}/device/uevent"
            try:
                with open(uevent) as f:
                    content = f.read()
                if "046D" in content:
                    candidates.append(p)
            except Exception:
                pass

        for p in candidates:
            try:
                inst = NativeHIDPP(p)
                if inst.open():
                    feat = inst.discover_feature(FEATURE_ONBOARD_PROFILES)
                    if feat:
                        inst.close()
                        return p
                    inst.close()
            except Exception:
                pass
        return candidates[0] if candidates else None

    def _drain_buffer(self):
        """Discards any unread/stale reports in the hidraw kernel buffer."""
        if self.fd is not None:
            try:
                while True:
                    r, _, _ = select.select([self.fd], [], [], 0.005)
                    if not r:
                        break
                    os.read(self.fd, 64)
            except Exception:
                pass

    def open(self) -> bool:
        if not self.dev_path:
            self.dev_path = self.find_device()
        if not self.dev_path:
            return False
        try:
            self.fd = os.open(self.dev_path, os.O_RDWR | os.O_NONBLOCK)
            self._drain_buffer()
            return True
        except Exception:
            self.fd = None
            return False

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None

    def request(self, feat_idx: int, fn_idx: int, params: bytes = b"", timeout: float = 0.3) -> Optional[bytes]:
        """Sends an HID++ 2.0 Long (0x11) request and waits for matching response."""
        if self.fd is None and not self.open():
            return None

        self._drain_buffer()
        req = bytes([0x11, self.device_index, feat_idx, fn_idx]) + params
        req = req.ljust(20, b"\x00")
        try:
            os.write(self.fd, req)
            for _ in range(10):
                r, _, _ = select.select([self.fd], [], [], timeout)
                if r:
                    resp = os.read(self.fd, 64)
                    if len(resp) >= 4 and resp[0] == 0x11 and resp[1] == self.device_index:
                        if resp[2] == feat_idx and (resp[3] & 0x0F) == (fn_idx & 0x0F):
                            return resp
                        if resp[2] == 0xFF and resp[4] == feat_idx:
                            return None
        except Exception:
            pass
        return None

    def discover_feature(self, feature_id: int) -> Optional[int]:
        if feature_id in self.features:
            return self.features[feature_id]

        resp = self.request(0x00, 0x01, bytes([(feature_id >> 8) & 0xFF, feature_id & 0xFF, 0x00]))
        if resp and resp[4] != 0:
            self.features[feature_id] = resp[4]
            return resp[4]
        return None

    def get_device_name(self) -> str:
        idx = self.discover_feature(FEATURE_DEVICE_NAME)
        if not idx:
            return self.device_name
        len_resp = self.request(idx, 0x01)
        if len_resp:
            n_len = len_resp[4]
            name_resp = self.request(idx, 0x11, bytes([0]))
            if name_resp:
                self.device_name = name_resp[4 : 4 + n_len].decode("utf-8", errors="ignore")
        return self.device_name

    def query_active_profile(self) -> int:
        idx = self.discover_feature(FEATURE_ONBOARD_PROFILES)
        if not idx:
            return 1
        resp = self.request(idx, 0x21)  # get mode
        if resp and resp[4] == 0x01:  # Onboard enabled
            p_resp = self.request(idx, 0x41)  # get active profile
            if p_resp:
                return (p_resp[4] << 8) | p_resp[5]
        return 1

    def ensure_profile_enabled(self, profile_num: int) -> bool:
        """Ensures the profile slot is marked enabled in Sector 0 so firmware accepts switching."""
        if not (1 <= profile_num <= 5):
            return True
        sec0 = self.read_sector(0, 240)
        if not sec0 or len(sec0) < 32:
            return False
        offset = (profile_num - 1) * 4
        if sec0[offset + 2] != 1:
            sec0_b = bytearray(sec0)
            sec0_b[offset] = (profile_num >> 8) & 0xFF
            sec0_b[offset + 1] = profile_num & 0xFF
            sec0_b[offset + 2] = 1
            sec0_b[offset + 3] = 0
            return self.write_sector(0, bytes(sec0_b))
        return True

    def set_active_profile(self, profile_num: int, force_cycle: bool = True) -> bool:
        import time
        self.ensure_profile_enabled(profile_num)
        idx = self.discover_feature(FEATURE_ONBOARD_PROFILES)
        if not idx:
            return False
        # Enable onboard mode (0x11, param 0x01)
        self.request(idx, 0x11, bytes([0x01]))
        if force_cycle:
            # Momentarily switch away so firmware microcontroller flushes internal cache
            alt = 2 if profile_num == 1 else 1
            self.request(idx, 0x31, bytes([(alt >> 8) & 0xFF, alt & 0xFF]))
            time.sleep(0.15)
        # Set profile (0x31, 2-byte profile sector)
        res = self.request(idx, 0x31, bytes([(profile_num >> 8) & 0xFF, profile_num & 0xFF]))
        return res is not None

    def read_sector(self, sector: int, length: int = 240) -> bytes:
        idx = self.discover_feature(FEATURE_ONBOARD_PROFILES)
        if not idx:
            return b""
        data = bytearray()
        offset = 0
        while offset < length:
            chunk_len = min(16, length - offset)
            resp = self.request(
                idx,
                0x51,
                bytes([(sector >> 8) & 0xFF, sector & 0xFF, (offset >> 8) & 0xFF, offset & 0xFF]),
            )
            if not resp:
                break
            data.extend(resp[4 : 4 + chunk_len])
            offset += 16
        return bytes(data)

    def write_sector(self, sector: int, data: bytes) -> bool:
        """Writes up to 255 bytes to an onboard memory sector with CRC-16 checksum."""
        idx = self.discover_feature(FEATURE_ONBOARD_PROFILES)
        if not idx:
            return False

        current = self.read_sector(sector, min(len(data), 240))
        if current and current[:len(data)] == data[:len(current)]:
            return True

        bs = bytearray(data)
        # Pad up to 253 bytes with 0xFF if writing profile sector
        while len(bs) < 253:
            bs.append(0xFF)
        c = self.crc16(bytes(bs[:253]))
        bs = bs[:253] + bytes([c >> 8, c & 0xFF])
        length = len(bs)

        # Open write session (0x61, sector, offset 0, length)
        open_req = bytes([
            (sector >> 8) & 0xFF, sector & 0xFF,
            0x00, 0x00,
            (length >> 8) & 0xFF, length & 0xFF
        ]).ljust(16, b"\x00")
        if not self.request(idx, 0x61, open_req):
            return False

        # Stream 16-byte chunks (0x71)
        for offset in range(0, length, 16):
            chunk = bytes(bs[offset : offset + 16]).ljust(16, b"\x00")
            if not self.request(idx, 0x71, chunk):
                return False

        # Commit (0x81)
        commit_resp = self.request(idx, 0x81)
        return commit_resp is not None

    def set_rgb_effect(
        self,
        effect_type: str,
        r: int = 255,
        g: int = 255,
        b: int = 255,
        brightness: int = 100,
        period_ms: int = 3000,
        waveform: int = 1,
        persistent: bool = True
    ) -> bool:
        """Sets hardware RGB lighting effect directly on mouse EEPROM and RAM.

        effect_type: 'off', 'static', 'breathing', 'cycle'
        brightness: 0 to 100
        period_ms: 500 to 30000 ms
        waveform: 0=Default, 1=Sine, 2=Square, 3=Triangle, 4=Sawtooth, 5=Sharkfin, 6=Exponential
        persistent: True for EEPROM + RAM (0x03), False for RAM live preview (0x01)
        """
        if self.fd is None and not self.open():
            return False

        if effect_type == "off" or brightness <= 0:
            return self.turn_off_rgb()

        rgb_idx = self.discover_feature(FEATURE_RGB_EFFECTS)
        if not rgb_idx:
            return False

        persist_byte = 0x03 if persistent else 0x01

        period = max(500, min(30000, period_ms))
        p_hi = (period >> 8) & 0xFF
        p_lo = period & 0xFF
        intensity_val = max(1, min(100, brightness))

        try:
            # 1. Host software control of clusters and power modes
            self.request(rgb_idx, 0x51, bytes([0x01, 0x03, 0x00]))

            # 2. Power mode 0 = Full Power ON
            self.request(rgb_idx, 0x81, bytes([0x01, 0x00, 0x00]))

            # 3. Enable bootUpEffect in NvConfig so the effect runs on boot / power-on
            self.request(rgb_idx, 0x31, bytes([0x01, 0x00, 0x01, 0x01]))

            if effect_type == "static":
                # Static / Fixed (Effect idx 1)
                # Static has no intensity register in HID++, so scale RGB directly
                bright_factor = max(0.0, min(1.0, brightness / 100.0))
                r_val = int(r * bright_factor) & 0xFF
                g_val = int(g * bright_factor) & 0xFF
                b_val = int(b * bright_factor) & 0xFF
                # bs: [r, g, b, ramp=0x02, 0, 0, 0, 0, 0, 0]
                params = bytes([0x00, 0x01, r_val, g_val, b_val, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, persist_byte])
                return self.request(rgb_idx, 0x11, params) is not None

            elif effect_type == "breathing":
                # Breathing (Effect idx 2 / 0x0A)
                # Keep full-scale RGB so the hardware PWM sine generator has full 8-bit dynamic range
                # to prevent low-brightness quantization stutter.
                # waveform: 0x01=Sine, 0x06=Exponential (perceptual gamma curve), etc.
                r_val = max(0, min(255, r))
                g_val = max(0, min(255, g))
                b_val = max(0, min(255, b))
                wf = max(0, min(6, waveform))
                # bs: [r, g, b, p_hi, p_lo, waveform, intensity, 0, 0, 0]
                params = bytes([0x00, 0x02, r_val, g_val, b_val, p_hi, p_lo, wf, intensity_val, 0x00, 0x00, 0x00, persist_byte])
                return self.request(rgb_idx, 0x11, params) is not None

            elif effect_type == "cycle":
                # Color Cycle (Effect idx 3)
                # bs: [0, 0, 0, 0, 0, p_hi, p_lo, intensity, 0, 0]
                # Period is at offset 5..6 (bs[5:7]), intensity is at offset 7 (bs[7])
                params = bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, p_hi, p_lo, intensity_val, 0x00, 0x00, persist_byte])
                return self.request(rgb_idx, 0x11, params) is not None

            return False
        except Exception:
            return False

    def turn_off_rgb(self) -> bool:
        """Completely and permanently disables and shuts off all RGB LED zones on the mouse.

        Applies host software control, disables hardware bootUpEffect in NvConfig so the
        mouse cannot replay effects on wake/reconnect, forces RGB power mode to off,
        sets all cluster effects to disabled with EEPROM persistence, clears all PerKey zones,
        and commits the frame with EEPROM persistence.
        """
        if self.fd is None and not self.open():
            return False

        rgb_idx = self.discover_feature(FEATURE_RGB_EFFECTS)
        perkey_idx = self.discover_feature(FEATURE_PER_KEY_LIGHTING_V2)

        try:
            if rgb_idx:
                # 1. 0x8071 fn 5 (manageSwControl): Host owns clusters and power modes (0x01, 0x03, 0x00)
                self.request(rgb_idx, 0x51, bytes([0x01, 0x03, 0x00]))

                # 2. 0x8071 fn 3 (manageNvConfig): Permanently disable bootUpEffect (state 2 = disabled)
                self.request(rgb_idx, 0x31, bytes([0x01, 0x00, 0x01, 0x02]))

                # 3. 0x8071 fn 8 (manageRgbPowerMode): Force power mode 3 = Power Off
                self.request(rgb_idx, 0x81, bytes([0x01, 0x03, 0x00]))

                # 4. 0x8071 fn 1 (setRgbClusterEffect): Cluster 0xFF, Effect 0 (Disabled), Persistence 0x03 (RAM + EEPROM)
                cluster_req = bytes([0xFF, 0x00]) + (b"\x00" * 10) + bytes([0x03, 0x00, 0x00, 0x00])
                self.request(rgb_idx, 0x11, cluster_req)

            if perkey_idx:
                # 5. 0x8081 fn 5 (set_range_rgb_zones): Set zones 0..31 to (0, 0, 0)
                self.request(perkey_idx, 0x51, bytes([0x00, 0x1F, 0x00, 0x00, 0x00]))

                # 6. 0x8081 fn 7 (frame_end): Commit frame with persistence 1 (VolatileAndNonVolatile / EEPROM)
                self.request(perkey_idx, 0x71, bytes([0x01, 0x00, 0x00, 0x00]))

            return True
        except Exception:
            return False
