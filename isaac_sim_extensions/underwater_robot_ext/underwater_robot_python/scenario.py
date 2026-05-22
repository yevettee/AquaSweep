# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 cmd_vel feedforward + 실제 pose 기반 closed-loop 보정 시나리오.

/under_robot_N/cmd_vel 에서 (v, ω_ff) 를 수신하고, 매 physics step 마다
shadow 목표 pose 와 실제 pose 를 비교해 횡방향·헤딩 오차를 ω 에 더해 보정한다.
물리 외란(부력·항력)으로 인한 드리프트를 자동으로 수렴시킨다.
"""

import math
from typing import Optional, Tuple

import carb

from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController

from .global_variables import DINGO_WHEEL_BASE_M, DINGO_WHEEL_RADIUS_M

LOG_TAG = "[underwater.robot]"

OMEGA_MAX = 2.8  # rad/s — spiral_planner 와 동일

# Closed-loop 게인
_K_HEADING = 2.0  # 헤딩 오차 게인 (rad/s per rad)
_K_LAT     = 1.2  # 횡방향 오차 게인 (rad/s per m)


class UnderwaterTankJetbotFsm:
    """ROS2 cmd_vel feedforward + 실제 pose 기반 closed-loop 보정."""

    def __init__(self) -> None:
        self._robot = None
        self._controller: Optional[DifferentialController] = None
        self._cmd_receiver = None
        self._pool_center: Tuple[float, float] = (0.0, 0.0)
        # shadow 목표 pose (풀 로컬 좌표계, 단위: m / rad)
        self._tgt_x: float = 0.0
        self._tgt_y: float = 0.0
        self._tgt_theta: float = 0.0

    def initialize(
        self,
        robot,
        physics_dt: float,
        pool_center: Tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self._robot = robot
        self._controller = DifferentialController(
            name="underwater_tank_diff",
            wheel_radius=DINGO_WHEEL_RADIUS_M,
            wheel_base=DINGO_WHEEL_BASE_M,
        )
        self._controller.reset()
        self._pool_center = pool_center
        self._reset_target()
        carb.log_info(
            f"{LOG_TAG} initialized — pool_center={pool_center} — waiting for cmd_vel"
        )

    def sync_after_world_reset(self, robot, physics_dt: float) -> None:
        self._robot = robot
        if self._controller is not None:
            self._controller.reset()
        self._reset_target()

    def teardown(self) -> None:
        self._robot = None
        self._controller = None
        self._cmd_receiver = None

    def set_cmd_vel_receiver(self, receiver) -> None:
        self._cmd_receiver = receiver
        carb.log_info(f"{LOG_TAG} cmd_vel receiver attached — closed-loop control enabled")

    def on_physics_step(self, step_size: float) -> None:
        if self._robot is None or self._controller is None or self._cmd_receiver is None:
            return

        v, omega_ff = self._cmd_receiver.get_cmd()

        # shadow 목표 pose 적분 (풀 로컬 좌표계, feedforward 기준)
        self._tgt_x     += v * math.cos(self._tgt_theta) * step_size
        self._tgt_y     += v * math.sin(self._tgt_theta) * step_size
        self._tgt_theta += omega_ff * step_size

        # 실제 로봇 pose (월드 → 풀 로컬 좌표계)
        pos, orient = self._robot.get_world_pose()
        rx = float(pos[0]) - self._pool_center[0]
        ry = float(pos[1]) - self._pool_center[1]
        rtheta = _quat_to_yaw(orient)

        # 횡방향 오차 (목표점과 로봇 헤딩 기준 직교 거리)
        ex = self._tgt_x - rx
        ey = self._tgt_y - ry
        e_lat     = -ex * math.sin(rtheta) + ey * math.cos(rtheta)
        e_heading = _wrap(self._tgt_theta - rtheta)

        # feedforward + PD 보정
        omega = omega_ff + _K_HEADING * e_heading + _K_LAT * e_lat
        omega = max(-OMEGA_MAX, min(OMEGA_MAX, omega))

        self._robot.apply_wheel_actions(self._controller.forward(command=[v, omega]))

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _reset_target(self) -> None:
        """나선 시작점 (풀 중심, +x 방향)으로 shadow pose 초기화."""
        self._tgt_x     = 0.0
        self._tgt_y     = 0.0
        self._tgt_theta = 0.0


def _quat_to_yaw(q) -> float:
    """Isaac Sim 쿼터니언 (w, x, y, z) 에서 yaw 추출."""
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def _wrap(a: float) -> float:
    """각도를 [-π, π] 범위로 정규화."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi
