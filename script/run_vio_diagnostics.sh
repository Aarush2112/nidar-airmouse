#!/usr/bin/env bash

set +e
source /opt/ros/jazzy/setup.bash
OUT="$HOME/NIDAR AirMouse/logs/vio/full_diagnostics_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p "$(dirname "$OUT")"
exec > >(tee "$OUT") 2>&1

section() {
    echo
    echo "============================================================"
    echo " $1"
    echo "============================================================"
}

check_topic() {
    echo
    echo "--- $1 ---"
    timeout 5s ros2 topic info "$1" --verbose 2>&1 | head -n 45
}

check_param() {
    echo
    echo "--- $1 / $2 ---"
    timeout 5s ros2 param get "$1" "$2" 2>&1
}

section "SYSTEM"
date
uptime
free -h
df -h "$HOME"
top -b -n 1 | head -n 20
echo
echo "--- Temperature ---"
for f in /sys/class/thermal/thermal_zone*/temp; do
    [ -r "$f" ] && printf '%s: ' "$f" && awk '{printf "%.1f C\n", $1/1000}' "$f"
done
echo
echo "--- Throttling status, if available ---"
command -v vcgencmd >/dev/null && vcgencmd get_throttled || true

section "ROS NODES"
timeout 10s ros2 node list

section "CAMERA TOPICS"
check_topic /camera/camera/infra1/image_rect_raw
check_topic /camera/camera/infra2/image_rect_raw
check_topic /camera/camera/infra1/camera_info
check_topic /camera/camera/infra2/camera_info
check_topic /camera/camera/imu
check_topic /rgbd_image
check_topic /stereo/rgbd_image
check_topic /odom
check_topic /odom_info

section "CAMERA PARAMETERS"
timeout 10s ros2 param dump /camera/camera

section "STEREO SYNC PARAMETERS"
timeout 10s ros2 param dump /stereo_sync

section "ODOMETRY PARAMETERS"
timeout 10s ros2 param dump /stereo_odometry

section "CALIBRATION: LEFT CAMERA"
timeout 5s ros2 topic echo /camera/camera/infra1/camera_info \
    --once --field k
timeout 5s ros2 topic echo /camera/camera/infra1/camera_info \
    --once --field p
timeout 5s ros2 topic echo /camera/camera/infra1/camera_info \
    --once --field header

section "CALIBRATION: RIGHT CAMERA"
timeout 5s ros2 topic echo /camera/camera/infra2/camera_info \
    --once --field k
timeout 5s ros2 topic echo /camera/camera/infra2/camera_info \
    --once --field p
timeout 5s ros2 topic echo /camera/camera/infra2/camera_info \
    --once --field header

section "TF FRAMES"
timeout 8s ros2 run tf2_ros tf2_echo camera_link camera_infra1_optical_frame
timeout 8s ros2 run tf2_ros tf2_echo camera_link camera_infra2_optical_frame

section "CPU PROCESS SNAPSHOT"
ps -eo pid,pcpu,pmem,rss,etime,args --sort=-pcpu | head -n 20

section "LATEST ODOMETRY LOGS"
grep -hE \
'stereo correspondences are rejected|Odom: quality=|Dropping image/scan data|Registration failed|Missing correspondences|Frames didn.t arrive|error|Error|ERROR' \
"$HOME/NIDAR AirMouse/logs/vio/"*stereo_odometry* \
"$HOME/NIDAR AirMouse/logs/vio/"* 2>/dev/null | tail -n 100

section "SHORT TOPIC RATE SAMPLES"
for topic in \
    /camera/camera/infra1/image_rect_raw \
    /camera/camera/infra2/image_rect_raw \
    /stereo/rgbd_image \
    /odom
do
    echo
    echo "--- $topic (5-second sample) ---"
    timeout 7s ros2 topic hz "$topic" --window 30 2>&1
done

section "DIAGNOSTICS COMPLETE"
echo "Report saved to: $OUT"
