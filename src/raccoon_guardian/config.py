from __future__ import annotations

import os
from datetime import datetime, time
from ipaddress import ip_network
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from raccoon_guardian.domain.enums import StrategyName, TargetClass, ZoneId


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file_enabled: bool = True
    file_path: Path = Path("data/logs/trash-panda-robocop.log")
    request_logging_enabled: bool = True


class SecurityConfig(BaseModel):
    api_key_enabled: bool = False
    api_key: str | None = None
    allow_unsafe_local_without_key: bool = True
    trusted_network_required: bool = False
    trusted_client_cidrs: list[str] = Field(default_factory=list)

    @field_validator("trusted_client_cidrs")
    @classmethod
    def validate_trusted_client_cidrs(cls, cidrs: list[str]) -> list[str]:
        for cidr in cidrs:
            ip_network(cidr, strict=False)
        return cidrs


class NotificationConfig(BaseModel):
    slack_enabled: bool = False
    slack_webhook_url: str | None = None
    deliver_morning_summary: bool = False
    escalation_enabled: bool = False
    escalation_failure_threshold: int = Field(default=2, ge=1)


class MorningSummaryConfig(BaseModel):
    enabled: bool = True
    delivery_hour_local: int = Field(default=7, ge=0, le=23)
    delivery_minute_local: int = Field(default=30, ge=0, le=59)


class GuardRoundConfig(BaseModel):
    enabled: bool = True
    interval_minutes: int = Field(default=30, ge=5, le=240)
    presets: list[str] = Field(default_factory=lambda: ["gate_watch", "pool_watch"])


class PatrolWaypointConfig(BaseModel):
    waypoint_id: str
    zone_id: ZoneId
    observation_preset: str
    linear_m_s: float = Field(default=0.0, ge=-1.0, le=1.0)
    angular_rad_s: float = Field(default=0.0, ge=-2.0, le=2.0)
    move_duration_s: float = Field(default=1.0, gt=0.0, le=10.0)
    dwell_s: float = Field(default=2.0, ge=0.0, le=60.0)
    servo_id: int = Field(default=1, ge=1, le=16)
    servo_position: int = Field(default=500, ge=0, le=1000)


class PatrolPathConfig(BaseModel):
    path_id: str
    display_name: str
    area_tags: list[str] = Field(default_factory=list)
    waypoints: list[PatrolWaypointConfig]

    @field_validator("waypoints")
    @classmethod
    def validate_waypoints(
        cls,
        waypoints: list[PatrolWaypointConfig],
    ) -> list[PatrolWaypointConfig]:
        if not waypoints:
            msg = "patrol paths must define at least one waypoint"
            raise ValueError(msg)
        return waypoints


class SentryConfig(BaseModel):
    enabled: bool = False
    interval_minutes: int = Field(default=20, ge=5, le=240)
    allow_agent_path_selection: bool = True
    regroup_preset: str = "dock"
    default_path_id: str | None = None
    patrol_paths: list[PatrolPathConfig] = Field(default_factory=list)


class FleetBotConfig(BaseModel):
    bot_id: str
    display_name: str
    assigned_areas: list[ZoneId] = Field(default_factory=list)
    home_path_id: str | None = None
    active: bool = True


