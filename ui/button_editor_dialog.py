"""Interactive dialog for editing an individual mouse button mapping."""

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from core.models import ButtonAction
from core.keycodes import (
    MOUSE_BUTTONS,
    MOUSE_BUTTON_NAMES_INV,
    FUNCTION_ACTIONS,
    FUNCTION_NAMES_INV,
    HID_KEYCODES,
    HID_KEYCODES_INV,
    MODIFIER_LEFT_CTRL,
    MODIFIER_LEFT_SHIFT,
    MODIFIER_LEFT_ALT,
    MODIFIER_LEFT_GUI,
)


# Qt Key to USB HID Keycode map
QT_KEY_TO_HID = {
    QtCore.Qt.Key.Key_A: 0x04, QtCore.Qt.Key.Key_B: 0x05, QtCore.Qt.Key.Key_C: 0x06,
    QtCore.Qt.Key.Key_D: 0x07, QtCore.Qt.Key.Key_E: 0x08, QtCore.Qt.Key.Key_F: 0x09,
    QtCore.Qt.Key.Key_G: 0x0A, QtCore.Qt.Key.Key_H: 0x0B, QtCore.Qt.Key.Key_I: 0x0C,
    QtCore.Qt.Key.Key_J: 0x0D, QtCore.Qt.Key.Key_K: 0x0E, QtCore.Qt.Key.Key_L: 0x0F,
    QtCore.Qt.Key.Key_M: 0x10, QtCore.Qt.Key.Key_N: 0x11, QtCore.Qt.Key.Key_O: 0x12,
    QtCore.Qt.Key.Key_P: 0x13, QtCore.Qt.Key.Key_Q: 0x14, QtCore.Qt.Key.Key_R: 0x15,
    QtCore.Qt.Key.Key_S: 0x16, QtCore.Qt.Key.Key_T: 0x17, QtCore.Qt.Key.Key_U: 0x18,
    QtCore.Qt.Key.Key_V: 0x19, QtCore.Qt.Key.Key_W: 0x1A, QtCore.Qt.Key.Key_X: 0x1B,
    QtCore.Qt.Key.Key_Y: 0x1C, QtCore.Qt.Key.Key_Z: 0x1D,
    QtCore.Qt.Key.Key_1: 0x1E, QtCore.Qt.Key.Key_2: 0x1F, QtCore.Qt.Key.Key_3: 0x20,
    QtCore.Qt.Key.Key_4: 0x21, QtCore.Qt.Key.Key_5: 0x22, QtCore.Qt.Key.Key_6: 0x23,
    QtCore.Qt.Key.Key_7: 0x24, QtCore.Qt.Key.Key_8: 0x25, QtCore.Qt.Key.Key_9: 0x26,
    QtCore.Qt.Key.Key_0: 0x27,
    QtCore.Qt.Key.Key_Return: 0x28, QtCore.Qt.Key.Key_Enter: 0x28,
    QtCore.Qt.Key.Key_Escape: 0x29,
    QtCore.Qt.Key.Key_Backspace: 0x2A,
    QtCore.Qt.Key.Key_Tab: 0x2B,
    QtCore.Qt.Key.Key_Space: 0x2C,
    QtCore.Qt.Key.Key_Minus: 0x2D, QtCore.Qt.Key.Key_Equal: 0x2E,
    QtCore.Qt.Key.Key_BracketLeft: 0x2F, QtCore.Qt.Key.Key_BracketRight: 0x30,
    QtCore.Qt.Key.Key_Backslash: 0x31,
    QtCore.Qt.Key.Key_Semicolon: 0x33, QtCore.Qt.Key.Key_Apostrophe: 0x34,
    QtCore.Qt.Key.Key_QuoteLeft: 0x35, QtCore.Qt.Key.Key_Comma: 0x36,
    QtCore.Qt.Key.Key_Period: 0x37, QtCore.Qt.Key.Key_Slash: 0x38,
    QtCore.Qt.Key.Key_CapsLock: 0x39,
    QtCore.Qt.Key.Key_F1: 0x3A, QtCore.Qt.Key.Key_F2: 0x3B, QtCore.Qt.Key.Key_F3: 0x3C,
    QtCore.Qt.Key.Key_F4: 0x3D, QtCore.Qt.Key.Key_F5: 0x3E, QtCore.Qt.Key.Key_F6: 0x3F,
    QtCore.Qt.Key.Key_F7: 0x40, QtCore.Qt.Key.Key_F8: 0x41, QtCore.Qt.Key.Key_F9: 0x42,
    QtCore.Qt.Key.Key_F10: 0x43, QtCore.Qt.Key.Key_F11: 0x44, QtCore.Qt.Key.Key_F12: 0x45,
    QtCore.Qt.Key.Key_Print: 0x46, QtCore.Qt.Key.Key_ScrollLock: 0x47, QtCore.Qt.Key.Key_Pause: 0x48,
    QtCore.Qt.Key.Key_Insert: 0x49, QtCore.Qt.Key.Key_Home: 0x4A, QtCore.Qt.Key.Key_PageUp: 0x4B,
    QtCore.Qt.Key.Key_Delete: 0x4C, QtCore.Qt.Key.Key_End: 0x4D, QtCore.Qt.Key.Key_PageDown: 0x4E,
    QtCore.Qt.Key.Key_Right: 0x4F, QtCore.Qt.Key.Key_Left: 0x50,
    QtCore.Qt.Key.Key_Down: 0x51, QtCore.Qt.Key.Key_Up: 0x52,
    QtCore.Qt.Key.Key_Shift: 0xE1,
    QtCore.Qt.Key.Key_Control: 0xE0,
    QtCore.Qt.Key.Key_Alt: 0xE2,
    QtCore.Qt.Key.Key_Meta: 0xE3,
}


