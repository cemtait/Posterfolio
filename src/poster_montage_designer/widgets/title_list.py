from __future__ import annotations

from PySide6.QtCore import QByteArray, QEvent, QItemSelectionModel, QMimeData, QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QIcon, QKeyEvent, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QAbstractItemView, QListWidget, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from poster_montage_designer.widgets.poster_visuals import PosterVisualState, paint_poster_outline


TITLE_MIME_TYPE = "application/x-posterfolio-title"
TITLE_LIST_MIME_TYPE = "application/x-posterfolio-title-list"


class BenchPosterDelegate(QStyledItemDelegate):
    """Paint each Bench poster and its selection outline from one shared rect."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # The Bench uses icon-only items. Paint the icon ourselves instead of
        # asking Qt's default delegate to paint it and then trying to infer the
        # decoration geometry afterwards. The poster and outline therefore use
        # exactly the same rectangle and cannot drift relative to one another.
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QIcon) or icon.isNull():
            clean = QStyleOptionViewItem(option)
            clean.state &= ~QStyle.StateFlag.State_Selected
            clean.state &= ~QStyle.StateFlag.State_HasFocus
            clean.state &= ~QStyle.StateFlag.State_MouseOver
            super().paint(painter, clean, index)
            return

        icon_size = option.widget.iconSize()
        width = min(icon_size.width(), option.rect.width())
        height = min(icon_size.height(), option.rect.height())
        left = option.rect.left() + (option.rect.width() - width) / 2
        top = option.rect.top() + (option.rect.height() - height) / 2
        poster_rect = QRectF(left, top, width, height)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        icon.paint(
            painter,
            poster_rect.toAlignedRect(),
            Qt.AlignmentFlag.AlignCenter,
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        painter.restore()

        if selected:
            paint_poster_outline(painter, poster_rect, PosterVisualState.SELECTED)


class DraggableTitleList(QListWidget):
    """Title list that exchanges IMDb IDs with the canvas via Qt drag-and-drop."""

    canvas_titles_dropped = Signal(object)
    canvas_poster_swap_requested = Signal(str, str)
    delete_requested = Signal()

    def __init__(self, source_kind: str, parent=None) -> None:
        super().__init__(parent)
        self.source_kind = source_kind
        self.setDragEnabled(True)
        if source_kind == "bench":
            # QAbstractItemView otherwise remains effectively source-only even
            # when acceptDrops is enabled. Explicit DragDrop mode is required
            # for Canvas drags to be admitted to the Bench viewport.
            self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
            self.setAcceptDrops(True)
            self.viewport().setAcceptDrops(True)
            self.setDropIndicatorShown(True)
        else:
            self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
            self.setAcceptDrops(False)
            self.viewport().setAcceptDrops(False)
            self.setDropIndicatorShown(False)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._held_selected_item = None
        self._held_press_pos = QPoint()
        self._held_drag_started = False
        if source_kind == "bench":
            self.setItemDelegate(BenchPosterDelegate(self))
            self.setMouseTracking(False)
            self.viewport().setMouseTracking(False)
            self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, False)
            self.viewport().installEventFilter(self)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Handle plain left-button presses on the Bench ourselves. This keeps
        # single- and multi-poster drag initiation identical and prevents
        # QListWidget from starting its empty-area rubber-band selection.
        if (
            self.source_kind == "bench"
            and event.button() == Qt.MouseButton.LeftButton
            and not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier))
        ):
            item = self.itemAt(event.pos())
            if item is not None:
                if not item.isSelected():
                    self.clearSelection()
                    item.setSelected(True)
                self.setCurrentItem(item, QItemSelectionModel.SelectionFlag.NoUpdate)
                self._held_selected_item = item
                self._held_press_pos = event.pos()
                self._held_drag_started = False
                event.accept()
                return

        self._held_selected_item = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._held_selected_item is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                if (event.pos() - self._held_press_pos).manhattanLength() >= QApplication.startDragDistance():
                    self._held_drag_started = True
                    self.startDrag(Qt.DropAction.MoveAction)
                    self._held_selected_item = None
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._held_selected_item is not None and event.button() == Qt.MouseButton.LeftButton:
            item = self._held_selected_item
            self._held_selected_item = None
            if not self._held_drag_started:
                self.clearSelection()
                item.setSelected(True)
                self.setCurrentItem(item)
            self._held_drag_started = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def startDrag(self, supported_actions) -> None:
        item = self.currentItem()
        if item is None:
            return

        selected = self.selectedItems()
        if item not in selected:
            selected = [item]
        ids = [str(entry.data(Qt.ItemDataRole.UserRole) or "") for entry in selected]
        ids = [item_id for item_id in ids if item_id]
        if not ids:
            return

        mime_data = QMimeData()
        mime_data.setData(TITLE_MIME_TYPE, QByteArray(f"{self.source_kind}|{ids[0]}".encode("utf-8")))
        mime_data.setData(TITLE_LIST_MIME_TYPE, QByteArray(f"{self.source_kind}|{','.join(ids)}".encode("utf-8")))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        front = item.icon().pixmap(self.iconSize())
        drag_pixmap = build_stacked_drag_pixmap(front, self.iconSize(), len(ids))
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(QPoint(drag_pixmap.width() // 2, drag_pixmap.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self.selectedItems():
            self.delete_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        # ResizeMode.Adjust performs the reflow. Avoid delayed layout calls,
        # which can preserve stale icon positions and leave apparent holes.
        super().resizeEvent(event)

    def eventFilter(self, watched, event) -> bool:
        # QAbstractItemView receives drag/drop events on its viewport rather
        # than on the outer QListWidget. Handle Canvas drops at that real drop
        # surface so Qt never rejects a valid multi-poster drag first.
        if self.source_kind == "bench" and watched is self.viewport():
            event_type = event.type()
            if event_type in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                source_kind, imdb_title_ids = decode_title_mime_ids(event.mimeData())
                if source_kind == "canvas" and imdb_title_ids:
                    event.setDropAction(Qt.DropAction.MoveAction)
                    event.accept()
                    return True
            elif event_type == QEvent.Type.Drop:
                source_kind, imdb_title_ids = decode_title_mime_ids(event.mimeData())
                if source_kind == "canvas" and imdb_title_ids:
                    target_item = self.itemAt(event.position().toPoint())
                    target_id = ""
                    if target_item is not None:
                        target_id = str(target_item.data(Qt.ItemDataRole.UserRole) or "")

                    if len(imdb_title_ids) == 1 and target_id:
                        self.canvas_poster_swap_requested.emit(imdb_title_ids[0], target_id)
                    else:
                        self.canvas_titles_dropped.emit(imdb_title_ids)
                    event.setDropAction(Qt.DropAction.MoveAction)
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event) -> None:
        source_kind, imdb_title_ids = decode_title_mime_ids(event.mimeData())
        if self.source_kind == "bench" and source_kind == "canvas" and imdb_title_ids:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        source_kind, imdb_title_ids = decode_title_mime_ids(event.mimeData())
        if self.source_kind == "bench" and source_kind == "canvas" and imdb_title_ids:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()

    def dropEvent(self, event) -> None:
        source_kind, imdb_title_ids = decode_title_mime_ids(event.mimeData())
        if self.source_kind == "bench" and source_kind == "canvas" and imdb_title_ids:
            target_item = self.itemAt(event.position().toPoint())
            target_id = ""
            if target_item is not None:
                target_id = str(target_item.data(Qt.ItemDataRole.UserRole) or "")

            if len(imdb_title_ids) == 1 and target_id:
                self.canvas_poster_swap_requested.emit(imdb_title_ids[0], target_id)
            else:
                self.canvas_titles_dropped.emit(imdb_title_ids)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        event.ignore()


def build_stacked_drag_pixmap(front: QPixmap, poster_size: QSize, count: int) -> QPixmap:
    """Create a poster drag image with stacked cards and a count badge."""
    width = max(1, poster_size.width())
    height = max(1, poster_size.height())
    stack_depth = 2 if count > 1 else 0
    offset = max(4, round(min(width, height) * 0.06))
    badge_diameter = max(24, round(min(width, height) * 0.28)) if count > 1 else 0
    pad = 3

    result = QPixmap(width + stack_depth * offset + pad * 2, height + stack_depth * offset + pad * 2)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    for layer in range(stack_depth, 0, -1):
        rect = QRectF(pad + layer * offset, pad + layer * offset, width, height)
        painter.setPen(QColor(235, 235, 235, 210))
        painter.setBrush(QColor(55, 55, 55, 235))
        painter.drawRoundedRect(rect, 3, 3)

    front_rect = QRectF(pad, pad, width, height)
    painter.setOpacity(0.94)
    if not front.isNull():
        scaled = front.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        source = QRectF(
            max(0, (scaled.width() - width) / 2),
            max(0, (scaled.height() - height) / 2),
            width,
            height,
        )
        painter.drawPixmap(front_rect, scaled, source)
    else:
        painter.fillRect(front_rect, QColor(70, 70, 70))
    painter.setOpacity(1.0)

    if count > 1:
        badge_rect = QRectF(
            result.width() - badge_diameter - 1,
            1,
            badge_diameter,
            badge_diameter,
        )
        painter.setPen(QColor(255, 255, 255))
        painter.setBrush(QColor(30, 30, 30, 245))
        painter.drawEllipse(badge_rect)
        font = QFont(painter.font())
        font.setBold(True)
        font.setPixelSize(max(12, round(badge_diameter * 0.48)))
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(count))

    painter.end()
    return result


def decode_title_mime_ids(mime_data: QMimeData) -> tuple[str, list[str]]:
    if mime_data.hasFormat(TITLE_LIST_MIME_TYPE):
        try:
            text = bytes(mime_data.data(TITLE_LIST_MIME_TYPE)).decode("utf-8")
            source_kind, raw_ids = text.split("|", 1)
            return source_kind, [item for item in raw_ids.split(",") if item]
        except (UnicodeDecodeError, ValueError):
            return "", []
    source_kind, imdb_title_id = decode_title_mime(mime_data)
    return source_kind, [imdb_title_id] if imdb_title_id else []


def decode_title_mime(mime_data: QMimeData) -> tuple[str, str]:
    if not mime_data.hasFormat(TITLE_MIME_TYPE):
        return "", ""
    try:
        text = bytes(mime_data.data(TITLE_MIME_TYPE)).decode("utf-8")
        source_kind, imdb_title_id = text.split("|", 1)
        return source_kind, imdb_title_id
    except (UnicodeDecodeError, ValueError):
        return "", ""
