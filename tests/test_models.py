from core.keycodes import (
    detect_mouse_model,
    get_button_labels,
)
from core.models import ButtonAction, create_default_buttons


def test_detect_mouse_model():
    assert detect_mouse_model("Logitech G502 X PLUS", 11) == "g502"
    assert detect_mouse_model("Logitech PRO X Superlight", 5) == "gpro"
    assert detect_mouse_model("Logitech G305", 6) == "g305"
    assert detect_mouse_model("Logitech G703 LIGHTSPEED", 6) == "g703"
    assert detect_mouse_model("Logitech G903", 11) == "g903"
    assert detect_mouse_model("Logitech G604", 15) == "g604"


def test_get_button_labels():
    labels = get_button_labels("Logitech G502 X PLUS", 11)
    assert 1 in labels
    assert "Left Click" in labels[1]
    assert 7 in labels
    assert "Scroll Wheel Tilt Left" in labels[7]


def test_button_action_mouse_click():
    action = ButtonAction.mouse_click(1)
    assert action.behavior == 8
    assert action.action_type == 1
    assert action.value == 1
    assert "Left Click" in action.display_name()


def test_button_action_key_shortcut():
    # Key 0x04 is 'A', modifier 0x01 is Left Ctrl
    action = ButtonAction.key_shortcut(0x04, modifiers=0x01)
    assert action.behavior == 8
    assert action.action_type == 2
    assert "Ctrl + A" == action.display_name()


def test_button_action_disabled():
    action = ButtonAction.disabled()
    assert action.behavior == 8
    assert action.action_type == 4
    assert action.display_name() == "Disabled"


def test_button_action_serialization():
    action = ButtonAction.mouse_click(2)
    d = action.to_dict()
    assert d["value"] == 2
    restored = ButtonAction.from_dict(d)
    assert restored.value == 2
    assert restored.behavior == 8


def test_create_default_buttons():
    buttons = create_default_buttons()
    assert len(buttons) == 11
    # B1, B2, B3 active mouse clicks
    assert buttons[0].action_type == 1
    assert buttons[1].action_type == 1
    assert buttons[2].action_type == 1
    # B4, B5, B6 blank/disabled
    assert buttons[3].action_type == 4
    assert buttons[4].action_type == 4
    assert buttons[5].action_type == 4
    # B7, B8 tilt left / tilt right
    assert buttons[6].value == 0x4A
    assert buttons[7].value == 0x4B
    # B9, B10, B11 disabled
    assert buttons[8].action_type == 4
    assert buttons[9].action_type == 4
    assert buttons[10].action_type == 4
