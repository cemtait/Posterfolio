from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths


# Read-only files bundled with Posterfolio, such as icons and UI assets.
PACKAGE_ROOT = Path(__file__).resolve().parent

if getattr(sys, "frozen", False):
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PACKAGE_ROOT))
else:
    RESOURCE_ROOT = PACKAGE_ROOT


# Writable user data. On Windows this resolves beneath the user's AppData folder.
_app_data_location = QStandardPaths.writableLocation(
    QStandardPaths.StandardLocation.AppLocalDataLocation
)

if _app_data_location:
    APP_DATA_DIR = Path(_app_data_location)
else:
    APP_DATA_DIR = Path.home() / ".posterfolio"


CONFIG_DIR = APP_DATA_DIR / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"

CACHE_DIR = APP_DATA_DIR / "cache"
METADATA_CACHE_DIR = CACHE_DIR / "metadata"
POSTER_CATALOGUE_CACHE_DIR = CACHE_DIR / "poster_catalogues"

POSTER_CACHE_DIR = CACHE_DIR / "posters"
POSTER_W500_CACHE_DIR = POSTER_CACHE_DIR / "w500"
POSTER_ORIGINAL_CACHE_DIR = POSTER_CACHE_DIR / "original"

PROJECTS_DIR = APP_DATA_DIR / "projects"
EXPORTS_DIR = APP_DATA_DIR / "exports"


def ensure_app_dirs() -> None:
    for path in (
        APP_DATA_DIR,
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