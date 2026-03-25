from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from raccoon_guardian.config import ZoneConfig
from raccoon_guardian.domain.enums import DirectionOfTravel, TargetClass
from raccoon_guardian.domain.models import DetectionEvent, NormalizedBBox
from raccoon_guardian.perception.zone_logic import zone_for_bbox


@dataclass(slots=True)
class FramePacket:
    image: Any
    source: str = "camera0"
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    frame_id: str = field(default_factory=lambda: str(uuid4()))


class DetectionCandidate(BaseModel):
    target_class: TargetClass = TargetClass.UNKNOWN
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: NormalizedBBox
    scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, str | float | int | bool] = Field(default_factory=dict)


class Detector(Protocol):
    def detect(self, frame: FramePacket) -> list[DetectionCandidate]: ...


class FrameSource(Protocol):
    def capture_frame(self) -> FramePacket: ...


class DetectionEventBuilder:
    def __init__(self, zones: list[ZoneConfig]) -> None:
        self.zones = zones

    def build_events(
        self,
        frame: FramePacket,
        candidates: list[DetectionCandidate],
    ) -> list[DetectionEvent]:
        events: list[DetectionEvent] = []
        for candidate in candidates:
            direction_value = candidate.metadata.get("direction", DirectionOfTravel.UNKNOWN.value)
            try:
                direction = DirectionOfTravel(str(direction_value))
            except ValueError:
                direction = DirectionOfTravel.UNKNOWN
            events.append(
                DetectionEvent(
                    target_detected=True,
                    target_class=candidate.target_class,
                    confidence=candidate.confidence,
                    zone_id=zone_for_bbox(candidate.bbox, self.zones),
                    direction_of_travel=direction,
                    timestamp=frame.captured_at,
                    is_human=candidate.target_class == TargetClass.PERSON,
                    is_pet=candidate.target_class in {TargetClass.CAT, TargetClass.DOG},
                    bbox=candidate.bbox,
                )
            )
        return events
