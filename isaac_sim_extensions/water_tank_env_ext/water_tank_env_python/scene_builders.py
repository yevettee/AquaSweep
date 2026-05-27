"""Scene-building helpers: pools (shell ref + water body), building ref, lighting, equipment.

Used by UIBuilder._setup_scene. Assumes Isaac Sim is already running (so
``pxr`` is importable).

Prim hierarchy:
    /World/Building                    ← Reference: aquafarm_environment.usda
    /World/Pools (Xform)
        /Pool_<n> (Xform, translate = pool centre)
            /Shell                     ← Reference: pool_shell.usda
                                          (Outer / InnerWall / Bottom / Drain / Air×4 / Sensor / Pipe)
                                          CollisionAPI baked in: InnerWall (none), Bottom (convexHull).
            /WaterBody                 ← solid water disc (code-generated, no collider)
            /UnderwaterLight           ← spotlight from below
    /World/Equipment                   ← /UnderwaterEquipment placeholder/asset
    /World/Lighting                    ← DomeLight + RectLight
"""
import math
from pathlib import Path

import carb
from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics, UsdShade

from . import params


WALL_SEGMENTS = 64

POOLS_ROOT = "/World/Pools"
EQUIPMENT_ROOT = "/World/Equipment"
BUILDING_ROOT = "/World/Building"
OUTDOOR_GROUND_ROOT = "/World/OutdoorGround"
PARKING_ROOT = "/World/OutdoorGround/Parking"
PARKED_CARS_ROOT = "/World/OutdoorGround/ParkedCars"
DOOR_ROOT = "/World/Building/EastDoor"

# Parking-paint diffuse — slightly off-white (avoids glare in RTX).
_PARKING_PAINT_DIFFUSE = Gf.Vec3f(0.88, 0.88, 0.86)

# Dark steel door — low albedo, metallic, slight roughness.
_STEEL_DIFFUSE = Gf.Vec3f(0.18, 0.18, 0.20)

# NVIDIA Base/Natural MDL material (S3-backed, no local Nucleus needed).
_ASPHALT_MDL_URL = (
    "http://omniverse-content-production.s3-us-west-2.amazonaws.com"
    "/Materials/Base/Natural/Asphalt.mdl"
)
_ASPHALT_MDL_NAME = "Asphalt"

# ── External USD assets (aquafarm slice) ──────────────────────────────────────
# Resolved at runtime from __file__ — portable across team members regardless of
# clone location. Requires aquafarm_final.usdz in the same folder because
# textures are sublayer-referenced as @./aquafarm_final.usdz[textures/...]@.
_SCENES_DIR = Path(__file__).resolve().parents[3] / "assets" / "scenes"
_AQUAFARM_ENV_USD = str(_SCENES_DIR / "aquafarm_environment.usda")
_POOL_SHELL_USD   = str(_SCENES_DIR / "pool_shell.usda")
_CARS_DIR = _SCENES_DIR.parent / "car"   # /home/rokey/water_ws/src/assets/car



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
        UsdPhysics.MeshCollisionAPI(mesh.GetPrim()).CreateApproximationAttr().Set("convexDecomposition")
    return mesh


