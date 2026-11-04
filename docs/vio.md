# Preferred D455 stereo pipeline

Use `script/start_nidar_vio_ba5_map1200.sh` for a fresh, non-running bench pipeline only. It starts the RealSense driver, waits for stereo topics, starts synchronization and metadata repair, then starts stereo odometry. Topic advertisement checks do not guarantee data flow. Log files are reused and may be overwritten on startup.

| Setting | Value |
| --- | --- |
| Infrared stream request | 640 × 480 at 30 Hz |
| `OdomF2M/BundleAdjustmentMaxFrames` | 5 |
| `OdomF2M/MaxSize` | 1200 |
| `Vis/MaxFeatures` | 1000 |
| `Odom/ImageDecimation` | 2 |
| Synchronization | approximate |
| image / CameraInfo QoS parameter | 1 / 1 |
| Odometry reference | `camera_link` |
| Camera unified IMU method | 2; not connected to odometry by this launcher |

These settings are embedded in the maintained launcher. `config/odom_before_ba_test.yaml` is a historical dump with different settings, not the preferred configuration and not loaded by the launcher.

The project owner measured approximately 9–10 Hz initially and 4–5 Hz as the local feature map fills; bundle adjustment occupied approximately 40.7% of estimation time. No performance test was repeated during repository preparation.

## Calibration and diagnostics

The driver supplies `/camera/camera/infra1/camera_info` and `/camera/camera/infra2/camera_info`, including intrinsics/projection matrices. No standalone current calibration export exists in the root calibration directory. Preserve the driver-provided calibration; the relay only fixes metadata. Legacy OpenVINS D455 configurations are separate research material, not verified current calibration.

With an already running pipeline, `script/check_stereo_sync.py` measures timestamp pairing over 30 seconds with 20 ms tolerance. `script/diagnose_stereo_full.py`, `script/diagnose_stereo_pipeline.sh`, `script/check_nidar_frequencies.sh` and `script/run_vio_diagnostics.sh` provide existing diagnostics. They can create local reports containing system/process details; review reports before sharing. None was run during this preparation.

Older `start_nidar_vio.sh`, `nidar_master.sh` and `nidar_vio.sh` remain as existing support entry points, but do not select the preferred tuned settings. Review copies of the latter two correct a stale relay path. Their startup behavior was not exercised. Do not run multiple launchers together.
