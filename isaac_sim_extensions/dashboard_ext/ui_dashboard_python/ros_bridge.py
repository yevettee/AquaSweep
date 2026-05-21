# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 bridge for dashboard_ext: subscribes to tank telemetry and sends CleanFloor goals."""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Type

from .ros_config import tank_clean_floor_action, tank_ids, tank_robot_status_topic, tank_status_topic

_common = Path(__file__).resolve().parents[2] / "common"
if str(_common) not in sys.path:
    sys.path.insert(0, str(_common))

from ros_isaac_env import (  # noqa: E402
    AQUA_INTERFACES_INSTALL_HINT,
    configure_isaac_ros_env,
    purge_stale_ros_modules,
)

rclpy = None  # type: ignore
CleanFloor = None  # type: ignore
RobotStatus = None  # type: ignore
TankStatus = None  # type: ignore
ActionClient = None  # type: ignore
_DashboardRosNode: Optional[Type[object]] = None

_ROS_IMPORT_ERROR = ""

ROBOT_STATE_NAMES = {
    0: "IDLE",
    1: "RUNNING",
    2: "PAUSED",
    3: "DISCHARGED",
}


@dataclass
class TankSnapshot:
    tank: Optional[object] = None
    robot: Optional[object] = None
    clean_progress: Optional[float] = None
    clean_running: bool = False
    last_error: Optional[str] = None


def _ensure_ros_imports() -> bool:
    global rclpy, CleanFloor, RobotStatus, TankStatus, ActionClient, _DashboardRosNode, _ROS_IMPORT_ERROR

    if rclpy is not None and _DashboardRosNode is not None:
        return True

    if not configure_isaac_ros_env():
        _ROS_IMPORT_ERROR = f"Isaac Sim rclpy/aqua_interfaces not found. {AQUA_INTERFACES_INSTALL_HINT}"
        return False

    purge_stale_ros_modules()

    try:
        import rclpy as _rclpy
        from aqua_interfaces.action import CleanFloor as _CleanFloor
        from aqua_interfaces.msg import RobotStatus as _RobotStatus, TankStatus as _TankStatus
        from rclpy.action import ActionClient as _ActionClient
        from rclpy.node import Node

        class DashboardRosNode(Node):
            def __init__(self, bridge: "RosBridge"):
                super().__init__("dashboard_ros_bridge")
                self._bridge = bridge

                for tank_id in tank_ids():
                    self.create_subscription(
                        _TankStatus,
                        tank_status_topic(tank_id),
                        lambda msg, tid=tank_id: self._bridge._on_tank_status(tid, msg),
                        10,
                    )
                    self.create_subscription(
                        _RobotStatus,
                        tank_robot_status_topic(tank_id),
                        lambda msg, tid=tank_id: self._bridge._on_robot_status(tid, msg),
                        10,
                    )
                    client = _ActionClient(self, _CleanFloor, tank_clean_floor_action(tank_id))
                    self._bridge._action_clients[tank_id] = client

        rclpy = _rclpy
        CleanFloor = _CleanFloor
        RobotStatus = _RobotStatus
        TankStatus = _TankStatus
        ActionClient = _ActionClient
        _DashboardRosNode = DashboardRosNode
        _ROS_IMPORT_ERROR = ""
        return True
    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        rclpy = None
        CleanFloor = None
        RobotStatus = None
        TankStatus = None
        ActionClient = None
        _DashboardRosNode = None
        return False


class RosBridge:
    def __init__(self):
        self._lock = threading.Lock()
        self._snapshots: Dict[int, TankSnapshot] = {tid: TankSnapshot() for tid in tank_ids()}
        self._action_clients: Dict[int, object] = {}
        self._node: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._started = False
        self.unavailable_reason: Optional[str] = None

    @property
    def available(self) -> bool:
        return self._started and self._node is not None

    def start(self) -> bool:
        if self._started:
            return self.available

        if not _ensure_ros_imports():
            self.unavailable_reason = f"ROS2 import failed: {_ROS_IMPORT_ERROR}"
            return False

        try:
            if not rclpy.ok():
                rclpy.init()
            self._node = _DashboardRosNode(self)
            self._running = True
            self._thread = threading.Thread(target=self._spin_loop, name="dashboard_ros_spin", daemon=True)
            self._thread.start()
            self._started = True
            self.unavailable_reason = None
            return True
        except Exception as exc:
            self.unavailable_reason = f"ROS2 start failed: {exc}"
            self._cleanup_node()
            return False

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._cleanup_node()
        self._started = False

    def _cleanup_node(self):
        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None
        self._action_clients.clear()

    def _spin_loop(self):
        while self._running and self._node is not None and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.05)

    def get_snapshot(self, tank_id: int) -> TankSnapshot:
        with self._lock:
            snap = self._snapshots.get(tank_id)
            if snap is None:
                return TankSnapshot()
            return TankSnapshot(
                tank=snap.tank,
                robot=snap.robot,
                clean_progress=snap.clean_progress,
                clean_running=snap.clean_running,
                last_error=snap.last_error,
            )

    def send_clean_floor(self, tank_id: int) -> str:
        if not self.available:
            return self.unavailable_reason or "ROS2 bridge not available"

        with self._lock:
            snap = self._snapshots[tank_id]
            if snap.clean_running:
                return "CleanFloor already running"

        client = self._action_clients.get(tank_id)
        if client is None:
            return f"No action client for tank {tank_id}"

        if not client.wait_for_server(timeout_sec=0.5):
            msg = f"CleanFloor server not available: {tank_clean_floor_action(tank_id)}"
            self._set_error(tank_id, msg)
            return msg

        goal = CleanFloor.Goal()
        send_future = client.send_goal_async(
            goal,
            feedback_callback=lambda fb, tid=tank_id: self._on_feedback(tid, fb),
        )
        send_future.add_done_callback(lambda fut, tid=tank_id: self._on_goal_sent(tid, fut))
        return ""

    def _on_tank_status(self, tank_id: int, msg):
        with self._lock:
            self._snapshots[tank_id].tank = msg

    def _on_robot_status(self, tank_id: int, msg):
        with self._lock:
            self._snapshots[tank_id].robot = msg

    def _on_goal_sent(self, tank_id: int, future):
        try:
            goal_handle = future.result()
        except Exception as exc:
            self._set_error(tank_id, f"Failed to send goal: {exc}")
            return

        if not goal_handle.accepted:
            self._set_error(tank_id, "CleanFloor goal rejected")
            return

        with self._lock:
            snap = self._snapshots[tank_id]
            snap.clean_running = True
            snap.clean_progress = 0.0
            snap.last_error = None

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(lambda fut, tid=tank_id: self._on_result(tid, fut))

    def _on_feedback(self, tank_id: int, feedback_msg):
        with self._lock:
            snap = self._snapshots[tank_id]
            snap.clean_progress = feedback_msg.feedback.progress

    def _on_result(self, tank_id: int, future):
        try:
            result = future.result().result
            success = result.success
        except Exception as exc:
            self._set_error(tank_id, f"CleanFloor failed: {exc}")
            return

        with self._lock:
            snap = self._snapshots[tank_id]
            snap.clean_running = False
            if success:
                snap.clean_progress = 1.0
                snap.last_error = None
            else:
                snap.last_error = "CleanFloor finished with success=False"

    def _set_error(self, tank_id: int, message: str):
        with self._lock:
            snap = self._snapshots[tank_id]
            snap.clean_running = False
            snap.last_error = message
