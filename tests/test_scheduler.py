from __future__ import annotations

from datetime import UTC, datetime

from raccoon_guardian.config import (
    AgentConfig,
    GuardRoundConfig,
    MorningSummaryConfig,
    SafetyConfig,
    SentryConfig,
)
from raccoon_guardian.control.scheduler import RuntimeScheduler


def test_runtime_scheduler_status_and_next_runs() -> None:
    safety = SafetyConfig(
        timezone="UTC",
        armed_hours_start=datetime(2026, 1, 15, 0, 0, tzinfo=UTC).time(),
        armed_hours_end=datetime(2026, 1, 15, 23, 59, tzinfo=UTC).time(),
    )
    scheduler = RuntimeScheduler(
        timezone_name="UTC",
        morning_summary=MorningSummaryConfig(
            enabled=True,
            delivery_hour_local=7,
            delivery_minute_local=30,
        ),
        guard_rounds=GuardRoundConfig(
            enabled=True,
            interval_minutes=30,
            presets=["gate_watch", "pool_watch"],
        ),
        sentry=SentryConfig(enabled=True, interval_minutes=20),
        agents=AgentConfig(enabled=True, run_interval_minutes=60),
        safety=safety,
    )
    now = datetime(2026, 1, 15, 2, 15, tzinfo=UTC)
    snapshot = scheduler.status(now)

    assert snapshot.scheduler_enabled is True
    assert snapshot.guard_rounds_enabled is True
    assert snapshot.next_morning_summary_local is not None
    assert snapshot.next_guard_round_local is not None
    assert snapshot.guard_round_presets == ["gate_watch", "pool_watch"]
    assert snapshot.next_sentry_patrol_local is not None
    assert snapshot.next_agent_cycle_local is not None


def test_runtime_scheduler_marks_summary_and_guard_round_runs() -> None:
    safety = SafetyConfig(
        timezone="UTC",
        armed_hours_start=datetime(2026, 1, 15, 0, 0, tzinfo=UTC).time(),
        armed_hours_end=datetime(2026, 1, 15, 23, 59, tzinfo=UTC).time(),
    )
    scheduler = RuntimeScheduler(
        timezone_name="UTC",
        morning_summary=MorningSummaryConfig(
            enabled=True, delivery_hour_local=7, delivery_minute_local=30
        ),
        guard_rounds=GuardRoundConfig(enabled=True, interval_minutes=30, presets=["gate_watch"]),
        sentry=SentryConfig(enabled=True, interval_minutes=20),
        agents=AgentConfig(enabled=True, run_interval_minutes=60),
        safety=safety,
    )
    now = datetime(2026, 1, 15, 2, 15, tzinfo=UTC)
    scheduler.mark_guard_round_attempt(now)
    scheduler.mark_morning_summary_attempt(now)
    scheduler.mark_sentry_patrol_attempt(now)
    scheduler.mark_agent_cycle_attempt(now)
    scheduler.mark_guard_round_run(now)
    scheduler.mark_morning_summary_delivered(now)
    scheduler.mark_sentry_patrol_run(now)
    scheduler.mark_agent_cycle_run(now)
    snapshot = scheduler.status(now)

    assert snapshot.last_guard_round_local is not None
    assert snapshot.last_morning_summary_local is not None
    assert snapshot.last_guard_round_attempt_local is not None
    assert snapshot.last_morning_summary_attempt_local is not None
    assert snapshot.last_sentry_patrol_attempt_local is not None
    assert snapshot.last_sentry_patrol_local is not None
    assert snapshot.last_agent_cycle_attempt_local is not None
    assert snapshot.last_agent_cycle_local is not None


def test_runtime_scheduler_due_checks_are_once_per_window() -> None:
    safety = SafetyConfig(
        timezone="UTC",
        armed_hours_start=datetime(2026, 1, 15, 0, 0, tzinfo=UTC).time(),
        armed_hours_end=datetime(2026, 1, 15, 23, 59, tzinfo=UTC).time(),
    )
    scheduler = RuntimeScheduler(
        timezone_name="UTC",
        morning_summary=MorningSummaryConfig(
            enabled=True, delivery_hour_local=7, delivery_minute_local=30
        ),
        guard_rounds=GuardRoundConfig(enabled=True, interval_minutes=30, presets=["gate_watch"]),
        sentry=SentryConfig(enabled=True, interval_minutes=20),
        agents=AgentConfig(enabled=True, run_interval_minutes=60),
        safety=safety,
    )
    now = datetime(2026, 1, 15, 7, 45, tzinfo=UTC)

    assert scheduler.should_deliver_morning_summary(now) is True
    scheduler.mark_morning_summary_attempt(now)
    assert scheduler.should_deliver_morning_summary(now) is False
    assert scheduler.morning_summary_target_date(now) == "2026-01-14"

    assert scheduler.should_run_guard_round(now) is True
    scheduler.mark_guard_round_attempt(now)
    assert scheduler.should_run_guard_round(now) is False

    assert scheduler.should_run_sentry_patrol(now) is True
    scheduler.mark_sentry_patrol_attempt(now)
    assert scheduler.should_run_sentry_patrol(now) is False

    assert scheduler.should_run_agent_cycle(now) is True
    scheduler.mark_agent_cycle_attempt(now)
    assert scheduler.should_run_agent_cycle(now) is False
