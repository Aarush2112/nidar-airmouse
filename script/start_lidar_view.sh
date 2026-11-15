#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash

export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0

# Prefer GNOME's XWayland compatibility for RViz2.
export QT_QPA_PLATFORM=xcb

AUTH_FILE=$(find "$XDG_RUNTIME_DIR" -maxdepth 1 \
    -name '.mutter-Xwaylandauth.*' -print -quit)

if [ -n "$AUTH_FILE" ]; then
    export XAUTHORITY="$AUTH_FILE"
fi

echo "Starting NIDAR LiDAR visualization..."
echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=${XAUTHORITY:-unset}"

exec rviz2
