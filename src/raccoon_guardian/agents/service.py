from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from raccoon_guardian.config import AppConfig
from raccoon_guardian.domain.enums import StrategyName, TargetClass
from raccoon_guardian.domain.models import (
    AgentCycleResult,
    AgentFinding,
    AgentProposal,
    AgentReport,
    AgentStatus,
)
from raccoon_guardian.logging import get_logger
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.tools.bounded_actions import BoundedStrategyTools


class NightlyReviewAgent:
    name = "nightly_review"

    def __init__(self, tools: BoundedStrategyTools) -> None:
        self.tools = tools

    def run(self, now: datetime) -> AgentReport:
        summary_date = self.tools.scheduler.morning_summary_target_date(now)
        summary = self.tools.get_nightly_summary(summary_date)
        current_strategy = self.tools.controller.selected_strategy
        findings: list[AgentFinding] = []
        proposals: list[AgentProposal] = []

        if summary.total_events == 0:
            findings.append(
                AgentFinding(
                    category="activity",
                    severity="info",
                    title="No overnight encounters",
                    detail="The system recorded no encounters for the reviewed summary window.",
                )
            )
        if summary.failed_deterrence_events > 0:
            findings.append(
                AgentFinding(
                    category="deterrence",
                    severity="warning",
                    title="Deterrence failures detected",
                    detail=(
                        f"{summary.failed_deterrence_events} acted encounters showed weak retreat "
                        "or repeat entry behavior."
                    ),
                )
            )
        if (
            summary.recommended_focus_strategy
            and summary.recommended_focus_strategy != current_strategy
        ):
            proposals.append(
                AgentProposal(
                    title="Review next strategy selection",
                    priority="medium",
                    rationale=(
                        f"Observed outcomes rank {summary.recommended_focus_strategy.value} above "
                        f"the current selection {current_strategy.value}."
                    ),
                    tags=["strategy", "nightly-review"],
                    implementation_hint=(
                        "Consider switching the next event window to the recommended focus "
                        "strategy if recurrence stays elevated."
                    ),
                )
            )
        for cell in summary.droppings_heatmap:
            if cell.intensity in {"medium", "high"}:
                proposals.append(
                    AgentProposal(
                        title=f"Inspect cleanup hotspot: {cell.zone_id.value}",
                        priority="medium",
                        rationale=(
                            f"{cell.flagged_events} encounters flagged possible droppings in "
                            f"{cell.zone_id.value}."
                        ),
                        tags=["cleanup", "zone", cell.zone_id.value],
                        implementation_hint=(
                            "Review camera framing and perform a physical cleanup check."
                        ),
                    )
                )

        summary_text = (
            f"Reviewed {summary.total_events} encounters for {summary_date}; "
            f"{summary.failed_deterrence_events} deterrence failures; "
            f"current strategy {current_strategy.value}."
        )
        return AgentReport(
            agent_name=self.name,
            summary=summary_text,
            findings=findings,
            proposals=proposals,
            metadata={
                "summary_date": summary_date,
                "current_strategy": current_strategy.value,
                "recommended_focus_strategy": (
                    summary.recommended_focus_strategy.value
                    if summary.recommended_focus_strategy
                    else None
                ),
                "failed_deterrence_events": summary.failed_deterrence_events,
            },
        )


