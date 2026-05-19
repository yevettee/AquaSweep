"""Scene-building helpers: tank floor + tube-mesh wall, water body, lighting.

Used by UIBuilder._setup_scene. Assumes Isaac Sim is already running (so
``pxr`` is importable).
"""
import math

from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics, UsdShade

from . import params


def enable_gpu_dynamics(stage) -> None:
    """OceanSim particle effects require GPU dynamics.

    Tries the World physics context API first (works at runtime).
    Falls back to USD attribute on every UsdPhysics.Scene prim.
    """
    # World API: 런타임에도 즉시 반영됨
    try:
        from isaacsim.core.api.world import World
        world = World.instance()
        if world is not None:
            world.get_physics_context().enable_gpu_dynamics(True)
            return
    except Exception:
        pass

    # Fallback: USD 속성 직접 설정 (다음 simulation 재시작 시 반영)
    try:
        from pxr import PhysxSchema
    except ImportError:
        return

    found = False
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.Scene):
            api = PhysxSchema.PhysxSceneAPI.Apply(prim)
            api.CreateEnableGPUDynamicsAttr(True)
            found = True

    if not found:
        scene_prim = UsdPhysics.Scene.Define(stage, Sdf.Path("/physicsScene"))
        api = PhysxSchema.PhysxSceneAPI.Apply(scene_prim.GetPrim())
        api.CreateEnableGPUDynamicsAttr(True)

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


def build_tank(stage, root="/World/Tank"):
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)
    r = params.TANK_RADIUS
    h = params.TANK_INNER_Z
    t = params.WALL_THICKNESS
    z0 = params.TANK_FLOOR_Z

    glass = (0.85, 0.92, 0.95)
    glass_opacity = 0.15

    _build_solid_cylinder_mesh(stage, f"{root}/Floor",
                               center=(0, 0, z0 - t / 2),
                               height=t, radius=r + t,
                               color=glass, opacity=glass_opacity,
                               collision=True)
    _build_tube_mesh(stage, f"{root}/Wall",
                     center=(0, 0, z0),
                     height=h, inner_radius=r, outer_radius=r + t,
                     color=glass, opacity=glass_opacity)


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
                               color=(0.10, 0.50, 0.40),
                               opacity=0.35,
                               collision=False,
                               roughness=0.16,
                               clearcoat=0.3,
                               clearcoat_roughness=0.1,
                               ior=1.33)


def add_lighting(stage, root="/World/Lighting"):
    """Indoor fish-farm lighting set: cool-white key + ceiling fluorescent
    rect light + subtle teal underwater accent."""
    if stage.GetPrimAtPath(root).IsValid():
        return
    UsdGeom.Xform.Define(stage, root)

    cool_white = Gf.Vec3f(0.91, 0.96, 1.0)   # #E8F4FF — fluorescent tone
    teal = Gf.Vec3f(0.00, 0.81, 0.67)        # #00CFAA — underwater accent

    # 1) Cool-white key light. DistantLight gives even fill across the tank.
    sun = UsdLux.DistantLight.Define(stage, f"{root}/Sun")
    sun.CreateIntensityAttr(800.0)
    sun.CreateColorAttr(cool_white)
    UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(-45.0, 0.0, 30.0))

    # 2) Ceiling fluorescent fixture — a wide rect light placed above the tank.
    ceiling = UsdLux.RectLight.Define(stage, f"{root}/CeilingLight")
    ceiling.CreateIntensityAttr(5000.0)
    ceiling.CreateColorAttr(cool_white)
    ceiling.CreateWidthAttr(2.5)
    ceiling.CreateHeightAttr(2.5)
    UsdGeom.Xformable(ceiling).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 3.0))

    # 3) Teal underwater accent — submerged sphere light at tank center to
    #    enhance the volumetric look without blowing out exposure.
    accent = UsdLux.SphereLight.Define(stage, f"{root}/UnderwaterAccent")
    accent.CreateIntensityAttr(300.0)
    accent.CreateColorAttr(teal)
    accent.CreateRadiusAttr(0.1)
    UsdGeom.Xformable(accent).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.3))


