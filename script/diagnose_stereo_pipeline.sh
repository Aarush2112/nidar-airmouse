#!/usr/bin/env bash

set -eo pipefail

ROS_SETUP="/opt/ros/jazzy/setup.bash"
LOG_DIR="$HOME/NIDAR AirMouse/logs/vio"
REPORT="$LOG_DIR/stereo_pipeline_report_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "$LOG_DIR"

if [[ ! -f "$ROS_SETUP" ]]; then
    echo "ERROR: ROS 2 setup file not found: $ROS_SETUP"
    exit 1
fi

source "$ROS_SETUP"

exec > >(tee "$REPORT") 2>&1

section() {
    echo
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

run_cmd() {
    echo
    echo "+ $*"
    "$@" 2>&1 || echo "[Command returned a non-zero exit status]"
}

section "NIDAR AIR MOUSE - STEREO PIPELINE DIAGNOSTICS"
date
echo "ROS_DISTRO=${ROS_DISTRO:-unknown}"
echo "Report: $REPORT"

section "1. ROS 2 NODES"
run_cmd ros2 node list

section "2. TOPIC LIST AND TYPES"
run_cmd ros2 topic list -t

section "3. TOPIC ENDPOINTS AND QoS"
for topic in \
    /camera/camera/infra1/image_rect_raw \
    /camera/camera/infra2/image_rect_raw \
    /camera/camera/infra1/camera_info \
    /camera/camera/infra2/camera_info \
    /camera/camera/imu \
    /rgbd_image \
    /stereo/rgbd_image \
    /odom \
    /odom_info
do
    section "TOPIC INFO: $topic"
    timeout 12s ros2 topic info "$topic" --verbose 2>&1 \
        || echo "[Topic info unavailable or timed out]"
done

section "4. RGBD IMAGE MESSAGE DEFINITION"
run_cmd ros2 interface show rtabmap_msgs/msg/RGBDImage

section "5. CAMERA INFO MESSAGE DEFINITION"
run_cmd ros2 interface show sensor_msgs/msg/CameraInfo

section "6. RGBD INPUT RATE (/rgbd_image)"
timeout --signal=INT 12s ros2 topic hz /rgbd_image 2>&1 \
    || echo "[Rate sampling ended]"

section "7. RGBD RELAY OUTPUT RATE (/stereo/rgbd_image)"
timeout --signal=INT 12s ros2 topic hz /stereo/rgbd_image 2>&1 \
    || echo "[Rate sampling ended]"

section "8. CAMERA IMAGE RATES"
for topic in \
    /camera/camera/infra1/image_rect_raw \
    /camera/camera/infra2/image_rect_raw \
    /camera/camera/imu
do
    echo
    echo "--- $topic ---"
    timeout --signal=INT 8s ros2 topic hz "$topic" 2>&1 \
        || echo "[Rate sampling ended]"
done

section "9. ODOMETRY RATE"
timeout --signal=INT 10s ros2 topic hz /odom 2>&1 \
    || echo "[Rate sampling ended]"

section "10. ODOMETRY NODE PARAMETERS"
for param in \
    frame_id \
    odom_frame_id \
    subscribe_rgbd \
    approx_sync \
    qos \
    qos_camera_info \
    always_process_most_recent_frame \
    Odom/Strategy \
    Vis/MaxFeatures \
    Stereo/MaxDisparity \
    OdomF2M/MaxSize
do
    echo
    echo "--- $param ---"
    timeout 5s ros2 param get /stereo_odometry "$param" 2>&1 \
        || echo "[Parameter unavailable]"
done

section "11. PROCESS CPU AND MEMORY"
ps -eo pid,ppid,pcpu,pmem,rss,etime,args --sort=-pcpu \
    | head -n 20

section "12. MEMORY SUMMARY"
free -h

section "13. RECENT PIPELINE LOG WARNINGS"
for logfile in "$LOG_DIR"/*.log; do
    [[ -f "$logfile" ]] || continue
    echo
    echo "--- $logfile ---"
    grep -Ei \
        'warn|error|timeout|dropping image|correspondences are rejected|failed' \
        "$logfile" | tail -n 30 || true
done

section "DIAGNOSTICS COMPLETE"
echo "Report saved to: $REPORT"
