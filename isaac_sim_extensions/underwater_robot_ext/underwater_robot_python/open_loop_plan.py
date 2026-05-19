# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""수조 반지름·dt·등속선속만으로 미리 이산화한 (v, ω) 세그먼트 — 월드 pose 불사용.

연속 나선은 아르키메데스형 r(θ)=r₀+kθ 로만 규정하고, 같은 θ를 시간과 함께 적분해
등속 v 로 주행 시 필요한 헤딩 변화율(요레이트) ω 를 해석적으로 구해 스텝마다 채운다.

가정 — 탱크 중심이 원점, 스타트 헤딩은 +x(반경 바깥), 연속 나선은 r=kθ(θ≥0) 로 원점에서 출발해
θ=0 에서 접선이 +x 와 일치한다. 종료는 명목 반경 r≥수조 허용 한계(직경 5 m − 마진) 시점까지.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from .global_variables import ROBOT_FOOTPRINT_M

# geometry — 수조 직경 5 m; 명목반경 한계는 중심거리 − 마진
TANK_DIAMETER_M = 5.0
TANK_RADIUS_M = TANK_DIAMETER_M * 0.5
TANK_MARGIN_M = 0.08
ROBOT_DIAMETER_M = ROBOT_FOOTPRINT_M

# 한 회전당 반경 증가량 (≈ 차량 직경, 달팽이 권 간격)
SPIRAL_RADIUS_INCREASE_PER_REV_M = ROBOT_DIAMETER_M

# speeds (m/s), rad/s cap
ORBIT_LINEAR = 0.55
OMEGA_MAX_RAD_S = 2.8

_MERGE_ROUND = 6
_MAX_GUARD_STEPS = 5_000_000


@dataclass(frozen=True)
class Segment:
    v: float
    omega: float
    num_steps: int


def build_spiral_segments(physics_dt: float) -> List[Segment]:
    if physics_dt <= 0:
        raise ValueError("physics_dt must be positive")

    k = SPIRAL_RADIUS_INCREASE_PER_REV_M / (2.0 * math.pi)
    v = float(ORBIT_LINEAR)
    lim = float(TANK_RADIUS_M) - float(TANK_MARGIN_M)

    theta = 0.0
    out: List[Segment] = []
    cur_v: float | None = None
    cur_omega: float | None = None
    cur_n = 0
    guard = 0

    def flush() -> None:
        nonlocal cur_v, cur_omega, cur_n
        if cur_n <= 0 or cur_v is None or cur_omega is None:
            return
        out.append(Segment(v=cur_v, omega=float(cur_omega), num_steps=cur_n))
        cur_v = cur_omega = None
        cur_n = 0

    while True:
        r = k * theta
        if r >= lim:
            break

        denom = math.hypot(k, r)
        if denom < 1e-12:
            break

        c = math.cos(theta)
        sn = math.sin(theta)
        # p'(θ) for x=r cos θ, y=r sin θ with r=r0+kθ, dr/dθ=k
        px_p = k * c - r * sn
        py_p = k * sn + r * c
        px_pp = -2.0 * k * sn - r * c
        py_pp = 2.0 * k * c - r * sn

        denom_sq = denom * denom
        dpsi_dtheta = (px_p * py_pp - py_p * px_pp) / max(denom_sq, 1e-18)

        v_allow = float(OMEGA_MAX_RAD_S) * denom / max(abs(dpsi_dtheta), 1e-12)
        v_eff = min(v, v_allow)

        dtheta_dt = v_eff / denom
        omega_raw = dpsi_dtheta * dtheta_dt
        omega = float(max(-OMEGA_MAX_RAD_S, min(OMEGA_MAX_RAD_S, omega_raw)))

        # 이상적인 나선에 걸린 공간 θ 적분 전개(오차는 오픈루프 특성상 물리에 맡김)
        theta = theta + dtheta_dt * physics_dt

        key_v = round(v_eff, _MERGE_ROUND)
        key_o = round(omega, _MERGE_ROUND)
        if cur_v is None:
            cur_v, cur_omega, cur_n = key_v, key_o, 1
        elif key_v == cur_v and key_o == cur_omega:
            cur_n += 1
        else:
            flush()
            cur_v, cur_omega, cur_n = key_v, key_o, 1

        guard += 1
        if guard > _MAX_GUARD_STEPS:
            raise RuntimeError("spiral planner exceeded guard step count")

    flush()
    return out


def summarize_plan(segments: List[Segment]) -> str:
    nseg = len(segments)
    total_steps = sum(s.num_steps for s in segments)
    return f"{nseg} segments, {total_steps} physics steps total"
