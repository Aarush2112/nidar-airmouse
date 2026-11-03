#!/usr/bin/env python3
import os
import glob
import time
import shutil
import subprocess
from pathlib import Path
from collections import defaultdict

import numpy as np

ROOT = Path.home() / "NIDAR AirMouse"
LOG_DIR = ROOT / "logs" / "vio"
CAPTURE_DIR = LOG_DIR / "stereo_check"

def section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72, flush=True)

def command(args, timeout=5):
    try:
        p = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        return (p.stdout + p.stderr).strip()
    except Exception as e:
        return f"Unavailable: {e}"

def print_command(label, args):
    print(f"\n--- {label} ---")
    result = command(args)
    print(result if result else "(no output)")

def system_checks():
    section("1. SYSTEM HEALTH")
    print("ROS_DISTRO:", os.environ.get("ROS_DISTRO", "(not sourced)"))
    print("Python:", command(["python3", "--version"]))
    print("OpenCV:", end=" ")
    try:
        import cv2
        print(cv2.__version__)
    except Exception as e:
        print("unavailable:", e)

    print("\nDisk:")
    print(command(["df", "-h", str(Path.home())]))

    print("\nMemory:")
    print(command(["free", "-h"]))

    print("\nCPU / processes:")
    print(command(["bash", "-lc",
        "ps -eo pid,pcpu,pmem,comm,args --sort=-pcpu | "
        "grep -E 'stereo_odometry|realsense|stereo_metadata|stereo_sync' | "
        "grep -v grep | head -n 12"]))

    for cmd in (
        ["vcgencmd", "get_throttled"],
        ["vcgencmd", "measure_temp"],
    ):
        if shutil.which(cmd[0]):
            print(command(cmd))

    print("\nROS nodes:")
    print(command(["ros2", "node", "list"]))

def topic_checks():
    section("2. TOPICS AND ACTIVE PARAMETERS")
    topics = [
        "/camera/camera/infra1/image_rect_raw",
        "/camera/camera/infra2/image_rect_raw",
        "/camera/camera/infra1/camera_info",
        "/camera/camera/infra2/camera_info",
        "/camera/camera/imu",
        "/rgbd_image",
        "/stereo/rgbd_image",
        "/odom",
        "/odom_info",
    ]
    for t in topics:
        print(f"\n{t}")
        print(command(["ros2", "topic", "type", t]) or "Topic type unavailable")

    for p in (
        "Rtabmap/ImagesAlreadyRectified",
        "Odom/Strategy",
        "Odom/ImageDecimation",
        "Stereo/MinDisparity",
        "Stereo/MaxDisparity",
        "Stereo/OpticalFlow",
        "Stereo/SSD",
        "Vis/FeatureType",
        "Vis/MinInliers",
        "g2o/Baseline",
        "frame_id",
        "odom_frame_id",
    ):
        print(f"\n{p}:")
        print(command(["ros2", "param", "get", "/stereo_odometry", p]))

def log_checks():
    section("3. RECENT VIO LOG WARNINGS")
    files = sorted(
        glob.glob(str(LOG_DIR / "*")),
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True
    )
    logs = [f for f in files if os.path.isfile(f) and
            (f.endswith(".log") or "log" in Path(f).name.lower())]
    patterns = (
        "stereo correspondences are rejected",
        "not enough inliers",
        "registration failed",
        "failed",
        "error",
        "warning",
        "dropping",
        "delay=",
        "Odom: quality=",
    )
    found = []
    for f in logs[:10]:
        try:
            with open(f, errors="ignore") as fp:
                for line in fp:
                    low = line.lower()
                    if any(p.lower() in low for p in patterns):
                        found.append((os.path.getmtime(f), line.rstrip()))
        except OSError:
            pass

    for _, line in sorted(found, key=lambda x: x[0])[-35:]:
        print(line)

    if not found:
        print("No matching lines found in regular log files.")
        print("Checking ros2 CLI logs is not a substitute for the live node console.")
        print("Log directory:", LOG_DIR)

