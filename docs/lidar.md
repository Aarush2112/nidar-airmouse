# NIDAR LiDAR + ICP + SLAM

The current Pi setup includes YDLIDAR X2, RTAB-Map ICP odometry and SLAM Toolbox. Start the preserved unified launcher with:

```bash
cd "$HOME/NIDAR AirMouse"
bash scripts/start_nidar_lidar_icp_slam.sh
```

It sources ROS 2 Jazzy and `ros2_ws/install/setup.bash`, starts `scripts/start_nidar_lidar_icp_tabletop.sh`, then starts SLAM Toolbox with `config/nidar_slam_icp_tabletop.yaml`. The driver reads the installed `ydlidar_ros2_driver/params/X2.yaml` (symlinked to package source), uses the existing serial by-id device and publishes `/scan`. ICP publishes `/odom_icp`; SLAM publishes `/map`. Preserve the existing scan inversion and static transform settings.

Previous tabletop/RF2O launchers, RViz layouts, parameter files and named backups remain available. Driver source is under `ros2_ws/src/ydlidar_ros2_driver`, SDK source under `lidar/YDLidar-SDK`, and RF2O source under `lidar_slam/ws/src/rf2o_laser_odometry`. Nested Git metadata stays local; source files are vendored directly.

Saved occupancy maps and serialized pose graphs are versioned under `maps/tabletop` and `maps/icp_tabletop`, including the `pose_graphs` directory. Retain paired `.data` and `.posegraph` files together.

The cleanup did not launch hardware, change algorithms or modify ROS parameters. Installed executables, libraries, build setup files and SDK installation remain on the Pi. Several installed files symlink into build directories, so those directories must not be removed wholesale. New clones require building the workspaces and SDK with the required dependencies. Hardware performance was not retested.
