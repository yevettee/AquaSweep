"""Scene-building helpers: pools (tank + water + surface), lighting, equipment.

Used by UIBuilder._setup_scene. Assumes Isaac Sim is already running (so
``pxr`` is importable).

Prim hierarchy:
    /World/Pools (Xform)
        /Pool_<n> (Xform, translate = pool centre)
            /Floor, /Wall, /WallInterior   ← FRP tank meshes (local coords)
            /WaterBody                     ← solid water volume (no collider)
            /WaterSurface                  ← animated wave disc
    /World/Equipment (Xform)
        /UnderwaterEquipment               ← referenced asset or placeholder
    /World/Lighting

Tank material — FRP (glass-fibre reinforced plastic):
    Interior: light teal (0.55, 0.88, 0.82)
    Exterior: blue        (0.14, 0.35, 0.70)
    Opacity ≈ 0.80–0.92, mid roughness (0.25–0.35).
"""
import math
import os

from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics, UsdShade

from . import params

# ── FRP tank colour constants ────────────────────────────────────────────────
_FRP_INTERIOR = (0.55, 0.88, 0.82)
_FRP_EXTERIOR = (0.14, 0.35, 0.70)
_FRP_ROUGHNESS_INT = 0.22
_FRP_ROUGHNESS_EXT = 0.32

WALL_SEGMENTS = 64

POOLS_ROOT = "/World/Pools"
EQUIPMENT_ROOT = "/World/Equipment"
BUILDING_ROOT = "/World/Building"

# ── Building (custom-built fish-farm hall) ────────────────────────────────────
# Built directly in code instead of referencing an Isaac Sim asset, because:
#  (a) Simple_Warehouse.usd brings its own UsdPhysics.Scene with GPU dynamics
#      OFF, which breaks PhysX particle (debris) spawning.
#  (b) Its interior size doesn't match our 40 m × 30 m pool layout.
_FLOOR_THICKNESS = 0.05
_WALL_THICKNESS = 0.30
_WALL_HEIGHT = 5.0
_FLOOR_COLOR = (0.0, 0.14, 0.08)         # 청테이프/방수페인트 녹색 (어둡게)
_WALL_COLOR  = (0.58, 0.57, 0.54)        # lighter concrete (poured panel)


# ── Physics scene helpers ────────────────────────────────────────────────────
def enable_gpu_dynamics(stage) -> None:
    """GPU particle / OceanSim effects require GPU dynamics.

    Sets both the World API context and the USD PhysxSceneAPI attributes —
    physx plugin reads attributes from the prim directly, and ``CreateXxxAttr``
    won't overwrite an existing value, so ``.Set(True)`` is mandatory.
    """
    try:
        from isaacsim.core.api.world import World
        world = World.instance()
        if world is not None:
            world.get_physics_context().enable_gpu_dynamics(True)
    except Exception:
        pass

    try:
        from pxr import PhysxSchema
    except ImportError:
        return

    found = False
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.Scene):
            api = PhysxSchema.PhysxSceneAPI.Apply(prim)
            api.CreateEnableGPUDynamicsAttr().Set(True)
            api.CreateBroadphaseTypeAttr().Set("MBP")
            api.CreateSolverTypeAttr().Set("TGS")
            found = True

    if not found:
        scene_prim = UsdPhysics.Scene.Define(stage, Sdf.Path("/World/PhysicsScene"))
        api = PhysxSchema.PhysxSceneAPI.Apply(scene_prim.GetPrim())
        api.CreateEnableGPUDynamicsAttr().Set(True)
        api.CreateBroadphaseTypeAttr().Set("MBP")
        api.CreateSolverTypeAttr().Set("TGS")


# ── Low-level mesh helpers ───────────────────────────────────────────────────
def _bind_preview_material(stage, prim, mat_path, color, opacity=1.0,
                           roughness=0.4, clearcoat=0.0, clearcoat_roughness=0.1,
                           ior=1.5, emissive=(0.0, 0.0, 0.0)):
    material = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, mat_path + "/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive))
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(clearcoat)
    shader.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(clearcoat_roughness)
    shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(ior)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI(prim).Bind(material)


