"""Scene-building helpers: tank floor + tube-mesh wall, water body, lighting.

Used by UIBuilder._setup_scene. Assumes Isaac Sim is already running (so
``pxr`` is importable).

수조 재질 — FRP (유리섬유강화플라스틱)
  내면 색상: 밝은 청록색  (0.55, 0.88, 0.82)
  외면 색상: 파란색       (0.14, 0.35, 0.70)
  재질 특성: 불투명에 가깝고 (opacity ≈ 0.80–0.92), 겔코트 마감으로
             유리보다 거칠고 금속보다 매끄러운 중간 roughness (0.25–0.35)
"""
import math

from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics, UsdShade

from . import params

# ── FRP 수조 색상 상수 ─────────────────────────────────────────────────────────
_FRP_INTERIOR = (0.55, 0.88, 0.82)   # 밝은 청록색 (수조 내면·바닥)
_FRP_EXTERIOR = (0.14, 0.35, 0.70)   # 파란색      (수조 외면)
# FRP roughness: 겔코트 마감 ≈ 0.25–0.35 (유리 0.05~0.15보다 거침)
_FRP_ROUGHNESS_INT = 0.22
_FRP_ROUGHNESS_EXT = 0.32


def enable_gpu_dynamics(stage) -> None:
    """GPU particle / OceanSim effects require GPU dynamics.

    World API와 USD 속성을 모두 설정한다.

    중요: physx plugin은 UsdPhysics.Scene prim의 USD 속성을 직접 읽는다.
    World API 호출만으로는 USD prim이 갱신되지 않으므로 반드시 두 경로를 모두 실행해야 한다.
    또한 CreateXxxAttr(value)는 속성이 이미 존재하면 value를 무시하므로
    .Set(True)를 반드시 별도 호출해야 기존 False 값을 덮어쓸 수 있다.
    """
    # 1) World API — 런타임 physics context 갱신 (단독으로는 USD 속성 미보장)
    try:
        from isaacsim.core.api.world import World
        world = World.instance()
        if world is not None:
            world.get_physics_context().enable_gpu_dynamics(True)
    except Exception:
        pass

    # 2) USD 속성 직접 설정 — physx plugin이 prim 속성을 읽으므로 필수
    try:
        from pxr import PhysxSchema
    except ImportError:
        return

    found = False
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.Scene):
            api = PhysxSchema.PhysxSceneAPI.Apply(prim)
            api.CreateEnableGPUDynamicsAttr().Set(True)   # .Set() 필수
            api.CreateBroadphaseTypeAttr().Set("MBP")
            api.CreateSolverTypeAttr().Set("TGS")
            found = True

    if not found:
        scene_prim = UsdPhysics.Scene.Define(stage, Sdf.Path("/World/PhysicsScene"))
        api = PhysxSchema.PhysxSceneAPI.Apply(scene_prim.GetPrim())
        api.CreateEnableGPUDynamicsAttr().Set(True)
        api.CreateBroadphaseTypeAttr().Set("MBP")
        api.CreateSolverTypeAttr().Set("TGS")

WALL_SEGMENTS = 64


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


def _make_cylinder(stage, path, center, height, radius, color, opacity=1.0,
                   collision=True, roughness=0.4, clearcoat=0.0,
                   clearcoat_roughness=0.1, ior=1.5, emissive=(0.0, 0.0, 0.0)):
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateAxisAttr().Set("Z")
    cyl.CreateHeightAttr().Set(height)
    cyl.CreateRadiusAttr().Set(radius)

    xform = UsdGeom.Xformable(cyl)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*center))

    _bind_preview_material(stage, cyl.GetPrim(), path + "_Mat", color, opacity,
                           roughness, clearcoat, clearcoat_roughness, ior, emissive)

    if collision:
        UsdPhysics.CollisionAPI.Apply(cyl.GetPrim())
    return cyl


def _build_solid_cylinder_mesh(stage, path, center, height, radius,
                                color, opacity=1.0, n_segments=WALL_SEGMENTS,
                                collision=False, roughness=0.4, clearcoat=0.0,
                                clearcoat_roughness=0.1, ior=1.5,
                                emissive=(0.0, 0.0, 0.0)):
    """Solid cylinder as a tessellated mesh (smoother than UsdGeom.Cylinder
    primitive, which RTX draws as a low-poly silhouette).
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
    """원기둥 측면 메시 (캡 없음, DoubleSided).

    내면 오버레이처럼 기존 튜브 위에 얇게 씌우는 순수 시각용 메시.
    충돌 처리는 _build_tube_mesh 가 담당하므로 collision 속성을 붙이지 않는다.
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


