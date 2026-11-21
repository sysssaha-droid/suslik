"""SQLite storage for telemetry readings.

The project intentionally keeps persistence lightweight: one SQLite file,
one connection guarded by a lock. This is enough for a single-container
deployment and keeps the Docker image free of external services.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Reading, ReadingCreate

DEFAULT_UNITS: dict[str, str] = {
    "temperature": "°C",
    "humidity": "%",
    "co2": "ppm",
    "pm25": "µg/m³",
    "voltage": "V",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT    NOT NULL,
    metric      TEXT    NOT NULL,
    value       REAL    NOT NULL,
    unit        TEXT,
    recorded_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_readings_recorded_at
    ON readings (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_device_id
    ON readings (device_id);
"""


class ReadingRepository:
    """Thread-safe repository backed by a single SQLite file."""

    def __init__(self, database_path: str) -> None:
        self._path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def add(self, payload: ReadingCreate) -> Reading:
        recorded_at = payload.recorded_at or datetime.now(timezone.utc)
        unit = payload.unit or DEFAULT_UNITS.get(payload.metric)

        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO readings (device_id, metric, value, unit, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.device_id,
                    payload.metric,
                    payload.value,
                    unit,
                    recorded_at.isoformat(),
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM readings WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()

        return self._to_reading(row)

    def list(self, limit: int = 50, device_id: str | None = None) -> list[Reading]:
        query = "SELECT * FROM readings"
        params: list[object] = []

        if device_id:
            query += " WHERE device_id = ?"
            params.append(device_id)

        query += " ORDER BY recorded_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._connection.execute(query, params).fetchall()

        return [self._to_reading(row) for row in rows]

    def devices(self) -> list[str]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT DISTINCT device_id FROM readings ORDER BY device_id"
            ).fetchall()
        return [row["device_id"] for row in rows]

    def stats(self) -> dict[str, object]:
        with self._lock:
            total = self._connection.execute(
                "SELECT COUNT(*) FROM readings"
            ).fetchone()[0]
            devices = self._connection.execute(
                "SELECT COUNT(DISTINCT device_id) FROM readings"
            ).fetchone()[0]
            latest = self._connection.execute(
                "SELECT MAX(recorded_at) FROM readings"
            ).fetchone()[0]
            grouped = self._connection.execute(
                """
                SELECT metric,
                       COUNT(*)    AS count,
                       AVG(value)  AS average,
                       MIN(value)  AS minimum,
                       MAX(value)  AS maximum
                FROM readings
                GROUP BY metric
                ORDER BY metric
                """
            ).fetchall()

        return {
            "total_readings": total,
            "devices": devices,
            "latest_reading_at": latest,
            "metrics": [
                {
                    "metric": row["metric"],
                    "count": row["count"],
                    "average": round(row["average"], 2),
                    "minimum": row["minimum"],
                    "maximum": row["maximum"],
                }
                for row in grouped
            ],
        }

    def count(self) -> int:
        with self._lock:
            return int(
                self._connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
            )

    def seed_demo(self) -> None:
        """Insert a small demo dataset once, so the dashboard is not empty."""
        if self.count() > 0:
            return

        now = datetime.now(timezone.utc)
        samples = [
            ("sensor-01", "temperature", 21.5),
            ("sensor-01", "humidity", 48.0),
            ("sensor-02", "temperature", 23.1),
            ("sensor-02", "co2", 612.0),
            ("sensor-02", "humidity", 51.2),
            ("sensor-03", "pm25", 12.4),
            ("sensor-03", "temperature", 19.8),
            ("sensor-03", "voltage", 3.71),
            ("sensor-01", "co2", 540.0),
            ("sensor-02", "voltage", 3.68),
            ("sensor-03", "humidity", 44.5),
            ("sensor-01", "temperature", 22.0),
        ]

        for index, (device_id, metric, value) in enumerate(samples):
            self.add(
                ReadingCreate(
                    device_id=device_id,
                    metric=metric,  # type: ignore[arg-type]
                    value=value,
                    recorded_at=now - timedelta(minutes=12 * index),
                )
            )

    @staticmethod
    def _to_reading(row: sqlite3.Row) -> Reading:
        return Reading(
            id=row["id"],
            device_id=row["device_id"],
            metric=row["metric"],
            value=row["value"],
            unit=row["unit"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]),
        )
