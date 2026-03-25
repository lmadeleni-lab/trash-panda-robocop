from __future__ import annotations

from typing import Protocol

from raccoon_guardian.domain.enums import ZoneId
from raccoon_guardian.domain.models import ActuationResult, BoundedAction


class ActuatorHub(Protocol):
    def flash_light(self, pattern: str) -> ActuationResult: ...

    def play_sound(self, mode: str, duration_s: float) -> ActuationResult: ...

    def spray_water(self, zone: ZoneId, duration_s: float) -> ActuationResult: ...

    def move_pan(
        self, preset: str | None = None, degrees: int | None = None
    ) -> ActuationResult: ...

    def stop_all(self) -> ActuationResult: ...

    def execute(self, action: BoundedAction) -> ActuationResult: ...
