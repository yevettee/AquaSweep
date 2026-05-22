"""Spawn 5–10 sturgeons into a random subset of pools.

Layout rules (drawn fresh from ``random.Random()`` each call):
  * 1 to 3 pools are left empty (water + robot only).
  * The remaining pools each get 5 to 10 sturgeons.
  * Each sturgeon's start pose (radius, angle, yaw, z) is randomised inside
    the pool.
  * Each sturgeon picks a random shade from a dark-grey palette so the school
    isn't uniformly coloured.
  * Some sturgeons are spawned "flipped" (belly-up) near the water surface,
    simulating dead/sick fish floating.

Prim layout:
    /World/Pools/Pool_<n>/Sturgeon_<m>   (m = 1..N for that pool)

Scale: one bbox measurement on the first spawned reference is reused for the
entire school (same USD ⇒ same natural length).
"""

import math
import os
import random
from typing import Optional

import carb
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

from . import params
from .scene_builders import POOLS_ROOT

# Path is resolved relative to this file:
#   <repo>/isaac_sim_extensions/water_tank_env_ext/water_tank_env_python/
#   <repo>/assets/shark/sturgeon_final.usdc
_HERE = os.path.dirname(os.path.realpath(__file__))
_STURGEON_USD = os.path.normpath(
    os.path.join(_HERE, "..", "..", "..", "assets", "shark", "sturgeon_final.usdc")
)

# ── Spawn-time tunables ──────────────────────────────────────────────────────
TARGET_LENGTH_M = 1.0                # 1 m sturgeon (was 0.90)

_EMPTY_POOLS_MIN = 1
_EMPTY_POOLS_MAX = 3
_FISH_PER_POOL_MIN = 5
_FISH_PER_POOL_MAX = 10

# Initial XY pose around pool centre — kept inside the inner radius with margin.
_RADIUS_MIN = 0.6
_RADIUS_MAX = params.TANK_RADIUS - 1.0  # ≈ 3.0 m, well clear of the wall

# Z spawn range — full water column from 0.30 m up to water surface.
_SPAWN_Z_MIN = 0.30
_SPAWN_Z_MAX = params.WATER_LEVEL - 0.1   # 1.10 m

# ── Flipped (belly-up) sturgeon settings ──────────────────────────────────────
_FLIP_PROBABILITY = 0.5             # 25% chance each fish is flipped
_FLIPPED_Z_MIN = params.WATER_LEVEL - 0.07  # slightly below surface
_FLIPPED_Z_MAX = params.WATER_LEVEL - 0.05  # nearly at surface (floating)
_FLIP_ROLL_DEG = 180.0               # X-axis rotation to show belly
_FLIP_Z_OFFSET = 0.13                # compensate for pivot offset when flipped

# ── Colour palette (dark → near-current) ─────────────────────────────────────
_COLOR_DARK    = (0.02, 0.02, 0.03)  # near-black
_COLOR_LIGHT   = (0.08, 0.08, 0.10)  # previous single-colour value
_PALETTE_SIZE  = 8
_STURGEON_ROUGHNESS = 0.55


def _resolve_asset_url() -> Optional[str]:
    if os.path.isfile(_STURGEON_USD):
        return _STURGEON_USD
    return None


def _pool_paths(stage) -> list[str]:
    pools_prim = stage.GetPrimAtPath(POOLS_ROOT)
    if not pools_prim or not pools_prim.IsValid():
        return []
    return sorted(str(p.GetPath()) for p in pools_prim.GetChildren())


_LIGHT_TYPES = (
    UsdLux.DistantLight, UsdLux.RectLight, UsdLux.SphereLight,
    UsdLux.DiskLight, UsdLux.CylinderLight, UsdLux.DomeLight,
)

_PROXY_NAME_HINTS = ("bound", "cube", "box", "proxy", "bbox", "aabb")
_PROXY_MAX_VERTS = 30


def _is_proxy_box_mesh(prim) -> bool:
    """Heuristically identify Mesh prims that are bounding/preview boxes."""
    if not prim.IsA(UsdGeom.Mesh):
        return False
    name_lower = prim.GetName().lower()
    if any(hint in name_lower for hint in _PROXY_NAME_HINTS):
        return True
    points = UsdGeom.Mesh(prim).GetPointsAttr().Get()
    return points is not None and len(points) <= _PROXY_MAX_VERTS


