from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from raccoon_guardian.domain.enums import (
    ActionType,
    DirectionOfTravel,
    StrategyName,
    SystemState,
    TargetClass,
    ZoneId,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class NormalizedBBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @field_validator("x1", "y1", "x2", "y2")
    @classmethod
    def validate_bounds(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            msg = "bbox coordinates must be normalized to [0, 1]"
            raise ValueError(msg)
        return value

    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


class OutcomeMetrics(BaseModel):
    retreat_detected: bool = False
    seconds_to_exit_zone: float | None = None
    returned_within_10_min: bool = False
    returned_same_night: bool = False
    false_positive: bool = False
    nuisance_score: float = 0.0
    possible_droppings_detected: bool = False
    possible_droppings_zone: ZoneId | None = None
    possible_droppings_note: str | None = None


class DetectionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    target_detected: bool = True
    target_class: TargetClass
    confidence: float = Field(ge=0.0, le=1.0)
    zone_id: ZoneId
    direction_of_travel: DirectionOfTravel = DirectionOfTravel.UNKNOWN
    timestamp: datetime = Field(default_factory=utc_now)
    is_human: bool = False
    is_pet: bool = False
    bbox: NormalizedBBox | None = None
    simulated_outcome: OutcomeMetrics | None = None


class BoundedAction(BaseModel):
    action_type: ActionType
    pattern: str | None = None
    mode: str | None = None
    duration_s: float | None = None
    zone: ZoneId | None = None
    preset: str | None = None
    degrees: int | None = None


class ActuationResult(BaseModel):
    action_type: ActionType
    success: bool
    detail: str
    issued_at: datetime = Field(default_factory=utc_now)


class DecisionTraceEntry(BaseModel):
    rule: str
    allowed: bool
    message: str


class SafetyDecision(BaseModel):
    allowed: bool
    action_plan: list[BoundedAction]
    trace: list[DecisionTraceEntry]


class StrategyDefinition(BaseModel):
    name: StrategyName
    description: str
    actions: list[BoundedAction]


class StrategyScore(BaseModel):
    strategy: StrategyName
    encounters: int
    mean_score: float
    retreat_rate: float


class TargetBreakdown(BaseModel):
    target_class: TargetClass
    total_events: int
    acted_events: int


class DroppingsZoneSummary(BaseModel):
    zone_id: ZoneId
    flagged_events: int


class HeatmapCell(BaseModel):
    zone_id: ZoneId
    intensity: str
    flagged_events: int


class OpenClawOperation(BaseModel):
    name: str
    description: str


class SchedulerStatus(BaseModel):
    scheduler_enabled: bool
    current_local_time: str
    next_morning_summary_local: str | None
    last_morning_summary_local: str | None
    last_morning_summary_attempt_local: str | None
    guard_rounds_enabled: bool
    next_guard_round_local: str | None
    last_guard_round_local: str | None
    last_guard_round_attempt_local: str | None
    guard_round_presets: list[str]
    agents_enabled: bool
    next_agent_cycle_local: str | None
    last_agent_cycle_local: str | None
    last_agent_cycle_attempt_local: str | None


class SystemStatus(BaseModel):
    environment: str
    state: str
    armed: bool
    selected_strategy: StrategyName
    last_action_at: str | None
    simulation_mode: bool
    detector_backend: str
    api_key_enabled: bool
    slack_enabled: bool
    morning_summary_enabled: bool
    guard_rounds_enabled: bool
    background_scheduler_enabled: bool
    agents_enabled: bool


class OpenClawManifest(BaseModel):
    integration_name: str
    api_version: str
    operations: list[OpenClawOperation]
    safety_notes: list[str]


class NightlySummary(BaseModel):
    date: str
    total_events: int
    acted_events: int
    denied_events: int
    failed_deterrence_events: int
    target_breakdown: list[TargetBreakdown]
    droppings_map: list[DroppingsZoneSummary]
    droppings_heatmap: list[HeatmapCell]
    recommended_focus_strategy: StrategyName | None = None
    rankings: list[StrategyScore]


class NotificationResult(BaseModel):
    delivered: bool
    channel: str
    detail: str


class AgentFinding(BaseModel):
    category: str
    severity: str
    title: str
    detail: str


class AgentProposal(BaseModel):
    title: str
    priority: str
    rationale: str
    tags: list[str] = Field(default_factory=list)
    implementation_hint: str | None = None


class AgentReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    created_at: datetime = Field(default_factory=utc_now)
    summary: str
    findings: list[AgentFinding] = Field(default_factory=list)
    proposals: list[AgentProposal] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentCycleResult(BaseModel):
    executed_at: datetime = Field(default_factory=utc_now)
    reports: list[AgentReport]
    auto_strategy_changed: bool = False
    selected_strategy_after: StrategyName | None = None


class AgentStatus(BaseModel):
    enabled: bool
    auto_strategy_selection: bool
    last_cycle_local: str | None
    next_cycle_local: str | None
    available_agents: list[str]
    total_reports: int
    latest_reports: list[AgentReport]


class EncounterRecord(BaseModel):
    encounter_id: str = Field(default_factory=lambda: str(uuid4()))
    detection: DetectionEvent
    state_before: SystemState
    state_after: SystemState
    chosen_strategy: StrategyName | None = None
    decision: SafetyDecision
    action_results: list[ActuationResult] = Field(default_factory=list)
    outcome: OutcomeMetrics | None = None
    created_at: datetime = Field(default_factory=utc_now)

    def as_storage_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class OpenClawBriefing(BaseModel):
    summary_date: str
    system_status: SystemStatus
    scheduler_status: SchedulerStatus
    recommendation_map: dict[str, str]
    strategies: list[StrategyDefinition]
    recent_outcomes: list[EncounterRecord]
    nightly_summary: NightlySummary
