from __future__ import annotations

import re
from typing import Any

from poster_montage_designer.models import Title


# Keep the browser-side JavaScript deliberately dumb.
# It uses the same approach as Developer > Dump Visible Links, which we know works:
# return every visible link with href/text/ariaLabel. Python then decides which links
# are IMDb title credits.
IMDB_CREDIT_CAPTURE_SCRIPT = r"""
(() => {
  const links = Array.from(document.querySelectorAll('a[href]')).map((a, index) => ({
    index,
    href: a.href || a.getAttribute('href') || '',
    text: (a.innerText || a.textContent || '').replace(/\s+/g, ' ').trim(),
    ariaLabel: a.getAttribute('aria-label') || '',
  }));

  return JSON.stringify(links);
})();
"""


_TITLE_ID_RE = re.compile(r"/title/(tt\d+)")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def titles_from_capture(raw_items: list[dict[str, Any]]) -> list[Title]:
    titles: list[Title] = []
    seen_ids: set[str] = set()

    for item in raw_items:
        href = str(item.get("href") or "").strip()
        match = _TITLE_ID_RE.search(href)
        if match is None:
            continue

        imdb_title_id = match.group(1)
        if imdb_title_id in seen_ids:
            continue

        text = _clean_title(item.get("text"))
        aria = _clean_title(item.get("ariaLabel"))
        title_text = text or aria

        if not _looks_like_credit_title(title_text):
            continue

        seen_ids.add(imdb_title_id)
        titles.append(
            Title(
                title=title_text,
                year=_year_from_text(text) or _year_from_text(aria) or _year_from_text(href),
                imdb_title_id=imdb_title_id,
                url=f"https://www.imdb.com/title/{imdb_title_id}/",
            )
        )

    return titles


def _clean_title(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^\s*\d+\.\s*", "", text)
    text = re.sub(r"\s*\((?:19|20)\d{2}(?:\s*[–-]\s*(?:19|20)?\d{2})?\)\s*$", "", text)
    text = text.strip(" \t\r\n:–-")
    return text


def _looks_like_credit_title(text: str) -> bool:
    if not text or len(text) < 2:
        return False

    lower = text.lower()
    reject_fragments = (
        "episode",
        "see full summary",
        "photo",
        "trailer",
        "watch options",
        "watchlist",
        "imdbpro",
        "learn more",
        "sign in",
        "use app",
    )
    if lower == "title":
        return False
    if any(fragment in lower for fragment in reject_fragments):
        return False
    return True


def _year_from_text(value: Any) -> int | None:
    text = str(value or "")
    match = _YEAR_RE.search(text)
    if match is None:
        return None

    try:
        year = int(match.group(0))
    except ValueError:
        return None

    if 1800 <= year <= 2200:
        return year
    return None
