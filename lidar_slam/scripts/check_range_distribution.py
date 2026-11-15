#!/usr/bin/env python3

"""NIDAR AirMouse — LiDAR range distribution."""

import math
import time
from collections import Counter

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

TARGET = 100

BINS = [
    (0.0, 0.2),
    (0.2, 0.5),
    (0.5, 1.0),
    (1.0, 2.0),
    (2.0, 4.0),
    (4.0, 6.0),
    (6.0, 8.0),
    (8.0, 10.0),
    (10.0, 12.0),
]


def main():
    rclpy.init()
    node = rclpy.create_node("nidar_range_distribution")

    counts = Counter()
    invalid = Counter()
    received = 0

    def callback(msg):
        nonlocal received

        if received >= TARGET:
            return

        received += 1

        for r in msg.ranges:
            if math.isnan(r):
                invalid["nan"] += 1
            elif math.isinf(r):
                invalid["infinite"] += 1
            elif r < msg.range_min:
                invalid["below_min"] += 1
            elif r > msg.range_max:
                invalid["above_max"] += 1
            else:
                for low, high in BINS:
                    if low <= r < high:
                        counts[(low, high)] += 1
                        break

    node.create_subscription(
        LaserScan,
        "/scan",
        callback,
        qos_profile_sensor_data
    )

    start = time.monotonic()

    try:
        while rclpy.ok() and received < TARGET:
            rclpy.spin_once(node, timeout_sec=0.2)

            if time.monotonic() - start > 20:
                break

        print("\n========== NIDAR RANGE DISTRIBUTION ==========")
        print("Scans collected:", received)

        print("\n===== VALID DISTANCE BANDS =====")
        for low, high in BINS:
            count = counts[(low, high)]
            print(f"{low:4.1f} - {high:4.1f} m : {count}")

        print("\n===== INVALID MEASUREMENTS =====")
        for reason in [
            "nan", "infinite", "below_min", "above_max"
        ]:
            print(f"{reason}: {invalid[reason]}")

        total_valid = sum(counts.values())
        total_invalid = sum(invalid.values())

        print("\nTotal valid:", total_valid)
        print("Total invalid:", total_invalid)

        if total_valid + total_invalid:
            pct = 100 * total_valid / (
                total_valid + total_invalid
            )
            print(f"Valid percentage: {pct:.2f}%")

        print("========== TEST COMPLETE ==========")

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
