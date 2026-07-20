from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Title:
    title: str
    year: int | None = None
    imdb_title_id: str | None = None
    url: str | None = None
    poster_path: Path | None = None
    selected_poster_index: int = 0
    benched: bool = False
    bench_reason: str = ""
    missing_poster: bool = False
    revenue: int | None = None
    popularity: float | None = None


# Backwards compatibility for old IMDb importer/scraper modules.
ImdbTitle = Title


@dataclass
class Project:
    name: str = "Untitled Project"
    path: Path | None = None
    source: str = "None"
    titles: list[Title] = field(default_factory=list)
    dirty: bool = False

    canvas_color: str = "#000000"
    airiness: int = 50
    page_width_mm: float = 27.0 * 25.4
    page_height_mm: float = 40.0 * 25.4
    canvas_preset: str = "One Sheet 27 × 40 in"

    # The layout is independent from the title database.
    # It stores IMDb IDs in the order they appear in grid cells.
    layout_order: list[str] = field(default_factory=list)

    @property
    def title_count(self) -> int:
        return len(self.titles)

    @property
    def active_titles(self) -> list[Title]:
        return [title for title in self.titles if not title.benched]

    @property
    def benched_titles(self) -> list[Title]:
        return [title for title in self.titles if title.benched]

    @property
    def benched_count(self) -> int:
        return len(self.benched_titles)

    @property
    def rejected_count(self) -> int:
        return self.benched_count

    def title_by_imdb_id(self, imdb_title_id: str) -> Title | None:
        for title in self.titles:
            if title.imdb_title_id == imdb_title_id:
                return title
        return None

    def active_imdb_ids(self) -> list[str]:
        return [
            title.imdb_title_id
            for title in self.active_titles
            if title.imdb_title_id and not title.missing_poster
        ]