def _disable_proxy_prims(stage, prim_path: str) -> dict:
    """Deactivate proxy/preview prims bundled inside a sturgeon reference.

    Handles bounding cubes, embedded cameras, and preview lights so they don't
    pollute the bbox calculation or leak into the scene.
    """
    counts = {"cubes": 0, "cameras": 0, "lights": 0}
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return counts
    for prim in Usd.PrimRange(root):
        if not prim.IsActive():
            continue
        if prim.IsA(UsdGeom.Cube) or _is_proxy_box_mesh(prim):
            prim.SetActive(False)
            counts["cubes"] += 1
        elif prim.IsA(UsdGeom.Camera) or prim.GetName().lower() == "camera":
            prim.SetActive(False)
            counts["cameras"] += 1
        elif any(prim.IsA(t) for t in _LIGHT_TYPES):
            prim.SetActive(False)
            counts["lights"] += 1
    return counts


def _natural_length(stage, prim_path: str) -> float:
    """Longest axis of the union of active mesh-only bboxes (metres).

    Computed BEFORE we add a ScaleOp so the result reflects the asset's own
    geometry. Inactive prims (bounding cube, camera mesh) are excluded.
    """
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return 0.0
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        includedPurposes=[UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
    )
    union = Gf.Range3d()
    for prim in Usd.PrimRange(root):
        if not prim.IsActive() or not prim.IsA(UsdGeom.Mesh):
            continue
        rng = cache.ComputeUntransformedBound(prim).GetRange()
        if not rng.IsEmpty():
            union.UnionWith(rng)
    if union.IsEmpty():
        return 0.0
    size = union.GetSize()
    return max(float(size[0]), float(size[1]), float(size[2]))


def _ensure_palette(stage) -> list[str]:
    """Build (once) a palette of dark-grey UsdPreviewSurface materials.

    Each palette entry is a slightly different shade between ``_COLOR_DARK``
    and ``_COLOR_LIGHT``. Returns the material prim paths.
    """
    paths = [f"/World/Looks/SturgeonGrey_{i}" for i in range(_PALETTE_SIZE)]
    if not stage.GetPrimAtPath("/World/Looks").IsValid():
        UsdGeom.Scope.Define(stage, "/World/Looks")
    for i, mat_path in enumerate(paths):
        if stage.GetPrimAtPath(mat_path).IsValid():
            continue
        t = i / max(_PALETTE_SIZE - 1, 1)
        color = tuple(
            _COLOR_DARK[c] + t * (_COLOR_LIGHT[c] - _COLOR_DARK[c]) for c in range(3)
        )
        material = UsdShade.Material.Define(stage, mat_path)
        shader = UsdShade.Shader.Define(stage, mat_path + "/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(*color)
        )
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(_STURGEON_ROUGHNESS)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        material.CreateSurfaceOutput().ConnectToSource(
            shader.ConnectableAPI(), "surface"
        )
    return paths


def _bind_random_palette_material(stage, prim, palette_paths: list[str], rng: random.Random) -> None:
    """Bind one of the palette materials at random to the sturgeon root prim."""
    mat_path = rng.choice(palette_paths)
    binding_api = UsdShade.MaterialBindingAPI.Apply(prim)
    binding_api.Bind(
        UsdShade.Material.Get(stage, mat_path),
        bindingStrength=UsdShade.Tokens.strongerThanDescendants,
    )


