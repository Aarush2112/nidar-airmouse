#!/usr/bin/env bash

set -Eeo pipefail

# Source ROS 2 with nounset disabled
source /opt/ros/jazzy/setup.bash
source "$HOME/NIDAR AirMouse/ros2_ws/install/setup.bash"

ROOT="$HOME/NIDAR AirMouse"
OLD_LAUNCHER="$ROOT/scripts/start_nidar_lidar_icp_recovery.sh"
SLAM_CONFIG="$ROOT/config/nidar_slam_icp_tabletop.yaml"
LOG_DIR="$ROOT/lidar_slam/logs/unified_recovery"

mkdir -p "$LOG_DIR"

echo "=========================================="
echo "   NIDAR AIR MOUSE - LIDAR ICP + SLAM"
echo "=========================================="

if [[ ! -f "$OLD_LAUNCHER" ]]; then
    echo "ERROR: Existing LiDAR + ICP launcher not found."
    exit 1
fi

if [[ ! -f "$SLAM_CONFIG" ]]; then
    echo "ERROR: SLAM Toolbox configuration not found."
    exit 1
fi

if pgrep -f '[/]icp_odometry' >/dev/null ||
   pgrep -f '[/]async_slam_toolbox_node' >/dev/null ||
   pgrep -f '[/]ydlidar_ros2_driver_node' >/dev/null; then
    echo "ERROR: A LiDAR, ICP, or SLAM process is already running."
    echo "Stop the previous session before using this launcher."
    exit 1
fi

PIDS=()

cleanup() {
    trap - INT TERM EXIT

    echo
    echo "Stopping NIDAR LiDAR + ICP + SLAM..."

    for pid in "${PIDS[@]}"; do
        kill -INT "$pid" 2>/dev/null || true
    done

    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    echo "NIDAR processes stopped."
}

trap cleanup INT TERM EXIT

echo
echo "[1/2] Starting YDLIDAR + Static TF + ICP..."

bash "$OLD_LAUNCHER" \
    > "$LOG_DIR/lidar_icp_launcher.log" 2>&1 &

PIDS+=("$!")

sleep 8

if ! kill -0 "${PIDS[0]}" 2>/dev/null; then
    echo "ERROR: LiDAR + ICP launcher exited."
    tail -40 "$LOG_DIR/lidar_icp_launcher.log"
    exit 1
fi

echo
echo "[2/2] Starting SLAM Toolbox..."

ros2 run slam_toolbox async_slam_toolbox_node \
    --ros-args \
    --params-file "$SLAM_CONFIG" \
    > "$LOG_DIR/slam_toolbox.log" 2>&1 &

PIDS+=("$!")

sleep 5

if ! kill -0 "${PIDS[1]}" 2>/dev/null; then
    echo "ERROR: SLAM Toolbox exited."
    tail -40 "$LOG_DIR/slam_toolbox.log"
    exit 1
fi

echo
echo "===== AUTOMATIC SLAM ACTIVATION ====="

SLAM_READY=false

for ATTEMPT in $(seq 1 15); do
    STATE=$(ros2 lifecycle get /slam_toolbox 2>/dev/null || true)

    echo "Attempt $ATTEMPT: $STATE"

    if [[ "$STATE" == *"active"* ]]; then
        SLAM_READY=true
        break
    fi

    if [[ "$STATE" == *"unconfigured"* ]]; then
        ros2 lifecycle set /slam_toolbox configure || true
        sleep 2
    fi

    STATE=$(ros2 lifecycle get /slam_toolbox 2>/dev/null || true)

    if [[ "$STATE" == *"inactive"* ]]; then
        ros2 lifecycle set /slam_toolbox activate || true
        sleep 2
    fi

    STATE=$(ros2 lifecycle get /slam_toolbox 2>/dev/null || true)

    if [[ "$STATE" == *"active"* ]]; then
        SLAM_READY=true
        break
    fi

    sleep 2
done

if [[ "$SLAM_READY" != true ]]; then
    echo "ERROR: SLAM Toolbox did not become active."
    exit 1
fi

echo
echo "===== FINAL SLAM STATUS ====="
ros2 lifecycle get /slam_toolbox

echo
echo "===== AVAILABLE TOPICS ====="
ros2 topic list | grep -E '^(/scan|/odom_icp|/map)$' || true

echo
echo "=========================================="
echo " NIDAR STARTUP SEQUENCE COMPLETE"
echo "=========================================="
echo
echo "Logs:"
echo "  $LOG_DIR/lidar_icp_launcher.log"
echo "  $LOG_DIR/slam_toolbox.log"
echo
echo "Press Ctrl+C to stop the session."

while true; do
    for pid in "${PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "ERROR: A launcher process exited."
            exit 1
        fi
    done
    sleep 2
done
