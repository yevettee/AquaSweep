"""수조 상단 원형 레일 메시 + 경첩(RevoluteJoint) 빌더.

레일 단면 (pool-local Z 기준):
        ┌────────┐  ← z = TANK_INNER_Z + RAIL_H  (= 1.56 m)
        │  Rail  │  ← 사각 단면 폭 RAIL_W × 높이 RAIL_H
        └────────┘  ← z = TANK_INNER_Z            (= 1.50 m)
        ↑ 수조 벽 상단

경첩 (C-클램프 방식):
  - RailPivot  : 레일 위의 고정 앵커 (plain Xform, body0 미설정 = world anchor)
  - RevoluteJoint(Z축) : 캐리지가 레일을 따라 360° 회전
  - HingeBracket : 캐리지에 붙은 C-클램프 비주얼

캐리지 로컬 프레임 (yaw=angle+180° 회전 후):
  +X → 수조 중심 방향 (inward, 팔이 뻗는 방향)
  -X → 레일 방향 (outward)
  +Z → 위

C-클램프 레일 단면 (캐리지 로컬):
  X = 0       : 레일 중심 (캐리지 위치)
  X = ±RAIL_W/2: 레일 내·외면
  Z = ±RAIL_H/2: 레일 상·하면
"""

import math

from pxr import Gf, Sdf, UsdGeom, UsdPhysics, UsdShade


def _make_cylinder(stage, path: str, center: tuple, radius: float, height: float,
                   axis: str = "Z", collision: bool = False) -> UsdGeom.Cylinder:
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateRadiusAttr(radius)
    cyl.CreateHeightAttr(height)
    cyl.CreateAxisAttr(axis)
    xf = UsdGeom.Xformable(cyl)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*center))
    if collision:
        UsdPhysics.CollisionAPI.Apply(cyl.GetPrim())
    return cyl

from .global_variables import (
    TANK_INNER_Z, TANK_RADIUS, WALL_THICKNESS,
    RAIL_W, RAIL_H, RAIL_CENTER_R, RAIL_MOUNT_Z,
    SCRAPER_ATTACH_LINK, SCRAPER_BLADE_WIDTH, SCRAPER_BLADE_HEIGHT, SCRAPER_BLADE_THICK,
)

# ── 레일 메시 파라미터 ────────────────────────────────────────────────────────
_RAIL_SEGMENTS = 128    # 원주 분할 수

_RAIL_Z_BOT = TANK_INNER_Z
_RAIL_Z_TOP = TANK_INNER_Z + RAIL_H

# ── 재질 색상 ─────────────────────────────────────────────────────────────────
_RAIL_COLOR     = (0.40, 0.40, 0.43)   # 철제 레일 — 어두운 회색
_BRACKET_COLOR  = (0.55, 0.55, 0.58)   # 경첩 브라켓 — 밝은 회색
_ROUGHNESS      = 0.25
_METALLIC       = 0.85


# ── 재질 헬퍼 ─────────────────────────────────────────────────────────────────

def _ensure_materials_scope(stage, pool_path: str) -> None:
    mat_scope = f"{pool_path}/Materials"
    if not stage.GetPrimAtPath(mat_scope).IsValid():
        stage.DefinePrim(mat_scope, "Scope")


def _bind_material(stage, prim, mat_path: str,
                   color: tuple, roughness: float = 0.25, metallic: float = 0.85) -> None:
    material = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, mat_path + "/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness",    Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("metallic",     Sdf.ValueTypeNames.Float).Set(metallic)
    shader.CreateInput("opacity",      Sdf.ValueTypeNames.Float).Set(1.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI(prim).Bind(material)


# ── 박스 프리미티브 헬퍼 ──────────────────────────────────────────────────────

def _make_box(stage, path: str, center: tuple, size: tuple,
              color: tuple, collision: bool = False) -> UsdGeom.Cube:
    """UsdGeom.Cube 기반 박스 생성. center·size 단위 m."""
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    xf = UsdGeom.Xformable(cube)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*center))
    xf.AddScaleOp().Set(Gf.Vec3f(*size))
    if collision:
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
    return cube


# ── 레일 링 메시 ──────────────────────────────────────────────────────────────

