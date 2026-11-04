#!/usr/bin/env python3
"""NIDAR 1 m x 1 m lawnmower waypoint planner (no flight commands).

Usage: python3 nidar_lawnmower_mission.py 0.5
The only user-supplied setting is target height in metres.
Coordinates are local ENU offsets relative to the planned takeoff point:
X forward, Y left, Z up. These are planning coordinates, not PX4 NED.
"""

import argparse
import math

AREA_LENGTH_M = 1.0
AREA_WIDTH_M = 1.0
LANE_SPACING_M = 0.25


def waypoints(height_m: float):
    """Return (label, x_m, y_m, z_m) as a continuous serpentine route."""
    points = [("Start / takeoff position", 0.0, 0.0, height_m)]
    lanes = int(round(AREA_WIDTH_M / LANE_SPACING_M)) + 1
    for lane in range(lanes):
        y = lane * LANE_SPACING_M
        x_end = AREA_LENGTH_M if lane % 2 == 0 else 0.0
        if lane > 0:
            x_prev = points[-1][1]
            points.append((f"Shift to lane {lane + 1}", x_prev, y, height_m))
        points.append((f"Traverse lane {lane + 1}", x_end, y, height_m))
    # Return to start inside the square, via the left boundary.
    if points[-1][1] != 0.0:
        points.append(("Return via upper edge", 0.0, AREA_WIDTH_M, height_m))
    points.append(("Return to start", 0.0, 0.0, height_m))
    return points


def main():
    parser = argparse.ArgumentParser(description="Preview the NIDAR 1 x 1 m lawnmower mission (NO FLIGHT).")
    parser.add_argument("height", type=float, help="Target flight height in metres above takeoff point")
    args = parser.parse_args()
    if not math.isfinite(args.height) or args.height <= 0:
        parser.error("height must be a finite, positive number of metres")
    print("NIDAR LAWNMOWER MISSION — PLAN ONLY / NO FLIGHT COMMANDS")
    print(f"Target height: {args.height:.2f} m above takeoff point")
    print("Reference: local ENU (X forward, Y left, Z up)")
    print(f"Coverage area: {AREA_LENGTH_M:.2f} m x {AREA_WIDTH_M:.2f} m")
    print(f"Lane spacing: {LANE_SPACING_M:.2f} m (five parallel lanes)")
    for index, (label, x, y, z) in enumerate(waypoints(args.height)):
        print(f"{index:02d}: {label:24s}  X={x:+.2f} m  Y={y:+.2f} m  Z={z:+.2f} m")
    print("Mission end: planned return to start XY; landing is NOT commanded.")
    print("SAFETY: This script does not connect to MAVROS, arm, take off, or move the drone.")


if __name__ == "__main__":
    main()
