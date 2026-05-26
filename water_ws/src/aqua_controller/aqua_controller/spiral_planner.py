"""Archimedes spiral planner ported from isaac_sim_extensions/underwater_robot_ext.

Segments are pre-computed on init (same algorithm as open_loop_plan.py).
Call next_cmd() each control tick to get the next (v, omega) pair.

경로 순서:
  1. 아르키메데스 나선 (중심 → 외곽)
  2. 수조 테두리 한 바퀴 (원주 추종)
  3. 중심 복귀 (제자리 회전 → 직진)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

# Defaults (used when no explicit arguments are passed)
_DEFAULT_ROBOT_FOOTPRINT_M = 0.686
_DEFAULT_TANK_DIAMETER_M   = 8.0
_DEFAULT_TANK_MARGIN_M     = 0.08
_DEFAULT_LINEAR_SPEED_M_S  = 0.55
_DEFAULT_OMEGA_MAX_RAD_S   = 2.8

_MERGE_ROUND     = 6
_MAX_GUARD_STEPS = 5_000_000


@dataclass(frozen=True)
class Segment:
    v: float
    omega: float
    num_steps: int


def _build_wall_follow(
    r_end: float,
    physics_dt: float,
    linear_speed: float,
) -> List[Segment]:
    """수조 테두리(반경 r_end)를 따라 한 바퀴 도는 세그먼트."""
    if r_end < 1e-3:
        return []
    omega_wall = linear_speed / r_end
    n_steps = max(1, round(2.0 * math.pi * r_end / (linear_speed * physics_dt)))
    return [Segment(v=float(linear_speed), omega=float(omega_wall), num_steps=n_steps)]


def _build_return_to_center(
    theta_end: float,
    k: float,
    physics_dt: float,
    linear_speed: float,
    omega_max: float,
) -> List[Segment]:
    """나선 끝 위치에서 수조 중심으로 복귀하는 세그먼트 (제자리 회전 → 직진)."""
    r_end = k * theta_end
    if r_end < 1e-3:
        return []

    c, s = math.cos(theta_end), math.sin(theta_end)

    # 나선 끝에서 로봇의 진행 방향(접선 방향)
    psi_end = math.atan2(k * s + r_end * c, k * c - r_end * s)

    # 현재 위치 → 중심 방향
    angle_to_center = math.atan2(-s, -c)

    # 회전 각도 [-pi, pi] 정규화
    delta = (angle_to_center - psi_end + math.pi) % (2.0 * math.pi) - math.pi

    segs: List[Segment] = []

    # 1) 제자리 회전
    if abs(delta) > 0.05:
        n_turn = max(1, round(abs(delta) / (omega_max * physics_dt)))
        segs.append(Segment(v=0.0, omega=float(math.copysign(omega_max, delta)),
                            num_steps=n_turn))

    # 2) 중심까지 직진
    n_drive = max(1, round(r_end / (linear_speed * physics_dt)))
    segs.append(Segment(v=float(linear_speed), omega=0.0, num_steps=n_drive))

    return segs


def _build_segments(
    physics_dt: float,
    tank_radius: float,
    tank_margin: float,
    robot_footprint: float,
    linear_speed: float,
    omega_max: float,
) -> List[Segment]:
    """Pre-compute all (v, omega) segments for one full spiral pass + return to center."""
    if physics_dt <= 0:
        raise ValueError("physics_dt must be positive")

    k   = robot_footprint / (2.0 * math.pi)
    v   = float(linear_speed)
    lim = tank_radius - tank_margin

    theta      = 0.0
    theta_last = 0.0   # 마지막으로 실제 처리된 theta (복귀 경로 계산에 사용)
    out: List[Segment] = []
    cur_v = cur_omega = None
    cur_n = 0
    guard = 0

    def flush() -> None:
        nonlocal cur_v, cur_omega, cur_n
        if cur_n > 0 and cur_v is not None and cur_omega is not None:
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

        c, sn = math.cos(theta), math.sin(theta)
        px_p  = k * c  - r * sn
        py_p  = k * sn + r * c
        px_pp = -2.0 * k * sn - r * c
        py_pp =  2.0 * k * c  - r * sn

        denom_sq    = denom * denom
        dpsi_dtheta = (px_p * py_pp - py_p * px_pp) / max(denom_sq, 1e-18)

        v_allow = omega_max * denom / max(abs(dpsi_dtheta), 1e-12)
        v_eff   = min(v, v_allow)

        dtheta_dt = v_eff / denom
        omega     = float(max(-omega_max, min(omega_max, dpsi_dtheta * dtheta_dt)))

        theta_last = theta
        theta += dtheta_dt * physics_dt

        kv = round(v_eff, _MERGE_ROUND)
        ko = round(omega,  _MERGE_ROUND)
        if cur_v is None:
            cur_v, cur_omega, cur_n = kv, ko, 1
        elif kv == cur_v and ko == cur_omega:
            cur_n += 1
        else:
            flush()
            cur_v, cur_omega, cur_n = kv, ko, 1

        guard += 1
        if guard > _MAX_GUARD_STEPS:
            raise RuntimeError("Spiral planner exceeded guard step count")

    flush()

    # 나선 완료 후 테두리 한 바퀴
    r_last = k * theta_last
    out.extend(_build_wall_follow(r_last, physics_dt, linear_speed))

    # 테두리 완료 후 중심 복귀 (한 바퀴 돌았으므로 위치·방향 동일 → theta_last 재사용)
    out.extend(_build_return_to_center(
        theta_end=theta_last,
        k=k,
        physics_dt=physics_dt,
        linear_speed=linear_speed,
        omega_max=omega_max,
    ))

    return out


class SpiralPlanner:
    """Stateful planner — call next_cmd() once per control tick."""

    def __init__(
        self,
        physics_dt:      float = 1.0 / 60.0,
        tank_diameter:   float = _DEFAULT_TANK_DIAMETER_M,
        tank_margin:     float = _DEFAULT_TANK_MARGIN_M,
        robot_footprint: float = _DEFAULT_ROBOT_FOOTPRINT_M,
        linear_speed:    float = _DEFAULT_LINEAR_SPEED_M_S,
        omega_max:       float = _DEFAULT_OMEGA_MAX_RAD_S,
    ) -> None:
        self._segments = _build_segments(
            physics_dt      = physics_dt,
            tank_radius     = tank_diameter * 0.5,
            tank_margin     = tank_margin,
            robot_footprint = robot_footprint,
            linear_speed    = linear_speed,
            omega_max       = omega_max,
        )
        self._seg_idx     = 0
        self._step_in_seg = 0

    @property
    def is_done(self) -> bool:
        return self._seg_idx >= len(self._segments)

    @property
    def total_segments(self) -> int:
        return len(self._segments)

    @property
    def current_segment(self) -> int:
        return self._seg_idx

    def next_cmd(self) -> Tuple[float, float]:
        """Return (v m/s, omega rad/s) for the current step and advance."""
        if self.is_done:
            return 0.0, 0.0

        seg = self._segments[self._seg_idx]
        v, omega = seg.v, seg.omega

        self._step_in_seg += 1
        if self._step_in_seg >= seg.num_steps:
            self._step_in_seg = 0
            self._seg_idx    += 1

        return v, omega

    def reset(self) -> None:
        self._seg_idx     = 0
        self._step_in_seg = 0
