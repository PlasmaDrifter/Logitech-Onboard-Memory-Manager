"""Core module for Logitech Onboard Memory GUI."""

from .backend import MouseBackend
from .keycodes import (
    FUNCTION_ACTIONS,
    G502_BUTTON_LABELS,
    HID_KEYCODES,
    MODIFIERS,
    MOUSE_BUTTONS,
)
from .models import ButtonAction, OnboardConfig, Profile