class HealthMonitorAgent:
    name = "health_monitor"

    def __init__(self, config: AppConfig, tools: BoundedStrategyTools) -> None:
        self.config = config
        self.tools = tools

    def run(self, now: datetime) -> AgentReport:
        system_status = self.tools.system_status()
        scheduler_status = self.tools.scheduler_status()
        findings: list[AgentFinding] = []
        proposals: list[AgentProposal] = []

        if self.config.environment != "local" and not system_status.api_key_enabled:
            findings.append(
                AgentFinding(
                    category="security",
                    severity="critical",
                    title="Control API lacks key protection",
                    detail=(
                        "Mutating endpoints should be protected by an API key "
                        "outside local mode."
                    ),
                )
            )
            proposals.append(
                AgentProposal(
                    title="Enable API key protection",
                    priority="high",
                    rationale=(
                        "Production-like deployments should never leave control "
                        "endpoints unauthenticated."
                    ),
                    tags=["security", "deployment"],
                    implementation_hint=(
                        "Set RG_API_KEY and keep security.api_key_enabled=true."
                    ),
                )
            )
        if not system_status.armed:
            findings.append(
                AgentFinding(
                    category="operations",
                    severity="warning",
                    title="System is disarmed",
                    detail=(
                        "The field node is currently disarmed and will not actuate "
                        "during detections."
                    ),
                )
            )
        if (
            scheduler_status.guard_rounds_enabled
            and scheduler_status.last_guard_round_attempt_local is None
        ):
            findings.append(
                AgentFinding(
                    category="scheduler",
                    severity="info",
                    title="Guard rounds have not run yet",
                    detail=(
                        "The scheduler is configured for guard rounds but no run "
                        "attempt has been recorded."
                    ),
                )
            )
        if (
            self.config.notifications.deliver_morning_summary
            and scheduler_status.last_morning_summary_attempt_local is None
        ):
            proposals.append(
                AgentProposal(
                    title="Verify morning summary delivery path",
                    priority="medium",
                    rationale=(
                        "Morning summaries are enabled, but no delivery attempt has "
                        "been logged yet."
                    ),
                    tags=["notifications", "scheduler"],
                    implementation_hint=(
                        "Confirm Slack webhook configuration and allow the next "
                        "morning window to execute."
                    ),
                )
            )

        return AgentReport(
            agent_name=self.name,
            summary=(
                f"Health review completed for environment {system_status.environment}; "
                f"state {system_status.state}; armed={system_status.armed}."
            ),
            findings=findings,
            proposals=proposals,
            metadata={
                "environment": system_status.environment,
                "armed": system_status.armed,
                "state": system_status.state,
            },
        )


class MissionImprovementAgent:
    name = "mission_improvement"

    def __init__(self, config: AppConfig, repository: EventRepository) -> None:
        self.config = config
        self.repository = repository

    def run(self) -> AgentReport:
        recent = self.repository.recent_outcomes(limit=self.config.agents.max_recent_outcomes)
        findings: list[AgentFinding] = []
        proposals: list[AgentProposal] = []

        if not recent:
            return AgentReport(
                agent_name=self.name,
                summary="Not enough outcome history to produce mission-improvement proposals yet.",
                findings=[
                    AgentFinding(
                        category="data",
                        severity="info",
                        title="Insufficient history",
                        detail=(
                            "Mission improvement proposals will become more useful "
                            "after more nights are logged."
                        ),
                    )
                ],
                proposals=[],
                metadata={"recent_outcome_count": 0},
            )

        unknown_count = sum(
            1 for encounter in recent if encounter.detection.target_class == TargetClass.UNKNOWN
        )
        nuisance_avg = sum(
            encounter.outcome.nuisance_score
            for encounter in recent
            if encounter.outcome is not None
        ) / len(recent)
        zone_returns = Counter(
            encounter.detection.zone_id.value
            for encounter in recent
            if encounter.outcome and encounter.outcome.returned_same_night
        )
        hazard_count = sum(
            1 for encounter in recent if encounter.detection.target_class == TargetClass.BEAR
        )

        if unknown_count / len(recent) >= 0.25:
            proposals.append(
                AgentProposal(
                    title="Skill candidate: improve night target classification",
                    priority="high",
                    rationale=(
                        f"{unknown_count} of the last {len(recent)} outcome-bearing encounters "
                        "were classified as unknown."
                    ),
                    tags=["skill", "perception", "night-vision"],
                    implementation_hint=(
                        "Collect more nighttime samples and tune the detector "
                        "backend or confidence thresholds."
                    ),
                )
            )
        if nuisance_avg >= 1.0:
            proposals.append(
                AgentProposal(
                    title="Feature candidate: quieter deterrence profiles",
                    priority="medium",
                    rationale=(
                        "Average nuisance score over the recent encounter window is "
                        f"{nuisance_avg:.2f}."
                    ),
                    tags=["feature", "nuisance", "soundpack"],
                    implementation_hint=(
                        "Add a quieter sound pack and prefer lower-noise strategies "
                        "before escalating."
                    ),
                )
            )
        for zone_name, count in zone_returns.items():
            if count >= 2:
                proposals.append(
                    AgentProposal(
                        title=f"Coverage improvement for {zone_name}",
                        priority="medium",
                        rationale=(
                            f"{count} recent encounters returned the same night in "
                            f"zone {zone_name}."
                        ),
                        tags=["feature", "coverage", zone_name],
                        implementation_hint=(
                            "Consider additional patrol viewpoints, geofence tuning, "
                            "or zone-specific strategy overrides."
                        ),
                    )
                )
        if hazard_count > 0:
            proposals.append(
                AgentProposal(
                    title="Operational drill: hazard wildlife safe-park review",
                    priority="high",
                    rationale=(
                        f"{hazard_count} recent hazard-class detections were "
                        "observed in the recent outcome window."
                    ),
                    tags=["safety", "hazard", "operations"],
                    implementation_hint=(
                        "Practice safe-park behavior and verify operator escalation "
                        "instructions."
                    ),
                )
            )

        findings.append(
            AgentFinding(
                category="improvement",
                severity="info",
                title="Mission backlog refreshed",
                detail=(
                    f"Generated {len(proposals)} active proposals from "
                    f"{len(recent)} recent outcomes."
                ),
            )
        )
        return AgentReport(
            agent_name=self.name,
            summary=(
                "Mission improvement scan completed against recent outcomes and "
                "recurrence patterns."
            ),
            findings=findings,
            proposals=proposals,
            metadata={
                "recent_outcome_count": len(recent),
                "unknown_count": unknown_count,
                "average_nuisance_score": round(nuisance_avg, 2),
                "return_hotspots": dict(zone_returns),
            },
        )


