from __future__ import annotations

from raccoon_guardian.control.controller import Controller
from raccoon_guardian.domain.enums import StrategyName
from raccoon_guardian.domain.models import EncounterRecord, NightlySummary, StrategyDefinition
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


class BoundedStrategyTools:
    def __init__(
        self,
        controller: Controller,
        repository: EventRepository,
        strategy_catalog: StrategyCatalog,
        evaluator: StrategyEvaluator,
        timezone_name: str,
    ) -> None:
        self.controller = controller
        self.repository = repository
        self.strategy_catalog = strategy_catalog
        self.evaluator = evaluator
        self.timezone_name = timezone_name

    def get_recent_outcomes(self, limit: int = 20) -> list[EncounterRecord]:
        return self.repository.recent_outcomes(limit)

    def list_strategies(self) -> list[StrategyDefinition]:
        return self.strategy_catalog.list_strategies()

    def set_next_strategy(self, strategy_name: StrategyName) -> StrategyName:
        return self.controller.select_strategy(strategy_name)

    def get_nightly_summary(self, local_date: str) -> NightlySummary:
        encounters = self.repository.list_encounters_for_local_date(local_date, self.timezone_name)
        return self.evaluator.summarize(local_date, encounters)
