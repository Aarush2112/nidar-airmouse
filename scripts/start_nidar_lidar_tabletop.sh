#!/usr/bin/env bash


PROJECT="$HOME/NIDAR AirMouse"
LOG_DIR="$PROJECT/lidar_slam/logs"
LIDAR_PORT="/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"
LIDAR_CONFIG="$PROJECT/ros2_ws/install/ydlidar_ros2_driver/share/ydlidar_ros2_driver/params/X2.yaml"

mkdir -p "$LOG_DIR"

source /opt/ros/jazzy/setup.bash
source "$PROJECT/ros2_ws/install/setup.bash"
source "$PROJECT/lidar_slam/ws/install/setup.bash"

echo "========================================"
echo " NIDAR AIRMOUSE - TABLETOP LIDAR SYSTEM"
echo "========================================"

# Check required hardware and configuration
if [ ! -e "$LIDAR_PORT" ]; then
    echo "ERROR: YDLIDAR X2 serial port not found."
    exit 1
fi

if [ ! -f "$LIDAR_CONFIG" ]; then
    echo "ERROR: LiDAR configuration not found."
    exit 1
fi

# Avoid duplicate publishers
if pgrep -u "$USER" -f '[y]dlidar_ros2_driver_node|[r]f2o_laser_odometry_node|[s]tatic_transform_publisher' >/dev/null; then
    echo "ERROR: An existing LiDAR, RF2O or static TF process is running."
    echo "Stop the previous tabletop processes before restarting."
    exit 1
fi

PIDS=()

cleanup() {
    trap - EXIT INT TERM
    echo
    echo "Stopping NIDAR tabletop LiDAR system..."
    for pid in "${PIDS[@]}"; do
        kill -TERM "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    echo "All launcher-managed processes stopped."
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo
echo "[1/3] Starting YDLIDAR X2..."

ros2 run ydlidar_ros2_driver ydlidar_ros2_driver_node \
  --ros-args \
  --params-file "$LIDAR_CONFIG" \
  -p port:="$LIDAR_PORT" \
  -p frequency:=7.0 \
  -p range_max:=8.0 \
  > "$LOG_DIR/lidar.log" 2>&1 &

PIDS+=("$!")

sleep 3

if ! kill -0 "${PIDS[0]}" 2>/dev/null; then
    echo "ERROR: LiDAR driver exited."
    tail -20 "$LOG_DIR/lidar.log"
    exit 1
fi

echo "[2/3] Starting 180-degree LiDAR orientation TF..."

ros2 run tf2_ros static_transform_publisher \
  --x 0 \
  --y 0 \
  --z 0 \
  --roll 0 \
  --pitch 0 \
  --yaw 3.141592653589793 \
  --frame-id base_link \
  --child-frame-id laser_frame \
  > "$LOG_DIR/static_tf.log" 2>&1 &

PIDS+=("$!")

sleep 2

if ! kill -0 "${PIDS[1]}" 2>/dev/null; then
    echo "ERROR: Static TF publisher exited."
    tail -20 "$LOG_DIR/static_tf.log"
    exit 1
fi

echo "[3/3] Starting RF2O Laser Odometry..."

ros2 run rf2o_laser_odometry rf2o_laser_odometry_node \
  --ros-args \
  -p laser_scan_topic:=/scan \
  -p odom_topic:=/odom_rf2o \
  -p publish_tf:=true \
  -p base_frame_id:=base_link \
  -p odom_frame_id:=odom \
  -p freq:=10.0 \
  -p 'init_pose_from_topic:=""' \
  > "$LOG_DIR/rf2o.log" 2>&1 &

PIDS+=("$!")

sleep 3

if ! kill -0 "${PIDS[2]}" 2>/dev/null; then
    echo "ERROR: RF2O exited."
    tail -30 "$LOG_DIR/rf2o.log"
    exit 1
fi

echo
echo "========================================"
echo " NIDAR TABLETOP PROCESSES STARTED"
echo "========================================"
echo "LiDAR topic : /scan"
echo "Odometry    : /odom_rf2o"
echo "Static TF   : base_link -> laser_frame"
echo "Yaw offset  : 180 degrees"
echo
echo "Logs: $LOG_DIR"
echo "Press Ctrl+C to stop this launcher."
echo

# Keep the launcher running and detect unexpected exits
while true; do
    for i in "${!PIDS[@]}"; do
        if ! kill -0 "${PIDS[$i]}" 2>/dev/null; then
            echo "ERROR: Process $((i+1)) exited."
            case "$i" in
                0) tail -25 "$LOG_DIR/lidar.log" ;;
                1) tail -25 "$LOG_DIR/static_tf.log" ;;
                2) tail -25 "$LOG_DIR/rf2o.log" ;;
            esac
            exit 1
        fi
    done
    sleep 2
done
