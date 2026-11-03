#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="$HOME/NIDAR AirMouse"
LOG_DIR="$PROJECT/logs/vio"
mkdir -p "$LOG_DIR"

# ROS setup scripts may reference unset variables; disable nounset only while sourcing.
set +u
source /opt/ros/jazzy/setup.bash
if [[ -f "$PROJECT/install/setup.bash" ]]; then
    source "$PROJECT/install/setup.bash"
fi
set -u

PIDS=()

cleanup() {
    trap - INT TERM EXIT
    echo
    echo "[NIDAR VIO] Stopping only launch wrappers started by this script."
    for pid in "${PIDS[@]}"; do
        kill -INT "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    echo "[NIDAR VIO] Shutdown requested."
}
trap cleanup INT TERM EXIT

node_exists() {
    ros2 node list 2>/dev/null | grep -Fxq "$1"
}

topic_exists() {
    ros2 topic list 2>/dev/null | grep -Fxq "$1"
}

wait_topic() {
    local topic="$1" limit="$2" elapsed=0
    until topic_exists "$topic"; do
        if (( elapsed >= limit )); then
            echo "[NIDAR VIO] ERROR: Timed out waiting for $topic"
            return 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo "[NIDAR VIO] Available: $topic"
}

start_node() {
    local name="$1"
    shift
    echo "[NIDAR VIO] Starting $name; log: $LOG_DIR/$name.log"
    "$@" > "$LOG_DIR/$name.log" 2>&1 &
    PIDS+=("$!")
}

echo "[NIDAR VIO] Starting at $(date --iso-8601=seconds)"
echo "[NIDAR VIO] Existing camera and MAVROS will not be started or stopped."

if ! node_exists /camera/camera; then
    echo "[NIDAR VIO] ERROR: RealSense camera is not running. Start it separately."
    exit 1
fi

wait_topic /camera/camera/infra1/image_rect_raw 20
wait_topic /camera/camera/infra2/image_rect_raw 20

if ! node_exists /stereo_sync; then
    start_node stereo_sync ros2 run rtabmap_sync stereo_sync --ros-args \
        -p approx_sync:=true -p qos:=1 -p qos_camera_info:=1 \
        -r left/image_rect:=/camera/camera/infra1/image_rect_raw \
        -r right/image_rect:=/camera/camera/infra2/image_rect_raw \
        -r left/camera_info:=/camera/camera/infra1/camera_info \
        -r right/camera_info:=/camera/camera/infra2/camera_info
fi
wait_topic /rgbd_image 30

if ! node_exists /stereo_metadata_relay; then
    start_node stereo_metadata_relay python3 "$PROJECT/stereo_metadata_relay.py"
fi
wait_topic /stereo/rgbd_image 20

if ! node_exists /stereo_odometry; then
    start_node stereo_odometry ros2 run rtabmap_odom stereo_odometry --ros-args \
        -p subscribe_rgbd:=true -p approx_sync:=true \
        -p qos:=1 -p qos_camera_info:=1 \
        -p frame_id:=camera_link \
        -r rgbd_image:=/stereo/rgbd_image
fi

sleep 3
echo
echo "[NIDAR VIO] Pipeline nodes:"
ros2 node list 2>/dev/null | grep -E 'camera/camera|stereo_sync|stereo_metadata_relay|stereo_odometry' || true
echo
echo "[NIDAR VIO] Running without continuous topic-rate monitoring."
echo "[NIDAR VIO] Press Ctrl+C to request shutdown of processes started by this script."
while true; do sleep 60; done
