from __future__ import annotations

from raccoon_guardian.domain.enums import ActionType, ZoneId
from raccoon_guardian.domain.models import ActuationResult
from raccoon_guardian.logging import get_logger


class LoggedWaterActuator:
    """Stub for a bounded valve or pump trigger."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def spray_water(self, zone: ZoneId, duration_s: float) -> ActuationResult:
        self.logger.info(
            "water actuation requested",
            extra={"context": {"zone": zone.value, "duration_s": duration_s}},
        )
        return ActuationResult(
            action_type=ActionType.WATER,
            success=True,
            detail=f"water spray in zone '{zone.value}' for {duration_s:.2f}s would be issued",
        )
