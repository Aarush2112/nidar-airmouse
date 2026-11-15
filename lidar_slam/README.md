# NIDAR AirMouse — LiDAR SLAM

## Objective

Develop an indoor GPS-denied localization and
2D mapping system for NIDAR AirMouse.

## Sensor Architecture

Primary:
- YDLIDAR X2 — 2D mapping and planar localization
- Flight controller IMU — attitude and motion estimation

Secondary:
- Intel RealSense D455 — visual odometry when reliable

## Development Stages

1. LiDAR driver and LaserScan validation
2. LiDAR scan-matching odometry
3. 2D SLAM mapping
4. LiDAR + IMU sensor fusion
5. Optional visual odometry integration
6. Square trajectory validation
7. Lawnmower trajectory validation
8. PX4 external odometry integration
9. Indoor autonomous navigation

## Existing ROS 2 Workspace

../ros2_ws

## ROS Distribution

Jazzy
