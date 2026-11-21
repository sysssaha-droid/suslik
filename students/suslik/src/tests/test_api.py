"""API tests. Run with: pytest -q (from the src/ directory)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        app_env="test",
        database_path=str(tmp_path / "ecotrack-test.db"),
        seed_demo=False,
        max_readings_per_request=50,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ecotrack-api",
        "version": "1.0.0",
        "environment": "test",
    }


def test_create_and_list_readings(client: TestClient) -> None:
    payload = {
        "device_id": "sensor-42",
        "metric": "temperature",
        "value": 22.75,
    }

    created = client.post("/api/readings", json=payload)
    assert created.status_code == 201

    body = created.json()
    assert body["id"] == 1
    assert body["device_id"] == "sensor-42"
    assert body["unit"] == "°C"
    recorded_at = datetime.fromisoformat(body["recorded_at"])
    assert recorded_at.utcoffset() == timedelta(0)

    listed = client.get("/api/readings")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["value"] == 22.75


def test_readings_can_be_filtered_by_device(client: TestClient) -> None:
    client.post("/api/readings", json={"device_id": "alpha", "metric": "humidity", "value": 40})
    client.post("/api/readings", json={"device_id": "beta", "metric": "co2", "value": 500})

    response = client.get("/api/readings", params={"device_id": "alpha"})

    assert response.status_code == 200
    assert [item["device_id"] for item in response.json()] == ["alpha"]


def test_stats_aggregate_metrics(client: TestClient) -> None:
    client.post("/api/readings", json={"device_id": "alpha", "metric": "temperature", "value": 20})
    client.post("/api/readings", json={"device_id": "beta", "metric": "temperature", "value": 24})

    response = client.get("/api/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["total_readings"] == 2
    assert stats["devices"] == 2
    assert stats["latest_reading_at"] is not None

    temperature = stats["metrics"][0]
    assert temperature == {
        "metric": "temperature",
        "count": 2,
        "average": 22.0,
        "minimum": 20.0,
        "maximum": 24.0,
    }


def test_invalid_payload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/readings",
        json={"device_id": "sensor 1", "metric": "temperature", "value": 20},
    )

    assert response.status_code == 422


def test_unknown_metric_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/readings",
        json={"device_id": "sensor-1", "metric": "pressure", "value": 1013},
    )

    assert response.status_code == 422


def test_dashboard_and_openapi_are_served(client: TestClient) -> None:
    dashboard = client.get("/")
    schema = client.get("/openapi.json")

    assert dashboard.status_code == 200
    assert "EcoTrack" in dashboard.text
    assert schema.status_code == 200
    assert "/api/readings" in schema.json()["paths"]
