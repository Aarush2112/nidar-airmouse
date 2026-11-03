#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash

# Source the workspace overlay if one is available.
if [ -f "$HOME/NIDAR AirMouse/install/setup.bash" ]; then
    source "$HOME/NIDAR AirMouse/install/setup.bash"
fi

DURATION=7
REPORT="$HOME/NIDAR AirMouse/nidar_frequency_report.txt"

topics=(
  "/camera/camera/infra1/image_rect_raw"
  "/camera/camera/infra2/image_rect_raw"
  "/camera/camera/depth/image_rect_raw"
  "/camera/camera/accel/sample"
  "/camera/camera/gyro/sample"
  "/mavros/imu/data"
  "/mavros/local_position/pose"
  "/odom"
  "/stereo/rgbd_image"
)

{
  echo "=================================================="
  echo "NIDAR AirMouse - Topic Frequency Check"
  echo "Date: $(date --iso-8601=seconds)"
  echo "Measurement duration: ${DURATION}s per topic"
  echo "=================================================="
  echo

  for topic in "${topics[@]}"; do
    echo
    echo "--------------------------------------------------"
    echo "TOPIC: $topic"
    echo "--------------------------------------------------"

    if ! timeout 4s ros2 topic info "$topic" >/dev/null 2>&1; then
      echo "STATUS: Topic not currently advertised"
      continue
    fi

    timeout "$((DURATION + 3))s" \
      ros2 topic hz "$topic" --window 100 2>&1 || true
  done

  echo
  echo "=================================================="
  echo "Frequency check finished: $(date --iso-8601=seconds)"
  echo "=================================================="
} | tee "$REPORT"

echo
echo "Report saved to: $REPORT"
