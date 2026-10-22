"""Core module for Logitech Onboard Memory GUI."""

from .models import ButtonAction, Profile, OnboardConfig
from .backend import MouseBackend
from .keycodes import G502_BUTTON_LABELS, MOUSE_BUTTONS, FUNCTION_ACTIONS, HID_KEYCODES, MODIFIERS