class FleetResourceConfig(BaseModel):
    low_battery_threshold_percent: float = Field(default=35.0, ge=0.0, le=100.0)
    critical_battery_threshold_percent: float = Field(default=15.0, ge=0.0, le=100.0)
    low_water_threshold_percent: float = Field(default=30.0, ge=0.0, le=100.0)
    critical_water_threshold_percent: float = Field(default=10.0, ge=0.0, le=100.0)
    min_battery_for_patrol_percent: float = Field(default=20.0, ge=0.0, le=100.0)
    min_water_for_deterrence_percent: float = Field(default=15.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> FleetResourceConfig:
        if self.critical_battery_threshold_percent > self.low_battery_threshold_percent:
            msg = "critical battery threshold must be less than or equal to low threshold"
            raise ValueError(msg)
        if self.critical_water_threshold_percent > self.low_water_threshold_percent:
            msg = "critical water threshold must be less than or equal to low threshold"
            raise ValueError(msg)
        return self


class FleetConfig(BaseModel):
    enabled: bool = False
    local_bot_id: str = "bot-alpha"
    coordination_enabled: bool = True
    regroup_enabled: bool = True
    max_bots_per_zone_observation: int = Field(default=2, ge=1, le=4)
    prohibit_live_target_convergence: bool = True
    bots: list[FleetBotConfig] = Field(default_factory=list)
    resources: FleetResourceConfig = Field(default_factory=FleetResourceConfig)


class RecoveryConfig(BaseModel):
    enabled: bool = True
    wheel_slip_timeout_s: float = Field(default=8.0, ge=1.0, le=60.0)
    max_recovery_attempts: int = Field(default=3, ge=1, le=10)
    reverse_duration_s: float = Field(default=1.0, gt=0.0, le=5.0)
    turn_duration_s: float = Field(default=1.0, gt=0.0, le=5.0)
    notify_on_recovery: bool = True


class RuntimeConfig(BaseModel):
    background_scheduler_enabled: bool = False
    scheduler_poll_interval_s: float = Field(default=30.0, ge=5.0, le=300.0)


class AgentConfig(BaseModel):
    enabled: bool = True
    run_interval_minutes: int = Field(default=60, ge=5, le=1440)
    auto_strategy_selection: bool = False
    max_recent_outcomes: int = Field(default=50, ge=5, le=500)


class PerceptionConfig(BaseModel):
    detector_backend: str = "mock"
    min_confidence: float = Field(default=0.45, ge=0.0, le=1.0)
    capture_dir: Path = Path("data/captures")
    save_debug_frames: bool = True
    max_saved_frames: int = Field(default=250, ge=1)
    camera_source: int | str = 0


class ZoneConfig(BaseModel):
    zone_id: ZoneId
    display_name: str
    polygon: list[tuple[float, float]]
    deterrence_enabled: bool = True

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, polygon: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(polygon) < 3:
            msg = "zone polygon must contain at least three points"
            raise ValueError(msg)
        return polygon


class SafetyConfig(BaseModel):
    timezone: str = "America/New_York"
    armed_hours_start: time
    armed_hours_end: time
    cooldown_s: float = Field(default=30.0, ge=0.0)
    max_water_duration_s: float = Field(default=1.5, gt=0.0)
    max_sound_duration_s: float = Field(default=1.0, gt=0.0)
    max_pan_degrees: int = Field(default=25, ge=0)
    manual_disable: bool = False
    allow_test_actuation: bool = False

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def is_within_arm_window(self, when: datetime) -> bool:
        local_time = when.astimezone(self.tzinfo).timetz().replace(tzinfo=None)
        if self.armed_hours_start <= self.armed_hours_end:
            return self.armed_hours_start <= local_time <= self.armed_hours_end
        return local_time >= self.armed_hours_start or local_time <= self.armed_hours_end


class AppConfig(BaseModel):
    name: str = "raccoon-guardian"
    environment: str = "local"
    database_path: Path = Path("data/raccoon_guardian.db")
    simulation_mode: bool = True
    armed_default: bool = True
    selected_strategy: StrategyName = StrategyName.LIGHT_ONLY
    target_strategy_preferences: dict[TargetClass, StrategyName] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    morning_summary: MorningSummaryConfig = Field(default_factory=MorningSummaryConfig)
    guard_rounds: GuardRoundConfig = Field(default_factory=GuardRoundConfig)
    sentry: SentryConfig = Field(default_factory=SentryConfig)
    fleet: FleetConfig = Field(default_factory=FleetConfig)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    agents: AgentConfig = Field(default_factory=AgentConfig)
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    safety: SafetyConfig
    zones: list[ZoneConfig]

    @model_validator(mode="after")
    def validate_zone_ids(self) -> AppConfig:
        expected = {ZoneId.GATE_ENTRY, ZoneId.BACKYARD_PROTECTED}
        present = {zone.zone_id for zone in self.zones}
        if not expected.issubset(present):
            msg = "configs must define gate_entry and backyard_protected zones"
            raise ValueError(msg)
        return self

    def zone_map(self) -> dict[ZoneId, ZoneConfig]:
        return {zone.zone_id: zone for zone in self.zones}

    def path_map(self) -> dict[str, PatrolPathConfig]:
        return {path.path_id: path for path in self.sentry.patrol_paths}

    def public_config(self) -> dict[str, object]:
        payload = self.model_dump(mode="json")
        security = payload.get("security")
        if isinstance(security, dict) and "api_key" in security:
            security["api_key"] = "***" if security["api_key"] else None
        notifications = payload.get("notifications")
        if isinstance(notifications, dict) and "slack_webhook_url" in notifications:
            notifications["slack_webhook_url"] = (
                "***" if notifications["slack_webhook_url"] else None
            )
        return payload


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return project_root() / "configs" / "default.yaml"


def load_config(path: Path | str | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else default_config_path()
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if isinstance(raw, dict):
        security = raw.setdefault("security", {})
        notifications = raw.setdefault("notifications", {})
        env_api_key = os.getenv("RG_API_KEY")
        env_slack_webhook = os.getenv("RG_SLACK_WEBHOOK_URL")
        env_log_file = os.getenv("RG_LOG_FILE")
        if env_api_key:
            security["api_key"] = env_api_key
            security["api_key_enabled"] = True
        if env_slack_webhook:
            notifications["slack_webhook_url"] = env_slack_webhook
        if env_log_file:
            logging = raw.setdefault("logging", {})
            logging["file_enabled"] = True
            logging["file_path"] = env_log_file
    return AppConfig.model_validate(raw)
