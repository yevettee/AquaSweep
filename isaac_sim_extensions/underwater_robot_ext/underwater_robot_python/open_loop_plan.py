# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""수조·스텝 길이·dt만으로 (v, ω) 구간과 스텝 수를 미리 계산 — 월드 pose 없음.

방사 직진 후 원심 기준 접선으로 맞추기 위해 제자리 90° 회전(반시계)을 넣고,
한 바퀴 궤도 후 다음 방사 전에는 접선→반경 방향으로 시계 90° 회전합니다.
시작 시 로봇 헤딩은 탱크 중심에서 바깥으로 향한다고 가정합니다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from .global_variables import JETBOT_TARGET_FOOTPRINT_M

# geometry (시뮬과 동치: 직경 5m 수조, close-loop 시나리오와 동일한 상수 유지)
TANK_RADIUS_M = 2.5
TANK_MARGIN_M = 0.08
ROBOT_DIAMETER_M = JETBOT_TARGET_FOOTPRINT_M

# speeds (m/s), rad/s cap
RADIAL_LINEAR = 0.85
ORBIT_LINEAR = 0.55
ORBIT_RADIUS_MIN_M = 0.08
OMEGA_MAX_RAD_S = 2.8

# 제자리 90°: ω 부호는 궤도 구간과 동일 컨벤션(+ = 반시계)
_TURN_MAG_RAD_S = min(2.5, OMEGA_MAX_RAD_S)


@dataclass(frozen=True)
class Segment:
    v: float
    omega: float
    num_steps: int


def _num_steps_quarter_turn(physics_dt: float) -> int:
    """π/2 rad @ |ω| = _TURN_MAG_RAD_S."""
    return max(1, int(round((math.pi / 2.0) / (_TURN_MAG_RAD_S * physics_dt))))


def build_spiral_segments(physics_dt: float) -> List[Segment]:
    if physics_dt <= 0:
        raise ValueError("physics_dt must be positive")

    d = float(ROBOT_DIAMETER_M)
    v_rad = float(RADIAL_LINEAR)
    v_orb = float(ORBIT_LINEAR)
    lim = float(TANK_RADIUS_M) - float(TANK_MARGIN_M)

    out: List[Segment] = []
    r_nom = 0.0
    n_turn = _num_steps_quarter_turn(physics_dt)

    while True:
        if r_nom + d > lim:
            break

        # 이전 고리까지 궤도로 끝났으면 헤딩은 접선(CCW); 다음 방사 직진 전 반경 방향으로 CW 90°
        if r_nom > 0.0:
            out.append(Segment(v=0.0, omega=-_TURN_MAG_RAD_S, num_steps=n_turn))

        n_rad = max(1, int(round(d / (v_rad * physics_dt))))
        out.append(Segment(v=v_rad, omega=0.0, num_steps=n_rad))

        r_nom += d

        # 반경 바깥 헤딩 → 탱크 중심 기준 CCW 접선으로 CCW 90°
        out.append(Segment(v=0.0, omega=_TURN_MAG_RAD_S, num_steps=n_turn))

        omega_raw = v_orb / max(r_nom, ORBIT_RADIUS_MIN_M)
        omega = float(max(-OMEGA_MAX_RAD_S, min(OMEGA_MAX_RAD_S, omega_raw)))

        arc_len = 2.0 * math.pi * r_nom
        T_orbit = arc_len / max(v_orb, 1e-6)
        n_orb = max(1, int(round(T_orbit / physics_dt)))
        out.append(Segment(v=v_orb, omega=omega, num_steps=n_orb))

    return out


def summarize_plan(segments: List[Segment]) -> str:
    nseg = len(segments)
    total_steps = sum(s.num_steps for s in segments)
    return f"{nseg} segments, {total_steps} physics steps total"