def _build_solid_cylinder_mesh(stage, path, center, height, radius,
                                color, opacity=1.0, n_segments=WALL_SEGMENTS,
                                collision=False, roughness=0.4, clearcoat=0.0,
                                clearcoat_roughness=0.1, ior=1.5,
                                emissive=(0.0, 0.0, 0.0),
                                skip_bottom_cap=False):
    """Solid cylinder mesh, optionally open at the bottom.

    ``skip_bottom_cap=True`` omits the disc at z=-half_h. We use this for the
    pool's translucent WaterBody so the robot's onboard camera, looking down,
    doesn't see sturgeons ghost-reflected off the water/floor interface mesh.
    """
    mesh = UsdGeom.Mesh.Define(stage, path)

    points = []
    half_h = height / 2.0
    for z in (-half_h, half_h):
        for i in range(n_segments):
            theta = 2.0 * math.pi * i / n_segments
            points.append(Gf.Vec3f(radius * math.cos(theta), radius * math.sin(theta), z))
    bottom_center_idx = len(points)
    points.append(Gf.Vec3f(0.0, 0.0, -half_h))
    top_center_idx = len(points)
    points.append(Gf.Vec3f(0.0, 0.0, half_h))

    fvc, fvi = [], []
    for i in range(n_segments):
        j = (i + 1) % n_segments
        fvc.append(4); fvi.extend([i, j, n_segments + j, n_segments + i])
        if not skip_bottom_cap:
            fvc.append(3); fvi.extend([bottom_center_idx, j, i])
        fvc.append(3); fvi.extend([top_center_idx, n_segments + i, n_segments + j])

    mesh.CreatePointsAttr().Set(points)
    mesh.CreateFaceVertexCountsAttr().Set(fvc)
    mesh.CreateFaceVertexIndicesAttr().Set(fvi)
    mesh.CreateDoubleSidedAttr().Set(True)

    xform = UsdGeom.Xformable(mesh)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*center))

    _bind_preview_material(stage, mesh.GetPrim(), path + "_Mat", color, opacity,
                           roughness, clearcoat, clearcoat_roughness, ior, emissive)

    if collision:
        UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
        UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim())
        UsdPhysics.MeshCollisionAPI(mesh.GetPrim()).CreateApproximationAttr().Set("none")
    return mesh


def _build_tube_mesh(stage, path, center, height, inner_radius, outer_radius,
                     color, opacity=1.0, n_segments=WALL_SEGMENTS,
                     roughness=0.4, clearcoat=0.0, clearcoat_roughness=0.1,
                     ior=1.5, emissive=(0.0, 0.0, 0.0)):
    mesh = UsdGeom.Mesh.Define(stage, path)

    points = []
    for r, z in [(inner_radius, 0.0), (inner_radius, height),
                 (outer_radius, 0.0), (outer_radius, height)]:
        for i in range(n_segments):
            theta = 2.0 * math.pi * i / n_segments
            points.append(Gf.Vec3f(r * math.cos(theta), r * math.sin(theta), z))

    ib = 0
    it = n_segments
    ob = 2 * n_segments
    ot = 3 * n_segments

    fvc, fvi = [], []
    for i in range(n_segments):
        j = (i + 1) % n_segments
        fvc.append(4); fvi.extend([ib + i, it + i, it + j, ib + j])
        fvc.append(4); fvi.extend([ob + i, ob + j, ot + j, ot + i])
        fvc.append(4); fvi.extend([it + i, ot + i, ot + j, it + j])
        fvc.append(4); fvi.extend([ib + i, ib + j, ob + j, ob + i])

    mesh.CreatePointsAttr().Set(points)
    mesh.CreateFaceVertexCountsAttr().Set(fvc)
    mesh.CreateFaceVertexIndicesAttr().Set(fvi)
    mesh.CreateDoubleSidedAttr().Set(True)

    xform = UsdGeom.Xformable(mesh)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*center))

    _bind_preview_material(stage, mesh.GetPrim(), path + "_Mat", color, opacity,
                           roughness, clearcoat, clearcoat_roughness, ior, emissive)

    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI(mesh.GetPrim()).CreateApproximationAttr().Set("none")
    return mesh


