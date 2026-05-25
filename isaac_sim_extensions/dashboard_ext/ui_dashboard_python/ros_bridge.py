# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 bridge for dashboard_ext: subscribes to tank telemetry, camera images, and sends start commands."""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Type

from .ros_config import (
    planner_start_service,
    pool_clean_floor_action,
    pool_ids,
    pool_robot_status_topic,
    pool_status_topic,
    pool_top_cam_det_topic,
    pool_under_cam_det_topic,
)

_common = Path(__file__).resolve().parents[2] / "common"
if str(_common) not in sys.path:
    sys.path.insert(0, str(_common))

from ros_isaac_env import (  # noqa: E402
    AQUA_INTERFACES_INSTALL_HINT,
    configure_isaac_ros_env,
    purge_stale_ros_modules,
)

rclpy = None  # type: ignore
RobotStatus = None  # type: ignore
PoolStatus = None  # type: ignore
CleanFloor = None  # type: ignore
Image = None  # type: ignore
Trigger = None  # type: ignore
_DashboardRosNode: Optional[Type[object]] = None

_ROS_IMPORT_ERROR = ""

ROBOT_STATE_NAMES = {
    0: "IDLE",
    1: "RUNNING",
    2: "PAUSED",
    3: "DISCHARGED",
}


@dataclass
class PoolSnapshot:
    tank: Optional[object] = None
    robot: Optional[object] = None
    top_cam_image: Optional[bytes] = None
    top_cam_dims: tuple = field(default_factory=lambda: (0, 0))
    under_cam_image: Optional[bytes] = None
    under_cam_dims: tuple = field(default_factory=lambda: (0, 0))
    clean_progress: Optional[float] = None
    clean_running: bool = False
    last_error: Optional[str] = None


# Backward compatibility alias
TankSnapshot = PoolSnapshot


def _ensure_ros_imports() -> bool:
    global rclpy, RobotStatus, PoolStatus, CleanFloor, Image, Trigger, _DashboardRosNode, _ROS_IMPORT_ERROR

    if rclpy is not None and _DashboardRosNode is not None:
        return True

    if not configure_isaac_ros_env():
        _ROS_IMPORT_ERROR = f"Isaac Sim rclpy/aqua_interfaces not found. {AQUA_INTERFACES_INSTALL_HINT}"
        return False

    purge_stale_ros_modules()

    try:
        import rclpy as _rclpy
        from aqua_interfaces.action import CleanFloor as _CleanFloor
        from aqua_interfaces.msg import RobotStatus as _RobotStatus, PoolStatus as _PoolStatus
        from rclpy.action import ActionClient as _ActionClient
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Image
        from std_srvs.srv import Trigger as _Trigger

        class DashboardRosNode(Node):
            def __init__(self, bridge: "RosBridge"):
                super().__init__("dashboard_ros_bridge")
                self._bridge = bridge

                self._planner_start_client = self.create_client(
                    _Trigger, planner_start_service()
                )

                for pool_id in pool_ids():
                    self.create_subscription(
                        _PoolStatus,
                        pool_status_topic(pool_id),
                        lambda msg, pid=pool_id: self._bridge._on_pool_status(pid, msg),
                        10,
                    )
                    self.create_subscription(
                        _RobotStatus,
                        pool_robot_status_topic(pool_id),
                        lambda msg, pid=pool_id: self._bridge._on_robot_status(pid, msg),
                        10,
                    )
                    self.create_subscription(
                        _Image,
                        pool_top_cam_det_topic(pool_id),
                        lambda msg, pid=pool_id: self._bridge._on_top_cam_image(pid, msg),
                        10,
                    )
                    self.create_subscription(
                        _Image,
                        pool_under_cam_det_topic(pool_id),
                        lambda msg, pid=pool_id: self._bridge._on_under_cam_image(pid, msg),
                        10,
                    )

                    action_client = _ActionClient(
                        self, _CleanFloor, pool_clean_floor_action(pool_id)
                    )
                    self._bridge._pool_action_clients[pool_id] = action_client

        rclpy = _rclpy
        RobotStatus = _RobotStatus
        PoolStatus = _PoolStatus
        CleanFloor = _CleanFloor
        Image = _Image
        Trigger = _Trigger
        _DashboardRosNode = DashboardRosNode
        _ROS_IMPORT_ERROR = ""
        return True
    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        rclpy = None
        RobotStatus = None
        PoolStatus = None
        CleanFloor = None
        Image = None
        Trigger = None
        _DashboardRosNode = None
        return False