def _build_water_body(stage, pool_path: str) -> None:
    """수면을 얇은 디스크로 표현.
    
    전체 수심을 채우는 실린더 대신 수면만 얇은 plate로 만들어서:
    - 빛이 물 아래까지 투과 (아래 물고기도 보임)
    - 사선에서 봤을 때 수면의 반사/굴절 효과 유지
    - 수면 위/아래 물고기 구분 가능

    Idempotent: skips if WaterBody already exists.
    """
    water_body_path = f"{pool_path}/WaterBody"
    if stage.GetPrimAtPath(water_body_path).IsValid():
        return

    r = params.TANK_RADIUS - 0.01
    surface_z = params.water_surface_z()  # 수면 높이 (1.2m)
    plate_thickness = 0.02  # 2cm 두께의 얇은 디스크

    mesh = _build_solid_cylinder_mesh(stage, water_body_path,
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
    light.CreateIntensityAttr(90.0)
    light.CreateExposureAttr(1.0)
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
    Idempotent: each component (Xform, Wall, WaterBody, etc.) is created only
    if it doesn't already exist, so partial states are recovered gracefully.

    The animated water-surface disc is intentionally omitted — its semi-transparent
    overlay made debris/sturgeon harder to see and added little visual value.
    """
    carb.log_info(f"[scene_builders] build_pool called: {pool_path}, center={center}")
    
    # Create Pool Xform if it doesn't exist
    pool_exists = stage.GetPrimAtPath(pool_path).IsValid()
    carb.log_info(f"[scene_builders] Pool Xform exists: {pool_exists}")
    
    if not pool_exists:
        pool_xform = UsdGeom.Xform.Define(stage, pool_path)
        xf = UsdGeom.Xformable(pool_xform)
        xf.ClearXformOpOrder()
        xf.AddTranslateOp().Set(Gf.Vec3d(center[0], center[1], 0.0))
        carb.log_info(f"[scene_builders] Created Pool Xform: {pool_path}")

    # Shell: aquafarm pool_shell.usda (Outer/InnerWall/Bottom/Drain/Air×4/...).
    # CollisionAPI lives inside pool_shell.usda (InnerWall=none, Bottom=convexHull).
    shell_path = f"{pool_path}/Shell"
    if not stage.GetPrimAtPath(shell_path).IsValid():
        shell_prim = stage.DefinePrim(shell_path, "Xform")
        shell_prim.GetReferences().AddReference(_POOL_SHELL_USD)
        carb.log_info(f"[scene_builders] Shell reference added: {shell_path} -> {_POOL_SHELL_USD}")

    _build_water_body(stage, pool_path)
    _build_underwater_light(stage, pool_path)

    shell_exists = stage.GetPrimAtPath(shell_path).IsValid()
    water_exists = stage.GetPrimAtPath(f"{pool_path}/WaterBody").IsValid()
    carb.log_info(f"[scene_builders] After build_pool: Shell={shell_exists}, WaterBody={water_exists}")


def build_pools(stage, root: str = POOLS_ROOT) -> None:
    """Build all 7 pools defined by params.POOL_CENTERS under root/Pool_<n>."""
    carb.log_info(f"[scene_builders] build_pools called, root={root}, POOL_CENTERS count={len(params.POOL_CENTERS)}")
    
    if not stage.GetPrimAtPath(root).IsValid():
        UsdGeom.Xform.Define(stage, root)
        carb.log_info(f"[scene_builders] Created Pools root: {root}")
    
    for i, center in enumerate(params.POOL_CENTERS, start=1):
        build_pool(stage, f"{root}/Pool_{i}", center)


# ── Top-view cameras (one per pool) ──────────────────────────────────────────
_TOPCAM_HEIGHT = 10.0           # m above pool floor
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


# ── Global top-view camera (single camera for all pools) ─────────────────────
_GLOBAL_CAM_HEIGHT = 12.0      # m — lowered for better resolution per pool
_GLOBAL_CAM_FOCAL = 6.5        # mm — wider FOV (~120°) to cover 40x30m at 12m height
_GLOBAL_CAM_H_APERTURE = 20.955  # mm
_GLOBAL_CAM_V_APERTURE = 15.291  # mm (4:3 aspect for 1920x1440)
GLOBAL_CAM_PATH = "/World/GlobalTopCamera"


def build_global_top_camera(stage, path: str = GLOBAL_CAM_PATH) -> None:
    """Single downward-facing camera viewing entire building from above.

    Replaces 7 per-pool cameras with 1 global camera for performance:
    - 7 render products → 1 render product (86% reduction)
    - GPU renders single large frame instead of 7 small ones

    Coverage: 40m × 30m building at 25m height with 8mm focal length.
    Recommended resolution: 1920×1440 (4:3) → ~480×480 per pool region.

    Detection node crops pool regions from the global image.
    """
    if stage.GetPrimAtPath(path).IsValid():
        return

    cam = UsdGeom.Camera.Define(stage, path)
    cam.CreateFocalLengthAttr(_GLOBAL_CAM_FOCAL)
    cam.CreateHorizontalApertureAttr(_GLOBAL_CAM_H_APERTURE)
    cam.CreateVerticalApertureAttr(_GLOBAL_CAM_V_APERTURE)
    cam.CreateClippingRangeAttr(Gf.Vec2f(_TOPCAM_CLIP_NEAR, _TOPCAM_CLIP_FAR))

    xf = UsdGeom.Xformable(cam)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, _GLOBAL_CAM_HEIGHT))


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


def build_building(stage, root: str = BUILDING_ROOT) -> None:
    """Reference the aquafarm building asset (walls + floor + ceiling + lights + machinery).

    Replaces the previous procedural cuboid build with a single Reference to
    ``aquafarm_environment.usda``. That file contains no UsdPhysics.Scene, so
    GPU dynamics for debris particles remain unaffected.
    Idempotent: only defines the prim if missing; AddReference is skipped on rerun.
    """
    if not stage.GetPrimAtPath(root).IsValid():
        building_prim = stage.DefinePrim(root, "Xform")
        building_prim.GetReferences().AddReference(_AQUAFARM_ENV_USD)
        carb.log_info(f"[scene_builders] Building reference added: {root} -> {_AQUAFARM_ENV_USD}")


def _create_mdl_material(
    stage,
    prim_path: str,
    mdl_url: str,
    sub_identifier: str,
    mdl_inputs: dict | None = None,
):
    """Build a UsdShade.Material backed by an MDL shader (S3 or Nucleus URL).

    ``mdl_inputs`` lets callers override OmniPBR parameters such as
    ``albedo_brightness`` or ``diffuse_tint`` — pass ``{name: (sdf_type, value)}``.
    """
    material = UsdShade.Material.Define(stage, prim_path)
    shader = UsdShade.Shader.Define(stage, f"{prim_path}/Shader")
    shader.CreateImplementationSourceAttr().Set(UsdShade.Tokens.sourceAsset)
    shader.SetSourceAsset(mdl_url, "mdl")
    shader.SetSourceAssetSubIdentifier(sub_identifier, "mdl")
    if mdl_inputs:
        for key, (sdf_type, value) in mdl_inputs.items():
            shader.CreateInput(key, sdf_type).Set(value)
    surface_output = material.CreateSurfaceOutput("mdl")
    surface_output.ConnectToSource(shader.ConnectableAPI(), "out")
    return material


def build_outdoor_ground(stage, root: str = OUTDOOR_GROUND_ROOT) -> None:
    """Visual-only dry-earth plane around the aquafarm building.

    Single quad mesh at z = params.GROUND_Z (flush with the aquafarm Floor's
    bottom face), so the building's own Floor mesh occludes it indoors.
    No collider — purely cosmetic, no physics cost. Idempotent.
    """
    if stage.GetPrimAtPath(root).IsValid():
        return

    half_x = params.GROUND_X * 0.5
    half_y = params.GROUND_Y * 0.5
    z = params.GROUND_Z

    mesh = UsdGeom.Mesh.Define(stage, root)
    mesh.CreatePointsAttr([
        Gf.Vec3f(-half_x, -half_y, z),
        Gf.Vec3f( half_x, -half_y, z),
        Gf.Vec3f( half_x,  half_y, z),
        Gf.Vec3f(-half_x,  half_y, z),
    ])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateNormalsAttr([Gf.Vec3f(0, 0, 1)] * 4)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr([
        Gf.Vec3f(-half_x, -half_y, z),
        Gf.Vec3f( half_x,  half_y, z),
    ])

    # UV tiling — without primvars:st the MDL samples a single pixel (solid color).
    # 1 repeat per ~8 m suits the asphalt texture's coarse aggregate pattern.
    uv_tiles_x = params.GROUND_X / 8.0
    uv_tiles_y = params.GROUND_Y / 8.0
    st_primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex
    )
    st_primvar.Set([
        Gf.Vec2f(0.0,        0.0),
        Gf.Vec2f(uv_tiles_x, 0.0),
        Gf.Vec2f(uv_tiles_x, uv_tiles_y),
        Gf.Vec2f(0.0,        uv_tiles_y),
    ])

    mat_path = f"{root}/AsphaltMat"
    material = _create_mdl_material(
        stage, mat_path, _ASPHALT_MDL_URL, _ASPHALT_MDL_NAME,
        mdl_inputs={"albedo_brightness": (Sdf.ValueTypeNames.Float, 0.5)},
    )
    UsdShade.MaterialBindingAPI(mesh.GetPrim()).Bind(material)

    carb.log_info(
        f"[scene_builders] Outdoor ground built: {root} "
        f"({params.GROUND_X}x{params.GROUND_Y}m at z={z})"
    )


def build_parking_lot(stage, root: str = PARKING_ROOT) -> None:
    """Painted parking stalls along the west wall (x = PARKING_WALL_X).

    Closed-rectangle pattern: each stall is fully outlined. Implemented as
    (n+1) cross-wall division stripes (sharing edges between neighbours) plus
    two wall-aligned stripes at the front and back, so 8 stalls render as
    8 closed rectangles with only n+3 strips total. Single mesh, one shared
    off-white material. Sits 5 mm above asphalt. Idempotent.
    """
    if stage.GetPrimAtPath(root).IsValid():
        return

    n = params.PARKING_STALL_COUNT
    w = params.PARKING_STALL_WIDTH
    d = params.PARKING_STALL_DEPTH
    line = params.PARKING_LINE_WIDTH
    half_line = line * 0.5
    wall_x = params.PARKING_WALL_X                          # building wall (x=-20)
    front_x = wall_x - params.PARKING_OFFSET_FROM_WALL      # stall entry (x=-22)
    back_x = front_x - d                                     # stall back (x=-27)
    array_half_y = (n * w) * 0.5                             # 14.0
    z = params.GROUND_Z + 0.005                              # 5 mm above asphalt

    points: list[Gf.Vec3f] = []
    face_indices: list[int] = []

    # n+1 cross-wall division stripes (along X, one between each pair + ends)
    for i in range(n + 1):
        cy = -array_half_y + i * w
        base = len(points)
        points.extend([
            Gf.Vec3f(back_x,  cy - half_line, z),
            Gf.Vec3f(front_x, cy - half_line, z),
            Gf.Vec3f(front_x, cy + half_line, z),
            Gf.Vec3f(back_x,  cy + half_line, z),
        ])
        face_indices.extend([base, base + 1, base + 2, base + 3])

    # 2 wall-aligned stripes (front and back edges, along Y)
    for edge_x in (front_x, back_x):
        base = len(points)
        points.extend([
            Gf.Vec3f(edge_x - half_line, -array_half_y, z),
            Gf.Vec3f(edge_x + half_line, -array_half_y, z),
            Gf.Vec3f(edge_x + half_line,  array_half_y, z),
            Gf.Vec3f(edge_x - half_line,  array_half_y, z),
        ])
        face_indices.extend([base, base + 1, base + 2, base + 3])

    face_count = n + 3  # (n+1) dividers + 2 wall-aligned edges

    mesh = UsdGeom.Mesh.Define(stage, root)
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr([4] * face_count)
    mesh.CreateFaceVertexIndicesAttr(face_indices)
    mesh.CreateNormalsAttr([Gf.Vec3f(0, 0, 1)] * len(points))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr([
        Gf.Vec3f(back_x,  -array_half_y, z),
        Gf.Vec3f(front_x,  array_half_y, z),
    ])

    mat_path = f"{root}/PaintMat"
    material = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(_PARKING_PAINT_DIFFUSE)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.7)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI(mesh.GetPrim()).Bind(material)

    carb.log_info(
        f"[scene_builders] Parking lot: {n} stalls along x={wall_x:+.1f}, "
        f"{face_count} paint stripes"
    )


def set_default_view(stage, camera_path: str = "/World/AquaSweep_DefaultView") -> None:
    """Snap the viewport to a dedicated camera prim under /World.

    /OmniverseKit_Persp lives on the session layer and ignores edits made on
    the root layer (only its rotation slipped through previously, translate
    did not). A camera we own on the root layer is fully editable, and we
    activate it via the Viewport API so Kit reads our transform directly.
    """
    cam_prim = stage.GetPrimAtPath(camera_path)
    if not cam_prim.IsValid():
        cam = UsdGeom.Camera.Define(stage, camera_path)
    else:
        cam = UsdGeom.Camera(cam_prim)

    xf = UsdGeom.Xformable(cam)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*params.DEFAULT_VIEW_TRANSLATE))
    xf.AddRotateXYZOp().Set(Gf.Vec3f(*params.DEFAULT_VIEW_ROTATE_XYZ))

    try:
        from omni.kit.viewport.utility import get_active_viewport
        viewport = get_active_viewport()
        if viewport is not None:
            viewport.set_active_camera(camera_path)
    except Exception as exc:
        carb.log_warn(f"[scene_builders] viewport switch skipped: {exc}")

    carb.log_info(
        f"[scene_builders] Default view set on {camera_path}: "
        f"translate={params.DEFAULT_VIEW_TRANSLATE} rotateXYZ={params.DEFAULT_VIEW_ROTATE_XYZ}"
    )


def build_parked_cars(stage, root: str = PARKED_CARS_ROOT) -> None:
    """Reference real car USDZ assets into selected parking stalls.

    Each car is placed at the stall's centre with a uniform Y-up→Z-up rotation
    and cm→m scale, then optionally fine-tuned via params.CAR_PER_INDEX_TUNING
    (z-offset, yaw, scale multiplier). Wrapper Xform pattern: our transforms
    sit on the wrapper, the inner prim holds the USDZ reference so its own
    xformOps remain intact. Visual-only, no collider. Idempotent.
    """
    if stage.GetPrimAtPath(root).IsValid():
        return

    UsdGeom.Xform.Define(stage, root)

    w = params.PARKING_STALL_WIDTH
    d = params.PARKING_STALL_DEPTH
    wall_x = params.PARKING_WALL_X
    front_x = wall_x - params.PARKING_OFFSET_FROM_WALL
    array_half_y = (params.PARKING_STALL_COUNT * w) * 0.5
    stall_center_x = front_x - d * 0.5

    rx, ry, rz_base = params.CAR_BASE_ROTATE_XYZ

    for slot_n, (stall_idx, usd_filename, tuning) in enumerate(zip(
        params.CAR_STALL_INDICES, params.CAR_USD_FILES, params.CAR_PER_INDEX_TUNING
    )):
        dx, dy, dz, yaw_extra, scale_mul, color_override = tuning
        cx = stall_center_x + dx
        cy = -array_half_y + stall_idx * w + w * 0.5 + dy
        cz = dz
        scale = params.CAR_BASE_SCALE * scale_mul

        car_path = f"{root}/Car_{slot_n}"
        wrapper = UsdGeom.Xform.Define(stage, car_path)
        xf = UsdGeom.Xformable(wrapper)
        xf.AddTranslateOp().Set(Gf.Vec3d(cx, cy, cz))
        # Rotation order: Z first (yaw in our world), then X (Y-up→Z-up).
        # RotateXYZ applies X→Y→Z, so we encode the yaw in the Z slot.
        xf.AddRotateXYZOp().Set(Gf.Vec3f(rx, ry, rz_base + yaw_extra))
        xf.AddScaleOp().Set(Gf.Vec3f(scale, scale, scale))

        # Inner Xform holds the reference so the USDZ's own xformOps stay intact
        inner_path = f"{car_path}/Model"
        inner = stage.DefinePrim(inner_path, "Xform")
        usdz_path = _CARS_DIR / usd_filename
        if not usdz_path.is_file():
            carb.log_error(f"[scene_builders] Car USDZ not found: {usdz_path}")
            continue
        inner.GetReferences().AddReference(str(usdz_path))

        # Optional colour override — strongerThanDescendants forces the USDZ's
        # nested mesh materials to inherit this paint instead of their bundled
        # one. Works because the referenced bindings carry the default
        # (weakerThanDescendants) strength.
        if color_override is not None:
            mat_path = f"{car_path}/PaintOverride"
            paint = UsdShade.Material.Define(stage, mat_path)
            shader = UsdShade.Shader.Define(stage, f"{mat_path}/Surface")
            shader.CreateIdAttr("UsdPreviewSurface")
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
                Gf.Vec3f(*color_override)
            )
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.3)
            paint.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
            UsdShade.MaterialBindingAPI(wrapper.GetPrim()).Bind(
                paint, UsdShade.Tokens.strongerThanDescendants
            )

    carb.log_info(
        f"[scene_builders] Parked {len(params.CAR_USD_FILES)} cars at stalls "
        f"{params.CAR_STALL_INDICES}"
    )


def build_door(stage, root: str = DOOR_ROOT) -> None:
    """Visual-only steel hangar door on the east wall.

    Placeholder UsdGeom.Cube sized/placed to match the user-tuned viewport
    transform (``params.DOOR_TRANSLATE`` / ``params.DOOR_SCALE``). Embedded
    in the wall is intentional — purely cosmetic, no collider. Idempotent.
    """
    if stage.GetPrimAtPath(root).IsValid():
        return

    cube = UsdGeom.Cube.Define(stage, root)
    # Match Isaac Sim GUI's cube (size=1.0, extent ±0.5) rather than the USD
    # default of 2.0 — otherwise the same scale values yield a 2× thicker box.
    cube.CreateSizeAttr(1.0)
    xf = UsdGeom.Xformable(cube)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*params.DOOR_TRANSLATE))
    xf.AddRotateXYZOp().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    xf.AddScaleOp().Set(Gf.Vec3f(*params.DOOR_SCALE))

    mat_path = f"{root}/SteelMat"
    material = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(_STEEL_DIFFUSE)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.85)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI(cube.GetPrim()).Bind(material)

    carb.log_info(
        f"[scene_builders] East steel door placed at {params.DOOR_TRANSLATE} "
        f"scale={params.DOOR_SCALE}"
    )


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
    """Indoor fish-farm lighting: cool-white DistantLight + ceiling RectLight.

    Idempotent: each light is created only if it doesn't already exist.
    """
    # Create Lighting Xform if it doesn't exist
    if not stage.GetPrimAtPath(root).IsValid():
        UsdGeom.Xform.Define(stage, root)

    # Isaac Sim 기본 환경 조명 비활성화/조절 (과도한 그림자 및 반사 방지)
    _configure_default_environment_light(stage)

    cool_white = Gf.Vec3f(0.91, 0.96, 1.0)   # #E8F4FF — fluorescent tone

    # 환경광 (DomeLight) - 전체적인 색조와 ambient 제공 (고정, 따라다니지 않음)
    dome_path = f"{root}/AmbientDome"
    if not stage.GetPrimAtPath(dome_path).IsValid():
        dome = UsdLux.DomeLight.Define(stage, dome_path)
        dome.CreateIntensityAttr(600.0)
        dome.CreateExposureAttr(1.0)
        dome.CreateColorAttr(cool_white)
        # 그림자 비활성화
        dome.GetPrim().CreateAttribute("inputs:shadow:enable", Sdf.ValueTypeNames.Bool).Set(False)

    # 천장 조명 - 실제 양식장처럼 균일한 실내 조명
    ceiling_path = f"{root}/CeilingLight"
    if not stage.GetPrimAtPath(ceiling_path).IsValid():
        ceiling = UsdLux.RectLight.Define(stage, ceiling_path)
        ceiling.CreateIntensityAttr(100.0)
        ceiling.CreateExposureAttr(1.0)
        ceiling.CreateColorTemperatureAttr(500.0)
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
