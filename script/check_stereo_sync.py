import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from message_filters import Subscriber, ApproximateTimeSynchronizer
from collections import deque

class StereoSyncCheck(Node):
    def __init__(self):
        super().__init__('stereo_sync_check')
        self.left = Subscriber(
            self, Image, '/camera/camera/infra1/image_rect_raw'
        )
        self.right = Subscriber(
            self, Image, '/camera/camera/infra2/image_rect_raw'
        )
        self.sync = ApproximateTimeSynchronizer(
            [self.left, self.right],
            queue_size=30,
            slop=0.02
        )
        self.sync.registerCallback(self.callback)
        self.skews_ms = deque(maxlen=300)
        self.count = 0
        self.get_logger().info(
            'Measuring stereo timestamp skew for 30 seconds; '
            'maximum pairing tolerance is 20 ms.'
        )
        self.create_timer(30.0, self.report)

    def callback(self, left, right):
        lt = left.header.stamp.sec + left.header.stamp.nanosec * 1e-9
        rt = right.header.stamp.sec + right.header.stamp.nanosec * 1e-9
        skew_ms = (rt - lt) * 1000.0
        self.skews_ms.append(skew_ms)
        self.count += 1

    def report(self):
        if not self.skews_ms:
            self.get_logger().error(
                'No synchronized pairs received. Check topic activity and QoS.'
            )
        else:
            values = sorted(self.skews_ms)
            n = len(values)
            median = values[n // 2]
            maximum = max(abs(v) for v in values)
            self.get_logger().info(
                f'Pairs: {self.count}; '
                f'median signed skew: {median:.3f} ms; '
                f'max absolute skew: {maximum:.3f} ms'
            )
        rclpy.shutdown()

def main():
    rclpy.init()
    node = StereoSyncCheck()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
