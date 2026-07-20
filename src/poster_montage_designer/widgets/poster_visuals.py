from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen


class PosterVisualState(Enum):
    NORMAL = auto()
    SELECTED = auto()
    DROP_TARGET = auto()
    PLACEHOLDER = auto()


SELECTED_OUTLINE_COLOR = QColor("#8dc8ff")
DROP_TARGET_OUTLINE_COLOR = QColor("#ffd36a")
OUTLINE_WIDTH_PX = 2.0
PLACEHOLDER_FILL_COLOR = QColor(72, 72, 72, 150)
PLACEHOLDER_HAS_OUTLINE = False


def _device_pixel_inset(painter: QPainter) -> tuple[float, float]:
    """Return half the cosmetic pen width in the painter's logical units.

    A cosmetic pen is measured in screen pixels. Converting its half-width
    back to logical coordinates lets the complete stroke sit just inside the
    poster edge at every Canvas zoom level and in the fixed-size Bench.
    """
    transform = painter.transform()
    scale_x = abs(transform.m11())
    scale_y = abs(transform.m22())

    if scale_x <= 0.0:
        scale_x = 1.0
    if scale_y <= 0.0:
        scale_y = 1.0

    half_width = OUTLINE_WIDTH_PX / 2.0
    return half_width / scale_x, half_width / scale_y


def outline_rect(painter: QPainter, rect: QRectF) -> QRectF:
    """Return the shared visible outline rectangle for a poster image."""
    inset_x, inset_y = _device_pixel_inset(painter)
    return QRectF(rect).adjusted(inset_x, inset_y, -inset_x, -inset_y)


def paint_poster_outline(
    painter: QPainter,
    rect: QRectF,
    state: PosterVisualState,
) -> None:
    if state == PosterVisualState.SELECTED:
        color = SELECTED_OUTLINE_COLOR
    elif state == PosterVisualState.DROP_TARGET:
        color = DROP_TARGET_OUTLINE_COLOR
    else:
        return

    pen = QPen(color)
    pen.setWidthF(OUTLINE_WIDTH_PX)
    pen.setCosmetic(True)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    pen.setCapStyle(Qt.PenCapStyle.SquareCap)

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(outline_rect(painter, rect))
    painter.restore()
