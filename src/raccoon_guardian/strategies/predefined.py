from __future__ import annotations

from raccoon_guardian.domain.enums import ActionType, StrategyName
from raccoon_guardian.domain.models import BoundedAction, StrategyDefinition


def light(pattern: str) -> BoundedAction:
    return BoundedAction(action_type=ActionType.LIGHT, pattern=pattern)


def sound(mode: str, duration_s: float) -> BoundedAction:
    return BoundedAction(action_type=ActionType.SOUND, mode=mode, duration_s=duration_s)


def water(duration_s: float) -> BoundedAction:
    return BoundedAction(action_type=ActionType.WATER, duration_s=duration_s)


def pan(preset: str, degrees: int) -> BoundedAction:
    return BoundedAction(action_type=ActionType.PAN, preset=preset, degrees=degrees)


def predefined_strategies() -> list[StrategyDefinition]:
    return [
        StrategyDefinition(
            name=StrategyName.LIGHT_ONLY,
            description="Single visible flash pattern with no sound or water.",
            actions=[light("triple-pulse")],
        ),
        StrategyDefinition(
            name=StrategyName.LIGHT_SOUND,
            description="Light pulse followed by a short chirp cue.",
            actions=[light("triple-pulse"), sound("chirp", 0.6)],
        ),
        StrategyDefinition(
            name=StrategyName.WATER_ONLY,
            description="Brief bounded water spray only.",
            actions=[water(1.0)],
        ),
        StrategyDefinition(
            name=StrategyName.LIGHT_WATER,
            description="Light pulse before a brief water spray.",
            actions=[light("burst"), water(1.2)],
        ),
        StrategyDefinition(
            name=StrategyName.SOUND_LIGHT_WATER,
            description="Short sound cue, light pulse, then bounded water spray.",
            actions=[sound("chirp", 0.5), light("burst"), water(1.2)],
        ),
        StrategyDefinition(
            name=StrategyName.LIGHT_SOUND_WATER_PAN,
            description="Light, sound, brief water, and a small preset pan assist.",
            actions=[light("burst"), sound("chirp", 0.6), water(1.0), pan("gate_track", 15)],
        ),
    ]
