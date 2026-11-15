# Hardware

| Component | Project configuration |
| --- | --- |
| Companion computer | Raspberry Pi 5 |
| Operating system | Ubuntu 24.04.5 LTS observed on source machine |
| Middleware | ROS 2 Jazzy |
| Flight controller | YARI V6X running PX4; firmware version not captured |
| Companion interface | MAVROS; tested connection configuration capture pending |
| Camera | Intel RealSense D455 |
| Planned ranging sensor | YDLIDAR X2, 360-degree 2D LiDAR |
| Development workstation | MacBook Pro; editing and remote development |

The V3 bridge assumes aligned camera/body axes and camera origin 0.12 m forward of the vehicle reference point. Geometry was checked during project bench work; verify the physical mount before reuse. No exported project calibration was present in `calibration/`. Do not substitute legacy OpenVINS example calibration for a measured current installation.

Firmware flashing, PX4 parameter changes and flight commands are outside repository setup.
