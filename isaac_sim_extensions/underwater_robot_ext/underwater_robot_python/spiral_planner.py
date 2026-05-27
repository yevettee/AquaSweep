"""Archimedes spiral planner for Isaac Sim.

경로 순서:
  1. spiral_out : 아르키메데스 나선 (중심 → 외곽)
  2. wall_follow : 수조 테두리를 따라 한 바퀴
  3. return      : 제자리 회전 → 직진으로 중심 복귀

제어 방식:
  - next_cmd_closed_loop(rel_x, rel_y, rel_theta) : Pure Pursuit 폐루프 (권장)
  - next_cmd()                                     : 오픈루프 (하위 호환)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

DEFAULT_ROBOT_FOOTPRINT_M = 0.686
DEFAULT_TANK_DIAMETER_M   = 8.0
DEFAULT_TANK_MARGIN_M     = 0.6
DEFAULT_LINEAR_SPEED_M_S  = 4.5
DEFAULT_OMEGA_MAX_RAD_S   = 15.0

_MERGE_ROUND     = 6
_MAX_GUARD_STEPS = 5_000_000
_LOOKAHEAD_M     = 0.5   # Pure Pursuit lookahead distance (m)
_DONE_RADIUS_M   = 0.3   # 이 반경 안에 들어오면 복귀 완료 판정


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
    r_override: float = None,
) -> List[Segment]:
    """나선 끝 위치에서 수조 중심으로 복귀하는 세그먼트 (제자리 회전 → 직진).

    r_override: 실제 반경(벽 순회 후 위치)을 명시적으로 지정할 때 사용.
                None이면 k * theta_end 로 계산.
    """
    r_end = r_override if r_override is not None else k * theta_end
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
) -> Tuple[List[Segment], int, int, int]:
    """나선 외곽 + 테두리 한 바퀴 + 중심 복귀 세그먼트 생성.

    Returns:
        (segments, spiral_out_count, wall_follow_count, return_count)
    """
    if physics_dt <= 0:
        raise ValueError("physics_dt must be positive")

    k   = robot_footprint / (2.0 * math.pi)
    v   = float(linear_speed)
    lim = tank_radius - tank_margin

    theta      = 0.0
    theta_last = 0.0
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
    spiral_out_count = len(spiral_out)

    # 2. 수조 테두리 한 바퀴 — 나선 끝 반경에서 순회
    r_last = k * theta_last
    r_wall_follow = max(0.5, r_last)
    wall_segs = _build_wall_follow(r_wall_follow, physics_dt, linear_speed)
    wall_follow_count = len(wall_segs)

    # 3. 중심 복귀 — 벽 순회 반경에서 출발
    return_segs = _build_return_to_center(
        theta_last, k, physics_dt, linear_speed, omega_max, r_override=r_wall_follow
    )
    return_count = len(return_segs)

    out = spiral_out + wall_segs + return_segs
    return out, spiral_out_count, wall_follow_count, return_count


def _compute_waypoints(
    segments: List[Segment], physics_dt: float
) -> List[Tuple[float, float, float]]:
    """세그먼트 → (x, y, theta) 경유점 리스트 (플래너 좌표계, 원점·0° 출발)."""
    x, y, theta = 0.0, 0.0, 0.0
    wps: List[Tuple[float, float, float]] = [(x, y, theta)]
    for seg in segments:
        for _ in range(seg.num_steps):
            theta += seg.omega * physics_dt
            x += seg.v * math.cos(theta) * physics_dt
            y += seg.v * math.sin(theta) * physics_dt
            wps.append((x, y, theta))
    return wps


class SpiralPlanner:
    """Stateful planner.

    경로 구조:
      1. spiral_out  : 중심 → 외곽 나선
      2. wall_follow : 수조 테두리 한 바퀴
      3. return      : 제자리 회전 → 직진 (중심 복귀)

    제어 API:
      - next_cmd_closed_loop(rel_x, rel_y, rel_theta) : Pure Pursuit 폐루프 (권장)
      - next_cmd()                                     : 오픈루프 (하위 호환)
    """

    PHASE_SPIRAL_OUT  = "spiral_out"
    PHASE_WALL_FOLLOW = "wall_follow"
    PHASE_RETURN      = "return"
    PHASE_DONE        = "done"

    # 하위 호환성
    PHASE_SPIRAL = PHASE_SPIRAL_OUT
    PHASE_TURN   = PHASE_WALL_FOLLOW
    PHASE_SPIRAL_RETURN = PHASE_RETURN

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
        self._build()

    def _build(self) -> None:
        p = self._params
        segs, spiral_out_count, wall_follow_count, return_count = _build_segments(
            physics_dt      = self._physics_dt,
            tank_radius     = p["tank_diameter"] * 0.5,
            tank_margin     = p["tank_margin"],
            robot_footprint = p["robot_footprint"],
            linear_speed    = p["linear_speed"],
            omega_max       = p["omega_max"],
        )
        self._segments     = segs
        self._total_steps  = sum(seg.num_steps for seg in segs)

        # 오픈루프용 페이즈 경계 (세그먼트 인덱스)
        self._spiral_out_end  = spiral_out_count - 1
        self._wall_follow_end = spiral_out_count + wall_follow_count - 1

        # 오픈루프 상태
        self._seg_idx      = 0
        self._step_in_seg  = 0
        self._current_step = 0

        # 폐루프용 경유점 및 경계 (경유점 인덱스)
        self._waypoints: List[Tuple[float, float, float]] = _compute_waypoints(
            segs, self._physics_dt
        )
        spiral_out_wp = sum(seg.num_steps for seg in segs[:spiral_out_count])
        wall_follow_wp = spiral_out_wp + sum(
            seg.num_steps for seg in segs[spiral_out_count:spiral_out_count + wall_follow_count]
        )
        self._spiral_out_wp_end  = spiral_out_wp
        self._wall_follow_wp_end = wall_follow_wp

        # 폐루프 상태
        self._wp_idx      = 0
        self._cl_done     = False

    def rebuild(
        self,
        tank_diameter:   float = None,
        tank_margin:     float = None,
        robot_footprint: float = None,
        linear_speed:    float = None,
        omega_max:       float = None,
    ) -> None:
        """파라미터 변경 후 segments·waypoints 재생성."""
        if tank_diameter   is not None: self._params["tank_diameter"]   = tank_diameter
        if tank_margin     is not None: self._params["tank_margin"]     = tank_margin
        if robot_footprint is not None: self._params["robot_footprint"] = robot_footprint
        if linear_speed    is not None: self._params["linear_speed"]    = linear_speed
        if omega_max       is not None: self._params["omega_max"]       = omega_max
        self._build()

    # ── 상태 프로퍼티 ──────────────────────────────────────────────────────────

    @property
    def is_done(self) -> bool:
        return self._cl_done or self._seg_idx >= len(self._segments)

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
        idx = self._wp_idx if self._wp_idx > 0 else self._current_step
        if idx <= self._spiral_out_wp_end:
            return self.PHASE_SPIRAL_OUT
        if idx <= self._wall_follow_wp_end:
            return self.PHASE_WALL_FOLLOW
        return self.PHASE_RETURN

    # ── 오픈루프 제어 (하위 호환) ──────────────────────────────────────────────

    def next_cmd(self) -> Tuple[float, float]:
        """Return (v m/s, omega rad/s) for the current step and advance (open-loop)."""
        if self.is_done:
            return 0.0, 0.0

        seg = self._segments[self._seg_idx]
        v, omega = seg.v, seg.omega

        self._step_in_seg  += 1
        self._current_step += 1
        if self._step_in_seg >= seg.num_steps:
            self._step_in_seg = 0
            self._seg_idx    += 1

        return v, omega

    # ── 폐루프 제어 (Pure Pursuit) ─────────────────────────────────────────────

    def next_cmd_closed_loop(
        self,
        rel_x: float,
        rel_y: float,
        rel_theta: float,
    ) -> Tuple[float, float]:
        """Pure Pursuit 기반 폐루프 제어.

        Args:
            rel_x, rel_y : 청소 시작 위치 기준 상대 좌표 (플래너 프레임, m)
            rel_theta    : 청소 시작 방향 기준 상대 헤딩 (rad)

        Returns:
            (v m/s, omega rad/s)
        """
        if self.is_done:
            return 0.0, 0.0

        wps = self._waypoints
        n   = len(wps)

        # 복귀 완료 판정: 원점 근처에 있고 return 페이즈이면 완료
        dist_to_origin = math.hypot(rel_x, rel_y)
        in_return_phase = self._wp_idx > self._wall_follow_wp_end
        if in_return_phase and dist_to_origin < _DONE_RADIUS_M:
            self._cl_done = True
            self._current_step = self._total_steps
            return 0.0, 0.0

        # 1. 가장 가까운 경유점 탐색 (현재 인덱스에서 최대 80스텝 전방)
        # 탐색 창이 너무 크면 원형 벽 순회 경로에서 반대편 점으로 점프하는 버그 발생
        search_end = min(self._wp_idx + 80, n)
        best_idx   = self._wp_idx
        best_dist  = float('inf')
        for i in range(self._wp_idx, search_end):
            d = math.hypot(wps[i][0] - rel_x, wps[i][1] - rel_y)
            if d < best_dist:
                best_dist = d
                best_idx  = i

        self._wp_idx      = best_idx
        self._current_step = best_idx

        # 2. lookahead 거리 앞의 목표점 찾기
        target_idx = n - 1
        for i in range(best_idx, n):
            if math.hypot(wps[i][0] - rel_x, wps[i][1] - rel_y) >= _LOOKAHEAD_M:
                target_idx = i
                break

        # 경로 끝 근처 → 완료 처리
        if best_idx >= n - 5:
            self._cl_done = True
            self._current_step = self._total_steps
            return 0.0, 0.0

        # 3. Pure Pursuit 조향각 계산
        tx, ty, _ = wps[target_idx]
        alpha = math.atan2(ty - rel_y, tx - rel_x) - rel_theta
        alpha = (alpha + math.pi) % (2.0 * math.pi) - math.pi

        v         = float(self._params['linear_speed'])
        omega_max = float(self._params['omega_max'])
        omega     = 2.0 * v * math.sin(alpha) / _LOOKAHEAD_M
        omega     = max(-omega_max, min(omega_max, omega))

        return v, omega

    # ── 공통 제어 ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self._seg_idx      = 0
        self._step_in_seg  = 0
        self._current_step = 0
        self._wp_idx       = 0
        self._cl_done      = False

    def pause(self) -> int:
        return self._current_step

    def resume(self) -> int:
        return self._current_step
