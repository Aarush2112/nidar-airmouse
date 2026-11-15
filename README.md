# NIDAR AirMouse

GPS-denied indoor drone research on Raspberry Pi 5, Ubuntu 24.04, and ROS 2 Jazzy.

**Current status: tabletop LiDAR localization and 2D mapping experiments. Autonomous flight has not been validated.**

## Project Overview

NIDAR AirMouse aims to navigate indoor spaces without GPS by estimating motion, building maps, and localizing within them. Intended drone capabilities include room exploration, waypoint navigation, obstacle avoidance, and autonomous flight through PX4. These are development objectives; the current LiDAR work is a ground/tabletop research pipeline rather than a flight-ready navigation system.

## Hardware

| Component | Role and integration status |
| --- | --- |
| Raspberry Pi 5 | Onboard companion computer running ROS 2 |
| YDLIDAR X2 | 2D LaserScan input for planar odometry and mapping |
| Intel RealSense D455 | Stereo camera and inertial sensing hardware for alternative camera localization experiments |
| YARI V6X running PX4 | Flight controller; integration of the current LiDAR localization pipeline is pending |
| USB/serial connections and sensor mounts | LiDAR USB-to-UART adapter and camera USB connection; mount geometry must match TF configuration |
| Flight-controller IMU | Intended attitude/motion input for future fusion; not fused by the current LiDAR launchers |

The current tabletop LiDAR TF uses zero translation and a corrected yaw. It is not a measured drone mounting calibration. Power delivery, final airframe installation, and flight configuration require separate validation.

## Software Architecture

Ubuntu 24.04 and ROS 2 Jazzy host the YDLIDAR driver, RTAB-Map ICP Odometry (`rtabmap_odom/icp_odometry`), and asynchronous SLAM Toolbox. The separate camera pipeline uses RealSense infrared stereo, RTAB-Map stereo synchronization, a metadata relay, stereo odometry, and a body-offset/covariance bridge. Legacy OpenVINS research source is retained in the repository.

```mermaid
flowchart TD
    L[YDLIDAR X2] --> S[/scan]
    S --> I[RTAB-Map ICP Odometry]
    I --> O[/odom_icp and odom to base_link TF]
    S --> T[SLAM Toolbox]
    O --> T
    T --> M[/map and map to odom TF]
    M --> D[Saved occupancy maps and serialized pose graphs]
    C[RealSense D455 stereo] --> V[Stereo sync, relay, stereo odometry]
    V --> B[Body-offset bridge and preview odometry]
    B -. future integration .-> F[Localization fusion and PX4]
    O -. future integration .-> F
```

## LiDAR SLAM

The pipeline is `/scan` → ICP odometry → SLAM Toolbox → `/map`. SLAM Toolbox also consumes `/scan` directly and obtains the odometry estimate through TF; `/odom_icp` is the published odometry topic.

```text
map --(SLAM Toolbox)--> odom --(ICP odometry)--> base_link --(static TF)--> laser_frame
```

The existing launchers correct LiDAR orientation with `inverted:=true`, `reversion:=false`, and a `base_link` → `laser_frame` yaw of π radians. Preserve this combination for the tested tabletop mounting and revalidate it after mounting changes. Driver settings request 7 Hz and an 8 m maximum range; these are configuration values, not measured performance guarantees.

`config/nidar_slam_icp_tabletop.yaml` selects mapping mode, a 0.05 m occupancy-grid resolution, and map saving. Saved occupancy maps (`.pgm`/`.yaml`) and serialized pose graphs (`.posegraph`/`.data`) live under `maps/icp_tabletop/`. A saved occupancy grid and a serialized graph serve different purposes; preserve both.

With SLAM active, use a **new, unused absolute output basename** for each save. For example, after checking these names do not already exist:

```bash
source /opt/ros/jazzy/setup.bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: '$HOME/NIDAR AirMouse/maps/icp_tabletop/session_new'}}"
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '$HOME/NIDAR AirMouse/maps/icp_tabletop/pose_graphs/session_new'}"
```

Check each response for `result: 0` and confirm the files were written before stopping. Service request fields were checked against the installed Jazzy service definitions. Saving is a separate step; the launchers do not automatically save on shutdown.

## Visual-Inertial Odometry (VIO)

VIO remains an alternative localization approach. Previous camera-based experiments experienced tracking difficulties around plain white, low-texture walls. **VIO can be reconsidered when the environment provides sufficient visual features and texture**, subject to camera calibration, lighting, motion conditions, and experimental validation. The absence of white walls alone does not establish reliable tracking.

The retained RTAB-Map stereo pipeline should not be interpreted as proof of validated visual-inertial fusion. Historical camera-to-bridge and PX4 reception observations do not establish flight readiness. The V3 bridge publishes preview odometry and TF; the separately tested MAVROS forwarding setup is not captured as a reproducible unified launcher. Historical records report external-vision fusion disabled (`EKF2_EV_CTRL=0`); verify live PX4 state before future integration.

The existing camera experiment entry point is:

```bash
cd "$HOME/NIDAR AirMouse"
bash script/start_nidar_vio_ba5_map1200.sh
```

See [VIO notes](docs/vio.md) and [MAVROS/PX4 notes](docs/mavros_px4.md) for historical details. These older documents may describe earlier development stages; this README records the current project status.

## Current Development Progress

