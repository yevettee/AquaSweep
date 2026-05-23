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
# 우리가 직접 개조한 underwater 청소 로봇 (Clearpath Dingo-D 플랫폼 기반).
HIPPO_USD_FILENAME = "hippo_v1.usd"

# 후방 호환: 기존 import 코드가 즉시 깨지지 않도록 별칭 유지.
DINGO_USD_FILENAME = HIPPO_USD_FILENAME

# data/hippo_v1.usd 측정값 (Dingo-D 플랫폼 wheel_link transforms)
# - left_wheel_link/collisions Cylinder radius
# - |left_wheel_link − right_wheel_link| in world XY
# - base_link world bbox max(X,Y)
HIPPO_WHEEL_RADIUS_M = 0.049
HIPPO_WHEEL_BASE_M = 0.4523
# 후방 호환
DINGO_WHEEL_RADIUS_M = HIPPO_WHEEL_RADIUS_M
DINGO_WHEEL_BASE_M = HIPPO_WHEEL_BASE_M

ROBOT_FOOTPRINT_M = 0.686

# Clearpath Dingo-D 플랫폼 질량 (USD collision mass 합 ~1.2 kg 은 플레이스홀더)
ROBOT_MASS_KG = 9.1

# 휠 반경 근사만큼 지면 위 스폰 (추가 스케일 없음)
ROBOT_SPAWN_Z_M = 0.05

# water_tank_env WaterPhysicsApplier용 aquasweep:* 속성값 — LOAD 시 base_link에 설정됨
ROBOT_VOLUME_M3 = 0.0  # 0.025 m³  hippo (Dingo-D 기반) 근사 부피 (부력 계산) — 디버그용 0
ROBOT_HALF_HEIGHT_M = 0.115   # m   부분 잠김 보간용 반높이

# 물리 스텝 기본 유체 근사 (타임라인 Play 중 전역 적용)
DEFAULT_FLUID_FORCES_ENABLED = False
BUOYANCY_WEIGHT_FRACTION = 0.0   # 0.92 강한 부력 — 로봇이 물에 거의 떠있는 느낌
DRAG_LINEAR_XY = 0.0  # 0.5            # 수평 항력 (원래 0.5) — 움직임이 뭉툭하게 감쇠
DRAG_LINEAR_Z  = 0.0   # 3.0            # 수직 항력 (원래 1.0) — 상하 진동 빠르게 감쇠
DRAG_ANGULAR   = 0.0   # 2.0           # 회전 항력 (원래 0.5) — 회전이 물속처럼 부드럽게 제동
GRAVITY_MPS2 = 9.81

# 루트 중심 궤적 시각화 (Physics step 샘플, 메인 로직과 무관)
DEBUG_CENTER_TRAIL_ENABLED = False
DEBUG_TRAIL_MAX_POINTS = 40000
DEBUG_TRAIL_CURVE_PRIM_PATH = "/World/Debug/HippoCenterTrail"
DEBUG_TRAIL_LINE_WIDTH_WORLD = 0.02

# Deprecated aliases (JetBot era)
JETBOT_SCENE_NAME = ROBOT_SCENE_NAME
JETBOT_TARGET_FOOTPRINT_M = ROBOT_FOOTPRINT_M
JETBOT_MASS_KG = ROBOT_MASS_KG
JETBOT_LINEAR_SCALE = 1.0

# ── Debug flags for physics step (toggle to isolate issues) ────────────────
# Set to False to disable each system and test robot movement in isolation.
# Usage: change flag → restart Isaac Sim or reload extension → LOAD → RUN
DEBUG_ENABLE_WATER_PHYSICS = True       # 부력, 항력, 지면효과
DEBUG_ENABLE_STURGEON_ANIM = True       # 물고기 수영 애니메이션
DEBUG_ENABLE_WATER_SURFACE_ANIM = True  # 물 표면 파동 애니메이션
DEBUG_ENABLE_SUCTION = True             # 흡입 시스템
