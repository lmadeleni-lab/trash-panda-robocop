from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.config import load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.control.fleet import FleetCoordinator
from raccoon_guardian.domain.enums import FleetBotMode, MobilityState, TargetClass, ZoneId
from raccoon_guardian.domain.models import DetectionEvent, FleetBotHeartbeat, OutcomeMetrics
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog


def test_fleet_coordinator_builds_local_patrol_from_config(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "fleet.db"}
    )
    repository = EventRepository(config.database_path)
    coordinator = FleetCoordinator(config=config, repository=repository)

    result = coordinator.run_local_patrol(now=datetime(2026, 1, 15, 2, 15, tzinfo=UTC))

    assert result.bot_id == "bot-alpha"
    assert result.path_id == "sim_perimeter"
    assert len(result.commands) == 2
    assert result.commands[0].movement_command["topic"] == "/controller/cmd_vel"


def test_fleet_coordinator_handles_stuck_bot_with_bounded_recovery(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "fleet-recovery.db"}
    )
    repository = EventRepository(config.database_path)
    coordinator = FleetCoordinator(config=config, repository=repository)
    coordinator.record_heartbeat(
        FleetBotHeartbeat(
            bot_id="bot-alpha",
            current_zone=ZoneId.GATE_ENTRY,
            mobility_state=MobilityState.STUCK,
            stuck_score=0.9,
            mode=FleetBotMode.RECOVERY,
        )
    )

    plan = coordinator.recovery_plan_for("bot-alpha")

    assert plan.should_regroup is True
    assert len(plan.actions) == 4
    assert plan.actions[1].command["reason"] == "recovery_reverse"


def test_fleet_coordination_prefers_hot_zone_coverage(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "fleet-pressure.db"}
    )
    repository = EventRepository(config.database_path)
    controller = Controller(
        config=config,
        repository=repository,
        actuator_hub=MockActuatorHub(),
        strategy_catalog=StrategyCatalog(),
    )
    controller.process_detection(
        DetectionEvent(
            target_detected=True,
            target_class=TargetClass.RACCOON,
            confidence=0.95,
            zone_id=ZoneId.GATE_ENTRY,
            timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
            simulated_outcome=OutcomeMetrics(
                retreat_detected=False,
                returned_same_night=True,
                nuisance_score=0.6,
            ),
        )
    )
    coordinator = FleetCoordinator(config=config, repository=repository)

    plan = coordinator.compute_plan(now=datetime(2026, 1, 15, 3, 0, tzinfo=UTC))

    assert plan.area_assignments[0].zone_id == ZoneId.GATE_ENTRY
    assert "no multi-bot convergence" in plan.coordination_notes[0]
