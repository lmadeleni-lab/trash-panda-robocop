from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from raccoon_guardian.config import AppConfig, PatrolPathConfig
from raccoon_guardian.domain.enums import FleetBotMode, MobilityState, TargetClass, ZoneId
from raccoon_guardian.domain.models import (
    FleetBotHeartbeat,
    FleetBotStatus,
    FleetCoordinationPlan,
    PatrolCommand,
    PatrolExecutionResult,
    PatrolPath,
    PatrolWaypoint,
    RecoveryAction,
    RecoveryPlan,
    SentryStatus,
    ZoneCoverageAssignment,
)
from raccoon_guardian.integrations.mentorpi_ros2 import (
    BoundedPatrolCommand,
    MentorPiRos2Bridge,
)
from raccoon_guardian.logging import get_logger
from raccoon_guardian.storage.repository import EventRepository


class FleetCoordinator:
    def __init__(
        self,
        config: AppConfig,
        repository: EventRepository,
        bridge: MentorPiRos2Bridge | None = None,
    ) -> None:
        self.config = config
        self.repository = repository
        self.bridge = bridge or MentorPiRos2Bridge()
        self.logger = get_logger(__name__)
        self._heartbeats: dict[str, FleetBotHeartbeat] = {}
        self._current_plan = FleetCoordinationPlan(
            local_bot_id=config.fleet.local_bot_id,
            area_assignments=[],
        )
        self._last_patrol_at: datetime | None = None
        self._last_patrol_plan: PatrolExecutionResult | None = None
        self._regroup_reason: str | None = None

    def _bot_configs(self) -> list[Any]:
        configured = self.config.fleet.bots
        if configured:
            return configured
        return [
            type(
                "LocalBot",
                (),
                {
                    "bot_id": self.config.fleet.local_bot_id,
                    "display_name": self.config.fleet.local_bot_id,
                    "assigned_areas": [ZoneId.GATE_ENTRY, ZoneId.BACKYARD_PROTECTED],
                    "home_path_id": self.config.sentry.default_path_id,
                    "active": True,
                },
            )()
        ]

    def _bot_config_by_id(self, bot_id: str) -> Any | None:
        return next((bot for bot in self._bot_configs() if bot.bot_id == bot_id), None)

    def record_heartbeat(self, heartbeat: FleetBotHeartbeat) -> FleetBotHeartbeat:
        self._heartbeats[heartbeat.bot_id] = heartbeat
        self.logger.info(
            "fleet heartbeat recorded",
            extra={
                "context": {
                    "bot_id": heartbeat.bot_id,
                    "mobility_state": heartbeat.mobility_state.value,
                    "mode": heartbeat.mode.value,
                    "battery_percent": heartbeat.battery_percent,
                    "water_percent": heartbeat.water_percent,
                }
            },
        )
        return heartbeat

    def _zone_pressure(self) -> Counter[str]:
        recent = self.repository.list_encounters(limit=100)
        pressure: Counter[str] = Counter()
        for encounter in recent:
            weight = 1
            if encounter.detection.target_class == TargetClass.RACCOON:
                weight += 1
            if encounter.outcome and encounter.outcome.returned_same_night:
                weight += 2
            pressure[encounter.detection.zone_id.value] += weight
        return pressure

    def _active_bots(self) -> list[tuple[str, str, list[ZoneId], bool]]:
        return [
            (bot.bot_id, bot.display_name, bot.assigned_areas, bot.active)
            for bot in self._bot_configs()
            if bot.active
        ]

    def _heartbeat_is_recent(self, heartbeat: FleetBotHeartbeat | None, now: datetime) -> bool:
        return heartbeat is not None and (now - heartbeat.reported_at) <= timedelta(minutes=10)

    def _recent_heartbeat(self, bot_id: str, now: datetime) -> FleetBotHeartbeat | None:
        heartbeat = self._heartbeats.get(bot_id)
        if self._heartbeat_is_recent(heartbeat, now):
            return heartbeat
        return None

    def _resource_state(
        self,
        heartbeat: FleetBotHeartbeat | None,
        now: datetime,
    ) -> tuple[str, str | None]:
        if heartbeat is None:
            return ("telemetry_unknown", "no recent fleet telemetry received")
        resources = self.config.fleet.resources
        if not self._heartbeat_is_recent(heartbeat, now):
            return (
                "telemetry_stale",
                "telemetry is stale; keep this bot out of takeover decisions",
            )
        if heartbeat.mobility_state == MobilityState.STUCK:
            return ("stuck", "mobility is stuck; regroup and hand off coverage")
        if heartbeat.battery_percent <= resources.critical_battery_threshold_percent:
            return ("critical_battery", "battery is critical; route this bot to recharge")
        if heartbeat.water_percent <= resources.critical_water_threshold_percent:
            return ("critical_water", "water reserve is critical; route this bot to refill")
        if heartbeat.battery_percent <= resources.low_battery_threshold_percent:
            return ("low_battery", "battery is low; prefer another bot for perimeter takeover")
        if heartbeat.water_percent <= resources.low_water_threshold_percent:
            return ("low_water", "water reserve is low; prefer another bot for deterrence coverage")
        return ("nominal", None)

    def _can_accept_takeover(self, heartbeat: FleetBotHeartbeat | None, now: datetime) -> bool:
        if heartbeat is None:
            return True
        if not self._heartbeat_is_recent(heartbeat, now):
            return False
        resources = self.config.fleet.resources
        return (
            heartbeat.mobility_state != MobilityState.STUCK
            and heartbeat.battery_percent >= resources.min_battery_for_patrol_percent
            and heartbeat.water_percent >= resources.min_water_for_deterrence_percent
        )

    def _resource_score(self, heartbeat: FleetBotHeartbeat | None, now: datetime) -> float:
        if heartbeat is None:
            return 100.0
        if not self._heartbeat_is_recent(heartbeat, now):
            return -1000.0
        score = heartbeat.battery_percent + heartbeat.water_percent
        if heartbeat.mobility_state == MobilityState.DEGRADED:
            score -= 25.0
        if heartbeat.mobility_state == MobilityState.STUCK:
            score -= 1000.0
        return score

    def _preferred_bot_for_zone(self, zone: ZoneId) -> str | None:
        for bot in self._bot_configs():
            if bot.active and zone in self._zone_candidates_for_bot(bot.assigned_areas):
                return str(bot.bot_id)
        return None

    def _zone_candidates_for_bot(self, assigned_areas: list[ZoneId]) -> list[ZoneId]:
        if assigned_areas:
            return assigned_areas
        return [ZoneId.GATE_ENTRY, ZoneId.BACKYARD_PROTECTED]

    def _select_path_for_zones(self, zones: list[ZoneId]) -> str | None:
        if not self.config.sentry.patrol_paths:
            return None
        desired = {zone.value for zone in zones}
        ranked: list[tuple[int, PatrolPathConfig]] = []
        for path in self.config.sentry.patrol_paths:
            path_zones = {waypoint.zone_id.value for waypoint in path.waypoints}
            ranked.append((len(path_zones & desired), path))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if ranked and ranked[0][0] > 0:
            return ranked[0][1].path_id
        return self.config.sentry.default_path_id or self.config.sentry.patrol_paths[0].path_id

    def compute_plan(self, now: datetime | None = None) -> FleetCoordinationPlan:
        plan_time = now or datetime.now(UTC)
        pressure = self._zone_pressure()
        sorted_zones = sorted(
            [ZoneId.GATE_ENTRY, ZoneId.BACKYARD_PROTECTED],
            key=lambda zone: pressure.get(zone.value, 0),
            reverse=True,
        )
        bots = self._active_bots()
        assignments: list[ZoneCoverageAssignment] = []
        coordination_notes: list[str] = []
        resource_notes: list[str] = []

        if self.config.fleet.prohibit_live_target_convergence:
            coordination_notes.append(
                "Bots may provide staggered zone observation coverage only; no multi-bot "
                "convergence on a live target."
            )

        if not bots:
            plan = FleetCoordinationPlan(
                created_at=plan_time,
                local_bot_id=self.config.fleet.local_bot_id,
                area_assignments=[],
                coordination_notes=coordination_notes,
                resource_notes=resource_notes,
            )
            self._current_plan = plan
            return plan

        for zone in sorted_zones:
            zone_assigned_candidates = [
                bot
                for bot in bots
                if zone in self._zone_candidates_for_bot(bot[2])
            ]
            zone_takeover_candidates = [
                bot
                for bot in bots
                if self._can_accept_takeover(
                    self._recent_heartbeat(bot[0], plan_time),
                    plan_time,
                )
            ]
            ranked_pool = (
                zone_assigned_candidates
                if any(
                    self._can_accept_takeover(self._recent_heartbeat(bot[0], plan_time), plan_time)
                    for bot in zone_assigned_candidates
                )
                else zone_takeover_candidates
            )
            if not ranked_pool:
                ranked_pool = zone_assigned_candidates or bots
            if not ranked_pool:
                break
            ranked_candidates = sorted(
                ranked_pool,
                key=lambda bot: self._resource_score(
                    self._recent_heartbeat(bot[0], plan_time),
                    plan_time,
                ),
                reverse=True,
            )
            primary = ranked_candidates[0][0]
            primary_heartbeat = self._recent_heartbeat(primary, plan_time)
            preferred_bot_id = self._preferred_bot_for_zone(zone)
            takeover_from_bot_id: str | None = None
            resource_note: str | None = None
            if preferred_bot_id and preferred_bot_id != primary:
                preferred_heartbeat = self._recent_heartbeat(preferred_bot_id, plan_time)
                if not self._can_accept_takeover(preferred_heartbeat, plan_time):
                    takeover_from_bot_id = preferred_bot_id
                    preferred_state, preferred_reason = self._resource_state(
                        preferred_heartbeat,
                        plan_time,
                    )
                    resource_note = (
                        f"{primary} extended coverage because {preferred_bot_id} "
                        f"is {preferred_state}"
                    )
                    if preferred_reason:
                        resource_notes.append(
                            f"{zone.value}: {primary} covering for {preferred_bot_id}; "
                            f"{preferred_reason}"
                        )
            elif primary_heartbeat and not self._can_accept_takeover(primary_heartbeat, plan_time):
                fallback = next(
                    (
                        bot_id
                        for bot_id, _display_name, areas, _active in ranked_candidates[1:]
                        if self._can_accept_takeover(
                            self._recent_heartbeat(bot_id, plan_time),
                            plan_time,
                        )
                    ),
                    None,
                )
                if fallback is not None:
                    takeover_from_bot_id = primary
                    primary = fallback
                    primary_state, primary_reason = self._resource_state(
                        primary_heartbeat,
                        plan_time,
                    )
                    resource_note = (
                        f"{fallback} extended coverage because {takeover_from_bot_id} "
                        f"is {primary_state}"
                    )
                    if primary_reason:
                        resource_notes.append(
                            f"{zone.value}: {fallback} covering for {takeover_from_bot_id}; "
                            f"{primary_reason}"
                        )
            supporters = [
                bot_id
                for bot_id, _display_name, areas, _active in ranked_candidates
                if bot_id != primary
                and zone in self._zone_candidates_for_bot(areas)
                and self._can_accept_takeover(self._recent_heartbeat(bot_id, plan_time), plan_time)
            ][: max(0, self.config.fleet.max_bots_per_zone_observation - 1)]
            assignments.append(
                ZoneCoverageAssignment(
                    zone_id=zone,
                    primary_bot_id=primary,
                    supporting_bot_ids=supporters,
                    note=(
                        "Use offset observation posts for different viewing angles on the zone, "
                        "not the target."
                    ),
                    takeover_from_bot_id=takeover_from_bot_id,
                    resource_note=resource_note,
                )
            )

        local_bot_tuple = next(
            (bot for bot in bots if bot[0] == self.config.fleet.local_bot_id),
            bots[0]
            if bots
            else (
                self.config.fleet.local_bot_id,
                self.config.fleet.local_bot_id,
                [],
                True,
            ),
        )
        local_assignments = [
            assignment.zone_id
            for assignment in assignments
            if assignment.primary_bot_id == self.config.fleet.local_bot_id
            or self.config.fleet.local_bot_id in assignment.supporting_bot_ids
        ]
        local_heartbeat = self._recent_heartbeat(self.config.fleet.local_bot_id, plan_time)
        local_resource_state, local_resource_reason = self._resource_state(
            local_heartbeat,
            plan_time,
        )
        local_bot_config = self._bot_config_by_id(self.config.fleet.local_bot_id)
        local_zones = local_assignments or self._zone_candidates_for_bot(local_bot_tuple[2])
        local_path_id = self._select_path_for_zones(local_zones)
        local_mode = FleetBotMode.PATROL

        if self._regroup_reason is not None:
            local_mode = FleetBotMode.REGROUP
        elif local_heartbeat and not self._can_accept_takeover(local_heartbeat, plan_time):
            local_mode = FleetBotMode.REGROUP
            if local_bot_config and local_bot_config.home_path_id:
                local_path_id = local_bot_config.home_path_id
            if local_resource_reason:
                resource_notes.append(
                    f"{self.config.fleet.local_bot_id}: {local_resource_reason}"
                )

        regroup_requested = self._regroup_reason is not None or local_mode == FleetBotMode.REGROUP
        if local_heartbeat and local_resource_state in {
            "critical_battery",
            "critical_water",
            "stuck",
        }:
            regroup_requested = True
        plan = FleetCoordinationPlan(
            created_at=plan_time,
            regroup_requested=regroup_requested,
            regroup_reason=self._regroup_reason or local_resource_reason,
            regroup_preset=self.config.sentry.regroup_preset if regroup_requested else None,
            local_bot_id=self.config.fleet.local_bot_id,
            area_assignments=assignments,
            local_path_id=local_path_id,
            local_mode=local_mode,
            coordination_notes=coordination_notes,
            resource_notes=resource_notes,
        )
        self._current_plan = plan
        return plan

    def request_regroup(self, reason: str, now: datetime | None = None) -> FleetCoordinationPlan:
        self._regroup_reason = reason
        return self.compute_plan(now=now)

    def clear_regroup(self) -> None:
        self._regroup_reason = None

    def _path_model(self, path_id: str) -> PatrolPath:
        path = self.config.path_map()[path_id]
        return PatrolPath(
            path_id=path.path_id,
            display_name=path.display_name,
            area_tags=path.area_tags,
            waypoints=[
                PatrolWaypoint(
                    waypoint_id=waypoint.waypoint_id,
                    zone_id=waypoint.zone_id,
                    observation_preset=waypoint.observation_preset,
                    linear_m_s=waypoint.linear_m_s,
                    angular_rad_s=waypoint.angular_rad_s,
                    move_duration_s=waypoint.move_duration_s,
                    dwell_s=waypoint.dwell_s,
                    servo_id=waypoint.servo_id,
                    servo_position=waypoint.servo_position,
                )
                for waypoint in path.waypoints
            ],
        )

    def run_local_patrol(self, now: datetime | None = None) -> PatrolExecutionResult:
        run_time = now or datetime.now(UTC)
        plan = self.compute_plan(now=run_time)
        if plan.local_path_id is None:
            msg = "no sentry patrol path is configured for the local bot"
            raise ValueError(msg)
        path = self._path_model(plan.local_path_id)
        commands: list[PatrolCommand] = []
        for waypoint in path.waypoints:
            movement = self.bridge.build_patrol_command(
                BoundedPatrolCommand(
                    linear_m_s=waypoint.linear_m_s,
                    angular_rad_s=waypoint.angular_rad_s,
                    duration_s=waypoint.move_duration_s,
                    reason=f"patrol:{path.path_id}:{waypoint.waypoint_id}",
                )
            )
            pan = self.bridge.build_pan_command(
                servo_id=waypoint.servo_id,
                position=waypoint.servo_position,
            )
            commands.append(
                PatrolCommand(
                    step_id=waypoint.waypoint_id,
                    movement_command=movement,
                    pan_command=pan,
                    dwell_s=waypoint.dwell_s,
                    zone_id=waypoint.zone_id,
                    observation_preset=waypoint.observation_preset,
                )
            )
        result = PatrolExecutionResult(
            bot_id=self.config.fleet.local_bot_id,
            path_id=path.path_id,
            created_at=run_time,
            commands=commands,
            mode=plan.local_mode,
        )
        self._last_patrol_at = run_time
        self._last_patrol_plan = result
        self.logger.info(
            "local sentry patrol planned",
            extra={
                "context": {
                    "bot_id": result.bot_id,
                    "path_id": result.path_id,
                    "command_count": len(result.commands),
                    "mode": result.mode.value,
                }
            },
        )
        return result

    def recovery_plan_for(self, bot_id: str) -> RecoveryPlan:
        heartbeat = self._heartbeats.get(bot_id)
        if heartbeat is None:
            return RecoveryPlan(
                bot_id=bot_id,
                mobility_state=MobilityState.DEGRADED,
                should_regroup=True,
                reason="no recent heartbeat is available for this bot",
                actions=[],
            )
        if heartbeat.mobility_state != MobilityState.STUCK:
            return RecoveryPlan(
                bot_id=bot_id,
                mobility_state=heartbeat.mobility_state,
                should_regroup=False,
                reason="mobility is nominal enough to continue patrol or observation",
                actions=[],
            )
        actions = [
            RecoveryAction(action="safe_stop", command=self.bridge.build_safe_stop_command()),
            RecoveryAction(
                action="short_reverse",
                command=self.bridge.build_patrol_command(
                    BoundedPatrolCommand(
                        linear_m_s=-0.12,
                        angular_rad_s=0.0,
                        duration_s=self.config.recovery.reverse_duration_s,
                        reason="recovery_reverse",
                    )
                ),
            ),
            RecoveryAction(
                action="slight_turn",
                command=self.bridge.build_patrol_command(
                    BoundedPatrolCommand(
                        linear_m_s=0.0,
                        angular_rad_s=0.35,
                        duration_s=self.config.recovery.turn_duration_s,
                        reason="recovery_turn",
                    )
                ),
            ),
            RecoveryAction(action="safe_stop", command=self.bridge.build_safe_stop_command()),
        ]
        return RecoveryPlan(
            bot_id=bot_id,
            mobility_state=heartbeat.mobility_state,
            should_regroup=True,
            reason="bot reported a stuck condition; issue bounded recovery motions then regroup",
            actions=actions,
        )

    def sentry_status(self, now: datetime, next_patrol_local: str | None) -> SentryStatus:
        return SentryStatus(
            enabled=self.config.sentry.enabled,
            local_bot_id=self.config.fleet.local_bot_id,
            selected_path_id=self._current_plan.local_path_id,
            last_patrol_local=(
                self._last_patrol_at.astimezone(self.config.safety.tzinfo).isoformat()
                if self._last_patrol_at
                else None
            ),
            next_patrol_local=next_patrol_local,
            available_paths=[
                self._path_model(path.path_id) for path in self.config.sentry.patrol_paths
            ],
        )

    def fleet_status(self, now: datetime) -> list[FleetBotStatus]:
        statuses: list[FleetBotStatus] = []
        for bot_id, display_name, assigned_areas, active in self._active_bots():
            heartbeat = self._heartbeats.get(bot_id)
            if heartbeat and (now - heartbeat.reported_at) > timedelta(minutes=10):
                mode = FleetBotMode.OFFLINE
                mobility_state = heartbeat.mobility_state
            elif heartbeat:
                mode = heartbeat.mode
                mobility_state = heartbeat.mobility_state
            else:
                mode = FleetBotMode.OFFLINE
                mobility_state = MobilityState.DEGRADED
            statuses.append(
                FleetBotStatus(
                    bot_id=bot_id,
                    display_name=display_name,
                    active=active,
                    assigned_areas=assigned_areas,
                    current_zone=heartbeat.current_zone if heartbeat else None,
                    current_path_id=heartbeat.current_path_id if heartbeat else None,
                    battery_percent=heartbeat.battery_percent if heartbeat else None,
                    water_percent=heartbeat.water_percent if heartbeat else None,
                    mobility_state=mobility_state,
                    mode=mode,
                    resource_state=self._resource_state(heartbeat, now)[0],
                    can_accept_takeover=self._can_accept_takeover(heartbeat, now),
                    needs_refill=bool(
                        heartbeat
                        and heartbeat.water_percent
                        < self.config.fleet.resources.min_water_for_deterrence_percent
                    ),
                    needs_recharge=bool(
                        heartbeat
                        and heartbeat.battery_percent
                        < self.config.fleet.resources.min_battery_for_patrol_percent
                    ),
                    takeover_reason=self._resource_state(heartbeat, now)[1],
                    last_seen_at=heartbeat.reported_at.isoformat() if heartbeat else None,
                )
            )
        return statuses