def _build_lateral_cylinder(stage, path, center, height, radius, color,
                             opacity=1.0, n_segments=WALL_SEGMENTS,
                             roughness=0.3):
    """Capless tube side mesh (DoubleSided, visual-only overlay).

    The outer wall already carries the collider, so no physics on this layer.
    """
    mesh = UsdGeom.Mesh.Define(stage, path)

    half_h = height / 2.0
    pts = []
    for z_off in (-half_h, half_h):
        for i in range(n_segments):
            theta = 2.0 * math.pi * i / n_segments
            pts.append(Gf.Vec3f(radius * math.cos(theta),
                                radius * math.sin(theta), z_off))

    fvc, fvi = [], []
    for i in range(n_segments):
        j = (i + 1) % n_segments
        fvc.append(4)
        fvi.extend([i, j, n_segments + j, n_segments + i])

    mesh.CreatePointsAttr().Set(pts)
    mesh.CreateFaceVertexCountsAttr().Set(fvc)
    mesh.CreateFaceVertexIndicesAttr().Set(fvi)
    mesh.CreateDoubleSidedAttr().Set(True)

    xform = UsdGeom.Xformable(mesh)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*center))

    _bind_preview_material(stage, mesh.GetPrim(), path + "_Mat",
                           color, opacity, roughness)
    return mesh


# ── Pool builders ────────────────────────────────────────────────────────────
def _build_tank_meshes(stage, pool_path: str) -> None:
    """Tank outer wall + inner colour overlay, all in pool-local coords.

    The pool *floor* mesh is intentionally omitted — its FRP material reflected
    debris and the sturgeon up into the robot's camera view. The building
    floor at z=0 already sits flush with the wall bottom and acts as the
    physical/visual floor inside each pool.
    """
    r  = params.TANK_RADIUS
    h  = params.TANK_INNER_Z
    z0 = params.TANK_FLOOR_Z

    _build_tube_mesh(stage, f"{pool_path}/Wall",
                     center=(0, 0, z0),
                     height=h, inner_radius=r, outer_radius=r + params.WALL_THICKNESS,
                     color=_FRP_EXTERIOR, opacity=0.78,
                     roughness=_FRP_ROUGHNESS_EXT)

    _build_lateral_cylinder(stage, f"{pool_path}/WallInterior",
                            center=(0.0, 0.0, z0 + h / 2.0),
                            height=h,
                            radius=r - 0.001,
                            color=_FRP_INTERIOR, opacity=0.88,
                            roughness=_FRP_ROUGHNESS_INT)


def _build_water_body(stage, pool_path: str) -> None:
    """수면을 얇은 디스크로 표현.
    
    전체 수심을 채우는 실린더 대신 수면만 얇은 plate로 만들어서:
    - 빛이 물 아래까지 투과 (아래 물고기도 보임)
    - 사선에서 봤을 때 수면의 반사/굴절 효과 유지
    - 수면 위/아래 물고기 구분 가능
    """
    r = params.TANK_RADIUS - 0.01
    surface_z = params.water_surface_z()  # 수면 높이 (1.2m)
    plate_thickness = 0.02  # 2cm 두께의 얇은 디스크

    mesh = _build_solid_cylinder_mesh(stage, f"{pool_path}/WaterBody",
                               center=(0, 0, surface_z),
                               height=plate_thickness, radius=r,
                               color=(0.15, 0.40, 0.55),   # 푸른 수면
                               opacity=0.25,               # 수면 느낌 (25%)
                               collision=False,
                               roughness=0.15,             # 약간의 물결 느낌
                               clearcoat=0.3,              # 수면 반사
                               clearcoat_roughness=0.2,
                               ior=1.33)
    
    # 그림자 드리움만 비활성화 - 수면이 물고기에 그림자를 드리우지 않도록
    # (invisibleToSecondaryRays는 사용 안 함 - 굴절/투과까지 차단됨)
    prim = mesh.GetPrim()
    prim.CreateAttribute("primvars:doNotCastShadows", Sdf.ValueTypeNames.Bool).Set(True)


