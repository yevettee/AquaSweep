"""Mockup vision publisher for testing planner communication.

Publishes fake pool status data for development/testing.

Topics:
    /pool_{id}/status (TankStatus)
"""

import rclpy
from rclpy.node import Node

from aqua_interfaces.msg import TankStatus


class MockupVisionPublisher(Node):
    """Publishes fake pool status for testing."""

    def __init__(self) -> None:
        super().__init__('mockup_vision_publisher')

        self.declare_parameter('pool_ids', ['pool_1', 'pool_2'])
        self.declare_parameter('publish_rate', 1.0)

        pool_ids = self.get_parameter('pool_ids').get_parameter_value().string_array_value
        rate = self.get_parameter('publish_rate').get_parameter_value().double_value

        self._publishers = {}
        for pool_id in pool_ids:
            topic = f'/{pool_id}/status'
            self._publishers[pool_id] = self.create_publisher(TankStatus, topic, 10)
            self.get_logger().info(f'Publishing to {topic}')

        self._timer = self.create_timer(1.0 / rate, self._publish_status)
        self._counter = 0

        self.get_logger().info(
            f'MockupVisionPublisher ready | pools={pool_ids} | rate={rate}Hz'
        )

    def _publish_status(self) -> None:
        """Publish fake status for all pools."""
        self._counter += 1

        for pool_id, pub in self._publishers.items():
            msg = TankStatus()
            msg.pollution_level = 0.3 + (self._counter % 10) * 0.05
            msg.fish_type = 'salmon'
            msg.fish_count = 10 + (hash(pool_id) % 5)
            msg.fish_count_suspicious = self._counter % 3

            pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockupVisionPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
