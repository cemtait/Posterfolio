from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

CACHE_DIR = PROJECT_ROOT / "cache"
METADATA_CACHE_DIR = CACHE_DIR / "metadata"
POSTER_CATALOGUE_CACHE_DIR = CACHE_DIR / "poster_catalogues"

POSTER_CACHE_DIR = CACHE_DIR / "posters"
POSTER_W500_CACHE_DIR = POSTER_CACHE_DIR / "w500"
POSTER_ORIGINAL_CACHE_DIR = POSTER_CACHE_DIR / "original"

PROJECTS_DIR = PROJECT_ROOT / "projects"
EXPORTS_DIR = PROJECT_ROOT / "exports"


def ensure_app_dirs() -> None:
    for path in (
        CONFIG_DIR,
        CACHE_DIR,
        METADATA_CACHE_DIR,
        POSTER_CATALOGUE_CACHE_DIR,
        POSTER_CACHE_DIR,
        POSTER_W500_CACHE_DIR,
        POSTER_ORIGINAL_CACHE_DIR,
        PROJECTS_DIR,
        EXPORTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)