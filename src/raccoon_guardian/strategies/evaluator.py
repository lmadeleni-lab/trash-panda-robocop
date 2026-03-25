from __future__ import annotations

from collections import defaultdict

from raccoon_guardian.domain.enums import ZoneId
from raccoon_guardian.domain.models import (
    DroppingsZoneSummary,
    EncounterRecord,
    NightlySummary,
    OutcomeMetrics,
    StrategyScore,
    TargetBreakdown,
)


class StrategyEvaluator:
    def deterrence_failed(self, encounter: EncounterRecord) -> bool:
        if not encounter.decision.allowed or encounter.outcome is None:
            return False
        return (
            not encounter.outcome.retreat_detected
            or encounter.outcome.returned_within_10_min
            or encounter.outcome.returned_same_night
        )

    def score_outcome(self, outcome: OutcomeMetrics | None) -> float:
        if outcome is None:
            return 0.0
        score = 0.0
        if outcome.retreat_detected:
            score += 4.0
        if outcome.seconds_to_exit_zone is not None:
            score += max(0.0, 3.0 - min(outcome.seconds_to_exit_zone, 180.0) / 60.0)
        if outcome.returned_within_10_min:
            score -= 3.0
        if outcome.returned_same_night:
            score -= 1.5
        if outcome.false_positive:
            score -= 5.0
        score -= outcome.nuisance_score
        return round(score, 2)

    def rank(self, encounters: list[EncounterRecord]) -> list[StrategyScore]:
        aggregates: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "total": 0.0, "retreats": 0.0}
        )
        strategy_lookup = {}
        for encounter in encounters:
            if encounter.chosen_strategy is None or not encounter.decision.allowed:
                continue
            key = encounter.chosen_strategy.value
            strategy_lookup[key] = encounter.chosen_strategy
            aggregates[key]["count"] += 1
            aggregates[key]["total"] += self.score_outcome(encounter.outcome)
            if encounter.outcome and encounter.outcome.retreat_detected:
                aggregates[key]["retreats"] += 1

        rankings = [
            StrategyScore(
                strategy=strategy_lookup[key],
                encounters=int(data["count"]),
                mean_score=round(data["total"] / data["count"], 2),
                retreat_rate=round(data["retreats"] / data["count"], 2),
            )
            for key, data in aggregates.items()
        ]
        return sorted(rankings, key=lambda item: item.mean_score, reverse=True)

    def summarize(self, date: str, encounters: list[EncounterRecord]) -> NightlySummary:
        rankings = self.rank(encounters)
        acted_events = sum(1 for encounter in encounters if encounter.decision.allowed)
        target_rollup: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "acted": 0})
        droppings_rollup: dict[str, int] = defaultdict(int)
        for encounter in encounters:
            key = encounter.detection.target_class.value
            target_rollup[key]["total"] += 1
            if encounter.decision.allowed:
                target_rollup[key]["acted"] += 1
            if encounter.outcome and encounter.outcome.possible_droppings_detected:
                zone = encounter.outcome.possible_droppings_zone or encounter.detection.zone_id
                droppings_rollup[zone.value] += 1
        target_breakdown = [
            TargetBreakdown(
                target_class=encounter.detection.target_class,
                total_events=data["total"],
                acted_events=data["acted"],
            )
            for encounter in encounters
            for key, data in target_rollup.items()
            if key == encounter.detection.target_class.value
        ]
        failed_deterrence_events = sum(
            1 for encounter in encounters if self.deterrence_failed(encounter)
        )
        droppings_map = [
            DroppingsZoneSummary(zone_id=ZoneId(zone_value), flagged_events=count)
            for zone_value, count in droppings_rollup.items()
        ]
        return NightlySummary(
            date=date,
            total_events=len(encounters),
            acted_events=acted_events,
            denied_events=len(encounters) - acted_events,
            failed_deterrence_events=failed_deterrence_events,
            target_breakdown=list({item.target_class: item for item in target_breakdown}.values()),
            droppings_map=list({item.zone_id: item for item in droppings_map}.values()),
            recommended_focus_strategy=rankings[0].strategy if rankings else None,
            rankings=rankings,
        )
