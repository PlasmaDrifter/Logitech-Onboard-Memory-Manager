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
    def find_device() -> Optional[str]:
        """Auto-detects Logitech HID++ 2.0 mouse hidraw node."""
        for p in sorted(glob.glob("/dev/hidraw*")):
            idx = p.replace("/dev/hidraw", "")
            uevent = f"/sys/class/hidraw/hidraw{idx}/device/uevent"
            try:
                with open(uevent) as f:
                    content = f.read()
                if "046D" in content:
                    fd = os.open(p, os.O_RDWR | os.O_NONBLOCK)
                    # Ping device 1 with root feature
                    req = bytes([0x11, 0x01, 0x00, 0x11, 0x00, 0x00, 0x00, 0x5A] + [0] * 12)
                    os.write(fd, req)
                    r, _, _ = select.select([fd], [], [], 0.15)
                    if r:
                        resp = os.read(fd, 64)
                        if len(resp) >= 4 and resp[0] == 0x11 and resp[1] == 0x01 and resp[2] == 0x00:
                            os.close(fd)
                            return p
                    os.close(fd)
            except Exception:
                pass
        return None

    def open(self) -> bool:
        if not self.dev_path:
            self.dev_path = self.find_device()
        if not self.dev_path:
            return False
        try:
            self.fd = os.open(self.dev_path, os.O_RDWR | os.O_NONBLOCK)
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

    def request(self, feat_idx: int, fn_idx: int, params: bytes = b"", timeout: float = 0.4) -> Optional[bytes]:
        """Sends an HID++ 2.0 Long (0x11) request and waits for matching response."""
        if self.fd is None and not self.open():
            return None

        req = bytes([0x11, self.device_index, feat_idx, fn_idx]) + params
        req = req.ljust(20, b"\x00")
        try:
            os.write(self.fd, req)
            for _ in range(12):
                r, _, _ = select.select([self.fd], [], [], timeout)
                if r:
                    resp = os.read(self.fd, 64)
                    if len(resp) >= 4 and resp[0] == 0x11 and resp[1] == self.device_index:
                        # Check feature index and function matching
                        if resp[2] == feat_idx and (resp[3] & 0x0F) == (fn_idx & 0x0F):
                            return resp
                        # Check if device reported error for this feature
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

    def set_active_profile(self, profile_num: int) -> bool:
        idx = self.discover_feature(FEATURE_ONBOARD_PROFILES)
        if not idx:
            return False
        # Enable onboard mode (0x11, param 0x01)
        self.request(idx, 0x11, bytes([0x01]))
        # Set profile (0x31, 2-byte profile sector)
        res = self.request(idx, 0x31, bytes([(profile_num >> 8) & 0xFF, profile_num & 0xFF]))
        return res is not None

    def read_sector(self, sector: int, length: int = 255) -> bytes:
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
        idx = self.discover_feature(FEATURE_ONBOARD_PROFILES)
        if not idx:
            return False
        current = self.read_sector(sector, len(data))
        if current == data:
            return True

        length = len(data)
        # Open write session (0x61, sector, 0, length)
        open_req = bytes([
            (sector >> 8) & 0xFF, sector & 0xFF,
            0x00, 0x00,
            (length >> 8) & 0xFF, length & 0xFF
        ])
        if not self.request(idx, 0x61, open_req):
            return False

        # Stream chunks (0x71)
        for offset in range(0, length, 16):
            chunk = data[offset : offset + 16].ljust(16, b"\x00")
            if not self.request(idx, 0x71, chunk):
                return False

        # Commit (0x81)
        commit_resp = self.request(idx, 0x81)
        return commit_resp is not None

    def turn_off_rgb(self) -> bool:
        rgb_idx = self.discover_feature(FEATURE_RGB_EFFECTS)
        if rgb_idx:
            # Zone 0 to Disabled (0x00)
            self.request(rgb_idx, 0x11, bytes([0x00, 0x00, 0x00, 0x00]))
            # Zone 0 to Static Black (0x01)
            self.request(rgb_idx, 0x11, bytes([0x00, 0x01, 0x00, 0x00, 0x00, 0x00]))

        perkey_idx = self.discover_feature(FEATURE_PER_KEY_LIGHTING_V2)
        if perkey_idx:
            # Set all 8 individual zones to black and commit
            for z in range(1, 9):
                self.request(perkey_idx, 0x61, bytes([z, 0, 0, 0, 1]))
            self.request(perkey_idx, 0x71, bytes([0x00]))

        return True
