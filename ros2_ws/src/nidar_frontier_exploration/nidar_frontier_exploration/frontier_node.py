"""Publish occupancy-grid frontier visualizations for ROS 2."""

import math

from geometry_msgs.msg import Point
from nav_msgs.msg import OccupancyGrid
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray

from .frontier_detector import cluster_centroid, cluster_frontiers, detect_frontiers


class FrontierNode(Node):
    """Visualize frontier clusters as ROS markers."""

    def __init__(self):
        """Configure the occupancy grid subscription and marker publisher."""
        super().__init__('nidar_frontier_detector')

        self.declare_parameter('min_cluster_size', 5)
        self.min_cluster_size = int(
            self.get_parameter('min_cluster_size').value
        )

        if self.min_cluster_size < 1:
            raise ValueError('min_cluster_size must be >= 1')

        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        self.subscription = self.create_subscription(
            OccupancyGrid,
            '/map',
            self.map_callback,
            map_qos
        )

        marker_qos = QoSProfile(depth=1)
        marker_qos.reliability = ReliabilityPolicy.RELIABLE
        marker_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        self.publisher = self.create_publisher(
            MarkerArray,
            '/nidar/frontier_markers',
            marker_qos
        )

        self.get_logger().info(
            'NIDAR Frontier Detector started. '
            'Waiting for /map.'
        )

    @staticmethod
    def grid_to_world(x, y, info):
        """Convert grid coordinates to map-frame cell centers."""
        resolution = info.resolution
        origin = info.origin.position
        q = info.origin.orientation

        yaw = math.atan2(
            2.0 * (q.w*q.z + q.x*q.y),
            1.0 - 2.0*(q.y*q.y + q.z*q.z)
        )

        gx = (x + 0.5) * resolution
        gy = (y + 0.5) * resolution

        point = Point()
        point.x = (
            origin.x
            + math.cos(yaw)*gx
            - math.sin(yaw)*gy
        )
        point.y = (
            origin.y
            + math.sin(yaw)*gx
            + math.cos(yaw)*gy
        )
        point.z = origin.z

        return point

    def map_callback(self, msg):
        """Detect and publish frontiers in the received occupancy grid."""
        if msg.info.width == 0 or msg.info.height == 0:
            self.get_logger().warning('Received empty map')
            return

        try:
            frontiers = detect_frontiers(
                msg.data,
                msg.info.width,
                msg.info.height
            )

            clusters = cluster_frontiers(
                frontiers,
                self.min_cluster_size
            )

        except ValueError as exc:
            self.get_logger().error(str(exc))
            return

        output = MarkerArray()

        # Clear markers from the previous map update.
        clear = Marker()
        clear.header.frame_id = msg.header.frame_id
        clear.header.stamp = msg.header.stamp
        clear.action = Marker.DELETEALL
        output.markers.append(clear)

        # Display filtered frontier cells as green points.
        points = Marker()
        points.header.frame_id = msg.header.frame_id
        points.header.stamp = msg.header.stamp
        points.ns = 'frontier_cells'
        points.id = 0
        points.type = Marker.POINTS
        points.action = Marker.ADD
        points.pose.orientation.w = 1.0

        points.scale.x = max(msg.info.resolution, 0.03)
        points.scale.y = max(msg.info.resolution, 0.03)

        points.color.r = 0.1
        points.color.g = 1.0
        points.color.b = 0.2
        points.color.a = 1.0

        for cluster in clusters:
            for x, y in cluster:
                points.points.append(
                    self.grid_to_world(x, y, msg.info)
                )

        output.markers.append(points)

        # Display each cluster centroid as an orange sphere.
        for i, cluster in enumerate(clusters):
            cx, cy = cluster_centroid(cluster)

            marker = Marker()
            marker.header.frame_id = msg.header.frame_id
            marker.header.stamp = msg.header.stamp
            marker.ns = 'frontier_centroids'
            marker.id = i + 1
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD

            marker.pose.position = self.grid_to_world(
                cx, cy, msg.info
            )
            marker.pose.orientation.w = 1.0

            marker.scale.x = 0.09
            marker.scale.y = 0.09
            marker.scale.z = 0.09

            marker.color.r = 1.0
            marker.color.g = 0.5
            marker.color.b = 0.0
            marker.color.a = 1.0

            output.markers.append(marker)

        self.publisher.publish(output)

        self.get_logger().info(
            f'Frontiers: {len(frontiers)} cells | '
            f'Clusters >= {self.min_cluster_size}: '
            f'{len(clusters)}'
        )


def main(args=None):
    """Run the frontier visualization node."""
    rclpy.init(args=args)
    node = None

    try:
        node = FrontierNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
