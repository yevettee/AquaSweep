"""Motion Command Bridge — Isaac Sim ↔ aqua_controller ROS2 통신 모듈.

역할:
- 서비스 서버: start, stop, pause, resume motion
- 토픽 발행: motion status (step_sync 대체)

사용법:
    from motion_command_bridge import create_motion_bridge
    
    bridge = create_motion_bridge('pool_1', 'clean_floor')
    # scenario에서 연결:
    bridge.set_scenario_callbacks(
        on_start=scenario.start,
        on_stop=scenario.stop,
        on_pause=scenario.pause,
        on_resume=scenario.resume,
    )
    # physics step에서:
    bridge.publish_status(progress, current_step, total_steps, phase)

IMPORTANT: configure_isaac_ros_env()를 먼저 호출한 후에 사용해야 합니다.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import carb

LOG_TAG = "[motion_bridge]"

_MotionCommandBridge = None


def _build_bridge_class() -> bool:
    """Build bridge class with lazy ROS2 import."""
    global _MotionCommandBridge
    
    if _MotionCommandBridge is not None:
        return True
    
    try:
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
        from aqua_interfaces.msg import MotionStatus
        from aqua_interfaces.srv import StartMotion, StopMotion, PauseMotion, ResumeMotion
    except ImportError as e:
        carb.log_warn(f"{LOG_TAG} ROS2 import failed: {e}")
        return False

    _qos = QoSProfile(
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
    )

    class MotionCommandBridgeImpl(Node):
        """ROS2 ↔ Isaac Sim 모션 명령 브릿지.
        
        Services:
            /{pool_id}/start_{motion_type}  - 모션 시작 (파라미터 포함)
            /{pool_id}/stop_{motion_type}   - 모션 정지
            /{pool_id}/pause_{motion_type}  - 모션 일시정지
            /{pool_id}/resume_{motion_type} - 모션 재개
        
        Topics:
            /{pool_id}/{motion_type}_status - 모션 상태 발행
        """

        # 상태 상수
        STATE_IDLE = 0
        STATE_RUNNING = 1
        STATE_PAUSED = 2
        STATE_DONE = 3

        def __init__(self, pool_id: str, motion_type: str = "clean_floor"):
            node_name = f"{pool_id}_{motion_type}_bridge".replace("-", "_")
            super().__init__(node_name)
            
            self._pool_id = pool_id
            self._motion_type = motion_type
            self._lock = threading.Lock()
            
            # 상태
            self._state = self.STATE_IDLE
            self._current_step = 0
            self._total_steps = 0
            self._phase = ""
            self._paused_at_step = 0
            
            # 시나리오 콜백
            self._on_start: Optional[Callable] = None
            self._on_stop: Optional[Callable] = None
            self._on_pause: Optional[Callable] = None
            self._on_resume: Optional[Callable] = None
            self._get_params: Optional[Callable] = None
            
            # 토픽 발행자
            status_topic = f"/{pool_id}/{motion_type}_status"
            self._status_pub = self.create_publisher(MotionStatus, status_topic, _qos)
            
            # 서비스 서버
            prefix = f"/{pool_id}"
            self._start_srv = self.create_service(
                StartMotion, f"{prefix}/start_{motion_type}", self._handle_start
            )
            self._stop_srv = self.create_service(
                StopMotion, f"{prefix}/stop_{motion_type}", self._handle_stop
            )
            self._pause_srv = self.create_service(
                PauseMotion, f"{prefix}/pause_{motion_type}", self._handle_pause
            )
            self._resume_srv = self.create_service(
                ResumeMotion, f"{prefix}/resume_{motion_type}", self._handle_resume
            )
            
            carb.log_info(
                f"{LOG_TAG} Bridge ready: {pool_id}/{motion_type} "
                f"(status: {status_topic})"
            )

        def set_scenario_callbacks(
            self,
            on_start: Optional[Callable] = None,
            on_stop: Optional[Callable] = None,
            on_pause: Optional[Callable] = None,
            on_resume: Optional[Callable] = None,
            get_params: Optional[Callable] = None,
        ) -> None:
            """시나리오의 콜백 함수들을 등록합니다.
            
            Args:
                on_start: 시작 시 호출 (params dict를 인자로 받음)
                on_stop: 정지 시 호출
                on_pause: 일시정지 시 호출, 현재 step 반환
                on_resume: 재개 시 호출, 현재 step 반환
                get_params: 현재 파라미터 조회
            """
            self._on_start = on_start
            self._on_stop = on_stop
            self._on_pause = on_pause
            self._on_resume = on_resume
            self._get_params = get_params

        def _handle_start(self, request, response) -> StartMotion.Response:
            """Start motion service handler."""
            with self._lock:
                if self._state == self.STATE_RUNNING:
                    response.success = False
                    response.message = "Already running"
                    return response
                
                if self._on_start is None:
                    response.success = False
                    response.message = "No start callback registered"
                    return response
            
            try:
                params = {
                    "tank_diameter": request.params.tank_diameter,
                    "tank_margin": request.params.tank_margin,
                    "robot_footprint": request.params.robot_footprint,
                    "linear_speed": request.params.linear_speed,
                    "omega_max": request.params.omega_max,
                }
                self._on_start(params)
                
                with self._lock:
                    self._state = self.STATE_RUNNING
                    self._current_step = 0
                    self._paused_at_step = 0
                
                response.success = True
                response.message = f"Started {self._motion_type}"
                carb.log_info(f"{LOG_TAG} [{self._pool_id}] {self._motion_type} started")
                
            except Exception as e:
                response.success = False
                response.message = str(e)
                carb.log_error(f"{LOG_TAG} Start failed: {e}")
            
            return response

        def _handle_stop(self, request, response) -> StopMotion.Response:
            """Stop motion service handler."""
            with self._lock:
                if self._state == self.STATE_IDLE:
                    response.success = True
                    response.message = "Already stopped"
                    return response
            
            try:
                if self._on_stop is not None:
                    self._on_stop()
                
                with self._lock:
                    self._state = self.STATE_IDLE
                    self._current_step = 0
                    self._paused_at_step = 0
                
                response.success = True
                response.message = f"Stopped {self._motion_type}"
                carb.log_info(f"{LOG_TAG} [{self._pool_id}] {self._motion_type} stopped")
                
            except Exception as e:
                response.success = False
                response.message = str(e)
                carb.log_error(f"{LOG_TAG} Stop failed: {e}")
            
            return response

        def _handle_pause(self, request, response) -> PauseMotion.Response:
            """Pause motion service handler."""
            with self._lock:
                if self._state != self.STATE_RUNNING:
                    response.success = False
                    response.message = "Not running"
                    response.paused_at_step = 0
                    return response
            
            try:
                paused_step = self._current_step
                if self._on_pause is not None:
                    result = self._on_pause()
                    if isinstance(result, int):
                        paused_step = result
                
                with self._lock:
                    self._state = self.STATE_PAUSED
                    self._paused_at_step = paused_step
                
                response.success = True
                response.message = f"Paused at step {paused_step}"
                response.paused_at_step = paused_step
                carb.log_info(f"{LOG_TAG} [{self._pool_id}] {self._motion_type} paused at step {paused_step}")
                
            except Exception as e:
                response.success = False
                response.message = str(e)
                response.paused_at_step = 0
                carb.log_error(f"{LOG_TAG} Pause failed: {e}")
            
            return response

        def _handle_resume(self, request, response) -> ResumeMotion.Response:
            """Resume motion service handler."""
            with self._lock:
                if self._state != self.STATE_PAUSED:
                    response.success = False
                    response.message = "Not paused"
                    response.resumed_from_step = 0
                    return response
                
                resumed_step = self._paused_at_step
            
            try:
                if self._on_resume is not None:
                    result = self._on_resume()
                    if isinstance(result, int):
                        resumed_step = result
                
                with self._lock:
                    self._state = self.STATE_RUNNING
                
                response.success = True
                response.message = f"Resumed from step {resumed_step}"
                response.resumed_from_step = resumed_step
                carb.log_info(f"{LOG_TAG} [{self._pool_id}] {self._motion_type} resumed from step {resumed_step}")
                
            except Exception as e:
                response.success = False
                response.message = str(e)
                response.resumed_from_step = 0
                carb.log_error(f"{LOG_TAG} Resume failed: {e}")
            
            return response

        def publish_status(
            self,
            progress: float,
            current_step: int,
            total_steps: int,
            phase: str = "",
        ) -> None:
            """모션 상태를 발행합니다 (physics step마다 호출).
            
            Args:
                progress: 진행률 (0.0 ~ 1.0)
                current_step: 현재 step 번호
                total_steps: 전체 step 수
                phase: 현재 단계 이름 (spiral, wall_follow, return 등)
            """
            with self._lock:
                self._current_step = current_step
                self._total_steps = total_steps
                self._phase = phase
                
                # 완료 체크
                if progress >= 1.0 and self._state == self.STATE_RUNNING:
                    self._state = self.STATE_DONE
                
                msg = MotionStatus()
                msg.state = self._state
                msg.progress = float(progress)
                msg.current_step = current_step
                msg.total_steps = total_steps
                msg.phase = phase
            
            self._status_pub.publish(msg)

        def mark_done(self) -> None:
            """모션 완료로 상태 변경."""
            with self._lock:
                self._state = self.STATE_DONE
            self.publish_status(1.0, self._current_step, self._total_steps, "done")

        def reset(self) -> None:
            """상태 초기화."""
            with self._lock:
                self._state = self.STATE_IDLE
                self._current_step = 0
                self._total_steps = 0
                self._phase = ""
                self._paused_at_step = 0

        @property
        def is_running(self) -> bool:
            with self._lock:
                return self._state == self.STATE_RUNNING

        @property
        def is_paused(self) -> bool:
            with self._lock:
                return self._state == self.STATE_PAUSED

        @property
        def state(self) -> int:
            with self._lock:
                return self._state

    _MotionCommandBridge = MotionCommandBridgeImpl
    return True


def create_motion_bridge(
    pool_id: str,
    motion_type: str = "clean_floor",
) -> Optional["_MotionCommandBridge"]:
    """MotionCommandBridge 인스턴스를 생성합니다.
    
    Args:
        pool_id: 풀 ID (예: 'pool_1')
        motion_type: 모션 타입 (예: 'clean_floor', 'clean_wall')
    
    Returns:
        MotionCommandBridge 인스턴스, ROS2 사용 불가 시 None
    
    Note:
        configure_isaac_ros_env()를 먼저 호출해야 합니다.
    """
    if not _build_bridge_class():
        return None
    return _MotionCommandBridge(pool_id, motion_type)
