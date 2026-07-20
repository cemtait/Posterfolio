from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import shutil
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from poster_montage_designer.config import load_config
from poster_montage_designer.paths import (
    POSTER_CATALOGUE_CACHE_DIR,
    POSTER_ORIGINAL_CACHE_DIR,
    POSTER_W500_CACHE_DIR,
    ensure_app_dirs,
)
from poster_montage_designer.services.tmdb import lookup_imdb_id


TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

_PREFETCH_LOCK = threading.Lock()
_PREFETCHING: set[tuple[str, int, str]] = set()


VALID_POSTER_SIZES = {
    "w500": POSTER_W500_CACHE_DIR,
    "original": POSTER_ORIGINAL_CACHE_DIR,
}


@dataclass
class PosterCandidate:
    index: int
    poster_path: str
    width: int | None = None
    height: int | None = None
    language: str | None = None
    vote_average: float | None = None
    vote_count: int | None = None


class PosterError(RuntimeError):
    pass


def get_poster_candidate_count(imdb_title_id: str) -> int:
    return len(get_poster_candidates(imdb_title_id))


def get_poster_candidates(imdb_title_id: str, *, use_cache: bool = True) -> list[PosterCandidate]:
    ensure_app_dirs()

    if use_cache:
        cached = _read_cached_catalogue(imdb_title_id)
        if cached is not None:
            return cached

    metadata = lookup_imdb_id(imdb_title_id)

    if metadata is None:
        return []

    url = _images_url(metadata.media_type, metadata.tmdb_id)
    data = _get_json(url)

    posters = data.get("posters") or []
    candidates = _poster_candidates_from_tmdb(posters)

    if not candidates and metadata.poster_path:
        candidates = [
            PosterCandidate(
                index=0,
                poster_path=metadata.poster_path,
            )
        ]

    _write_cached_catalogue(imdb_title_id, candidates)
    return candidates


def get_poster(imdb_title_id: str, *, index: int = 0, size: str = "w500") -> Path | None:
    ensure_app_dirs()

    if size not in VALID_POSTER_SIZES:
        raise PosterError(f"Unsupported poster size: {size}")

    candidates = get_poster_candidates(imdb_title_id)

    if not candidates:
        return None

    index = max(0, min(index, len(candidates) - 1))
    candidate = candidates[index]

    cache_dir = VALID_POSTER_SIZES[size] / imdb_title_id
    poster_path = cache_dir / f"{index}.jpg"

    if poster_path.exists():
        return poster_path

    url = f"{TMDB_IMAGE_BASE_URL}/{size}{candidate.poster_path}"
    _download_file(url, poster_path)

    return poster_path


def _catalogue_cache_path(imdb_title_id: str) -> Path:
    return POSTER_CATALOGUE_CACHE_DIR / f"{imdb_title_id}.json"


def _read_cached_catalogue(imdb_title_id: str) -> list[PosterCandidate] | None:
    path = _catalogue_cache_path(imdb_title_id)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    candidates = [PosterCandidate(**item) for item in data]
    normalized = _filter_and_sort_candidates(candidates)

    if [item.poster_path for item in normalized] != [item.poster_path for item in candidates]:
        _clear_downloaded_variants(imdb_title_id)
        _write_cached_catalogue(imdb_title_id, normalized)

    return normalized


def _write_cached_catalogue(imdb_title_id: str, candidates: list[PosterCandidate]) -> None:
    path = _catalogue_cache_path(imdb_title_id)

    with path.open("w", encoding="utf-8") as file:
        json.dump([asdict(candidate) for candidate in candidates], file, indent=2)


def _poster_candidates_from_tmdb(posters: list[dict[str, Any]]) -> list[PosterCandidate]:
    candidates: list[PosterCandidate] = []

    for item in posters:
        poster_path = str(item.get("file_path") or "").strip()
        if not poster_path:
            continue
        candidates.append(
            PosterCandidate(
                index=len(candidates),
                poster_path=poster_path,
                width=_safe_int(item.get("width")),
                height=_safe_int(item.get("height")),
                language=item.get("iso_639_1"),
                vote_average=_safe_float(item.get("vote_average")),
                vote_count=_safe_int(item.get("vote_count")),
            )
        )

    return _filter_and_sort_candidates(candidates)


def _filter_and_sort_candidates(candidates: list[PosterCandidate]) -> list[PosterCandidate]:
    english = [item for item in candidates if item.language == "en"]
    chosen = english if english else candidates
    chosen = sorted(
        chosen,
        key=lambda item: (
            -(item.vote_count or 0),
            -(item.vote_average or 0.0),
            -(item.width or 0),
            item.poster_path,
        ),
    )
    return [
        PosterCandidate(
            index=index,
            poster_path=item.poster_path,
            width=item.width,
            height=item.height,
            language=item.language,
            vote_average=item.vote_average,
            vote_count=item.vote_count,
        )
        for index, item in enumerate(chosen)
    ]


def _clear_downloaded_variants(imdb_title_id: str) -> None:
    for base_dir in VALID_POSTER_SIZES.values():
        shutil.rmtree(base_dir / imdb_title_id, ignore_errors=True)


def prefetch_poster_neighbors(
    imdb_title_id: str,
    *,
    index: int,
    radius: int = 2,
    size: str = "w500",
) -> None:
    """Quietly cache nearby poster variants without blocking the UI."""
    count = get_poster_candidate_count(imdb_title_id)
    indexes = [candidate_index for candidate_index in range(max(0, index - radius), min(count, index + radius + 1)) if candidate_index != index]

    def worker(candidate_index: int) -> None:
        key = (imdb_title_id, candidate_index, size)
        with _PREFETCH_LOCK:
            if key in _PREFETCHING:
                return
            _PREFETCHING.add(key)
        try:
            get_poster(imdb_title_id, index=candidate_index, size=size)
        except Exception:
            pass
        finally:
            with _PREFETCH_LOCK:
                _PREFETCHING.discard(key)

    for candidate_index in indexes:
        thread = threading.Thread(target=worker, args=(candidate_index,), daemon=True)
        thread.start()


def _images_url(media_type: str, tmdb_id: int) -> str:
    query = urllib.parse.urlencode({"include_image_language": "en,null"})
    return f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}/images?{query}"


def _get_json(url: str) -> dict[str, Any]:
    config = load_config()

    if not config.tmdb_read_token:
        raise PosterError(
            "TMDb read token is missing. Add it to PosterMontageDesigner/config/settings.json."
        )

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {config.tmdb_read_token}",
            "Accept": "application/json",
            "User-Agent": "PosterMontageDesigner/0.1",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise PosterError(f"TMDb HTTP error {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise PosterError(f"Could not connect to TMDb: {error}") from error


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PosterMontageDesigner/0.1"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        raise PosterError(f"Poster HTTP error {error.code}: {url}") from error
    except urllib.error.URLError as error:
        raise PosterError(f"Could not connect to poster server: {error}") from error

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None