def _build_underwater_light(stage, pool_path: str) -> None:
    """수조 바닥에 원형 조명 추가 - WaterBody가 위에서 오는 빛을 차단해도 물고기가 보이도록.
    
    실제 양식장에서도 수중 조명을 사용하는 경우가 많음.
    """
    light_path = f"{pool_path}/UnderwaterLight"
    if stage.GetPrimAtPath(light_path).IsValid():
        return
    
    # 수조 형태에 맞춘 원형 조명 (DiskLight)
    light = UsdLux.DiskLight.Define(stage, light_path)
    light.CreateIntensityAttr(200.0)             # 밝은 조명
    light.CreateColorAttr(Gf.Vec3f(0.95, 0.98, 1.0))  # 차가운 흰색 (수중 느낌)
    light.CreateRadiusAttr(params.TANK_RADIUS)  # 수조 반경에 맞춤
    
    # 바닥에서 위를 향하도록 배치 (Z=0.1, 위쪽 방향)
    xf = UsdGeom.Xformable(light)
    xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.1))
    xf.AddRotateXYZOp().Set(Gf.Vec3f(180.0, 0.0, 0.0))  # 위쪽을 향하도록 뒤집기


def _build_water_surface(stage, pool_path: str) -> None:
    """Tessellated water surface disc; WaterSurfaceAnimator drives the Z over time."""
    surface_path = f"{pool_path}/WaterSurface"

    R = params.TANK_RADIUS - 0.01
    z = params.water_surface_z()

    N_RINGS = 8
    N_SEGS = 36

    points = [Gf.Vec3f(0.0, 0.0, z)]
    ring_radii = [R * (i + 1) / N_RINGS for i in range(N_RINGS)]
    for r in ring_radii:
        for j in range(N_SEGS):
            theta = 2.0 * math.pi * j / N_SEGS
            points.append(Gf.Vec3f(r * math.cos(theta), r * math.sin(theta), z))

    fvc, fvi = [], []
    for j in range(N_SEGS):
        k = (j + 1) % N_SEGS
        fvc.append(3)
        fvi.extend([0, 1 + j, 1 + k])
    for ring in range(N_RINGS - 1):
        base_c = 1 + ring * N_SEGS
        base_n = 1 + (ring + 1) * N_SEGS
        for j in range(N_SEGS):
            k = (j + 1) % N_SEGS
            fvc.append(4)
            fvi.extend([base_c + j, base_c + k, base_n + k, base_n + j])

    mesh = UsdGeom.Mesh.Define(stage, surface_path)
    mesh.CreatePointsAttr().Set(points)
    mesh.CreateFaceVertexCountsAttr().Set(fvc)
    mesh.CreateFaceVertexIndicesAttr().Set(fvi)
    mesh.CreateDoubleSidedAttr().Set(True)

    _bind_preview_material(stage, mesh.GetPrim(), surface_path + "_Mat",
                           color=(0.18, 0.40, 0.50),
                           opacity=0.45,
                           roughness=0.70,
                           clearcoat=0.0,
                           clearcoat_roughness=0.0,
                           ior=1.33)


def build_pool(stage, pool_path: str, center: tuple[float, float]) -> None:
    """Build one full pool (tank + water body) at a 2-D centre.

    The Pool Xform carries the translate; child meshes are in local coords.
    Idempotent: skips if pool_path already exists.

    The animated water-surface disc is intentionally omitted — its semi-transparent
    overlay made debris/sturgeon harder to see and added little visual value.
    """
    if stage.GetPrimAtPath(pool_path).IsValid():
        return
    pool_xform = UsdGeom.Xform.Define(stage, pool_path)
    xf = UsdGeom.Xformable(pool_xform)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(center[0], center[1], 0.0))

    _build_tank_meshes(stage, pool_path)
    _build_water_body(stage, pool_path)
    _build_underwater_light(stage, pool_path)


