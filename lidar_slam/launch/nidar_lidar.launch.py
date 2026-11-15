#!/usr/bin/env python3

"""NIDAR AirMouse: YDLIDAR X2 standalone launch."""

from pathlib import Path

from launch import LaunchDescription
from launch_ros.actions import LifecycleNode

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PARAM_FILE = PROJECT_ROOT / "config" / "nidar_x2.yaml"


def generate_launch_description():
    if not PARAM_FILE.is_file():
        raise FileNotFoundError(
            f"LiDAR configuration not found: {PARAM_FILE}"
        )

    lidar = LifecycleNode(
        package="ydlidar_ros2_driver",
        executable="ydlidar_ros2_driver_node",
        name="ydlidar_ros2_driver_node",
        namespace="/",
        output="screen",
        emulate_tty=True,
        parameters=[str(PARAM_FILE)],
    )

    return LaunchDescription([lidar])
