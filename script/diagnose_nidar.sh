#!/usr/bin/env bash

set -u

PROJECT="$HOME/NIDAR AirMouse"
LOG_DIR="$PROJECT/logs/vio"
DURATION=8

section() {
    printf '\n\n========== %s ==========\n' "$1"
}

section "NIDAR AIR MOUSE DIAGNOSTICS"
date
printf 'Hostname: '; hostname
printf 'ROS_DISTRO=%s\n' "${ROS_DISTRO:-NOT SET}"
printf 'AMENT_PREFIX_PATH=%s\n' "${AMENT_PREFIX_PATH:-NOT SET}"

section "ROS 2 NODES"
timeout 12s ros2 node list 2>&1 || true

section "REQUIRED TOPIC DISCOVERY"
ros2 topic list 2>&1 | grep -E \
'(^/camera/camera/(infra1|infra2|imu)|^/rgbd_image$|^/stereo/rgbd_image$|^/odom($|_)|^/odom_info$)' \
|| true

section "TOPIC TYPES"
for topic in \
    /camera/camera/infra1/image_rect_raw \
    /camera/camera/infra2/image_rect_raw \
    /camera/camera/imu \
    /rgbd_image \
    /stereo/rgbd_image \
    /odom \
    /odom_info
do
    echo
    echo "--- $topic ---"
    timeout 5s ros2 topic type "$topic" 2>&1 || true
done

section "PUBLISHING RATES (each measured for ${DURATION}s)"
for topic in \
    /camera/camera/infra1/image_rect_raw \
    /camera/camera/infra2/image_rect_raw \
    /camera/camera/imu \
    /rgbd_image \
    /stereo/rgbd_image \
    /odom
do
    echo
    echo "--- $topic ---"
    timeout "$((DURATION + 3))s" \
        ros2 topic hz "$topic" --window 50 2>&1 || true
done

section "ODOMETRY STATUS"
timeout 8s ros2 topic echo /odom_info --once 2>&1 || true

section "KEY ODOMETRY PARAMETERS"
for param in \
    frame_id \
    odom_frame_id \
    subscribe_rgbd \
    approx_sync \
    qos \
    qos_camera_info \
    always_process_most_recent_frame \
    Odom/ImageDecimation \
    Odom/Strategy \
    Vis/MaxFeatures \
    Vis/MinInliers \
    Stereo/MaxDisparity \
    OdomF2M/MaxSize \
    publish_tf
do
    echo
    echo "--- $param ---"
    timeout 5s ros2 param get /stereo_odometry "$param" 2>&1 || true
done

section "PIPELINE PROCESS CPU AND MEMORY"
ps -eo pid,ppid,%cpu,%mem,rss,etime,args --sort=-%cpu |
    grep -E '[r]ealsense2_camera|[s]tereo_sync|[s]tereo_metadata_relay|[s]tereo_odometry' ||
    true

section "SYSTEM MEMORY"
free -h 2>&1 || true

section "RECENT LOG WARNINGS AND ERRORS"
for name in camera stereo_sync stereo_metadata_relay stereo_odometry
do
    file="$LOG_DIR/$name.log"
    echo
    echo "--- $name ---"
    if [[ -f "$file" ]]; then
        grep -Ei 'error|warn|failed|dropping|lost|exception|rejected' "$file" |
            tail -n 12 || echo "No matching warnings/errors in log."
    else
        echo "Log file not found: $file"
    fi
done

section "DIAGNOSTICS COMPLETE"
echo "No ROS parameters or processes were intentionally changed."
