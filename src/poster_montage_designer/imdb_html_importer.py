from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urljoin

from .models import ImdbTitle

TITLE_ID_RE = re.compile(r'href=["\']([^"\']*/title/(tt\d+)[^"\']*)["\']', re.I)
TAG_RE = re.compile(r"<[^>]+>")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def import_imdb_html(path: str) -> list[ImdbTitle]:
    html_path = Path(path)
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    found: OrderedDict[str, ImdbTitle] = OrderedDict()

    for match in TITLE_ID_RE.finditer(html):
        href = match.group(1)
        imdb_id = match.group(2)

        start = max(0, match.start() - 500)
        end = min(len(html), match.end() + 1000)
        context_html = html[start:end]
        context_text = _clean_text(context_html)

        title = _best_title_from_context(context_text, imdb_id)
        if not title:
            continue

        year_match = YEAR_RE.search(context_text)
        year = year_match.group(0) if year_match else None

        found.setdefault(
            imdb_id,
            ImdbTitle(
                title=title,
                imdb_title_id=imdb_id,
                year=year,
                url=urljoin("https://www.imdb.com", f"/title/{imdb_id}/"),
            ),
        )

    return list(found.values())


def _clean_text(html: str) -> str:
    text = TAG_RE.sub(" ", html)
    text = (
        text.replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&apos;", "'")
        .replace("&nbsp;", " ")
    )
    return " ".join(text.split())


def _best_title_from_context(text: str, imdb_id: str) -> str | None:
    # IMDb saved pages usually include title text close to the /title/tt link.
    # This deliberately starts simple; we will tighten it once we see real output.
    chunks = re.split(r"\s{2,}| \| | - ", text)
    candidates = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if imdb_id in chunk:
            continue
        if len(chunk) > 80:
            continue
        if _looks_like_noise(chunk):
            continue
        candidates.append(chunk)

    if candidates:
        return candidates[0]

    return None


def _looks_like_noise(text: str) -> bool:
    lower = text.lower().strip()
    if len(lower) < 2:
        return True

    noise_bits = [
        "imdb",
        "photos",
        "photo",
        "videos",
        "video",
        "trailer",
        "see all",
        "show all",
        "external sites",
        "official sites",
        "full cast",
        "company credits",
        "technical specs",
    ]

    return any(bit == lower for bit in noise_bits)