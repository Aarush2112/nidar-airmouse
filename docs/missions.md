# Mission planning

Both programs are planning-only Python scripts. They accept one finite positive height in metres and print coordinates; they do not import ROS, connect to MAVROS, arm, take off, command motion or land.

```bash
python3 script/nidar_square_mission.py 0.5
python3 script/nidar_lawnmower_mission.py 0.5
```

The square has fixed 1 m sides and five waypoint positions including the starting point at target height and return to starting XY. The lawnmower covers a fixed 1 m × 1 m area, five lanes spaced 0.25 m apart, and 12 waypoint positions including the return route.

Coordinates are local planning offsets: X forward, Y left, Z up, relative to the planned takeoff point. The scripts call this local ENU, but their forward/left labels do not establish geographic east/north alignment. They are not PX4 NED coordinates and need an explicit verified frame mapping before any future controller use. All positions are at requested height; no takeoff or landing trajectory is generated.

The project owner ran both on the Pi. Offline checks verify route counts, dimensions, spacing, return positions and input rejection. Autonomous flight remains unvalidated.
