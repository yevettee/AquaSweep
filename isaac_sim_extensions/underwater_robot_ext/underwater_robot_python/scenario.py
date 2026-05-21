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

"""ROS2 cmd_vel 토픽으로 로봇을 제어하는 시나리오.

/under_robot_1/cmd_vel (geometry_msgs/Twist) 을 구독하며,
매 physics step마다 최신 (linear.x, angular.z) 값을 DifferentialController에 전달한다.
cmd_vel_receiver가 연결되지 않은 상태에서는 로봇이 정지한다.
"""

from typing import Optional

import carb

from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController

from .global_variables import DINGO_WHEEL_BASE_M, DINGO_WHEEL_RADIUS_M

LOG_TAG = "[underwater.robot]"


class UnderwaterTankJetbotFsm:
    """ROS2 cmd_vel 토픽 수신값을 매 physics step마다 로봇에 적용한다."""

    def __init__(self) -> None:
        self._robot = None
        self._controller: Optional[DifferentialController] = None
        self._cmd_receiver = None

    def initialize(self, robot, physics_dt: float) -> None:
        self._robot = robot
        self._controller = DifferentialController(
            name="underwater_tank_diff",
            wheel_radius=DINGO_WHEEL_RADIUS_M,
            wheel_base=DINGO_WHEEL_BASE_M,
        )
        self._controller.reset()
        carb.log_info(f"{LOG_TAG} initialized — waiting for /under_robot_1/cmd_vel")

    def sync_after_world_reset(self, robot, physics_dt: float) -> None:
        self._robot = robot
        if self._controller is not None:
            self._controller.reset()

    def teardown(self) -> None:
        self._robot = None
        self._controller = None
        self._cmd_receiver = None

    def set_cmd_vel_receiver(self, receiver) -> None:
        self._cmd_receiver = receiver
        carb.log_info(f"{LOG_TAG} cmd_vel receiver attached — topic control enabled")

    def on_physics_step(self, step_size: float) -> None:
        del step_size
        if self._robot is None or self._controller is None or self._cmd_receiver is None:
            return

        v, omega = self._cmd_receiver.get_cmd()
        self._robot.apply_wheel_actions(self._controller.forward(command=[v, omega]))
