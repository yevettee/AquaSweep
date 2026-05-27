# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""수중 바닥 청소 — 내부 SpiralPlanner 또는 ROS2 cmd_vel 사용.

두 가지 모드 지원:
1. 내부 모드 (use_internal_planner=True): Isaac Sim 내부의 SpiralPlanner 사용
   - MotionCommandBridge를 통해 start/stop/pause/resume 서비스 제공
   - motion_status 토픽으로 진행상황 발행
   
2. 외부 모드 (use_internal_planner=False, 기본값): ROS2 cmd_vel 수신
   - aqua_controller에서 cmd_vel 발행
   - step_sync로 동기화 (기존 방식 유지)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import carb
import numpy as np

from .global_variables import ROBOT_PRIM_PATH

LOG_TAG = "[underwater.robot]"


def _quat_to_yaw(q) -> float:
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class UnderwaterSpiralScenario:
    """수중 바닥 청소 시나리오 — 내부 플래너 또는 외부 cmd_vel 사용.

    내부 모드:
        - SpiralPlanner가 궤적 계산
        - MotionCommandBridge로 서비스/상태 토픽 제공
        
    외부 모드 (기존 호환):
        - aqua_controller가 cmd_vel 발행
        - step_sync로 동기화
        
    Thread Safety:
        ROS 콜백(서비스 핸들러)은 PhysX 스레드와 다른 스레드에서 실행됨.
        Physics 객체 접근은 on_physics_step()에서만 수행하고,
        ROS 콜백에서는 플래그만 설정하여 race condition 방지.
    """

    def __init__(self, use_internal_planner: bool = False) -> None:
        self._robot = None
        self._robot_name: str = "under_robot_1"
        self._pool_id: str = "pool_1"
        self._running: bool = False      # 물리 활성화 (RUN 버튼)
        self._cleaning_active: bool = False  # 실제 청소 진행 중 (Action/Service 호출)
        self._paused: bool = False
        self._debug_tick: int = 0
        self._physics_dt: float = 1.0 / 60.0
        
        # Thread-safe 요청 플래그 (ROS 콜백 → Physics 스레드)
        self._stop_requested: bool = False
        self._pause_requested: bool = False
        
        # 모드 설정
        self._use_internal_planner = use_internal_planner
        
        # 외부 모드용
        self._cmd_receiver = None  # rclpy CmdVelReceiver 인스턴스
        
        # 내부 모드용
        self._spiral_planner = None
        self._motion_bridge = None
        self._initial_pose: Optional[Tuple[float, float, float]] = None  # (x0, y0, theta0)

    # ── 초기화 ──────────────────────────────────────────────────────────────

    def initialize(
        self,
        robot,
        physics_dt: float,
        robot_prim_path: str = ROBOT_PRIM_PATH,
        robot_name: str = "under_robot_1",
        pool_id: str = None,
    ) -> None:
        self._robot = robot
        self._robot_name = robot_name
        self._physics_dt = physics_dt
        
        if pool_id:
            self._pool_id = pool_id
        else:
            # robot_name에서 pool_id 추출 (under_robot_1 -> pool_1)
            try:
                idx = robot_name.split("_")[-1]
                self._pool_id = f"pool_{idx}"
            except Exception:
                self._pool_id = "pool_1"
        
        # 내부 플래너 모드일 경우 초기화
        if self._use_internal_planner:
            self._init_internal_planner()
        
        carb.log_warn(
            f"{LOG_TAG} [{robot_name}] 초기화 완료 — "
            f"mode={'internal' if self._use_internal_planner else 'external'}, "
            f"robot={'OK' if robot else 'None'}"
        )

    def _init_internal_planner(self) -> None:
        """내부 SpiralPlanner 및 MotionCommandBridge 초기화."""
        try:
            from .spiral_planner import SpiralPlanner
            self._spiral_planner = SpiralPlanner(physics_dt=self._physics_dt)
            carb.log_info(f"{LOG_TAG} [{self._robot_name}] SpiralPlanner 초기화 완료")
        except Exception as e:
            carb.log_error(f"{LOG_TAG} SpiralPlanner 초기화 실패: {e}")
            self._spiral_planner = None

    def set_motion_bridge(self, bridge) -> None:
        """MotionCommandBridge 인스턴스 설정 (ui_builder에서 호출)."""
        self._motion_bridge = bridge
        if bridge is not None:
            bridge.set_scenario_callbacks(
                on_start=self._on_bridge_start,
                on_stop=self._on_bridge_stop,
                on_pause=self._on_bridge_pause,
                on_resume=self._on_bridge_resume,
            )
            carb.log_info(f"{LOG_TAG} [{self._robot_name}] MotionCommandBridge 연결됨")

    def _on_bridge_start(self, params: dict) -> None:
        """MotionCommandBridge에서 start 서비스 호출 시 — 실제 청소 시작.
        
        파라미터 값이 0.0이거나 None이면 spiral_planner.py의 기본값 사용.
        """
        if self._spiral_planner is not None:
            # 0.0 또는 None은 기본값 사용 (None으로 변환)
            def _or_none(v):
                return v if v and v > 0 else None
            
            self._spiral_planner.rebuild(
                tank_diameter=_or_none(params.get("tank_diameter")),
                tank_margin=_or_none(params.get("tank_margin")),
                robot_footprint=_or_none(params.get("robot_footprint")),
                linear_speed=_or_none(params.get("linear_speed")),
                omega_max=_or_none(params.get("omega_max")),
            )
        self._running = True  # 물리 활성화 (서비스 호출 시 자동 시작)
        self._cleaning_active = True
        self._paused = False
        self._initial_pose = None  # 첫 physics step에서 기록
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 청소 시작 (서비스 호출)")

    def _on_bridge_stop(self) -> None:
        """MotionCommandBridge에서 stop 서비스 호출 시 — 청소 정지 요청.
        
        NOTE: ROS 콜백 스레드에서 호출됨. Physics 객체 직접 접근 금지!
        플래그만 설정하고, 실제 정지는 on_physics_step()에서 처리.
        """
        self._stop_requested = True
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 청소 정지 요청됨 (서비스 호출)")

    def _on_bridge_pause(self) -> int:
        """MotionCommandBridge에서 pause 서비스 호출 시 — 일시정지 요청.
        
        NOTE: ROS 콜백 스레드에서 호출됨. Physics 객체 직접 접근 금지!
        플래그만 설정하고, 실제 정지는 on_physics_step()에서 처리.
        """
        self._pause_requested = True
        if self._spiral_planner is not None:
            return self._spiral_planner.pause()
        return 0

    def _on_bridge_resume(self) -> int:
        """MotionCommandBridge에서 resume 서비스 호출 시."""
        self._paused = False
        self._pause_requested = False
        if self._spiral_planner is not None:
            return self._spiral_planner.resume()
        return 0

    def set_cmd_vel_receiver(self, receiver) -> None:
        """외부 모드용 cmd_vel 수신기 설정."""
        self._cmd_receiver = receiver

    def sync_after_reset(self, robot) -> None:
        self._robot = robot
        self._running = False
        self._cleaning_active = False
        self._paused = False
        self._stop_requested = False
        self._pause_requested = False
        self._initial_pose = None
        if self._spiral_planner is not None:
            self._spiral_planner.reset()

    # ── 제어 진입점 ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """물리 활성화 (RUN 버튼). 청소는 Action/Service 호출 시에만 시작."""
        self._running = True
        self._paused = False
        # 내부 플래너 모드에서도 여기서는 청소를 시작하지 않음
        # 청소는 _on_bridge_start() (서비스 호출) 시에만 시작
        if self._use_internal_planner:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 물리 활성화 — 청소 서비스 대기 중")
        else:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 물리 활성화 — cmd_vel 대기 중")

    def stop(self) -> None:
        """물리 비활성화 (STOP 버튼)."""
        self._running = False
        self._cleaning_active = False
        self._paused = False
        if self._robot is not None:
            try:
                self._robot.set_linear_velocity(np.zeros(3, dtype=float))
                self._robot.set_angular_velocity(np.zeros(3, dtype=float))
            except Exception:
                pass
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 물리 비활성화")

    def pause(self) -> None:
        """일시정지."""
        self._paused = True
        if self._robot is not None:
            try:
                self._robot.set_linear_velocity(np.zeros(3, dtype=float))
                self._robot.set_angular_velocity(np.zeros(3, dtype=float))
            except Exception:
                pass
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 일시정지")

    def resume(self) -> None:
        """재개."""
        self._paused = False
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 재개")

    # ── physics step ────────────────────────────────────────────────────────

    def on_physics_step(self, dt: float) -> None:
        # Thread-safe 요청 처리 (ROS 콜백에서 설정된 플래그)
        self._process_pending_requests()
        
        if not self._running or self._robot is None:
            return
        
        if self._paused:
            return

        if self._use_internal_planner:
            # 내부 플래너 모드: 청소가 활성화된 경우에만 실행
            if self._cleaning_active:
                self._step_internal_planner(dt)
        else:
            # 외부 모드: cmd_vel 수신 시 실행 (기존 동작)
            self._step_external_cmd_vel(dt)

    def _process_pending_requests(self) -> None:
        """ROS 콜백에서 요청된 stop/pause를 Physics 스레드에서 안전하게 처리."""
        # Stop 요청 처리
        if self._stop_requested:
            self._stop_requested = False
            self._cleaning_active = False
            self._paused = False
            if self._spiral_planner is not None:
                self._spiral_planner.reset()
            if self._robot is not None:
                try:
                    self._robot.set_linear_velocity(np.zeros(3, dtype=float))
                    self._robot.set_angular_velocity(np.zeros(3, dtype=float))
                except Exception:
                    pass
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 청소 정지 완료")
            return
        
        # Pause 요청 처리
        if self._pause_requested:
            self._pause_requested = False
            self._paused = True
            if self._robot is not None:
                try:
                    self._robot.set_linear_velocity(np.zeros(3, dtype=float))
                    self._robot.set_angular_velocity(np.zeros(3, dtype=float))
                except Exception:
                    pass
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 일시정지 완료")

    def _step_internal_planner(self, dt: float) -> None:
        """내부 SpiralPlanner 모드의 physics step (Pure Pursuit 폐루프)."""
        if self._spiral_planner is None:
            return

        # 완료 체크
        if self._spiral_planner.is_done:
            self._cleaning_active = False
            if self._motion_bridge is not None:
                self._motion_bridge.mark_done()
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 청소 완료")
            return

        # 현재 포즈 읽기
        try:
            pos, orient = self._robot.get_world_pose()
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] pose 읽기 실패: {e}")
            return

        x, y  = float(pos[0]), float(pos[1])
        theta = _quat_to_yaw(orient)

        # 초기 위치 기록 (청소 시작 첫 스텝)
        if self._initial_pose is None:
            self._initial_pose = (x, y, theta)
            carb.log_warn(
                f"{LOG_TAG} [{self._robot_name}] 초기 위치: "
                f"({x:.2f}, {y:.2f}, {math.degrees(theta):.1f}°)"
            )

        # 플래너 프레임으로 좌표 변환 (초기 위치·방향 기준 상대 좌표)
        x0, y0, theta0 = self._initial_pose
        dx, dy = x - x0, y - y0
        c0, s0  = math.cos(-theta0), math.sin(-theta0)
        rel_x   = dx * c0 - dy * s0
        rel_y   = dx * s0 + dy * c0
        rel_theta = theta - theta0

        # Pure Pursuit 폐루프 제어
        v, omega = self._spiral_planner.next_cmd_closed_loop(rel_x, rel_y, rel_theta)

        # 속도 적용 (이미 theta를 알고 있으므로 직접 계산)
        try:
            vx = v * math.cos(theta)
            vy = v * math.sin(theta)
            self._robot.set_linear_velocity(np.array([vx, vy, 0.0], dtype=float))
            self._robot.set_angular_velocity(np.array([0.0, 0.0, omega], dtype=float))
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 속도 설정 실패: {e}")

        # 상태 발행
        if self._motion_bridge is not None:
            self._motion_bridge.publish_status(
                progress=self._spiral_planner.progress,
                current_step=self._spiral_planner.current_step,
                total_steps=self._spiral_planner.total_steps,
                phase=self._spiral_planner.phase,
            )

        # 디버그 로그
        self._debug_tick += 1
        if self._debug_tick % 120 == 1:
            carb.log_warn(
                f"{LOG_TAG} [{self._robot_name}] CL: v={v:.3f} ω={omega:.3f} "
                f"rel=({rel_x:.2f},{rel_y:.2f}) {self._spiral_planner.phase} "
                f"{self._spiral_planner.progress:.1%}"
            )

    def _step_external_cmd_vel(self, dt: float) -> None:
        """외부 cmd_vel 모드의 physics step (기존 로직)."""
        if self._cmd_receiver is None:
            return

        v, omega = self._cmd_receiver.get_cmd()
        
        self._debug_tick += 1
        if self._debug_tick % 60 == 1:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] cmd_vel: v={v:.4f} ω={omega:.4f}")

        self._apply_velocity(v, omega)
        
        # step_sync 발행 (기존 동기화 방식)
        self._cmd_receiver.publish_step_sync()

    def _apply_velocity(self, v: float, omega: float) -> None:
        """로봇에 속도 적용."""
        try:
            pos, orient = self._robot.get_world_pose()
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] pose 읽기 실패: {e}")
            return

        theta = _quat_to_yaw(orient)
        vx = v * math.cos(theta)
        vy = v * math.sin(theta)

        try:
            self._robot.set_linear_velocity(np.array([vx, vy, 0.0], dtype=float))
            self._robot.set_angular_velocity(np.array([0.0, 0.0, omega], dtype=float))
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 속도 설정 실패: {e}")

    @property
    def is_running(self) -> bool:
        """물리 활성화 상태 (RUN 버튼)."""
        return self._running

    @property
    def is_cleaning(self) -> bool:
        """청소 진행 중 여부 (Action/Service로 시작됨)."""
        return self._cleaning_active

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def use_internal_planner(self) -> bool:
        return self._use_internal_planner
