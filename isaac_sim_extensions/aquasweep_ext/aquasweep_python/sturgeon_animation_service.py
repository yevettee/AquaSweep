"""Sturgeon animation control service.

Provides ROS2 services to pause/resume sturgeon animation:
- /sturgeon/pause: Pause all sturgeon animations (for cleaning phase)
- /sturgeon/resume: Resume all sturgeon animations (for monitoring phase)

This allows reducing GPU/CPU load during robot cleaning by stopping
unnecessary sturgeon transform updates (~35 USD Set() calls per physics step).
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import carb

if TYPE_CHECKING:
    from water_tank_env_python.sturgeon_animator import SturgeonAnimator

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
_SturgeonAnimNode = None
_ROS_IMPORT_ERROR = ""


def _ensure_ros_imports() -> bool:
    """Ensure ROS2 imports are available."""
    global rclpy, Trigger, _SturgeonAnimNode, _ROS_IMPORT_ERROR

    if rclpy is not None and _SturgeonAnimNode is not None:
        return True

    if not configure_isaac_ros_env():
        _ROS_IMPORT_ERROR = f"Isaac Sim rclpy not found. {AQUA_INTERFACES_INSTALL_HINT}"
        return False

    purge_stale_ros_modules()

    try:
        import rclpy as _rclpy
        from rclpy.node import Node
        from std_srvs.srv import Trigger as _Trigger

        class SturgeonAnimNode(Node):
            """ROS2 node providing sturgeon animation control services."""

            def __init__(self, service: "SturgeonAnimationService"):
                super().__init__("sturgeon_animation_service")
                self._service = service

                self.create_service(
                    _Trigger,
                    "/sturgeon/pause",
                    self._handle_pause,
                )
                self.create_service(
                    _Trigger,
                    "/sturgeon/resume",
                    self._handle_resume,
                )

                self.get_logger().info(
                    "SturgeonAnimationService ready | services: /sturgeon/pause, /sturgeon/resume"
                )

            def _handle_pause(self, request, response):
                """Handle /sturgeon/pause service call."""
                success, message = self._service.pause()
                response.success = success
                response.message = message
                return response

            def _handle_resume(self, request, response):
                """Handle /sturgeon/resume service call."""
                success, message = self._service.resume()
                response.success = success
                response.message = message
                return response

        rclpy = _rclpy
        Trigger = _Trigger
        _SturgeonAnimNode = SturgeonAnimNode
        _ROS_IMPORT_ERROR = ""
        return True

    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        rclpy = None
        Trigger = None
        _SturgeonAnimNode = None
        return False


class SturgeonAnimationService:
    """Service to control sturgeon animation pause/resume.
    
    Usage:
        from water_tank_env_python.sturgeon_animator import SturgeonAnimator
        
        animator = SturgeonAnimator()
        service = SturgeonAnimationService(animator)
        service.start()
        # ... later ...
        service.stop()
    """

    def __init__(self, animator: "SturgeonAnimator"):
        """Initialize the service.
        
        Args:
            animator: SturgeonAnimator instance to control
        """
        self._animator = animator
        self._node = None
        self._thread = None
        self._running = False
        self._started = False
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        """Check if the ROS2 service is available."""
        return self._started and self._node is not None

    @property
    def is_paused(self) -> bool:
        """Check if animation is currently paused."""
        return not self._animator.enabled

    def start(self) -> bool:
        """Start the ROS2 service node."""
        if self._started:
            return self.available

        if not _ensure_ros_imports():
            carb.log_warn(f"[sturgeon_anim_service] ROS2 import failed: {_ROS_IMPORT_ERROR}")
            return False

        try:
            if not rclpy.ok():
                rclpy.init()
            self._node = _SturgeonAnimNode(self)
            self._running = True
            self._thread = threading.Thread(
                target=self._spin_loop, name="sturgeon_anim_spin", daemon=True
            )
            self._thread.start()
            self._started = True
            carb.log_info("[sturgeon_anim_service] Service started")
            return True
        except Exception as exc:
            carb.log_error(f"[sturgeon_anim_service] Failed to start: {exc}")
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
        carb.log_info("[sturgeon_anim_service] Service stopped")

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

    def pause(self) -> tuple[bool, str]:
        """Pause sturgeon animation.
        
        Returns:
            (success, message) tuple
        """
        with self._lock:
            if not self._animator.enabled:
                return True, "Sturgeon animation already paused"
            
            self._animator.set_enabled(False)
            carb.log_info("[sturgeon_anim_service] Animation paused")
            return True, "Sturgeon animation paused"

    def resume(self) -> tuple[bool, str]:
        """Resume sturgeon animation.
        
        Returns:
            (success, message) tuple
        """
        with self._lock:
            if self._animator.enabled:
                return True, "Sturgeon animation already running"
            
            self._animator.set_enabled(True)
            carb.log_info("[sturgeon_anim_service] Animation resumed")
            return True, "Sturgeon animation resumed"
