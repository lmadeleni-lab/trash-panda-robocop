from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from raccoon_guardian.domain.enums import StrategyName, SystemState, TargetClass, ZoneId
from raccoon_guardian.domain.models import (
    DetectionEvent,
    EncounterRecord,
    OutcomeMetrics,
    SafetyDecision,
)
from raccoon_guardian.notifications.slack import SlackNotifier
from raccoon_guardian.reporting.morning_summary import MorningSummaryService
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


def test_morning_summary_service_builds_summary_and_noops_without_slack(tmp_path: Path) -> None:
    repository = EventRepository(tmp_path / "morning.db")
    record = EncounterRecord(
        detection=DetectionEvent(
            target_detected=True,
            target_class=TargetClass.RACCOON,
            confidence=0.91,
            zone_id=ZoneId.GATE_ENTRY,
            timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
        ),
        state_before=SystemState.IDLE,
        state_after=SystemState.COOLDOWN,
        chosen_strategy=StrategyName.LIGHT_WATER,
        decision=SafetyDecision(allowed=True, action_plan=[], trace=[]),
        outcome=OutcomeMetrics(
            retreat_detected=True,
            seconds_to_exit_zone=20.0,
            possible_droppings_detected=True,
            possible_droppings_zone=ZoneId.GATE_ENTRY,
        ),
    )
    repository.record_encounter(record)
    service = MorningSummaryService(
        repository=repository,
        evaluator=StrategyEvaluator(),
        timezone_name="UTC",
        slack_notifier=SlackNotifier(webhook_url=None, enabled=False),
    )

    summary = service.build_summary("2026-01-15")
    result = service.deliver_summary("2026-01-15")

    assert summary.total_events == 1
    assert summary.target_breakdown[0].target_class == TargetClass.RACCOON
    assert summary.droppings_map[0].zone_id == ZoneId.GATE_ENTRY
    assert result.delivered is False


def test_morning_summary_service_escalates_only_after_threshold() -> None:
    service = MorningSummaryService(
        repository=EventRepository(Path("/tmp") / "unused-reporting.db"),
        evaluator=StrategyEvaluator(),
        timezone_name="UTC",
        slack_notifier=SlackNotifier(webhook_url=None, enabled=False),
    )
    encounter = EncounterRecord(
        detection=DetectionEvent(
            target_detected=True,
            target_class=TargetClass.RACCOON,
            confidence=0.9,
            zone_id=ZoneId.GATE_ENTRY,
            timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
        ),
        state_before=SystemState.IDLE,
        state_after=SystemState.COOLDOWN,
        chosen_strategy=StrategyName.LIGHT_WATER,
        decision=SafetyDecision(allowed=True, action_plan=[], trace=[]),
        outcome=OutcomeMetrics(retreat_detected=False, returned_within_10_min=True),
    )
    result = service.escalate_if_needed([encounter], failure_threshold=2)
    assert result.delivered is False
    assert result.detail == "failure threshold not reached"
