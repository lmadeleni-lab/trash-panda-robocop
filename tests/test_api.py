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
    assert "failed_deterrence_events" in response.json()
    assert "droppings_map" in response.json()
    assert "droppings_heatmap" in response.json()


def test_api_strategy_recommendations_and_delivery_endpoints(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "recommendations.db"}
    )
    client = TestClient(create_app(config=config))

    recommendations = client.get("/strategies/recommendations")
    assert recommendations.status_code == 200
    payload = recommendations.json()
    assert any(item["target_class"] == "raccoon" for item in payload)

    delivery = client.post("/summary/morning/deliver?date=2026-01-14")
    assert delivery.status_code == 200
    assert delivery.json()["delivered"] is False

    escalation = client.post("/alerts/escalate")
    assert escalation.status_code == 200
    assert "detail" in escalation.json()


def test_api_redacts_secrets_and_enforces_api_key(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "secure.db"}
    )
    config.security.api_key_enabled = True
    config.security.api_key = "topsecret"
    config.security.allow_unsafe_local_without_key = False
    client = TestClient(create_app(config=config))

    config_response = client.get("/config")
    assert config_response.status_code == 200
    assert config_response.json()["security"]["api_key"] == "***"

    unauthorized = client.post("/arm")
    assert unauthorized.status_code == 401

    authorized = client.post("/arm", headers={"x-api-key": "topsecret"})
    assert authorized.status_code == 200

    manifest = client.get("/agent/opencclaw/manifest", headers={"x-api-key": "topsecret"})
    assert manifest.status_code == 200
    assert manifest.json()["integration_name"] == "trash-panda-robocop"

    briefing = client.get("/agent/opencclaw/briefing", headers={"x-api-key": "topsecret"})
    assert briefing.status_code == 200
    assert "system_status" in briefing.json()
    assert "nightly_summary" in briefing.json()


def test_api_status_and_scheduler_endpoints(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "status.db"}
    )
    client = TestClient(create_app(config=config))

    readiness = client.get("/health/ready")
    assert readiness.status_code == 200
    assert readiness.json()["status"] in {"ready", "degraded"}

    status = client.get("/status")
    assert status.status_code == 200
    assert "selected_strategy" in status.json()
    assert "background_scheduler_enabled" in status.json()

    scheduler = client.get("/scheduler")
    assert scheduler.status_code == 200
    assert "guard_round_presets" in scheduler.json()
    assert "last_guard_round_attempt_local" in scheduler.json()
    assert "next_agent_cycle_local" in scheduler.json()

    agent_status = client.get("/agents/status")
    assert agent_status.status_code == 200
    assert "available_agents" in agent_status.json()

    reports = client.get("/agents/reports")
    assert reports.status_code == 200
    assert isinstance(reports.json(), list)


def test_api_agent_cycle_execution(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "agents.db"}
    )
    config.security.api_key_enabled = True
    config.security.api_key = "topsecret"
    config.security.allow_unsafe_local_without_key = False
    client = TestClient(create_app(config=config))

    run = client.post("/agents/run", headers={"x-api-key": "topsecret"})
    assert run.status_code == 200
    assert len(run.json()["reports"]) == 3

    reports = client.get("/agents/reports?limit=5")
    assert reports.status_code == 200
    assert len(reports.json()) == 3


def test_api_trusted_network_gate_blocks_untrusted_clients(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "trusted-network.db"}
    )
    config.security.trusted_network_required = True
    config.security.trusted_client_cidrs = ["127.0.0.1/32"]
    config.security.api_key_enabled = True
    config.security.api_key = "topsecret"
    config.security.allow_unsafe_local_without_key = False

    untrusted_client = TestClient(create_app(config=config), client=("198.51.100.20", 50000))
    trusted_client = TestClient(create_app(config=config), client=("127.0.0.1", 50001))

    blocked_status = untrusted_client.get("/status")
    assert blocked_status.status_code == 403

    blocked_control = untrusted_client.post("/arm", headers={"x-api-key": "topsecret"})
    assert blocked_control.status_code == 403

    allowed_status = trusted_client.get("/status")
    assert allowed_status.status_code == 200

    allowed_control = trusted_client.post("/arm", headers={"x-api-key": "topsecret"})
    assert allowed_control.status_code == 200
