from __future__ import annotations

from typing import Protocol

from raccoon_guardian.domain.enums import StrategyName
from raccoon_guardian.domain.models import StrategyDefinition


class StrategyProvider(Protocol):
    def list_strategies(self) -> list[StrategyDefinition]: ...

    def get(self, name: StrategyName) -> StrategyDefinition: ...
