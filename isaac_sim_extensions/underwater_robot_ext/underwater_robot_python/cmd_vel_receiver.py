"""Thread-safe cmd_vel subscriber for use inside Isaac Sim.

Isaac Sim runs its own event loop. rclpy must be initialized externally
(in ui_builder.py) and an executor spun in a daemon thread before
instantiating this class.

Usage:
    # ui_builder: configure_isaac_ros_env() -> rclpy.init() first
    receiver = create_cmd_vel_receiver('under_robot_1')
    # in physics step:
    v, omega = receiver.get_cmd()
"""

from __future__ import annotations

import threading
from typing import Optional, Type

_CmdVelReceiver: Optional[Type[object]] = None
_ROS_IMPORT_ERROR = ""


def get_last_ros_import_error() -> str:
    return _ROS_IMPORT_ERROR


def _ensure_receiver_class() -> bool:
    """Define CmdVelReceiver once. Caller must configure env and rclpy.init() first."""
    global _CmdVelReceiver, _ROS_IMPORT_ERROR

    if _CmdVelReceiver is not None:
        return True

    try:
        from geometry_msgs.msg import Twist
        from rclpy.node import Node

        class CmdVelReceiver(Node):
            """Subscribes to /<robot_name>/cmd_vel and stores the latest Twist."""

            def __init__(self, robot_name: str = "under_robot_1") -> None:
                super().__init__(f"{robot_name}_cmd_vel_receiver")
                self._lock = threading.Lock()
                self._linear_x = 0.0
                self._angular_z = 0.0

                topic = f"/{robot_name}/cmd_vel"
                self.create_subscription(Twist, topic, self._callback, 10)
                self.get_logger().info(f"Subscribed to {topic}")

            def _callback(self, msg: Twist) -> None:
                with self._lock:
                    self._linear_x = msg.linear.x
                    self._angular_z = msg.angular.z

            def get_cmd(self) -> tuple[float, float]:
                """Return (linear_x m/s, angular_z rad/s) — safe to call from any thread."""
                with self._lock:
                    return self._linear_x, self._angular_z

        _CmdVelReceiver = CmdVelReceiver
        _ROS_IMPORT_ERROR = ""
        return True
    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        _CmdVelReceiver = None
        return False


def create_cmd_vel_receiver(robot_name: str = "under_robot_1") -> Optional[object]:
    """Create a cmd_vel subscriber node, or None if ROS imports are unavailable."""
    if not _ensure_receiver_class():
        return None
    return _CmdVelReceiver(robot_name)
