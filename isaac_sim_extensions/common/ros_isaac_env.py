"""Shared Isaac Sim + ROS2 (rclpy) environment setup for all extensions.

Use from any extension *after* isaacsim.ros2.bridge is loaded (extension.toml dependency).
Do not import rclpy at module import time — call configure_isaac_ros_env() first, then import.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

_BRIDGE_MARKERS = ("isaacsim.ros2.bridge", "omni.isaac.ros2_bridge")

AQUA_INTERFACES_INSTALL_HINT = (
    "Run: water_ws/scripts/install_aqua_interfaces_for_isaac.sh "
    "(re-run after changing aqua_interfaces msg/action definitions)"
)


def repo_root_from_here(*path_parts: str) -> str:
    """Return AquaSweep_2 repo root; optional join with extra path parts."""
    # common/ros_isaac_env.py -> isaac_sim_extensions/common -> repo root
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if path_parts:
        return os.path.join(root, *path_parts)
    return root


def purge_stale_ros_modules() -> None:
    """Drop cached ROS modules so Isaac py3.11 bindings reload cleanly."""
    prefixes = (
        "rclpy",
        "rcl_interfaces",
        "aqua_interfaces",
        "rosidl_",
        "rmw_",
        "builtin_interfaces",
        "unique_identifier_",
        "action_msgs",
        "std_msgs",
    )
    stale = [
        name
        for name in list(sys.modules)
        if any(name == prefix or name.startswith(prefix) for prefix in prefixes)
    ]
    for name in stale:
        del sys.modules[name]


def find_isaac_bridge_humble_dir() -> Optional[str]:
    ros_distro = os.environ.get("ROS_DISTRO", "humble")

    for path in sys.path:
        if not any(marker in path for marker in _BRIDGE_MARKERS):
            continue
        if os.path.basename(path) == "rclpy":
            humble_dir = os.path.dirname(path)
            if os.path.isdir(os.path.join(humble_dir, "lib")):
                return humble_dir

    fallback = os.path.join(
        os.path.expanduser("~"),
        "dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts",
        "isaacsim.ros2.bridge",
        ros_distro,
    )
    if os.path.isdir(os.path.join(fallback, "lib")):
        return fallback

    return None


def find_aqua_interfaces_py311_root() -> Optional[str]:
    humble_dir = find_isaac_bridge_humble_dir()
    if humble_dir is not None:
        rclpy_root = os.path.join(humble_dir, "rclpy")
        if os.path.isdir(os.path.join(rclpy_root, "aqua_interfaces")):
            return rclpy_root

    fallback_site = repo_root_from_here(
        "water_ws/install_isaac/aqua_interfaces/lib/python3.11/site-packages"
    )
    if os.path.isdir(os.path.join(fallback_site, "aqua_interfaces")):
        return fallback_site

    return None


def _should_deprioritize_sys_path(path: str) -> bool:
    if "/opt/ros/" in path:
        return True
    if "aqua_interfaces" in path and "python3.10" in path:
        return True
    if path.endswith("/site-packages/aqua_interfaces") or path.endswith("/dist-packages/aqua_interfaces"):
        return True
    return False


def _prepend_env_path(var: str, *paths: str) -> None:
    existing = os.environ.get(var, "")
    parts = [part for part in existing.split(":") if part]
    for path in reversed(paths):
        if path and os.path.isdir(path) and path not in parts:
            parts.insert(0, path)
    os.environ[var] = ":".join(parts)


def configure_isaac_ros_env() -> bool:
    """Prepare LD_LIBRARY_PATH + sys.path for Isaac bundled rclpy (py3.11) and aqua_interfaces."""
    humble_dir = find_isaac_bridge_humble_dir()
    if humble_dir is None:
        return False

    rclpy_root = os.path.join(humble_dir, "rclpy")
    lib_dir = os.path.join(humble_dir, "lib")
    python_lib = os.path.join(sys.prefix, "lib")
    aqua_interfaces_root = find_aqua_interfaces_py311_root()

    _prepend_env_path("LD_LIBRARY_PATH", lib_dir, python_lib)
    os.environ.setdefault("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")
    os.environ.setdefault("ROS_DISTRO", "humble")

    head: list[str] = []
    tail: list[str] = []
    priority = [p for p in (rclpy_root, aqua_interfaces_root) if p]

    for path in sys.path:
        if _should_deprioritize_sys_path(path):
            tail.append(path)
        elif path in priority:
            continue
        else:
            head.append(path)

    for path in reversed(priority):
        if path not in head:
            head.insert(0, path)

    sys.path[:] = head + tail

    if aqua_interfaces_root is None or not os.path.isdir(os.path.join(aqua_interfaces_root, "aqua_interfaces")):
        return False
    return os.path.isdir(os.path.join(rclpy_root, "rclpy"))
