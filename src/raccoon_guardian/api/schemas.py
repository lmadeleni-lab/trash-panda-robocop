from __future__ import annotations

from pydantic import BaseModel, Field

from raccoon_guardian.domain.enums import StrategyName, ZoneId
from raccoon_guardian.domain.models import DetectionEvent


class HealthResponse(BaseModel):
    status: str
    state: str


class MockEventRequest(DetectionEvent):
    pass


class StrategySelectionRequest(BaseModel):
    strategy_name: StrategyName


class TestActuationRequest(BaseModel):
    strategy_name: StrategyName = Field(default=StrategyName.LIGHT_ONLY)
    zone_id: ZoneId = Field(default=ZoneId.GATE_ENTRY)
