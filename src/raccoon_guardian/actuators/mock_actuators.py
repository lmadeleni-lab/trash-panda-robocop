from __future__ import annotations

from raccoon_guardian.actuators.base import ActuatorHub
from raccoon_guardian.domain.enums import ActionType, ZoneId
from raccoon_guardian.domain.models import ActuationResult, BoundedAction


class MockActuatorHub(ActuatorHub):
    def __init__(self) -> None:
        self.history: list[ActuationResult] = []

    def flash_light(self, pattern: str) -> ActuationResult:
        result = ActuationResult(
            action_type=ActionType.LIGHT,
            success=True,
            detail=f"mock light pattern={pattern}",
        )
        self.history.append(result)
        return result

    def play_sound(self, mode: str, duration_s: float) -> ActuationResult:
        result = ActuationResult(
            action_type=ActionType.SOUND,
            success=True,
            detail=f"mock sound mode={mode} duration_s={duration_s:.2f}",
        )
        self.history.append(result)
        return result

    def spray_water(self, zone: ZoneId, duration_s: float) -> ActuationResult:
        result = ActuationResult(
            action_type=ActionType.WATER,
            success=True,
            detail=f"mock water zone={zone.value} duration_s={duration_s:.2f}",
        )
        self.history.append(result)
        return result

    def move_pan(self, preset: str | None = None, degrees: int | None = None) -> ActuationResult:
        result = ActuationResult(
            action_type=ActionType.PAN,
            success=True,
            detail=f"mock pan preset={preset!r} degrees={degrees!r}",
        )
        self.history.append(result)
        return result

    def stop_all(self) -> ActuationResult:
        result = ActuationResult(
            action_type=ActionType.STOP_ALL,
            success=True,
            detail="mock stop_all",
        )
        self.history.append(result)
        return result

    def execute(self, action: BoundedAction) -> ActuationResult:
        if action.action_type == ActionType.LIGHT:
            return self.flash_light(action.pattern or "default")
        if action.action_type == ActionType.SOUND:
            return self.play_sound(action.mode or "chirp", action.duration_s or 0.0)
        if action.action_type == ActionType.WATER:
            return self.spray_water(action.zone or ZoneId.GATE_ENTRY, action.duration_s or 0.0)
        if action.action_type == ActionType.PAN:
            return self.move_pan(action.preset, action.degrees)
        return self.stop_all()
