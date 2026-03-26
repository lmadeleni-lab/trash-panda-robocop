from __future__ import annotations

from datetime import UTC, datetime

from raccoon_guardian.domain.enums import StrategyName
from raccoon_guardian.domain.models import (
    EncounterRecord,
    NightlySummary,
    OpenClawBriefing,
    OpenClawManifest,
    OpenClawOperation,
    StrategyDefinition,
)
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

    def get_manifest(self) -> OpenClawManifest:
        return OpenClawManifest(
            integration_name="trash-panda-robocop",
            api_version="v1",
            operations=[
                OpenClawOperation(
                    name="get_recent_outcomes",
                    description="Read recent encounters and their measured outcomes.",
                ),
                OpenClawOperation(
                    name="list_strategies",
                    description="List the approved deterrence strategies in the fixed catalog.",
                ),
                OpenClawOperation(
                    name="set_next_strategy",
                    description="Set the approved strategy to use for the next encounter window.",
                ),
                OpenClawOperation(
                    name="get_nightly_summary",
                    description="Fetch the nightly summary and strategy ranking for a local date.",
                ),
                OpenClawOperation(
                    name="get_briefing",
                    description=(
                        "Fetch a single briefing payload for Mac mini operator or agent use."
                    ),
                ),
            ],
            safety_notes=[
                "OpenClaw may not issue arbitrary actuator commands.",
                "OpenClaw may not change safety caps, geofences, or arm windows.",
                "All selected strategies are re-evaluated by the safety policy at event time.",
            ],
        )

    def get_briefing(self, limit: int = 10, local_date: str | None = None) -> OpenClawBriefing:
        summary_date = local_date or self.tools.scheduler.morning_summary_target_date(
            datetime.now(UTC)
        )
        recommendation_map = {
            target_class.value: strategy_name.value
            for target_class, strategy_name in self.tools.recommendation_map().items()
        }
        return OpenClawBriefing(
            summary_date=summary_date,
            system_status=self.tools.system_status(),
            scheduler_status=self.tools.scheduler_status(),
            recommendation_map=recommendation_map,
            strategies=self.tools.list_strategies(),
            recent_outcomes=self.tools.get_recent_outcomes(limit),
            nightly_summary=self.tools.get_nightly_summary(summary_date),
        )
