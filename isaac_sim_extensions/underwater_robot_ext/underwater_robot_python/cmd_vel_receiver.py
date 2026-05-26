"""Thread-safe cmd_vel subscriber + step sync publisher for Isaac Sim.

Isaac Sim runs its own event loop. rclpy must be initialized externally
(in ui_builder.py) and an executor spun in a daemon thread before
instantiating this class.

Usage:
    receiver = create_cmd_vel_receiver('under_robot_1', 'pool_1')
    # in physics step:
    v, omega = receiver.get_cmd()
    receiver.publish_step_sync()   # signal ROS2 controller: ready for next cmd
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
        from std_msgs.msg import Empty
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

        _be1 = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        class CmdVelReceiver(Node):
            """cmd_vel 구독 + step_sync 발행 (물리스텝마다 ROS2 컨트롤러에 신호)."""

            def __init__(self, robot_name: str = "under_robot_1",
                         pool_id: str = None) -> None:
                super().__init__(f"{robot_name}_cmd_vel_receiver")
                self._lock = threading.Lock()
                self._linear_x = 0.0
                self._angular_z = 0.0

                topic = f"/{robot_name}/cmd_vel"
                self.create_subscription(Twist, topic, self._callback, _be1)
                self.get_logger().info(f"Subscribed to {topic}")

                self._sync_pub = None
                if pool_id:
                    sync_topic = f"/{pool_id}/step_sync"
                    self._sync_pub = self.create_publisher(Empty, sync_topic, _be1)
                    self.get_logger().info(f"Step sync publisher: {sync_topic}")

            def _callback(self, msg: Twist) -> None:
                with self._lock:
                    self._linear_x = msg.linear.x
                    self._angular_z = msg.angular.z

            def get_cmd(self) -> tuple[float, float]:
                """Return (linear_x m/s, angular_z rad/s) — safe from any thread."""
                with self._lock:
                    return self._linear_x, self._angular_z

            def publish_step_sync(self) -> None:
                """매 physics step 끝에 호출 — ROS2 컨트롤러가 다음 cmd_vel을 보내도록 신호."""
                if self._sync_pub is not None:
                    self._sync_pub.publish(Empty())

        _CmdVelReceiver = CmdVelReceiver
        _ROS_IMPORT_ERROR = ""
        return True
    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        _CmdVelReceiver = None
        return False


def create_cmd_vel_receiver(robot_name: str = "under_robot_1",
                            pool_id: str = None) -> Optional[object]:
    """Create a cmd_vel subscriber + step sync publisher node, or None if ROS unavailable."""
    if not _ensure_receiver_class():
        return None
    return _CmdVelReceiver(robot_name, pool_id)
