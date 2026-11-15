#!/usr/bin/env python3

"""NIDAR AirMouse — scan geometry and invalid-return analysis."""

import math
import time
from collections import defaultdict

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

TARGET = 100


def main():
    rclpy.init()
    node = rclpy.create_node("nidar_scan_geometry")

    sectors = defaultdict(
        lambda: {"total": 0, "valid": 0, "near": 0}
    )

    zero = 0
    below_min_nonzero = 0
    nan_count = 0
    inf_count = 0
    scans = 0

    def callback(msg):
        nonlocal zero, below_min_nonzero
        nonlocal nan_count, inf_count, scans

        if scans >= TARGET:
            return

        scans += 1

        for i, distance in enumerate(msg.ranges):
            angle = msg.angle_min + i * msg.angle_increment
            degrees = math.degrees(angle) % 360
            sector = int(degrees // 30) * 30

            sectors[sector]["total"] += 1

            if math.isnan(distance):
                nan_count += 1
                continue

            if math.isinf(distance):
                inf_count += 1
                continue

            if distance == 0:
                zero += 1
                continue

            if distance < msg.range_min:
                below_min_nonzero += 1
                continue

            if distance > msg.range_max:
                continue

            sectors[sector]["valid"] += 1

            if distance < 0.2:
                sectors[sector]["near"] += 1

    node.create_subscription(
        LaserScan,
        "/scan",
        callback,
        qos_profile_sensor_data
    )

    start = time.monotonic()

    try:
        while rclpy.ok() and scans < TARGET:
            rclpy.spin_once(node, timeout_sec=0.2)

            if time.monotonic() - start > 20:
                break

        print("\n========== NIDAR SCAN GEOMETRY ==========")
        print("Scans:", scans)
        print("Zero readings:", zero)
        print("Nonzero below minimum:", below_min_nonzero)
        print("NaN readings:", nan_count)
        print("Infinite readings:", inf_count)

        print("\n===== ANGULAR SECTORS =====")
        print("Sector | Valid % | Near (<0.2m)")

        for sector in range(0, 360, 30):
            data = sectors[sector]
            total = data["total"]

            percentage = (
                100 * data["valid"] / total
                if total else 0
            )

            print(
                f"{sector:3d}-{sector+30:3d} | "
                f"{percentage:6.2f}% | "
                f"{data['near']}"
            )

        print("========== TEST COMPLETE ==========")

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
