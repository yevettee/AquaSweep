"""흡입 시스템 — 로봇 주변 이물질 파티클에 인력(引力)을 적용해 수거를 시뮬레이션한다.

동작 원리:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  suction_radius (기본 0.5 m)                                         │
  │  ┌──────────────────────────────────────────┐                        │
  │  │  collection_radius (기본 0.15 m)          │                        │
  │  │  ┌──────────────┐                         │                        │
  │  │  │   [로봇]      │ ← 이 거리 이내: 수거   │ ← 속도 인력 구간       │
  │  │  └──────────────┘                         │                        │
  │  └──────────────────────────────────────────┘                        │
  └─────────────────────────────────────────────────────────────────────┘

GPU 파티클 위치 직접 쓰기의 한계:
  PhysX GPU solver는 매 스텝마다 자체 계산으로 파티클 위치를 덮어씁니다.
  pos_attr.Set()으로 CPU에서 쓴 값은 GPU solver가 다음 프레임에서 무시합니다.
  따라서 인력 구현은 velocities 속성을 사용합니다.
  GPU solver는 velocities를 읽어 위치에 적분하므로 매 스텝마다 속도를 덮어쓰면
  solver와 협력하는 방향으로 작동합니다.

  수거(collection): z = -100 m 텔레포트 (위치 쓰기) + 속도 0 초기화.
                    z=-100 아래에는 충돌체가 없으므로 GPU solver가 덮어써도 계속 낙하/유지됨.
  인력(attraction): 매 스텝 velocities를 로봇 방향으로 덮어씀 → solver가 적분해 파티클 이동.
"""

import math

import carb
import numpy as np
from pxr import Gf, UsdGeom, Vt

# Default particle path — back-compat for single-tank workflow. The per-pool
# refactor (debris_system → /World/Pools/Pool_<n>/Debris/Particles) means
# aquasweep_ext should construct SuctionSystem with an explicit path matching
# the primary robot's pool.
DEFAULT_PARTICLES_PRIM_PATH = "/World/Pools/Pool_1/Debris/Particles"
_HIDDEN_Z = -100.0


def _forward_xy(quat_wxyz: np.ndarray) -> np.ndarray:
    """쿼터니언 [w,x,y,z]에서 로봇 +X 방향의 XY 단위벡터를 반환."""
    w, x, y, z = quat_wxyz
    fx = 1.0 - 2.0 * (y * y + z * z)
    fy = 2.0 * (x * y + w * z)
    norm = math.sqrt(fx * fx + fy * fy)
    if norm < 1e-9:
        return np.array([1.0, 0.0])
    return np.array([fx / norm, fy / norm])


class SuctionSystem:
    """로봇 흡입구 근처 파티클에 속도 인력을 적용하고 접촉 시 수거하는 시스템."""

    def __init__(
        self,
        suction_radius: float = 0.8,
        collection_radius: float = 0.30,
        attraction_speed: float = 8.0,
        nozzle_offset: float = 0.35,
        particles_prim_path: str = DEFAULT_PARTICLES_PRIM_PATH,
    ):
        """
        Args:
            suction_radius    : 흡입력이 미치는 최대 반경 (m)
            collection_radius : 이 거리 이내 파티클은 즉시 수거 (m)
            attraction_speed  : 흡입 반경 경계에서의 속도 크기 (m/s)
            nozzle_offset     : 로봇 중심에서 앞쪽 흡입구까지 오프셋 (m)
            particles_prim_path : 흡입 대상 파티클 Points prim 경로
                                  (per-pool refactor 이후 Pool 별로 별도 경로)
        """
        self.suction_radius    = suction_radius
        self.collection_radius = collection_radius
        self.attraction_speed  = attraction_speed
        self.nozzle_offset     = nozzle_offset
        self.particles_prim_path = particles_prim_path
        self._collected        = 0
        self._step_count       = 0

    # ------------------------------------------------------------------
    def step(self, stage, robot_pos: np.ndarray, robot_orient: np.ndarray, dt: float) -> int:
        """매 physics step 호출.

        Args:
            stage        : 현재 USD Stage
            robot_pos    : 로봇 월드 위치 [x, y, z]
            robot_orient : 로봇 쿼터니언 [w, x, y, z]
            dt           : physics step 크기 (초)

        Returns:
            이번 스텝에서 새로 수거된 파티클 수
        """
        self._step_count += 1

        pts = UsdGeom.Points.Get(stage, self.particles_prim_path)
        if not pts:
            if self._step_count <= 5:
                carb.log_warn(f"[suction] 파티클 prim 없음: {self.particles_prim_path}")
            return 0

        pos_attr = pts.GetPointsAttr()
        vel_attr = pts.GetVelocitiesAttr()

        positions = pos_attr.Get()
        if positions is None or len(positions) == 0:
            return 0

        count = len(positions)
        velocities = vel_attr.Get()
        if velocities is None or len(velocities) != count:
            velocities = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)] * count)

        # 흡입구 위치: 로봇 중심에서 앞쪽(+X)으로 nozzle_offset만큼 이동
        fwd = _forward_xy(robot_orient)
        nozzle_xy = robot_pos[:2].astype(float) + fwd * self.nozzle_offset

        new_pos        = list(positions)
        new_vel        = list(velocities)
        newly_collected = 0
        pos_changed    = False
        vel_changed    = False

        for i, pos in enumerate(positions):
            # 이미 수거된 파티클(숨김 위치) 건너뜀
            if pos[2] < _HIDDEN_Z * 0.5:
                continue

            p_xy  = np.array([pos[0], pos[1]], dtype=float)
            diff  = nozzle_xy - p_xy
            dist  = float(np.linalg.norm(diff))

            if dist < self.collection_radius:
                # ── 수거: z=-100 텔레포트 + 속도 제로 ──────────────────
                new_pos[i] = Gf.Vec3f(0.0, 0.0, _HIDDEN_Z)
                new_vel[i] = Gf.Vec3f(0.0, 0.0, 0.0)
                newly_collected += 1
                pos_changed = True
                vel_changed = True

            elif dist < self.suction_radius:
                # ── 인력: 매 스텝 velocities를 로봇 방향으로 덮어씀 ─────
                # GPU solver가 이 속도를 적분 → 파티클이 로봇 쪽으로 이동
                # 가까울수록 강하게 (선형: 경계=0, 중심=attraction_speed)
                factor    = 1.0 - dist / self.suction_radius
                direction = diff / (dist + 1e-9)
                speed     = self.attraction_speed * factor

                cur_v = new_vel[i]
                new_vel[i] = Gf.Vec3f(
                    float(direction[0] * speed),
                    float(direction[1] * speed),
                    float(cur_v[2]),   # Z 속도는 중력/충돌에 맡김
                )
                vel_changed = True

        if pos_changed:
            pos_attr.Set(Vt.Vec3fArray(new_pos))
        if vel_changed:
            vel_attr.Set(Vt.Vec3fArray(new_vel))

        self._collected += newly_collected

        # 최초 10 스텝만 로그 (동작 확인용)
        if self._step_count <= 10:
            carb.log_info(
                f"[suction] step={self._step_count} nozzle_xy={nozzle_xy} "
                f"particles={count} vel_changed={vel_changed} collected={newly_collected}"
            )

        return newly_collected

    # ------------------------------------------------------------------
    @property
    def collected_count(self) -> int:
        return self._collected

    def reset(self) -> None:
        self._collected  = 0
        self._step_count = 0