def build_rail_ring(stage, pool_path: str, pool_idx: int) -> None:
    """pool_path 하위에 사각 단면 원형 레일 메시를 생성한다 (pool-local 좌표).

    Idempotent — 이미 존재하면 스킵.
    """
    rail_path = f"{pool_path}/Rail"
    if stage.GetPrimAtPath(rail_path).IsValid():
        return

    N    = _RAIL_SEGMENTS
    r_in  = RAIL_CENTER_R - RAIL_W * 0.5
    r_out = RAIL_CENTER_R + RAIL_W * 0.5

    # 정점: 세그먼트 i → 4 코너 (inner-bot, outer-bot, outer-top, inner-top)
    points = []
    for i in range(N):
        t = 2.0 * math.pi * i / N
        c, s = math.cos(t), math.sin(t)
        points.append(Gf.Vec3f(r_in  * c, r_in  * s, _RAIL_Z_BOT))
        points.append(Gf.Vec3f(r_out * c, r_out * s, _RAIL_Z_BOT))
        points.append(Gf.Vec3f(r_out * c, r_out * s, _RAIL_Z_TOP))
        points.append(Gf.Vec3f(r_in  * c, r_in  * s, _RAIL_Z_TOP))

    # 4각형 면: bottom / outer / top / inner
    fvc, fvi = [], []
    for i in range(N):
        j = (i + 1) % N
        b, n = i * 4, j * 4
        fvc.append(4); fvi.extend([b+0, n+0, n+1, b+1])
        fvc.append(4); fvi.extend([b+1, n+1, n+2, b+2])
        fvc.append(4); fvi.extend([b+2, n+2, n+3, b+3])
        fvc.append(4); fvi.extend([b+3, n+3, n+0, b+0])

    mesh = UsdGeom.Mesh.Define(stage, rail_path)
    mesh.CreatePointsAttr().Set(points)
    mesh.CreateFaceVertexCountsAttr().Set(fvc)
    mesh.CreateFaceVertexIndicesAttr().Set(fvi)
    mesh.CreateDoubleSidedAttr().Set(False)
    mesh.CreateSubdivisionSchemeAttr().Set("none")
    UsdGeom.Xformable(mesh).ClearXformOpOrder()

    _ensure_materials_scope(stage, pool_path)
    _bind_material(stage, mesh.GetPrim(),
                   f"{pool_path}/Materials/RailMat_{pool_idx}",
                   _RAIL_COLOR)

    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI(mesh.GetPrim()).CreateApproximationAttr().Set("convexDecomposition")


# ── C-클램프 경첩 브라켓 ──────────────────────────────────────────────────────

def build_hinge_bracket(stage, carriage_path: str, pool_idx: int) -> None:
    """캐리지에 붙는 C-클램프 경첩 브라켓 비주얼을 생성한다.

    캐리지 로컬 프레임 (yaw=angle+180° 상태):
      -X 방향 = 레일 방향 (outward)
      레일 단면은 캐리지 로컬 x=0 중심, z=±RAIL_H/2 범위

    브라켓 구성:
      ┌─── 뒷판  ─────────────────────────────────┐ (레일 외면에 밀착)
      │  ┌──── 상단 클램프 팔 ────────────────┐   │
      │  │         [레일 단면]                │   │
      │  └──── 하단 클램프 팔 ────────────────┘   │
      └───────────────────────────────────────────┘
    """
    bracket_root = f"{carriage_path}/HingeBracket"
    if stage.GetPrimAtPath(bracket_root).IsValid():
        return

    stage.DefinePrim(bracket_root, "Xform")

    hw = RAIL_W * 0.5   # = 0.04 m  레일 반폭
    hh = RAIL_H * 0.5   # = 0.03 m  레일 반높이
    thick = 0.010       # 판 두께
    arm_len = hw + 0.015  # 클램프 팔 길이 (레일 내면까지 + 여유)
    y_half = 0.055      # 브라켓 Y 방향 반폭 (레일 tangent)

    pool_path = "/".join(carriage_path.split("/")[:-2])  # Pool_n 경로
    _ensure_materials_scope(stage, pool_path)
    mat_path = f"{pool_path}/Materials/BracketMat_{pool_idx}"

    def _box(name, center, size):
        cube = _make_box(stage, f"{bracket_root}/{name}", center, size, _BRACKET_COLOR)
        _bind_material(stage, cube.GetPrim(), mat_path + f"_{name}", _BRACKET_COLOR)
        return cube

    # 1. 뒷판: 레일 외면(-x = -hw)에 밀착, Y·Z 방향으로 넓게
    _box("BackPlate",
         center=(-hw - thick * 0.5, 0.0, 0.0),
         size=(thick, y_half * 2, (hh + thick) * 2))

    # 2. 상단 클램프 팔: 레일 상면(z = +hh) 위로 걸침
    _box("TopArm",
         center=(-hw + arm_len * 0.5 - hw, 0.0, hh + thick * 0.5),
         size=(arm_len, y_half * 2, thick))

    # 3. 하단 클램프 팔: 레일 하면(z = -hh) 아래로 걸침
    _box("BottomArm",
         center=(-hw + arm_len * 0.5 - hw, 0.0, -hh - thick * 0.5),
         size=(arm_len, y_half * 2, thick))

    # 4. 내측 잠금판: 레일 내면(+x = +hw)에서 꽉 죄는 판
    _box("InnerLock",
         center=(hw + thick * 0.5, 0.0, 0.0),
         size=(thick, y_half * 2, hh * 2))


