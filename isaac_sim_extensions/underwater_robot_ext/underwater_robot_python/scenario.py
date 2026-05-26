# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""수중 바닥 청소 — ROS2 cmd_vel → 직접 속도 설정.

aqua_controller 노드가 /under_robot_N/cmd_vel (Twist) 를 발행하면
Isaac Sim ActionGraph 의 ROS2SubscribeTwist 가 수신하고,
이 시나리오는 매 physics step 마다 그 값을 읽어 로봇에
set_linear_velocity / set_angular_velocity 를 직접 인가한다.
힘(force) 기반 제어가 아니므로 RigidPrim 초기화 타이밍 문제가 없다.
"""

from __future__ import annotations

import math

import carb
import numpy as np

from .global_variables import ROBOT_PRIM_PATH

LOG_TAG = "[underwater.robot]"


def _quat_to_yaw(q) -> float:
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class UnderwaterSpiralScenario:
    """ROS2 cmd_vel 을 받아 직접 속도를 설정하는 바닥 청소 시나리오.

    경로 계획(나선)은 aqua_controller 노드가 담당하고,
    Isaac Sim 은 수신한 (v, ω) 를 로봇에 직접 set_linear/angular_velocity 로 인가한다.
    """

    def __init__(self) -> None:
        self._robot = None
        self._robot_name: str = "under_robot_1"
        self._running: bool = False
        self._debug_tick: int = 0
        self._cmd_receiver = None  # rclpy CmdVelReceiver 인스턴스

    # ── 초기화 ──────────────────────────────────────────────────────────────

    def initialize(self, robot, physics_dt: float,
                   robot_prim_path: str = ROBOT_PRIM_PATH,
                   robot_name: str = "under_robot_1") -> None:
        self._robot = robot
        self._robot_name = robot_name
        carb.log_warn(f"{LOG_TAG} [{robot_name}] 초기화 완료 — robot={'OK' if robot else 'None'}")

    def set_cmd_vel_receiver(self, receiver) -> None:
        self._cmd_receiver = receiver

    def sync_after_reset(self, robot) -> None:
        self._robot = robot
        self._running = False

    # ── 제어 진입점 ─────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 스러스터 제어 시작 — cmd_vel 대기 중")

    def stop(self) -> None:
        self._running = False
        if self._robot is not None:
            try:
                self._robot.set_linear_velocity(np.zeros(3, dtype=float))
                self._robot.set_angular_velocity(np.zeros(3, dtype=float))
            except Exception:
                pass
        carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 스러스터 제어 정지")

    # ── physics step ────────────────────────────────────────────────────────

    def on_physics_step(self, dt: float) -> None:
        if not self._running or self._robot is None:
            return

        if self._cmd_receiver is None:
            return

        # rclpy 구독자에서 최신 cmd_vel 읽기
        v, omega = self._cmd_receiver.get_cmd()

        # 1초마다 진단 로그
        self._debug_tick += 1
        if self._debug_tick % 60 == 1:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] cmd_vel: v={v:.4f} ω={omega:.4f}")

        try:
            pos, orient = self._robot.get_world_pose()
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] pose 읽기 실패: {e}")
            return

        theta = _quat_to_yaw(orient)
        vx = v * math.cos(theta)
        vy = v * math.sin(theta)

        try:
            # Z=0.0 으로 고정하면 중력에 의한 침강 없이 현재 높이 유지
            self._robot.set_linear_velocity(np.array([vx, vy, 0.0], dtype=float))
            self._robot.set_angular_velocity(np.array([0.0, 0.0, omega], dtype=float))
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} [{self._robot_name}] 속도 설정 실패: {e}")

    @property
    def is_running(self) -> bool:
        return self._running
