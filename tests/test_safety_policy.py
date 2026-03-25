from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from raccoon_guardian.config import load_config
from raccoon_guardian.domain.enums import ActionType, TargetClass, ZoneId
from raccoon_guardian.domain.models import BoundedAction, DetectionEvent
from raccoon_guardian.safety.policy import SafetyPolicy


def test_policy_denies_human_detection() -> None:
    config = load_config(Path("configs/simulation.yaml"))
    policy = SafetyPolicy(config)
    detection = DetectionEvent(
        target_detected=True,
        target_class=TargetClass.PERSON,
        confidence=0.99,
        zone_id=ZoneId.GATE_ENTRY,
        is_human=True,
        timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
    )
    decision = policy.evaluate(
        detection,
        [BoundedAction(action_type=ActionType.LIGHT)],
        now=detection.timestamp,
        last_action_at=None,
    )
    assert decision.allowed is False
    assert any(entry.rule == "human_exclusion" and not entry.allowed for entry in decision.trace)


def test_policy_clamps_water_duration() -> None:
    config = load_config(Path("configs/simulation.yaml"))
    policy = SafetyPolicy(config)
    detection = DetectionEvent(
        target_detected=True,
        target_class=TargetClass.RACCOON,
        confidence=0.95,
        zone_id=ZoneId.GATE_ENTRY,
        timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
    )
    decision = policy.evaluate(
        detection,
        [BoundedAction(action_type=ActionType.WATER, duration_s=5.0)],
        now=detection.timestamp,
        last_action_at=None,
    )
    assert decision.allowed is True
    assert decision.action_plan[0].duration_s == config.safety.max_water_duration_s
