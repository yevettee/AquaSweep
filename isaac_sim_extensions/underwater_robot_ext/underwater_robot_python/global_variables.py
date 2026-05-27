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

# Stage 상 로봇 루트 (hippo USD reference). 단일 로봇 시절의 기본값이며
# 멀티풀에서는 /World/Pools/Pool_<n>/Robot 으로 spawn 됨.
ROBOT_PRIM_PATH = "/World/Hippo"

# extension/data/hippo_v1.usd — /Root/hippo, VisualWheels 는 base_link 자식.
HIPPO_USD_FILENAME = "hippo_v1_lite.usdz"

# data/hippo_v1.usd 측정값 (wheel_link transforms)
HIPPO_WHEEL_RADIUS_M = 0.049
HIPPO_WHEEL_BASE_M = 0.4523

ROBOT_FOOTPRINT_M = 0.686

# 풀 Bottom mesh 상면(z≈0.25) 위로 약간 띄워 스폰 (aquafarm_final 풀 shell 기준)
ROBOT_SPAWN_Z_M = 0.26

# D6 Joint Z 구속 — wheel_low = 0.0이 되는 base_link Z 높이
# 바퀴 반경(0.049m) 기준으로 설정, 테스트 후 미세 조정 가능
ROBOT_CONSTRAINT_Z_M = 0.049

# water_tank_env WaterPhysicsApplier — LOAD 시 tag_aquasweep_attrs()가 base_link에 설정
# BCD 모드: volume 은 mass/ρ 균형값. scenario 가 aquasweep:buoyancy_mult 로 상태별 부력비 조절.
#   IDLE_FLOATING ≈ 1.10 (부유)  SINKING ≈ 0.70  CLEANING ≈ 0.95  ASCENDING ≈ 1.30
# mass 추정 ~15 kg (Dingo-D 13 kg + 청소 장비) → 균형 부피 0.015 m³. 실측 후 튜닝 권장.
ROBOT_VOLUME_M3 = 0.015     # 균형 부피 (multiplier=1.0 에서 부력 = 중력)
ROBOT_HALF_HEIGHT_M = 0.115
DRAG_LINEAR_XY = 8.0        # N·s/m — 스러스터 추진과 균형 (0.55m/s @ ~4.4N)
DRAG_ANGULAR = 6.0          # N·m·s/rad

# BCD multiplier — 모션 상태별 부력비 (mass·g 대비)
BUOYANCY_MULT_IDLE_FLOATING = 1.10
BUOYANCY_MULT_SINKING       = 0.70
BUOYANCY_MULT_CLEANING      = 0.95
BUOYANCY_MULT_ASCENDING     = 1.30

# 루트 중심 궤적 시각화 (Physics step 샘플)
DEBUG_CENTER_TRAIL_ENABLED = False
DEBUG_TRAIL_MAX_POINTS = 40000
DEBUG_TRAIL_CURVE_PRIM_PATH = "/World/Debug/HippoCenterTrail"
DEBUG_TRAIL_LINE_WIDTH_WORLD = 0.02

# 양식장 순환 수류 — 수조 중심 기준 solid-body rotation
WATER_ROTATION_OMEGA = 0.05       # rad/s (양수=반시계, 음수=시계 방향)
WATER_ROTATION_CENTER = (0.0, 0.0)  # 수조 중심 좌표 (m)

# Physics step 디버그 — False로 끄고 extension reload 후 LOAD → RUN
DEBUG_ENABLE_WATER_PHYSICS = True
DEBUG_ENABLE_STURGEON_ANIM = True
DEBUG_ENABLE_WATER_SURFACE_ANIM = True
DEBUG_ENABLE_SUCTION = True
