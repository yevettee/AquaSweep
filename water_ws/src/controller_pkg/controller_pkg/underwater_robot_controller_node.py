"""underwater_robot_controller_node

Publishes geometry_msgs/Twist to /<robot_name>/cmd_vel at CONTROL_HZ.

Phase 1: node start → auto-start spiral.
Phase 2+: replace _auto_start() with an Action Server goal handler.

Topic published: /<robot_name>/cmd_vel  (geometry_msgs/msg/Twist)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from .spiral_planner import SpiralPlanner

CONTROL_HZ = 60.0  # must match Isaac Sim physics rate


class UnderwaterRobotControllerNode(Node):

    def __init__(self) -> None:
        super().__init__('underwater_robot_controller')

        self.declare_parameter('robot_name', 'under_robot_1')
        robot_name = self.get_parameter('robot_name').get_parameter_value().string_value

        self._topic = f'/{robot_name}/cmd_vel'
        self._pub = self.create_publisher(Twist, self._topic, 10)
        self._timer = self.create_timer(1.0 / CONTROL_HZ, self._control_loop)

        self._planner = SpiralPlanner(physics_dt=1.0 / CONTROL_HZ)
        self._running = False

        self.get_logger().info(
            f'Controller ready | topic={self._topic} | '
            f'segments={self._planner.total_segments}'
        )

        # Phase 1: auto-start. Phase 2+: remove this and use Action Server.
        self._auto_start()

    # ------------------------------------------------------------------
    # Public control interface (will be called by Action Server later)
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._planner.reset()
        self._running = True
        self.get_logger().info('Spiral started')

    def stop(self) -> None:
        self._running = False
        self._publish_zero()
        self.get_logger().info('Spiral stopped')

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _auto_start(self) -> None:
        self.start()

    def _control_loop(self) -> None:
        if not self._running:
            return

        if self._planner.is_done:
            self._publish_zero()
            self._running = False
            self.get_logger().info('Spiral complete — robot stopped')
            return

        v, omega = self._planner.next_cmd()
        msg = Twist()
        msg.linear.x = v
        msg.angular.z = omega
        self._pub.publish(msg)

    def _publish_zero(self) -> None:
        self._pub.publish(Twist())


def main(args=None) -> None:
    rclpy.init(args=args)
    node = UnderwaterRobotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
