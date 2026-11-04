#!/usr/bin/env bash
set -eo pipefail

PROJECT="$HOME/NIDAR AirMouse"
LOG_DIR="$PROJECT/logs/master"
mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash
if [[ -f "$PROJECT/install/setup.bash" ]]; then
    source "$PROJECT/install/setup.bash"
fi

PIDS=()
NAMES=()

cleanup() {
    trap - INT TERM EXIT
    echo
    echo "[NIDAR] Stopping only processes started by this script..."
    for pid in "${PIDS[@]}"; do
        kill -INT "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    echo "[NIDAR] Shutdown complete. Existing MAVROS/camera processes were not intentionally stopped."
}
trap cleanup INT TERM EXIT

node_exists() {
    ros2 node list 2>/dev/null | grep -Fxq "$1"
}

topic_exists() {
    ros2 topic list 2>/dev/null | grep -Fxq "$1"
}

start_managed() {
    local name="$1"
    shift
    echo "[NIDAR] Starting $name..."
    "$@" > "$LOG_DIR/$name.log" 2>&1 &
    PIDS+=("$!")
    NAMES+=("$name")
}

wait_topic() {
    local topic="$1"
    local seconds="$2"
    local elapsed=0
    echo "[NIDAR] Waiting for $topic"
    while (( elapsed < seconds )); do
        if topic_exists "$topic"; then
            echo "[NIDAR] Found $topic"
            return 0
        fi
        sleep 1
        ((elapsed += 1))
    done
    echo "[NIDAR] ERROR: Timed out waiting for $topic"
    return 1
}

echo "=================================================="
echo "NIDAR AirMouse MASTER"
echo "Started: $(date --iso-8601=seconds)"
echo "Logs: $LOG_DIR"
echo "=================================================="

# Never start a second MAVROS instance.
if node_exists /mavros; then
    echo "[NIDAR] Reusing existing MAVROS."
else
    echo "[NIDAR] MAVROS is not running."
    echo "[NIDAR] Start the approved MAVROS connection separately, then rerun this script."
    exit 1
fi

# Reuse the existing camera, or start it if absent.
if node_exists /camera/camera; then
    echo "[NIDAR] Reusing existing RealSense camera."
else
    start_managed camera \
        ros2 launch realsense2_camera rs_launch.py \
        camera_namespace:=camera camera_name:=camera \
        enable_infra1:=true enable_infra2:=true \
        enable_gyro:=true enable_accel:=true
    wait_topic /camera/camera/infra1/image_rect_raw 60
    wait_topic /camera/camera/infra2/image_rect_raw 30
fi

# Reuse the existing stereo synchronizer, or start it.
if node_exists /stereo_sync; then
    echo "[NIDAR] Reusing existing stereo synchronizer."
else
    start_managed stereo_sync \
        ros2 run rtabmap_sync stereo_sync --ros-args \
        -p approx_sync:=true -p qos:=1 -p qos_camera_info:=1 \
        -r left/image_rect:=/camera/camera/infra1/image_rect_raw \
        -r right/image_rect:=/camera/camera/infra2/image_rect_raw \
        -r left/camera_info:=/camera/camera/infra1/camera_info \
        -r right/camera_info:=/camera/camera/infra2/camera_info
fi
wait_topic /rgbd_image 30

# Reuse the relay, or start it.
if node_exists /stereo_metadata_relay; then
    echo "[NIDAR] Reusing existing metadata relay."
else
    start_managed stereo_metadata_relay \
        python3 "$PROJECT/script/stereo_metadata_relay.py"
fi
wait_topic /stereo/rgbd_image 20

# Start odometry only if its node is not already present.
if node_exists /stereo_odometry; then
    echo "[NIDAR] Reusing existing stereo odometry."
else
    start_managed stereo_odometry \
        ros2 run rtabmap_odom stereo_odometry --ros-args \
        -p subscribe_rgbd:=true -p approx_sync:=true \
        -p qos:=1 -p qos_camera_info:=1 \
        -p frame_id:=camera_link \
        -r rgbd_image:=/stereo/rgbd_image
fi

sleep 3

echo
echo "[NIDAR] Pipeline status:"
ros2 node list 2>/dev/null | grep -E 'camera/camera|mavros$|stereo_sync|stereo_metadata_relay|stereo_odometry' || true

echo
echo "[NIDAR] Monitoring topic rates. Press Ctrl+C to stop managed processes."
echo "[NIDAR] Existing MAVROS and camera processes are left running."
echo

topics=(
    /camera/camera/infra1/image_rect_raw
    /camera/camera/infra2/image_rect_raw
    /camera/camera/accel/sample
    /camera/camera/gyro/sample
    /rgbd_image
    /stereo/rgbd_image
    /odom
    /mavros/imu/data
    /mavros/local_position/pose
)

while true; do
    {
        echo
        echo "===== $(date --iso-8601=seconds) ====="
        for topic in "${topics[@]}"; do
            echo "--- $topic ---"
            if topic_exists "$topic"; then
                timeout 5s ros2 topic hz "$topic" --window 30 2>&1 | tail -n 3 || true
            else
                echo "Not advertised"
            fi
        done
        echo "--- MAVROS state ---"
        timeout 4s ros2 topic echo /mavros/state --once 2>&1 || true
        echo "--- Estimator flags ---"
        timeout 4s ros2 topic echo /mavros/estimator_status --once 2>&1 || true
    } | tee -a "$LOG_DIR/monitor.log"

    sleep 3
done
