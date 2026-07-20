from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QSizeF, QMarginsF
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter, QPixmap

from poster_montage_designer.layouts.grid import GridLayout
from poster_montage_designer.models import Project, Title
from poster_montage_designer.services.posters import get_poster


class RenderError(RuntimeError):
    pass


ProgressCallback = Callable[[str, int, int], None]


def render_project_image(
    *,
    project: Project,
    layout: GridLayout,
    visible_imdb_ids: list[str],
    output_path: Path,
    width_px: int = 4961,
    output_format: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    if width_px <= 0:
        raise RenderError("Export width must be greater than zero.")

    output_format = (output_format or output_path.suffix.lstrip(".") or "png").lower()
    if output_format == "jpg":
        output_format = "jpeg"
    if output_format == "tif":
        output_format = "tiff"

    image = _render_to_image(
        project=project,
        layout=layout,
        visible_imdb_ids=visible_imdb_ids,
        width_px=width_px,
        progress_callback=progress_callback,
    )

    if output_format == "pdf":
        _report(progress_callback, "Saving PDF...", 0, 1)
        _save_pdf(image=image, output_path=output_path, project=project)
        _report(progress_callback, "Saving PDF...", 1, 1)
        return

    _report(progress_callback, f"Saving {output_format.upper()} image...", 0, 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not image.save(str(output_path)):
        raise RenderError(f"Could not save export image: {output_path}")

    _report(progress_callback, f"Saving {output_format.upper()} image...", 1, 1)


def _render_to_image(
    *,
    project: Project,
    layout: GridLayout,
    visible_imdb_ids: list[str],
    width_px: int,
    progress_callback: ProgressCallback | None,
) -> QImage:
    title_by_id = {
        title.imdb_title_id: title
        for title in project.titles
        if title.imdb_title_id
    }

    export_items: list[tuple[str, Title, Path]] = []
    total = len(visible_imdb_ids)

    _report(progress_callback, "Preparing original posters...", 0, max(1, total))

    for index, imdb_title_id in enumerate(visible_imdb_ids, start=1):
        title = title_by_id.get(imdb_title_id)
        if title is None:
            _report(progress_callback, f"Preparing original posters {index} / {total}", index, total)
            continue

        _report(
            progress_callback,
            f"Preparing original posters {index} / {total}: {title.title}",
            index - 1,
            total,
        )

        poster_path = _poster_path_for_export(title)
        if poster_path is not None:
            export_items.append((imdb_title_id, title, poster_path))

        _report(
            progress_callback,
            f"Preparing original posters {index} / {total}: {title.title}",
            index,
            total,
        )

    height_px = round(width_px * project.page_height_mm / project.page_width_mm)
    image = QImage(width_px, height_px, QImage.Format.Format_RGB32)
    image.fill(QColor(project.canvas_color))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale = width_px / project.page_width_mm
    visible_path_by_id = {
        imdb_title_id: poster_path
        for imdb_title_id, _title, poster_path in export_items
    }

    try:
        _report(progress_callback, "Rendering montage...", 0, max(1, len(visible_imdb_ids)))

        for index, (imdb_title_id, cell) in enumerate(
            zip(visible_imdb_ids, layout.cells, strict=False),
            start=1,
        ):
            poster_path = visible_path_by_id.get(imdb_title_id)
            title = title_by_id.get(imdb_title_id)

            label = title.title if title is not None else imdb_title_id
            _report(
                progress_callback,
                f"Rendering montage {index} / {total}: {label}",
                index - 1,
                total,
            )

            if poster_path is None:
                _report(progress_callback, f"Rendering montage {index} / {total}: {label}", index, total)
                continue

            pixmap = QPixmap(str(poster_path))
            if pixmap.isNull():
                _report(progress_callback, f"Rendering montage {index} / {total}: {label}", index, total)
                continue

            target = QRectF(
                cell.x_mm * scale,
                cell.y_mm * scale,
                cell.width_mm * scale,
                cell.height_mm * scale,
            )
            source = _cover_source_rect(pixmap, cell.width_mm / cell.height_mm)
            painter.drawPixmap(target, pixmap, source)

            _report(progress_callback, f"Rendering montage {index} / {total}: {label}", index, total)
    finally:
        painter.end()

    return image


def _save_pdf(*, image: QImage, output_path: Path, project: Project) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(output_path))
    writer.setResolution(300)

    page_size = QPageSize(
        QSizeF(project.page_width_mm, project.page_height_mm),
        QPageSize.Unit.Millimeter,
        "Posterfolio Export",
    )
    writer.setPageSize(page_size)
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    painter = QPainter(writer)
    try:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(QRectF(painter.viewport()), image)
    finally:
        painter.end()


def _report(
    progress_callback: ProgressCallback | None,
    message: str,
    value: int,
    maximum: int,
) -> None:
    if progress_callback is None:
        return

    progress_callback(message, value, max(1, maximum))


def _poster_path_for_export(title: Title) -> Path | None:
    if not title.imdb_title_id:
        return None

    original = get_poster(
        title.imdb_title_id,
        index=title.selected_poster_index,
        size="original",
    )
    if original is not None:
        return original

    return get_poster(
        title.imdb_title_id,
        index=title.selected_poster_index,
        size="w500",
    )


def _cover_source_rect(pixmap: QPixmap, target_aspect: float) -> QRectF:
    pixmap_aspect = pixmap.width() / pixmap.height()

    if pixmap_aspect > target_aspect:
        source_height = pixmap.height()
        source_width = source_height * target_aspect
        source_x = (pixmap.width() - source_width) / 2.0
        source_y = 0.0
    else:
        source_width = pixmap.width()
        source_height = source_width / target_aspect
        source_x = 0.0
        source_y = (pixmap.height() - source_height) / 2.0

    return QRectF(source_x, source_y, source_width, source_height)