def build_pools(stage, root: str = POOLS_ROOT) -> None:
    """Build all 7 pools defined by params.POOL_CENTERS under root/Pool_<n>."""
    if not stage.GetPrimAtPath(root).IsValid():
        UsdGeom.Xform.Define(stage, root)
    for i, center in enumerate(params.POOL_CENTERS, start=1):
        build_pool(stage, f"{root}/Pool_{i}", center)


# ── Top-view cameras (one per pool) ──────────────────────────────────────────
_TOPCAM_HEIGHT = 12.0           # m above pool floor
_TOPCAM_FOCAL_LENGTH = 15.0    # mm — wide enough to frame an 8 m pool
_TOPCAM_H_APERTURE = 20.955    # mm — Isaac Sim default 16:9 sensor
_TOPCAM_V_APERTURE = 15.291    # mm
_TOPCAM_CLIP_NEAR = 0.1
_TOPCAM_CLIP_FAR = 100.0


def _build_top_camera(stage, pool_path: str) -> None:
    """Single downward-facing camera centred over a pool, in pool-local coords.

    USD cameras look down the local -Z axis by default. With a Z-up stage and
    no extra rotation, placing the camera at (0, 0, +h) makes it look straight
    down onto the floor — exactly the top-view we want.
    """
    cam_path = f"{pool_path}/TopCamera"
    if stage.GetPrimAtPath(cam_path).IsValid():
        return

    cam = UsdGeom.Camera.Define(stage, cam_path)
    cam.CreateFocalLengthAttr(_TOPCAM_FOCAL_LENGTH)
    cam.CreateHorizontalApertureAttr(_TOPCAM_H_APERTURE)
    cam.CreateVerticalApertureAttr(_TOPCAM_V_APERTURE)
    cam.CreateClippingRangeAttr(Gf.Vec2f(_TOPCAM_CLIP_NEAR, _TOPCAM_CLIP_FAR))

    xf = UsdGeom.Xformable(cam)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, _TOPCAM_HEIGHT))


def build_top_cameras(stage, root: str = POOLS_ROOT) -> None:
    """Attach a top-view camera under each Pool_<n> Xform.

    Must run *after* :func:`build_pools` so the Pool prims exist.
    Idempotent — re-running skips pools that already have a TopCamera child.
    """
    pools_prim = stage.GetPrimAtPath(root)
    if not pools_prim or not pools_prim.IsValid():
        return
    for pool_prim in sorted(pools_prim.GetChildren(), key=lambda p: str(p.GetPath())):
        _build_top_camera(stage, str(pool_prim.GetPath()))


# ── Equipment builder (Isaac asset reference w/ placeholder fallback) ────────
# Isaac Sim 5.1 asset paths (relative to get_assets_root_path()).
# Verified against https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1
# Plastic barrels visually read as water-treatment / filtration equipment.
_EQUIPMENT_CANDIDATES: list[str] = [
    "/Isaac/Environments/Simple_Warehouse/Props/SM_BarelPlastic_A_01.usd",
    "/Isaac/Environments/Simple_Warehouse/Props/SM_BarelPlastic_B_01.usd",
    "/Isaac/Environments/Simple_Warehouse/Props/SM_PaletteA_01.usd",
]


def _asset_exists(url: str) -> bool:
    try:
        import omni.client
        result, _ = omni.client.stat(url)
        return result == omni.client.Result.OK
    except Exception:
        return False


