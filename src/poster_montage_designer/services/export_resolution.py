from __future__ import annotations

from math import floor

from poster_montage_designer.layouts.grid import GridLayout
from poster_montage_designer.models import Project
from poster_montage_designer.services.posters import get_poster_candidates


DEFAULT_EXPORT_WIDTH_PX = 4961
MIN_EXPORT_WIDTH_PX = 800
MAX_EXPORT_WIDTH_PX = 30000


def calculate_max_export_width_px(
    *,
    project: Project,
    layout: GridLayout,
    visible_imdb_ids: list[str],
    fallback_width_px: int = DEFAULT_EXPORT_WIDTH_PX,
) -> int:
    """Return the largest canvas width that should not upscale any visible poster.

    The calculation uses TMDb's original poster dimensions from the poster
    catalogue. For each visible poster, it computes how many canvas pixels per
    millimetre can be used before that poster's cover-cropped source pixels
    would need to be enlarged. The most restrictive poster wins.
    """

    if project.page_width_mm <= 0 or project.page_height_mm <= 0:
        return fallback_width_px

    title_by_id = {
        title.imdb_title_id: title
        for title in project.titles
        if title.imdb_title_id
    }

    limits: list[float] = []

    for imdb_title_id, cell in zip(visible_imdb_ids, layout.cells, strict=False):
        title = title_by_id.get(imdb_title_id)
        if title is None or not title.imdb_title_id:
            continue

        candidates = get_poster_candidates(title.imdb_title_id)
        if not candidates:
            continue

        candidate_index = max(0, min(title.selected_poster_index, len(candidates) - 1))
        candidate = candidates[candidate_index]

        if not candidate.width or not candidate.height:
            continue

        target_aspect = cell.width_mm / cell.height_mm
        source_width, source_height = _cover_source_size(
            float(candidate.width),
            float(candidate.height),
            target_aspect,
        )

        if cell.width_mm <= 0 or cell.height_mm <= 0:
            continue

        px_per_mm_by_width = source_width / cell.width_mm
        px_per_mm_by_height = source_height / cell.height_mm
        px_per_mm = min(px_per_mm_by_width, px_per_mm_by_height)
        limits.append(px_per_mm * project.page_width_mm)

    if not limits:
        return fallback_width_px

    result = floor(min(limits))
    return max(MIN_EXPORT_WIDTH_PX, min(MAX_EXPORT_WIDTH_PX, result))


def _cover_source_size(source_width: float, source_height: float, target_aspect: float) -> tuple[float, float]:
    source_aspect = source_width / source_height

    if source_aspect > target_aspect:
        cropped_height = source_height
        cropped_width = cropped_height * target_aspect
    else:
        cropped_width = source_width
        cropped_height = cropped_width / target_aspect

    return cropped_width, cropped_height
