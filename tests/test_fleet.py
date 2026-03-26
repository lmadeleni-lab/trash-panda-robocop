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


def test_fleet_coordination_hands_off_when_primary_bot_is_resource_drained(
    tmp_path: Path,
) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "fleet-handoff.db"}
    )
    repository = EventRepository(config.database_path)
    coordinator = FleetCoordinator(config=config, repository=repository)
    now = datetime(2026, 1, 15, 3, 0, tzinfo=UTC)

    coordinator.record_heartbeat(
        FleetBotHeartbeat(
            bot_id="bot-alpha",
            current_zone=ZoneId.GATE_ENTRY,
            battery_percent=82.0,
            water_percent=8.0,
            mode=FleetBotMode.PATROL,
            reported_at=now,
        )
    )
    coordinator.record_heartbeat(
        FleetBotHeartbeat(
            bot_id="bot-bravo",
            current_zone=ZoneId.BACKYARD_PROTECTED,
            battery_percent=91.0,
            water_percent=77.0,
            mode=FleetBotMode.OBSERVE,
            reported_at=now,
        )
    )

    plan = coordinator.compute_plan(now=now)
    gate_assignment = next(
        assignment
        for assignment in plan.area_assignments
        if assignment.zone_id == ZoneId.GATE_ENTRY
    )

    assert gate_assignment.primary_bot_id == "bot-bravo"
    assert gate_assignment.takeover_from_bot_id == "bot-alpha"
    assert gate_assignment.resource_note is not None
    assert any("water reserve is critical" in note for note in plan.resource_notes)
    assert plan.local_mode == FleetBotMode.REGROUP


def test_fleet_status_surfaces_shared_resource_levels(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "fleet-status.db"}
    )
    repository = EventRepository(config.database_path)
    coordinator = FleetCoordinator(config=config, repository=repository)
    now = datetime(2026, 1, 15, 3, 0, tzinfo=UTC)

    coordinator.record_heartbeat(
        FleetBotHeartbeat(
            bot_id="bot-alpha",
            current_zone=ZoneId.GATE_ENTRY,
            battery_percent=19.0,
            water_percent=55.0,
            mode=FleetBotMode.PATROL,
            reported_at=now,
        )
    )

    status = next(item for item in coordinator.fleet_status(now) if item.bot_id == "bot-alpha")

    assert status.water_percent == 55.0
    assert status.resource_state == "low_battery"
    assert status.can_accept_takeover is False
    assert status.needs_recharge is True
