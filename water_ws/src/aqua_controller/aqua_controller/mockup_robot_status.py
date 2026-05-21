"""Mockup robot status publisher for testing.

Publishes fake robot status data for development/testing.

Topics:
    /under_robot_{id}/status (RobotStatus)
"""

import rclpy
from rclpy.node import Node

from aqua_interfaces.msg import RobotStatus


class MockupRobotStatus(Node):
    """Publishes fake robot status for testing."""

    def __init__(self) -> None:
        super().__init__('mockup_robot_status')

        self.declare_parameter('robot_name', 'under_robot_1')
        self.declare_parameter('publish_rate', 1.0)

        robot_name = self.get_parameter('robot_name').get_parameter_value().string_value
        rate = self.get_parameter('publish_rate').get_parameter_value().double_value

        self._topic = f'/{robot_name}/status'
        self._pub = self.create_publisher(RobotStatus, self._topic, 10)

        self._timer = self.create_timer(1.0 / rate, self._publish_status)
        self._battery = 1.0

        self.get_logger().info(
            f'MockupRobotStatus ready | topic={self._topic} | rate={rate}Hz'
        )

    def _publish_status(self) -> None:
        """Publish fake robot status."""
        msg = RobotStatus()
        msg.state = RobotStatus.IDLE
        msg.battery_level = self._battery
        msg.collision_force = 0.0

        self._battery = max(0.0, self._battery - 0.001)

        self._pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockupRobotStatus()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
