"""Data models for Logitech Onboard Profiles and Button Mappings."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from .keycodes import (
    MOUSE_BUTTONS,
    FUNCTION_ACTIONS,
    HID_KEYCODES,
    MODIFIERS,
    G502_BUTTON_LABELS,
)


@dataclass
class ButtonAction:
    behavior: int = 8  # 0=macro, 8=send, 9=function, 15=disabled
    action_type: int = 1  # 1=mouse button, 2=modifier+key, 3=consumer key, 4=no action
    value: int = 1  # button bitmask, HID keycode, or function ID
    modifiers: int = 0  # modifier bitmask for type 2
    data: int = 0  # optional data for function
    sector: Optional[int] = None  # for macro
    address: Optional[int] = None  # for macro
    raw_bytes: Optional[bytes] = None
    macro_text: Optional[str] = None

    def display_name(self) -> str:
        """Returns a user-friendly label for the mapped button action."""
        if self.behavior == 8:
            if self.action_type == 1:
                return MOUSE_BUTTONS.get(self.value, f"Mouse Button 0x{self.value:X}")
            elif self.action_type == 2:
                mods = []
                if self.modifiers & 0x01 or self.modifiers & 0x10:
                    mods.append("Ctrl")
                if self.modifiers & 0x02 or self.modifiers & 0x20:
                    mods.append("Shift")
                if self.modifiers & 0x04 or self.modifiers & 0x40:
                    mods.append("Alt")
                if self.modifiers & 0x08 or self.modifiers & 0x80:
                    mods.append("Super")

                key = HID_KEYCODES.get(self.value, f"Key 0x{self.value:02X}")
                if mods:
                    return f"{' + '.join(mods)} + {key}"
                return key
            elif self.action_type == 4:
                return "Disabled"
        elif self.behavior == 9:
            return FUNCTION_ACTIONS.get(self.value, f"Function 0x{self.value:X}")
        elif self.behavior == 0:
            if self.macro_text:
                return self.macro_text
            return f"Macro (Sector {self.sector}, Addr {self.address})"
        elif self.behavior == 15:
            return "Disabled"

        return f"Unknown (b:{self.behavior}, t:{self.action_type}, v:{self.value})"

    @classmethod
    def mouse_click(cls, button_mask: int) -> "ButtonAction":
        return cls(behavior=8, action_type=1, value=button_mask, modifiers=0)

    @classmethod
    def key_shortcut(cls, keycode: int, modifiers: int = 0) -> "ButtonAction":
        return cls(behavior=8, action_type=2, value=keycode, modifiers=modifiers)

    @classmethod
    def function(cls, func_id: int) -> "ButtonAction":
        return cls(behavior=9, action_type=0, value=func_id, modifiers=0, data=0)

    @classmethod
    def disabled(cls) -> "ButtonAction":
        return cls(behavior=8, action_type=4, value=0, modifiers=0)

    def to_yaml_dict(self) -> dict:
        d = {"behavior": self.behavior}
        if self.behavior == 8:
            d["type"] = self.action_type
            if self.action_type == 2:
                d["modifiers"] = self.modifiers
            d["value"] = self.value
        elif self.behavior == 9:
            d["value"] = self.value
            d["data"] = self.data
        elif self.behavior == 0:
            d["sector"] = self.sector
            d["address"] = self.address
        elif self.behavior == 15:
            d["bytes"] = b"\xff\xff\xff\xff"
        return d

    def to_dict(self) -> dict:
        return {
            "behavior": self.behavior,
            "action_type": self.action_type,
            "value": self.value,
            "modifiers": self.modifiers,
            "data": self.data,
            "sector": self.sector,
            "address": self.address,
            "macro_text": self.macro_text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ButtonAction":
        return cls(
            behavior=d.get("behavior", 8),
            action_type=d.get("action_type", d.get("type", 1)),
            value=d.get("value", 1),
            modifiers=d.get("modifiers", 0),
            data=d.get("data", 0),
            sector=d.get("sector"),
            address=d.get("address"),
            macro_text=d.get("macro_text"),
        )


def create_default_buttons() -> List[ButtonAction]:
    """Returns standard default button mappings for new profiles:
    - Button 1: Left Click
    - Button 2: Right Click
    - Button 3: Middle Click
    - Button 9: Scroll Wheel Tilt Left
    - Button 10: Scroll Wheel Tilt Right
    All other buttons disabled (blank).
    """
    return [
        ButtonAction.mouse_click(1),  # B1: Left Click
        ButtonAction.mouse_click(2),  # B2: Right Click
        ButtonAction.mouse_click(4),  # B3: Middle Click
        ButtonAction.disabled(),      # B4: Blank
        ButtonAction.disabled(),      # B5: Blank
        ButtonAction.disabled(),      # B6: Blank
        ButtonAction.disabled(),      # B7: Blank
        ButtonAction.disabled(),      # B8: Blank
        ButtonAction.function(0x4A),  # B9: Scroll Wheel Tilt Left
        ButtonAction.function(0x4B),  # B10: Scroll Wheel Tilt Right
        ButtonAction.disabled(),      # B11: Blank
    ]


@dataclass
class Profile:
    profile_id: int
    sector: int
    enabled: int
    name: str = "Default"
    report_rate: int = 1  # 1ms = 1000Hz, 2ms = 500Hz
    resolutions: List[int] = field(default_factory=lambda: [800, 1200, 1600, 2400, 3200])
    resolution_default_index: int = 0
    resolution_shift_index: int = 0
    buttons: List[ButtonAction] = field(default_factory=create_default_buttons)
    gbuttons: List[ButtonAction] = field(default_factory=create_default_buttons)
    angle_snap: int = 0
    red: int = 255
    green: int = 255
    blue: int = 255
    power_mode: int = 255
    ps_timeout: int = 60
    po_timeout: int = 300
    write_count: int = 65535
    reserved: bytes = b"\xff" * 8
    lighting: List[Any] = field(default_factory=list)


@dataclass
class OnboardConfig:
    device_name: str
    count: int = 5
    buttons_count: int = 11
    gbuttons_count: int = 11
    sectors: int = 16
    size: int = 255
    version: int = 3
    profiles: Dict[int, Profile] = field(default_factory=dict)
    active_profile_id: int = 1
