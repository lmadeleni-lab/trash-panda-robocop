from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.config import load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.domain.enums import TargetClass, ZoneId
from raccoon_guardian.domain.models import DetectionEvent
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog


def test_controller_executes_mock_actions_for_raccoon(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "controller.db"}
    )
    actuator_hub = MockActuatorHub()
    controller = Controller(
        config=config,
        repository=EventRepository(config.database_path),
        actuator_hub=actuator_hub,
        strategy_catalog=StrategyCatalog(),
    )
    detection = DetectionEvent(
        target_detected=True,
        target_class=TargetClass.RACCOON,
        confidence=0.93,
        zone_id=ZoneId.GATE_ENTRY,
        timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
    )
    record = controller.process_detection(detection)
    assert record.decision.allowed is True
    assert len(record.action_results) >= 1
    assert actuator_hub.history


def test_controller_denies_pet_event(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "controller-pet.db"}
    )
    controller = Controller(
        config=config,
        repository=EventRepository(config.database_path),
        actuator_hub=MockActuatorHub(),
        strategy_catalog=StrategyCatalog(),
    )
    detection = DetectionEvent(
        target_detected=True,
        target_class=TargetClass.CAT,
        confidence=0.90,
        zone_id=ZoneId.GATE_ENTRY,
        is_pet=True,
        timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
    )
    record = controller.process_detection(detection)
    assert record.decision.allowed is False
    assert record.action_results == []
