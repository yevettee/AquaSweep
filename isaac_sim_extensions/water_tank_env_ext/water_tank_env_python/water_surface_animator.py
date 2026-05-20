"""수면 디스크 메시 꼭짓점을 매 step 변위시켜 출렁거림을 시각화한다.

서로 다른 방향·속도의 평면파 여러 개를 중첩해
불규칙하고 자연스러운 수면 출렁거림을 만든다.

    dz = sum_i( A_i * sin(kx_i*x + ky_i*y - omega_i*t + phi_i) )
"""

import math

from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf, UsdGeom, Vt

WATER_SURFACE_PATH = "/World/Water/Surface"

# 파동 컴포넌트: (진폭 m, kx rad/m, ky rad/m, 각주파수 rad/s, 초기위상 rad)
_WAVES = [
    ( 0.006,  0.70,  0.35,  0.50,  0.00),
    ( 0.005, -0.50,  0.80,  0.60,  1.20),
    ( 0.004,  0.30, -0.90,  0.40,  2.40),
    ( 0.003, -0.80, -0.30,  0.70,  0.70),
    ( 0.002,  0.90,  0.60,  0.35,  1.90),
    ( 0.002, -0.20,  0.70,  0.80,  3.10),
]


class WaterSurfaceAnimator:
    def __init__(self):
        self._t = 0.0
        self._base_points: list | None = None

    def reset(self) -> None:
        self._t = 0.0
        self._base_points = None

    def step(self, dt: float) -> None:
        self._t += dt
        t = self._t

        stage = get_current_stage()
        if not stage:
            return

        mesh = UsdGeom.Mesh.Get(stage, WATER_SURFACE_PATH)
        if not mesh:
            return

        pts_attr = mesh.GetPointsAttr()

        if self._base_points is None:
            raw = pts_attr.Get()
            if not raw:
                return
            self._base_points = [(float(p[0]), float(p[1]), float(p[2])) for p in raw]

        new_pts = []
        for x, y, z0 in self._base_points:
            dz = 0.0
            for A, kx, ky, omega, phi in _WAVES:
                dz += A * math.sin(kx * x + ky * y - omega * t + phi)
            new_pts.append(Gf.Vec3f(x, y, z0 + dz))

        pts_attr.Set(Vt.Vec3fArray(new_pts))
