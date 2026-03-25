from __future__ import annotations

from raccoon_guardian.domain.enums import TargetClass
from raccoon_guardian.domain.models import DetectionEvent

PET_CLASSES = {TargetClass.CAT, TargetClass.DOG}


def is_human_detection(detection: DetectionEvent) -> bool:
    return detection.is_human or detection.target_class == TargetClass.PERSON


def is_pet_detection(detection: DetectionEvent) -> bool:
    return detection.is_pet or detection.target_class in PET_CLASSES
