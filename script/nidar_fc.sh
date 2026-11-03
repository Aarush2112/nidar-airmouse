#!/usr/bin/env bash
set -Eeuo pipefail

LOG_DIR="$HOME/NIDAR AirMouse/logs/fc"
mkdir -p "$LOG_DIR"
source /opt/ros/jazzy/setup.bash

echo "[NIDAR FC] Read-only connection and estimator checks."
echo "[NIDAR FC] This script will not start MAVROS, arm, or change parameters."
echo "[NIDAR FC] Log: $LOG_DIR/checks.log"

if ! ros2 node list 2>/dev/null | grep -Fxq /mavros; then
    echo "[NIDAR FC] ERROR: MAVROS is not visible. Start the approved MAVROS connection separately."
    exit 1
fi

while true; do
    {
        echo
        echo "===== $(date --iso-8601=seconds) ====="
        echo "--- MAVROS state ---"
        timeout 8s ros2 topic echo /mavros/state --once 2>&1 || true
        echo "--- Estimator status ---"
        timeout 8s ros2 topic echo /mavros/estimator_status --once 2>&1 || true
    } | tee -a "$LOG_DIR/checks.log"
    sleep 30
done
