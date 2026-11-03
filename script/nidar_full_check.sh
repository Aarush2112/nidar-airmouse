#!/usr/bin/env bash

set +u

PROJECT="$HOME/NIDAR AirMouse"
REPORT="$PROJECT/nidar_full_check_report.txt"
mkdir -p "$PROJECT"

source /opt/ros/jazzy/setup.bash

# Save all output to both the terminal and report file.
exec > >(tee "$REPORT") 2>&1

section() {
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

check_command() {
    echo
    echo "\$ $*"
    timeout 8s "$@" 2>&1 || echo "[No result, timeout, or command unavailable]"
}

section "NIDAR AIRMouse FULL DIAGNOSTIC"
date --iso-8601=seconds
echo "Host: $(hostname)"
echo "Report: $REPORT"
echo "Mode: Read-only diagnostics; no FC parameter writes"

section "1. OPERATING SYSTEM"
uname -a
grep -E 'PRETTY_NAME|VERSION_ID' /etc/os-release
uptime
free -h
df -h "$HOME"

section "2. CPU, TEMPERATURE AND THROTTLING"
if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp
    vcgencmd get_throttled
else
    echo "vcgencmd unavailable"
fi

for f in /sys/class/thermal/thermal_zone*/temp; do
    [ -r "$f" ] || continue
    printf '%s: ' "$f"
    awk '{printf "%.1f C\n", $1/1000}' "$f"
done

ps -eo pid,pcpu,pmem,comm --sort=-pcpu | head -n 12

section "3. USB FLIGHT CONTROLLER"
ls -l /dev/serial/by-id/ 2>&1
lsusb 2>&1 | grep -Ei 'YARI|3185:04d2' || true
if [ -e /dev/ttyACM0 ]; then
    echo "/dev/ttyACM0 exists"
    sudo -n fuser -v /dev/ttyACM0 2>&1 ||
        echo "fuser found no holder or sudo requires a password"
else
    echo "/dev/ttyACM0 not present"
fi

section "4. ROS 2 NODES"
check_command ros2 node list

section "5. KEY ROS 2 TOPICS"
check_command ros2 topic list

section "6. MAVROS STATE"
check_command ros2 topic echo /mavros/state --once

section "7. PX4 ESTIMATOR STATUS"
check_command ros2 topic echo /mavros/estimator_status --once

section "8. MAVROS IMU SAMPLE"
check_command ros2 topic echo /mavros/imu/data --once

section "9. MAVROS LOCAL POSE SAMPLE"
check_command ros2 topic echo /mavros/local_position/pose --once

section "10. MAVROS LOCAL POSE RATE (5 SECONDS)"
check_command timeout 6s ros2 topic hz /mavros/local_position/pose

section "11. MAVROS IMU RATE (5 SECONDS)"
check_command timeout 6s ros2 topic hz /mavros/imu/data

section "12. VIO TOPIC AVAILABILITY"
ros2 topic list 2>/dev/null |
    grep -E '^(/camera/|/stereo/|/rgbd_image$|/odom$|/odom_info$)' ||
    echo "No matching camera/VIO topics currently advertised"

for topic in /odom /odom_info /stereo/rgbd_image \
             /camera/camera/imu \
             /camera/camera/infra1/image_rect_raw \
             /camera/camera/infra2/image_rect_raw; do
    if ros2 topic list 2>/dev/null | grep -Fxq "$topic"; then
        echo
        echo "--- $topic ---"
        timeout 4s ros2 topic hz "$topic" 2>&1 ||
            echo "[No rate result within timeout]"
    else
        echo
        echo "$topic: not currently advertised"
    fi
done

section "13. MAVROS CONNECTION DETAILS"
ros2 node list 2>/dev/null | grep -i mavros || true
ros2 topic info /mavros/state 2>&1
ros2 topic info /mavros/imu/data 2>&1
ros2 topic info /mavros/local_position/pose 2>&1

section "14. RECENT VIO LOGS"
LOG_DIR="$PROJECT/logs/vio"
if [ -d "$LOG_DIR" ]; then
    for f in "$LOG_DIR"/stereo_odometry.log \
             "$LOG_DIR"/stereo_sync.log \
             "$LOG_DIR"/stereo_metadata_relay.log \
             "$LOG_DIR"/camera.log; do
        [ -f "$f" ] || continue
        echo
        echo "--- Last 15 lines: $(basename "$f") ---"
        tail -n 15 "$f"
    done
else
    echo "VIO log directory not found: $LOG_DIR"
fi

section "15. SUMMARY"
echo "Diagnostics finished: $(date --iso-8601=seconds)"
echo "Report saved to: $REPORT"
echo "This script did not intentionally change FC settings."
echo "No MAVLink serial client was opened; MAVROS may remain connected."
echo "Review estimator flags and VIO topic availability before flight."

