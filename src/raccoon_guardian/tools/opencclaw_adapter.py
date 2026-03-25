from __future__ import annotations

from raccoon_guardian.domain.enums import StrategyName
from raccoon_guardian.domain.models import EncounterRecord, NightlySummary, StrategyDefinition
from raccoon_guardian.tools.bounded_actions import BoundedStrategyTools


class OpenCCLawAdapter:
    """Bounded adapter surface for an external OpenClaw-connected strategy client."""

    def __init__(self, tools: BoundedStrategyTools) -> None:
        self.tools = tools

    def get_recent_outcomes(self, limit: int = 20) -> list[EncounterRecord]:
        return self.tools.get_recent_outcomes(limit)

    def list_strategies(self) -> list[StrategyDefinition]:
        return self.tools.list_strategies()

    def set_next_strategy(self, strategy_name: StrategyName) -> StrategyName:
        return self.tools.set_next_strategy(strategy_name)

    def get_nightly_summary(self, local_date: str) -> NightlySummary:
        return self.tools.get_nightly_summary(local_date)
