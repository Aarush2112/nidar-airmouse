#!/usr/bin/env python3

import time
import subprocess
import threading

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from nav_msgs.msg import Odometry
from rtabmap_msgs.msg import RGBDImage, OdomInfo


DURATION = 6.0

LEFT_IMAGE = '/camera/camera/infra1/image_rect_raw'
RIGHT_IMAGE = '/camera/camera/infra2/image_rect_raw'
LEFT_INFO = '/camera/camera/infra1/camera_info'
RIGHT_INFO = '/camera/camera/infra2/camera_info'
RGBD_TOPIC = '/stereo/rgbd_image'
ODOM_INFO_TOPIC = '/odom_info'
ODOM_TOPIC = '/odom'
rate_data = {'rgbd': [], 'odom': []}

lock = threading.Lock()
data = {
    'left_image': [],
    'right_image': [],
    'left_info': None,
    'right_info': None,
    'rgbd': None,
    'odom': None,
}


def stamp_seconds(stamp):
    return stamp.sec + stamp.nanosec / 1e9


def image_stats(msg):
    """Calculate image statistics without opening a GUI."""
    try:
        enc = msg.encoding.lower()
        if enc not in ('mono8', '8uc1', 'mono16', '16uc1'):
            return {'error': f'Unsupported encoding: {msg.encoding}'}

        dtype = np.uint8 if enc in ('mono8', '8uc1') else np.dtype('<u2')
        arr = np.frombuffer(msg.data, dtype=dtype)

        bytes_per_pixel = 1 if dtype == np.uint8 else 2
        row_elements = msg.step // bytes_per_pixel
        arr = arr.reshape(msg.height, row_elements)[:, :msg.width]

        # Sample pixels for a quick, low-cost diagnostic.
        sample = arr[::4, ::4].astype(np.float32)
        return {
            'width': msg.width,
            'height': msg.height,
            'encoding': msg.encoding,
            'frame': msg.header.frame_id,
            'stamp': stamp_seconds(msg.header.stamp),
            'mean': float(np.mean(sample)),
            'std': float(np.std(sample)),
            'min': int(np.min(sample)),
            'max': int(np.max(sample)),
            'texture': float(np.mean(np.abs(
                np.diff(sample, axis=0)
            ))) if sample.shape[0] > 1 else 0.0,
        }
    except Exception as exc:
        return {'error': str(exc)}


def camera_info_summary(msg):
    return {
        'frame': msg.header.frame_id,
        'size': f'{msg.width}x{msg.height}',
        'distortion_model': msg.distortion_model,
        'D': list(msg.d),
        'K': list(msg.k),
        'P': list(msg.p),
        'stamp': stamp_seconds(msg.header.stamp),
    }


class StereoDiagnostic(Node):
    def __init__(self):
        super().__init__('nidar_stereo_diagnostic')

        self.create_subscription(
            RGBDImage, RGBD_TOPIC,
            lambda m: rate_data['rgbd'].append(time.monotonic()), 10
        )
        self.create_subscription(
            Odometry, ODOM_TOPIC,
            lambda m: rate_data['odom'].append(time.monotonic()), 10
        )

        self.create_subscription(
            Image, LEFT_IMAGE,
            lambda m: self.save_image('left_image', m), 10
        )
        self.create_subscription(
            Image, RIGHT_IMAGE,
            lambda m: self.save_image('right_image', m), 10
        )
        self.create_subscription(
            CameraInfo, LEFT_INFO,
            lambda m: self.save_value('left_info', m), 10
        )
        self.create_subscription(
            CameraInfo, RIGHT_INFO,
            lambda m: self.save_value('right_info', m), 10
        )
        self.create_subscription(
            RGBDImage, RGBD_TOPIC,
            lambda m: self.save_value('rgbd', m), 5
        )
        self.create_subscription(
            OdomInfo, ODOM_INFO_TOPIC,
            lambda m: self.save_value('odom', m), 5
        )

    def save_image(self, key, msg):
        stats = image_stats(msg)
        with lock:
            data[key].append((time.monotonic(), stats))
            data[key] = data[key][-100:]

    def save_value(self, key, msg):
        with lock:
            data[key] = msg


def topic_info(topic):
    try:
        result = subprocess.run(
            ['ros2', 'topic', 'info', topic],
            capture_output=True, text=True, timeout=4
        )
        print(f'\n[{topic}]')
        print((result.stdout or result.stderr).strip() or
              'No output from ros2 topic info')
    except Exception as exc:
        print(f'\n[{topic}] Check failed: {exc}')


def parameter(name):
    try:
        result = subprocess.run(
            ['ros2', 'param', 'get', '/stereo_odometry', name],
            capture_output=True, text=True, timeout=4
        )
        print(f'{name}: {(result.stdout or result.stderr).strip()}')
    except Exception as exc:
        print(f'{name}: check failed: {exc}')