def _resolve_equipment_asset_url() -> str | None:
    try:
        from isaacsim.storage.native import get_assets_root_path
    except ImportError:
        try:
            from isaacsim.core.utils.nucleus import get_assets_root_path  # legacy
        except ImportError:
            return None

    root = get_assets_root_path()
    if not root:
        return None
    for rel in _EQUIPMENT_CANDIDATES:
        url = root + rel
        if _asset_exists(url):
            return url
    return None


def _build_equipment_placeholder(stage, prim_path: str) -> None:
    """Fallback: a labelled cylinder occupying the equipment slot footprint."""
    r = params.TANK_RADIUS
    h = params.TANK_INNER_Z
    _build_solid_cylinder_mesh(stage, prim_path,
                               center=(0, 0, h / 2.0),
                               height=h, radius=r,
                               color=(0.42, 0.45, 0.50),  # steel grey
                               opacity=1.0,
                               collision=True,
                               roughness=0.45)


def _build_box(stage, path: str, center: tuple[float, float, float],
               size: tuple[float, float, float], color: tuple[float, float, float],
               opacity: float = 1.0, collision: bool = True,
               roughness: float = 0.6, ior: float = 1.5) -> UsdGeom.Cube:
    """Axis-aligned cuboid via UsdGeom.Cube + translate/scale xformOps.

    ``size`` is the full extent on each axis (UsdGeom.Cube starts as a 1 m
    unit cube, so the scale equals the desired extents directly).
    """
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    xf = UsdGeom.Xformable(cube)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*center))
    xf.AddScaleOp().Set(Gf.Vec3f(*size))

    _bind_preview_material(stage, cube.GetPrim(), path + "_Mat",
                           color, opacity, roughness, ior=ior)
    if collision:
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
    return cube


def build_building(stage, root: str = BUILDING_ROOT) -> None:
    """Build a simple fish-farm hall: 40 × 30 m floor + 4 walls + ceiling slab.

    Coordinate convention:
      - Interior usable footprint exactly ``params.BUILDING_X × BUILDING_Y``
        (40 × 30 m), centred on the world origin.
      - Walls sit *outside* that footprint, so pool meshes never clip them.
      - Floor top surface is at ``z=0``; walls rise to ``z=_WALL_HEIGHT``.

    Built procedurally instead of referencing an asset so the building owns no
    extra UsdPhysics.Scene (which previously broke particle GPU dynamics).
    Idempotent.
    """
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)

    bx = params.BUILDING_X
    by = params.BUILDING_Y
    wt = _WALL_THICKNESS
    wh = _WALL_HEIGHT
    ft = _FLOOR_THICKNESS

    # Floor — top face flush with z=0, extends slightly under the walls.
    # Near-fully matte (roughness ≈ 1.0) and ior=1.0 to suppress fresnel
    # reflection — otherwise sturgeons swimming above appear mirrored on the
    # floor through the translucent water body.
    _build_box(stage, f"{root}/Floor",
               center=(0.0, 0.0, -ft / 2.0),
               size=(bx + 2 * wt, by + 2 * wt, ft),
               color=_FLOOR_COLOR, roughness=0.98, ior=1.0)

    # Walls — 4 cuboids hugging the building perimeter.
    half_bx_out = (bx + wt) / 2.0   # wall centre offset along x (south/north walls span full x)
    half_by_out = (by + wt) / 2.0
    full_x_len  = bx + 2 * wt       # south/north walls extend past corners
    interior_y_len = by             # east/west walls fit between the n/s walls

    _build_box(stage, f"{root}/Wall_South",
               center=(0.0, -half_by_out, wh / 2.0),
               size=(full_x_len, wt, wh),
               color=_WALL_COLOR, roughness=0.85)
    _build_box(stage, f"{root}/Wall_North",
               center=(0.0,  half_by_out, wh / 2.0),
               size=(full_x_len, wt, wh),
               color=_WALL_COLOR, roughness=0.85)
    _build_box(stage, f"{root}/Wall_West",
               center=(-half_bx_out, 0.0, wh / 2.0),
               size=(wt, interior_y_len, wh),
               color=_WALL_COLOR, roughness=0.85)
    _build_box(stage, f"{root}/Wall_East",
               center=( half_bx_out, 0.0, wh / 2.0),
               size=(wt, interior_y_len, wh),
               color=_WALL_COLOR, roughness=0.85)


