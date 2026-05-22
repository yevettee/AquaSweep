"""Mock publisher node for AquaSweep testing.

Publishes simulated data for dashboard and planner development:
- PoolStatus for each pool
- RobotStatus for each robot
- Placeholder camera detection images
"""

import math
from typing import Dict

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from aqua_interfaces.msg import RobotStatus, PoolStatus

POOL_COUNT = 7


def pool_ids() -> range:
    return range(1, POOL_COUNT + 1)


class MockPublisherNode(Node):
    """Mock node that publishes test data for dashboard/planner development."""

    def __init__(self):
        super().__init__("mock_publisher_node")
        self._tick = 0

        self._pool_pubs: Dict[int, object] = {}
        self._robot_pubs: Dict[int, object] = {}
        self._top_cam_pubs: Dict[int, object] = {}
        self._under_cam_pubs: Dict[int, object] = {}

        for pool_id in pool_ids():
            self._pool_pubs[pool_id] = self.create_publisher(
                PoolStatus,
                f"/pool_{pool_id}/status",
                10,
            )
            self._robot_pubs[pool_id] = self.create_publisher(
                RobotStatus,
                f"/under_robot_{pool_id}/status",
                10,
            )
            self._top_cam_pubs[pool_id] = self.create_publisher(
                Image,
                f"/pool_{pool_id}/top_img_det",
                10,
            )
            self._under_cam_pubs[pool_id] = self.create_publisher(
                Image,
                f"/pool_{pool_id}/under_img_det",
                10,
            )

        self.create_timer(1.0, self._publish_telemetry)
        self.create_timer(2.0, self._publish_images)

        self.get_logger().info(
            f"Mock publisher active for {POOL_COUNT} pools.\n"
            f"  Topics: /pool_<id>/status, /under_robot_<id>/status, "
            f"/pool_<id>/top_img_det, /pool_<id>/under_img_det"
        )

    def _publish_telemetry(self):
        """Publish PoolStatus and RobotStatus for all pools."""
        self._tick += 1
        phase = self._tick * 0.5

        for pool_id in pool_ids():
            pool_msg = PoolStatus()
            pool_msg.pollution_level = 0.5 + 0.4 * math.sin(phase + pool_id)
            pool_msg.fish_type = f"species_{pool_id}"
            # 홀수 pool (1,3,5,7) → 0 (청소 가능), 짝수 pool (2,4,6) → 1 (청소 불가)
            pool_msg.fish_count = 0 if pool_id % 2 == 1 else 1
            pool_msg.fish_count_suspicious = 0
            self._pool_pubs[pool_id].publish(pool_msg)

            robot_msg = RobotStatus()
            robot_msg.state = RobotStatus.IDLE
            robot_msg.battery_level = 0.5 + 0.45 * math.sin(phase * 0.7 + pool_id * 0.3)
            robot_msg.collision_force = 0.1 * (pool_id % 3)
            self._robot_pubs[pool_id].publish(robot_msg)

    def _publish_images(self):
        """Publish placeholder camera images."""
        for pool_id in pool_ids():
            top_img = self._create_placeholder_image(pool_id, "top")
            self._top_cam_pubs[pool_id].publish(top_img)

            under_img = self._create_placeholder_image(pool_id, "under")
            self._under_cam_pubs[pool_id].publish(under_img)

    def _create_placeholder_image(self, pool_id: int, cam_type: str) -> Image:
        """Create a solid-color placeholder image."""
        img = Image()
        img.header.stamp = self.get_clock().now().to_msg()
        img.header.frame_id = f"pool_{pool_id}_{cam_type}_cam"
        img.height = 120
        img.width = 160
        img.encoding = "rgb8"
        img.is_bigendian = 0
        img.step = img.width * 3

        if cam_type == "top":
            r, g, b = (50 + (pool_id * 25) % 200, 100, 150)
        else:
            r, g, b = (100, 50 + (pool_id * 25) % 200, 180)

        img.data = bytes([r, g, b] * (img.width * img.height))
        return img


def main(args=None):
    rclpy.init(args=args)
    node = MockPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