def main():
    print('=' * 68)
    print('NIDAR AirMouse — Stereo Pipeline Diagnostic')
    print('Read-only checks; no parameters or hardware commands are changed.')
    print('=' * 68)

    topics = [
        LEFT_IMAGE, RIGHT_IMAGE, LEFT_INFO, RIGHT_INFO,
        RGBD_TOPIC, ODOM_INFO_TOPIC
    ]
    for topic in topics:
        topic_info(topic)

    rclpy.init()
    node = StereoDiagnostic()
    executor_thread = threading.Thread(
        target=rclpy.spin, args=(node,), daemon=True
    )
    executor_thread.start()

    print(f'\nCollecting live messages for {DURATION:.0f} seconds...')
    time.sleep(DURATION)

    with lock:
        snapshot = {
            'left_image': list(data['left_image']),
            'right_image': list(data['right_image']),
            'left_info': data['left_info'],
            'right_info': data['right_info'],
            'rgbd': data['rgbd'],
            'odom': data['odom'],
        }

    print('\n' + '=' * 68)
    print('1. TOPIC RATE CHECK')
    print('=' * 68)
    for key, topic in (('rgbd', RGBD_TOPIC), ('odom', ODOM_TOPIC)):
        stamps = sorted(rate_data[key])
        elapsed = stamps[-1] - stamps[0] if len(stamps) > 1 else 0.0
        rate = (len(stamps) - 1) / elapsed if elapsed > 0 else 0.0
        print(f'{topic}: {len(stamps)} messages; measured rate: {rate:.2f} Hz')
        if len(stamps) < 2:
            print('  WARNING: insufficient messages to calculate rate')

    print('\n' + '=' * 68)
    print('2. LIVE IMAGE HEALTH')
    print('=' * 68)

    for key, label in [
        ('left_image', 'LEFT INFRARED'),
        ('right_image', 'RIGHT INFRARED'),
    ]:
        samples = snapshot[key]
        print(f'\n{label}: received {len(samples)} messages in {DURATION:.0f}s')
        if not samples:
            print('  ERROR: no images received')
            continue

        _, latest = samples[-1]
        print(f'  Latest sample: {latest}')
        if len(samples) > 1:
            elapsed = samples[-1][0] - samples[0][0]
            rate = (len(samples) - 1) / elapsed if elapsed > 0 else 0
            print(f'  Approximate receive rate: {rate:.1f} Hz')
        if latest.get('std', 0) < 3:
            print('  WARNING: very low image contrast/texture may hinder tracking.')

    left_samples = snapshot['left_image']
    right_samples = snapshot['right_image']
    if left_samples and right_samples:
        l = left_samples[-1][1]
        r = right_samples[-1][1]
        if 'mean' in l and 'mean' in r:
            print('\n  Left/right mean brightness difference:',
                  f'{abs(l["mean"] - r["mean"]):.2f}')
            print('  Left/right contrast (std):',
                  f'{l["std"]:.2f} vs {r["std"]:.2f}')
            print('  Left/right texture metric:',
                  f'{l["texture"]:.2f} vs {r["texture"]:.2f}')
            if abs(l['mean'] - r['mean']) > 30:
                print('  WARNING: large brightness difference; inspect exposure.')

    print('\n' + '=' * 68)
    print('2. CAMERA CALIBRATION')
    print('=' * 68)

    for key, label in [
        ('left_info', 'LEFT CAMERA INFO'),
        ('right_info', 'RIGHT CAMERA INFO'),
    ]:
        msg = snapshot[key]
        print(f'\n{label}:')
        if msg is None:
            print('  ERROR: no CameraInfo received')
            continue
        info = camera_info_summary(msg)
        for k, v in info.items():
            print(f'  {k}: {v}')

    li = snapshot['left_info']
    ri = snapshot['right_info']
    if li and ri:
        if (li.width, li.height) != (ri.width, ri.height):
            print('\n  WARNING: left/right camera dimensions differ.')
        if li.header.frame_id == ri.header.frame_id:
            print('\n  WARNING: both CameraInfo messages have the same frame ID.')
        if li.p[3] == 0 and ri.p[3] == 0:
            print('\n  WARNING: both projection matrices have P[0,3] = 0.')
        elif li.p[3] == 0 and ri.p[3] != 0:
            baseline = abs(ri.p[3] / ri.p[0]) if ri.p[0] else 0
            print(f'\n  Right projection baseline estimate: {baseline:.4f} m')

    print('\n' + '=' * 68)
    print('3. RELAYED STEREO MESSAGE')
    print('=' * 68)

    rgbd = snapshot['rgbd']
    if rgbd is None:
        print(f'No messages received on {RGBD_TOPIC}')
    else:
        print('RGBD timestamp:',
              stamp_seconds(rgbd.header.stamp))
        print('RGB frame:', rgbd.rgb.header.frame_id)
        print('RGB encoding:', rgbd.rgb.encoding)
        print('RGB dimensions:', f'{rgbd.rgb.width}x{rgbd.rgb.height}')
        print('Depth/right frame:', rgbd.depth.header.frame_id)
        print('Depth/right encoding:', rgbd.depth.encoding)
        print('Depth/right dimensions:',
              f'{rgbd.depth.width}x{rgbd.depth.height}')
        print('Left info frame:', rgbd.rgb_camera_info.header.frame_id)
        print('Right info frame:', rgbd.depth_camera_info.header.frame_id)
        print('Keypoints:', len(rgbd.key_points))
        print('3D points:', len(rgbd.points))

    print('\n' + '=' * 68)
    print('4. RTAB-MAP ODOMETRY STATUS')
    print('=' * 68)

    odom = snapshot['odom']
    if odom is None:
        print(f'No messages received on {ODOM_INFO_TOPIC}')
    else:
        for field in (
            'lost', 'matches', 'inliers', 'features',
            'distance_travelled', 'time_estimation', 'interval'
        ):
            if hasattr(odom, field):
                print(f'{field}: {getattr(odom, field)}')
        print('guess translation:',
              odom.guess.pose.pose.position if hasattr(odom.guess, 'pose')
              else odom.guess)

    print('\n' + '=' * 68)
    print('5. CURRENT ODOMETRY PARAMETERS')
    print('=' * 68)
    for name in ('Odom/Strategy', 'Odom/GuessMotion',
                 'Stereo/MaxDisparity', 'Vis/MinInliers'):
        parameter(name)

    print('\n' + '=' * 68)
    print('Diagnostic complete.')
    print('Share the complete output before changing parameters.')
    print('=' * 68)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