def build_equipment(stage, root: str = EQUIPMENT_ROOT) -> None:
    """Place the underwater-equipment asset at params.EQUIPMENT_CENTER.

    Tries Isaac Sim built-in assets first; falls back to a grey cylinder
    placeholder so the build always succeeds. Idempotent.
    """
    if not stage.GetPrimAtPath(root).IsValid():
        UsdGeom.Xform.Define(stage, root)

    slot_path = f"{root}/UnderwaterEquipment"
    if stage.GetPrimAtPath(slot_path).IsValid():
        return

    slot_xform = UsdGeom.Xform.Define(stage, slot_path)
    asset_url = _resolve_equipment_asset_url()
    if asset_url is not None:
        # AddReference first; the referenced asset's root may carry its own
        # xformOps. We then enforce our translate via xformOpOrder (`!resetXformStack!`
        # would discard the asset's transform — we want to keep its internal
        # transform but place the whole thing at EQUIPMENT_CENTER).
        slot_xform.GetPrim().GetReferences().AddReference(asset_url)

    xf = UsdGeom.Xformable(slot_xform)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(params.EQUIPMENT_CENTER[0],
                                      params.EQUIPMENT_CENTER[1],
                                      0.0))

    if asset_url is None:
        # Fallback: placeholder cylinder as a child of the slot xform
        _build_equipment_placeholder(stage, f"{slot_path}/Placeholder")


# ── Lighting ─────────────────────────────────────────────────────────────────
def add_lighting(stage, root: str = "/World/Lighting") -> None:
    """Indoor fish-farm lighting: cool-white DistantLight + ceiling RectLight."""
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)

    # Isaac Sim 기본 환경 조명 비활성화/조절 (과도한 그림자 및 반사 방지)
    _configure_default_environment_light(stage)

    cool_white = Gf.Vec3f(0.91, 0.96, 1.0)   # #E8F4FF — fluorescent tone

    # 환경광 (DomeLight) - 전체적인 색조와 ambient 제공 (고정, 따라다니지 않음)
    dome = UsdLux.DomeLight.Define(stage, f"{root}/AmbientDome")
    dome.CreateIntensityAttr(600.0)
    dome.CreateExposureAttr(1.0)
    dome.CreateColorAttr(cool_white)
    # 그림자 비활성화
    dome.GetPrim().CreateAttribute("inputs:shadow:enable", Sdf.ValueTypeNames.Bool).Set(False)

    # 천장 조명 - 실제 양식장처럼 균일한 실내 조명
    ceiling = UsdLux.RectLight.Define(stage, f"{root}/CeilingLight")
    ceiling.CreateIntensityAttr(1000.0)
    ceiling.CreateExposureAttr(1.0)
    ceiling.CreateColorAttr(cool_white)
    ceiling.CreateWidthAttr(params.BUILDING_X * 0.9)
    ceiling.CreateHeightAttr(params.BUILDING_Y * 0.9)
    UsdGeom.Xformable(ceiling).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 3.0))
    # 그림자 비활성화
    ceiling.GetPrim().CreateAttribute("inputs:shadow:enable", Sdf.ValueTypeNames.Bool).Set(False)


def _configure_default_environment_light(stage) -> None:
    """Isaac Sim 기본 환경 조명(/Environment/defaultLight) 비활성화.
    
    Camera Light는 카메라를 따라다니므로 비활성화하고,
    고정된 Stage 조명(CeilingLight, UnderwaterLight)만 사용.
    """
    default_light_path = "/Environment/defaultLight"
    prim = stage.GetPrimAtPath(default_light_path)
    
    if not prim or not prim.IsValid():
        return
    
    # Camera Light 완전 비활성화 (따라다니는 빛 반사 제거)
    prim.SetActive(False)
