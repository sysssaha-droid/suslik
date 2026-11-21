"""Pydantic models used by the API and the dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Metric = Literal["temperature", "humidity", "co2", "pm25", "voltage"]


class ReadingCreate(BaseModel):
    """Payload accepted by ``POST /api/readings``."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
        examples=["sensor-01"],
    )
    metric: Metric = Field(..., examples=["temperature"])
    value: float = Field(..., allow_inf_nan=False, examples=[21.4])
    unit: str | None = Field(default=None, max_length=16, examples=["°C"])
    recorded_at: datetime | None = Field(
        default=None,
        description="ISO-8601 timestamp. Defaults to the current UTC time.",
    )

    @field_validator("recorded_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        """Store every timestamp as timezone-aware UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Reading(ReadingCreate):
    """A persisted reading returned by the API."""

    id: int
    recorded_at: datetime


class MetricStats(BaseModel):
    """Aggregated values for one metric."""

    metric: str
    count: int
    average: float
    minimum: float
    maximum: float


class Stats(BaseModel):
    """Aggregated overview of all stored readings."""

    total_readings: int
    devices: int
    latest_reading_at: datetime | None
    metrics: list[MetricStats]
