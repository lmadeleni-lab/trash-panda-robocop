from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from raccoon_guardian.domain.enums import StrategyName, ZoneId


class LoggingConfig(BaseModel):
    level: str = "INFO"


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
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
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


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return project_root() / "configs" / "default.yaml"


def load_config(path: Path | str | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else default_config_path()
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
