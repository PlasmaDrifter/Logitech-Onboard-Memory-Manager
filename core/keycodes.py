"""HID Keycode and modifier translation tables for Logitech HID++ 2.0."""

from typing import cast

# Modifier bitmasks (used in button mapping type 2: MODIFIER_AND_KEY)
MODIFIER_LEFT_CTRL = 0x01
MODIFIER_LEFT_SHIFT = 0x02
MODIFIER_LEFT_ALT = 0x04
MODIFIER_LEFT_GUI = 0x08
MODIFIER_RIGHT_CTRL = 0x10
MODIFIER_RIGHT_SHIFT = 0x20
MODIFIER_RIGHT_ALT = 0x40
MODIFIER_RIGHT_GUI = 0x80

MODIFIERS = {
    "Ctrl": MODIFIER_LEFT_CTRL,
    "Shift": MODIFIER_LEFT_SHIFT,
    "Alt": MODIFIER_LEFT_ALT,
    "Super": MODIFIER_LEFT_GUI,
}

# Mouse standard buttons (bitmask / value used in type 1: BUTTON)
MOUSE_BUTTONS = {
    1: "Left Click",
    2: "Right Click",
    4: "Middle Click",
    8: "Back",
    16: "Forward",
    32: "Extra 1",
    64: "Extra 2",
}

MOUSE_BUTTON_NAMES_INV = {v: k for k, v in MOUSE_BUTTONS.items()}

# Logitech Special Functions (behavior 9: FUNCTION)
FUNCTION_ACTIONS = {
    0x00: "No Action",
    0x01: "Tilt Left",
    0x02: "Tilt Right",
    0x03: "Next DPI",
    0x04: "Previous DPI",
    0x05: "Cycle DPI",
    0x06: "Default DPI",
    0x07: "DPI Shift (Sniper)",
    0x08: "Next Profile",
    0x09: "Previous Profile",
    0x0A: "Cycle Profile",
    0x0B: "G-Shift",
    0x0C: "Battery Status",
    0x0D: "Profile Select",
    0x0E: "Mode Switch",
    0x10: "Scroll Down",
    0x11: "Scroll Up",
    0x45: "Next DPI",
    0x46: "Previous DPI",
    0x47: "DPI Shift (Sniper)",
    0x49: "Cycle Profile",
    0x4A: "Tilt Left",
    0x4B: "Tilt Right",
}

FUNCTION_NAMES_INV = {v: k for k, v in FUNCTION_ACTIONS.items()}

