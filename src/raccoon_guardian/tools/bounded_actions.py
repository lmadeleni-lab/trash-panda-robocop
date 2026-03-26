from __future__ import annotations

from datetime import UTC, datetime

from raccoon_guardian.control.controller import Controller
from raccoon_guardian.control.scheduler import RuntimeScheduler
from raccoon_guardian.domain.enums import StrategyName, TargetClass
from raccoon_guardian.domain.models import (
    ActuationResult,
    AgentReport,
    EncounterRecord,
    NightlySummary,
    NotificationResult,
    SchedulerStatus,
    StrategyDefinition,
    SystemStatus,
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
        scheduler: RuntimeScheduler,
    ) -> None:
        self.controller = controller
        self.repository = repository
        self.strategy_catalog = strategy_catalog
        self.evaluator = evaluator
        self.timezone_name = timezone_name
        self.scheduler = scheduler
        self.summary_service = MorningSummaryService(
            repository=repository,
            evaluator=evaluator,
            timezone_name=timezone_name,
            slack_notifier=slack_notifier,
        )
        self.escalation_failure_threshold = escalation_failure_threshold

    def get_recent_outcomes(self, limit: int = 20) -> list[EncounterRecord]:
        return self.repository.recent_outcomes(limit)

    def list_agent_reports(
        self, limit: int = 20, agent_name: str | None = None
    ) -> list[AgentReport]:
        return self.repository.list_agent_reports(limit=limit, agent_name=agent_name)

    def list_strategies(self) -> list[StrategyDefinition]:
        return self.strategy_catalog.list_strategies()

    def set_next_strategy(self, strategy_name: StrategyName) -> StrategyName:
        return self.controller.select_strategy(strategy_name)

    def get_nightly_summary(self, local_date: str) -> NightlySummary:
        return self.summary_service.build_summary(local_date)

    def deliver_morning_summary(self, local_date: str) -> NotificationResult:
        attempted_at = datetime.now(UTC)
        self.scheduler.mark_morning_summary_attempt(attempted_at)
        result = self.summary_service.deliver_summary(local_date)
        if result.delivered:
            self.scheduler.mark_morning_summary_delivered(attempted_at)
        return result

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

    def scheduler_status(self) -> SchedulerStatus:
        return self.scheduler.status(datetime.now(UTC))

    def system_status(self) -> SystemStatus:
        return SystemStatus(
            environment=self.controller.config.environment,
            state=self.controller.state.value,
            armed=self.controller.armed,
            selected_strategy=self.controller.selected_strategy,
            last_action_at=self.controller.last_action_at.isoformat()
            if self.controller.last_action_at
            else None,
            simulation_mode=self.controller.config.simulation_mode,
            detector_backend=self.controller.config.perception.detector_backend,
            api_key_enabled=self.controller.config.security.api_key_enabled,
            slack_enabled=self.controller.config.notifications.slack_enabled,
            morning_summary_enabled=self.controller.config.morning_summary.enabled,
            guard_rounds_enabled=self.controller.config.guard_rounds.enabled,
            background_scheduler_enabled=self.controller.config.runtime.background_scheduler_enabled,
            agents_enabled=self.controller.config.agents.enabled,
            sentry_enabled=self.controller.config.sentry.enabled,
            fleet_enabled=self.controller.config.fleet.enabled,
        )

    def run_guard_round(self) -> list[ActuationResult]:
        attempted_at = datetime.now(UTC)
        self.scheduler.mark_guard_round_attempt(attempted_at)
        results = self.controller.run_guard_round(
            self.controller.config.guard_rounds.presets,
            now=attempted_at,
        )
        self.scheduler.mark_guard_round_run(attempted_at)
        return results
