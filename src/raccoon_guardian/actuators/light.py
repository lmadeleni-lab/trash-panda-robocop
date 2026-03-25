from __future__ import annotations

from raccoon_guardian.domain.enums import ActionType
from raccoon_guardian.domain.models import ActuationResult
from raccoon_guardian.logging import get_logger


class LoggedLightActuator:
    """Stub for future GPIO-backed light control."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def flash_light(self, pattern: str) -> ActuationResult:
        self.logger.info("light actuation requested", extra={"context": {"pattern": pattern}})
        return ActuationResult(
            action_type=ActionType.LIGHT,
            success=True,
            detail=f"light pattern '{pattern}' would be issued to hardware",
        )
