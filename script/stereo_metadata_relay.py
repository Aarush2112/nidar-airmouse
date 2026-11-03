import rclpy
from rclpy.node import Node
from rtabmap_msgs.msg import RGBDImage


class StereoMetadataRelay(Node):
    def __init__(self):
        super().__init__('stereo_metadata_relay')

        self.subscription = self.create_subscription(
            RGBDImage,
            '/rgbd_image',
            self.callback,
            1,
        )
        self.publisher = self.create_publisher(
            RGBDImage,
            '/stereo/rgbd_image',
            1,
        )

        self.count = 0
        self.get_logger().info(
            'Relaying /rgbd_image to /stereo/rgbd_image; '
            'correcting only depth_camera_info.header.frame_id.'
        )

    def callback(self, msg):
        msg.depth_camera_info.header.frame_id = 'camera_infra2_optical_frame'
        self.publisher.publish(msg)

        self.count += 1
        if self.count == 1:
            self.get_logger().info(
                f'First message relayed. Right camera frame: '
                f'{msg.depth_camera_info.header.frame_id}'
            )


def main():
    rclpy.init()
    node = StereoMetadataRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
