#!/usr/bin/env python3
import math
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

OFFSET = (0.12, 0.0, 0.0)

def cross(a, b):
    return (
        a[1]*b[2]-a[2]*b[1],
        a[2]*b[0]-a[0]*b[2],
        a[0]*b[1]-a[1]*b[0]
    )

def rotate(q, v):
    x,y,z,w = q
    n = math.sqrt(sum(z*z for z in q))
    if n < 1e-9 or not math.isfinite(n):
        raise ValueError("Invalid orientation")
    x,y,z,w = (z/n for z in q)
    t = cross((x,y,z),v)
    t = [2*z for z in t]
    u = cross((x,y,z),t)
    return tuple(v[i]+w*t[i]+u[i] for i in range(3))

def skew(v):
    x,y,z = v
    return [
        [0,-z,y],
        [z,0,-x],
        [-y,x,0]
    ]

def propagate(cov, lever):
    # J = [[I, skew(lever)], [0, I]]
    J = [[float(i==j) for j in range(6)] for i in range(6)]
    S = skew(lever)
    for i in range(3):
        for j in range(3):
            J[i][j+3] = S[i][j]

    P = [list(cov[i*6:(i+1)*6]) for i in range(6)]
    JP = [[sum(J[i][k]*P[k][j] for k in range(6))
           for j in range(6)] for i in range(6)]
    C = [[sum(JP[i][k]*J[j][k] for k in range(6))
          for j in range(6)] for i in range(6)]
    return [C[i][j] for i in range(6) for j in range(6)]

class Bridge(Node):
    def __init__(self):
        super().__init__('nidar_covariance_preview_v2')
        self.pub = self.create_publisher(
            Odometry, '/nidar/vehicle_odometry_preview_v2', 10)
        self.sub = self.create_subscription(
            Odometry, '/odom', self.cb, 10)
        self.tf_pub = TransformBroadcaster(self)
        self.count = 0
        self.start = time.monotonic()
        print("NIDAR V2 PREVIEW — NO PX4 OUTPUT", flush=True)

    def cb(self, msg):
        if msg.child_frame_id != 'camera_link':
            return

        q = msg.pose.pose.orientation
        try:
            rw = rotate((q.x,q.y,q.z,q.w),OFFSET)
        except ValueError:
            return

        if not all(math.isfinite(x) for x in
                   list(msg.pose.covariance)+list(msg.twist.covariance)):
            return

        out = Odometry()
        out.header = msg.header
        out.child_frame_id = 'base_link'

        p = msg.pose.pose.position
        out.pose.pose.position.x = p.x-rw[0]
        out.pose.pose.position.y = p.y-rw[1]
        out.pose.pose.position.z = p.z-rw[2]
        out.pose.pose.orientation = q

        w = msg.twist.twist.angular
        v = msg.twist.twist.linear
        correction = cross((w.x,w.y,w.z),OFFSET)

        out.twist.twist.linear.x = v.x-correction[0]
        out.twist.twist.linear.y = v.y-correction[1]
        out.twist.twist.linear.z = v.z-correction[2]
        out.twist.twist.angular = w

        # Pose covariance in parent frame: camera -> CG.
        out.pose.covariance = propagate(
            msg.pose.covariance, rw)

        # Twist covariance in aligned camera/body axes.
        out.twist.covariance = propagate(
            msg.twist.covariance, OFFSET)

        self.pub.publish(out)

        tf = TransformStamped()
        tf.header = out.header
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x = out.pose.pose.position.x
        tf.transform.translation.y = out.pose.pose.position.y
        tf.transform.translation.z = out.pose.pose.position.z
        tf.transform.rotation = out.pose.pose.orientation
        self.tf_pub.sendTransform(tf)
        self.count += 1

        if self.count in (1,30,60,100):
            before = [msg.pose.covariance[i*6+i]
                      for i in range(6)]
            after = [out.pose.covariance[i*6+i]
                     for i in range(6)]
            print(f"\nMessages: {self.count}")
            print("Original pose covariance:", before)
            print("Corrected pose covariance:", after)
            print("Camera-body X offset:",
                  round((p.x-out.pose.pose.position.x)*100,2),
                  "cm", flush=True)

def main():
    rclpy.init()
    node = Bridge()
    try:
        while rclpy.ok():
            rclpy.spin_once(node,timeout_sec=0.05)
        duration = time.monotonic()-node.start
        print("\n===== V2 RESULT =====")
        print("Messages:",node.count)
        print("Average frequency:",
              round(node.count/duration,2),"Hz")
        print("Output: /nidar/vehicle_odometry_preview_v2")
        print("PX4 output: DISABLED")
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