# USB HID Keycodes (0x04 - 0xE7)
HID_KEYCODES = {
    0x00: "None",
    0x04: "A",
    0x05: "B",
    0x06: "C",
    0x07: "D",
    0x08: "E",
    0x09: "F",
    0x0A: "G",
    0x0B: "H",
    0x0C: "I",
    0x0D: "J",
    0x0E: "K",
    0x0F: "L",
    0x10: "M",
    0x11: "N",
    0x12: "O",
    0x13: "P",
    0x14: "Q",
    0x15: "R",
    0x16: "S",
    0x17: "T",
    0x18: "U",
    0x19: "V",
    0x1A: "W",
    0x1B: "X",
    0x1C: "Y",
    0x1D: "Z",
    0x1E: "1",
    0x1F: "2",
    0x20: "3",
    0x21: "4",
    0x22: "5",
    0x23: "6",
    0x24: "7",
    0x25: "8",
    0x26: "9",
    0x27: "0",
    0x28: "Enter",
    0x29: "Escape",
    0x2A: "Backspace",
    0x2B: "Tab",
    0x2C: "Space",
    0x2D: "-",
    0x2E: "=",
    0x2F: "[",
    0x30: "]",
    0x31: "\\",
    0x33: ";",
    0x34: "'",
    0x35: "`",
    0x36: ",",
    0x37: ".",
    0x38: "/",
    0x39: "CapsLock",
    0x3A: "F1",
    0x3B: "F2",
    0x3C: "F3",
    0x3D: "F4",
    0x3E: "F5",
    0x3F: "F6",
    0x40: "F7",
    0x41: "F8",
    0x42: "F9",
    0x43: "F10",
    0x44: "F11",
    0x45: "F12",
    0x46: "PrintScreen",
    0x47: "ScrollLock",
    0x48: "Pause",
    0x49: "Insert",
    0x4A: "Home",
    0x4B: "PageUp",
    0x4C: "Delete",
    0x4D: "End",
    0x4E: "PageDown",
    0x4F: "Right",
    0x50: "Left",
    0x51: "Down",
    0x52: "Up",
    0x53: "NumLock",
    0x54: "Keypad /",
    0x55: "Keypad *",
    0x56: "Keypad -",
    0x57: "Keypad +",
    0x58: "Keypad Enter",
    0x59: "Keypad 1",
    0x5A: "Keypad 2",
    0x5B: "Keypad 3",
    0x5C: "Keypad 4",
    0x5D: "Keypad 5",
    0x5E: "Keypad 6",
    0x5F: "Keypad 7",
    0x60: "Keypad 8",
    0x61: "Keypad 9",
    0x62: "Keypad 0",
    0x63: "Keypad .",
    0x68: "F13",
    0x69: "F14",
    0x6A: "F15",
    0x6B: "F16",
    0x6C: "F17",
    0x6D: "F18",
    0x6E: "F19",
    0x6F: "F20",
    0x70: "F21",
    0x71: "F22",
    0x72: "F23",
    0x73: "F24",
    0x7F: "Mute",
    0x80: "VolumeUp",
    0x81: "VolumeDown",
    0xE0: "Left Ctrl",
    0xE1: "Left Shift",
    0xE2: "Left Alt",
    0xE3: "Left GUI (Super)",
    0xE4: "Right Ctrl",
    0xE5: "Right Shift",
    0xE6: "Right Alt",
    0xE7: "Right GUI (Super)",
}

HID_KEYCODES_INV = {v.upper(): k for k, v in HID_KEYCODES.items()}

# Physical buttons for various Logitech gaming mouse families
G502_BUTTON_LABELS = {
    1: "Button 1: Left Click",
    2: "Button 2: Right Click",
    3: "Button 3: Middle Click / Scroll Wheel Press",
    4: "Button 4: Side Back",
    5: "Button 5: Side Middle",
    6: "Button 6: Side Front",
    7: "Button 7: Scroll Wheel Tilt Left",
    8: "Button 8: Scroll Wheel Tilt Right",
    9: "Button 9: Profile Switcher (Behind wheel)",
    10: "Button 10: G7 (DPI Down / Index finger outer)",
    11: "Button 11: G8 (DPI Up / Index finger outer)",
}

GPRO_BUTTON_LABELS = {
    1: "Button 1: Left Click",
    2: "Button 2: Right Click",
    3: "Button 3: Middle Click / Scroll Wheel Press",
    4: "Button 4: Side Lower (Thumb Back)",
    5: "Button 5: Side Upper (Thumb Forward)",
}

G305_BUTTON_LABELS = {
    1: "Button 1: Left Click",
    2: "Button 2: Right Click",
    3: "Button 3: Middle Click / Scroll Wheel Press",
    4: "Button 4: Side Lower (Thumb Back)",
    5: "Button 5: Side Upper (Thumb Forward)",
    6: "Button 6: DPI Cycle (Top Button)",
}

G703_BUTTON_LABELS = {
    1: "Button 1: Left Click",
    2: "Button 2: Right Click",
    3: "Button 3: Middle Click / Scroll Wheel Press",
    4: "Button 4: Side Lower (Thumb Back)",
    5: "Button 5: Side Upper (Thumb Forward)",
    6: "Button 6: DPI Cycle (Top Button)",
}

