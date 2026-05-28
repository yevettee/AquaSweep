"""Gantry Command Bridge — Isaac Sim ↔ Dashboard ROS2 통신 모듈.

역할:
- 서비스 서버: start, pause, resume gantry motion
- 토픽 발행: gantry status

사용법:
    from gantry_command_bridge import create_gantry_bridge
    
    bridge = create_gantry_bridge()
    bridge.set_gantry_callbacks(
        on_start_motion=gantry_builder.start_motion,
        on_pause_motion=gantry_builder.pause_motion,
        on_resume_motion=gantry_builder.resume_motion,
        is_motion_enabled=gantry_builder.is_motion_enabled,
        is_built=gantry_builder.is_built,
        get_stage=get_current_stage,
    )
    
    # 메인 스레드(physics step/timeline)에서 주기적으로 호출:
    bridge.process_pending_requests()

IMPORTANT: 
- configure_isaac_ros_env()를 먼저 호출한 후에 사용해야 합니다.
- USD 작업은 메인 스레드에서만 실행되어야 합니다.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import carb

LOG_TAG = "[gantry_bridge]"

_GantryCommandBridge = None


def _build_bridge_class() -> bool:
    """Build bridge class with lazy ROS2 import."""
    global _GantryCommandBridge
    
    if _GantryCommandBridge is not None:
        return True
    
    try:
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
        from std_srvs.srv import Trigger
        from std_msgs.msg import String
    except ImportError as e:
        carb.log_warn(f"{LOG_TAG} ROS2 import failed: {e}")
        return False

    _qos = QoSProfile(
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
    )

    class GantryCommandBridgeImpl(Node):
        """ROS2 ↔ Isaac Sim 겐트리 모션 명령 브릿지.
        
        Services:
            /gantry/start  - 겐트리 모션 시작 (STOPPED → RUNNING)
            /gantry/stop   - 겐트리 모션 정지 (→ STOPPED, 상태 유지로 pause 동작)
        
        Topics:
            /gantry/status - 겐트리 상태 발행
        
        Note:
            Stop 후 Start로 재개 가능 (pause/resume 동작).
            서비스 콜백은 플래그만 설정, 실제 작업은 process_pending_requests()에서 수행.
        """

        # 상태 상수
        STATE_STOPPED = 0
        STATE_RUNNING = 1

        def __init__(self):
            super().__init__("gantry_command_bridge")
            
            self._lock = threading.Lock()
            
            # 상태
            self._state = self.STATE_STOPPED
            self._sm_state = "IDLE"  # gantry state machine state
            self._fish_processed = 0
            
            # 요청 플래그
            self._start_requested = False
            self._stop_requested = False
            
            # 콜백
            self._on_start_motion: Optional[Callable] = None
            self._on_pause_motion: Optional[Callable] = None
            self._on_resume_motion: Optional[Callable] = None
            self._is_motion_enabled: Optional[Callable] = None
            self._is_built_fn: Optional[Callable] = None
            self._get_stage: Optional[Callable] = None
            
            # 토픽 발행자
            self._status_pub = self.create_publisher(String, "/gantry/status", _qos)
            
            # 서비스 서버
            self._start_srv = self.create_service(
                Trigger, "/gantry/start", self._handle_start
            )
            self._stop_srv = self.create_service(
                Trigger, "/gantry/stop", self._handle_stop
            )
            
            carb.log_info(f"{LOG_TAG} Bridge ready (services: /gantry/start, /gantry/stop)")

        def set_gantry_callbacks(
            self,
            on_start_motion: Optional[Callable] = None,
            on_pause_motion: Optional[Callable] = None,
            on_resume_motion: Optional[Callable] = None,
            is_motion_enabled: Optional[Callable] = None,
            is_built: Optional[Callable] = None,
            get_stage: Optional[Callable] = None,
        ) -> None:
            """겐트리 모션 콜백 함수들을 등록합니다.
            
            Args:
                on_start_motion: 모션 시작 함수 (처음 시작, 상태 초기화)
                on_pause_motion: 모션 일시정지 함수 (상태 유지)
                on_resume_motion: 모션 재개 함수 (이전 상태에서 계속)
                is_motion_enabled: 모션 활성화 여부 확인 함수
                is_built: 겐트리 빌드 여부 확인 함수 (stage 인자)
                get_stage: 현재 stage 반환 함수
            """
            self._on_start_motion = on_start_motion
            self._on_pause_motion = on_pause_motion
            self._on_resume_motion = on_resume_motion
            self._is_motion_enabled = is_motion_enabled
            self._is_built_fn = is_built
            self._get_stage = get_stage

        def _handle_start(self, request, response) -> Trigger.Response:
            """Start/Resume gantry motion service handler."""
            with self._lock:
                # 빌드 여부 확인
                if self._is_built_fn is not None and self._get_stage is not None:
                    stage = self._get_stage()
                    if stage is None or not self._is_built_fn(stage):
                        response.success = False
                        response.message = "Gantry not built — run LOAD first"
                        return response
                
                # 이미 실행 중인지 확인
                if self._is_motion_enabled is not None and self._is_motion_enabled():
                    response.success = True
                    response.message = "Gantry motion already running"
                    return response
                
                if self._start_requested:
                    response.success = True
                    response.message = "Start already requested, waiting..."
                    return response
                
                self._start_requested = True
                self._stop_requested = False
                carb.log_info(f"{LOG_TAG} Start/Resume motion requested")
            
            response.success = True
            response.message = "Start/Resume motion request accepted"
            return response

        def _handle_stop(self, request, response) -> Trigger.Response:
            """Pause gantry motion service handler (상태 유지)."""
            with self._lock:
                # 이미 정지 상태인지 확인
                if self._is_motion_enabled is not None and not self._is_motion_enabled():
                    response.success = True
                    response.message = "Gantry motion already stopped"
                    return response
                
                if self._stop_requested:
                    response.success = True
                    response.message = "Stop already requested, waiting..."
                    return response
                
                self._stop_requested = True
                self._start_requested = False
                carb.log_info(f"{LOG_TAG} Pause motion requested")
            
            response.success = True
            response.message = "Pause motion request accepted"
            return response

        def process_pending_requests(self) -> None:
            """메인 스레드에서 호출: 대기 중인 시작/정지 요청을 처리합니다."""
            # 정지(pause) 요청 처리
            with self._lock:
                should_stop = self._stop_requested
                self._stop_requested = False
            
            if should_stop:
                self._do_pause_motion()
            
            # 시작/재개 요청 처리
            with self._lock:
                should_start = self._start_requested
                self._start_requested = False
            
            if should_start:
                self._do_start_or_resume_motion()

        def _do_start_or_resume_motion(self) -> None:
            """시작 또는 재개 (메인 스레드에서 호출)."""
            try:
                # 이미 실행 중이면 스킵
                if self._is_motion_enabled is not None and self._is_motion_enabled():
                    return
                
                # 처음 시작인지 재개인지 판단
                is_first_start = (self._state == self.STATE_STOPPED and 
                                  self._sm_state in ("IDLE", "STOPPED", ""))
                
                if is_first_start and self._on_start_motion is not None:
                    success = self._on_start_motion()
                    if success:
                        with self._lock:
                            self._state = self.STATE_RUNNING
                            self._sm_state = "IDLE"
                        self.publish_status("IDLE", "Motion started")
                        carb.log_info(f"{LOG_TAG} Motion started (fresh)")
                    else:
                        self.publish_status("ERROR", "Start failed")
                        
                elif self._on_resume_motion is not None:
                    success = self._on_resume_motion()
                    if success:
                        with self._lock:
                            self._state = self.STATE_RUNNING
                        self.publish_status(self._sm_state, "Motion resumed")
                        carb.log_info(f"{LOG_TAG} Motion resumed (state={self._sm_state})")
                    else:
                        # resume 실패 시 start 시도
                        if self._on_start_motion is not None:
                            success = self._on_start_motion()
                            if success:
                                with self._lock:
                                    self._state = self.STATE_RUNNING
                                    self._sm_state = "IDLE"
                                self.publish_status("IDLE", "Motion started")
                                carb.log_info(f"{LOG_TAG} Motion started (after resume fail)")
                
            except Exception as e:
                carb.log_error(f"{LOG_TAG} Start/Resume failed: {e}")
                self.publish_status("ERROR", str(e))

        def _do_pause_motion(self) -> None:
            """일시정지 (메인 스레드에서 호출, 상태 유지)."""
            try:
                if self._on_pause_motion is not None:
                    self._on_pause_motion()
                
                with self._lock:
                    self._state = self.STATE_STOPPED
                    # _sm_state는 유지 (재개 시 사용)
                
                self.publish_status("PAUSED", f"state={self._sm_state}")
                carb.log_info(f"{LOG_TAG} Motion paused (state={self._sm_state})")
                
            except Exception as e:
                carb.log_error(f"{LOG_TAG} Pause failed: {e}")

        def publish_status(self, state: str, phase: str = "") -> None:
            """겐트리 상태를 발행합니다."""
            with self._lock:
                if state not in ("PAUSED", "ERROR"):
                    self._sm_state = state
                
                msg = String()
                if phase:
                    msg.data = f"{state}:{phase}"
                else:
                    msg.data = state
            
            self._status_pub.publish(msg)

        def update_state(self, state: str) -> None:
            """외부에서 상태 업데이트 (gantry_builder에서 호출)."""
            with self._lock:
                if self._sm_state != state:
                    self._sm_state = state
                    if state == "DROP":
                        self._fish_processed += 1
            
            self.publish_status(state, f"fish={self._fish_processed}")

        def reset(self) -> None:
            """상태 초기화."""
            with self._lock:
                self._state = self.STATE_STOPPED
                self._sm_state = "IDLE"
                self._fish_processed = 0
                self._start_requested = False
                self._stop_requested = False
            self.publish_status("STOPPED")

        @property
        def is_running(self) -> bool:
            with self._lock:
                return self._state == self.STATE_RUNNING

        @property
        def current_state(self) -> str:
            with self._lock:
                return self._sm_state

        @property
        def has_pending_request(self) -> bool:
            with self._lock:
                return self._start_requested or self._stop_requested

    _GantryCommandBridge = GantryCommandBridgeImpl
    return True


def create_gantry_bridge() -> Optional["_GantryCommandBridge"]:
    """GantryCommandBridge 인스턴스를 생성합니다."""
    if not _build_bridge_class():
        return None
    return _GantryCommandBridge()