class KeyRecorderWidget(QtWidgets.QLineEdit):
    """Line edit that captures keyboard shortcuts upon keypress."""
    shortcut_captured = QtCore.Signal(int, int)  # keycode, modifiers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click here and press any key / shortcut...")
        self.current_keycode = 0
        self.current_modifiers = 0

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()

        # Handle standalone modifier presses
        if key in (QtCore.Qt.Key.Key_Control, QtCore.Qt.Key.Key_Shift, QtCore.Qt.Key.Key_Alt, QtCore.Qt.Key.Key_Meta):
            hid_code = QT_KEY_TO_HID.get(key, 0)
            if hid_code:
                self.current_keycode = hid_code
                self.current_modifiers = 0
                name = HID_KEYCODES.get(hid_code, f"0x{hid_code:02X}")
                self.setText(name)
                self.shortcut_captured.emit(self.current_keycode, 0)
                event.accept()
                return

        mods = 0
        event_mods = event.modifiers()
        if event_mods & QtCore.Qt.KeyboardModifier.ControlModifier:
            mods |= MODIFIER_LEFT_CTRL
        if event_mods & QtCore.Qt.KeyboardModifier.ShiftModifier:
            mods |= MODIFIER_LEFT_SHIFT
        if event_mods & QtCore.Qt.KeyboardModifier.AltModifier:
            mods |= MODIFIER_LEFT_ALT
        if event_mods & QtCore.Qt.KeyboardModifier.MetaModifier:
            mods |= MODIFIER_LEFT_GUI

        hid_code = QT_KEY_TO_HID.get(key, 0)
        if hid_code:
            self.current_keycode = hid_code
            self.current_modifiers = mods

            # Update display text
            parts = []
            if mods & MODIFIER_LEFT_CTRL:
                parts.append("Ctrl")
            if mods & MODIFIER_LEFT_SHIFT:
                parts.append("Shift")
            if mods & MODIFIER_LEFT_ALT:
                parts.append("Alt")
            if mods & MODIFIER_LEFT_GUI:
                parts.append("Super")
            parts.append(HID_KEYCODES.get(hid_code, f"0x{hid_code:02X}"))

            self.setText(" + ".join(parts))
            self.shortcut_captured.emit(self.current_keycode, self.current_modifiers)
            event.accept()
        else:
            super().keyPressEvent(event)


