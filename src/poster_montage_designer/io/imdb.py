from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from poster_montage_designer.models import Title


TITLE_YEAR_RE = re.compile(r"^(?P<title>.+?)\s*\((?P<year>(?:19|20)\d{2})\)\s*$")


def import_imdb_json(path: str | Path) -> list[Title]:
    json_path = Path(path)

    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("IMDb JSON must contain a list of titles.")

    titles: list[Title] = []
    seen_ids: set[str] = set()

    for raw in data:
        if not isinstance(raw, dict):
            continue

        title = _parse_title(raw)

        if title is None:
            continue

        if title.imdb_title_id and title.imdb_title_id in seen_ids:
            continue

        if title.imdb_title_id:
            seen_ids.add(title.imdb_title_id)

        titles.append(title)

    return titles


def _parse_title(raw: dict[str, Any]) -> Title | None:
    raw_title = str(raw.get("title", "")).strip()
    imdb_title_id = str(raw.get("imdb_title_id", "")).strip() or None
    url = str(raw.get("url", "")).strip() or None

    if not raw_title:
        return None

    title, year_from_title = _split_title_year(raw_title)
    year_from_field = _safe_year(raw.get("year"))

    # IMDb person pages include Charles' birth year, 1972, so do not trust it
    # if the title itself provides a different year.
    year = year_from_title or year_from_field

    if _looks_like_junk_title(title):
        return None

    return Title(
        title=title,
        year=year,
        imdb_title_id=imdb_title_id,
        url=url,
    )


def _split_title_year(raw_title: str) -> tuple[str, int | None]:
    match = TITLE_YEAR_RE.match(raw_title)

    if not match:
        return raw_title.strip(), None

    title = match.group("title").strip()
    year = int(match.group("year"))
    return title, year


def _safe_year(value: Any) -> int | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if not re.fullmatch(r"(?:19|20)\d{2}", text):
        return None

    return int(text)


def _looks_like_junk_title(title: str) -> bool:
    lower = title.lower()

    junk_bits = [
        "<",
        ">",
        "aria-label",
        "width=",
        "srcset",
        "close",
        "more",
    ]

    return any(bit in lower for bit in junk_bits)