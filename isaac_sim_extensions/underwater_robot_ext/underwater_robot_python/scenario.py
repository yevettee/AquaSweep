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
# See the License for the specific language governing permissions and
# limitations under the License.

"""
원형 수조(직경 5m, 중심=원점 가정) 나선형 패턴:
중심에서 로봇 지름만큼 바깥으로 직진 → 직진 직후 중심까지 거리 R을 R_target 으로 고정한 채
그 반지름의 원을 CCW 로 한 바퀴 → 다시 바깥으로 d 만큼 직진 → … 반복.
`UIBuilder`가 로봇을 로드한 뒤 physics callback에서 구동합니다.
"""

from enum import Enum, auto

import carb
import numpy as np
from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController

from .global_variables import JETBOT_LINEAR_SCALE, JETBOT_TARGET_FOOTPRINT_M

# 스케일 적용 후 차동 모델 (스톡 JetBot 물리값 × LINEAR_SCALE)
JETBOT_WHEEL_RADIUS = 0.03 * JETBOT_LINEAR_SCALE
JETBOT_WHEEL_BASE = 0.1125 * JETBOT_LINEAR_SCALE

# 수조·경로 (m)
TANK_CENTER_XY = np.array([0.0, 0.0], dtype=float)
TANK_RADIUS_M = 2.5
TANK_MARGIN_M = 0.08
ROBOT_DIAMETER_M = JETBOT_TARGET_FOOTPRINT_M

R_CENTER_EPS_M = 0.05

# 명령 속도·궤도 P 제어
RADIAL_LINEAR = 0.85
ORBIT_LINEAR = 0.55
ORBIT_YAW_KP = 2.2
ORBIT_RADIAL_KP = 2.0
ORBIT_RADIUS_MIN_M = 0.08
RADIAL_ALIGN_KP = 2.5
OMEGA_MAX_RAD_S = 2.8

DIST_TOL_M = 0.03
ORBIT_ANGLE_TOL_RAD = 0.12
ALIGN_YAW_TOL_RAD = 0.06

LOG_TAG = "[underwater.robot]"


class _Phase(Enum):
    RADIAL = auto()
    ORBIT = auto()
    DONE = auto()


