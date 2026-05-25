"""Robot activation control service.

Provides ROS2 services to activate/deactivate robot ActionGraph per pool:
- /{pool_id}/activate_robot: Create ActionGraph for cmd_vel control
- /{pool_id}/deactivate_robot: Remove ActionGraph

This allows the planner to activate only the robots needed for cleaning,
rather than activating all robots at once via the UI.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import carb

_common = Path(__file__).resolve().parents[2] / "common"
if str(_common) not in sys.path:
    sys.path.insert(0, str(_common))

from ros_isaac_env import (
    AQUA_INTERFACES_INSTALL_HINT,
    configure_isaac_ros_env,
    purge_stale_ros_modules,
)

rclpy = None
Trigger = None
_RobotActivationNode = None
_ROS_IMPORT_ERROR = ""


def _ensure_ros_imports() -> bool:
    """Ensure ROS2 imports are available."""
    global rclpy, Trigger, _RobotActivationNode, _ROS_IMPORT_ERROR

    if rclpy is not None and _RobotActivationNode is not None:
        return True

    if not configure_isaac_ros_env():
        _ROS_IMPORT_ERROR = f"Isaac Sim rclpy not found. {AQUA_INTERFACES_INSTALL_HINT}"
        return False

    purge_stale_ros_modules()

    try:
        import rclpy as _rclpy
        from rclpy.node import Node
        from std_srvs.srv import Trigger as _Trigger

        class RobotActivationNode(Node):
            """ROS2 node providing robot activation control services."""

            def __init__(self, service: "RobotActivationService"):
                super().__init__("robot_activation_service")
                self._service = service

                for pool_id in self._service.pool_ids:
                    self.create_service(
                        _Trigger,
                        f"/{pool_id}/activate_robot",
                        lambda req, resp, pid=pool_id: self._handle_activate(req, resp, pid),
                    )
                    self.create_service(
                        _Trigger,
                        f"/{pool_id}/deactivate_robot",
                        lambda req, resp, pid=pool_id: self._handle_deactivate(req, resp, pid),
                    )

                services_list = ", ".join(
                    f"/{pid}/activate_robot, /{pid}/deactivate_robot"
                    for pid in self._service.pool_ids
                )
                self.get_logger().info(
                    f"RobotActivationService ready | services: {services_list}"
                )

            def _handle_activate(self, request, response, pool_id: str):
                """Handle /{pool_id}/activate_robot service call."""
                success, message = self._service.activate(pool_id)
                response.success = success
                response.message = message
                return response

            def _handle_deactivate(self, request, response, pool_id: str):
                """Handle /{pool_id}/deactivate_robot service call."""
                success, message = self._service.deactivate(pool_id)
                response.success = success
                response.message = message
                return response

        rclpy = _rclpy
        Trigger = _Trigger
        _RobotActivationNode = RobotActivationNode
        _ROS_IMPORT_ERROR = ""
        return True

    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        rclpy = None
        Trigger = None
        _RobotActivationNode = None
        return False


class RobotSpec:
    """Robot specification for a pool."""

    def __init__(
        self,
        idx: int,
        scene_name: str,
        spawn_path: str,
        robot_root_path: str,
        wheel_radius: float,
        wheel_base: float,
    ):
        self.idx = idx
        self.scene_name = scene_name
        self.spawn_path = spawn_path
        self.robot_root_path = robot_root_path
        self.wheel_radius = wheel_radius
        self.wheel_base = wheel_base

    @property
    def robot_name(self) -> str:
        """Robot name for ROS2 topics (e.g., under_robot_1)."""
        return f"under_robot_{self.idx}"


class RobotActivationService:
    """Service to control robot ActionGraph activation/deactivation.
    
    Usage:
        specs = {
            "pool_1": RobotSpec(1, "hippo_1", "/World/Pools/Pool_1/Robot", 
                                "/World/Pools/Pool_1/Robot/hippo", 0.049, 0.4523),
            ...
        }
        service = RobotActivationService(specs)
        service.start()
        # ... later ...
        service.stop()
    """

    def __init__(self, robot_specs: dict[str, RobotSpec]):
        """Initialize the service.
        
        Args:
            robot_specs: Dictionary mapping pool_id to RobotSpec
        """
        self._robot_specs = robot_specs
        self._node = None
        self._thread = None
        self._running = False
        self._started = False
        self._lock = threading.Lock()

    @property
    def pool_ids(self) -> list[str]:
        """List of pool IDs."""
        return list(self._robot_specs.keys())

    @property
    def available(self) -> bool:
        """Check if the ROS2 service is available."""
        return self._started and self._node is not None

    def start(self) -> bool:
        """Start the ROS2 service node."""
        if self._started:
            return self.available

        if not _ensure_ros_imports():
            carb.log_warn(f"[robot_activation_service] ROS2 import failed: {_ROS_IMPORT_ERROR}")
            return False

        try:
            if not rclpy.ok():
                rclpy.init()
            self._node = _RobotActivationNode(self)
            self._running = True
            self._thread = threading.Thread(
                target=self._spin_loop, name="robot_activation_spin", daemon=True
            )
            self._thread.start()
            self._started = True
            carb.log_info("[robot_activation_service] Service started")
            return True
        except Exception as exc:
            carb.log_error(f"[robot_activation_service] Failed to start: {exc}")
            self._cleanup_node()
            return False

    def stop(self):
        """Stop the ROS2 service node."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._cleanup_node()
        self._started = False
        carb.log_info("[robot_activation_service] Service stopped")

    def _cleanup_node(self):
        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None

    def _spin_loop(self):
        while self._running and self._node is not None and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.05)

    def activate(self, pool_id: str) -> tuple[bool, str]:
        """Activate robot ActionGraph for the specified pool.
        
        Args:
            pool_id: Pool identifier (e.g., "pool_1")
            
        Returns:
            (success, message) tuple
        """
        with self._lock:
            spec = self._robot_specs.get(pool_id)
            if spec is None:
                return False, f"Unknown pool: {pool_id}"

            try:
                from underwater_robot_python.actiongraph_setup import (
                    create_cmd_vel_graph,
                    graph_exists,
                )
            except ImportError as e:
                return False, f"Failed to import actiongraph_setup: {e}"

            if graph_exists(spec.robot_name):
                return True, f"Robot {spec.robot_name} already activated"

            graph_path = create_cmd_vel_graph(
                robot_prim_path=spec.robot_root_path,
                robot_name=spec.robot_name,
                wheel_radius=spec.wheel_radius,
                wheel_base=spec.wheel_base,
            )

            if graph_path:
                carb.log_info(f"[robot_activation_service] Activated {spec.robot_name}: {graph_path}")
                return True, f"Robot activated: {graph_path}"
            else:
                carb.log_warn(f"[robot_activation_service] Failed to activate {spec.robot_name}")
                return False, f"Failed to create ActionGraph for {spec.robot_name}"

    def deactivate(self, pool_id: str) -> tuple[bool, str]:
        """Deactivate robot ActionGraph for the specified pool.
        
        Args:
            pool_id: Pool identifier (e.g., "pool_1")
            
        Returns:
            (success, message) tuple
        """
        with self._lock:
            spec = self._robot_specs.get(pool_id)
            if spec is None:
                return False, f"Unknown pool: {pool_id}"

            try:
                from underwater_robot_python.actiongraph_setup import (
                    remove_cmd_vel_graph,
                    graph_exists,
                )
            except ImportError as e:
                return False, f"Failed to import actiongraph_setup: {e}"

            if not graph_exists(spec.robot_name):
                return True, f"Robot {spec.robot_name} already deactivated"

            success = remove_cmd_vel_graph(spec.robot_name)

            if success:
                carb.log_info(f"[robot_activation_service] Deactivated {spec.robot_name}")
                return True, f"Robot deactivated: {spec.robot_name}"
            else:
                carb.log_warn(f"[robot_activation_service] Failed to deactivate {spec.robot_name}")
                return False, f"Failed to remove ActionGraph for {spec.robot_name}"
