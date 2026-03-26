from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.agents.service import MissionAgentOrchestrator
from raccoon_guardian.config import load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.control.scheduler import RuntimeScheduler
from raccoon_guardian.domain.enums import DirectionOfTravel, TargetClass, ZoneId
from raccoon_guardian.domain.models import DetectionEvent, OutcomeMetrics
from raccoon_guardian.notifications.slack import SlackNotifier
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator
from raccoon_guardian.tools.bounded_actions import BoundedStrategyTools


def test_mission_agents_generate_persistent_reports(tmp_path: Path) -> None:
    config = load_config(Path("configs/simulation.yaml")).model_copy(
        update={"database_path": tmp_path / "agents.db"}
    )
    repository = EventRepository(config.database_path)
    controller = Controller(
        config=config,
        repository=repository,
        actuator_hub=MockActuatorHub(),
        strategy_catalog=StrategyCatalog(),
    )
    detection = DetectionEvent(
        target_detected=True,
        target_class=TargetClass.RACCOON,
        confidence=0.91,
        zone_id=ZoneId.GATE_ENTRY,
        direction_of_travel=DirectionOfTravel.INBOUND,
        timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
        simulated_outcome=OutcomeMetrics(
            retreat_detected=False,
            returned_same_night=True,
            nuisance_score=1.2,
        ),
    )
    controller.process_detection(detection)
    scheduler = RuntimeScheduler(
        timezone_name=config.safety.timezone,
        morning_summary=config.morning_summary,
        guard_rounds=config.guard_rounds,
        agents=config.agents,
        safety=config.safety,
    )
    tools = BoundedStrategyTools(
        controller=controller,
        repository=repository,
        strategy_catalog=StrategyCatalog(),
        evaluator=StrategyEvaluator(),
        timezone_name=config.safety.timezone,
        slack_notifier=SlackNotifier(webhook_url=None, enabled=False),
        escalation_failure_threshold=config.notifications.escalation_failure_threshold,
        scheduler=scheduler,
    )
    orchestrator = MissionAgentOrchestrator(
        config=config,
        repository=repository,
        tools=tools,
    )

    result = orchestrator.run_cycle(now=datetime(2026, 1, 15, 8, 0, tzinfo=UTC))

    assert len(result.reports) == 3
    assert repository.count_agent_reports() == 3
    assert any(report.agent_name == "mission_improvement" for report in result.reports)
    assert orchestrator.status().total_reports == 3