def spawn_sturgeons(stage, target_length_m: float = TARGET_LENGTH_M) -> int:
    """Place 5–10 sturgeons into a random subset of pools (1–3 left empty).

    Returns the total number of sturgeons placed. Each sturgeon gets a unique
    name ``Sturgeon_<m>`` under its pool.
    """
    asset_url = _resolve_asset_url()
    if asset_url is None:
        carb.log_warn(
            f"[sturgeon_spawner] sturgeon USD not found at {_STURGEON_USD}; "
            "skipping spawn"
        )
        return 0

    pool_paths = _pool_paths(stage)
    if not pool_paths:
        return 0

    rng = random.Random()           # fresh entropy each call → different layout per LOAD
    palette = _ensure_palette(stage)

    # Decide which pools are empty (robot only). Always leave at least one
    # pool occupied even if there are fewer pools than the default range.
    n_pools = len(pool_paths)
    n_empty = min(rng.randint(_EMPTY_POOLS_MIN, _EMPTY_POOLS_MAX), n_pools - 1)
    empty_indices = set(rng.sample(range(n_pools), n_empty))
    occupied = [i for i in range(n_pools) if i not in empty_indices]
    carb.log_info(
        f"[sturgeon_spawner] {n_pools} pools total, "
        f"{len(empty_indices)} left empty: {sorted(i + 1 for i in empty_indices)}; "
        f"{len(occupied)} occupied: {sorted(i + 1 for i in occupied)}"
    )

    scale_factor: Optional[float] = None
    total_placed = 0

    for pool_idx, pool_path in enumerate(pool_paths):
        if pool_idx in empty_indices:
            continue

        n_fish = rng.randint(_FISH_PER_POOL_MIN, _FISH_PER_POOL_MAX)
        n_flipped_in_pool = 0
        for fish_id in range(1, n_fish + 1):
            sturgeon_path = f"{pool_path}/Sturgeon_{fish_id:02d}"
            if stage.GetPrimAtPath(sturgeon_path).IsValid():
                continue

            # Random pose inside the pool footprint and water column.
            angle = rng.uniform(0.0, 2.0 * math.pi)
            radius = rng.uniform(_RADIUS_MIN, _RADIUS_MAX)
            local_x = radius * math.cos(angle)
            local_y = radius * math.sin(angle)
            yaw_deg = rng.uniform(0.0, 360.0)

            # Determine if this fish is flipped (belly-up, floating near surface).
            is_flipped = rng.random() < _FLIP_PROBABILITY
            if is_flipped:
                # Add Z offset to compensate for pivot point shift after RotateX(180)
                spawn_z = rng.uniform(_FLIPPED_Z_MIN, _FLIPPED_Z_MAX) + _FLIP_Z_OFFSET
                roll_deg = _FLIP_ROLL_DEG
                n_flipped_in_pool += 1
            else:
                spawn_z = rng.uniform(_SPAWN_Z_MIN, _SPAWN_Z_MAX)
                roll_deg = 0.0

            sturgeon_xform = UsdGeom.Xform.Define(stage, Sdf.Path(sturgeon_path))
            sturgeon_xform.GetPrim().GetReferences().AddReference(asset_url)

            proxies = _disable_proxy_prims(stage, sturgeon_path)

            if scale_factor is None:
                natural = _natural_length(stage, sturgeon_path)
                scale_factor = target_length_m / natural if natural > 0.0 else 1.0
                carb.log_info(
                    f"[sturgeon_spawner] mesh-only length={natural:.3f} m → "
                    f"scale={scale_factor:.4f} (target {target_length_m * 100:.1f} cm; "
                    f"proxies disabled — cubes={proxies['cubes']}, "
                    f"cameras={proxies['cameras']}, lights={proxies['lights']})"
                )

            xf = UsdGeom.Xformable(sturgeon_xform)
            # Force-override the referenced asset's xformOpOrder with an
            # explicit empty array, then add suffixed ops so the asset's
            # animated xformOp:translate timeSamples can't override our values.
            # Order: Translate → Yaw → Flip → Roll → Scale
            # (Roll applied in local coords after flip, for body sway animation)
            xf.GetXformOpOrderAttr().Set([])
            xf.AddTranslateOp(opSuffix="anim").Set(Gf.Vec3d(local_x, local_y, spawn_z))
            xf.AddRotateZOp(opSuffix="yaw").Set(yaw_deg)
            xf.AddRotateXOp(opSuffix="flip").Set(roll_deg)  # flip belly-up if non-zero
            xf.AddRotateZOp(opSuffix="roll").Set(0.0)  # body roll for alive fish (local Z)
            xf.AddScaleOp(opSuffix="anim").Set(
                Gf.Vec3f(scale_factor, scale_factor, scale_factor)
            )

            # Store flipped state as custom attribute for animator to read
            prim = sturgeon_xform.GetPrim()
            prim.CreateAttribute(
                "aquasweep:isFlipped", Sdf.ValueTypeNames.Bool
            ).Set(is_flipped)

            # Add semantic label for vision model training (segmentation masks)
            semantic_class = "sturgeon_dead" if is_flipped else "sturgeon_alive"
            prim.CreateAttribute(
                "aquasweep:semanticClass", Sdf.ValueTypeNames.String
            ).Set(semantic_class)

            _bind_random_palette_material(
                stage, sturgeon_xform.GetPrim(), palette, rng
            )
            total_placed += 1

        carb.log_info(
            f"[sturgeon_spawner] Pool_{pool_idx + 1}: spawned {n_fish} sturgeons "
            f"({n_flipped_in_pool} flipped)"
        )

    return total_placed
