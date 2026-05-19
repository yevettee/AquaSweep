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
원형 수조(직경 5 m, 중심 시작)에서 아르키메데스 나선 r=kθ 형태를 오픈루프로 재생합니다.
물리 스텝마다 미리 계산한 (v, ω) 구간 큐만 진행하며 pose 기반 피드백은 사용하지 않습니다.
명목 반경이 수조 허용 한계에 도달하면 세그먼트 재생 종료 후 정지 명령이 이어집니다.
시작 헤딩은 +x 반경 바깥으로, θ=0 대응 접선과 가정합니다.
"""

from typing import List, Optional

import carb

from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController

from .global_variables import DINGO_WHEEL_BASE_M, DINGO_WHEEL_RADIUS_M
from .open_loop_plan import (
    ROBOT_DIAMETER_M,
    Segment,
    TANK_DIAMETER_M,
    TANK_RADIUS_M,
    build_spiral_segments,
    summarize_plan,
)

LOG_TAG = "[underwater.robot]"


class UnderwaterTankJetbotFsm:
    """미리 계산한 등속 나선 (v, ω) 세그먼트를 순서대로 재생하는 오픈루프 시나리오."""

    def __init__(self) -> None:
        self._robot = None
        self._controller: Optional[DifferentialController] = None
        self._physics_dt = 1.0 / 60.0
        self._segments: List[Segment] = []
        self._seg_idx = 0
        self._step_in_seg = 0

    def initialize(self, robot, physics_dt: float) -> None:
        self._physics_dt = float(physics_dt)
        self._robot = robot
        self._controller = DifferentialController(
            name="underwater_tank_diff",
            wheel_radius=DINGO_WHEEL_RADIUS_M,
            wheel_base=DINGO_WHEEL_BASE_M,
        )
        self._controller.reset()
        self._rebuild_plan_and_indices()
        self._log_session_start()

    def sync_after_world_reset(self, robot, physics_dt: float) -> None:
        self._robot = robot
        self._physics_dt = float(physics_dt)
        if self._controller is not None:
            self._controller.reset()
        self._rebuild_plan_and_indices()
        self._log_session_start()

    def teardown(self) -> None:
        self._robot = None
        self._controller = None
        self._segments.clear()
        self._seg_idx = 0
        self._step_in_seg = 0

    def on_physics_step(self, step_size: float) -> None:
        del step_size
        if self._robot is None or self._controller is None:
            return

        if self._seg_idx >= len(self._segments):
            self._robot.apply_wheel_actions(self._controller.forward(command=[0.0, 0.0]))
            return

        seg = self._segments[self._seg_idx]
        self._robot.apply_wheel_actions(self._controller.forward(command=[seg.v, seg.omega]))

        self._step_in_seg += 1
        if self._step_in_seg >= seg.num_steps:
            self._step_in_seg = 0
            self._seg_idx += 1

    def _rebuild_plan_and_indices(self) -> None:
        self._segments = build_spiral_segments(self._physics_dt)
        self._seg_idx = 0
        self._step_in_seg = 0

    def _log_session_start(self) -> None:
        summary = summarize_plan(self._segments)
        msg = (
            f"{LOG_TAG} open-loop spiral START physics_dt={self._physics_dt:.6g}s "
            f"tank_D={TANK_DIAMETER_M}m tank_R={TANK_RADIUS_M}m spiral_Δr/rev={ROBOT_DIAMETER_M:.4f}m — {summary}"
        )
        carb.log_info(msg)
        print(msg, flush=True)
