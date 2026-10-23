"""Hardware RGB Lighting configuration dialog.

Directly configures and burns RGB lighting effects (Static, Breathing,
Color Cycle, Off) into Logitech mouse EEPROM and RAM over HID++ 2.0 (0x8071).
"""

from typing import Optional, Tuple
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from core.backend import MouseBackend


class RGBLightingDialog(QtWidgets.QDialog):
    """Dialog for configuring hardware RGB lighting directly on the mouse."""

    def __init__(self, backend: MouseBackend, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.backend = backend
        self.setWindowTitle("Hardware RGB Lighting")
        self.resize(520, 520)

        self.qsettings = QtCore.QSettings("LogitechLinux", "OnboardMemoryManager")

        # Load saved preferences or defaults
        self.current_effect = self.qsettings.value("rgb_effect_mode", "static", type=str)
        self.current_color = QtGui.QColor(self.qsettings.value("rgb_color_hex", "#00aeef", type=str))
        if not self.current_color.isValid():
            self.current_color = QtGui.QColor(0, 174, 239)
        self.current_brightness = int(self.qsettings.value("rgb_brightness", 100))
        self.current_speed_ms = int(self.qsettings.value("rgb_speed_ms", 5000))
        self.current_waveform = int(self.qsettings.value("rgb_waveform", 6))  # Default to Exponential (6) for smoother low-brightness curve

        self._setup_styling()
        self._init_ui()
        self._update_ui_state()

    def _setup_styling(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e24;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Inter', 'Segoe UI', 'Noto Sans', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #33333e;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 14px;
                font-weight: bold;
                color: #60a5fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #1a1a20;
                border: 1px solid #3f3f4e;
                border-radius: 4px;
                padding: 6px 10px;
                color: #ffffff;
                font-size: 13px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2a2a36;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #3b82f6;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#secondaryBtn {
                background-color: #2e2e38;
                color: #e0e0e0;
                border: 1px solid #3f3f4e;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #3f3f4e;
            }
            QPushButton#dangerBtn {
                background-color: #dc2626;
                color: #ffffff;
            }
            QPushButton#dangerBtn:hover {
                background-color: #b91c1c;
            }
            QPushButton#colorBtn {
                border: 2px solid #ffffff;
                border-radius: 6px;
                min-height: 36px;
            }
            QPushButton#swatchBtn {
                border: 1px solid #4b5563;
                border-radius: 4px;
                min-width: 28px;
                min-height: 24px;
                padding: 0;
            }
        """)

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Title & Subtitle
        lbl_title = QtWidgets.QLabel("Hardware RGB Lighting")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        lbl_desc = QtWidgets.QLabel(
            "Hardware lighting runs inside the mouse onboard controller and flash EEPROM.\n"
            "Effects persist across power cycles, reboots, and systems without host software."
        )
        lbl_desc.setStyleSheet("color: #9ca3af; font-size: 12px;")
        main_layout.addWidget(lbl_title)
        main_layout.addWidget(lbl_desc)

        # Effect Mode Selection
        mode_group = QtWidgets.QGroupBox("Lighting Effect")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)

        self.combo_effect = QtWidgets.QComboBox()
        self.combo_effect.addItem("Static (Fixed Color)", "static")
        self.combo_effect.addItem("Breathing", "breathing")
        self.combo_effect.addItem("Color Cycle", "cycle")
        self.combo_effect.addItem("Off (Disabled)", "off")

        idx = self.combo_effect.findData(self.current_effect)
        if idx >= 0:
            self.combo_effect.setCurrentIndex(idx)
        self.combo_effect.currentIndexChanged.connect(self._on_effect_changed)

        mode_layout.addWidget(self.combo_effect)
        main_layout.addWidget(mode_group)

        # Color Selection Group
        self.color_group = QtWidgets.QGroupBox("Color Selection")
        color_layout = QtWidgets.QVBoxLayout(self.color_group)

        color_picker_row = QtWidgets.QHBoxLayout()
        self.btn_color_picker = QtWidgets.QPushButton()
        self.btn_color_picker.setObjectName("colorBtn")
        self.btn_color_picker.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_color_picker.clicked.connect(self._on_pick_color)

        self.lbl_hex = QtWidgets.QLabel()
        self.lbl_hex.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold;")

        color_picker_row.addWidget(self.btn_color_picker, stretch=3)
        color_picker_row.addWidget(self.lbl_hex, stretch=1)
        color_layout.addLayout(color_picker_row)

        # Quick Swatches
        lbl_quick = QtWidgets.QLabel("Quick Presets:")
        lbl_quick.setStyleSheet("color: #9ca3af; font-size: 11px; margin-top: 4px;")
        color_layout.addWidget(lbl_quick)

        swatch_layout = QtWidgets.QHBoxLayout()
        preset_colors = [
            ("Logitech Cyan", "#00aeef"),
            ("Red", "#ef4444"),
            ("Green", "#22c55e"),
            ("Blue", "#3b82f6"),
            ("Yellow", "#eab308"),
            ("Purple", "#a855f7"),
            ("White", "#ffffff"),
        ]
        for name, hex_val in preset_colors:
            btn_swatch = QtWidgets.QPushButton()
            btn_swatch.setObjectName("swatchBtn")
            btn_swatch.setToolTip(f"{name} ({hex_val})")
            btn_swatch.setStyleSheet(f"background-color: {hex_val};")
            btn_swatch.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            btn_swatch.clicked.connect(lambda _, h=hex_val: self._set_color_hex(h))
            swatch_layout.addWidget(btn_swatch)
        color_layout.addLayout(swatch_layout)

        main_layout.addWidget(self.color_group)

        # Brightness Group
        self.brightness_group = QtWidgets.QGroupBox("Brightness")
        brightness_layout = QtWidgets.QHBoxLayout(self.brightness_group)

        self.slider_brightness = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_brightness.setRange(1, 100)
        self.slider_brightness.setValue(self.current_brightness)
        self.slider_brightness.valueChanged.connect(self._on_brightness_slider_changed)

        self.lbl_brightness_val = QtWidgets.QLabel(f"{self.current_brightness}%")
        self.lbl_brightness_val.setStyleSheet("min-width: 48px; font-weight: bold;")

        brightness_layout.addWidget(self.slider_brightness, stretch=4)
        brightness_layout.addWidget(self.lbl_brightness_val, stretch=1)
        main_layout.addWidget(self.brightness_group)

        # Cycle / Breathing Speed Group
        self.speed_group = QtWidgets.QGroupBox("Effect Speed / Cycle Period")
        speed_layout = QtWidgets.QHBoxLayout(self.speed_group)

        self.slider_speed = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_speed.setRange(1000, 20000)
        self.slider_speed.setSingleStep(500)
        self.slider_speed.setValue(self.current_speed_ms)
        self.slider_speed.valueChanged.connect(self._on_speed_slider_changed)

        self.lbl_speed_val = QtWidgets.QLabel(f"{self.current_speed_ms / 1000.0:.1f}s")
        self.lbl_speed_val.setStyleSheet("min-width: 48px; font-weight: bold;")

        speed_layout.addWidget(self.slider_speed, stretch=4)
        speed_layout.addWidget(self.lbl_speed_val, stretch=1)
        main_layout.addWidget(self.speed_group)

        # Breathing Curve / Waveform Group
        self.waveform_group = QtWidgets.QGroupBox("Breathing Transition Curve")
        wf_layout = QtWidgets.QVBoxLayout(self.waveform_group)

        self.combo_waveform = QtWidgets.QComboBox()
        self.combo_waveform.addItem("Exponential (Compensates for Low-Light Stepping)", 6)
        self.combo_waveform.addItem("Sine Wave (Standard)", 1)
        self.combo_waveform.addItem("Smooth Default", 0)
        self.combo_waveform.addItem("Sharkfin", 5)
        self.combo_waveform.addItem("Triangle", 3)

        idx_wf = self.combo_waveform.findData(self.current_waveform)
        if idx_wf >= 0:
            self.combo_waveform.setCurrentIndex(idx_wf)
        self.combo_waveform.currentIndexChanged.connect(
            lambda idx: setattr(self, "current_waveform", self.combo_waveform.currentData())
        )
        wf_layout.addWidget(self.combo_waveform)
        main_layout.addWidget(self.waveform_group)

        # Status / Feedback Label
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold; min-height: 20px;")
        main_layout.addWidget(self.lbl_status)

        # Action Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_turn_off = QtWidgets.QPushButton("Turn Off RGB")
        self.btn_turn_off.setObjectName("dangerBtn")
        self.btn_turn_off.clicked.connect(self._on_turn_off)
        btn_layout.addWidget(self.btn_turn_off)

        self.btn_preview = QtWidgets.QPushButton("Live Preview")
        self.btn_preview.setObjectName("secondaryBtn")
        self.btn_preview.clicked.connect(self._on_live_preview)
        btn_layout.addWidget(self.btn_preview)

        self.btn_burn = QtWidgets.QPushButton("Burn to Memory (Permanent)")
        self.btn_burn.clicked.connect(self._on_burn_to_memory)
        btn_layout.addWidget(self.btn_burn)

        main_layout.addLayout(btn_layout)

        # Update color swatch visually
        self._update_color_swatch()

    def _update_ui_state(self):
        effect = self.combo_effect.currentData()
        if effect == "off":
            self.color_group.setEnabled(False)
            self.brightness_group.setEnabled(False)
            self.speed_group.setEnabled(False)
            if hasattr(self, "waveform_group"):
                self.waveform_group.setVisible(False)
            self.btn_preview.setEnabled(False)
        elif effect == "static":
            self.color_group.setEnabled(True)
            self.brightness_group.setEnabled(True)
            self.speed_group.setEnabled(False)
            if hasattr(self, "waveform_group"):
                self.waveform_group.setVisible(False)
            self.btn_preview.setEnabled(True)
        elif effect == "breathing":
            self.color_group.setEnabled(True)
            self.brightness_group.setEnabled(True)
            self.speed_group.setEnabled(True)
            if hasattr(self, "waveform_group"):
                self.waveform_group.setVisible(True)
                self.waveform_group.setEnabled(True)
            self.btn_preview.setEnabled(True)
        elif effect == "cycle":
            self.color_group.setEnabled(False)
            self.brightness_group.setEnabled(True)
            self.speed_group.setEnabled(True)
            if hasattr(self, "waveform_group"):
                self.waveform_group.setVisible(False)
            self.btn_preview.setEnabled(True)

    def _update_color_swatch(self):
        hex_str = self.current_color.name().upper()
        self.lbl_hex.setText(hex_str)
        # Invert text color for readability if needed
        lum = (0.299 * self.current_color.red() + 0.587 * self.current_color.green() + 0.114 * self.current_color.blue())
        fg_col = "#000000" if lum > 140 else "#ffffff"
        self.btn_color_picker.setStyleSheet(
            f"background-color: {hex_str}; color: {fg_col}; font-weight: bold; border-radius: 4px; padding: 8px;"
        )
        self.btn_color_picker.setText(f"Choose Custom Color ({hex_str})")

    def _on_effect_changed(self, idx: int):
        self.current_effect = self.combo_effect.currentData()
        self._update_ui_state()

    def _on_pick_color(self):
        col = QtWidgets.QColorDialog.getColor(self.current_color, self, "Select RGB Lighting Color")
        if col.isValid():
            self.current_color = col
            self._update_color_swatch()

    def _set_color_hex(self, hex_val: str):
        col = QtGui.QColor(hex_val)
        if col.isValid():
            self.current_color = col
            self._update_color_swatch()

    def _on_brightness_slider_changed(self, val: int):
        self.current_brightness = val
        self.lbl_brightness_val.setText(f"{val}%")

    def _on_speed_slider_changed(self, val: int):
        self.current_speed_ms = val
        self.lbl_speed_val.setText(f"{val / 1000.0:.1f}s")

    def _save_preferences(self):
        self.qsettings.setValue("rgb_effect_mode", self.current_effect)
        self.qsettings.setValue("rgb_color_hex", self.current_color.name())
        self.qsettings.setValue("rgb_brightness", self.current_brightness)
        self.qsettings.setValue("rgb_speed_ms", self.current_speed_ms)
        if hasattr(self, "combo_waveform"):
            self.qsettings.setValue("rgb_waveform", self.combo_waveform.currentData())

    def _on_live_preview(self):
        """Sends lighting parameters to mouse RAM only for real-time preview."""
        effect = self.combo_effect.currentData()
        self.lbl_status.setText("Previewing effect on mouse...")
        QtWidgets.QApplication.processEvents()

        wf = self.combo_waveform.currentData() if hasattr(self, "combo_waveform") else 1
        ok, msg = self.backend.set_lighting_effect(
            effect_type=effect,
            r=self.current_color.red(),
            g=self.current_color.green(),
            b=self.current_color.blue(),
            brightness=self.current_brightness,
            period_ms=self.current_speed_ms,
            waveform=wf,
            persistent=False
        )
        if ok:
            self.lbl_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
            self.lbl_status.setText("Live preview active (RAM).")
        else:
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            self.lbl_status.setText(f"Preview error: {msg}")

    def _on_burn_to_memory(self):
        """Burns lighting parameters to EEPROM and RAM so it persists across power cycles."""
        effect = self.combo_effect.currentData()
        if effect == "off":
            self._on_turn_off()
            return

        self.lbl_status.setText("Burning effect into mouse EEPROM...")
        QtWidgets.QApplication.processEvents()

        wf = self.combo_waveform.currentData() if hasattr(self, "combo_waveform") else 1
        ok, msg = self.backend.set_lighting_effect(
            effect_type=effect,
            r=self.current_color.red(),
            g=self.current_color.green(),
            b=self.current_color.blue(),
            brightness=self.current_brightness,
            period_ms=self.current_speed_ms,
            waveform=wf,
            persistent=True
        )
        if ok:
            self._save_preferences()
            self.lbl_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
            self.lbl_status.setText("Effect burned to mouse memory (EEPROM).")
        else:
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            self.lbl_status.setText(f"Burn error: {msg}")

    def _on_turn_off(self):
        self.lbl_status.setText("Disabling hardware RGB lighting...")
        QtWidgets.QApplication.processEvents()

        ok, msg = self.backend.turn_off_lighting()
        if ok:
            self.combo_effect.setCurrentIndex(self.combo_effect.findData("off"))
            self._save_preferences()
            self.lbl_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
            self.lbl_status.setText("Lighting completely turned off.")
        else:
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            self.lbl_status.setText(f"Error: {msg}")
