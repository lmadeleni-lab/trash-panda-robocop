from __future__ import annotations

from raccoon_guardian.domain.enums import ActionType
from raccoon_guardian.domain.models import ActuationResult
from raccoon_guardian.logging import get_logger


class LoggedSoundActuator:
    """Stub for future audio playback or GPIO trigger support."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def play_sound(self, mode: str, duration_s: float) -> ActuationResult:
        self.logger.info(
            "sound actuation requested",
            extra={"context": {"mode": mode, "duration_s": duration_s}},
        )
        return ActuationResult(
            action_type=ActionType.SOUND,
            success=True,
            detail=f"sound mode '{mode}' for {duration_s:.2f}s would be issued to hardware",
        )
