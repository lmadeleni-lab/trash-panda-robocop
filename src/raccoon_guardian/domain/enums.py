from __future__ import annotations

from enum import StrEnum


class SystemState(StrEnum):
    DISARMED = "DISARMED"
    IDLE = "IDLE"
    DETECTING = "DETECTING"
    DECIDING = "DECIDING"
    ACTING = "ACTING"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"


class ZoneId(StrEnum):
    GATE_ENTRY = "gate_entry"
    BACKYARD_PROTECTED = "backyard_protected"
    OUTSIDE = "outside"


class TargetClass(StrEnum):
    RACCOON = "raccoon"
    CAT = "cat"
    DOG = "dog"
    BEAR = "bear"
    PERSON = "person"
    UNKNOWN = "unknown"


class DirectionOfTravel(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    LATERAL = "lateral"
    UNKNOWN = "unknown"


class ActionType(StrEnum):
    LIGHT = "light"
    SOUND = "sound"
    WATER = "water"
    PAN = "pan"
    STOP_ALL = "stop_all"


class StrategyName(StrEnum):
    LIGHT_ONLY = "LIGHT_ONLY"
    LIGHT_SOUND = "LIGHT_SOUND"
    WATER_ONLY = "WATER_ONLY"
    LIGHT_WATER = "LIGHT_WATER"
    SOUND_LIGHT_WATER = "SOUND_LIGHT_WATER"
    LIGHT_SOUND_WATER_PAN = "LIGHT_SOUND_WATER_PAN"