# ── RevoluteJoint 경첩 조인트 ────────────────────────────────────────────────

def build_revolute_joint(stage, pool_path: str, pool_idx: int) -> str:
    """레일 회전 제어 — kinematic Xform 방식 사용.

    Carriage 안에 M1013 ArticulationRootAPI가 있어 외부 RevoluteJoint와
    body 충돌이 발생하므로 Joint를 생성하지 않는다.
    캐리지 이동은 scenario.set_rail_angle()의 kinematic Xform 설정으로 처리.
    """
    return ""


# ── Toolspar 스타일 스크레이퍼 ───────────────────────────────────────────────
# link_6 로컬 프레임: +Z = 벽 방향 (날 끝), +Y = 수평, +X = 수직
#
# 구조:
#   -Z: 검정 고무 캡 + 딤플 그립 핸들
#    0: 크롬 칼라 (link_6 플랜지)
#   +Z: 짧은 넥 → 부채꼴 알루미늄 플레이트(넥 쪽 좁고 날 쪽 넓음) → 쐐기 블레이드

_BLACK   = (0.06, 0.06, 0.06)   # 검정 고무 핸들
_CHROME  = (0.78, 0.78, 0.81)   # 크롬 금속
_SILVER  = (0.74, 0.74, 0.76)   # 알루미늄 헤드 플레이트
_BLADE_C = (0.88, 0.88, 0.90)   # 광택 블레이드 (은색)


