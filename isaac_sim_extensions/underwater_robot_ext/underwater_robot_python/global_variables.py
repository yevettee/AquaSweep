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
JETBOT_SCENE_NAME = "underwater_tank_jetbot"

# 휠 링크 아래에 추가되는 트랙 비주얼 Xform 이름 (기본 JetBot 휠 메시 대신 얹을 레이어)
TRACK_VISUAL_CHILD_NAME = "track_visual"

# 스톡 JetBot 평면 풋프린트 근사(m) → 목표 약 40cm 에 맞춘 USD/Differential 공통 스케일
JETBOT_REF_FOOTPRINT_M = 0.14
JETBOT_TARGET_FOOTPRINT_M = 0.4
JETBOT_LINEAR_SCALE = JETBOT_TARGET_FOOTPRINT_M / JETBOT_REF_FOOTPRINT_M

# 물리 스텝 기본 유체 근사 (타임라인 Play 중 전역 적용)
DEFAULT_FLUID_FORCES_ENABLED = True
BUOYANCY_WEIGHT_FRACTION = 0.75
DRAG_LINEAR_XY = 0.5
DRAG_LINEAR_Z = 1.0
GRAVITY_MPS2 = 9.81
JETBOT_MASS_KG = 3.0
