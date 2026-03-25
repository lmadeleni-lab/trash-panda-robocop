from __future__ import annotations

from datetime import datetime

from raccoon_guardian.config import SafetyConfig


class ArmingScheduler:
    def __init__(self, config: SafetyConfig) -> None:
        self.config = config

    def is_armed_time(self, when: datetime) -> bool:
        return self.config.is_within_arm_window(when)