def build_scraper_tool(stage, carriage_path: str, pool_idx: int, articulation=None) -> None:
    """link_6 엔드 이펙터에 Toolspar 스타일 스크레이퍼를 장착한다.

    구조 (+Z = 벽 방향):
      ●   ← 검정 고무 캡
      ║║║ ← 딤플 그립 (검정 고무, 6개 텍스처 링)
      ╠   ← 크롬 칼라 (광택)
      ║   ← 넥 (크롬)
      ◁▷  ← 부채꼴 알루미늄 플레이트 (트라페조이드, 넥 쪽 좁음 → 날 쪽 넓음)
      ○   ← 검정 조임 노브 (플레이트 면에 돌출)
      ═   ← 쐐기형 블레이드 (은색, collision ON)
    """
    import carb

    candidates = [SCRAPER_ATTACH_LINK, "m1013/tool0", "m1013/link_6", "m1013/link_5"]
    attach_path = None
    for name in candidates:
        path = f"{carriage_path}/{name}"
        if stage.GetPrimAtPath(path).IsValid():
            attach_path = path
            carb.log_warn(f"[rail_robot] pool_{pool_idx} 스크레이퍼 장착: {path}")
            break
    if attach_path is None:
        carb.log_warn(f"[rail_robot] pool_{pool_idx} 링크 탐색 실패 — carriage fallback")
        attach_path = carriage_path

    tool_root = f"{attach_path}/ScraperTool"
    if stage.GetPrimAtPath(tool_root).IsValid():
        return

    stage.DefinePrim(tool_root, "Xform")
    pool_path = "/".join(carriage_path.split("/")[:-2])
    _ensure_materials_scope(stage, pool_path)

    def _cyl(name, center, radius, height, color, roughness=0.35, metallic=0.05, axis="Z"):
        p = _make_cylinder(stage, f"{tool_root}/{name}", center, radius, height, axis)
        _bind_material(stage, p.GetPrim(),
                       f"{pool_path}/Materials/Sc{name}_{pool_idx}",
                       color, roughness, metallic)

    # ── 1. 검정 고무 캡 (둥근 끝) ─────────────────────────────────────────────
    _cyl("Cap", center=(0.0, 0.0, -0.192), radius=0.023, height=0.028,
         color=_BLACK, roughness=0.65, metallic=0.0)

    # ── 2. 그립 핸들 본체 (검정 고무) ────────────────────────────────────────
    _cyl("Grip", center=(0.0, 0.0, -0.100), radius=0.018, height=0.150,
         color=_BLACK, roughness=0.75, metallic=0.0)

    # 딤플 밴드 — 그립 텍스처 표현 (6개 링, 미세 돌출)
    for i, gz in enumerate([-0.168, -0.138, -0.108, -0.078, -0.048, -0.018]):
        _cyl(f"Ring{i}", center=(0.0, 0.0, gz), radius=0.0205, height=0.006,
             color=_BLACK, roughness=0.80, metallic=0.0)

    # ── 3. 크롬 칼라 (손잡이→헤드, 광택 금속) ────────────────────────────────
    _cyl("Collar", center=(0.0, 0.0, -0.006), radius=0.026, height=0.022,
         color=_CHROME, roughness=0.06, metallic=0.96)

    # ── 4. 넥 30cm (크롬, 칼라→플레이트 연결) ───────────────────────────────
    # 칼라 끝 z ≈ 0.005 → 넥 중심 = 0.005 + 0.150 = 0.155, 끝 = 0.305
    _cyl("Neck", center=(0.0, 0.0, 0.155), radius=0.012, height=0.300,
         color=_CHROME, roughness=0.10, metallic=0.90)

    # ── 5. 부채꼴 알루미늄 플레이트 (트라페조이드 메시) ───────────────────────
    # 좌표계: +Z = 벽(날 방향), +Y = 수평, +X = 수직
    # 플레이트는 X 방향으로 얇고, Z 방향으로 깊이가 있으며,
    # Y 방향으로 넥 쪽(z_near)은 좁고 날 쪽(z_far)은 넓다.
    z_near  = 0.307   # 플레이트 시작 (넥 끝, 칼라 z0.005 + 넥 0.300 + 2mm 여유)
    z_far   = 0.363   # 플레이트 끝 (날 부착 면, 56mm 깊이 유지)
    hx      = 0.004   # 판 두께 반값 (총 8mm)
    hy_near = 0.022   # 넥 쪽 Y 반폭 (4.4cm)
    hy_far  = 0.180   # 날 쪽 Y 반폭 (36cm)

    # 트라페조이드 프리즘 8 정점 (+X/-X 면 각 4개)
    plate_pts = [
        Gf.Vec3f(+hx, -hy_near, z_near),  # 0
        Gf.Vec3f(+hx, +hy_near, z_near),  # 1
        Gf.Vec3f(+hx, -hy_far,  z_far),   # 2
        Gf.Vec3f(+hx, +hy_far,  z_far),   # 3
        Gf.Vec3f(-hx, -hy_near, z_near),  # 4
        Gf.Vec3f(-hx, +hy_near, z_near),  # 5
        Gf.Vec3f(-hx, -hy_far,  z_far),   # 6
        Gf.Vec3f(-hx, +hy_far,  z_far),   # 7
    ]
    plate_fvc = [4, 4, 4, 4, 4, 4]
    plate_fvi = [
        0, 2, 3, 1,   # +X 면 (한쪽 평면)
        4, 5, 7, 6,   # -X 면 (반대 평면)
        0, 1, 5, 4,   # z_near 면 (좁은 끝, 넥 쪽)
        2, 6, 7, 3,   # z_far 면 (넓은 끝, 날 쪽)
        0, 4, 6, 2,   # -Y 경사 측면
        1, 3, 7, 5,   # +Y 경사 측면
    ]
    plate_mesh = UsdGeom.Mesh.Define(stage, f"{tool_root}/Plate")
    plate_mesh.CreatePointsAttr().Set(plate_pts)
    plate_mesh.CreateFaceVertexCountsAttr().Set(plate_fvc)
    plate_mesh.CreateFaceVertexIndicesAttr().Set(plate_fvi)
    plate_mesh.CreateDoubleSidedAttr().Set(False)
    plate_mesh.CreateSubdivisionSchemeAttr().Set("none")
    UsdGeom.Xformable(plate_mesh).ClearXformOpOrder()
    _bind_material(stage, plate_mesh.GetPrim(),
                   f"{pool_path}/Materials/ScPlate_{pool_idx}",
                   _SILVER, 0.15, 0.88)

    # ── 6. 검정 조임 노브 (플레이트 +X 면에 돌출) ────────────────────────────
    knob_z = z_near + (z_far - z_near) * 0.28   # 플레이트 앞쪽 28% 위치
    _cyl("Knob", center=(hx + 0.006, 0.0, knob_z), radius=0.013, height=0.012,
         color=_BLACK, roughness=0.60, metallic=0.0, axis="X")

    # ── 7. 쐐기형 블레이드 (날 끝으로 수렴, collision ON) ────────────────────
    # 플레이트 z_far 면에서 z_tip 으로 X 두께 ±hx_b → ±t 로 수렴
    z_b  = z_far
    z_t  = z_far + 0.015   # 15mm 돌출
    hx_b = hx + 0.002      # 블레이드 기저 X 반값 (판보다 약간 큼)
    hy_b = hy_far + 0.005  # 블레이드 Y 반폭
    t    = 0.0015          # 날 끝 X 반두께

    blade_pts = [
        Gf.Vec3f(+hx_b, -hy_b, z_b),  # 0
        Gf.Vec3f(+hx_b, +hy_b, z_b),  # 1
        Gf.Vec3f(-hx_b, -hy_b, z_b),  # 2
        Gf.Vec3f(-hx_b, +hy_b, z_b),  # 3
        Gf.Vec3f(+t,    -hy_b, z_t),  # 4
        Gf.Vec3f(+t,    +hy_b, z_t),  # 5
        Gf.Vec3f(-t,    -hy_b, z_t),  # 6
        Gf.Vec3f(-t,    +hy_b, z_t),  # 7
    ]
    blade_fvc = [4, 4, 4, 4, 4, 4]
    blade_fvi = [
        2, 0, 1, 3,   # 뒷면 (플레이트 부착)
        0, 4, 5, 1,   # +X 경사면
        2, 3, 7, 6,   # -X 경사면
        4, 6, 7, 5,   # 날 끝 면 (얇음)
        0, 2, 6, 4,   # -Y 캡
        1, 5, 7, 3,   # +Y 캡
    ]
    blade_mesh = UsdGeom.Mesh.Define(stage, f"{tool_root}/Blade")
    blade_mesh.CreatePointsAttr().Set(blade_pts)
    blade_mesh.CreateFaceVertexCountsAttr().Set(blade_fvc)
    blade_mesh.CreateFaceVertexIndicesAttr().Set(blade_fvi)
    blade_mesh.CreateDoubleSidedAttr().Set(False)
    blade_mesh.CreateSubdivisionSchemeAttr().Set("none")
    UsdGeom.Xformable(blade_mesh).ClearXformOpOrder()
    UsdPhysics.CollisionAPI.Apply(blade_mesh.GetPrim())
    _bind_material(stage, blade_mesh.GetPrim(),
                   f"{pool_path}/Materials/ScBlade_{pool_idx}",
                   _BLADE_C, 0.08, 0.92)


# ── 일괄 빌더 ─────────────────────────────────────────────────────────────────

def build_rails(stage, pools_root: str = "/World/Pools") -> None:
    """pools_root 아래 모든 Pool_n 에 레일 링을 추가한다. Idempotent."""
    pools_prim = stage.GetPrimAtPath(pools_root)
    if not pools_prim or not pools_prim.IsValid():
        return
    for pool_prim in sorted(pools_prim.GetChildren(), key=lambda p: str(p.GetPath())):
        pool_path = str(pool_prim.GetPath())
        name = pool_prim.GetName()
        idx = int(name.split("_")[-1]) if "_" in name else 0
        build_rail_ring(stage, pool_path, idx)
