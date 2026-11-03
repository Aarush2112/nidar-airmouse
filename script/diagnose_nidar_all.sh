#!/usr/bin/env bash

set +u

source /opt/ros/jazzy/setup.bash

LOG_DIR="$HOME/NIDAR AirMouse/logs/vio"
OUT="$LOG_DIR/diagnostics_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "$LOG_DIR"
exec > >(tee "$OUT") 2>&1

section() {
    printf '\n\n========== %s ==========\n' "$1"
}

check_topic() {
    local topic="$1"
    local field="${2:-}"

    section "TOPIC: $topic ${field:+FIELD: $field}"
    if [[ -n "$field" ]]; then
        timeout 7s ros2 topic echo "$topic" --once --field "$field" \
            || echo "No message received, timeout, or command failed."
    else
        timeout 7s ros2 topic echo "$topic" --once \
            || echo "No message received, timeout, or command failed."
    fi
}

check_rate() {
    local topic="$1"
    section "RATE: $topic (about 4 seconds)"
    timeout 5s ros2 topic hz "$topic" \
        || echo "Rate check timed out or topic unavailable."
}

section "SYSTEM"
date
uname -a
ros2 doctor --report 2>&1 | head -n 70

section "ROS 2 NODES"
ros2 node list

section "RELEVANT TOPICS"
ros2 topic list | grep -E \
    'camera/camera/(infra[12]/(image_rect_raw|camera_info)|imu)|rgbd_image|/odom($|_info)|/tf' \
    || true

section "LEFT CAMERA INFO"
check_topic /camera/camera/infra1/camera_info

section "RIGHT CAMERA INFO"
check_topic /camera/camera/infra2/camera_info

section "LEFT IMAGE HEADER"
check_topic /camera/camera/infra1/image_rect_raw header

section "RIGHT IMAGE HEADER"
check_topic /camera/camera/infra2/image_rect_raw header

section "SYNC OUTPUT: /rgbd_image LEFT CAMERA INFO"
check_topic /rgbd_image rgb_camera_info

section "SYNC OUTPUT: /rgbd_image RIGHT CAMERA INFO"
check_topic /rgbd_image depth_camera_info

section "RELAY OUTPUT: /stereo/rgbd_image LEFT CAMERA INFO"
check_topic /stereo/rgbd_image rgb_camera_info

section "RELAY OUTPUT: /stereo/rgbd_image RIGHT CAMERA INFO"
check_topic /stereo/rgbd_image depth_camera_info

section "IMAGE TOPIC RATES"
check_rate /camera/camera/infra1/image_rect_raw
check_rate /camera/camera/infra2/image_rect_raw
check_rate /rgbd_image
check_rate /stereo/rgbd_image

section "ODOMETRY PARAMETERS"
timeout 10s ros2 param dump /stereo_odometry \
    || echo "Could not dump odometry parameters."

section "ODOMETRY SAMPLE"
check_topic /odom

section "ODOMETRY RATE"
check_rate /odom

section "ODOMETRY NODE INFO"
timeout 7s ros2 node info /stereo_odometry \
    || echo "Odometry node unavailable."

section "RECENT ODOMETRY LOG"
if [[ -f "$LOG_DIR/stereo_odometry.log" ]]; then
    tail -n 100 "$LOG_DIR/stereo_odometry.log"
else
    echo "Log not found: $LOG_DIR/stereo_odometry.log"
fi

section "RECENT RELAY LOGS"
find "$LOG_DIR" -maxdepth 1 -type f \
    \( -iname '*relay*.log' -o -iname '*sync*.log' \) \
    -print

section "DIAGNOSTICS COMPLETE"
echo "Report saved to: $OUT"
