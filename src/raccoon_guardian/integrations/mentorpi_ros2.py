from __future__ import annotations

from pydantic import BaseModel, Field


class MentorPiRosTopicConfig(BaseModel):
    controller_cmd_vel_topic: str = "/controller/cmd_vel"
    app_cmd_vel_topic: str = "/cmd_vel"
    motor_topic: str = "ros_robot_controller/set_motor"
    servo_topic: str = "ros_robot_controller/bus_servo/set_state"
    pose_topic: str = "set_pose"


class MentorPiMotionLimits(BaseModel):
    max_linear_m_s: float = Field(default=0.2, ge=0.0, le=1.0)
    max_angular_rad_s: float = Field(default=0.5, ge=0.0, le=2.0)
    max_duration_s: float = Field(default=3.0, gt=0.0, le=10.0)


class BoundedPatrolCommand(BaseModel):
    linear_m_s: float = Field(default=0.0)
    angular_rad_s: float = Field(default=0.0)
    duration_s: float = Field(default=1.0, gt=0.0)
    reason: str = "patrol"


class MentorPiRos2Bridge:
    """Builds bounded ROS2 command payloads for a MentorPi-style rover.

    This is intentionally transport-agnostic so we can wire it to actual ROS2
    publishers later without taking a hard dependency on rclpy in the MVP.
    """

    def __init__(
        self,
        *,
        topics: MentorPiRosTopicConfig | None = None,
        limits: MentorPiMotionLimits | None = None,
    ) -> None:
        self.topics = topics or MentorPiRosTopicConfig()
        self.limits = limits or MentorPiMotionLimits()

    def build_patrol_command(self, command: BoundedPatrolCommand) -> dict[str, object]:
        linear_m_s = min(
            max(command.linear_m_s, -self.limits.max_linear_m_s),
            self.limits.max_linear_m_s,
        )
        angular_rad_s = min(
            max(command.angular_rad_s, -self.limits.max_angular_rad_s),
            self.limits.max_angular_rad_s,
        )
        duration_s = min(command.duration_s, self.limits.max_duration_s)
        return {
            "topic": self.topics.controller_cmd_vel_topic,
            "message_type": "geometry_msgs/msg/Twist",
            "payload": {
                "linear": {"x": linear_m_s, "y": 0.0, "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": angular_rad_s},
            },
            "duration_s": duration_s,
            "reason": command.reason,
        }

    def build_safe_stop_command(self) -> dict[str, object]:
        return self.build_patrol_command(
            BoundedPatrolCommand(
                linear_m_s=0.0,
                angular_rad_s=0.0,
                duration_s=0.5,
                reason="safe_stop",
            )
        )

    def build_pan_command(
        self,
        *,
        servo_id: int,
        position: int,
        duration_ms: int = 500,
    ) -> dict[str, object]:
        bounded_duration_ms = min(max(duration_ms, 100), 2_000)
        return {
            "topic": self.topics.servo_topic,
            "message_type": "SetBusServoState",
            "payload": {
                "servo_id": servo_id,
                "position": position,
                "duration_ms": bounded_duration_ms,
            },
        }

    def telemetry_topics(self) -> list[str]:
        return [
            self.topics.controller_cmd_vel_topic,
            self.topics.app_cmd_vel_topic,
            self.topics.motor_topic,
            self.topics.servo_topic,
            self.topics.pose_topic,
        ]
