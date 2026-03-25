from __future__ import annotations

from raccoon_guardian.domain.enums import TargetClass
from raccoon_guardian.domain.models import DetectionEvent

HAZARD_CLASSES = {TargetClass.BEAR}


def is_hazard_detection(detection: DetectionEvent) -> bool:
    return detection.target_class in HAZARD_CLASSES
