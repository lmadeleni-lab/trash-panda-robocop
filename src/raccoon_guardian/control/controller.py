from __future__ import annotations

from datetime import UTC, datetime

from raccoon_guardian.actuators.base import ActuatorHub
from raccoon_guardian.config import AppConfig
from raccoon_guardian.control.cooldown import CooldownGate
from raccoon_guardian.control.scheduler import ArmingScheduler
from raccoon_guardian.domain.enums import ActionType, StrategyName, SystemState, TargetClass, ZoneId
from raccoon_guardian.domain.models import (
    ActuationResult,
    BoundedAction,
    DecisionTraceEntry,
    DetectionEvent,
    EncounterRecord,
    SafetyDecision,
)
from raccoon_guardian.logging import get_logger
from raccoon_guardian.safety.policy import SafetyPolicy
from raccoon_guardian.state_machine import SystemStateMachine
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog


class Controller:
    def __init__(
        self,
        config: AppConfig,
        repository: EventRepository,
        actuator_hub: ActuatorHub,
        strategy_catalog: StrategyCatalog,
    ) -> None:
        initial_state = SystemState.IDLE if config.armed_default else SystemState.DISARMED
        self.state_machine = SystemStateMachine(initial_state)
        self.config = config
        self.repository = repository
        self.actuator_hub = actuator_hub
        self.strategy_catalog = strategy_catalog
        self.policy = SafetyPolicy(config)
        self.scheduler = ArmingScheduler(config.safety)
        self.cooldown = CooldownGate(config.safety.cooldown_s)
        self.selected_strategy = config.selected_strategy
        self.last_action_at: datetime | None = None
        self.armed = config.armed_default
        self.logger = get_logger(__name__)

    @property
    def state(self) -> SystemState:
        return self.state_machine.state

    def arm(self) -> dict[str, str]:
        self.armed = True
        if self.state_machine.state == SystemState.DISARMED:
            self.state_machine.transition(SystemState.IDLE)
        return {"state": self.state.value}

    def disarm(self) -> dict[str, str]:
        self.armed = False
        if self.state_machine.state != SystemState.DISARMED:
            self.actuator_hub.stop_all()
            self.state_machine.state = SystemState.DISARMED
        return {"state": self.state.value}

    def select_strategy(self, strategy_name: StrategyName) -> StrategyName:
        self.strategy_catalog.get(strategy_name)
        self.selected_strategy = strategy_name
        return strategy_name

    def strategy_for_target(self, target_class: TargetClass) -> StrategyName:
        return self.strategy_catalog.recommended_strategy_for_target(
            target_class,
            fallback=self.selected_strategy,
            overrides=self.config.target_strategy_preferences,
        )

    def _refresh_cooldown(self, now: datetime) -> None:
        if self.state_machine.state == SystemState.COOLDOWN and self.cooldown.is_ready(
            now, self.last_action_at
        ):
            self.state_machine.transition(SystemState.IDLE)

    def _disarmed_decision(self) -> SafetyDecision:
        return SafetyDecision(
            allowed=False,
            action_plan=[],
            trace=[
                DecisionTraceEntry(
                    rule="armed_state",
                    allowed=False,
                    message="System is disarmed; actuation denied.",
                )
            ],
        )

    @staticmethod
    def _requested_safe_park(decision: SafetyDecision) -> bool:
        return any(
            entry.rule == "hazard_hide_mode" and not entry.allowed for entry in decision.trace
        )

    def process_detection(self, detection: DetectionEvent) -> EncounterRecord:
        self._refresh_cooldown(detection.timestamp)
        state_before = self.state
        self.logger.info(
            "processing detection",
            extra={
                "context": {
                    "event_id": detection.event_id,
                    "target_class": detection.target_class.value,
                    "zone_id": detection.zone_id.value,
                    "confidence": detection.confidence,
                    "is_human": detection.is_human,
                    "is_pet": detection.is_pet,
                    "state_before": state_before.value,
                }
            },
        )
        if not self.armed:
            record = EncounterRecord(
                detection=detection,
                state_before=state_before,
                state_after=SystemState.DISARMED,
                chosen_strategy=None,
                decision=self._disarmed_decision(),
                outcome=detection.simulated_outcome,
            )
            self.repository.record_encounter(record)
            self.logger.info(
                "detection denied because system is disarmed",
                extra={
                    "context": {
                        "event_id": detection.event_id,
                        "encounter_id": record.encounter_id,
                    }
                },
            )
            return record

        try:
            if self.state_machine.state == SystemState.IDLE:
                self.state_machine.transition(SystemState.DETECTING)
            elif self.state_machine.state == SystemState.COOLDOWN:
                self.state_machine.transition(SystemState.DETECTING)

            self.state_machine.transition(SystemState.DECIDING)
            strategy_name = self.strategy_for_target(detection.target_class)
            strategy = self.strategy_catalog.get(strategy_name)
            decision = self.policy.evaluate(
                detection,
                strategy.actions,
                now=detection.timestamp,
                last_action_at=self.last_action_at,
            )

            if not decision.allowed:
                if self._requested_safe_park(decision):
                    self.actuator_hub.stop_all()
                    self.armed = False
                    self.state_machine.state = SystemState.DISARMED
                else:
                    self.state_machine.transition(SystemState.IDLE)
                record = EncounterRecord(
                    detection=detection,
                    state_before=state_before,
                    state_after=self.state,
                    chosen_strategy=strategy.name,
                    decision=decision,
                    outcome=detection.simulated_outcome,
                )
                self.repository.record_encounter(record)
                self.logger.info(
                    "detection evaluated without actuation",
                    extra={
                        "context": {
                            "event_id": detection.event_id,
                            "encounter_id": record.encounter_id,
                            "chosen_strategy": strategy.name.value,
                            "allowed": False,
                            "state_after": self.state.value,
                        }
                    },
                )
                return record

            self.state_machine.transition(SystemState.ACTING)
            results = [self.actuator_hub.execute(action) for action in decision.action_plan]
            self.last_action_at = detection.timestamp
            self.state_machine.transition(SystemState.COOLDOWN)
            record = EncounterRecord(
                detection=detection,
                state_before=state_before,
                state_after=self.state,
                chosen_strategy=strategy.name,
                decision=decision,
                action_results=results,
                outcome=detection.simulated_outcome,
            )
            self.repository.record_encounter(record)
            self.logger.info(
                "detection acted successfully",
                extra={
                    "context": {
                        "event_id": detection.event_id,
                        "encounter_id": record.encounter_id,
                        "chosen_strategy": strategy.name.value,
                        "action_count": len(results),
                        "state_after": self.state.value,
                    }
                },
            )
            return record
        except Exception as exc:
            self.logger.exception("controller failure")
            self.state_machine.state = SystemState.ERROR
            raise RuntimeError("controller processing failed") from exc

    def run_test_actuation(
        self,
        strategy_name: StrategyName,
        zone_id: ZoneId = ZoneId.GATE_ENTRY,
    ) -> EncounterRecord:
        detection = DetectionEvent(
            target_detected=True,
            target_class=TargetClass.RACCOON,
            confidence=0.99,
            zone_id=zone_id,
            timestamp=datetime.now(UTC),
        )
        previous_strategy = self.selected_strategy
        self.selected_strategy = strategy_name
        try:
            return self.process_detection(detection)
        finally:
            self.selected_strategy = previous_strategy

    def run_guard_round(
        self, presets: list[str], *, now: datetime | None = None
    ) -> list[ActuationResult]:
        current_time = now or datetime.now(UTC)
        if self.config.safety.manual_disable:
            msg = "guard rounds are disabled while manual disable is active"
            raise ValueError(msg)
        if not self.scheduler.is_armed_time(current_time):
            msg = "guard rounds may only run during the configured arm window"
            raise ValueError(msg)
        results: list[ActuationResult] = []
        for preset in presets:
            results.append(
                self.actuator_hub.execute(
                    BoundedAction(action_type=ActionType.PAN, preset=preset, degrees=0)
                )
            )
        self.logger.info(
            "guard round executed",
            extra={"context": {"presets": presets, "result_count": len(results)}},
        )
        return results
