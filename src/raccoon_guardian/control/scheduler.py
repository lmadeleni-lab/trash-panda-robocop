from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from raccoon_guardian.config import (
    AgentConfig,
    GuardRoundConfig,
    MorningSummaryConfig,
    SafetyConfig,
)
from raccoon_guardian.domain.models import SchedulerStatus


class ArmingScheduler:
    def __init__(self, config: SafetyConfig) -> None:
        self.config = config

    def is_armed_time(self, when: datetime) -> bool:
        return self.config.is_within_arm_window(when)


@dataclass(slots=True)
class RuntimeScheduler:
    timezone_name: str
    morning_summary: MorningSummaryConfig
    guard_rounds: GuardRoundConfig
    agents: AgentConfig
    safety: SafetyConfig
    last_morning_summary_at: datetime | None = None
    last_morning_summary_attempt_at: datetime | None = None
    last_guard_round_at: datetime | None = None
    last_guard_round_attempt_at: datetime | None = None
    last_agent_cycle_at: datetime | None = None
    last_agent_cycle_attempt_at: datetime | None = None

    def _tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def _localize(self, when: datetime) -> datetime:
        return when.astimezone(self._tz())

    def _scheduled_morning_summary_time(self, now: datetime) -> datetime:
        local_now = self._localize(now)
        return local_now.replace(
            hour=self.morning_summary.delivery_hour_local,
            minute=self.morning_summary.delivery_minute_local,
            second=0,
            microsecond=0,
        )

    def next_morning_summary(self, now: datetime) -> datetime | None:
        if not self.morning_summary.enabled:
            return None
        local_now = self._localize(now)
        scheduled = self._scheduled_morning_summary_time(now)
        if scheduled <= local_now:
            scheduled += timedelta(days=1)
        return scheduled

    def next_guard_round(self, now: datetime) -> datetime | None:
        if not self.guard_rounds.enabled:
            return None
        if not self.safety.is_within_arm_window(now):
            return None
        last_run = self.last_guard_round_attempt_at or self.last_guard_round_at
        if last_run is None:
            return self._localize(now)
        return self._localize(last_run) + timedelta(minutes=self.guard_rounds.interval_minutes)

    def should_deliver_morning_summary(self, now: datetime) -> bool:
        if not self.morning_summary.enabled:
            return False
        local_now = self._localize(now)
        if local_now < self._scheduled_morning_summary_time(now):
            return False
        if self.last_morning_summary_attempt_at is None:
            return True
        last_attempt_local = self._localize(self.last_morning_summary_attempt_at)
        return last_attempt_local.date() < local_now.date()

    def morning_summary_target_date(self, now: datetime) -> str:
        return (self._localize(now).date() - timedelta(days=1)).isoformat()

    def should_run_guard_round(self, now: datetime) -> bool:
        if not self.guard_rounds.enabled or not self.safety.is_within_arm_window(now):
            return False
        last_attempt = self.last_guard_round_attempt_at or self.last_guard_round_at
        if last_attempt is None:
            return True
        return now >= last_attempt + timedelta(minutes=self.guard_rounds.interval_minutes)

    def next_agent_cycle(self, now: datetime) -> datetime | None:
        if not self.agents.enabled:
            return None
        last_run = self.last_agent_cycle_attempt_at or self.last_agent_cycle_at
        if last_run is None:
            return self._localize(now)
        return self._localize(last_run) + timedelta(minutes=self.agents.run_interval_minutes)

    def should_run_agent_cycle(self, now: datetime) -> bool:
        if not self.agents.enabled:
            return False
        last_attempt = self.last_agent_cycle_attempt_at or self.last_agent_cycle_at
        if last_attempt is None:
            return True
        return now >= last_attempt + timedelta(minutes=self.agents.run_interval_minutes)

    def mark_guard_round_attempt(self, when: datetime) -> None:
        self.last_guard_round_attempt_at = when

    def mark_guard_round_run(self, when: datetime) -> None:
        self.last_guard_round_attempt_at = when
        self.last_guard_round_at = when

    def mark_agent_cycle_attempt(self, when: datetime) -> None:
        self.last_agent_cycle_attempt_at = when

    def mark_agent_cycle_run(self, when: datetime) -> None:
        self.last_agent_cycle_attempt_at = when
        self.last_agent_cycle_at = when

    def mark_morning_summary_attempt(self, when: datetime) -> None:
        self.last_morning_summary_attempt_at = when

    def mark_morning_summary_delivered(self, when: datetime) -> None:
        self.last_morning_summary_attempt_at = when
        self.last_morning_summary_at = when

    def status(self, now: datetime) -> SchedulerStatus:
        next_summary = self.next_morning_summary(now)
        next_guard_round = self.next_guard_round(now)
        next_agent_cycle = self.next_agent_cycle(now)
        return SchedulerStatus(
            scheduler_enabled=(
                self.morning_summary.enabled or self.guard_rounds.enabled or self.agents.enabled
            ),
            current_local_time=self._localize(now).isoformat(),
            next_morning_summary_local=next_summary.isoformat() if next_summary else None,
            last_morning_summary_local=(
                self._localize(self.last_morning_summary_at).isoformat()
                if self.last_morning_summary_at
                else None
            ),
            last_morning_summary_attempt_local=(
                self._localize(self.last_morning_summary_attempt_at).isoformat()
                if self.last_morning_summary_attempt_at
                else None
            ),
            guard_rounds_enabled=self.guard_rounds.enabled,
            next_guard_round_local=next_guard_round.isoformat() if next_guard_round else None,
            last_guard_round_local=(
                self._localize(self.last_guard_round_at).isoformat()
                if self.last_guard_round_at
                else None
            ),
            last_guard_round_attempt_local=(
                self._localize(self.last_guard_round_attempt_at).isoformat()
                if self.last_guard_round_attempt_at
                else None
            ),
            guard_round_presets=self.guard_rounds.presets,
            agents_enabled=self.agents.enabled,
            next_agent_cycle_local=next_agent_cycle.isoformat() if next_agent_cycle else None,
            last_agent_cycle_local=(
                self._localize(self.last_agent_cycle_at).isoformat()
                if self.last_agent_cycle_at
                else None
            ),
            last_agent_cycle_attempt_local=(
                self._localize(self.last_agent_cycle_attempt_at).isoformat()
                if self.last_agent_cycle_attempt_at
                else None
            ),
        )
