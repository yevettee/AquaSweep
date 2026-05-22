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

# ── Motion bounds for ALIVE sturgeons ─────────────────────────────────────────
_Z_MIN_ALIVE = 0.30
_Z_MAX_ALIVE = 0.80                  # stay deeper in the water
_Z_MID_ALIVE = (_Z_MIN_ALIVE + _Z_MAX_ALIVE) / 2.0
_Z_AMP_ALIVE = (_Z_MAX_ALIVE - _Z_MIN_ALIVE) / 2.0

_OMEGA_MIN_ALIVE = 0.16              # rad/s ≈ 9.2 °/s (2x faster)
_OMEGA_MAX_ALIVE = 0.44              # rad/s ≈ 25 °/s (2x faster)

# Body roll for alive fish (side-to-side swimming motion)
_ROLL_AMP_DEG = 35.0                 # ±35 degrees (exaggerated swim)
_ROLL_FREQ_MIN = 3                 # faster roll for swimming feel
_ROLL_FREQ_MAX = 5

# ── Motion bounds for FLIPPED (dead/sick) sturgeons ───────────────────────────
_Z_MIN_FLIPPED = params.WATER_LEVEL - 0.15   # 1.05 m (near surface)
_Z_MAX_FLIPPED = params.WATER_LEVEL - 0.05   # 1.15 m (nearly at surface)
_Z_MID_FLIPPED = (_Z_MIN_FLIPPED + _Z_MAX_FLIPPED) / 2.0
_Z_AMP_FLIPPED = 0.03                # minimal bobbing

_OMEGA_MIN_FLIPPED = 0.05           # very slow drift
_OMEGA_MAX_FLIPPED = 0.1

# ── Shared radius bounds ──────────────────────────────────────────────────────
_RADIUS_MIN = 0.6
_RADIUS_MAX = 3.0
_RADIUS_AMP = 0.25


class _SturgeonCache:
    __slots__ = ("translate_op", "rotate_op", "roll_op", "prim", "params", "is_flipped")

    def __init__(
        self,
        translate_op,
        rotate_op,
        roll_op,
        prim,
        motion_params: dict,
        is_flipped: bool,
    ):
        self.translate_op = translate_op
        self.rotate_op = rotate_op
        self.roll_op = roll_op
        self.prim = prim
        self.params = motion_params
        self.is_flipped = is_flipped


def _params_from_path(prim_path_str: str, is_flipped: bool) -> dict:
    """Deterministic per-fish motion params keyed off the prim path.

    MD5 is used (not Python's ``hash``) because the built-in hash is salted
    per process and would give different results across Isaac Sim launches.

    Parameters differ for flipped (dead/sick) vs alive fish.
    """
    digest = hashlib.md5(prim_path_str.encode("utf-8")).digest()

    def uniform(start: int, end: int, low: float, high: float) -> float:
        chunk = int.from_bytes(digest[start:end], "little")
        max_val = (1 << ((end - start) * 8)) - 1
        u = chunk / max_val if max_val else 0.0
        return low + u * (high - low)

    direction = 1.0 if (digest[0] & 0x01) else -1.0

    if is_flipped:
        omega_min, omega_max = _OMEGA_MIN_FLIPPED, _OMEGA_MAX_FLIPPED
        z_mid, z_amp = _Z_MID_FLIPPED, _Z_AMP_FLIPPED
    else:
        omega_min, omega_max = _OMEGA_MIN_ALIVE, _OMEGA_MAX_ALIVE
        z_mid, z_amp = _Z_MID_ALIVE, _Z_AMP_ALIVE

    return {
        "angle0":      uniform(1, 3, 0.0, 2.0 * math.pi),
        "omega":       direction * uniform(3, 5, omega_min, omega_max),
        "radius_base": uniform(5, 7, _RADIUS_MIN, _RADIUS_MAX),
        "radius_amp":  uniform(7, 8, 0.0, _RADIUS_AMP),
        "r_freq":      uniform(8, 10, 0.15, 0.45),
        "r_phase":     uniform(10, 12, 0.0, 2.0 * math.pi),
        "z_freq":      uniform(12, 14, 0.08, 0.25),
        "z_phase":     uniform(14, 16, 0.0, 2.0 * math.pi),
        "z_mid":       z_mid,
        "z_amp":       z_amp,
        "roll_freq":   uniform(0, 2, _ROLL_FREQ_MIN, _ROLL_FREQ_MAX),
        "roll_phase":  uniform(2, 4, 0.0, 2.0 * math.pi),
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
            z = p["z_mid"] + p["z_amp"] * math.sin(t * p["z_freq"] + p["z_phase"])

            # Yaw aligned with the orbit tangent — sign comes from omega so
            # CCW and CW swimmers both face forward.
            yaw_rad = angle + math.copysign(math.pi / 2.0, p["omega"])
            yaw_deg = math.degrees(yaw_rad) % 360.0

            s.translate_op.Set(Gf.Vec3d(x, y, z))
            s.rotate_op.Set(yaw_deg)

            # Body roll for alive fish only (side-to-side swimming motion)
            if s.roll_op is not None and not s.is_flipped:
                roll_deg = _ROLL_AMP_DEG * math.sin(t * p["roll_freq"] + p["roll_phase"])
                s.roll_op.Set(roll_deg)

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
        yaw_op = None
        roll_op = None
        for op in xform.GetOrderedXformOps():
            op_type = op.GetOpType()
            op_name = op.GetName()
            if op_type == UsdGeom.XformOp.TypeTranslate and translate_op is None:
                translate_op = op
            elif op_type == UsdGeom.XformOp.TypeRotateZ:
                # Distinguish yaw vs roll by opSuffix in the name
                if "yaw" in op_name and yaw_op is None:
                    yaw_op = op
                elif "roll" in op_name and roll_op is None:
                    roll_op = op
                elif yaw_op is None:
                    # Fallback for legacy prims without suffix
                    yaw_op = op
        if translate_op is None or yaw_op is None:
            return None

        is_flipped = False
        flipped_attr = prim.GetAttribute("aquasweep:isFlipped")
        if flipped_attr and flipped_attr.IsValid():
            is_flipped = bool(flipped_attr.Get())

        return _SturgeonCache(
            translate_op=translate_op,
            rotate_op=yaw_op,
            roll_op=roll_op,
            prim=prim,
            motion_params=_params_from_path(str(prim.GetPath()), is_flipped),
            is_flipped=is_flipped,
        )
