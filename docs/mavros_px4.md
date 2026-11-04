# MAVROS and PX4

The project owner verified ROS odometry reaching the V3 bridge, MAVROS forwarding visual odometry, and PX4 receiving `vehicle_visual_odometry`. Camera-to-body TF geometry was checked. These observations were not repeated during repository preparation.

**`EKF2_EV_CTRL=0`: external-vision fusion is disabled.** PX4 horizontal position and velocity are not valid for autonomous flight. Reception of a message is not estimator fusion or flight validation. Do not modify PX4 parameters or firmware as part of setup.

## V3 preview bridge

`script/nidar_bridge_v3.py` subscribes to `/odom`, filters for `child_frame_id == camera_link`, and publishes `nav_msgs/Odometry` to `/nidar/vehicle_odometry_preview_v2` with child `base_link`. Its internal node/log labels still say V2; this is the actual maintained V3 file.

The camera offset is `(0.12, 0, 0)` metres in aligned camera/body axes. The bridge subtracts the orientation-rotated lever arm from position, and subtracts angular velocity cross lever arm from linear velocity. Pose covariance propagates with the world-frame lever arm and twist covariance with the body-frame lever arm using `J P Jᵀ`, `J = [[I, skew(lever)], [0, I]]`. Orientation and angular velocity are retained.

It rejects invalid quaternion norm and non-finite covariance values, but does not implement comprehensive position, timestamp, tracking-loss or flight-safety validation. It broadcasts the output parent-to-body TF; avoid duplicate body TF authorities. Aligned axes and angular-rate/twist conventions need validation for each mount.

The bridge itself has no MAVROS publisher, serial connection, ENU-to-NED conversion or PX4 output. Do not route its output directly to a differently framed interface without verifying conventions. The exact tested MAVROS forwarding/remapping/plugin configuration and connection settings were not found in the project and remain a reproducibility gap. No guessed connection endpoint is published.

`script/nidar_fc.sh` observes an existing MAVROS connection and estimator status. It does not start MAVROS. This preparation did not launch it or alter existing ROS processes.