G903_BUTTON_LABELS = {
    1: "Button 1: Left Click",
    2: "Button 2: Right Click",
    3: "Button 3: Middle Click / Scroll Wheel Press",
    4: "Button 4: Left Side Back (Thumb)",
    5: "Button 5: Left Side Forward (Thumb)",
    6: "Button 6: Right Side Back",
    7: "Button 7: Right Side Forward",
    8: "Button 8: Scroll Wheel Tilt Left",
    9: "Button 9: Scroll Wheel Tilt Right",
    10: "Button 10: DPI Down",
    11: "Button 11: DPI Up",
}

G604_BUTTON_LABELS = {
    1: "Button 1: Left Click",
    2: "Button 2: Right Click",
    3: "Button 3: Middle Click / Scroll Wheel Press",
    4: "Button 4: Side G4 (Thumb Front Lower)",
    5: "Button 5: Side G5 (Thumb Mid Lower)",
    6: "Button 6: Side G6 (Thumb Rear Lower)",
    7: "Button 7: Side G7 (Thumb Front Upper)",
    8: "Button 8: Side G8 (Thumb Mid Upper)",
    9: "Button 9: Side G9 (Thumb Rear Upper)",
    10: "Button 10: Scroll Wheel Tilt Left",
    11: "Button 11: Scroll Wheel Tilt Right",
    12: "Button 12: Top DPI Down",
    13: "Button 13: Top DPI Up",
    14: "Button 14: Profile Switch",
    15: "Button 15: Bluetooth / Lightspeed Toggle",
}

SUPPORTED_MODELS = {
    "g502": {
        "name": "Logitech G502 Series (11 Buttons)",
        "labels": G502_BUTTON_LABELS,
        "buttons": 11,
    },
    "gpro": {
        "name": "Logitech G PRO / Superlight (5 Buttons)",
        "labels": GPRO_BUTTON_LABELS,
        "buttons": 5,
    },
    "g305": {
        "name": "Logitech G305 / G203 (6 Buttons)",
        "labels": G305_BUTTON_LABELS,
        "buttons": 6,
    },
    "g703": {
        "name": "Logitech G703 / G403 / G603 (6 Buttons)",
        "labels": G703_BUTTON_LABELS,
        "buttons": 6,
    },
    "g903": {
        "name": "Logitech G903 / G900 (11 Buttons)",
        "labels": G903_BUTTON_LABELS,
        "buttons": 11,
    },
    "g604": {
        "name": "Logitech G604 Lightspeed (15 Buttons)",
        "labels": G604_BUTTON_LABELS,
        "buttons": 15,
    },
}


def detect_mouse_model(device_name: str, button_count: int = 11) -> str:
    """Matches hardware device name and button count to a known mouse model profile."""
    name = (device_name or "").upper()
    if "G502" in name or "HERO" in name or "502" in name:
        return "g502"
    elif "903" in name or "900" in name:
        return "g903"
    elif "604" in name:
        return "g604"
    elif "703" in name or "403" in name or "603" in name:
        return "g703"
    elif "305" in name or "203" in name or "102" in name:
        return "g305"
    elif "SUPERLIGHT" in name or "PRO X" in name or "G PRO" in name:
        return "gpro"

    # Fallback heuristic by button count
    if button_count >= 15:
        return "g604"
    elif button_count == 11:
        return "g502"
    elif button_count == 6:
        return "g305"
    elif button_count == 5:
        return "gpro"

    return "g502"


def get_button_labels(
    device_name: str, button_count: int = 11, model_key: str | None = None
) -> dict[int, str]:
    """Returns human-readable button labels for the specified or auto-detected mouse model."""
    if not model_key:
        model_key = detect_mouse_model(device_name, button_count)

    model_info = SUPPORTED_MODELS.get(model_key)
    if model_info and isinstance(model_info.get("labels"), dict):
        return cast(dict[int, str], model_info["labels"])
    return G502_BUTTON_LABELS
