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


def test_catalog_recommends_strategy_for_target() -> None:
    catalog = StrategyCatalog()
    recommendation = catalog.recommended_strategy_for_target(
        TargetClass.RACCOON,
        fallback=StrategyName.LIGHT_ONLY,
        overrides={TargetClass.RACCOON: StrategyName.SOUND_LIGHT_WATER},
    )
    assert recommendation == StrategyName.SOUND_LIGHT_WATER


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


def test_strategy_evaluator_summary_includes_failure_and_target_breakdown() -> None:
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
                retreat_detected=False,
                returned_within_10_min=True,
                nuisance_score=0.8,
            ),
        )
    ]
    summary = evaluator.summarize("2026-01-15", encounters)
    assert summary.failed_deterrence_events == 1
    assert summary.target_breakdown[0].target_class == TargetClass.RACCOON


def test_strategy_evaluator_summary_includes_droppings_map() -> None:
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
            chosen_strategy=StrategyName.LIGHT_WATER,
            decision=SafetyDecision(allowed=True, action_plan=[], trace=[]),
            outcome=OutcomeMetrics(
                retreat_detected=True,
                possible_droppings_detected=True,
                possible_droppings_zone=ZoneId.GATE_ENTRY,
            ),
        )
    ]
    summary = evaluator.summarize("2026-01-15", encounters)
    assert summary.droppings_map[0].zone_id == ZoneId.GATE_ENTRY
    assert summary.droppings_map[0].flagged_events == 1
