#!/usr/bin/env python3
"""NIDAR 1 m x 1 m square waypoint planner (no flight commands).

Usage: python3 nidar_square_mission.py 0.5
The only user-supplied setting is target height in metres.
Coordinates are local ENU offsets relative to the planned takeoff point:
X forward, Y left, Z up. These are planning coordinates, not PX4 NED.
"""

import argparse
import math

SIDE_M = 1.0


def waypoints(height_m: float):
    """Return (label, x_m, y_m, z_m) in local ENU coordinates."""
    return [
        ("Start / takeoff position", 0.0, 0.0, height_m),
        ("Corner 1", SIDE_M, 0.0, height_m),
        ("Corner 2", SIDE_M, SIDE_M, height_m),
        ("Corner 3", 0.0, SIDE_M, height_m),
        ("Return to start", 0.0, 0.0, height_m),
    ]


def main():
    parser = argparse.ArgumentParser(description="Preview the NIDAR 1 x 1 m square mission (NO FLIGHT).")
    parser.add_argument("height", type=float, help="Target flight height in metres above takeoff point")
    args = parser.parse_args()
    if not math.isfinite(args.height) or args.height <= 0:
        parser.error("height must be a finite, positive number of metres")
    print("NIDAR SQUARE MISSION — PLAN ONLY / NO FLIGHT COMMANDS")
    print(f"Target height: {args.height:.2f} m above takeoff point")
    print("Reference: local ENU (X forward, Y left, Z up)")
    print("Square: 1.00 m x 1.00 m")
    for index, (label, x, y, z) in enumerate(waypoints(args.height)):
        print(f"{index}: {label:24s}  X={x:+.2f} m  Y={y:+.2f} m  Z={z:+.2f} m")
    print("Mission end: planned return to start XY; landing is NOT commanded.")
    print("SAFETY: This script does not connect to MAVROS, arm, take off, or move the drone.")


if __name__ == "__main__":
    main()
