"""Application settings, read once from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime configuration.

    All values have safe defaults so the app can be started with a single
    ``docker run`` command; production values are injected as env vars.
    """

    app_env: str = "development"
    database_path: str = "data/ecotrack.db"
    log_level: str = "info"
    seed_demo: bool = False
    max_readings_per_request: int = 200

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            database_path=os.getenv("DATABASE_PATH", "data/ecotrack.db"),
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            seed_demo=_env_bool("SEED_DEMO", False),
            max_readings_per_request=int(os.getenv("MAX_READINGS_PER_REQUEST", "200")),
        )
