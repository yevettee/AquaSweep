"""흡입 시스템 — 로봇 주변 이물질 파티클에 인력(引力)을 적용해 수거를 시뮬레이션한다.

동작 원리:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  suction_radius (기본 0.35 m)                                        │
  │  ┌──────────────────────────────────────────┐                        │
  │  │  collection_radius (기본 0.12 m)          │                        │
  │  │  ┌──────────────┐                         │                        │
  │  │  │   [로봇]      │ ← 이 거리 이내: 수거   │ ← 인력 구간            │
  │  │  └──────────────┘                         │                        │
  │  └──────────────────────────────────────────┘                        │
  └─────────────────────────────────────────────────────────────────────┘

  1. 매 physics step마다 /World/Debris/UnifiedParticles 위치를 읽는다.
  2. suction_radius 이내 파티클: 로봇 방향으로 XY 위치를 직접 이동(position-based).
     - 속도 대신 위치를 직접 조작하면 GPU solver와 충돌 없이 안정적으로 동작한다.
  3. collection_radius 이내 파티클: z = -100 m 숨김 위치로 순간이동 → 수거 처리.

GPU 파티클 주의사항:
  USD attribute 쓰기는 CPU→GPU 동기화를 거치므로 1~2 프레임 지연이 있을 수 있다.
  물리적 정확도보다 시각적 설득력을 목적으로 설계되었다.
"""

import numpy as np
from pxr import Gf, UsdGeom, Vt

PARTICLES_PRIM_PATH = "/World/Debris/UnifiedParticles"
_HIDDEN_Z = -100.0   # 수거된 파티클을 시뮬레이션 영역 밖으로 숨기는 Z 좌표


class SuctionSystem:
    """로봇 흡입구 근처 파티클에 인력을 적용하고 접촉 시 수거하는 시스템."""

    def __init__(
        self,
        suction_radius: float = 0.35,
        collection_radius: float = 0.12,
        strength: float = 0.04,
    ):
        """
        Args:
            suction_radius    : 흡입력이 미치는 최대 반경 (m)
            collection_radius : 이 거리 이내에 들어온 파티클은 즉시 수거 (m)
            strength          : 1 physics step당 파티클이 이동하는 최대 거리 (m/step).
                                너무 크면 파티클이 튀고, 너무 작으면 흡입이 느림.
        """
        self.suction_radius    = suction_radius
        self.collection_radius = collection_radius
        self.strength          = strength
        self._collected        = 0

    # ------------------------------------------------------------------
    def step(self, stage, robot_pos: np.ndarray, dt: float) -> int:
        """매 physics step 호출.

        Args:
            stage     : 현재 USD Stage
            robot_pos : 로봇 월드 위치 [x, y, z] (numpy 1-D array)
            dt        : physics step 크기 (초, 현재 미사용 — 위치 기반이므로)

        Returns:
            이번 스텝에서 새로 수거된 파티클 수
        """
        pts = UsdGeom.Points.Get(stage, PARTICLES_PRIM_PATH)
        if not pts:
            return 0

        pos_attr  = pts.GetPointsAttr()
        positions = pos_attr.Get()
        if positions is None or len(positions) == 0:
            return 0

        rxy            = robot_pos[:2].astype(float)
        new_pos        = list(positions)
        newly_collected = 0
        changed        = False

        for i, pos in enumerate(positions):
            # 이미 수거된 파티클(숨김 위치) 건너뜀
            if pos[2] < _HIDDEN_Z * 0.5:
                continue

            p_xy  = np.array([pos[0], pos[1]], dtype=float)
            diff  = rxy - p_xy
            dist  = float(np.linalg.norm(diff))

            if dist < self.collection_radius:
                # ── 수거: 시뮬레이션 영역 밖으로 이동 ──────────────────
                new_pos[i] = Gf.Vec3f(0.0, 0.0, _HIDDEN_Z)
                newly_collected += 1
                changed = True

            elif dist < self.suction_radius:
                # ── 인력: 로봇 방향으로 위치를 직접 이동 ────────────────
                # 가까울수록 강하게 (선형 감쇠)
                factor    = 1.0 - dist / self.suction_radius
                direction = diff / (dist + 1e-9)
                move      = direction * (self.strength * factor)

                new_pos[i] = Gf.Vec3f(
                    pos[0] + float(move[0]),
                    pos[1] + float(move[1]),
                    pos[2],                  # Z는 중력/충돌에 맡김
                )
                changed = True

        if changed:
            pos_attr.Set(Vt.Vec3fArray(new_pos))

        self._collected += newly_collected
        return newly_collected

    # ------------------------------------------------------------------
    @property
    def collected_count(self) -> int:
        """지금까지 수거된 파티클 누적 수."""
        return self._collected

    def reset(self) -> None:
        """수거 카운터 초기화 (RESET 버튼 시 호출)."""
        self._collected = 0
