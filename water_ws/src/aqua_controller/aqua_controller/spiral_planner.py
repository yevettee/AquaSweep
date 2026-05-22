"""Archimedes spiral planner ported from isaac_sim_extensions/underwater_robot_ext.

Segments are pre-computed on init (same algorithm as open_loop_plan.py).
Call next_cmd() each control tick to get the next (v, omega) pair.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

# Robot geometry (Dingo-D)
ROBOT_FOOTPRINT_M = 0.686

# Tank geometry
TANK_DIAMETER_M = 8.0
TANK_RADIUS_M = TANK_DIAMETER_M * 0.5
TANK_MARGIN_M = 0.08

# Speed limits
ORBIT_LINEAR_M_S = 0.55
OMEGA_MAX_RAD_S = 2.8

_MERGE_ROUND = 6
_MAX_GUARD_STEPS = 5_000_000


@dataclass(frozen=True)
class Segment:
    v: float
    omega: float
    num_steps: int


def _build_segments(physics_dt: float) -> List[Segment]:
    """Pre-compute all (v, omega) segments for one full spiral pass."""
    if physics_dt <= 0:
        raise ValueError("physics_dt must be positive")

    k = ROBOT_FOOTPRINT_M / (2.0 * math.pi)
    v = float(ORBIT_LINEAR_M_S)
    lim = TANK_RADIUS_M - TANK_MARGIN_M

    theta = 0.0
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
        px_p = k * c - r * sn
        py_p = k * sn + r * c
        px_pp = -2.0 * k * sn - r * c
        py_pp = 2.0 * k * c - r * sn

        denom_sq = denom * denom
        dpsi_dtheta = (px_p * py_pp - py_p * px_pp) / max(denom_sq, 1e-18)

        v_allow = OMEGA_MAX_RAD_S * denom / max(abs(dpsi_dtheta), 1e-12)
        v_eff = min(v, v_allow)

        dtheta_dt = v_eff / denom
        omega = float(max(-OMEGA_MAX_RAD_S, min(OMEGA_MAX_RAD_S, dpsi_dtheta * dtheta_dt)))

        theta += dtheta_dt * physics_dt

        kv = round(v_eff, _MERGE_ROUND)
        ko = round(omega, _MERGE_ROUND)
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
    return out


class SpiralPlanner:
    """Stateful planner — call next_cmd() once per control tick."""

    def __init__(self, physics_dt: float = 1.0 / 60.0) -> None:
        self._segments = _build_segments(physics_dt)
        self._seg_idx = 0
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
            self._seg_idx += 1

        return v, omega

    def reset(self) -> None:
        self._seg_idx = 0
        self._step_in_seg = 0
