from core.backend import MouseBackend
from core.models import ButtonAction


def test_translate_raw_to_ui_and_back_g502():
    backend = MouseBackend("Logitech G502 X PLUS")
    # Create an 11-button raw list
    raw_buttons = [ButtonAction.mouse_click(1 << i) for i in range(11)]
    ui_buttons = backend._translate_raw_to_ui_buttons(raw_buttons)
    assert len(ui_buttons) == 11
    # Check that slot 3 in UI is B4 (hardware index 3)
    # Check that slot 4 in UI is B5 (hardware index 5)
    # Check that slot 5 in UI is B6 (hardware index 4)
    assert ui_buttons[3] == raw_buttons[3]
    assert ui_buttons[4] == raw_buttons[5]
    assert ui_buttons[5] == raw_buttons[4]

    # Convert back to raw
    converted_raw = backend._translate_ui_to_raw_buttons(ui_buttons)
    assert converted_raw == raw_buttons


def test_translate_raw_to_ui_non_g502():
    # G305 has 6 buttons and should preserve 1:1 chunk order
    backend = MouseBackend("Logitech G305")
    raw_buttons = [ButtonAction.mouse_click(1 << i) for i in range(6)]
    ui_buttons = backend._translate_raw_to_ui_buttons(raw_buttons)
    assert ui_buttons == raw_buttons

    converted_raw = backend._translate_ui_to_raw_buttons(ui_buttons)
    assert converted_raw == raw_buttons
