from __future__ import annotations

from dataclasses import dataclass, field

from raccoon_guardian.domain.enums import SystemState

ALLOWED_TRANSITIONS: dict[SystemState, set[SystemState]] = {
    SystemState.DISARMED: {SystemState.IDLE},
    SystemState.IDLE: {SystemState.DISARMED, SystemState.DETECTING, SystemState.ERROR},
    SystemState.DETECTING: {SystemState.IDLE, SystemState.DECIDING, SystemState.ERROR},
    SystemState.DECIDING: {SystemState.IDLE, SystemState.ACTING, SystemState.ERROR},
    SystemState.ACTING: {SystemState.COOLDOWN, SystemState.ERROR},
    SystemState.COOLDOWN: {
        SystemState.IDLE,
        SystemState.DETECTING,
        SystemState.DISARMED,
        SystemState.ERROR,
    },
    SystemState.ERROR: {SystemState.DISARMED, SystemState.IDLE},
}


@dataclass(slots=True)
class SystemStateMachine:
    state: SystemState = field(default=SystemState.DISARMED)

    def transition(self, new_state: SystemState) -> None:
        allowed = ALLOWED_TRANSITIONS[self.state]
        if new_state not in allowed:
            msg = f"invalid transition from {self.state.value} to {new_state.value}"
            raise ValueError(msg)
        self.state = new_state

    def reset_to_idle(self) -> None:
        if self.state == SystemState.ERROR:
            self.transition(SystemState.IDLE)
