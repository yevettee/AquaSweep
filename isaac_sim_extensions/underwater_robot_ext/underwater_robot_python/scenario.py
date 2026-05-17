# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific governing permissions and
# limitations under the License.

"""
JetBot tank-cleaning FSM (logic ported from water_robot).
`UIBuilder` loads the robot, then drives this scenario via the Run Scenario physics callback.
"""

from enum import Enum, auto

import carb
import numpy as np
from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController

# JetBot 물리 파라미터 (공식 예제와 동일)
JETBOT_WHEEL_RADIUS = 0.03
JETBOT_WHEEL_BASE = 0.1125

# 수조·로봇 치수 (m) — 실제 수조에 맞게 조정
TANK_WIDTH_M = 2
ROBOT_DIAMETER_M = 0.14

# 명령 속도: DifferentialController.forward(command=[선속도 v, 각속도 ω])
ROW_LINEAR = 1
TURN_ANGULAR = np.pi / 2

# 종료 허용 오차
DIST_TOL_M = 0.02
YAW_TOL_RAD = 0.04

LOG_TAG = "[underwater.robot]"


class _MotionKind(Enum):
    MOVE = auto()
    TURN = auto()


class UnderwaterTankJetbotFsm:
    """수조 너비·로봇 지름 기준 한 번 왕복 FSM (전진·90°·…)."""

    def __init__(self) -> None:
        self._jetbot = None
        self._controller = None
        self._phase_index = 0
        self._phase_origin_xy = None
        self._phase_target_yaw = None
        self._specs = None
        self._cycle_start_xy = None
        self._cycle_start_yaw = None

    def initialize(self, jetbot) -> None:
        """Load 직후 최초 호출: 제어기 생성·페이즈 스펙 구성·FSM 시작."""
        self._jetbot = jetbot
        self._controller = DifferentialController(
            name="underwater_tank_diff",
            wheel_radius=JETBOT_WHEEL_RADIUS,
            wheel_base=JETBOT_WHEEL_BASE,
        )
        self._controller.reset()
        self._build_phase_specs()
        self._reset_fsm()

    def sync_after_world_reset(self, jetbot) -> None:
        """World Reset 후: 동일 스펙으로 제어기·상태만 리셋."""
        self._jetbot = jetbot
        if self._controller is not None:
            self._controller.reset()
        self._reset_fsm()

    def teardown(self) -> None:
        self._jetbot = None
        self._controller = None
        self._specs = None
        self._phase_index = 0
        self._phase_origin_xy = None
        self._phase_target_yaw = None

    def on_physics_step(self, step_size: float) -> None:
        del step_size
        if self._jetbot is None or self._controller is None or self._specs is None:
            return
        if self._phase_index >= len(self._specs):
            self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, 0.0]))
            return

        kind, mag, sign = self._specs[self._phase_index]
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)

        if kind == _MotionKind.MOVE:
            traveled = float(np.hypot(pos[0] - self._phase_origin_xy[0], pos[1] - self._phase_origin_xy[1]))
            if traveled >= mag - DIST_TOL_M:
                self._advance_phase()
                return
            v = sign * ROW_LINEAR
            w = 0.0
            self._jetbot.apply_wheel_actions(self._controller.forward(command=[v, w]))
            return

        if self._angle_abs_diff(yaw, self._phase_target_yaw) <= YAW_TOL_RAD:
            self._advance_phase()
            return
        w = sign * TURN_ANGULAR
        self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, w]))

    def _build_phase_specs(self) -> None:
        hw = np.pi / 2.0
        self._specs = [
            (_MotionKind.MOVE, TANK_WIDTH_M, 1.0),
            (_MotionKind.TURN, hw, 1.0),
            (_MotionKind.MOVE, ROBOT_DIAMETER_M, 1.0),
            (_MotionKind.TURN, hw, 1.0),
            (_MotionKind.MOVE, TANK_WIDTH_M, 1.0),
        ]

    def _reset_fsm(self) -> None:
        self._phase_index = 0
        self._phase_origin_xy = None
        self._phase_target_yaw = None
        self._begin_current_phase()
        self._log_cycle_start_pose()

    def _log_cycle_start_pose(self) -> None:
        if self._jetbot is None:
            return
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        self._cycle_start_xy = np.array([pos[0], pos[1]], dtype=float)
        self._cycle_start_yaw = yaw
        msg = (
            f"{LOG_TAG} cycle START world_xyz=({pos[0]:.4f},{pos[1]:.4f},{pos[2]:.4f}) yaw_rad={yaw:.4f}"
        )
        carb.log_info(msg)
        print(msg, flush=True)

    def _log_cycle_end_pose(self) -> None:
        if self._jetbot is None or self._cycle_start_xy is None:
            return
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        dx = float(pos[0] - self._cycle_start_xy[0])
        dy = float(pos[1] - self._cycle_start_xy[1])
        err_xy = float(np.hypot(dx, dy))
        dyaw = self._angle_abs_diff(yaw, self._cycle_start_yaw)
        msg = (
            f"{LOG_TAG} cycle END world_xyz=({pos[0]:.4f},{pos[1]:.4f},{pos[2]:.4f}) "
            f"yaw_rad={yaw:.4f} | planar_err={err_xy:.4f} m dx={dx:.4f} dy={dy:.4f} |yaw_err|={dyaw:.4f} rad"
        )
        carb.log_info(msg)
        print(msg, flush=True)

    def _advance_phase(self) -> None:
        self._phase_index += 1
        if self._specs is not None and self._phase_index == len(self._specs):
            self._log_cycle_end_pose()
        self._begin_current_phase()

    def _begin_current_phase(self) -> None:
        if self._jetbot is None or self._specs is None:
            return
        if self._phase_index >= len(self._specs):
            return
        kind, mag, sign = self._specs[self._phase_index]
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        if kind == _MotionKind.MOVE:
            self._phase_origin_xy = np.array([pos[0], pos[1]], dtype=float)
            self._phase_target_yaw = None
            return
        self._phase_origin_xy = None
        self._phase_target_yaw = self._normalize_angle(yaw + sign * mag)

    @staticmethod
    def _normalize_angle(a: float) -> float:
        return (float(a) + np.pi) % (2.0 * np.pi) - np.pi

    def _angle_abs_diff(self, a: float, b: float) -> float:
        return abs(self._normalize_angle(a - b))

    @staticmethod
    def _yaw_from_orientation(orient) -> float:
        """로봇 루트 쿼터니언에서 Z축 요 각 ([w,x,y,z])."""
        q = np.asarray(orient, dtype=float).reshape(-1)
        if q.size != 4:
            return 0.0
        w, x, y, z = q[0], q[1], q[2], q[3]
        return float(np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))
