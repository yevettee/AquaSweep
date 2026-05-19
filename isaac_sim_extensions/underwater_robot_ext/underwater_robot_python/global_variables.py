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

EXTENSION_TITLE = "underwater.robot"

EXTENSION_DESCRIPTION = ""

# World.scene에 등록하는 WheeledRobot의 scene 이름 (다른 확장과 충돌 방지)
ROBOT_SCENE_NAME = "underwater_robot_v1"

# Stage 상 로봇 루트 (data/underwater_robot_camera_v1.usd reference)
ROBOT_PRIM_PATH = "/World/Dingo"

# extension/data/underwater_robot_camera_v1.usd — /Root/dingo, VisualWheels 는 base_link 자식
DINGO_USD_FILENAME = "test_dingo_2.usd"

# v1 USD 측정값 (usd-core BBoxCache / wheel_link transforms)
DINGO_WHEEL_RADIUS_M = 0.049
DINGO_WHEEL_BASE_M = 0.4523
ROBOT_FOOTPRINT_M = 0.686

# Clearpath Dingo-D 플랫폼 질량 (USD collision mass 합 ~1.2 kg 은 플레이스홀더)
ROBOT_MASS_KG = 9.1

# 휠 반경 근사만큼 지면 위 스폰 (추가 스케일 없음)
ROBOT_SPAWN_Z_M = 0.05

# 물리 스텝 기본 유체 근사 (타임라인 Play 중 전역 적용)
DEFAULT_FLUID_FORCES_ENABLED = False
BUOYANCY_WEIGHT_FRACTION = 0.75
DRAG_LINEAR_XY = 0.5
DRAG_LINEAR_Z = 1.0
GRAVITY_MPS2 = 9.81

# 루트 중심 궤적 시각화 (Physics step 샘플, 메인 로직과 무관)
DEBUG_CENTER_TRAIL_ENABLED = True
DEBUG_TRAIL_MAX_POINTS = 40000
DEBUG_TRAIL_CURVE_PRIM_PATH = "/World/Debug/DingoCenterTrail"
DEBUG_TRAIL_LINE_WIDTH_WORLD = 0.02

# suction_intake 전방 키네마틱 끌어오기 (물리/충돌 없음, set_world_pose)
SUCTION_KINEMATIC_ENABLED = True
SUCTION_INTAKE_PRIM_PATH = f"{ROBOT_PRIM_PATH}/dingo/base_link/suction_intake"
SUCTION_FORWARD_OFFSET_M = 0.20
SUCTION_PULL_SPEED_MPS = 0.5
SUCTION_CATCH_RADIUS_M = 0.5
SUCTION_TEST_DEBRIS_PRIM_PATH = "/World/SuctionTest/debris"
SUCTION_TEST_DEBRIS_SIZE_M = 0.06
# bind 시 앵커에서 intake 반대 방향으로 이만큼 떨어진 곳에 스폰 (catch 반경 안)
SUCTION_TEST_DEBRIS_SPAWN_BEFORE_ANCHOR_M = 0.12

# Deprecated aliases (JetBot era)
JETBOT_SCENE_NAME = ROBOT_SCENE_NAME
JETBOT_TARGET_FOOTPRINT_M = ROBOT_FOOTPRINT_M
JETBOT_MASS_KG = ROBOT_MASS_KG
JETBOT_LINEAR_SCALE = 1.0
