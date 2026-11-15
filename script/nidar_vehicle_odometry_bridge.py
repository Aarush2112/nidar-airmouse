#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


# Camera mounting relative to drone CG, in metres.
# Assumes camera_link and base_link axes are aligned.
CAMERA_OFFSET = (0.12, 0.0, 0.0)


def cross(a, b):
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    )


def rotate_vector(q, v):
    """Rotate vector v using quaternion q (xyzw)."""
    x, y, z, w = q

    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if norm < 1e-9:
        raise ValueError("Invalid quaternion")

    x, y, z, w = (
        x/norm, y/norm, z/norm, w/norm
    )

    xyz = (x, y, z)
    t = cross(xyz, v)
    t = tuple(2.0*a for a in t)
    u = cross(xyz, t)

    return tuple(
        v[i] + w*t[i] + u[i]
        for i in range(3)
    )


class NIDARBridge(Node):
    def __init__(self):
        super().__init__('nidar_vehicle_odometry_bridge')

        self.publisher = self.create_publisher(
            Odometry,
            '/nidar/vehicle_odometry_preview',
            10
        )

        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.callback,
            10
        )

        self.count = 0

        self.get_logger().info(
            'NIDAR preview bridge started. '
            'Camera offset: X=+0.12m, Y=0, Z=0. '
            'NO PX4 OUTPUT.'
        )

    def callback(self, msg):
        if msg.child_frame_id != 'camera_link':
            self.get_logger().warning(
                f'Unexpected child frame: {msg.child_frame_id}',
                throttle_duration_sec=5.0
            )
            return

        q = msg.pose.pose.orientation
        quaternion = (q.x, q.y, q.z, q.w)

        try:
            offset_world = rotate_vector(
                quaternion, CAMERA_OFFSET
            )
        except ValueError:
            return

        output = Odometry()
        output.header = msg.header
        output.child_frame_id = 'base_link'

        # Camera pose to drone CG pose.
        p = msg.pose.pose.position
        bp = output.pose.pose.position

        bp.x = p.x - offset_world[0]
        bp.y = p.y - offset_world[1]
        bp.z = p.z - offset_world[2]

        output.pose.pose.orientation = q

        # Twist is assumed to be expressed in the
        # camera_link axes, aligned with base_link.
        v = msg.twist.twist.linear
        w = msg.twist.twist.angular

        omega = (w.x, w.y, w.z)

        # Correct linear velocity for the lever arm.
        correction = cross(omega, CAMERA_OFFSET)

        output.twist.twist.linear.x = v.x - correction[0]
        output.twist.twist.linear.y = v.y - correction[1]
        output.twist.twist.linear.z = v.z - correction[2]

        output.twist.twist.angular = w

        # Preview only: covariance is copied, not
        # propagated through the rigid-body transform.
        # Do not feed this directly to PX4.
        output.pose.covariance = msg.pose.covariance
        output.twist.covariance = msg.twist.covariance

        self.publisher.publish(output)

        self.count += 1
        if self.count == 1:
            self.get_logger().info(
                'First vehicle odometry preview published.'
            )


def main():
    rclpy.init()
    node = NIDARBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
