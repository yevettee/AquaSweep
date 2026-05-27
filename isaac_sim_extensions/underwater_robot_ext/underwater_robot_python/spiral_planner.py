"""Archimedes spiral planner for Isaac Sim.

aqua_controller/spiral_planner.py에서 이식.
Segments are pre-computed on init (same algorithm as open_loop_plan.py).
Call next_cmd() each control tick to get the next (v, omega) pair.

경로 순서 (진행률 50/50):
  1. spiral_out: 아르키메데스 나선 (중심 → 외곽) ~50%
  2. turn: 180도 제자리 회전
  3. spiral_return: 역방향 나선 (외곽 → 중심) ~50%
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

DEFAULT_ROBOT_FOOTPRINT_M = 0.686
DEFAULT_TANK_DIAMETER_M   = 8.0
DEFAULT_TANK_MARGIN_M     = 0.8   # 벽에서 0.5m 여유
DEFAULT_LINEAR_SPEED_M_S  = 4.5   # 1.5 m/s (빠르지만 안정적)
DEFAULT_OMEGA_MAX_RAD_S   = 15.0   # 4.0 rad/s (≈230°/초, 180도 회전 ~0.8초)

_MERGE_ROUND     = 6
_MAX_GUARD_STEPS = 5_000_000


@dataclass(frozen=True)
class Segment:
    v: float
    omega: float
    num_steps: int


def _build_180_reverse_turn(
    physics_dt: float,
    omega_max: float,
    linear_speed: float,
) -> List[Segment]:
    """후진하면서 180도 회전 (U턴).
    
    나선이 반시계 방향으로 진행하므로, 180도 회전 시:
    - 시계 방향(음수 omega)으로 회전해야 중심 쪽으로 호를 그림
    - 후진하면서 시계방향 회전 → 벽에서 멀어지며 방향 전환
    """
    reverse_speed = linear_speed * 0.5  # 후진 속도 (전진의 절반)
    turn_omega = omega_max * 0.7        # 회전 속도 (약간 줄임)
    
    n_turn = max(1, round(math.pi / (turn_omega * physics_dt)))
    # 시계 방향 회전 (음수 omega) → 중심 쪽으로 호를 그림
    return [Segment(v=-reverse_speed, omega=-float(turn_omega), num_steps=n_turn)]


def _build_reverse_spiral(
    spiral_segs: List[Segment],
) -> List[Segment]:
    """나선 세그먼트를 역순으로 뒤집어서 복귀 경로 생성.
    
    외곽→중심으로 돌아가려면:
    1. 세그먼트 순서를 역순으로
    2. omega 부호를 반전 (반대 방향으로 휘어야 함)
    """
    reversed_segs = []
    for seg in reversed(spiral_segs):
        reversed_segs.append(Segment(
            v=seg.v,
            omega=-seg.omega,  # 회전 방향 반전
            num_steps=seg.num_steps,
        ))
    return reversed_segs


def _build_segments(
    physics_dt: float,
    tank_radius: float,
    tank_margin: float,
    robot_footprint: float,
    linear_speed: float,
    omega_max: float,
) -> Tuple[List[Segment], int, int]:
    """나선 외곽 진행 + 180도 회전 + 나선 복귀 세그먼트 생성.
    
    경로:
      1. 나선 외곽 (중심 → 외곽): ~50%
      2. 180도 제자리 회전: 짧음
      3. 나선 복귀 (외곽 → 중심): ~50%
    
    Returns:
        (segments, spiral_out_count, turn_count): 세그먼트 리스트와 페이즈별 수
    """
    if physics_dt <= 0:
        raise ValueError("physics_dt must be positive")

    k   = robot_footprint / (2.0 * math.pi)
    v   = float(linear_speed)
    lim = tank_radius - tank_margin

    theta      = 0.0
    spiral_out: List[Segment] = []
    cur_v = cur_omega = None
    cur_n = 0
    guard = 0

    def flush() -> None:
        nonlocal cur_v, cur_omega, cur_n
        if cur_n > 0 and cur_v is not None and cur_omega is not None:
            spiral_out.append(Segment(v=cur_v, omega=float(cur_omega), num_steps=cur_n))
        cur_v = cur_omega = None
        cur_n = 0

    # 1. 나선 외곽 (중심 → 외곽)
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
    spiral_out_count = len(spiral_out)

    # 2. 후진하면서 180도 회전 (U턴, 벽 충돌 방지)
    turn_segs = _build_180_reverse_turn(physics_dt, omega_max, linear_speed)
    turn_count = len(turn_segs)

    # 3. 나선 복귀 (역방향 나선)
    spiral_return = _build_reverse_spiral(spiral_out)

    # 전체 세그먼트 조합
    out = spiral_out + turn_segs + spiral_return

    return out, spiral_out_count, turn_count


class SpiralPlanner:
    """Stateful planner — call next_cmd() once per control tick.
    
    새 경로 구조 (진행률 50/50):
      1. spiral_out: 중심 → 외곽 (~50%)
      2. turn: 180도 회전 (짧음)
      3. spiral_return: 외곽 → 중심 (~50%)
    """

    # Phase names for status reporting
    PHASE_SPIRAL_OUT = "spiral_out"      # 외곽 진행 (~50%)
    PHASE_TURN = "turn"                   # 180도 회전
    PHASE_SPIRAL_RETURN = "spiral_return" # 중심 복귀 (~50%)
    PHASE_DONE = "done"
    
    # 하위 호환성 (기존 코드에서 참조할 수 있음)
    PHASE_SPIRAL = PHASE_SPIRAL_OUT
    PHASE_RETURN = PHASE_SPIRAL_RETURN

    def __init__(
        self,
        physics_dt:      float = 1.0 / 60.0,
        tank_diameter:   float = DEFAULT_TANK_DIAMETER_M,
        tank_margin:     float = DEFAULT_TANK_MARGIN_M,
        robot_footprint: float = DEFAULT_ROBOT_FOOTPRINT_M,
        linear_speed:    float = DEFAULT_LINEAR_SPEED_M_S,
        omega_max:       float = DEFAULT_OMEGA_MAX_RAD_S,
    ) -> None:
        self._physics_dt = physics_dt
        self._params = {
            "tank_diameter": tank_diameter,
            "tank_margin": tank_margin,
            "robot_footprint": robot_footprint,
            "linear_speed": linear_speed,
            "omega_max": omega_max,
        }
        self._segments, spiral_out_count, turn_count = _build_segments(
            physics_dt      = physics_dt,
            tank_radius     = tank_diameter * 0.5,
            tank_margin     = tank_margin,
            robot_footprint = robot_footprint,
            linear_speed    = linear_speed,
            omega_max       = omega_max,
        )
        self._seg_idx     = 0
        self._step_in_seg = 0
        self._total_steps = sum(seg.num_steps for seg in self._segments)
        self._current_step = 0
        
        # Phase boundaries
        # spiral_out: 인덱스 0 ~ (spiral_out_count - 1)
        # turn: 인덱스 spiral_out_count ~ (spiral_out_count + turn_count - 1)
        # spiral_return: 나머지
        self._spiral_out_end_seg = spiral_out_count - 1 if spiral_out_count > 0 else -1
        self._turn_end_seg = spiral_out_count + turn_count - 1 if turn_count > 0 else self._spiral_out_end_seg

    def rebuild(
        self,
        tank_diameter:   float = None,
        tank_margin:     float = None,
        robot_footprint: float = None,
        linear_speed:    float = None,
        omega_max:       float = None,
    ) -> None:
        """파라미터 변경 후 segments 재생성."""
        if tank_diameter is not None:
            self._params["tank_diameter"] = tank_diameter
        if tank_margin is not None:
            self._params["tank_margin"] = tank_margin
        if robot_footprint is not None:
            self._params["robot_footprint"] = robot_footprint
        if linear_speed is not None:
            self._params["linear_speed"] = linear_speed
        if omega_max is not None:
            self._params["omega_max"] = omega_max
        
        self._segments, spiral_out_count, turn_count = _build_segments(
            physics_dt      = self._physics_dt,
            tank_radius     = self._params["tank_diameter"] * 0.5,
            tank_margin     = self._params["tank_margin"],
            robot_footprint = self._params["robot_footprint"],
            linear_speed    = self._params["linear_speed"],
            omega_max       = self._params["omega_max"],
        )
        self._total_steps = sum(seg.num_steps for seg in self._segments)
        
        # Phase boundaries 재계산
        self._spiral_out_end_seg = spiral_out_count - 1 if spiral_out_count > 0 else -1
        self._turn_end_seg = spiral_out_count + turn_count - 1 if turn_count > 0 else self._spiral_out_end_seg
        
        self.reset()

    @property
    def is_done(self) -> bool:
        return self._seg_idx >= len(self._segments)

    @property
    def total_segments(self) -> int:
        return len(self._segments)

    @property
    def current_segment(self) -> int:
        return self._seg_idx

    @property
    def total_steps(self) -> int:
        return self._total_steps

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def progress(self) -> float:
        if self._total_steps == 0:
            return 1.0
        return min(1.0, self._current_step / self._total_steps)

    @property
    def phase(self) -> str:
        if self.is_done:
            return self.PHASE_DONE
        if self._seg_idx <= self._spiral_out_end_seg:
            return self.PHASE_SPIRAL_OUT
        if self._seg_idx <= self._turn_end_seg:
            return self.PHASE_TURN
        return self.PHASE_SPIRAL_RETURN

    def next_cmd(self) -> Tuple[float, float]:
        """Return (v m/s, omega rad/s) for the current step and advance."""
        if self.is_done:
            return 0.0, 0.0

        seg = self._segments[self._seg_idx]
        v, omega = seg.v, seg.omega

        self._step_in_seg += 1
        self._current_step += 1
        if self._step_in_seg >= seg.num_steps:
            self._step_in_seg = 0
            self._seg_idx    += 1

        return v, omega

    def reset(self) -> None:
        self._seg_idx     = 0
        self._step_in_seg = 0
        self._current_step = 0

    def pause(self) -> int:
        """일시정지 — 현재 step 반환."""
        return self._current_step

    def resume(self) -> int:
        """재개 — 현재 step 반환."""
        return self._current_step
