from __future__ import annotations

import argparse
import json

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.config import load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.simulation.sample_events import default_night_scenario
from raccoon_guardian.simulation.simulator import NightSimulator
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a mock raccoon-guardian night scenario.")
    parser.add_argument(
        "--config",
        default="configs/simulation.yaml",
        help="Path to YAML config to load for simulation.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    repository = EventRepository(config.database_path)
    evaluator = StrategyEvaluator()
    controller = Controller(
        config=config,
        repository=repository,
        actuator_hub=MockActuatorHub(),
        strategy_catalog=StrategyCatalog(),
    )
    simulator = NightSimulator(controller, evaluator)
    records = simulator.run(default_night_scenario())
    summary = evaluator.summarize("2026-01-14", records)
    print(json.dumps(summary.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