def stereo_image_check():
    section("4. SAVED STEREO IMAGE / DISPARITY CHECK")
    left_path = CAPTURE_DIR / "left.png"
    right_path = CAPTURE_DIR / "right.png"
    print("Left:", left_path)
    print("Right:", right_path)

    try:
        import cv2
    except Exception as e:
        print("OpenCV unavailable:", e)
        return

    left = cv2.imread(str(left_path), cv2.IMREAD_GRAYSCALE)
    right = cv2.imread(str(right_path), cv2.IMREAD_GRAYSCALE)
    if left is None or right is None:
        print("No saved stereo pair available. Capture one before running this check.")
        return
    if left.shape != right.shape:
        print("IMAGE SIZE MISMATCH:", left.shape, right.shape)
        return

    print("Image size:", left.shape[1], "x", left.shape[0])
    print("Capture modified:", time.ctime(left_path.stat().st_mtime))
    print("Mean intensity L/R:", round(float(left.mean()), 2),
          round(float(right.mean()), 2))
    print("Std intensity L/R:", round(float(left.std()), 2),
          round(float(right.std()), 2))

    orb = cv2.ORB_create(nfeatures=2500)
    k1, d1 = orb.detectAndCompute(left, None)
    k2, d2 = orb.detectAndCompute(right, None)
    print("ORB keypoints L/R:", len(k1), len(k2))

    if d1 is not None and d2 is not None:
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1, d2, k=2)
        good = [m for pair in pairs if len(pair) == 2
                for m, n in [pair] if m.distance < 0.75 * n.distance]
        print("ORB ratio-test matches:", len(good))
        if good:
            dy = np.array([
                abs(k1[m.queryIdx].pt[1] - k2[m.trainIdx].pt[1])
                for m in good
            ])
            print("ORB vertical error percentiles [50, 75, 90]:",
                  np.round(np.percentile(dy, [50, 75, 90]), 2).tolist())
            print("Matches within 1px:", round(100 * float(np.mean(dy <= 1)), 1), "%")
            print("Note: ORB matches alone do not prove rectification.")

    try:
        sgbm = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=128,
            blockSize=5,
            P1=200,
            P2=800,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=2,
            disp12MaxDiff=1,
        )
        disp = sgbm.compute(left, right).astype(np.float32) / 16.0
        valid = np.isfinite(disp) & (disp > 0) & (disp < 128)
        print("SGBM valid pixels:", int(valid.sum()), "/", disp.size)
        print("SGBM valid percentage:", round(100 * float(valid.mean()), 2), "%")
        if valid.any():
            vals = disp[valid]
            q = np.percentile(vals, [10, 25, 50, 75, 90])
            print("Disparity percentiles [10,25,50,75,90]:",
                  np.round(q, 2).tolist())
            med = float(np.median(vals))
            if med > 0:
                z = 425.1183776855469 * 0.095 / med
                print("Approximate median depth:", round(z, 3), "m")
                print("WARNING: approximate SGBM depth, not ground truth.")
    except Exception as e:
        print("SGBM check failed:", repr(e))

