"""Interactive visual mouse diagram showing G502 physical button layout with callouts."""

from PySide6 import QtCore, QtGui, QtWidgets
from typing import Dict, Optional, Tuple


class MouseCanvas(QtWidgets.QWidget):
    """Custom interactive widget displaying the G502 ergonomic contour and button callout zones."""

    button_clicked = QtCore.Signal(int)
    button_double_clicked = QtCore.Signal(int)

    # 540x560 canvas with mouse chassis centered at X=270
    # Left callouts at X=70, Right callouts at X=470, Center on-mouse badges
    BUTTON_DEFINITIONS = {
        1: {
            "name": "Left Click",
            "tag": "B1: Left",
            "pos": (200, 115),
            "target": (200, 115),
            "anchor": (200, 115),
            "box_w": 68,
        },
        2: {
            "name": "Right Click",
            "tag": "B2: Right",
            "pos": (340, 115),
            "target": (340, 115),
            "anchor": (340, 115),
            "box_w": 68,
        },
        3: {
            "name": "Middle Click",
            "tag": "B3: Wheel",
            "pos": (270, 95),
            "target": (270, 95),
            "anchor": (270, 95),
            "box_w": 72,
        },
        4: {
            "name": "Side Back",
            "tag": "B4: Back",
            "pos": (70, 310),
            "target": (175, 290),
            "anchor": (70, 310),
            "box_w": 74,
        },
        5: {
            "name": "Thumb Sniper",
            "tag": "B5: Sniper",
            "pos": (70, 245),
            "target": (155, 235),
            "anchor": (70, 245),
            "box_w": 78,
        },
        6: {
            "name": "Side Forward",
            "tag": "B6: Fwd",
            "pos": (70, 185),
            "target": (175, 195),
            "anchor": (70, 185),
            "box_w": 74,
        },
        7: {
            "name": "Tilt Left",
            "tag": "B7: Tilt ◀",
            "pos": (195, 45),
            "target": (250, 85),
            "anchor": (195, 45),
            "box_w": 76,
        },
        8: {
            "name": "Tilt Right",
            "tag": "B8: Tilt ▶",
            "pos": (345, 45),
            "target": (290, 85),
            "anchor": (345, 45),
            "box_w": 76,
        },
        9: {
            "name": "Profile Switch",
            "tag": "B9: Profile",
            "pos": (270, 165),
            "target": (270, 165),
            "anchor": (270, 165),
            "box_w": 78,
        },
        10: {
            "name": "G7 (DPI Up)",
            "tag": "B10: G7",
            "pos": (70, 50),
            "target": (190, 68),
            "anchor": (70, 50),
            "box_w": 74,
        },
        11: {
            "name": "G8 (DPI Down)",
            "tag": "B11: G8",
            "pos": (70, 115),
            "target": (185, 110),
            "anchor": (70, 115),
            "box_w": 74,
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 480)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self.selected_button: Optional[int] = None
        self.hovered_button: Optional[int] = None
        self._button_rects: Dict[int, QtCore.QRectF] = {}

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
        # Outer G502 Contour Path centered around X=270
        path = QtGui.QPainterPath()
        path.moveTo(270, 36)
        # Top-right primary click slope
        path.cubicTo(330, 36, 375, 85, 380, 160)
        # Right grip edge
        path.cubicTo(385, 230, 375, 350, 360, 410)
        # Bottom palm curve
        path.cubicTo(340, 470, 295, 485, 270, 485)
        path.cubicTo(245, 485, 205, 470, 190, 420)
        # Left flare (Thumb Rest Wing)
        path.cubicTo(180, 390, 145, 350, 140, 280)
        path.cubicTo(135, 220, 175, 180, 185, 130)
        path.cubicTo(190, 75, 225, 36, 270, 36)
        path.closeSubpath()

        # Chassis fill
        grad = QtGui.QLinearGradient(270, 36, 270, 485)
        grad.setColorAt(0.0, QtGui.QColor("#242833"))
        grad.setColorAt(1.0, QtGui.QColor("#181a20"))
        painter.setBrush(QtGui.QBrush(grad))
        painter.setPen(QtGui.QPen(QtGui.QColor("#4b556b"), 2.2))
        painter.drawPath(path)

        # Center split line between primary clicks
        pen_split = QtGui.QPen(QtGui.QColor("#3d4557"), 2)
        painter.setPen(pen_split)
        painter.drawLine(270, 38, 270, 160)

        # Left Click Outline
        path_lclick = QtGui.QPainterPath()
        path_lclick.moveTo(270, 38)
        path_lclick.lineTo(235, 40)
        path_lclick.cubicTo(205, 75, 195, 130, 202, 175)
        path_lclick.lineTo(270, 175)
        painter.strokePath(path_lclick, QtGui.QPen(QtGui.QColor("#3d4659"), 1.5))

        # Right Click Outline
        path_rclick = QtGui.QPainterPath()
        path_rclick.moveTo(270, 38)
        path_rclick.lineTo(305, 40)
        path_rclick.cubicTo(340, 75, 355, 130, 345, 175)
        path_rclick.lineTo(270, 175)
        painter.strokePath(path_rclick, QtGui.QPen(QtGui.QColor("#3d4659"), 1.5))

        # Thumb Wing Contour Accent
        wing_path = QtGui.QPainterPath()
        wing_path.moveTo(180, 240)
        wing_path.cubicTo(150, 270, 150, 330, 185, 370)
        painter.strokePath(wing_path, QtGui.QPen(QtGui.QColor("#333b4d"), 2))

        # Thumb Switches (Physical buttons on shell)
        # Sniper button
        painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 1.5))
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#1f242e")))
        painter.drawRoundedRect(150, 226, 15, 22, 4, 4)

        # Forward & Back buttons
        painter.drawRoundedRect(170, 185, 15, 24, 3, 3)
        painter.drawRoundedRect(170, 278, 15, 28, 3, 3)

        # G7 & G8 Physical Buttons (beside left click)
        painter.drawRoundedRect(185, 58, 12, 22, 3, 3)
        painter.drawRoundedRect(180, 98, 12, 22, 3, 3)

        # Scroll Wheel Housing
        painter.setPen(QtGui.QPen(QtGui.QColor("#54607a"), 2))
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#111317")))
        painter.drawRoundedRect(258, 58, 24, 75, 7, 7)

        # Wheel Ribs
        painter.setPen(QtGui.QPen(QtGui.QColor("#3d4659"), 1.5))
        for y in range(68, 128, 10):
            painter.drawLine(262, y, 278, y)

        # Profile Switch Button Housing
        painter.setPen(QtGui.QPen(QtGui.QColor("#475166"), 1.5))
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#1b1e26")))
        painter.drawRoundedRect(262, 152, 16, 26, 4, 4)

        # Onboard Memory Logo Panel
        painter.setPen(QtGui.QPen(QtGui.QColor("#384052"), 1.5))
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#16181f")))
        painter.drawRoundedRect(240, 310, 60, 42, 6, 6)
        painter.drawText(QtCore.QRect(240, 310, 60, 42), QtCore.Qt.AlignmentFlag.AlignCenter, "ONBOARD\nMEMORY")

    def _draw_button_hotspots(self, painter: QtGui.QPainter):
        self._button_rects.clear()
        tx = painter.combinedTransform()

        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        for b_num, info in self.BUTTON_DEFINITIONS.items():
            cx, cy = info["pos"]
            tx_pt, ty_pt = info["target"]
            box_w = info.get("box_w", 74)
            box_h = 25
            is_selected = (self.selected_button == b_num)
            is_hovered = (self.hovered_button == b_num)

            rect = QtCore.QRectF(cx - box_w / 2.0, cy - box_h / 2.0, box_w, box_h)

            # Store transformed rectangle for click detection
            screen_rect = tx.mapRect(rect)
            self._button_rects[b_num] = screen_rect

            # Colors
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

            # Draw Callout Pointer Line if the badge is offset from target
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

            # Draw Glow Aura
            if glow_color:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QBrush(glow_color))
                painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 6, 6)

            # Draw Hotspot Badge
            painter.setPen(QtGui.QPen(border_color, 1.75))
            painter.setBrush(QtGui.QBrush(bg_color))
            painter.drawRoundedRect(rect, 5, 5)

            # Draw Button Label Text
            painter.setPen(QtGui.QPen(text_color))
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, info["tag"])
