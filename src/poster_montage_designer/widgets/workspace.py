from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QDrag, QKeyEvent, QMouseEvent, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView, QApplication, QRubberBand

from poster_montage_designer.layouts.grid import GridLayout
from poster_montage_designer.widgets.poster_visuals import (
    PLACEHOLDER_FILL_COLOR,
    PosterVisualState,
    paint_poster_outline,
)
from poster_montage_designer.widgets.title_list import (
    TITLE_MIME_TYPE,
    TITLE_LIST_MIME_TYPE,
    build_stacked_drag_pixmap,
    decode_title_mime_ids,
)


MM_PER_INCH = 25.4


class PosterPageItem(QGraphicsItem):
    def __init__(self, width_mm: float, height_mm: float) -> None:
        super().__init__()
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.canvas_color = QColor("#000000")

    def set_canvas_color(self, color: QColor | str) -> None:
        self.canvas_color = QColor(color)
        self.update()

    def boundingRect(self) -> QRectF:
        shadow_pad = 32
        return QRectF(-shadow_pad, -shadow_pad, self.width_mm + shadow_pad * 2, self.height_mm + shadow_pad * 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        page = QRectF(0, 0, self.width_mm, self.height_mm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for i in range(18, 0, -1):
            offset = 2.0 + i * 0.65
            alpha = int(20 * (i / 18.0) ** 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(page.translated(offset, offset), 1.0, 1.0)
        painter.setBrush(self.canvas_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(page)


class CroppedPosterItem(QGraphicsItem):
    def __init__(self, imdb_title_id: str, pixmap: QPixmap, target_rect: QRectF) -> None:
        super().__init__()
        self.imdb_title_id = imdb_title_id
        self.pixmap = pixmap
        self.width_mm = target_rect.width()
        self.height_mm = target_rect.height()
        self.selected = False
        self.drop_target = False
        self.drag_placeholder = False
        self.setPos(target_rect.topLeft())
        self.setZValue(10)

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self.pixmap = pixmap
        self.update()

    def set_selected_visual(self, selected: bool) -> None:
        self.selected = selected
        self.update()

    def set_drop_target(self, active: bool) -> None:
        self.drop_target = active
        self.update()

    def set_drag_placeholder(self, active: bool) -> None:
        self.drag_placeholder = active
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width_mm, self.height_mm)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        target = QRectF(0, 0, self.width_mm, self.height_mm)

        if self.drag_placeholder:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(PLACEHOLDER_FILL_COLOR)
            painter.drawRect(target)
            painter.restore()
            return

        if self.pixmap.isNull():
            return
        pixmap_aspect = self.pixmap.width() / self.pixmap.height()
        target_aspect = self.width_mm / self.height_mm
        if pixmap_aspect > target_aspect:
            source_height = self.pixmap.height()
            source_width = source_height * target_aspect
            source_x = (self.pixmap.width() - source_width) / 2.0
            source_y = 0.0
        else:
            source_width = self.pixmap.width()
            source_height = source_width / target_aspect
            source_x = 0.0
            source_y = (self.pixmap.height() - source_height) / 2.0
        source = QRectF(source_x, source_y, source_width, source_height)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(target, self.pixmap, source)
        if self.drop_target:
            paint_poster_outline(painter, target, PosterVisualState.DROP_TARGET)
        elif self.selected:
            paint_poster_outline(painter, target, PosterVisualState.SELECTED)


class WorkspaceView(QGraphicsView):
    poster_selected = Signal(str)
    selection_changed = Signal(object)
    delete_requested = Signal()
    poster_swap_requested = Signal(str, str)
    bench_poster_replace_requested = Signal(str, str)
    bench_posters_promote_requested = Signal(object)
    context_menu_requested = Signal(object, object)
    canvas_drag_released = Signal(object, object)

    MIN_ZOOM = 0.05
    MAX_ZOOM = 20.0
    ZOOM_STEP = 1.15

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._page_width_mm = 27.0 * MM_PER_INCH
        self._page_height_mm = 40.0 * MM_PER_INCH
        self._page_item = PosterPageItem(self._page_width_mm, self._page_height_mm)
        self._poster_items: list[CroppedPosterItem] = []
        self._poster_item_by_imdb_id: dict[str, CroppedPosterItem] = {}
        self._selected_imdb_id: str | None = None
        self._selected_imdb_ids: set[str] = set()
        self._selection_anchor_id: str | None = None
        self._pressed_item: CroppedPosterItem | None = None
        self._defer_single_selection = False
        self._drag_started = False
        self._press_view_pos = QPoint()
        self._drop_target_item: CroppedPosterItem | None = None
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self._rubber_origin = QPoint()
        self._rubber_active = False
        self._rubber_base_selection: set[str] = set()
        self._rubber_modifiers = Qt.KeyboardModifier.NoModifier
        self._zoom = 1.0
        self._is_panning = False
        self._last_pan_pos = QPoint()
        self._scene.setBackgroundBrush(QColor("#202020"))
        self._scene.addItem(self._page_item)
        self.setObjectName("workspaceView")
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setAcceptDrops(True)
        self._rebuild_scene_rect()
        QTimer.singleShot(0, self.fit_page)

    @property
    def zoom(self) -> float:
        return self._zoom

    def set_canvas_color(self, color: QColor | str) -> None:
        self._page_item.set_canvas_color(color)
        self._scene.update(self._page_item.sceneBoundingRect())
        self.viewport().update()

    def set_page_size(self, width_mm: float, height_mm: float) -> None:
        current_color = self._page_item.canvas_color
        self._page_width_mm = width_mm
        self._page_height_mm = height_mm
        self.clear_posters()
        self._scene.removeItem(self._page_item)
        self._page_item = PosterPageItem(width_mm, height_mm)
        self._page_item.set_canvas_color(current_color)
        self._scene.addItem(self._page_item)
        self._rebuild_scene_rect()
        self.fit_page()

    def clear_posters(self) -> None:
        self._clear_drop_target()
        for item in self._poster_items:
            self._scene.removeItem(item)
        self._poster_items.clear()
        self._poster_item_by_imdb_id.clear()
        self._selected_imdb_id = None
        self._selected_imdb_ids.clear()
        self._selection_anchor_id = None
        self._pressed_item = None

    def show_poster_grid(self, poster_entries: list[tuple[str, Path]], layout: GridLayout) -> None:
        selected_ids = set(self._selected_imdb_ids)
        selected_id = self._selected_imdb_id
        self.clear_posters()
        for (imdb_title_id, poster_path), cell in zip(poster_entries[: layout.used_count], layout.cells, strict=False):
            pixmap = QPixmap(str(poster_path))
            if pixmap.isNull():
                continue
            item = CroppedPosterItem(imdb_title_id, pixmap, QRectF(cell.x_mm, cell.y_mm, cell.width_mm, cell.height_mm))
            self._scene.addItem(item)
            self._poster_items.append(item)
            self._poster_item_by_imdb_id[imdb_title_id] = item
        if selected_ids:
            self.set_selected_posters(selected_ids)
        elif selected_id:
            self.select_poster(selected_id)

    def update_poster(self, imdb_title_id: str, poster_path: Path) -> None:
        item = self._poster_item_by_imdb_id.get(imdb_title_id)
        if item is None:
            return
        pixmap = QPixmap(str(poster_path))
        if not pixmap.isNull():
            item.set_pixmap(pixmap)

    def select_poster(self, imdb_title_id: str | None) -> None:
        self.set_selected_posters([imdb_title_id] if imdb_title_id else [])

    def set_selected_posters(self, imdb_title_ids: list[str] | set[str]) -> None:
        valid_ids = {item.imdb_title_id for item in self._poster_items}
        self._selected_imdb_ids = {item_id for item_id in imdb_title_ids if item_id in valid_ids}
        self._selected_imdb_id = next(iter(self._selected_imdb_ids), None)
        for item in self._poster_items:
            item.set_selected_visual(item.imdb_title_id in self._selected_imdb_ids)

    def selected_poster_ids(self) -> list[str]:
        return [item.imdb_title_id for item in self._poster_items if item.imdb_title_id in self._selected_imdb_ids]

    def _apply_click_selection(self, item: CroppedPosterItem, modifiers: Qt.KeyboardModifier) -> None:
        item_id = item.imdb_title_id
        if modifiers & Qt.KeyboardModifier.ShiftModifier and self._selection_anchor_id:
            ordered_ids = [poster.imdb_title_id for poster in self._poster_items]
            try:
                start = ordered_ids.index(self._selection_anchor_id)
                end = ordered_ids.index(item_id)
            except ValueError:
                self._selected_imdb_ids = {item_id}
            else:
                lo, hi = sorted((start, end))
                range_ids = set(ordered_ids[lo:hi + 1])
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    self._selected_imdb_ids.update(range_ids)
                else:
                    self._selected_imdb_ids = range_ids
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            if item_id in self._selected_imdb_ids:
                self._selected_imdb_ids.remove(item_id)
            else:
                self._selected_imdb_ids.add(item_id)
            self._selection_anchor_id = item_id
        else:
            self._selected_imdb_ids = {item_id}
            self._selection_anchor_id = item_id

        self._selected_imdb_id = item_id if item_id in self._selected_imdb_ids else next(iter(self._selected_imdb_ids), None)
        for poster in self._poster_items:
            poster.set_selected_visual(poster.imdb_title_id in self._selected_imdb_ids)
        self.selection_changed.emit(self.selected_poster_ids())

    def fit_page(self) -> None:
        if self.viewport().width() <= 1 or self.viewport().height() <= 1:
            return
        page = QRectF(0, 0, self._page_width_mm, self._page_height_mm)
        padded = page.adjusted(-90, -90, 90, 90)
        self.resetTransform()
        self.fitInView(padded, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.centerOn(page.center())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.angleDelta().y() == 0:
            return
        factor = self.ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / self.ZOOM_STEP
        new_zoom = self._zoom * factor
        if new_zoom < self.MIN_ZOOM:
            factor = self.MIN_ZOOM / self._zoom
            new_zoom = self.MIN_ZOOM
        elif new_zoom > self.MAX_ZOOM:
            factor = self.MAX_ZOOM / self._zoom
            new_zoom = self.MAX_ZOOM
        old_scene_pos = self.mapToScene(event.position().toPoint())
        self.scale(factor, factor)
        self._zoom = new_zoom
        new_scene_pos = self.mapToScene(event.position().toPoint())
        delta = new_scene_pos - old_scene_pos
        self.translate(delta.x(), delta.y())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            item = self._poster_item_at(event.pos())
            if item is not None:
                if item.imdb_title_id not in self._selected_imdb_ids:
                    self.set_selected_posters([item.imdb_title_id])
                    self.selection_changed.emit(self.selected_poster_ids())
                    self.poster_selected.emit(item.imdb_title_id)
                self.context_menu_requested.emit(self.selected_poster_ids(), event.globalPosition().toPoint())
                event.accept()
                return
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._poster_item_at(event.pos())
            if item is not None:
                self._pressed_item = item
                self._press_view_pos = event.pos()
                self._drag_started = False
                self._defer_single_selection = (
                    item.imdb_title_id in self._selected_imdb_ids
                    and len(self._selected_imdb_ids) > 1
                    and not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier))
                )
                if not self._defer_single_selection:
                    self._apply_click_selection(item, event.modifiers())
                    if self._selected_imdb_id:
                        self.poster_selected.emit(self._selected_imdb_id)
                event.accept()
                return

            self._pressed_item = None
            self._rubber_origin = event.pos()
            self._rubber_active = True
            self._rubber_modifiers = event.modifiers()
            self._rubber_base_selection = set(self._selected_imdb_ids)
            if not (event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                self.set_selected_posters([])
                self.selection_changed.emit([])
                self._rubber_base_selection.clear()
            self._rubber_band.setGeometry(QRect(self._rubber_origin, self._rubber_origin))
            self._rubber_band.show()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_panning:
            delta = event.pos() - self._last_pan_pos
            self._last_pan_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        if self._rubber_active:
            rect = QRect(self._rubber_origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)
            hit_ids: set[str] = set()
            for poster in self._poster_items:
                scene_rect = poster.mapRectToScene(poster.boundingRect())
                view_rect = self.mapFromScene(scene_rect).boundingRect()
                if rect.intersects(view_rect):
                    hit_ids.add(poster.imdb_title_id)

            if self._rubber_modifiers & Qt.KeyboardModifier.ControlModifier:
                selected = self._rubber_base_selection.symmetric_difference(hit_ids)
            elif self._rubber_modifiers & Qt.KeyboardModifier.ShiftModifier:
                selected = self._rubber_base_selection.union(hit_ids)
            else:
                selected = hit_ids
            self.set_selected_posters(selected)
            self.selection_changed.emit(self.selected_poster_ids())
            event.accept()
            return
        if self._pressed_item and (event.pos() - self._press_view_pos).manhattanLength() >= QApplication.startDragDistance():
            self._drag_started = True
            self._start_poster_drag(self._pressed_item)
            self._pressed_item = None
            self._defer_single_selection = False
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            pressed_item = self._pressed_item
            self._pressed_item = None
            if self._defer_single_selection and not self._drag_started and pressed_item is not None:
                self._apply_click_selection(pressed_item, Qt.KeyboardModifier.NoModifier)
                self.poster_selected.emit(pressed_item.imdb_title_id)
            self._defer_single_selection = False
            self._drag_started = False
            if self._rubber_active:
                self._rubber_active = False
                self._rubber_band.hide()
                self._rubber_base_selection.clear()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event) -> None:
        source_kind, source_ids = decode_title_mime_ids(event.mimeData())
        if source_kind in {"canvas", "bench"} and source_ids:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        source_kind, source_ids = decode_title_mime_ids(event.mimeData())
        source_id = source_ids[0] if source_ids else ""
        target = self._poster_item_at(event.position().toPoint())
        if source_kind == "bench" and target is None and source_ids:
            self._set_drop_target(None)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        valid = (
            target is not None
            and target.imdb_title_id != source_id
            and source_kind in {"canvas", "bench"}
            and len(source_ids) == 1
        )
        self._set_drop_target(target if valid else None)
        if valid:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        # QGraphicsView can receive a synthetic leave from an internal drag
        # before it has recorded the corresponding enter. Clearing our own
        # highlight is sufficient and avoids Qt's spurious terminal warning.
        self._clear_drop_target()
        event.accept()

    def dropEvent(self, event) -> None:
        source_kind, source_ids = decode_title_mime_ids(event.mimeData())
        source_id = source_ids[0] if source_ids else ""
        target = self._poster_item_at(event.position().toPoint())
        self._clear_drop_target()
        if source_kind == "bench" and target is None and source_ids:
            self.bench_posters_promote_requested.emit(source_ids)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        if target is None or not source_id or target.imdb_title_id == source_id:
            event.ignore()
            return
        if source_kind == "canvas" and len(source_ids) == 1:
            self.poster_swap_requested.emit(source_id, target.imdb_title_id)
        elif source_kind == "bench" and len(source_ids) == 1:
            self.bench_poster_replace_requested.emit(source_id, target.imdb_title_id)
        else:
            event.ignore()
            return
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.fit_page()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_F:
            self.fit_page()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and self._selected_imdb_ids:
            self.delete_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _start_poster_drag(self, item: CroppedPosterItem) -> None:
        from PySide6.QtCore import QByteArray, QMimeData

        mime_data = QMimeData()
        dragged_ids = self.selected_poster_ids() if item.imdb_title_id in self._selected_imdb_ids else [item.imdb_title_id]
        if not dragged_ids:
            dragged_ids = [item.imdb_title_id]
        mime_data.setData(TITLE_MIME_TYPE, QByteArray(f"canvas|{dragged_ids[0]}".encode("utf-8")))
        mime_data.setData(TITLE_LIST_MIME_TYPE, QByteArray(f"canvas|{','.join(dragged_ids)}".encode("utf-8")))
        drag = QDrag(self)
        drag.setMimeData(mime_data)

        scene_rect = item.mapRectToScene(item.boundingRect())
        view_rect = self.mapFromScene(scene_rect).boundingRect()
        poster_size = view_rect.size().expandedTo(QSize(1, 1))
        drag_pixmap = build_stacked_drag_pixmap(item.pixmap, poster_size, len(dragged_ids))
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(QPoint(drag_pixmap.width() // 2, drag_pixmap.height() // 2))
        placeholder_items = [
            self._poster_item_by_imdb_id[item_id]
            for item_id in dragged_ids
            if item_id in self._poster_item_by_imdb_id
        ]
        for placeholder in placeholder_items:
            placeholder.set_drag_placeholder(True)
        # Qt/QAbstractItemView can reject custom drags before the Bench list
        # receives its drop event. Record the final global cursor position so
        # MainWindow can resolve a release over the Bench deterministically.
        # A transparent IgnoreAction cursor also avoids showing a misleading
        # no-entry badge while the pointer is over that valid destination.
        ignore_cursor = QPixmap(1, 1)
        ignore_cursor.fill(Qt.GlobalColor.transparent)
        drag.setDragCursor(ignore_cursor, Qt.DropAction.IgnoreAction)
        try:
            result = drag.exec(Qt.DropAction.MoveAction)
            if result == Qt.DropAction.IgnoreAction:
                self.canvas_drag_released.emit(dragged_ids, QCursor.pos())
        finally:
            for placeholder in placeholder_items:
                placeholder.set_drag_placeholder(False)
            self._clear_drop_target()

    def _set_drop_target(self, item: CroppedPosterItem | None) -> None:
        if item is self._drop_target_item:
            return
        self._clear_drop_target()
        self._drop_target_item = item
        if item is not None:
            item.set_drop_target(True)

    def _clear_drop_target(self) -> None:
        if self._drop_target_item is not None:
            self._drop_target_item.set_drop_target(False)
            self._drop_target_item = None

    def _poster_item_at(self, view_pos: QPoint) -> CroppedPosterItem | None:
        item = self.itemAt(view_pos)
        while item is not None:
            if isinstance(item, CroppedPosterItem):
                return item
            item = item.parentItem()
        return None

    def _rebuild_scene_rect(self) -> None:
        margin = 220
        self._page_item.setPos(0, 0)
        self._scene.setSceneRect(
            QRectF(
                -margin,
                -margin,
                self._page_width_mm + margin * 2,
                self._page_height_mm + margin * 2,
            )
        )
