from __future__ import annotations

from collections import defaultdict

from raccoon_guardian.domain.models import (
    EncounterRecord,
    NightlySummary,
    OutcomeMetrics,
    StrategyScore,
)


class StrategyEvaluator:
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
        return NightlySummary(
            date=date,
            total_events=len(encounters),
            acted_events=acted_events,
            denied_events=len(encounters) - acted_events,
            rankings=rankings,
        )