def live_ros_check():
    section("5. LIVE ROS SENSOR / ODOMETRY CHECK")
    try:
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image, CameraInfo
        from nav_msgs.msg import Odometry
        from rtabmap_msgs.msg import RGBDImage
    except Exception as e:
        print("ROS message imports failed:", repr(e))
        print("Make sure /opt/ros/jazzy/setup.bash is sourced.")
        return

    try:
        from rtabmap_msgs.msg import OdomInfo
    except Exception:
        OdomInfo = None

    class Inspector(Node):
        def __init__(self):
            super().__init__("nidar_inspection_script")
            self.counts = defaultdict(int)
            self.first = {}
            self.last = {}
            self.cam = {}
            self.rgbd_count = 0
            self.odom_count = 0
            self.odom_info_count = 0
            self.rgbd_delta_ms = []
            self.odom_last = None
            self.odom_info_last = None

            self.create_subscription(
                Image, "/camera/camera/infra1/image_rect_raw",
                lambda m: self.image("left", m), 10)
            self.create_subscription(
                Image, "/camera/camera/infra2/image_rect_raw",
                lambda m: self.image("right", m), 10)
            self.create_subscription(
                Image, "/camera/camera/imu", self.imu_image, 10
            ) if False else None

            self.create_subscription(
                CameraInfo, "/camera/camera/infra1/camera_info",
                lambda m: self.camera("left", m), 10)
            self.create_subscription(
                CameraInfo, "/camera/camera/infra2/camera_info",
                lambda m: self.camera("right", m), 10)
            self.create_subscription(
                RGBDImage, "/stereo/rgbd_image", self.rgbd, 10)
            self.create_subscription(
                Odometry, "/odom", self.odom, 10)
            if OdomInfo:
                self.create_subscription(
                    OdomInfo, "/odom_info", self.odom_info, 10)

        def stamp(self, s):
            return s.sec + s.nanosec / 1e9

        def image(self, name, msg):
            now = time.monotonic()
            self.counts[name] += 1
            if name not in self.first:
                self.first[name] = now
                self.cam[name] = (
                    msg.width, msg.height, msg.encoding, msg.header.frame_id
                )
            self.last[name] = now

        def camera(self, name, msg):
            if name not in self.cam:
                self.cam[name] = {}
            self.cam[name + "_info"] = {
                "frame": msg.header.frame_id,
                "width": msg.width,
                "height": msg.height,
                "fx": msg.k[0],
                "fy": msg.k[4],
                "cx": msg.k[2],
                "cy": msg.k[5],
                "p03": msg.p[3],
                "D": list(msg.d),
                "R": list(msg.r),
            }

        def rgbd(self, msg):
            self.rgbd_count += 1
            a = self.stamp(msg.rgb.header.stamp)
            b = self.stamp(msg.depth.header.stamp)
            self.rgbd_delta_ms.append(abs(a - b) * 1000.0)
            if self.rgbd_count == 1:
                print("\nRGBD first message:")
                print("  left image:", msg.rgb.width, "x", msg.rgb.height,
                      msg.rgb.encoding, msg.rgb.header.frame_id)
                print("  right image:", msg.depth.width, "x", msg.depth.height,
                      msg.depth.encoding, msg.depth.header.frame_id)
                print("  left info frame:", msg.rgb_camera_info.header.frame_id)
                print("  right info frame:", msg.depth_camera_info.header.frame_id)
                print("  fx left/right:", msg.rgb_camera_info.k[0],
                      msg.depth_camera_info.k[0])
                print("  P03 left/right:", msg.rgb_camera_info.p[3],
                      msg.depth_camera_info.p[3])

        def odom(self, msg):
            self.odom_count += 1
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            self.odom_last = (
                msg.header.frame_id, msg.child_frame_id,
                (p.x, p.y, p.z), (q.x, q.y, q.z, q.w)
            )

        def odom_info(self, msg):
            self.odom_info_count += 1
            self.odom_info_last = msg

    rclpy.init()
    node = Inspector()
    duration = 8.0
    start = time.monotonic()
    print(f"Collecting live messages for {duration:.0f} seconds...")
    try:
        while rclpy.ok() and time.monotonic() - start < duration:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        elapsed = max(time.monotonic() - start, 0.001)
        print("\nLive message counts / approximate rates:")
        for name in ("left", "right"):
            rate = node.counts[name] / elapsed
            print(f"  {name}: {node.counts[name]} messages, {rate:.2f} Hz")
            if name in node.cam:
                print("   image:", node.cam[name])
            info = node.cam.get(name + "_info")
            if info:
                print("   camera info:", info)

        print("  /stereo/rgbd_image:", node.rgbd_count,
              f"({node.rgbd_count / elapsed:.2f} Hz)")
        if node.rgbd_delta_ms:
            print("  stereo timestamp delta median/max ms:",
                  round(float(np.median(node.rgbd_delta_ms)), 4),
                  round(float(max(node.rgbd_delta_ms)), 4))
        print("  /odom:", node.odom_count,
              f"({node.odom_count / elapsed:.2f} Hz)")
        if node.odom_last:
            print("  last odometry frame/child:", node.odom_last[:2])
            print("  last position:", node.odom_last[2])
            print("  last quaternion:", node.odom_last[3])
            q = np.array(node.odom_last[3], dtype=float)
            print("  quaternion norm:", round(float(np.linalg.norm(q)), 6))
        print("  /odom_info messages:", node.odom_info_count)
        if node.odom_info_last:
            msg = node.odom_info_last
            for field in ("lost", "matches", "inliers", "features",
                          "local_map_size", "local_keyframes", "time_estimation"):
                if hasattr(msg, field):
                    print(f"  OdomInfo.{field}:", getattr(msg, field))
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

def main():
    print("NIDAR AirMouse — READ-ONLY INSPECTION")
    print("This script does not alter parameters or send flight commands.")
    system_checks()
    topic_checks()
    log_checks()
    stereo_image_check()
    live_ros_check()
    section("INSPECTION COMPLETE")
    print("This is a diagnostic report, not a flight-readiness certification.")
    print("Do not install propellers or attempt autonomous flight until the")
    print("flight controller, estimator, failsafes, and trajectory controller")
    print("have been separately verified.")

if __name__ == "__main__":
    main()
