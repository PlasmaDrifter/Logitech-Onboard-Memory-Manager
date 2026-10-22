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
            1: {"tag": "B1: Left", "pos": (200, 115), "target": (200, 115), "box_w": 68},
            2: {"tag": "B2: Right", "pos": (340, 115), "target": (340, 115), "box_w": 68},
            3: {"tag": "B3: Wheel", "pos": (270, 95), "target": (270, 95), "box_w": 72},
            4: {"tag": "B4: Back", "pos": (70, 310), "target": (175, 290), "box_w": 74},
            5: {"tag": "B5: Sniper", "pos": (70, 245), "target": (155, 235), "box_w": 78},
            6: {"tag": "B6: Fwd", "pos": (70, 185), "target": (175, 195), "box_w": 74},
            7: {"tag": "B7: Tilt ◀", "pos": (195, 45), "target": (250, 85), "box_w": 76},
            8: {"tag": "B8: Tilt ▶", "pos": (345, 45), "target": (290, 85), "box_w": 76},
            9: {"tag": "B9: Profile", "pos": (270, 165), "target": (270, 165), "box_w": 78},
            10: {"tag": "B10: G7", "pos": (70, 50), "target": (190, 68), "box_w": 74},
            11: {"tag": "B11: G8", "pos": (70, 115), "target": (185, 110), "box_w": 74},
        },
        "gpro": {
            1: {"tag": "B1: Left", "pos": (205, 120), "target": (205, 120), "box_w": 72},
            2: {"tag": "B2: Right", "pos": (335, 120), "target": (335, 120), "box_w": 72},
            3: {"tag": "B3: Wheel", "pos": (270, 100), "target": (270, 100), "box_w": 76},
            4: {"tag": "B4: Back", "pos": (95, 255), "target": (176, 255), "box_w": 76},
            5: {"tag": "B5: Fwd", "pos": (95, 195), "target": (178, 195), "box_w": 76},
        },
        "g305": {
            1: {"tag": "B1: Left", "pos": (205, 125), "target": (205, 125), "box_w": 72},
            2: {"tag": "B2: Right", "pos": (335, 125), "target": (335, 125), "box_w": 72},
            3: {"tag": "B3: Wheel", "pos": (270, 95), "target": (270, 95), "box_w": 76},
            4: {"tag": "B4: Back", "pos": (95, 265), "target": (180, 265), "box_w": 76},
            5: {"tag": "B5: Fwd", "pos": (95, 205), "target": (182, 205), "box_w": 76},
            6: {"tag": "B6: DPI", "pos": (270, 175), "target": (270, 175), "box_w": 74},
        },
        "g703": {
            1: {"tag": "B1: Left", "pos": (205, 125), "target": (205, 125), "box_w": 72},
            2: {"tag": "B2: Right", "pos": (340, 125), "target": (340, 125), "box_w": 72},
            3: {"tag": "B3: Wheel", "pos": (270, 95), "target": (270, 95), "box_w": 76},
            4: {"tag": "B4: Back", "pos": (95, 275), "target": (180, 275), "box_w": 76},
            5: {"tag": "B5: Fwd", "pos": (95, 210), "target": (182, 210), "box_w": 76},
            6: {"tag": "B6: DPI", "pos": (270, 175), "target": (270, 175), "box_w": 74},
        },
        "g903": {
            1: {"tag": "B1: Left", "pos": (200, 115), "target": (200, 115), "box_w": 68},
            2: {"tag": "B2: Right", "pos": (340, 115), "target": (340, 115), "box_w": 68},
            3: {"tag": "B3: Wheel", "pos": (270, 90), "target": (270, 90), "box_w": 72},
            4: {"tag": "B4: L-Back", "pos": (85, 270), "target": (182, 270), "box_w": 80},
            5: {"tag": "B5: L-Fwd", "pos": (85, 205), "target": (182, 205), "box_w": 80},
            6: {"tag": "B6: R-Back", "pos": (455, 270), "target": (358, 270), "box_w": 80},
            7: {"tag": "B7: R-Fwd", "pos": (455, 205), "target": (358, 205), "box_w": 80},
            8: {"tag": "B8: Tilt ◀", "pos": (195, 45), "target": (252, 85), "box_w": 76},
            9: {"tag": "B9: Tilt ▶", "pos": (345, 45), "target": (288, 85), "box_w": 76},
            10: {"tag": "B10: DPI-", "pos": (270, 155), "target": (270, 155), "box_w": 76},
            11: {"tag": "B11: DPI+", "pos": (270, 195), "target": (270, 195), "box_w": 76},
        },
        "g604": {
            1: {"tag": "B1: Left", "pos": (205, 115), "target": (205, 115), "box_w": 68},
            2: {"tag": "B2: Right", "pos": (340, 115), "target": (340, 115), "box_w": 68},
            3: {"tag": "B3: Wheel", "pos": (270, 90), "target": (270, 90), "box_w": 72},
            4: {"tag": "B4: G4", "pos": (70, 215), "target": (175, 215), "box_w": 72},
            5: {"tag": "B5: G5", "pos": (70, 260), "target": (170, 260), "box_w": 72},
            6: {"tag": "B6: G6", "pos": (70, 305), "target": (168, 305), "box_w": 72},
            7: {"tag": "B7: G7", "pos": (70, 170), "target": (180, 175), "box_w": 72},
            8: {"tag": "B8: G8", "pos": (148, 160), "target": (185, 200), "box_w": 72},
            9: {"tag": "B9: G9", "pos": (148, 345), "target": (175, 290), "box_w": 72},
            10: {"tag": "B10: Tilt ◀", "pos": (195, 45), "target": (250, 85), "box_w": 76},
            11: {"tag": "B11: Tilt ▶", "pos": (345, 45), "target": (290, 85), "box_w": 76},
            12: {"tag": "B12: DPI-", "pos": (270, 155), "target": (270, 155), "box_w": 74},
            13: {"tag": "B13: DPI+", "pos": (270, 195), "target": (270, 195), "box_w": 74},
            14: {"tag": "B14: Prof", "pos": (270, 235), "target": (270, 235), "box_w": 74},
            15: {"tag": "B15: BT", "pos": (270, 275), "target": (270, 275), "box_w": 74},
        },
    }

    def __init__(self, parent=None, model_key: str = "g502"):
        super().__init__(parent)
        self.setMinimumSize(400, 480)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self.model_key = model_key
        self.selected_button: Optional[int] = None
        self.hovered_button: Optional[int] = None
        self._button_rects: Dict[int, QtCore.QRectF] = {}

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

        # Base reference canvas is 540 x 540
        scale = min(w / 540.0, h / 540.0) * 0.96
        dx = (w - (540.0 * scale)) / 2.0
        dy = (h - (540.0 * scale)) / 2.0

        painter.save()
        painter.translate(dx, dy)
        painter.scale(scale, scale)

        self._draw_mouse_chassis(painter)
        self._draw_button_hotspots(painter)

        painter.restore()

    def _draw_mouse_chassis(self, painter: QtGui.QPainter):
        model = self.model_key

        if model in ("gpro", "g305"):
            # Symmetrical Oval / Egg Contour
            path = QtGui.QPainterPath()
            path.moveTo(270, 36)
            path.cubicTo(320, 36, 360, 85, 365, 170)
            path.cubicTo(370, 260, 360, 380, 345, 430)
            path.cubicTo(330, 480, 290, 490, 270, 490)
            path.cubicTo(250, 490, 210, 480, 195, 430)
            path.cubicTo(180, 380, 170, 260, 175, 170)
            path.cubicTo(180, 85, 220, 36, 270, 36)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 36, 270, 490)
            grad.setColorAt(0.0, QtGui.QColor("#242833"))
            grad.setColorAt(1.0, QtGui.QColor("#181a20"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#4b556b"), 2.2))
            painter.drawPath(path)

            # Center split line
            painter.setPen(QtGui.QPen(QtGui.QColor("#3d4557"), 2))
            painter.drawLine(270, 38, 270, 160)

            # Side Thumb Buttons
            painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 1.5))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1f242e")))
            painter.drawRoundedRect(170, 185, 12, 26, 3, 3)
            painter.drawRoundedRect(168, 245, 12, 28, 3, 3)

            # Scroll Wheel Housing
            painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 2))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#111317")))
            painter.drawRoundedRect(258, 60, 24, 75, 7, 7)
            painter.setPen(QtGui.QPen(QtGui.QColor("#3d4659"), 1.5))
            for y in range(70, 130, 10):
                painter.drawLine(262, y, 278, y)

            if model == "g305":
                # DPI Switch button
                painter.setPen(QtGui.QPen(QtGui.QColor("#475166"), 1.5))
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#1b1e26")))
                painter.drawRoundedRect(264, 165, 12, 22, 3, 3)

        elif model in ("g703", "g403", "g603"):
            # Ergonomic Right-Handed Curve
            path = QtGui.QPainterPath()
            path.moveTo(270, 36)
            path.cubicTo(325, 36, 370, 85, 375, 170)
            path.cubicTo(380, 260, 370, 390, 350, 440)
            path.cubicTo(330, 485, 290, 490, 270, 490)
            path.cubicTo(245, 490, 200, 480, 185, 430)
            path.cubicTo(170, 370, 165, 250, 172, 170)
            path.cubicTo(180, 85, 220, 36, 270, 36)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 36, 270, 490)
            grad.setColorAt(0.0, QtGui.QColor("#242833"))
            grad.setColorAt(1.0, QtGui.QColor("#181a20"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#4b556b"), 2.2))
            painter.drawPath(path)

            painter.setPen(QtGui.QPen(QtGui.QColor("#3d4557"), 2))
            painter.drawLine(270, 38, 270, 160)

            # Prominent Ergonomic Side Buttons
            painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 1.5))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1f242e")))
            painter.drawRoundedRect(168, 195, 14, 30, 4, 4)
            painter.drawRoundedRect(165, 260, 14, 32, 4, 4)

            # Scroll Wheel & DPI
            painter.drawRoundedRect(258, 60, 24, 75, 7, 7)
            painter.drawRoundedRect(264, 165, 12, 22, 3, 3)

        elif model in ("g903", "g900"):
            # Angular Ambidextrous Chassis
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
            grad.setColorAt(0.0, QtGui.QColor("#242833"))
            grad.setColorAt(1.0, QtGui.QColor("#181a20"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#4b556b"), 2.2))
            painter.drawPath(path)

            painter.setPen(QtGui.QPen(QtGui.QColor("#3d4557"), 2))
            painter.drawLine(270, 36, 270, 150)

            # Modular Side Buttons (Left and Right sides)
            painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 1.5))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1f242e")))
            painter.drawRoundedRect(162, 192, 12, 26, 3, 3)
            painter.drawRoundedRect(162, 255, 12, 26, 3, 3)
            painter.drawRoundedRect(366, 192, 12, 26, 3, 3)
            painter.drawRoundedRect(366, 255, 12, 26, 3, 3)

            # Wheel & Dual DPI
            painter.drawRoundedRect(258, 56, 24, 75, 7, 7)
            painter.drawRoundedRect(263, 146, 14, 18, 3, 3)
            painter.drawRoundedRect(263, 186, 14, 18, 3, 3)

        else:
            # G502 & G604 Family (Right Handed with Wing)
            path = QtGui.QPainterPath()
            path.moveTo(270, 36)
            path.cubicTo(330, 36, 375, 85, 380, 160)
            path.cubicTo(385, 230, 375, 350, 360, 410)
            path.cubicTo(340, 470, 295, 485, 270, 485)
            path.cubicTo(245, 485, 205, 470, 190, 420)
            path.cubicTo(180, 390, 145, 350, 140, 280)
            path.cubicTo(135, 220, 175, 180, 185, 130)
            path.cubicTo(190, 75, 225, 36, 270, 36)
            path.closeSubpath()

            grad = QtGui.QLinearGradient(270, 36, 270, 485)
            grad.setColorAt(0.0, QtGui.QColor("#242833"))
            grad.setColorAt(1.0, QtGui.QColor("#181a20"))
            painter.setBrush(QtGui.QBrush(grad))
            painter.setPen(QtGui.QPen(QtGui.QColor("#4b556b"), 2.2))
            painter.drawPath(path)

            painter.setPen(QtGui.QPen(QtGui.QColor("#3d4557"), 2))
            painter.drawLine(270, 38, 270, 160)

            # Thumb Switches
            painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 1.5))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("#1f242e")))
            if model == "g604":
                # 6 button thumb grid
                for y in (165, 210, 255, 300):
                    painter.drawRoundedRect(165, y, 12, 18, 2, 2)
            else:
                # G502 Sniper + Fwd/Back + G7/G8
                painter.drawRoundedRect(150, 226, 15, 22, 4, 4)
                painter.drawRoundedRect(170, 185, 15, 24, 3, 3)
                painter.drawRoundedRect(170, 278, 15, 28, 3, 3)
                painter.drawRoundedRect(185, 58, 12, 22, 3, 3)
                painter.drawRoundedRect(180, 98, 12, 22, 3, 3)

            # Scroll Wheel Housing
            painter.drawRoundedRect(258, 58, 24, 75, 7, 7)
            painter.drawRoundedRect(262, 152, 16, 26, 4, 4)

    def _draw_button_hotspots(self, painter: QtGui.QPainter):
        self._button_rects.clear()
        tx = painter.combinedTransform()

        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        buttons_dict = self.MODEL_BUTTONS.get(self.model_key, self.MODEL_BUTTONS["g502"])

        for b_num, info in buttons_dict.items():
            cx, cy = info["pos"]
            tx_pt, ty_pt = info["target"]
            box_w = info.get("box_w", 74)
            box_h = 25
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
                glow_color = QtGui.QColor(96, 165, 250, 90)
            elif is_hovered:
                bg_color = QtGui.QColor("#374151")
                border_color = QtGui.QColor("#93c5fd")
                text_color = QtGui.QColor("#ffffff")
                line_color = QtGui.QColor("#93c5fd")
                glow_color = QtGui.QColor(147, 197, 253, 40)
            else:
                bg_color = QtGui.QColor("#1e222b")
                border_color = QtGui.QColor("#4b5563")
                text_color = QtGui.QColor("#e2e8f0")
                line_color = QtGui.QColor("#4b5563")
                glow_color = None

            if abs(cx - tx_pt) > 15 or abs(cy - ty_pt) > 15:
                pen_line = QtGui.QPen(
                    line_color,
                    1.75 if (is_selected or is_hovered) else 1.25,
                    QtCore.Qt.PenStyle.SolidLine if is_selected else QtCore.Qt.PenStyle.DashLine,
                )
                painter.setPen(pen_line)
                painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(tx_pt, ty_pt))
                painter.setBrush(QtGui.QBrush(line_color))
                painter.drawEllipse(QtCore.QPointF(tx_pt, ty_pt), 3, 3)

            if glow_color:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QBrush(glow_color))
                painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 6, 6)

            painter.setPen(QtGui.QPen(border_color, 1.75))
            painter.setBrush(QtGui.QBrush(bg_color))
            painter.drawRoundedRect(rect, 5, 5)

            painter.setPen(QtGui.QPen(text_color))
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, info["tag"])