class ButtonEditorDialog(QtWidgets.QDialog):
    def __init__(self, button_num: int, button_label: str, current_action: ButtonAction, parent=None):
        super().__init__(parent)
        self.button_num = button_num
        self.button_label = button_label
        self.action = current_action
        self.result_action = ButtonAction(
            behavior=current_action.behavior,
            action_type=current_action.action_type,
            value=current_action.value,
            modifiers=current_action.modifiers,
            data=current_action.data,
            sector=current_action.sector,
            address=current_action.address,
        )

        self.setWindowTitle(f"Edit {button_label}")
        self.resize(460, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Header
        header = QtWidgets.QLabel(f"<b>{self.button_label}</b>")
        header.setStyleSheet("font-size: 15px; margin-bottom: 8px;")
        layout.addWidget(header)

        # Tab widget for action category
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # Tab 0: Keyboard Shortcut (Leftmost default)
        tab_key = QtWidgets.QWidget()
        tk_layout = QtWidgets.QVBoxLayout(tab_key)
        tk_layout.addWidget(QtWidgets.QLabel("Press any key or combination:"))
        self.recorder = KeyRecorderWidget()
        self.recorder.shortcut_captured.connect(self._on_shortcut_captured)
        tk_layout.addWidget(self.recorder)

        # Manual dropdowns as secondary option
        tk_layout.addWidget(QtWidgets.QLabel("Or manually select key & modifiers:"))
        mod_box = QtWidgets.QHBoxLayout()
        self.chk_ctrl = QtWidgets.QCheckBox("Ctrl")
        self.chk_shift = QtWidgets.QCheckBox("Shift")
        self.chk_alt = QtWidgets.QCheckBox("Alt")
        self.chk_super = QtWidgets.QCheckBox("Super")
        self.chk_ctrl.toggled.connect(self._on_manual_key_changed)
        self.chk_shift.toggled.connect(self._on_manual_key_changed)
        self.chk_alt.toggled.connect(self._on_manual_key_changed)
        self.chk_super.toggled.connect(self._on_manual_key_changed)
        mod_box.addWidget(self.chk_ctrl)
        mod_box.addWidget(self.chk_shift)
        mod_box.addWidget(self.chk_alt)
        mod_box.addWidget(self.chk_super)
        tk_layout.addLayout(mod_box)

        self.combo_key = QtWidgets.QComboBox()
        for code, name in sorted(HID_KEYCODES.items(), key=lambda x: x[1]):
            if code != 0:
                self.combo_key.addItem(name, code)
        self.combo_key.currentIndexChanged.connect(self._on_manual_key_changed)
        tk_layout.addWidget(self.combo_key)
        tk_layout.addStretch()
        self.tab_widget.addTab(tab_key, "Keyboard Key")

        # Tab 1: Mouse Button Click
        tab_mouse = QtWidgets.QWidget()
        tm_layout = QtWidgets.QVBoxLayout(tab_mouse)
        tm_layout.addWidget(QtWidgets.QLabel("Select standard mouse button action:"))
        self.combo_mouse_button = QtWidgets.QComboBox()
        for mask, name in MOUSE_BUTTONS.items():
            self.combo_mouse_button.addItem(name, mask)
        tm_layout.addWidget(self.combo_mouse_button)
        tm_layout.addStretch()
        self.tab_widget.addTab(tab_mouse, "Mouse Click")

        # Tab 2: Hardware Functions
        tab_func = QtWidgets.QWidget()
        tf_layout = QtWidgets.QVBoxLayout(tab_func)
        tf_layout.addWidget(QtWidgets.QLabel("Select hardware/DPI function:"))
        self.combo_function = QtWidgets.QComboBox()
        for fid, name in sorted(FUNCTION_ACTIONS.items()):
            if fid != 0:
                self.combo_function.addItem(name, fid)
        tf_layout.addWidget(self.combo_function)
        tf_layout.addStretch()
        self.tab_widget.addTab(tab_func, "DPI / Function")

        # Tab 3: Disabled
        tab_disabled = QtWidgets.QWidget()
        td_layout = QtWidgets.QVBoxLayout(tab_disabled)
        td_layout.addWidget(QtWidgets.QLabel("Disables this button so it performs no action."))
        td_layout.addStretch()
        self.tab_widget.addTab(tab_disabled, "Disabled")

        # Default to Keyboard Key tab
        self.tab_widget.setCurrentIndex(0)

        # Set initial values based on current action
        self._populate_current()

        # Auto-focus the key recorder input
        QtCore.QTimer.singleShot(50, self.recorder.setFocus)

        # Bottom buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _populate_current(self):
        if self.action.behavior == 8 and self.action.action_type == 2:
            self.tab_widget.setCurrentIndex(0)
            idx = self.combo_key.findData(self.action.value)
            if idx >= 0:
                self.combo_key.setCurrentIndex(idx)
            self.chk_ctrl.setChecked(bool(self.action.modifiers & 0x11))
            self.chk_shift.setChecked(bool(self.action.modifiers & 0x22))
            self.chk_alt.setChecked(bool(self.action.modifiers & 0x44))
            self.chk_super.setChecked(bool(self.action.modifiers & 0x88))
            self.recorder.setText(self.action.display_name())
        elif self.action.behavior == 8 and self.action.action_type == 1:
            self.tab_widget.setCurrentIndex(1)
            idx = self.combo_mouse_button.findData(self.action.value)
            if idx >= 0:
                self.combo_mouse_button.setCurrentIndex(idx)
        elif self.action.behavior == 9:
            self.tab_widget.setCurrentIndex(2)
            idx = self.combo_function.findData(self.action.value)
            if idx >= 0:
                self.combo_function.setCurrentIndex(idx)
        elif self.action.behavior in (15, 8) and self.action.action_type == 4:
            self.tab_widget.setCurrentIndex(3)
        else:
            self.tab_widget.setCurrentIndex(0)

    def _on_shortcut_captured(self, keycode: int, modifiers: int):
        idx = self.combo_key.findData(keycode)
        if idx >= 0:
            self.combo_key.setCurrentIndex(idx)
        self.chk_ctrl.setChecked(bool(modifiers & MODIFIER_LEFT_CTRL))
        self.chk_shift.setChecked(bool(modifiers & MODIFIER_LEFT_SHIFT))
        self.chk_alt.setChecked(bool(modifiers & MODIFIER_LEFT_ALT))
        self.chk_super.setChecked(bool(modifiers & MODIFIER_LEFT_GUI))

    def _on_manual_key_changed(self):
        # Update recorder preview
        mods = 0
        if self.chk_ctrl.isChecked():
            mods |= MODIFIER_LEFT_CTRL
        if self.chk_shift.isChecked():
            mods |= MODIFIER_LEFT_SHIFT
        if self.chk_alt.isChecked():
            mods |= MODIFIER_LEFT_ALT
        if self.chk_super.isChecked():
            mods |= MODIFIER_LEFT_GUI

        keycode = self.combo_key.currentData()
        parts = []
        if mods & MODIFIER_LEFT_CTRL:
            parts.append("Ctrl")
        if mods & MODIFIER_LEFT_SHIFT:
            parts.append("Shift")
        if mods & MODIFIER_LEFT_ALT:
            parts.append("Alt")
        if mods & MODIFIER_LEFT_GUI:
            parts.append("Super")
        parts.append(self.combo_key.currentText())
        self.recorder.setText(" + ".join(parts))

    def _on_accept(self):
        tab_idx = self.tab_widget.currentIndex()
        if tab_idx == 0:  # Mouse Click
            mask = self.combo_mouse_button.currentData()
            self.result_action = ButtonAction.mouse_click(mask)
        elif tab_idx == 1:  # Keyboard
            keycode = self.combo_key.currentData()
            mods = 0
            if self.chk_ctrl.isChecked():
                mods |= MODIFIER_LEFT_CTRL
            if self.chk_shift.isChecked():
                mods |= MODIFIER_LEFT_SHIFT
            if self.chk_alt.isChecked():
                mods |= MODIFIER_LEFT_ALT
            if self.chk_super.isChecked():
                mods |= MODIFIER_LEFT_GUI
            self.result_action = ButtonAction.key_shortcut(keycode, mods)
        elif tab_idx == 2:  # Function
            fid = self.combo_function.currentData()
            self.result_action = ButtonAction.function(fid)
        elif tab_idx == 3:  # Disabled
            self.result_action = ButtonAction.disabled()

        self.accept()
