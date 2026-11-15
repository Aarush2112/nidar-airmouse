#!/usr/bin/env python3

"""NIDAR AirMouse — multi-scan LiDAR stability test."""

import math
import statistics
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

TARGET_SCANS = 100
TIMEOUT_SECONDS = 25.0


def main():
    rclpy.init()
    node = rclpy.create_node("nidar_scan_stability")

    records = []
    timestamps = []
    frame_ids = set()

    def callback(msg):
        if len(records) >= TARGET_SCANS:
            return

        values = [
            value for value in msg.ranges
            if math.isfinite(value)
            and msg.range_min <= value <= msg.range_max
        ]

        count = len(msg.ranges)
        percentage = 100 * len(values) / count if count else 0

        records.append({
            "total": count,
            "valid": len(values),
            "percentage": percentage,
            "min_range": min(values) if values else None,
            "max_range": max(values) if values else None
        })

        timestamps.append(time.monotonic())
        frame_ids.add(msg.header.frame_id)

    node.create_subscription(
        LaserScan,
        "/scan",
        callback,
        qos_profile_sensor_data
    )

    print("========== NIDAR SCAN STABILITY ==========")
    print(f"Collecting up to {TARGET_SCANS} scans...")

    start = time.monotonic()

    try:
        while rclpy.ok() and len(records) < TARGET_SCANS:
            rclpy.spin_once(node, timeout_sec=0.2)

            if time.monotonic() - start > TIMEOUT_SECONDS:
                print("Collection timeout reached.")
                break

        if not records:
            print("ERROR: No scans received.")
            raise SystemExit(1)

        percentages = [r["percentage"] for r in records]
        counts = [r["total"] for r in records]

        minimums = [
            r["min_range"] for r in records
            if r["min_range"] is not None
        ]

        maximums = [
            r["max_range"] for r in records
            if r["max_range"] is not None
        ]

        print("\n===== RESULTS =====")
        print("Scans collected:", len(records))
        print("Frame IDs:", sorted(frame_ids))

        print(
            "Average samples per scan:",
            round(statistics.mean(counts), 2)
        )

        print(
            "Average valid percentage:",
            round(statistics.mean(percentages), 2),
            "%"
        )

        print(
            "Minimum valid percentage:",
            round(min(percentages), 2),
            "%"
        )

        print(
            "Maximum valid percentage:",
            round(max(percentages), 2),
            "%"
        )

        if minimums:
            print(
                "Closest valid detection:",
                round(min(minimums), 3),
                "m"
            )

        if maximums:
            print(
                "Farthest valid detection:",
                round(max(maximums), 3),
                "m"
            )

        if len(timestamps) > 1:
            duration = timestamps[-1] - timestamps[0]

            if duration > 0:
                rate = (len(timestamps) - 1) / duration
                print("Measured scan rate:", round(rate, 3), "Hz")

        empty_scans = sum(
            1 for r in records if r["valid"] == 0
        )

        print("Scans with zero valid points:", empty_scans)
        print("========== TEST COMPLETE ==========")

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
