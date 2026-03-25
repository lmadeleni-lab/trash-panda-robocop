from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class CooldownGate:
    cooldown_s: float

    def is_ready(self, now: datetime, last_action_at: datetime | None) -> bool:
        if last_action_at is None:
            return True
        return now - last_action_at >= timedelta(seconds=self.cooldown_s)
