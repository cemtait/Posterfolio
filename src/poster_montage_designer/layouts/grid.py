from __future__ import annotations

from dataclasses import dataclass
from math import log


@dataclass(frozen=True)
class GridCell:
    index: int
    row: int
    column: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float


@dataclass(frozen=True)
class GridLayout:
    rows: int
    columns: int
    used_count: int
    omitted_count: int
    page_width_mm: float
    page_height_mm: float
    margin_mm: float
    gutter_mm: float
    cell_width_mm: float
    cell_height_mm: float
    score: float
    cells: list[GridCell]


def calculate_grid_layout(
    title_count: int,
    page_width_mm: float,
    page_height_mm: float,
    *,
    content_aspect_ratio: float = 27.0 / 40.0,
    max_omissions: int = 3,
    max_rows: int = 20,
    max_columns: int = 20,
    airiness: int = 50,
) -> GridLayout:
    if title_count <= 0:
        raise ValueError("title_count must be greater than zero.")

    if page_width_mm <= 0 or page_height_mm <= 0:
        raise ValueError("Page dimensions must be greater than zero.")

    if content_aspect_ratio <= 0:
        raise ValueError("content_aspect_ratio must be greater than zero.")

    airiness = max(0, min(100, airiness))

    candidates: list[GridLayout] = []

    for rows in range(1, max_rows + 1):
        for columns in range(1, max_columns + 1):
            capacity = rows * columns

            if capacity > title_count:
                continue

            omitted = title_count - capacity

            if omitted > max_omissions:
                continue

            layout = _build_layout(
                rows=rows,
                columns=columns,
                title_count=title_count,
                page_width_mm=page_width_mm,
                page_height_mm=page_height_mm,
                content_aspect_ratio=content_aspect_ratio,
                omitted_count=omitted,
                airiness=airiness,
            )

            candidates.append(layout)

    if not candidates:
        raise ValueError(
            f"No grid found for {title_count} titles with max_omissions={max_omissions}."
        )

    return max(candidates, key=lambda layout: layout.score)


def _build_layout(
    *,
    rows: int,
    columns: int,
    title_count: int,
    page_width_mm: float,
    page_height_mm: float,
    content_aspect_ratio: float,
    omitted_count: int,
    airiness: int,
) -> GridLayout:
    used_count = rows * columns

    # Airiness is intentionally simple and artist-facing:
    #   0   = tight
    #   50  = default
    #   100 = spacious
    air = airiness / 100.0
    margin_ratio = 0.25 + air * 0.70
    gutter_ratio = 0.04 + air * 0.34

    available_width_units = columns + (columns - 1) * gutter_ratio + 2 * margin_ratio
    available_height_units = (
        rows / content_aspect_ratio
        + (rows - 1) * gutter_ratio
        + 2 * margin_ratio
    )

    unit_from_width = page_width_mm / available_width_units
    unit_from_height = page_height_mm / available_height_units

    cell_width = min(unit_from_width, unit_from_height)
    cell_height = cell_width / content_aspect_ratio
    gutter = cell_width * gutter_ratio
    margin = cell_width * margin_ratio

    grid_width = columns * cell_width + (columns - 1) * gutter
    grid_height = rows * cell_height + (rows - 1) * gutter

    start_x = (page_width_mm - grid_width) / 2.0
    start_y = (page_height_mm - grid_height) / 2.0

    cells: list[GridCell] = []

    for index in range(used_count):
        row = index // columns
        column = index % columns

        x = start_x + column * (cell_width + gutter)
        y = start_y + row * (cell_height + gutter)

        cells.append(
            GridCell(
                index=index,
                row=row,
                column=column,
                x_mm=x,
                y_mm=y,
                width_mm=cell_width,
                height_mm=cell_height,
            )
        )

    page_aspect = page_width_mm / page_height_mm
    grid_aspect = grid_width / grid_height

    aspect_error = abs(log(grid_aspect / page_aspect))
    aspect_score = 1.0 / (1.0 + aspect_error * 4.0)

    page_area = page_width_mm * page_height_mm
    used_area = grid_width * grid_height
    area_score = used_area / page_area

    omission_score = 1.0 - (omitted_count / max(title_count, 1))
    shape_score = 1.0 / (1.0 + abs(rows - columns) * 0.08)

    score = (
        aspect_score * 1000.0
        + area_score * 400.0
        + omission_score * 180.0
        + shape_score * 60.0
    )

    return GridLayout(
        rows=rows,
        columns=columns,
        used_count=used_count,
        omitted_count=omitted_count,
        page_width_mm=page_width_mm,
        page_height_mm=page_height_mm,
        margin_mm=margin,
        gutter_mm=gutter,
        cell_width_mm=cell_width,
        cell_height_mm=cell_height,
        score=score,
        cells=cells,
    )
