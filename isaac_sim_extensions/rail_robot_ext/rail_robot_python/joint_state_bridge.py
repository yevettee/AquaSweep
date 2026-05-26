"""ROS2 bridge — rail angle + arm joint commands pub/sub."""

from __future__ import annotations

import math
import threading
from typing import Optional

from .global_variables import JOINT_NAMES

_RailBridge = None


def _build_bridge_class() -> bool:
    global _RailBridge
    if _RailBridge is not None:
        return True
    try:
        from sensor_msgs.msg import JointState
        from std_msgs.msg import Float64
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

        _qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        class RailBridge(Node):
            def __init__(self, robot_name: str = "rail_robot_1"):
                super().__init__(f"{robot_name}_bridge")
                self._lock = threading.Lock()
                self._robot_name = robot_name
                self._rail_angle: float = 0.0
                self._joint_positions: dict = {n: 0.0 for n in JOINT_NAMES}

                self._joint_state_pub = self.create_publisher(
                    JointState, f"/{robot_name}/joint_states", 10
                )
                self._rail_angle_pub = self.create_publisher(
                    Float64, f"/{robot_name}/rail_angle", 10
                )
                self.create_subscription(
                    JointState,
                    f"/{robot_name}/joint_commands",
                    self._on_joint_cmd,
                    _qos,
                )
                self.create_subscription(
                    Float64,
                    f"/{robot_name}/rail_cmd",
                    self._on_rail_cmd,
                    _qos,
                )
                self.get_logger().info(f"RailBridge ready: {robot_name}")

            def _on_joint_cmd(self, msg: JointState) -> None:
                with self._lock:
                    for i, name in enumerate(msg.name):
                        if name in self._joint_positions and i < len(msg.position):
                            self._joint_positions[name] = msg.position[i]

            def _on_rail_cmd(self, msg: Float64) -> None:
                with self._lock:
                    self._rail_angle = msg.data

            def get_command(self) -> Optional[dict]:
                with self._lock:
                    return {
                        "rail_angle": self._rail_angle,
                        "joint_positions": self._joint_positions.copy(),
                    }

            def publish_joint_states(self, positions: list) -> None:
                msg = JointState()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.name = JOINT_NAMES
                msg.position = [float(p) for p in positions]
                msg.velocity = [0.0] * len(positions)
                msg.effort = [0.0] * len(positions)
                self._joint_state_pub.publish(msg)

                rail_msg = Float64()
                with self._lock:
                    rail_msg.data = self._rail_angle
                self._rail_angle_pub.publish(rail_msg)

        _RailBridge = RailBridge
        return True
    except Exception as e:
        print(f"[rail_robot] bridge import error: {e}")
        return False


def create_bridge(robot_name: str = "rail_robot_1"):
    if not _build_bridge_class():
        return None
    return _RailBridge(robot_name)
