from __future__ import annotations

from raccoon_guardian.domain.enums import StrategyName, TargetClass
from raccoon_guardian.domain.models import StrategyDefinition
from raccoon_guardian.strategies.base import StrategyProvider
from raccoon_guardian.strategies.predefined import predefined_strategies


class StrategyCatalog(StrategyProvider):
    def __init__(self) -> None:
        self._strategies = {strategy.name: strategy for strategy in predefined_strategies()}
        self._recommended_by_target = {
            TargetClass.RACCOON: StrategyName.LIGHT_WATER,
            TargetClass.UNKNOWN: StrategyName.LIGHT_ONLY,
        }

    def list_strategies(self) -> list[StrategyDefinition]:
        return list(self._strategies.values())

    def get(self, name: StrategyName) -> StrategyDefinition:
        return self._strategies[name]

    def recommended_strategy_for_target(
        self,
        target_class: TargetClass,
        fallback: StrategyName,
        overrides: dict[TargetClass, StrategyName] | None = None,
    ) -> StrategyName:
        if overrides and target_class in overrides:
            return overrides[target_class]
        return self._recommended_by_target.get(target_class, fallback)

    def recommendation_map(
        self,
        fallback: StrategyName,
        overrides: dict[TargetClass, StrategyName] | None = None,
    ) -> dict[TargetClass, StrategyName]:
        recommendations = dict(self._recommended_by_target)
        if overrides:
            recommendations.update(overrides)
        recommendations.setdefault(TargetClass.UNKNOWN, fallback)
        return recommendations
