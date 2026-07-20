from __future__ import annotations

import json
from dataclasses import dataclass

from poster_montage_designer.paths import SETTINGS_PATH, ensure_app_dirs


@dataclass
class AppConfig:
    tmdb_read_token: str = ""


def load_config() -> AppConfig:
    ensure_app_dirs()

    if not SETTINGS_PATH.exists():
        save_config(AppConfig())
        return AppConfig()

    with SETTINGS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return AppConfig(
        tmdb_read_token=str(data.get("tmdb_read_token", "")).strip(),
    )


def save_config(config: AppConfig) -> None:
    ensure_app_dirs()

    data = {
        "tmdb_read_token": config.tmdb_read_token,
    }

    with SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)