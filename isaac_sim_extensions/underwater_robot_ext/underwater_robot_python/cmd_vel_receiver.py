"""Thread-safe cmd_vel subscriber for use inside Isaac Sim.

Isaac Sim runs its own event loop. rclpy must be initialized externally
(in ui_builder.py) and an executor spun in a daemon thread before
instantiating this class.

Usage:
    receiver = CmdVelReceiver('under_robot_1')   # after rclpy.init()
    # in physics step:
    v, omega = receiver.get_cmd()
"""

import threading

from geometry_msgs.msg import Twist
from rclpy.node import Node


class CmdVelReceiver(Node):
    """Subscribes to /<robot_name>/cmd_vel and stores the latest Twist."""

    def __init__(self, robot_name: str = 'under_robot_1') -> None:
        super().__init__(f'{robot_name}_cmd_vel_receiver')
        self._lock = threading.Lock()
        self._linear_x = 0.0
        self._angular_z = 0.0

        topic = f'/{robot_name}/cmd_vel'
        self.create_subscription(Twist, topic, self._callback, 10)
        self.get_logger().info(f'Subscribed to {topic}')

    def _callback(self, msg: Twist) -> None:
        with self._lock:
            self._linear_x = msg.linear.x
            self._angular_z = msg.angular.z

    def get_cmd(self) -> tuple[float, float]:
        """Return (linear_x m/s, angular_z rad/s) — safe to call from any thread."""
        with self._lock:
            return self._linear_x, self._angular_z
