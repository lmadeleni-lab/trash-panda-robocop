from __future__ import annotations

from raccoon_guardian.integrations.mentorpi_ros2 import (
    BoundedPatrolCommand,
    MentorPiRos2Bridge,
)


def test_mentorpi_bridge_clamps_patrol_motion() -> None:
    bridge = MentorPiRos2Bridge()

    command = bridge.build_patrol_command(
        BoundedPatrolCommand(
            linear_m_s=0.8,
            angular_rad_s=1.2,
            duration_s=20.0,
            reason="guard_round",
        )
    )

    assert command["topic"] == "/controller/cmd_vel"
    payload = command["payload"]
    assert isinstance(payload, dict)
    assert payload["linear"]["x"] == 0.2
    assert payload["angular"]["z"] == 0.5
    assert command["duration_s"] == 3.0


def test_mentorpi_bridge_pan_command_is_bounded() -> None:
    bridge = MentorPiRos2Bridge()
    command = bridge.build_pan_command(servo_id=3, position=650, duration_ms=20)

    assert command["topic"] == "ros_robot_controller/bus_servo/set_state"
    payload = command["payload"]
    assert isinstance(payload, dict)
    assert payload["duration_ms"] == 100