- Completed tabletop LiDAR scan, corrected orientation, ICP odometry, and SLAM mapping tests.
- The project owner reports a successful **25 × 25 cm square-path experiment**, with approximately **1.67 cm return-position error** and **0.18° return-yaw error**. These are experimental return errors from one reported tabletop test, not absolute trajectory accuracy, repeatability statistics, or flight performance. The test was not rerun during documentation synchronization.
- Preserved map snapshots include `nidar_icp_slam_v1`, `nidar_icp_slam_return_v2`, and `nidar_icp_recovery_square_v3`, with serialized graphs for the latter two.
- Unified launchers combine driver, static TF, ICP, and SLAM startup with lifecycle activation attempts and process monitoring. Recovery and no-motion-guess variants are retained for experiments.
- Square and lawnmower mission scripts print waypoint plans; they do not command flight.

## Known Limitations

- ICP can lose tracking; robustness across motion and scene conditions remains incomplete.
- Automatic odometry recovery is unverified. The recovery variant sets `Odom/GuessMotion` to `true` and `Odom/ResetCountdown` to `3`; parameter presence does not prove successful recovery or continuous mapping after a reset.
- Obstacles can appear irregularly in maps; structured obstacle mapping needs further tests.
- Room-scale and large-area accuracy, loop closure, repeatability, and long-duration operation remain incompletely validated.
- Planar LiDAR SLAM alone does not provide a complete 3D drone state estimate or obstacle model.
- Current LiDAR-to-PX4 integration, estimator validity, failsafes, and autonomous flight validation are pending.

## Startup Instructions

These commands target the existing Pi installation at `$HOME/NIDAR AirMouse`. Launchers source `/opt/ros/jazzy/setup.bash` and `ros2_ws/install/setup.bash`. They require the built YDLIDAR driver and its installed `params/X2.yaml`, RTAB-Map odometry, SLAM Toolbox, TF tools, and access to the configured CP2102 serial device. A fresh clone does not include build/install artifacts. See [setup notes](docs/setup.md) for historical dependency context; LiDAR additionally requires SLAM Toolbox and the local driver workspace.

Start **one** unified launcher in a terminal with no competing LiDAR, odometry, SLAM, or static-TF session:

```bash
cd "$HOME/NIDAR AirMouse"
bash scripts/start_nidar_lidar_icp_slam.sh
```

For the experimental recovery configuration, use instead:

```bash
cd "$HOME/NIDAR AirMouse"
bash scripts/start_nidar_lidar_icp_slam_recovery.sh
```

`start_nidar_lidar_icp_slam_no_guess.sh` is an additional experimental variant that disables ICP motion guessing. Lower-level `start_nidar_lidar_icp_tabletop.sh`, `start_nidar_lidar_icp_recovery.sh`, and `start_nidar_lidar_icp_no_guess.sh` start LiDAR/TF/ICP without SLAM.

Check a running session from another terminal:

```bash
source /opt/ros/jazzy/setup.bash
ros2 lifecycle get /slam_toolbox
ros2 topic list
ros2 run tf2_ros tf2_echo map base_link
```

Expect SLAM to be active and `/scan`, `/odom_icp`, and `/map` to be present. Inspect actual data and tracking before moving the test rig. The unified lifecycle loop attempts activation; confirm the final state independently.

Logs are written under `lidar_slam/logs/`: `unified/` and `icp/` for the standard launcher, `unified_recovery/` and `icp_recovery/` for recovery, and corresponding `*_no_guess/` directories for no-guess experiments.

**To stop:** save any desired map and graph first, then press **Ctrl+C in the launch terminal**. Cleanup handlers signal managed children and wait for them. Confirm the launcher exits and its nodes have stopped before restarting; if shutdown stalls, inspect remaining processes and terminate only identified session processes with SIGTERM. Do not start a second pipeline or use broad process-kill commands. Shutdown behavior was reviewed in source, not exercised against hardware during this task.

## Repository Layout

| Path | Contents |
| --- | --- |
| `scripts/` | LiDAR/ICP/SLAM launchers and experimental variants |
| `script/` | Camera pipeline, bridges, diagnostics, and waypoint planners |
| `config/` | SLAM parameters, RViz configuration, and historical snapshots |
| `maps/icp_tabletop/` | Valuable occupancy maps and serialized pose graphs |
| `ros2_ws/src/` | YDLIDAR ROS 2 driver and retained OpenVINS source |
| `lidar/`, `lidar_slam/` | SDK and LiDAR research workspace/notes |
| `docs/`, `tests/` | Supporting documentation and offline planner tests |

Generated ROS builds, logs, caches, credentials, and disposable snapshots are excluded from Git. Saved maps and pose graphs remain versioned. Upstream licenses are retained; no project-wide license has been approved.

## Roadmap

1. Validate mapping of structured obstacles with repeatable geometry and reference measurements.
2. Extend to room-scale SLAM, loop closure, and larger-area repeatability tests.
3. Improve localization robustness, tracking-loss detection, and experimentally validate recovery.
4. Reassess VIO in suitable visual conditions and evaluate calibrated, time-aligned VIO/LiDAR/IMU fusion.
5. Develop obstacle avoidance and navigation using validated localization and maps.
6. Integrate external odometry with PX4; verify frames, timing, covariance, estimator acceptance, and failsafes.
7. Progress through simulation and controlled flight tests before validating autonomous indoor missions.
