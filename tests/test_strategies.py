from __future__ import annotations

from raccoon_guardian.domain.enums import StrategyName, SystemState, TargetClass, ZoneId
from raccoon_guardian.domain.models import (
    DetectionEvent,
    EncounterRecord,
    OutcomeMetrics,
    SafetyDecision,
)
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


def test_catalog_contains_expected_strategy_names() -> None:
    catalog = StrategyCatalog()
    names = {strategy.name for strategy in catalog.list_strategies()}
    assert StrategyName.LIGHT_ONLY in names
    assert StrategyName.LIGHT_SOUND_WATER_PAN in names


def test_strategy_evaluator_ranks_by_score() -> None:
    evaluator = StrategyEvaluator()
    encounters = [
        EncounterRecord(
            detection=DetectionEvent(
                target_detected=True,
                target_class=TargetClass.RACCOON,
                confidence=0.95,
                zone_id=ZoneId.GATE_ENTRY,
            ),
            state_before=SystemState.IDLE,
            state_after=SystemState.COOLDOWN,
            chosen_strategy=StrategyName.LIGHT_ONLY,
            decision=SafetyDecision(allowed=True, action_plan=[], trace=[]),
            outcome=OutcomeMetrics(
                retreat_detected=True, seconds_to_exit_zone=20.0, nuisance_score=0.1
            ),
        ),
        EncounterRecord(
            detection=DetectionEvent(
                target_detected=True,
                target_class=TargetClass.RACCOON,
                confidence=0.95,
                zone_id=ZoneId.GATE_ENTRY,
            ),
            state_before=SystemState.IDLE,
            state_after=SystemState.COOLDOWN,
            chosen_strategy=StrategyName.WATER_ONLY,
            decision=SafetyDecision(allowed=True, action_plan=[], trace=[]),
            outcome=OutcomeMetrics(
                retreat_detected=False,
                returned_within_10_min=True,
                nuisance_score=1.0,
            ),
        ),
    ]
    rankings = evaluator.rank(encounters)
    assert rankings[0].strategy == StrategyName.LIGHT_ONLY
