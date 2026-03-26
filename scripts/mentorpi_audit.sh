#!/usr/bin/env bash
set -euo pipefail

echo "== trash-panda Robocop MentorPi audit =="
echo "timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

echo "== host info =="
uname -a || true
echo

echo "== docker containers =="
if command -v docker >/dev/null 2>&1; then
  docker ps -a || true
else
  echo "docker not found"
fi
echo

echo "== vendor services =="
if command -v systemctl >/dev/null 2>&1; then
  systemctl status start_node.service --no-pager || true
else
  echo "systemctl not found"
fi
echo

echo "== ros2 topics =="
if command -v ros2 >/dev/null 2>&1; then
  ros2 topic list || true
else
  echo "ros2 not found on host path"
fi
echo

echo "== mentorpi workspace hints =="
for path in \
  "$HOME/docker" \
  "$HOME/MentorPi" \
  "$HOME/ros2_ws" \
  "/home/ubuntu/ros2_ws/src" \
  "/home/ubuntu/ros2_ws/src/driver" \
  "/home/ubuntu/ros2_ws/src/peripherals"; do
  if [ -e "$path" ]; then
    echo "found: $path"
    ls "$path" | head -50 || true
    echo
  fi
done

echo "== likely reusable control topics =="
cat <<'EOF'
/controller/cmd_vel
/cmd_vel
ros_robot_controller/set_motor
ros_robot_controller/bus_servo/set_state
set_pose
EOF
echo

echo "== audit done =="
