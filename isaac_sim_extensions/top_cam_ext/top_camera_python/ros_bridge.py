# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 bridge for top_cam_ext:
7개 수조(Pool_1~Pool_7)를 모두 지원하는 다중 카메라 ROS 브릿지.
각 수조의 중앙 50% ROI 크롭 후 /pool_N/top_img_raw 토픽으로 발행.
"""

from __future__ import annotations

import sys
import os
import threading
import time
import subprocess
import signal
from pathlib import Path
from typing import Any, Optional, Type, Dict
import numpy as np
import carb

_common = Path(__file__).resolve().parents[2] / "common"
if str(_common) not in sys.path:
    sys.path.insert(0, str(_common))

from ros_isaac_env import (  # noqa: E402
    AQUA_INTERFACES_INSTALL_HINT,
    configure_isaac_ros_env,
    purge_stale_ros_modules,
)

rclpy = None  # type: ignore
Image = None  # type: ignore
_TopCamRosNode: Optional[Type[object]] = None

_ROS_IMPORT_ERROR = ""

# 매 실행(PLAY)마다 colcon build를 돌리려면 True로 설정하세요.
# 파이썬 노드는 최초 1회 빌드해두면 심볼릭 링크를 통해 소스 수정사항이 실시간 자동 반영되므로 False를 권장합니다.
ENABLE_AUTO_BUILD = False


def bootstrap_ros_environment():
    """Dynamically inject water_ws and ROS2 paths to sys.path and env variables."""
    try:
        repo_root = str(Path(__file__).resolve().parents[3])
        water_ws = os.path.join(repo_root, "water_ws")
        install_dir = os.path.join(water_ws, "install")
        
        ros_distro = "humble"
        ros_root = f"/opt/ros/{ros_distro}"
        
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        ros_paths = [
            os.path.join(ros_root, "lib", f"python{py_ver}", "site-packages"),
            os.path.join(ros_root, "local", "lib", f"python{py_ver}", "dist-packages"),
        ]
        
        if os.path.isdir(install_dir):
            for pkg_dir in Path(install_dir).iterdir():
                pkg_py = pkg_dir / "lib" / f"python{py_ver}" / "site-packages"
                if pkg_py.is_dir():
                    ros_paths.append(str(pkg_py))
        
        for p in ros_paths:
            if p not in sys.path:
                sys.path.insert(0, p)
        
        lib_paths = [
            os.path.join(ros_root, "lib"),
            os.path.join(ros_root, "lib", "x86_64-linux-gnu"),
        ]
        if os.path.isdir(install_dir):
            for pkg_dir in Path(install_dir).iterdir():
                pkg_lib = pkg_dir / "lib"
                if pkg_lib.is_dir():
                    lib_paths.append(str(pkg_lib))
        
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        for lp in lib_paths:
            if lp not in current_ld:
                current_ld = f"{lp}:{current_ld}"
        os.environ["LD_LIBRARY_PATH"] = current_ld
        
        os.environ.setdefault("ROS_DOMAIN_ID", "152")
        os.environ.setdefault("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp")
        
    except Exception as e:
        carb.log_warn(f"[top_cam_ext] bootstrap_ros_environment warning: {e}")


def _ensure_ros_imports() -> bool:
    """Lazily import rclpy and message types; return True on success."""
    global rclpy, Image, _TopCamRosNode, _ROS_IMPORT_ERROR

    if rclpy is not None and _TopCamRosNode is not None:
        return True

    bootstrap_ros_environment()

    if not configure_isaac_ros_env():
        _ROS_IMPORT_ERROR = f"Isaac Sim rclpy not found. {AQUA_INTERFACES_INSTALL_HINT}"
        return False

    purge_stale_ros_modules()

    try:
        import rclpy as _rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Image
        from std_msgs.msg import String as _String
        import json

        class TopCamRosNode(Node):
            """다중 수조 지원 ROS 노드.
            
            num_pools 파라미터로 수조 개수를 받아 각 수조별 publisher/subscriber 생성.
            """
            def __init__(self, num_pools: int = 7):
                super().__init__("top_camera_ros_bridge")
                self.num_pools = num_pools
                self.pub_raw: Dict[int, Any] = {}
                self.sub_status: Dict[int, Any] = {}
                self._last_status_log_t: Dict[int, float] = {}

                for pool_id in range(1, num_pools + 1):
                    # 각 수조별 이미지 발행 토픽
                    self.pub_raw[pool_id] = self.create_publisher(
                        _Image, f"/pool_{pool_id}/top_img_raw", 10
                    )
                    # 각 수조별 상태 구독 토픽
                    self.sub_status[pool_id] = self.create_subscription(
                        _String,
                        f"/pool_{pool_id}/status_string",
                        lambda msg, pid=pool_id: self.status_callback(msg, pid),
                        10
                    )
                    self._last_status_log_t[pool_id] = 0.0

                # carb.log_warn("[top_cam_ext] [SUCCESS] 토픽 생성 완료.") 생략

            def status_callback(self, msg, pool_id: int):
                # 개발용 status 수신 콘솔 로그 스로틀링 제거 (상용 릴리즈 정리)
                pass

        rclpy = _rclpy
        Image = _Image
        _TopCamRosNode = TopCamRosNode
        _ROS_IMPORT_ERROR = ""
        return True
    except Exception as exc:
        _ROS_IMPORT_ERROR = str(exc)
        rclpy = None
        Image = None
        _TopCamRosNode = None
        return False


class RosBridge:
    """싱글톤 ROS 브릿지 — 다중 수조 지원.

    extension.py 와 ui_builder.py 가 각각 RosBridge() 를 호출하더라도
    동일한 인스턴스가 반환되므로 rclpy.init() 이중 호출,
    top_detection_node 이중 생성, publisher context 무효화 문제가 방지된다.
    """

    _instance: Optional["RosBridge"] = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._lock = threading.Lock()
        self._node: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._started = False
        self._is_starting = False
        self._num_pools = 7
        self.unavailable_reason: Optional[str] = None
        self._proc: Optional[subprocess.Popen] = None
        
        # 디버깅용 타이머 및 카운터
        self._last_log_time = 0.0
        self._frame_count = 0
        self._publish_error_logged = False

    @property
    def available(self) -> bool:
        return self._started and self._node is not None

    def _kill_stale_detection_nodes(self):
        try:
            import subprocess
            subprocess.run(["pkill", "-9", "-f", "top_detection_node"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def start(self, num_pools: int = 7) -> bool:
        with self._lock:
            if self._started or self._is_starting:
                return self.available
            self._is_starting = True
            self._num_pools = num_pools

        try:
            if not _ensure_ros_imports():
                self.unavailable_reason = f"ROS2 import failed: {_ROS_IMPORT_ERROR}"
                carb.log_error(f"[top_cam_ext] ERROR: {self.unavailable_reason}")
                with self._lock:
                    self._is_starting = False
                return False

            # 1. 기존에 잔존하는 고스트/좀비 디텍션 노드 완벽 정리
            self._kill_stale_detection_nodes()

            # 2. aqua_detection 패키지 백그라운드 구동 전 동기식 자동 빌드 (옵션 적용)
            if ENABLE_AUTO_BUILD:
                try:
                    import subprocess
                    build_cmd = (
                        "bash -c 'source /opt/ros/humble/setup.bash && "
                        "cd /home/rokey/AquaSweep/water_ws && "
                        "colcon build --packages-select aqua_detection'"
                    )
                    res = subprocess.run(build_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                except Exception:
                    pass

            try:
                import subprocess
                import signal
                cmd = (
                    "bash -c 'source /opt/ros/humble/setup.bash && "
                    "source /home/rokey/AquaSweep/water_ws/install/setup.bash && "
                    "export ROS_DOMAIN_ID=152 && "
                    "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && "
                    "python3 /home/rokey/AquaSweep/ros2_nodes/aqua_detection/src/top/detection_node.py'"
                )
                log_file = open("/tmp/top_detection.log", "w")
                self._proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    start_new_session=True,
                    stdout=log_file,
                    stderr=log_file
                )
            except Exception:
                pass

                self._cleanup_rclpy_context()
                rclpy.init()
                self._node = _TopCamRosNode(num_pools=num_pools)
                self._running = True
                self._thread = threading.Thread(target=self._spin_loop, name="top_cam_ros_spin", daemon=True)
                self._thread.start()
                
                with self._lock:
                    self._started = True
                    self._is_starting = False
                
                self.unavailable_reason = None
                return True
            except Exception as exc:
                self.unavailable_reason = f"ROS2 start failed: {exc}"
                carb.log_error(f"[top_cam_ext] ERROR: {self.unavailable_reason}")
                self._cleanup_node()
                if self._proc is not None:
                    try:
                        import signal
                        os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                    except Exception:
                        pass
                    self._proc = None
                with self._lock:
                    self._is_starting = False
                return False
        except Exception as e:
            with self._lock:
                self._is_starting = False
            carb.log_error(f"[top_cam_ext] start 과정 전체 예외 발생: {e}")
            return False

    @staticmethod
    def _cleanup_rclpy_context():
        """rclpy 컨텍스트와 FastRTPS 공유 메모리를 정리하여 세그폴트를 예방한다."""
        # 1) rclpy 컨텍스트 종료 시도
        try:
            import rclpy as _rclpy
            if _rclpy.ok():
                _rclpy.try_shutdown()
        except Exception:
            pass
        # 2) FastRTPS 공유 메모리 정리
        try:
            import glob
            for shm_file in glob.glob("/dev/shm/fastrtps_*"):
                try:
                    os.remove(shm_file)
                except Exception:
                    pass
        except Exception:
            pass

    def stop(self):
        with self._lock:
            if not self._started and not self._is_starting:
                return  # 이미 중지 상태이면 중복 정리 방지
            self._running = False
            self._started = False
            self._is_starting = False

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._cleanup_node()

        # rclpy 컨텍스트 종료 (다음 실행 시 세그폴트 예방)
        try:
            if rclpy is not None and rclpy.ok():
                rclpy.try_shutdown()
        except Exception:
            pass

        if self._proc is not None:
            try:
                import signal
                os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                self._proc.wait(timeout=1.0)
            except Exception:
                try:
                    import signal
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            self._proc = None
        
        # 잔존 프로세스 재확인 사살
        self._kill_stale_detection_nodes()
        
        # 싱글톤 재사용 가능하도록 초기화 플래그 리셋
        self._publish_error_logged = False

    def _cleanup_node(self):
        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:
                pass
            self._node = None

    def _spin_loop(self):
        try:
            from rclpy.executors import SingleThreadedExecutor, ExternalShutdownException
            executor = SingleThreadedExecutor()
            executor.add_node(self._node)
            try:
                while self._running and self._node is not None and rclpy.ok():
                    executor.spin_once(timeout_sec=0.05)
            except ExternalShutdownException:
                pass
            # 종료 시 노드 제거
            try:
                executor.remove_node(self._node)
            except Exception:
                pass
        except Exception as e:
            if "ExternalShutdownException" not in str(type(e).__name__):
                import traceback
                carb.log_error(f"[top_cam_ext] ERROR in _spin_loop: {e}\n{traceback.format_exc()}")

    def publish_frame(self, frame_np, pool_id: int = 1):
        """pool_id 수조의 카메라 프레임을 발행한다."""
        current_time = time.time()
        self._frame_count += 1
        
        # 3초에 한 번씩만 상태 로그 출력 (7개 수조 → 콘솔 도배 방지)
        should_log = (current_time - self._last_log_time) >= 3.0

        if not self.available or frame_np is None:
            return

        try:
            H, W = frame_np.shape[0], frame_np.shape[1]
            
            # 옆 수조가 가려지도록 양옆 22%씩 제거하고 중앙 56% 영역만 취함
            crop_margin = int(W * 0.22)
            xmin = crop_margin
            xmax = W - crop_margin
            
            cropped_rgb = frame_np[:, xmin:xmax, :3]
            
            msg_raw = Image()
            msg_raw.height = cropped_rgb.shape[0]
            msg_raw.width = cropped_rgb.shape[1]
            msg_raw.encoding = "rgb8"
            msg_raw.is_bigendian = 0
            msg_raw.step = cropped_rgb.shape[1] * 3
            msg_raw.data = cropped_rgb.tobytes()

            with self._lock:
                if self._node is not None and pool_id in self._node.pub_raw:
                    self._node.pub_raw[pool_id].publish(msg_raw)
        except Exception as e:
            # context invalid 에러는 1회만 경고 출력 (에러 도배 방지)
            if "context is invalid" in str(e):
                if not self._publish_error_logged:
                    carb.log_warn(f"[top_cam_ext] publisher context가 무효화됨 (재시작 시 자동 복구): {e}")
                    self._publish_error_logged = True
            else:
                carb.log_error(f"[top_cam_ext] Pool_{pool_id} 프레임 발행 실패: {e}")