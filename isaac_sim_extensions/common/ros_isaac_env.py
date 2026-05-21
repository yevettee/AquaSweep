"""Shared Isaac Sim + ROS2 (rclpy) environment setup for all extensions.

Use from any extension *after* isaacsim.ros2.bridge is loaded (extension.toml dependency).
Do not import rclpy at module import time — call configure_isaac_ros_env() first, then import.
"""

from __future__ import annotations

import glob
import importlib.util
import os
import sys
import sysconfig
from typing import Optional

_BRIDGE_MARKERS = ("isaacsim.ros2.bridge", "omni.isaac.ros2_bridge")

AQUA_INTERFACES_INSTALL_HINT = (
    "Run: water_ws/scripts/install_aqua_interfaces_for_isaac.sh "
    "(re-run after changing aqua_interfaces msg/action definitions)"
)

# Evict exact module names and any ``pkg.*`` submodules cached from system py3.10.
_ROS2_MODULE_ROOTS = (
    "rclpy",
    "rpyutils",
    "rcl_interfaces",
    "geometry_msgs",
    "std_msgs",
    "sensor_msgs",
    "builtin_interfaces",
    "action_msgs",
    "rosgraph_msgs",
    "lifecycle_msgs",
    "composition_interfaces",
    "unique_identifier_msgs",
    "rmw_dds_common",
    "rosidl_generator_py",
    "rosidl_runtime_py",
    "rosidl_parser",
    "rosidl_typesupport_c",
    "rosidl_typesupport_cpp",
    "rosidl_typesupport_fastrtps_c",
    "rosidl_typesupport_introspection_c",
    "ament_index_python",
    "aqua_interfaces",
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
    stale = [
        name
        for name in list(sys.modules)
        if name in _ROS2_MODULE_ROOTS
        or any(name.startswith(prefix + ".") for prefix in _ROS2_MODULE_ROOTS)
        or name.startswith("rosidl_")
        or name.startswith("rmw_")
        or name.startswith("unique_identifier_")
    ]
    for name in stale:
        del sys.modules[name]


def _bundled_rclpy_has_package(rclpy_root: str) -> bool:
    return os.path.isdir(os.path.join(rclpy_root, "rclpy"))


def find_bundled_rclpy_root() -> Optional[str]:
    """Return ``.../isaacsim.ros2.bridge/humble/rclpy`` (parent of the rclpy package)."""
    ros_distro = os.environ.get("ROS_DISTRO", "humble")
    so_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    so_name = f"_rclpy_pybind11{so_suffix}" if so_suffix else "_rclpy_pybind11"

    # Strategy A: Isaac extension manager
    try:
        import omni.kit.app

        ext_manager = omni.kit.app.get_app().get_extension_manager()
        bridge_path = ext_manager.get_extension_path("isaacsim.ros2.bridge")
        if bridge_path:
            candidate = os.path.join(bridge_path, ros_distro, "rclpy")
            if _bundled_rclpy_has_package(candidate):
                return candidate
    except Exception:
        pass

    # Strategy B: bridge markers already on sys.path
    for path in sys.path:
        if not any(marker in path for marker in _BRIDGE_MARKERS):
            continue
        if os.path.basename(path) == "rclpy" and _bundled_rclpy_has_package(path):
            return path

    # Strategy C: scan sys.path for the bundled py3.11 C extension
    if so_suffix:
        for path in sys.path:
            candidate_so = os.path.join(path, "rclpy", so_name)
            if os.path.exists(candidate_so) and "isaacsim" in path:
                return path

    # Strategy D: glob known install prefixes
    patterns = (
        os.path.expanduser("~/dev_ws/isaac_sim/**/isaacsim.ros2.bridge/humble/rclpy"),
        "/isaac-sim/**/isaacsim.ros2.bridge/humble/rclpy",
    )
    for pattern in patterns:
        for match in glob.glob(pattern, recursive=True):
            if _bundled_rclpy_has_package(match):
                return match

    # Strategy E: fixed fallback path
    fallback = os.path.join(
        os.path.expanduser("~"),
        "dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts",
        "isaacsim.ros2.bridge",
        ros_distro,
        "rclpy",
    )
    if _bundled_rclpy_has_package(fallback):
        return fallback

    return None


def find_isaac_bridge_humble_dir() -> Optional[str]:
    rclpy_root = find_bundled_rclpy_root()
    if rclpy_root is None:
        return None

    humble_dir = os.path.dirname(rclpy_root)
    if os.path.isdir(os.path.join(humble_dir, "lib")):
        return humble_dir
    return None


def find_aqua_interfaces_py311_root() -> Optional[str]:
    rclpy_root = find_bundled_rclpy_root()
    if rclpy_root is not None and os.path.isdir(os.path.join(rclpy_root, "aqua_interfaces")):
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


def _ensure_ament_prefix_path() -> None:
    ros_root = f"/opt/ros/{os.environ.get('ROS_DISTRO', 'humble')}"
    if os.path.isdir(ros_root):
        _prepend_env_path("AMENT_PREFIX_PATH", ros_root)


def preload_rclpy_pybind11(rclpy_root: str) -> bool:
    """Pre-load Isaac's py3.11 ``rclpy._rclpy_pybind11`` before ``import rclpy``."""
    so_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not so_suffix:
        return False

    so_path = os.path.join(rclpy_root, "rclpy", f"_rclpy_pybind11{so_suffix}")
    if not os.path.exists(so_path):
        return False

    if "rclpy._rclpy_pybind11" in sys.modules:
        return True

    try:
        spec = importlib.util.spec_from_file_location("rclpy._rclpy_pybind11", so_path)
        if spec is None or spec.loader is None:
            return False
        mod = importlib.util.module_from_spec(spec)
        sys.modules["rclpy._rclpy_pybind11"] = mod
        spec.loader.exec_module(mod)
        return True
    except Exception:
        return False


def configure_isaac_ros_env() -> bool:
    """Prepare env vars + sys.path for Isaac bundled rclpy (py3.11) and aqua_interfaces."""
    rclpy_root = find_bundled_rclpy_root()
    if rclpy_root is None:
        return False

    humble_dir = os.path.dirname(rclpy_root)
    lib_dir = os.path.join(humble_dir, "lib")
    python_lib = os.path.join(sys.prefix, "lib")
    aqua_interfaces_root = find_aqua_interfaces_py311_root()

    _ensure_ament_prefix_path()
    _prepend_env_path("LD_LIBRARY_PATH", lib_dir, python_lib)
    os.environ.setdefault("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")
    os.environ.setdefault("ROS_DISTRO", "humble")

    purge_stale_ros_modules()

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

    preload_rclpy_pybind11(rclpy_root)

    if aqua_interfaces_root is None or not os.path.isdir(os.path.join(aqua_interfaces_root, "aqua_interfaces")):
        return False
    return os.path.isdir(os.path.join(rclpy_root, "rclpy"))
