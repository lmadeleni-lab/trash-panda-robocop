from __future__ import annotations

from raccoon_guardian.domain.enums import StrategyName
from raccoon_guardian.domain.models import StrategyDefinition
from raccoon_guardian.strategies.base import StrategyProvider
from raccoon_guardian.strategies.predefined import predefined_strategies


class StrategyCatalog(StrategyProvider):
    def __init__(self) -> None:
        self._strategies = {strategy.name: strategy for strategy in predefined_strategies()}

    def list_strategies(self) -> list[StrategyDefinition]:
        return list(self._strategies.values())

    def get(self, name: StrategyName) -> StrategyDefinition:
        return self._strategies[name]