class MissionAgentOrchestrator:
    def __init__(
        self,
        config: AppConfig,
        repository: EventRepository,
        tools: BoundedStrategyTools,
    ) -> None:
        self.config = config
        self.repository = repository
        self.tools = tools
        self.logger = get_logger(__name__)
        self._nightly_review = NightlyReviewAgent(tools)
        self._health_monitor = HealthMonitorAgent(config, tools)
        self._mission_improvement = MissionImprovementAgent(config, repository)

    def available_agents(self) -> list[str]:
        return [
            self._nightly_review.name,
            self._health_monitor.name,
            self._mission_improvement.name,
        ]

    def run_cycle(self, *, now: datetime | None = None) -> AgentCycleResult:
        executed_at = now or datetime.now(UTC)
        reports = [
            self._nightly_review.run(executed_at),
            self._health_monitor.run(executed_at),
            self._mission_improvement.run(),
        ]
        for report in reports:
            self.repository.record_agent_report(report)

        auto_strategy_changed = False
        selected_strategy_after: StrategyName | None = self.tools.controller.selected_strategy
        if self.config.agents.auto_strategy_selection:
            nightly_report = reports[0]
            recommended = nightly_report.metadata.get("recommended_focus_strategy")
            failed_events = int(nightly_report.metadata.get("failed_deterrence_events", 0))
            if isinstance(recommended, str) and failed_events > 0:
                next_strategy = StrategyName(recommended)
                if next_strategy != self.tools.controller.selected_strategy:
                    selected_strategy_after = self.tools.set_next_strategy(next_strategy)
                    auto_strategy_changed = True

        self.logger.info(
            "mission agent cycle completed",
            extra={
                "context": {
                    "report_count": len(reports),
                    "auto_strategy_changed": auto_strategy_changed,
                    "selected_strategy_after": (
                        selected_strategy_after.value if selected_strategy_after else None
                    ),
                }
            },
        )
        return AgentCycleResult(
            executed_at=executed_at,
            reports=reports,
            auto_strategy_changed=auto_strategy_changed,
            selected_strategy_after=selected_strategy_after,
        )

    def status(self) -> AgentStatus:
        scheduler_status = self.tools.scheduler_status()
        latest_reports = self.repository.list_agent_reports(limit=5)
        return AgentStatus(
            enabled=self.config.agents.enabled,
            auto_strategy_selection=self.config.agents.auto_strategy_selection,
            last_cycle_local=scheduler_status.last_agent_cycle_local,
            next_cycle_local=scheduler_status.next_agent_cycle_local,
            available_agents=self.available_agents(),
            total_reports=self.repository.count_agent_reports(),
            latest_reports=latest_reports,
        )
