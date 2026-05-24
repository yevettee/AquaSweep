# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""수중 바닥 청소 — ROS2 cmd_vel → 스러스터 직접 힘 제어.

aqua_controller 노드가 /under_robot_N/cmd_vel (Twist) 를 발행하면
Isaac Sim ActionGraph 의 ROS2SubscribeTwist 가 수신하고,
이 시나리오는 매 physics step 마다 그 값을 읽어 base_link 에
추진력(Fx, Fy)과 요 토크(Mz)를 직접 인가한다.
바퀴 관절은 passive(무구동)로 방치한다.
"""

from __future__ import annotations

import math
from typing import Optional

import carb
import numpy as np
from isaacsim.core.utils.stage import get_current_stage
from pxr import Usd, UsdPhysics

from .actiongraph_setup import read_cmd_vel
from .global_variables import ROBOT_PRIM_PATH, ROBOT_SPAWN_Z_M

LOG_TAG = "[underwater.robot]"

# ── 추진력 게인 ──────────────────────────────────────────────────────────────
_KV    = 60.0   # N / (m/s)    — 선속도 추적 P 게인
_KW    = 10.0   # N·m / (rad/s) — 각속도 추적 P 게인
_MAX_F = 30.0   # N             — 최대 수평 추진력
_MAX_T = 12.0   # N·m           — 최대 요 토크

# ── Z 소프트 구속 ────────────────────────────────────────────────────────────
_Z_TARGET = float(ROBOT_SPAWN_Z_M)
_KZ  = 300.0   # N/m
_KZD = 80.0    # N·s/m


def _find_rigid_base(root_prim_path: str) -> Optional[str]:
    stage = get_current_stage()
    if not stage:
        return None
    root = stage.GetPrimAtPath(root_prim_path)
    if not root.IsValid():
        return None
    for prim in Usd.PrimRange(root):
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            return prim.GetPath().pathString
    return None


def _quat_to_yaw(q) -> float:
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class UnderwaterSpiralScenario:
    """ROS2 cmd_vel 을 받아 스러스터 힘으로 변환하는 바닥 청소 시나리오.

    경로 계획(나선)은 aqua_controller 노드가 담당하고,
    Isaac Sim 은 수신한 (v, ω) 를 (Fx, Fy, Mz) 힘으로 변환하여 인가한다.
    """

    def __init__(self) -> None:
        self._robot = None
        self._body_view = None
        self._robot_name: str = "under_robot_1"
        self._running: bool = False

    # ── 초기화 ──────────────────────────────────────────────────────────────

    def initialize(self, robot, physics_dt: float,
                   robot_prim_path: str = ROBOT_PRIM_PATH,
                   robot_name: str = "under_robot_1") -> None:
        from isaacsim.core.prims import RigidPrim

        self._robot = robot
        self._robot_name = robot_name

        base_path = _find_rigid_base(robot_prim_path)
        if base_path is None:
            carb.log_error(f"{LOG_TAG} RigidBodyAPI prim not found under {robot_prim_path}")
            return

        self._body_view = RigidPrim(prim_paths_expr=base_path)
        try:
            self._body_view.initialize()
        except Exception as e:
            carb.log_error(f"{LOG_TAG} RigidPrim init failed: {e}")
            self._body_view = None
            return

        carb.log_info(
            f"{LOG_TAG} thruster scenario ready | robot={robot_name} | base={base_path}\n"
            f"  cmd_vel topic: /{robot_name}/cmd_vel"
        )

    def sync_after_reset(self, robot) -> None:
        self._robot = robot
        self._running = False

    # ── 제어 진입점 ─────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._body_view is None:
            carb.log_warn(f"{LOG_TAG} scenario not initialized")
            return
        self._running = True
        carb.log_info(f"{LOG_TAG} thruster control started — waiting for cmd_vel")

    def stop(self) -> None:
        self._running = False
        self._apply_zero()
        carb.log_info(f"{LOG_TAG} thruster control stopped")

    # ── physics step ────────────────────────────────────────────────────────

    def on_physics_step(self, dt: float) -> None:
        if not self._running or self._robot is None or self._body_view is None:
            return

        # ROS2 ActionGraph 에서 최신 cmd_vel 읽기
        v, omega = read_cmd_vel(self._robot_name)

        # 로봇 상태
        try:
            pos, orient = self._robot.get_world_pose()
            lin_vels = self._body_view.get_linear_velocities()
            ang_vels = self._body_view.get_angular_velocities()
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} state read failed: {e}")
            return

        lv = np.asarray(lin_vels[0], dtype=float)
        av = np.asarray(ang_vels[0], dtype=float)
        theta = _quat_to_yaw(orient)

        # 수평 추진력 (P 제어)
        vx_des = v * math.cos(theta)
        vy_des = v * math.sin(theta)

        fx = float(np.clip(_KV * (vx_des - lv[0]), -_MAX_F, _MAX_F))
        fy = float(np.clip(_KV * (vy_des - lv[1]), -_MAX_F, _MAX_F))
        mz = float(np.clip(_KW * (omega - av[2]), -_MAX_T, _MAX_T))

        # Z 소프트 구속
        fz = _KZ * (_Z_TARGET - float(pos[2])) - _KZD * lv[2]

        try:
            self._body_view.apply_forces_and_torques_at_pos(
                forces=np.array([[fx, fy, fz]], dtype=float),
                torques=np.array([[0.0, 0.0, mz]], dtype=float),
                is_global=True,
            )
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} force apply failed: {e}")

    # ── 내부 헬퍼 ───────────────────────────────────────────────────────────

    def _apply_zero(self) -> None:
        if self._body_view is None:
            return
        try:
            self._body_view.apply_forces_and_torques_at_pos(
                forces=np.zeros((1, 3)),
                torques=np.zeros((1, 3)),
                is_global=True,
            )
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        return self._running
