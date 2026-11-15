# Setup

The working Pi is the source of truth. Preserve its installation and processes. A new checkout is for review or a separately scheduled bench setup; it must not overwrite runtime files.

## Dependencies

Use Ubuntu 24.04 with ROS 2 Jazzy and Bash. The preferred pipeline uses installed ROS packages rather than a local package build. Required packages include `realsense2_camera`, `rtabmap_sync`, `rtabmap_odom`, `rtabmap_msgs`, `rclpy`, `nav_msgs`, `geometry_msgs`, `sensor_msgs`, `tf2_ros` and `message_filters`. Existing extended diagnostics also use NumPy and OpenCV. MAVROS and MAVROS messages are required for the separate flight-controller integration.

On a separately provisioned host with ROS apt repositories already configured, an installation starting point is:

```bash
sudo apt install ros-jazzy-realsense2-camera ros-jazzy-rtabmap-sync ros-jazzy-rtabmap-odom ros-jazzy-rtabmap-msgs ros-jazzy-rclpy ros-jazzy-nav-msgs ros-jazzy-geometry-msgs ros-jazzy-sensor-msgs ros-jazzy-tf2-ros ros-jazzy-message-filters ros-jazzy-mavros ros-jazzy-mavros-extras python3-numpy python3-opencv
```

This was not executed during preparation. Configure USB permissions, camera bandwidth and MAVROS prerequisites for the new host; the repository does not yet contain a complete MAVROS provisioning recipe. Do not change a working Pi to match these instructions.

```bash
source /opt/ros/jazzy/setup.bash
ros2 pkg prefix realsense2_camera
ros2 pkg prefix rtabmap_sync
ros2 pkg prefix rtabmap_odom
ros2 pkg prefix mavros
```

Existing launchers expect `$HOME/NIDAR AirMouse`, including the space. The preferred launcher sources `/opt/ros/jazzy/setup.bash` and launches installed packages. No custom ROS package is required. The existing OpenVINS tree has ROS package manifests/CMake files but is not a runtime dependency of this stereo pipeline.

## Reproduction limits

[Observed package versions](dependencies-observed.tsv) record relevant installed Debian packages, not a fully pinned OS image or guarantee of future availability. PX4 firmware version, tested MAVROS launch/plugin configuration and current exported camera calibration remain to be captured. Read [VIO](vio.md) before starting any nodes.

## Offline validation

Run `python3 -m unittest discover -s tests`. Python compilation and `bash -n` can check syntax without starting hardware. Documentation and secret checks are described in [validation](validation.md).
