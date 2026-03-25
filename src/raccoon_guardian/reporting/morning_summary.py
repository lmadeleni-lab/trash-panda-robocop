from __future__ import annotations

from raccoon_guardian.domain.models import EncounterRecord, NightlySummary, NotificationResult
from raccoon_guardian.notifications.slack import SlackNotifier
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


class MorningSummaryService:
    def __init__(
        self,
        repository: EventRepository,
        evaluator: StrategyEvaluator,
        timezone_name: str,
        slack_notifier: SlackNotifier,
    ) -> None:
        self.repository = repository
        self.evaluator = evaluator
        self.timezone_name = timezone_name
        self.slack_notifier = slack_notifier

    def build_summary(self, local_date: str) -> NightlySummary:
        encounters = self.repository.list_encounters_for_local_date(local_date, self.timezone_name)
        return self.evaluator.summarize(local_date, encounters)

    def deliver_summary(self, local_date: str) -> NotificationResult:
        summary = self.build_summary(local_date)
        lines = [
            f"Morning summary for {summary.date}",
            f"Total events: {summary.total_events}",
            f"Acted events: {summary.acted_events}",
            f"Denied events: {summary.denied_events}",
            f"Failed deterrence events: {summary.failed_deterrence_events}",
        ]
        if summary.recommended_focus_strategy is not None:
            lines.append(f"Recommended focus strategy: {summary.recommended_focus_strategy.value}")
        if summary.target_breakdown:
            breakdown = ", ".join(
                f"{item.target_class.value}:{item.total_events}"
                for item in summary.target_breakdown
            )
            lines.append(f"Targets seen: {breakdown}")
        return self.slack_notifier.send_message("\n".join(lines))

    def escalate_if_needed(
        self,
        recent_encounters: list[EncounterRecord],
        failure_threshold: int,
    ) -> NotificationResult:
        failures = [
            encounter
            for encounter in recent_encounters
            if self.evaluator.deterrence_failed(encounter)
        ]
        if len(failures) < failure_threshold:
            return NotificationResult(
                delivered=False,
                channel="slack",
                detail="failure threshold not reached",
            )
        latest = failures[0]
        text = (
            "Deterrence escalation triggered\n"
            f"Target: {latest.detection.target_class.value}\n"
            f"Recent failures: {len(failures)}\n"
            f"Zone: {latest.detection.zone_id.value}\n"
            "Recommended action: review strategy, geofence, and hardware state."
        )
        return self.slack_notifier.send_message(text)
