from __future__ import annotations

from raccoon_guardian.domain.enums import ActionType
from raccoon_guardian.domain.models import ActuationResult
from raccoon_guardian.logging import get_logger


class LoggedPanActuator:
    """Stub for a bounded preset or small-angle pan mount."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def move_pan(self, preset: str | None = None, degrees: int | None = None) -> ActuationResult:
        self.logger.info(
            "pan actuation requested",
            extra={"context": {"preset": preset, "degrees": degrees}},
        )
        detail = f"pan move preset={preset!r} degrees={degrees!r} would be issued"
        return ActuationResult(action_type=ActionType.PAN, success=True, detail=detail)
