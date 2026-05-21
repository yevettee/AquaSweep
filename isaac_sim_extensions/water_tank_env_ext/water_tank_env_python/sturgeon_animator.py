"""Per-step animation for every sturgeon reference under /World/Pools.

Each sturgeon is parented under its Pool_<n> Xform, so we drive local-coord
xform ops:

  translate: (x, y, z) — orbiting motion around the pool centre with a slow
             radial wobble. z oscillates in [Z_MIN, Z_MAX].
  rotateZ:   yaw aligned with the swimming tangent so the fish appears to
             face forward.

The scale op set by ``sturgeon_spawner`` is untouched.

Per-fish motion parameters are derived from an MD5 hash of the prim path so
every sturgeon swims differently *and* the pattern is stable across reloads
of the same stage (Python's built-in ``hash()`` is randomised per process).
"""

import hashlib
import math

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf, UsdGeom

from . import params
from .scene_builders import POOLS_ROOT

# ── Motion bounds ────────────────────────────────────────────────────────────
_Z_MIN = 0.30
_Z_MAX = params.WATER_LEVEL          # 1.20 m
_Z_MID = (_Z_MIN + _Z_MAX) / 2.0     # 0.75
_Z_AMP = (_Z_MAX - _Z_MIN) / 2.0     # 0.45 → sin oscillates exactly [0.30, 1.20]

# Per-fish radius is sampled inside [_RADIUS_MIN, _RADIUS_MAX] then breathes by
# ±_RADIUS_AMP. Pool radius is 4 m, fish length ≈ 0.9 m, so we stay clear of
# the wall.
_RADIUS_MIN = 0.6
_RADIUS_MAX = 3.0
_RADIUS_AMP = 0.25

# Slow swim speed envelope. Both signs are used (some CCW, some CW).
_OMEGA_MIN = 0.08      # rad/s ≈ 4.6 °/s
_OMEGA_MAX = 0.22      # rad/s ≈ 12.6 °/s


class _SturgeonCache:
    __slots__ = ("translate_op", "rotate_op", "prim", "params")

    def __init__(self, translate_op, rotate_op, prim, motion_params: dict):
        self.translate_op = translate_op
        self.rotate_op = rotate_op
        self.prim = prim
        self.params = motion_params


def _params_from_path(prim_path_str: str) -> dict:
    """Deterministic per-fish motion params keyed off the prim path.

    MD5 is used (not Python's ``hash``) because the built-in hash is salted
    per process and would give different results across Isaac Sim launches.
    """
    digest = hashlib.md5(prim_path_str.encode("utf-8")).digest()

    def uniform(start: int, end: int, low: float, high: float) -> float:
        chunk = int.from_bytes(digest[start:end], "little")
        max_val = (1 << ((end - start) * 8)) - 1
        u = chunk / max_val if max_val else 0.0
        return low + u * (high - low)

    direction = 1.0 if (digest[0] & 0x01) else -1.0
    return {
        "angle0":      uniform(1, 3, 0.0, 2.0 * math.pi),
        "omega":       direction * uniform(3, 5, _OMEGA_MIN, _OMEGA_MAX),
        "radius_base": uniform(5, 7, _RADIUS_MIN, _RADIUS_MAX),
        "radius_amp":  uniform(7, 8, 0.0, _RADIUS_AMP),
        "r_freq":      uniform(8, 10, 0.15, 0.45),
        "r_phase":     uniform(10, 12, 0.0, 2.0 * math.pi),
        "z_freq":      uniform(12, 14, 0.08, 0.25),
        "z_phase":     uniform(14, 16, 0.0, 2.0 * math.pi),
    }


class SturgeonAnimator:
    def __init__(self):
        self._t = 0.0
        self._sturgeons: list[_SturgeonCache] | None = None

    def reset(self) -> None:
        self._t = 0.0
        self._sturgeons = None

    def step(self, dt: float) -> None:
        self._t += dt
        stage = get_current_stage()
        if not stage:
            return

        # Invalidate cache if a prim has been replaced (stage reload).
        if self._sturgeons and not self._sturgeons[0].prim.IsValid():
            self._sturgeons = None

        if self._sturgeons is None:
            self._sturgeons = self._discover(stage)
            carb.log_info(
                f"[sturgeon_animator] discovered {len(self._sturgeons)} sturgeon(s)"
            )
            if not self._sturgeons:
                return

        t = self._t
        for s in self._sturgeons:
            p = s.params
            angle = p["angle0"] + p["omega"] * t
            radius = p["radius_base"] + p["radius_amp"] * math.sin(
                t * p["r_freq"] + p["r_phase"]
            )
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            z = _Z_MID + _Z_AMP * math.sin(t * p["z_freq"] + p["z_phase"])

            # Yaw aligned with the orbit tangent — sign comes from omega so
            # CCW and CW swimmers both face forward.
            yaw_rad = angle + math.copysign(math.pi / 2.0, p["omega"])
            yaw_deg = math.degrees(yaw_rad) % 360.0

            s.translate_op.Set(Gf.Vec3d(x, y, z))
            s.rotate_op.Set(yaw_deg)

    # ── private ──────────────────────────────────────────────────────────────
    @staticmethod
    def _discover(stage) -> list[_SturgeonCache]:
        pools_prim = stage.GetPrimAtPath(POOLS_ROOT)
        if not pools_prim or not pools_prim.IsValid():
            return []

        results: list[_SturgeonCache] = []
        # Sort by prim path for deterministic order.
        pool_children = sorted(pools_prim.GetChildren(), key=lambda p: str(p.GetPath()))
        for pool_prim in pool_children:
            # Every child of a pool whose name starts with "Sturgeon" is a
            # spawned fish (e.g. Sturgeon_01, Sturgeon_02, ...).
            for child in pool_prim.GetChildren():
                if not child.GetName().startswith("Sturgeon"):
                    continue
                cache = SturgeonAnimator._cache_for_prim(child)
                if cache is not None:
                    results.append(cache)
        return results

    @staticmethod
    def _cache_for_prim(prim) -> _SturgeonCache | None:
        xform = UsdGeom.Xformable(prim)
        translate_op = None
        rotate_op = None
        for op in xform.GetOrderedXformOps():
            op_type = op.GetOpType()
            if op_type == UsdGeom.XformOp.TypeTranslate and translate_op is None:
                translate_op = op
            elif op_type == UsdGeom.XformOp.TypeRotateZ and rotate_op is None:
                rotate_op = op
        if translate_op is None or rotate_op is None:
            return None
        return _SturgeonCache(
            translate_op=translate_op,
            rotate_op=rotate_op,
            prim=prim,
            motion_params=_params_from_path(str(prim.GetPath())),
        )
