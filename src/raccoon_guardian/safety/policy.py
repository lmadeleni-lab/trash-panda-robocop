from __future__ import annotations

from datetime import datetime, timedelta

from raccoon_guardian.config import AppConfig
from raccoon_guardian.domain.enums import ActionType
from raccoon_guardian.domain.models import (
    BoundedAction,
    DecisionTraceEntry,
    DetectionEvent,
    SafetyDecision,
)
from raccoon_guardian.safety.geofence import is_zone_deterrence_enabled
from raccoon_guardian.safety.human_pet_exclusion import is_human_detection, is_pet_detection


class SafetyPolicy:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def evaluate(
        self,
        detection: DetectionEvent,
        proposed_actions: list[BoundedAction],
        *,
        now: datetime,
        last_action_at: datetime | None,
    ) -> SafetyDecision:
        trace: list[DecisionTraceEntry] = []

        if not detection.target_detected:
            trace.append(
                DecisionTraceEntry(
                    rule="target_detected",
                    allowed=False,
                    message="No actionable target was present.",
                )
            )
            return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="target_detected",
                allowed=True,
                message="Structured target event received.",
            )
        )

        if self.config.safety.manual_disable:
            trace.append(
                DecisionTraceEntry(
                    rule="manual_disable",
                    allowed=False,
                    message="Manual disable is active.",
                )
            )
            return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="manual_disable",
                allowed=True,
                message="Manual disable is not active.",
            )
        )

        if is_human_detection(detection):
            trace.append(
                DecisionTraceEntry(
                    rule="human_exclusion",
                    allowed=False,
                    message="Target classified as human; actuation denied.",
                )
            )
            return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="human_exclusion",
                allowed=True,
                message="Target is not classified as human.",
            )
        )

        if is_pet_detection(detection):
            trace.append(
                DecisionTraceEntry(
                    rule="pet_exclusion",
                    allowed=False,
                    message="Target classified as pet; actuation denied.",
                )
            )
            return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="pet_exclusion",
                allowed=True,
                message="Target is not classified as pet.",
            )
        )

        if not self.config.safety.is_within_arm_window(now):
            trace.append(
                DecisionTraceEntry(
                    rule="arm_window",
                    allowed=False,
                    message="Current time falls outside configured arm hours.",
                )
            )
            return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="arm_window",
                allowed=True,
                message="Current time falls inside the arm window.",
            )
        )

        if not is_zone_deterrence_enabled(self.config, detection.zone_id):
            trace.append(
                DecisionTraceEntry(
                    rule="zone_geofence",
                    allowed=False,
                    message=f"Zone {detection.zone_id.value} is not deterrence-enabled.",
                )
            )
            return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="zone_geofence",
                allowed=True,
                message=f"Zone {detection.zone_id.value} is deterrence-enabled.",
            )
        )

        if last_action_at is not None:
            elapsed = now - last_action_at
            if elapsed < timedelta(seconds=self.config.safety.cooldown_s):
                trace.append(
                    DecisionTraceEntry(
                        rule="cooldown",
                        allowed=False,
                        message="Cooldown window has not elapsed.",
                    )
                )
                return SafetyDecision(allowed=False, action_plan=[], trace=trace)
        trace.append(
            DecisionTraceEntry(
                rule="cooldown",
                allowed=True,
                message="Cooldown gate satisfied.",
            )
        )

        bounded_actions: list[BoundedAction] = []
        for action in proposed_actions:
            bounded_action = action.model_copy(deep=True)
            if (
                bounded_action.action_type == ActionType.WATER
                and bounded_action.duration_s is not None
            ):
                if bounded_action.duration_s > self.config.safety.max_water_duration_s:
                    bounded_action.duration_s = self.config.safety.max_water_duration_s
                    trace.append(
                        DecisionTraceEntry(
                            rule="max_water_duration",
                            allowed=True,
                            message="Water duration exceeded cap and was clamped.",
                        )
                    )
            if (
                bounded_action.action_type == ActionType.SOUND
                and bounded_action.duration_s is not None
            ):
                if bounded_action.duration_s > self.config.safety.max_sound_duration_s:
                    bounded_action.duration_s = self.config.safety.max_sound_duration_s
                    trace.append(
                        DecisionTraceEntry(
                            rule="max_sound_duration",
                            allowed=True,
                            message="Sound duration exceeded cap and was clamped.",
                        )
                    )
            if bounded_action.action_type == ActionType.PAN and bounded_action.degrees is not None:
                if abs(bounded_action.degrees) > self.config.safety.max_pan_degrees:
                    bounded_action.degrees = min(
                        max(bounded_action.degrees, -self.config.safety.max_pan_degrees),
                        self.config.safety.max_pan_degrees,
                    )
                    trace.append(
                        DecisionTraceEntry(
                            rule="max_pan_degrees",
                            allowed=True,
                            message="Pan degrees exceeded cap and were clamped.",
                        )
                    )
            if bounded_action.zone is None:
                bounded_action.zone = detection.zone_id
            bounded_actions.append(bounded_action)

        trace.append(
            DecisionTraceEntry(
                rule="final_decision",
                allowed=True,
                message="All immutable safety gates passed.",
            )
        )
        return SafetyDecision(allowed=True, action_plan=bounded_actions, trace=trace)