def build_tank(stage, root="/World/Tank"):
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)
    r  = params.TANK_RADIUS
    h  = params.TANK_INNER_Z
    t  = params.WALL_THICKNESS
    z0 = params.TANK_FLOOR_Z

    # ── 바닥: FRP 내면 색상 (밝은 청록색) ──────────────────────────────────────
    # FRP 겔코트 마감 → opacity 0.92 (거의 불투명), roughness 낮게 (광택)
    _build_solid_cylinder_mesh(stage, f"{root}/Floor",
                               center=(0, 0, z0 - t / 2),
                               height=t, radius=r + t,
                               color=_FRP_INTERIOR, opacity=0.92,
                               collision=True,
                               roughness=_FRP_ROUGHNESS_INT)

    # ── 벽 본체: 충돌 포함, 외면 파란색 FRP ────────────────────────────────────
    # DoubleSided=True 이므로 양쪽에서 파란색이 보임; 내면 오버레이로 덮어씀
    # opacity=0.78: 시뮬레이션에서 로봇을 볼 수 있도록 약간 투시
    _build_tube_mesh(stage, f"{root}/Wall",
                     center=(0, 0, z0),
                     height=h, inner_radius=r, outer_radius=r + t,
                     color=_FRP_EXTERIOR, opacity=0.78,
                     roughness=_FRP_ROUGHNESS_EXT)

    # ── 벽 내면 오버레이: 밝은 청록색 (수조 안에서 보이는 색) ──────────────────
    # 벽 내반경 r 바로 안쪽(r-0.001)에 캡 없는 측면 메시를 씌워
    # 내부 시점에서는 청록색, 외부 시점에서는 외면의 파란색이 우세하게 보임
    _build_lateral_cylinder(stage, f"{root}/WallInterior",
                            center=(0.0, 0.0, z0 + h / 2.0),
                            height=h,
                            radius=r - 0.001,
                            color=_FRP_INTERIOR, opacity=0.88,
                            roughness=_FRP_ROUGHNESS_INT)


def build_water(stage, root="/World/Water"):
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)
    inset = 0.01
    r = params.TANK_RADIUS - inset
    body_height = params.WATER_LEVEL
    body_center_z = params.TANK_FLOOR_Z + body_height / 2

    _build_solid_cylinder_mesh(stage, f"{root}/Body",
                               center=(0, 0, body_center_z),
                               height=body_height, radius=r,
                               color=(0.06, 0.28, 0.38),
                               opacity=0.72,
                               collision=False,
                               roughness=0.55,
                               clearcoat=0.05,
                               clearcoat_roughness=0.4,
                               ior=1.33)


def build_water_surface(stage, root="/World/Water"):
    """와류 애니메이션용 수면 디스크 메시를 생성한다.

    ring × segment 분할된 평탄한 원형 메시를 수면 높이에 배치한다.
    꼭짓점 Z는 WaterSurfaceAnimator가 매 step 갱신한다.
    """
    surface_path = f"{root}/Surface"
    if stage.GetPrimAtPath(surface_path).IsValid():
        return

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
                           color=(0.07, 0.20, 0.30),
                           opacity=0.78,
                           roughness=0.70,
                           clearcoat=0.0,
                           clearcoat_roughness=0.0,
                           ior=1.33)


def add_lighting(stage, root="/World/Lighting"):
    """Indoor fish-farm lighting set: cool-white key + ceiling fluorescent
    rect light + subtle teal underwater accent."""
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)

    cool_white = Gf.Vec3f(0.91, 0.96, 1.0)   # #E8F4FF — fluorescent tone

    # 1) Cool-white key light. DistantLight gives even fill across the tank.
    sun = UsdLux.DistantLight.Define(stage, f"{root}/Sun")
    sun.CreateIntensityAttr(800.0)
    sun.CreateColorAttr(cool_white)
    UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-45.0, 0.0, 30.0))

    # 2) Ceiling fluorescent fixture — a wide rect light placed above the tank.
    ceiling = UsdLux.RectLight.Define(stage, f"{root}/CeilingLight")
    ceiling.CreateIntensityAttr(2500.0)
    ceiling.CreateColorAttr(cool_white)
    ceiling.CreateWidthAttr(2.5)
    ceiling.CreateHeightAttr(2.5)
    UsdGeom.Xformable(ceiling).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 3.0))



