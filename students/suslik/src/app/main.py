"""FastAPI application factory and HTTP routes."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings
from .models import MetricStats, Reading, ReadingCreate, Stats
from .storage import ReadingRepository

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application.

    Using a factory keeps tests isolated: each test passes its own
    ``Settings`` with a temporary database file.
    """
    settings = settings or Settings.from_env()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("ecotrack")

    repository = ReadingRepository(settings.database_path)
    if settings.seed_demo:
        repository.seed_demo()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "EcoTrack API v%s started (env=%s, db=%s)",
            __version__,
            settings.app_env,
            settings.database_path,
        )
        yield
        repository.close()

    app = FastAPI(
        title="EcoTrack API",
        description="IoT telemetry collection and lightweight analytics.",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repository

    @app.get("/health", tags=["system"], summary="Liveness and readiness probe")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "ecotrack-api",
            "version": __version__,
            "environment": settings.app_env,
        }

    @app.get("/api/readings", response_model=list[Reading], tags=["readings"])
    def list_readings(
        limit: int = Query(50, ge=1, le=settings.max_readings_per_request),
        device_id: str | None = Query(None, max_length=64),
    ) -> list[Reading]:
        return repository.list(limit=limit, device_id=device_id)

    @app.post(
        "/api/readings",
        response_model=Reading,
        status_code=status.HTTP_201_CREATED,
        tags=["readings"],
    )
    def create_reading(payload: ReadingCreate) -> Reading:
        return repository.add(payload)

    @app.get("/api/stats", response_model=Stats, tags=["readings"])
    def get_stats() -> Stats:
        raw = repository.stats()
        return Stats(
            total_readings=raw["total_readings"],  # type: ignore[arg-type]
            devices=raw["devices"],  # type: ignore[arg-type]
            latest_reading_at=raw["latest_reading_at"],  # type: ignore[arg-type]
            metrics=[MetricStats(**item) for item in raw["metrics"]],  # type: ignore[arg-type]
        )

    @app.get("/api/devices", response_model=list[str], tags=["readings"])
    def list_devices() -> list[str]:
        return repository.devices()

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
