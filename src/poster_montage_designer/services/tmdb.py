from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, fields
from typing import Any

from poster_montage_designer.config import load_config
from poster_montage_designer.paths import METADATA_CACHE_DIR, ensure_app_dirs


TMDB_BASE_URL = "https://api.themoviedb.org/3"


@dataclass
class TmdbLookupResult:
    imdb_title_id: str
    media_type: str
    tmdb_id: int
    title: str
    year: int | None
    poster_path: str | None
    overview: str | None
    revenue: int | None = None
    runtime: int | None = None
    popularity: float | None = None


class TmdbError(RuntimeError):
    pass


def lookup_imdb_id(imdb_title_id: str, *, use_cache: bool = True) -> TmdbLookupResult | None:
    ensure_app_dirs()

    if use_cache:
        cached = _read_cached_metadata(imdb_title_id)
        if cached is not None and _cached_metadata_is_current(imdb_title_id):
            return cached

    config = load_config()

    if not config.tmdb_read_token:
        raise TmdbError(
            "TMDb read token is missing. Add it to PosterMontageDesigner/config/settings.json."
        )

    query = urllib.parse.urlencode({"external_source": "imdb_id"})
    url = f"{TMDB_BASE_URL}/find/{imdb_title_id}?{query}"

    data = _get_json(url, config.tmdb_read_token)
    result = _best_result(imdb_title_id, data, config.tmdb_read_token)

    if result is not None:
        _write_cached_metadata(result)

    return result


def _metadata_cache_path(imdb_title_id: str):
    return METADATA_CACHE_DIR / f"{imdb_title_id}.json"


def _read_cached_metadata(imdb_title_id: str) -> TmdbLookupResult | None:
    path = _metadata_cache_path(imdb_title_id)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    valid_keys = {field.name for field in fields(TmdbLookupResult)}
    clean_data = {key: value for key, value in data.items() if key in valid_keys}
    return TmdbLookupResult(**clean_data)


def _cached_metadata_is_current(imdb_title_id: str) -> bool:
    path = _metadata_cache_path(imdb_title_id)
    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False

    # Older cache files did not include revenue/runtime/popularity. Refresh once.
    return "revenue" in data and "popularity" in data


def _write_cached_metadata(result: TmdbLookupResult) -> None:
    path = _metadata_cache_path(result.imdb_title_id)

    with path.open("w", encoding="utf-8") as file:
        json.dump(asdict(result), file, indent=2)


def _get_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "PosterMontageDesigner/0.1",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise TmdbError(f"TMDb HTTP error {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise TmdbError(f"Could not connect to TMDb: {error}") from error


def _best_result(imdb_title_id: str, data: dict[str, Any], token: str) -> TmdbLookupResult | None:
    movie_results = data.get("movie_results") or []
    tv_results = data.get("tv_results") or []

    if movie_results:
        return _result_from_movie(imdb_title_id, movie_results[0], token)

    if tv_results:
        return _result_from_tv(imdb_title_id, tv_results[0], token)

    return None


def _result_from_movie(imdb_title_id: str, item: dict[str, Any], token: str) -> TmdbLookupResult:
    details = _details_json("movie", int(item["id"]), token)
    title = str(details.get("title") or item.get("title") or item.get("original_title") or "").strip()
    year = _year_from_date(details.get("release_date") or item.get("release_date"))

    return TmdbLookupResult(
        imdb_title_id=imdb_title_id,
        media_type="movie",
        tmdb_id=int(item["id"]),
        title=title,
        year=year,
        poster_path=details.get("poster_path") or item.get("poster_path"),
        overview=details.get("overview") or item.get("overview"),
        revenue=_safe_int(details.get("revenue")),
        runtime=_safe_int(details.get("runtime")),
        popularity=_safe_float(details.get("popularity") or item.get("popularity")),
    )


def _result_from_tv(imdb_title_id: str, item: dict[str, Any], token: str) -> TmdbLookupResult:
    details = _details_json("tv", int(item["id"]), token)
    title = str(details.get("name") or item.get("name") or item.get("original_name") or "").strip()
    year = _year_from_date(details.get("first_air_date") or item.get("first_air_date"))

    return TmdbLookupResult(
        imdb_title_id=imdb_title_id,
        media_type="tv",
        tmdb_id=int(item["id"]),
        title=title,
        year=year,
        poster_path=details.get("poster_path") or item.get("poster_path"),
        overview=details.get("overview") or item.get("overview"),
        revenue=None,
        runtime=None,
        popularity=_safe_float(details.get("popularity") or item.get("popularity")),
    )


def _details_json(media_type: str, tmdb_id: int, token: str) -> dict[str, Any]:
    return _get_json(f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}", token)


def _year_from_date(value: Any) -> int | None:
    text = str(value or "").strip()

    if len(text) < 4:
        return None

    year_text = text[:4]

    if not year_text.isdigit():
        return None

    return int(year_text)


def _safe_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
