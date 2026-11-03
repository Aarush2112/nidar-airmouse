#!/usr/bin/env bash
set -Eeo pipefail

PROJECT="$HOME/NIDAR AirMouse"
LOG_DIR="$PROJECT/logs/vio"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash

PIDS=()
TAIL_PID=""

cleanup() {
    echo
    echo "[NIDAR] Stopping VIO pipeline..."

    if [[ -n "$TAIL_PID" ]]; then
        kill "$TAIL_PID" 2>/dev/null || true
    fi

    for pid in "${PIDS[@]}"; do
        kill -INT "$pid" 2>/dev/null || true
    done

    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    echo "[NIDAR] Pipeline stopped."
}

trap cleanup EXIT INT TERM

start_process() {
    local name="$1"
    shift

    echo "[NIDAR] Starting $name..."
    "$@" > "$LOG_DIR/$name.log" 2>&1 &
    PIDS+=("$!")
}

wait_for_topic() {
    local topic="$1"
    local timeout="$2"
    local elapsed=0

    echo "[NIDAR] Waiting for $topic..."

    while (( elapsed < timeout )); do
        if ros2 topic list 2>/dev/null | grep -Fxq "$topic"; then
            echo "[NIDAR] Found $topic"
            return 0
        fi

        sleep 1
        ((elapsed += 1))
    done

    echo "[NIDAR] ERROR: Timed out waiting for $topic"
    echo "[NIDAR] Check logs in: $LOG_DIR"
    return 1
}

start_process camera \
    ros2 launch realsense2_camera rs_launch.py \
    camera_namespace:=camera camera_name:=camera \
    enable_infra1:=true enable_infra2:=true \
    depth_module.infra_profile:=640x480x30 \
    enable_gyro:=true enable_accel:=true \
    unite_imu_method:=2

wait_for_topic /camera/camera/infra1/image_rect_raw 60
wait_for_topic /camera/camera/infra2/image_rect_raw 30

start_process stereo_sync \
    ros2 run rtabmap_sync stereo_sync --ros-args \
    -p approx_sync:=true \
    -p qos:=1 \
    -p qos_camera_info:=1 \
    -r left/image_rect:=/camera/camera/infra1/image_rect_raw \
    -r right/image_rect:=/camera/camera/infra2/image_rect_raw \
    -r left/camera_info:=/camera/camera/infra1/camera_info \
    -r right/camera_info:=/camera/camera/infra2/camera_info

wait_for_topic /rgbd_image 30

start_process stereo_metadata_relay \
    python3 "$PROJECT/script/stereo_metadata_relay.py"

wait_for_topic /stereo/rgbd_image 15

start_process stereo_odometry \
    ros2 run rtabmap_odom stereo_odometry --ros-args \
    -p subscribe_rgbd:=true \
    -p approx_sync:=true \
    -p qos:=1 \
    -p qos_camera_info:=1 \
    -p frame_id:=camera_link \
    -p 'Odom/ImageDecimation:="2"' \
    -p 'OdomF2M/BundleAdjustmentMaxFrames:="5"' \
    -p 'Vis/MaxFeatures:="1000"' \
    -p wait_imu_to_init:=true \
    -p qos_imu:=2 \
    -p always_check_imu_tf:=false \
    -r imu:=/camera/camera/imu \
    -r rgbd_image:=/stereo/rgbd_image

sleep 3

echo
echo "[NIDAR] Startup sequence complete."
echo "[NIDAR] Logs: $LOG_DIR"
echo "[NIDAR] Press Ctrl+C to stop the pipeline."
echo "[NIDAR] Note: camera_link is a temporary bench-test reference,"
echo "        not the drone body frame."

touch "$LOG_DIR/camera.log" "$LOG_DIR/stereo_sync.log" \
      "$LOG_DIR/stereo_metadata_relay.log" \
      "$LOG_DIR/stereo_odometry.log"

tail -n 20 -F \
    "$LOG_DIR/camera.log" \
    "$LOG_DIR/stereo_sync.log" \
    "$LOG_DIR/stereo_metadata_relay.log" \
    "$LOG_DIR/stereo_odometry.log" &
TAIL_PID=$!
wait
