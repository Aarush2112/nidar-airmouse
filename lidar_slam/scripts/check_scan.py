#!/usr/bin/env python3

"""NIDAR AirMouse — LiDAR LaserScan quality diagnostic."""

import math
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def main():
    rclpy.init()
    node = rclpy.create_node("nidar_scan_quality_test")

    received = False

    def callback(msg):
        nonlocal received

        if received:
            return

        received = True

        ranges = list(msg.ranges)

        valid = [
            value for value in ranges
            if math.isfinite(value)
            and msg.range_min <= value <= msg.range_max
        ]

        invalid = len(ranges) - len(valid)

        print("\n========== NIDAR SCAN QUALITY ==========")
        print("Frame:", msg.header.frame_id)
        print("Total samples:", len(ranges))
        print("Valid samples:", len(valid))
        print("Invalid samples:", invalid)

        if ranges:
            percentage = 100.0 * len(valid) / len(ranges)
            print(f"Valid percentage: {percentage:.2f}%")

        if valid:
            print(f"Minimum distance: {min(valid):.3f} m")
            print(f"Maximum distance: {max(valid):.3f} m")
            print("Range data: AVAILABLE")
        else:
            print("Range data: NO VALID MEASUREMENTS")

        print(f"Angle minimum: {msg.angle_min:.4f} rad")
        print(f"Angle maximum: {msg.angle_max:.4f} rad")
        print(f"Angle increment: {msg.angle_increment:.6f} rad")
        print(f"Scan time: {msg.scan_time:.4f} s")
        print(f"Configured range min: {msg.range_min:.3f} m")
        print(f"Configured range max: {msg.range_max:.3f} m")
        print("========================================\n")

    node.create_subscription(
        LaserScan,
        "/scan",
        callback,
        qos_profile_sensor_data
    )

    start = time.monotonic()

    try:
        while rclpy.ok() and not received:
            rclpy.spin_once(node, timeout_sec=0.2)

            if time.monotonic() - start > 10.0:
                print("ERROR: No LaserScan received within 10 seconds")
                break
    finally:
        node.destroy_node()
        rclpy.shutdown()

    if not received:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
