"""Interactive visual mouse diagram supporting multiple Logitech mouse model variations."""

from PySide6 import QtCore, QtGui, QtWidgets
from typing import Dict, Optional, Tuple


class MouseCanvas(QtWidgets.QWidget):
    """Interactive visualizer widget rendering mouse outlines and button hotspots for various models."""

    button_clicked = QtCore.Signal(int)
    button_double_clicked = QtCore.Signal(int)

    # Hotspot definitions per model family on a 540x540 virtual canvas
    # Each entry defines: pos=(badge_x, badge_y), target=(switch_x, switch_y), tag="Label", box_w=width
    MODEL_BUTTONS = {
        "g502": {
            1: {"tag": "B1: Left Click", "pos": (205, 138), "target": (225, 138), "box_w": 95},
            2: {"tag": "B2: Right Click", "pos": (445, 125), "target": (335, 125), "box_w": 100},
            3: {"tag": "B3: Middle Click", "pos": (270, 85), "target": (270, 85), "box_w": 105},
            6: {"tag": "B6: Forward (G5)", "pos": (68, 185), "target": (156, 185), "box_w": 105},
            4: {"tag": "B4: Back (G4)", "pos": (68, 250), "target": (153, 250), "box_w": 95},
            5: {"tag": "B5: DPI Shift (G6)", "pos": (68, 315), "target": (149, 315), "box_w": 110},
            7: {"tag": "B7: Tilt ◀", "pos": (175, 25), "target": (248, 75), "box_w": 80},
            8: {"tag": "B8: Tilt ▶", "pos": (365, 25), "target": (292, 75), "box_w": 80},
            9: {"tag": "B9: Profile", "pos": (270, 185), "target": (270, 185), "box_w": 90},
            10: {"tag": "B10: G7 (DPI-)", "pos": (68, 65), "target": (172, 68), "box_w": 95},
            11: {"tag": "B11: G8 (DPI+)", "pos": (68, 122), "target": (167, 110), "box_w": 95},
        },
        "gpro": {
            1: {"tag": "B1: Left Click", "pos": (205, 135), "target": (205, 135), "box_w": 105},
            2: {"tag": "B2: Right Click", "pos": (415, 125), "target": (335, 125), "box_w": 110},
            3: {"tag": "B3: Wheel Press", "pos": (270, 95), "target": (270, 95), "box_w": 115},
            4: {"tag": "B4: Thumb Back", "pos": (85, 260), "target": (172, 260), "box_w": 112},
            5: {"tag": "B5: Thumb Fwd", "pos": (85, 195), "target": (174, 195), "box_w": 112},
        },
        "g305": {
            1: {"tag": "B1: Left Click", "pos": (205, 135), "target": (205, 135), "box_w": 105},
            2: {"tag": "B2: Right Click", "pos": (415, 125), "target": (335, 125), "box_w": 110},
            3: {"tag": "B3: Wheel Press", "pos": (270, 95), "target": (270, 95), "box_w": 115},
            4: {"tag": "B4: Thumb Back", "pos": (85, 265), "target": (178, 265), "box_w": 112},
            5: {"tag": "B5: Thumb Fwd", "pos": (85, 205), "target": (180, 205), "box_w": 112},
            6: {"tag": "B6: DPI", "pos": (270, 175), "target": (270, 175), "box_w": 85},
        },
        "g703": {
            1: {"tag": "B1: Left Click", "pos": (205, 135), "target": (205, 135), "box_w": 105},
            2: {"tag": "B2: Right Click", "pos": (420, 125), "target": (340, 125), "box_w": 110},
            3: {"tag": "B3: Wheel Press", "pos": (270, 95), "target": (270, 95), "box_w": 115},
            4: {"tag": "B4: Thumb Back", "pos": (85, 275), "target": (176, 275), "box_w": 112},
            5: {"tag": "B5: Thumb Fwd", "pos": (85, 210), "target": (178, 210), "box_w": 112},
            6: {"tag": "B6: DPI", "pos": (270, 175), "target": (270, 175), "box_w": 85},
        },
        "g903": {
            1: {"tag": "B1: Left Click", "pos": (200, 125), "target": (200, 125), "box_w": 105},
            2: {"tag": "B2: Right Click", "pos": (340, 125), "target": (340, 125), "box_w": 105},
            3: {"tag": "B3: Wheel Press", "pos": (270, 90), "target": (270, 90), "box_w": 115},
            4: {"tag": "B4: L-Back", "pos": (85, 270), "target": (182, 270), "box_w": 95},
            5: {"tag": "B5: L-Fwd", "pos": (85, 205), "target": (182, 205), "box_w": 95},
            6: {"tag": "B6: R-Back", "pos": (455, 270), "target": (358, 270), "box_w": 95},
            7: {"tag": "B7: R-Fwd", "pos": (455, 205), "target": (358, 205), "box_w": 95},
            8: {"tag": "B8: Tilt ◀", "pos": (195, 42), "target": (252, 85), "box_w": 85},
            9: {"tag": "B9: Tilt ▶", "pos": (345, 42), "target": (288, 85), "box_w": 85},
            10: {"tag": "B10: DPI-", "pos": (270, 155), "target": (270, 155), "box_w": 85},
            11: {"tag": "B11: DPI+", "pos": (270, 195), "target": (270, 195), "box_w": 85},
        },
        "g604": {
            1: {"tag": "B1: Left Click", "pos": (205, 125), "target": (205, 125), "box_w": 105},
            2: {"tag": "B2: Right Click", "pos": (420, 125), "target": (340, 125), "box_w": 110},
            3: {"tag": "B3: Wheel Press", "pos": (270, 90), "target": (270, 90), "box_w": 115},
            4: {"tag": "B4: G4", "pos": (70, 215), "target": (175, 215), "box_w": 80},
            5: {"tag": "B5: G5", "pos": (70, 260), "target": (170, 260), "box_w": 80},
            6: {"tag": "B6: G6", "pos": (70, 305), "target": (168, 305), "box_w": 80},
            7: {"tag": "B7: G7", "pos": (70, 170), "target": (180, 175), "box_w": 80},
            8: {"tag": "B8: G8", "pos": (148, 160), "target": (185, 200), "box_w": 80},
            9: {"tag": "B9: G9", "pos": (148, 345), "target": (175, 290), "box_w": 80},
            10: {"tag": "B10: Tilt ◀", "pos": (195, 42), "target": (250, 85), "box_w": 85},
            11: {"tag": "B11: Tilt ▶", "pos": (345, 42), "target": (290, 85), "box_w": 85},
            12: {"tag": "B12: DPI-", "pos": (270, 155), "target": (270, 155), "box_w": 85},
            13: {"tag": "B13: DPI+", "pos": (270, 195), "target": (270, 195), "box_w": 85},
            14: {"tag": "B14: Prof", "pos": (270, 235), "target": (270, 235), "box_w": 85},
            15: {"tag": "B15: BT", "pos": (270, 275), "target": (270, 275), "box_w": 85},
        },
    }

    def __init__(self, parent=None, model_key: str = "g502"):
        super().__init__(parent)
        self.setMinimumSize(480, 520)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self.model_key = model_key
        self.selected_button: Optional[int] = None
        self.hovered_button: Optional[int] = None
        self._button_rects: Dict[int, QtCore.QRectF] = {}
        self.custom_actions: Dict[int, str] = {}

    def set_button_actions(self, actions: Dict[int, str]):
        """Sets user-assigned action names for each button and refreshes display."""
        self.custom_actions = actions
        self.update()

    def _get_button_tag(self, b_num: int, default_tag: str) -> str:
        if b_num in self.custom_actions and self.custom_actions[b_num]:
            action_name = self.custom_actions[b_num]
            if action_name.startswith(f"B{b_num}:"):
                display = action_name[len(f"B{b_num}:"):].strip()
            else:
                display = action_name.strip()

            # Remove any "Macro: " or "Macro" prefix
            for pfx in ("Macro: ", "Macro:", "Macro "):
                if display.startswith(pfx):
                    display = display[len(pfx):].strip()
                    break

            display = display.replace(" (Sniper)", "")
            return f"B{b_num}: {display}"
        return default_tag

    def set_model(self, model_key: str):
        if model_key in self.MODEL_BUTTONS and self.model_key != model_key:
            self.model_key = model_key
            self.selected_button = None
            self.hovered_button = None
            self.update()

    def set_selected_button(self, button_num: Optional[int]):
        if self.selected_button != button_num:
            self.selected_button = button_num
            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        pos = event.position()
        found = None
        for b_num, rect in self._button_rects.items():
            if rect.contains(pos):
                found = b_num
                break

        if found != self.hovered_button:
            self.hovered_button = found
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor if found else QtCore.Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, event: QtCore.QEvent):
        if self.hovered_button is not None:
            self.hovered_button = None
            self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            pos = event.position()
            for b_num, rect in self._button_rects.items():
                if rect.contains(pos):
                    self.selected_button = b_num
                    self.button_clicked.emit(b_num)
                    self.update()
                    return

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            pos = event.position()
            for b_num, rect in self._button_rects.items():
                if rect.contains(pos):
                    self.selected_button = b_num
                    self.button_double_clicked.emit(b_num)
                    self.update()
                    return

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Dark Canvas Background
        painter.fillRect(0, 0, w, h, QtGui.QColor("#13151b"))

        buttons_dict = self.MODEL_BUTTONS.get(self.model_key, self.MODEL_BUTTONS["g502"])

        # Base bounds of mouse chassis
        min_x, max_x = 120.0, 400.0
        min_y, max_y = 20.0, 485.0

        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        fm = QtGui.QFontMetrics(font)

        for b_num, info in buttons_dict.items():
            cx, cy = info["pos"]
            tx_pt, ty_pt = info["target"]
            tag = self._get_button_tag(b_num, info["tag"])
            text_w = fm.horizontalAdvance(tag)
            bw = max(info.get("box_w", 80), text_w + 16)
            bh = 28
            min_x = min(min_x, cx - bw / 2.0, tx_pt)
            max_x = max(max_x, cx + bw / 2.0, tx_pt)
            min_y = min(min_y, cy - bh / 2.0, ty_pt)
            max_y = max(max_y, cy + bh / 2.0, ty_pt)

        content_w = max_x - min_x
        content_h = max_y - min_y
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0

        padding = 16.0
        scale = min((w - 2 * padding) / content_w, (h - 2 * padding) / content_h)
        dx = (w / 2.0) - (center_x * scale)
        dy = (h / 2.0) - (center_y * scale)

        painter.save()
        painter.translate(dx, dy)
        painter.scale(scale, scale)

        self._draw_mouse_chassis(painter)
        self._draw_button_hotspots(painter, fm)

        painter.restore()

    def _draw_mouse_chassis(self, painter: QtGui.QPainter):
        model = self.model_key

        if model in ("gpro", "g305"):
            # Symmetrical Oval / Egg Contour
            path = QtGui.QPainterPath()
            path.moveTo(270, 36)
            path.cubicTo(325, 36, 365, 85, 370, 170)
            path.cubicTo(375, 260, 365, 380, 350, 430)
            path.cubicTo(335, 480, 290, 490, 270, 490)
            path.cubicTo(250, 490, 205, 480, 190, 430)
            path.cubicTo(175, 380, 165, 260, 170, 170)
            path.cubicTo(175, 85, 215, 36, 270, 36)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 36, 270, 490)
            grad.setColorAt(0.0, QtGui.QColor("#272d3b"))
            grad.setColorAt(0.6, QtGui.QColor("#1e222c"))
            grad.setColorAt(1.0, QtGui.QColor("#15171e"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#53627c"), 2.4))
            painter.drawPath(path)

            # Center split line
            painter.setPen(QtGui.QPen(QtGui.QColor("#384152"), 2))
            painter.drawLine(270, 38, 270, 160)

            # Side Thumb Buttons
            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 1.6))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1b1e27")))
            painter.drawRoundedRect(165, 185, 13, 26, 3, 3)
            painter.drawRoundedRect(163, 245, 13, 28, 3, 3)

            # Scroll Wheel Housing
            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 2))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#0f1115")))
            painter.drawRoundedRect(257, 56, 26, 76, 7, 7)
            painter.setPen(QtGui.QPen(QtGui.QColor("#47536b"), 1.5))
            for y in range(64, 126, 9):
                painter.drawLine(261, y, 279, y)

            if model == "g305":
                painter.setPen(QtGui.QPen(QtGui.QColor("#4b5770"), 1.6))
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#181b22")))
                painter.drawRoundedRect(263, 165, 14, 22, 3, 3)

        elif model in ("g703", "g403", "g603"):
            path = QtGui.QPainterPath()
            path.moveTo(270, 36)
            path.cubicTo(330, 36, 375, 85, 380, 170)
            path.cubicTo(385, 260, 375, 390, 355, 440)
            path.cubicTo(335, 485, 290, 490, 270, 490)
            path.cubicTo(245, 490, 195, 480, 180, 430)
            path.cubicTo(165, 370, 160, 250, 167, 170)
            path.cubicTo(175, 85, 215, 36, 270, 36)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 36, 270, 490)
            grad.setColorAt(0.0, QtGui.QColor("#272d3b"))
            grad.setColorAt(0.6, QtGui.QColor("#1e222c"))
            grad.setColorAt(1.0, QtGui.QColor("#15171e"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#53627c"), 2.4))
            painter.drawPath(path)

            painter.setPen(QtGui.QPen(QtGui.QColor("#384152"), 2))
            painter.drawLine(270, 38, 270, 160)

            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 1.6))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1b1e27")))
            painter.drawRoundedRect(162, 195, 15, 32, 4, 4)
            painter.drawRoundedRect(159, 260, 15, 34, 4, 4)

            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 2))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#0f1115")))
            painter.drawRoundedRect(257, 56, 26, 76, 7, 7)
            painter.drawRoundedRect(263, 165, 14, 22, 3, 3)

        elif model in ("g903", "g900"):
            path = QtGui.QPainterPath()
            path.moveTo(270, 34)
            path.lineTo(330, 38)
            path.cubicTo(365, 90, 375, 160, 375, 210)
            path.lineTo(360, 260)
            path.lineTo(370, 340)
            path.cubicTo(365, 420, 330, 480, 270, 480)
            path.cubicTo(210, 480, 175, 420, 170, 340)
            path.lineTo(180, 260)
            path.lineTo(165, 210)
            path.cubicTo(165, 160, 175, 90, 210, 38)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 34, 270, 480)
            grad.setColorAt(0.0, QtGui.QColor("#272d3b"))
            grad.setColorAt(0.6, QtGui.QColor("#1e222c"))
            grad.setColorAt(1.0, QtGui.QColor("#15171e"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#53627c"), 2.4))
            painter.drawPath(path)

            painter.setPen(QtGui.QPen(QtGui.QColor("#384152"), 2))
            painter.drawLine(270, 36, 270, 150)

            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 1.6))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1b1e27")))
            painter.drawRoundedRect(162, 192, 12, 26, 3, 3)
            painter.drawRoundedRect(162, 255, 12, 26, 3, 3)
            painter.drawRoundedRect(366, 192, 12, 26, 3, 3)
            painter.drawRoundedRect(366, 255, 12, 26, 3, 3)

            painter.drawRoundedRect(257, 54, 26, 76, 7, 7)
            painter.drawRoundedRect(263, 146, 14, 18, 3, 3)
            painter.drawRoundedRect(263, 186, 14, 18, 3, 3)

        else:
            # G502 & G604 Family (Right Handed with Wing)
            path = QtGui.QPainterPath()
            path.moveTo(270, 36)
            path.cubicTo(340, 36, 390, 85, 396, 160)
            path.cubicTo(402, 230, 390, 350, 375, 410)
            path.cubicTo(350, 470, 300, 485, 270, 485)
            path.cubicTo(240, 485, 195, 470, 180, 420)
            path.cubicTo(168, 390, 126, 350, 120, 280)
            path.cubicTo(115, 220, 160, 180, 172, 130)
            path.cubicTo(178, 75, 218, 36, 270, 36)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 36, 270, 485)
            grad.setColorAt(0.0, QtGui.QColor("#272d3b"))
            grad.setColorAt(0.5, QtGui.QColor("#1e222c"))
            grad.setColorAt(1.0, QtGui.QColor("#15171e"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#53627c"), 2.4))
            painter.drawPath(path)

            painter.setPen(QtGui.QPen(QtGui.QColor("#384152"), 2))
            painter.drawLine(270, 38, 270, 160)

            # Palm rest contour line
            palm = QtGui.QPainterPath()
            palm.moveTo(185, 290)
            palm.cubicTo(225, 260, 315, 260, 360, 290)
            painter.setPen(QtGui.QPen(QtGui.QColor("#333c4c"), 1.8))
            painter.drawPath(palm)

            # Stylized subtle G-Logo on palm
            g_pen = QtGui.QPen(QtGui.QColor("#3a4454"), 2.2)
            painter.setPen(g_pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawArc(QtCore.QRectF(250, 355, 40, 40), 0, 16 * 270)
            painter.drawLine(270, 375, 288, 375)

            # Thumb Switches
            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 1.6))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1b1e27")))
            if model == "g604":
                for y in (165, 210, 255, 300):
                    painter.drawRoundedRect(165, y, 12, 18, 2, 2)
            else:
                # G502 Side switches:
                # B6 Forward (G5) (Upper switch on contour)
                painter.drawRoundedRect(156, 172, 14, 26, 3, 3)
                # B4 Back (G4) (Middle switch)
                painter.drawRoundedRect(153, 237, 14, 26, 3, 3)
                # B5 DPI Shift (G6) (Lower switch)
                painter.drawRoundedRect(149, 302, 14, 26, 3, 3)
                # G7 & G8 Index switches
                painter.drawRoundedRect(172, 58, 13, 22, 3, 3)
                painter.drawRoundedRect(167, 98, 13, 22, 3, 3)

            # Thumb rest rubber grip pattern lines (below side switches)
            painter.setPen(QtGui.QPen(QtGui.QColor("#252b37"), 1.5))
            for gy in range(335, 375, 12):
                painter.drawLine(140, gy, 170, gy + 14)

            # Scroll Wheel Housing
            painter.setPen(QtGui.QPen(QtGui.QColor("#5a6784"), 2))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#0f1115")))
            painter.drawRoundedRect(257, 54, 26, 76, 7, 7)
            painter.setPen(QtGui.QPen(QtGui.QColor("#47536b"), 1.5))
            for y in range(62, 124, 8):
                painter.drawLine(261, y, 279, y)

            # Profile Switch
            painter.setPen(QtGui.QPen(QtGui.QColor("#4b5770"), 1.6))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#181b22")))
            painter.drawRoundedRect(261, 148, 18, 26, 4, 4)

    def _draw_button_hotspots(self, painter: QtGui.QPainter, fm: QtGui.QFontMetrics):
        self._button_rects.clear()
        tx = painter.combinedTransform()

        buttons_dict = self.MODEL_BUTTONS.get(self.model_key, self.MODEL_BUTTONS["g502"])

        for b_num, info in buttons_dict.items():
            cx, cy = info["pos"]
            tx_pt, ty_pt = info["target"]
            tag = self._get_button_tag(b_num, info["tag"])
            text_w = fm.horizontalAdvance(tag)
            box_w = max(info.get("box_w", 80), text_w + 16)
            box_h = 28
            is_selected = (self.selected_button == b_num)
            is_hovered = (self.hovered_button == b_num)

            rect = QtCore.QRectF(cx - box_w / 2.0, cy - box_h / 2.0, box_w, box_h)

            screen_rect = tx.mapRect(rect)
            self._button_rects[b_num] = screen_rect

            if is_selected:
                bg_color = QtGui.QColor("#2563eb")
                border_color = QtGui.QColor("#60a5fa")
                text_color = QtGui.QColor("#ffffff")
                line_color = QtGui.QColor("#60a5fa")
                glow_color = QtGui.QColor(96, 165, 250, 110)
            elif is_hovered:
                bg_color = QtGui.QColor("#374151")
                border_color = QtGui.QColor("#93c5fd")
                text_color = QtGui.QColor("#ffffff")
                line_color = QtGui.QColor("#93c5fd")
                glow_color = QtGui.QColor(147, 197, 253, 50)
            else:
                bg_color = QtGui.QColor("#1e222b")
                border_color = QtGui.QColor("#4b5563")
                text_color = QtGui.QColor("#e2e8f0")
                line_color = QtGui.QColor("#4b5563")
                glow_color = None

            if abs(cx - tx_pt) > 15 or abs(cy - ty_pt) > 15:
                pen_line = QtGui.QPen(
                    line_color,
                    1.8 if (is_selected or is_hovered) else 1.2,
                    QtCore.Qt.PenStyle.SolidLine if is_selected else QtCore.Qt.PenStyle.DashLine,
                )
                painter.setPen(pen_line)
                painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(tx_pt, ty_pt))
                painter.setBrush(QtGui.QBrush(line_color))
                painter.drawEllipse(QtCore.QPointF(tx_pt, ty_pt), 3.0, 3.0)

            if glow_color:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QBrush(glow_color))
                painter.drawRoundedRect(rect.adjusted(-2.5, -2.5, 2.5, 2.5), 6, 6)

            painter.setPen(QtGui.QPen(border_color, 1.6))
            painter.setBrush(QtGui.QBrush(bg_color))
            painter.drawRoundedRect(rect, 5, 5)

            painter.setPen(QtGui.QPen(text_color))
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, tag)