class RosBridge:
    def __init__(self):
        self._lock = threading.Lock()
        self._snapshots: Dict[int, PoolSnapshot] = {pid: PoolSnapshot() for pid in pool_ids()}
        self._pool_action_clients: Dict[int, Any] = {}
        self._node: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._started = False
        self._global_task_active = False
        self.unavailable_reason: Optional[str] = None

    @property
    def available(self) -> bool:
        return self._started and self._node is not None

    @property
    def global_task_active(self) -> bool:
        with self._lock:
            return self._global_task_active

    def any_pool_running(self) -> bool:
        with self._lock:
            return any(snap.clean_running for snap in self._snapshots.values())

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
        self._pool_action_clients.clear()

    def _spin_loop(self):
        while self._running and self._node is not None and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.05)

    def get_snapshot(self, pool_id: int) -> PoolSnapshot:
        with self._lock:
            snap = self._snapshots.get(pool_id)
            if snap is None:
                return PoolSnapshot()
            return PoolSnapshot(
                tank=snap.tank,
                robot=snap.robot,
                top_cam_image=snap.top_cam_image,
                top_cam_dims=snap.top_cam_dims,
                under_cam_image=snap.under_cam_image,
                under_cam_dims=snap.under_cam_dims,
                clean_progress=snap.clean_progress,
                clean_running=snap.clean_running,
                last_error=snap.last_error,
            )

    def call_global_start(self) -> str:
        """Call /planner/start service to start cleaning all eligible pools."""
        if not self.available:
            return self.unavailable_reason or "ROS2 bridge not available"

        if self._global_task_active or self.any_pool_running():
            return "Task already running"

        client = self._node._planner_start_client
        # Non-blocking service check
        if not client.service_is_ready():
            return f"Planner start service not available: {planner_start_service()}"

        request = Trigger.Request()
        future = client.call_async(request)
        future.add_done_callback(self._on_global_start_response)

        with self._lock:
            self._global_task_active = True

        return ""

    def call_pool_start(self, pool_id: int) -> str:
        """Send CleanFloor action directly to Controller (bypasses Planner, no fish_count check)."""
        if not self.available:
            return self.unavailable_reason or "ROS2 bridge not available"

        with self._lock:
            snap = self._snapshots.get(pool_id)
            if snap and snap.clean_running:
                return f"Pool {pool_id}: Task already running"
            if self._global_task_active:
                return "Global task in progress"

        action_client = self._pool_action_clients.get(pool_id)
        if action_client is None:
            return f"No action client for pool {pool_id}"

        # Non-blocking server check
        if not action_client.server_is_ready():
            msg = f"CleanFloor action server not available: {pool_clean_floor_action(pool_id)}"
            self._set_error(pool_id, msg)
            return msg

        goal_msg = CleanFloor.Goal()
        send_goal_future = action_client.send_goal_async(
            goal_msg,
            feedback_callback=lambda fb, pid=pool_id: self._on_action_feedback(pid, fb)
        )
        send_goal_future.add_done_callback(
            lambda fut, pid=pool_id: self._on_goal_response(pid, fut)
        )

        with self._lock:
            snap = self._snapshots.get(pool_id)
            if snap:
                snap.clean_running = True
                snap.clean_progress = 0.0

        return ""

    def _on_global_start_response(self, future):
        try:
            response = future.result()
            if not response.success:
                with self._lock:
                    self._global_task_active = False
        except Exception:
            with self._lock:
                self._global_task_active = False

    def _on_goal_response(self, pool_id: int, future):
        """Handle goal acceptance/rejection from Controller."""
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self._set_error(pool_id, "Goal rejected by controller")
                return
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(
                lambda fut, pid=pool_id: self._on_action_result(pid, fut)
            )
        except Exception as exc:
            self._set_error(pool_id, f"Goal send failed: {exc}")

    def _on_action_feedback(self, pool_id: int, feedback_msg):
        """Handle CleanFloor action feedback (progress updates)."""
        with self._lock:
            snap = self._snapshots.get(pool_id)
            if snap:
                snap.clean_progress = feedback_msg.feedback.progress

    def _on_action_result(self, pool_id: int, future):
        """Handle CleanFloor action result (completion)."""
        try:
            result = future.result().result
            with self._lock:
                snap = self._snapshots.get(pool_id)
                if snap:
                    snap.clean_running = False
                    snap.clean_progress = 1.0 if result.success else snap.clean_progress
                    if not result.success:
                        snap.last_error = "CleanFloor action failed"
                self._check_task_completion()
        except Exception as exc:
            self._set_error(pool_id, f"Action result failed: {exc}")

    def _on_pool_status(self, pool_id: int, msg):
        with self._lock:
            self._snapshots[pool_id].tank = msg
            self._check_task_completion()

    def _on_robot_status(self, pool_id: int, msg):
        with self._lock:
            snap = self._snapshots[pool_id]
            snap.robot = msg
            if msg.state == 0:  # IDLE
                if snap.clean_running:
                    snap.clean_running = False
                    snap.clean_progress = 1.0
            elif msg.state == 1:  # RUNNING
                if not snap.clean_running:
                    snap.clean_running = True
            self._check_task_completion()

    def _on_top_cam_image(self, pool_id: int, msg):
        with self._lock:
            snap = self._snapshots[pool_id]
            snap.top_cam_image = bytes(msg.data)
            snap.top_cam_dims = (msg.width, msg.height)

    def _on_under_cam_image(self, pool_id: int, msg):
        with self._lock:
            snap = self._snapshots[pool_id]
            snap.under_cam_image = bytes(msg.data)
            snap.under_cam_dims = (msg.width, msg.height)

    def _check_task_completion(self):
        if self._global_task_active:
            if not any(snap.clean_running for snap in self._snapshots.values()):
                self._global_task_active = False

    def _set_error(self, pool_id: int, message: str):
        with self._lock:
            snap = self._snapshots[pool_id]
            snap.clean_running = False
            snap.last_error = message
