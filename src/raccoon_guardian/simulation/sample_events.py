from __future__ import annotations

from datetime import UTC, datetime

from raccoon_guardian.domain.enums import DirectionOfTravel, TargetClass, ZoneId
from raccoon_guardian.domain.models import DetectionEvent, OutcomeMetrics


def default_night_scenario() -> list[DetectionEvent]:
    return [
        DetectionEvent(
            target_detected=True,
            target_class=TargetClass.RACCOON,
            confidence=0.92,
            zone_id=ZoneId.GATE_ENTRY,
            direction_of_travel=DirectionOfTravel.INBOUND,
            timestamp=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
            simulated_outcome=OutcomeMetrics(
                retreat_detected=True,
                seconds_to_exit_zone=18.0,
                returned_within_10_min=False,
                returned_same_night=True,
                nuisance_score=0.4,
            ),
        ),
        DetectionEvent(
            target_detected=True,
            target_class=TargetClass.CAT,
            confidence=0.89,
            zone_id=ZoneId.GATE_ENTRY,
            direction_of_travel=DirectionOfTravel.LATERAL,
            timestamp=datetime(2026, 1, 15, 2, 25, tzinfo=UTC),
            is_pet=True,
            simulated_outcome=OutcomeMetrics(false_positive=True, nuisance_score=0.0),
        ),
        DetectionEvent(
            target_detected=True,
            target_class=TargetClass.PERSON,
            confidence=0.98,
            zone_id=ZoneId.BACKYARD_PROTECTED,
            direction_of_travel=DirectionOfTravel.INBOUND,
            timestamp=datetime(2026, 1, 15, 2, 35, tzinfo=UTC),
            is_human=True,
            simulated_outcome=OutcomeMetrics(false_positive=True, nuisance_score=0.0),
        ),
        DetectionEvent(
            target_detected=True,
            target_class=TargetClass.RACCOON,
            confidence=0.95,
            zone_id=ZoneId.GATE_ENTRY,
            direction_of_travel=DirectionOfTravel.INBOUND,
            timestamp=datetime(2026, 1, 15, 2, 55, tzinfo=UTC),
            simulated_outcome=OutcomeMetrics(
                retreat_detected=True,
                seconds_to_exit_zone=10.0,
                returned_within_10_min=False,
                returned_same_night=False,
                nuisance_score=0.5,
            ),
        ),
    ]
