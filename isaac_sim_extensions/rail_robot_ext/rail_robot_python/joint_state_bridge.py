"""ROS2 bridge — rail angle + arm joint commands pub/sub + step_sync.

step_sync: Isaac Sim physics step마다 발행하여 aqua_controller와 동기화.
외부에서 joint_commands/rail_cmd를 수신하면 override 모드로 전환.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Optional

from .global_variables import JOINT_NAMES

_RailBridge = None

# 외부 명령 타임아웃 (초) — 이 시간 내에 명령이 없으면 override 해제
_CMD_TIMEOUT = 1.0


def _build_bridge_class() -> bool:
    global _RailBridge
    if _RailBridge is not None:
        return True
    try:
        from sensor_msgs.msg import JointState
        from std_msgs.msg import Float64, Empty
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

        _qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        class RailBridge(Node):
            def __init__(self, robot_name: str = "rail_robot_1",
                         pool_id: str = None):
                super().__init__(f"{robot_name}_bridge")
                self._lock = threading.Lock()
                self._robot_name = robot_name
                self._pool_id = pool_id or robot_name.replace("rail_robot_", "pool_")
                self._rail_angle: float = 0.0
                self._joint_positions: dict = {n: 0.0 for n in JOINT_NAMES}
                self._last_cmd_time: float = 0.0
                self._override: bool = False

                self._joint_state_pub = self.create_publisher(
                    JointState, f"/{robot_name}/joint_states", 10
                )
                self._rail_angle_pub = self.create_publisher(
                    Float64, f"/{robot_name}/rail_angle", 10
                )
                self._step_sync_pub = self.create_publisher(
                    Empty, f"/{self._pool_id}/rail_step_sync", _qos
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
                self.get_logger().info(
                    f"RailBridge ready: {robot_name} | step_sync: /{self._pool_id}/rail_step_sync"
                )

            def _on_joint_cmd(self, msg: JointState) -> None:
                with self._lock:
                    for i, name in enumerate(msg.name):
                        if name in self._joint_positions and i < len(msg.position):
                            self._joint_positions[name] = msg.position[i]
                    self._last_cmd_time = time.time()
                    self._override = True

            def _on_rail_cmd(self, msg: Float64) -> None:
                with self._lock:
                    self._rail_angle = msg.data
                    self._last_cmd_time = time.time()
                    self._override = True

            def get_command(self) -> Optional[dict]:
                """외부 명령 반환. override 모드가 아니면 None 반환."""
                with self._lock:
                    if not self._override:
                        return None
                    if time.time() - self._last_cmd_time > _CMD_TIMEOUT:
                        self._override = False
                        return None
                    return {
                        "override": True,
                        "rail_angle": self._rail_angle,
                        "joint_positions": self._joint_positions.copy(),
                    }

            def publish_joint_states(self, positions: list, rail_angle_rad: float = None) -> None:
                msg = JointState()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.name = JOINT_NAMES
                msg.position = [float(p) for p in positions]
                msg.velocity = [0.0] * len(positions)
                msg.effort = [0.0] * len(positions)
                self._joint_state_pub.publish(msg)

                rail_msg = Float64()
                with self._lock:
                    rail_msg.data = rail_angle_rad if rail_angle_rad is not None else self._rail_angle
                self._rail_angle_pub.publish(rail_msg)

            def publish_step_sync(self) -> None:
                """Physics step 완료 신호 — aqua_controller와 동기화."""
                self._step_sync_pub.publish(Empty())

        _RailBridge = RailBridge
        return True
    except Exception as e:
        print(f"[rail_robot] bridge import error: {e}")
        return False


def create_bridge(robot_name: str = "rail_robot_1", pool_id: str = None):
    if not _build_bridge_class():
        return None
    return _RailBridge(robot_name, pool_id)
