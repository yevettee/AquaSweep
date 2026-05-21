"""Animate the per-pool water-surface meshes by displacing their vertices.

Wave field: sum of several plane waves in WORLD coordinates, so neighbouring
pools share a visually consistent ripple pattern.

    dz(x_world, y_world, t) = sum_i( A_i * sin(kx_i*x + ky_i*y - omega_i*t + phi_i) )

Surfaces are discovered each step under params/POOLS_ROOT/Pool_*/WaterSurface,
so adding/removing pools at runtime works without code changes.
"""

import math

from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf, UsdGeom, Vt

from .scene_builders import POOLS_ROOT

# Wave components: (amplitude m, kx rad/m, ky rad/m, omega rad/s, phase rad)
_WAVES = [
    ( 0.006,  0.70,  0.35,  0.50,  0.00),
    ( 0.005, -0.50,  0.80,  0.60,  1.20),
    ( 0.004,  0.30, -0.90,  0.40,  2.40),
    ( 0.003, -0.80, -0.30,  0.70,  0.70),
    ( 0.002,  0.90,  0.60,  0.35,  1.90),
    ( 0.002, -0.20,  0.70,  0.80,  3.10),
]


class _SurfaceCache:
    """Per-surface cached state (base local points + world centre offset)."""

    __slots__ = ("mesh", "base_points", "offset_x", "offset_y")

    def __init__(self, mesh: UsdGeom.Mesh, base_points: list[tuple[float, float, float]],
                 offset_x: float, offset_y: float) -> None:
        self.mesh = mesh
        self.base_points = base_points
        self.offset_x = offset_x
        self.offset_y = offset_y


class WaterSurfaceAnimator:
    def __init__(self):
        self._t = 0.0
        self._surfaces: list[_SurfaceCache] | None = None

    def reset(self) -> None:
        self._t = 0.0
        self._surfaces = None

    def step(self, dt: float) -> None:
        self._t += dt
        t = self._t

        stage = get_current_stage()
        if not stage:
            return

        # Invalidate cache if a prim has been replaced (stage reload, etc).
        if self._surfaces and not self._surfaces[0].mesh.GetPrim().IsValid():
            self._surfaces = None

        if self._surfaces is None:
            self._surfaces = self._discover_surfaces(stage)
            if not self._surfaces:
                return

        for surf in self._surfaces:
            new_pts = []
            ox, oy = surf.offset_x, surf.offset_y
            for x, y, z0 in surf.base_points:
                wx, wy = x + ox, y + oy
                dz = 0.0
                for A, kx, ky, omega, phi in _WAVES:
                    dz += A * math.sin(kx * wx + ky * wy - omega * t + phi)
                new_pts.append(Gf.Vec3f(x, y, z0 + dz))
            surf.mesh.GetPointsAttr().Set(Vt.Vec3fArray(new_pts))

    # ── private ──────────────────────────────────────────────────────────────
    @staticmethod
    def _discover_surfaces(stage) -> list[_SurfaceCache]:
        pools_prim = stage.GetPrimAtPath(POOLS_ROOT)
        if not pools_prim or not pools_prim.IsValid():
            return []

        results: list[_SurfaceCache] = []
        # Sort by prim path for deterministic order across sublayer composition.
        children = sorted(pools_prim.GetChildren(), key=lambda p: str(p.GetPath()))
        for pool_prim in children:
            surface_path = pool_prim.GetPath().AppendChild("WaterSurface")
            mesh = UsdGeom.Mesh.Get(stage, surface_path)
            if not mesh:
                continue

            raw_pts = mesh.GetPointsAttr().Get()
            if not raw_pts:
                continue
            base_points = [(float(p[0]), float(p[1]), float(p[2])) for p in raw_pts]

            ox, oy = WaterSurfaceAnimator._read_translate_xy(pool_prim)
            results.append(_SurfaceCache(mesh, base_points, ox, oy))

        return results

    @staticmethod
    def _read_translate_xy(prim) -> tuple[float, float]:
        """Read the pool xform's translate so wave eq uses world coords."""
        xformable = UsdGeom.Xformable(prim)
        for op in xformable.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                v = op.Get()
                if v is not None:
                    return float(v[0]), float(v[1])
        return 0.0, 0.0
