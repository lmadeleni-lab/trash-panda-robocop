from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from raccoon_guardian.app import create_app
from raccoon_guardian.config import load_config


def test_api_health_and_mock_event(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "api.db"}
    )
    client = TestClient(create_app(config=config))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    response = client.post(
        "/events/mock",
        json={
            "target_detected": True,
            "target_class": "raccoon",
            "confidence": 0.94,
            "zone_id": "gate_entry",
            "direction_of_travel": "inbound",
            "timestamp": "2026-01-15T02:15:00Z",
            "is_human": False,
            "is_pet": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"]["allowed"] is True


def test_api_summary_endpoint(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "summary.db"}
    )
    client = TestClient(create_app(config=config))
    response = client.get("/summary/nightly?date=2026-01-14")
    assert response.status_code == 200
    assert response.json()["date"] == "2026-01-14"
