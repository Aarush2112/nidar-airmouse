# Architecture

D455 infrared rectified images and CameraInfo feed `rtabmap_sync/stereo_sync`. It publishes `/rgbd_image`; `stereo_metadata_relay.py` publishes `/stereo/rgbd_image`. The RGBD container carries the right stereo image in its depth field. The relay changes only the right CameraInfo frame name to `camera_infra2_optical_frame`; it does not change calibration or image pixels.

`rtabmap_odom/stereo_odometry` publishes `/odom` with child `camera_link`. `nidar_bridge_v3.py` accepts only that child frame, corrects the camera lever arm, publishes body odometry to `/nidar/vehicle_odometry_preview_v2`, and broadcasts the output parent-to-`base_link` TF.

MAVROS-to-PX4 visual odometry reception was verified separately by the project owner. The precise forwarding configuration is absent from project files. The preview bridge alone does not complete this connection. External-vision fusion is disabled.

Camera IMU streams are enabled but the preferred launcher has no IMU input remapping into odometry. The project term VIO does not demonstrate tightly coupled visual-inertial fusion in this configuration.

The waypoint planners are independent Python programs producing text, with no ROS or flight-control connection. No project-specific simulation or LiDAR source was found. Existing OpenVINS simulator code belongs to the legacy upstream source tree.
