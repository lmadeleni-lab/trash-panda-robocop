from __future__ import annotations

from pathlib import Path

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.config import load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.simulation.sample_events import default_night_scenario
from raccoon_guardian.simulation.simulator import NightSimulator
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


def test_full_night_simulation_replays_end_to_end(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "sim.db"}
    )
    evaluator = StrategyEvaluator()
    controller = Controller(
        config=config,
        repository=EventRepository(config.database_path),
        actuator_hub=MockActuatorHub(),
        strategy_catalog=StrategyCatalog(),
    )
    simulator = NightSimulator(controller, evaluator)
    records = simulator.run(default_night_scenario())
    summary = evaluator.summarize("2026-01-14", records)

    assert len(records) == 4
    assert any(record.decision.allowed for record in records)
    assert any(not record.decision.allowed for record in records)
    assert summary.total_events == 4