class UnderwaterTankJetbotFsm:
    """직진으로 고리 반경을 한 단계씩 키운 뒤, 그 고리에서 중심 거리 R_target 을 유지하며 한 바퀴 돕니다."""

    def __init__(self) -> None:
        self._jetbot = None
        self._controller = None
        self._phase = _Phase.RADIAL
        self._radial_start_xy = None
        self._radial_dir_xy = None
        self._radial_need_align = True
        self._orbit_last_theta = None
        self._orbit_accum_rad = 0.0
        self._orbit_radius_target_m = None

    def initialize(self, jetbot) -> None:
        self._jetbot = jetbot
        self._controller = DifferentialController(
            name="underwater_tank_diff",
            wheel_radius=JETBOT_WHEEL_RADIUS,
            wheel_base=JETBOT_WHEEL_BASE,
        )
        self._controller.reset()
        self._reset_fsm()
        self._log_session_start()

    def sync_after_world_reset(self, jetbot) -> None:
        self._jetbot = jetbot
        if self._controller is not None:
            self._controller.reset()
        self._reset_fsm()
        self._log_session_start()

    def teardown(self) -> None:
        self._jetbot = None
        self._controller = None
        self._reset_fsm()

    def on_physics_step(self, step_size: float) -> None:
        del step_size
        if self._jetbot is None or self._controller is None:
            return

        if self._phase == _Phase.DONE:
            self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, 0.0]))
            return

        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        xy = np.array([pos[0], pos[1]], dtype=float)

        if self._phase == _Phase.RADIAL:
            self._step_radial(xy, yaw)
            return

        if self._phase == _Phase.ORBIT:
            self._step_orbit(xy, yaw)

    def _step_radial(self, xy: np.ndarray, yaw: float) -> None:
        if self._radial_start_xy is None or self._radial_dir_xy is None:
            self._begin_radial(xy, yaw)

        desired_yaw = float(np.arctan2(self._radial_dir_xy[1], self._radial_dir_xy[0]))
        yaw_err = self._normalize_angle(desired_yaw - yaw)
        if self._radial_need_align:
            if abs(yaw_err) <= ALIGN_YAW_TOL_RAD:
                self._radial_need_align = False
                self._radial_start_xy = xy.copy()
            else:
                w = float(np.clip(RADIAL_ALIGN_KP * yaw_err, -OMEGA_MAX_RAD_S, OMEGA_MAX_RAD_S))
                self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, w]))
                return

        delta = xy - self._radial_start_xy
        traveled = float(np.dot(delta, self._radial_dir_xy))
        if traveled >= ROBOT_DIAMETER_M - DIST_TOL_M:
            self._finish_radial(xy)
            return

        v = RADIAL_LINEAR
        self._jetbot.apply_wheel_actions(self._controller.forward(command=[v, 0.0]))

    def _begin_radial(self, xy: np.ndarray, yaw: float) -> None:
        rel = xy - TANK_CENTER_XY
        r = float(np.hypot(rel[0], rel[1]))
        if r < R_CENTER_EPS_M:
            self._radial_dir_xy = np.array([np.cos(yaw), np.sin(yaw)], dtype=float)
        else:
            self._radial_dir_xy = rel / r
        self._radial_start_xy = xy.copy()
        self._radial_need_align = True

    def _finish_radial(self, xy: np.ndarray) -> None:
        rel = xy - TANK_CENTER_XY
        r_now = float(np.hypot(rel[0], rel[1]))
        if r_now + ROBOT_DIAMETER_M > TANK_RADIUS_M - TANK_MARGIN_M:
            self._enter_done(f"radial stop r≈{r_now:.3f} next step would exceed tank")
            return

        self._phase = _Phase.ORBIT
        self._orbit_radius_target_m = r_now
        theta = float(np.arctan2(rel[1], rel[0]))
        self._orbit_last_theta = theta
        self._orbit_accum_rad = 0.0
        msg = (
            f"{LOG_TAG} orbit START R_target={r_now:.4f} m (hold this radius CCW 2pi) "
            f"theta0={theta:.4f}"
        )
        carb.log_info(msg)
        print(msg, flush=True)

    def _step_orbit(self, xy: np.ndarray, yaw: float) -> None:
        rel = xy - TANK_CENTER_XY
        r = float(np.hypot(rel[0], rel[1]))
        if r < 1e-6:
            self._enter_done("orbit aborted — at tank center")
            return

        R_t = self._orbit_radius_target_m
        if R_t is None or R_t < 1e-6:
            self._enter_done("orbit aborted — missing R_target")
            return

        theta = float(np.arctan2(rel[1], rel[0]))
        dtheta = self._unwrap_angle_delta(self._orbit_last_theta, theta)
        self._orbit_accum_rad += dtheta
        self._orbit_last_theta = theta

        if self._orbit_accum_rad >= 2.0 * np.pi - ORBIT_ANGLE_TOL_RAD:
            msg = (
                f"{LOG_TAG} orbit COMPLETE accum_rad={self._orbit_accum_rad:.4f} "
                f"r≈{r:.3f} R_target={R_t:.3f}"
            )
            carb.log_info(msg)
            print(msg, flush=True)

            rel2 = xy - TANK_CENTER_XY
            r2 = float(np.hypot(rel2[0], rel2[1]))
            if r2 + ROBOT_DIAMETER_M > TANK_RADIUS_M - TANK_MARGIN_M:
                self._enter_done("coverage complete (next radial would exceed tank)")
                return

            self._phase = _Phase.RADIAL
            self._radial_start_xy = None
            self._radial_dir_xy = None
            self._radial_need_align = True
            self._orbit_last_theta = None
            self._orbit_accum_rad = 0.0
            self._orbit_radius_target_m = None
            return

        tx = -rel[1] / r
        ty = rel[0] / r
        desired_yaw = float(np.arctan2(ty, tx))
        yaw_err = self._normalize_angle(desired_yaw - yaw)
        # 원점 중심·반지름 R_t 원을 따라 CCW: ω ≈ v/R_t + 접선 추종 + 반경 유지
        omega_ff = ORBIT_LINEAR / max(R_t, ORBIT_RADIUS_MIN_M)
        omega_fb = ORBIT_YAW_KP * yaw_err
        r_err = r - R_t
        omega_rad = ORBIT_RADIAL_KP * r_err
        w = float(np.clip(omega_ff + omega_fb + omega_rad, -OMEGA_MAX_RAD_S, OMEGA_MAX_RAD_S))
        v = ORBIT_LINEAR
        self._jetbot.apply_wheel_actions(self._controller.forward(command=[v, w]))

    def _enter_done(self, reason: str) -> None:
        self._phase = _Phase.DONE
        self._orbit_radius_target_m = None
        msg = f"{LOG_TAG} DONE: {reason}"
        carb.log_info(msg)
        print(msg, flush=True)
        self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, 0.0]))

    def _reset_fsm(self) -> None:
        self._phase = _Phase.RADIAL
        self._radial_start_xy = None
        self._radial_dir_xy = None
        self._radial_need_align = True
        self._orbit_last_theta = None
        self._orbit_accum_rad = 0.0
        self._orbit_radius_target_m = None

    def _log_session_start(self) -> None:
        if self._jetbot is None:
            return
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        msg = (
            f"{LOG_TAG} circular sweep START xyz=({pos[0]:.4f},{pos[1]:.4f},{pos[2]:.4f}) "
            f"yaw={yaw:.4f} tank_R={TANK_RADIUS_M} step_d={ROBOT_DIAMETER_M}"
        )
        carb.log_info(msg)
        print(msg, flush=True)

    @staticmethod
    def _unwrap_angle_delta(prev_theta: float, theta: float) -> float:
        d = float(theta - prev_theta)
        while d <= -np.pi:
            d += 2.0 * np.pi
        while d > np.pi:
            d -= 2.0 * np.pi
        return d

    @staticmethod
    def _normalize_angle(a: float) -> float:
        return (float(a) + np.pi) % (2.0 * np.pi) - np.pi

    @staticmethod
    def _yaw_from_orientation(orient) -> float:
        q = np.asarray(orient, dtype=float).reshape(-1)
        if q.size != 4:
            return 0.0
        w, x, y, z = q[0], q[1], q[2], q[3]
        return float(np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))
