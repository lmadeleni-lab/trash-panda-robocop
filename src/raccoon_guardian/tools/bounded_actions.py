from __future__ import annotations

from raccoon_guardian.control.controller import Controller
from raccoon_guardian.domain.enums import StrategyName, TargetClass
from raccoon_guardian.domain.models import (
    EncounterRecord,
    NightlySummary,
    NotificationResult,
    StrategyDefinition,
)
from raccoon_guardian.notifications.slack import SlackNotifier
from raccoon_guardian.reporting.morning_summary import MorningSummaryService
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
        slack_notifier: SlackNotifier,
        escalation_failure_threshold: int,
    ) -> None:
        self.controller = controller
        self.repository = repository
        self.strategy_catalog = strategy_catalog
        self.evaluator = evaluator
        self.timezone_name = timezone_name
        self.summary_service = MorningSummaryService(
            repository=repository,
            evaluator=evaluator,
            timezone_name=timezone_name,
            slack_notifier=slack_notifier,
        )
        self.escalation_failure_threshold = escalation_failure_threshold

    def get_recent_outcomes(self, limit: int = 20) -> list[EncounterRecord]:
        return self.repository.recent_outcomes(limit)

    def list_strategies(self) -> list[StrategyDefinition]:
        return self.strategy_catalog.list_strategies()

    def set_next_strategy(self, strategy_name: StrategyName) -> StrategyName:
        return self.controller.select_strategy(strategy_name)

    def get_nightly_summary(self, local_date: str) -> NightlySummary:
        return self.summary_service.build_summary(local_date)

    def deliver_morning_summary(self, local_date: str) -> NotificationResult:
        return self.summary_service.deliver_summary(local_date)

    def maybe_escalate_failed_deterrence(self, limit: int = 20) -> NotificationResult:
        recent = self.repository.recent_outcomes(limit)
        return self.summary_service.escalate_if_needed(recent, self.escalation_failure_threshold)

    def recommended_strategy_for_target(self, target_class: TargetClass) -> StrategyName:
        return self.controller.strategy_for_target(target_class)

    def recommendation_map(self) -> dict[TargetClass, StrategyName]:
        return self.strategy_catalog.recommendation_map(
            fallback=self.controller.selected_strategy,
            overrides=self.controller.config.target_strategy_preferences,
        )
