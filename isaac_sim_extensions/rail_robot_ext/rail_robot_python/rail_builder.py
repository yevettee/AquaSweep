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

from .global_variables import (
    TANK_INNER_Z, TANK_RADIUS, WALL_THICKNESS,
    RAIL_W, RAIL_H, RAIL_CENTER_R, RAIL_MOUNT_Z,
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
    """레일 중심축(Z)을 pivot으로 하는 RevoluteJoint를 생성한다.

    구조:
      world (body0 미설정 = world anchor)
          ↕  RevoluteJoint (Z축)
      RailRobot/Carriage  (pool-local RAIL_CENTER_R 위치, dynamic rigid body)

    body0를 static/kinematic RigidBody로 지정하면 articulation body1과 함께
    "cannot create joint between static bodies" 오류가 발생하므로 body0는 미설정.
    DriveAPI 실패 시 scenario.set_rail_angle() kinematic fallback이 동작한다.

    Returns:
        joint_prim_path (str)  — 없으면 빈 문자열
    """
    joint_path  = f"{pool_path}/RailHinge"
    pivot_path  = f"{pool_path}/RailPivot"
    carriage_path = f"{pool_path}/RailRobot/Carriage"

    if stage.GetPrimAtPath(joint_path).IsValid():
        return joint_path

    if not stage.GetPrimAtPath(carriage_path).IsValid():
        return ""

    # ── RailPivot: pool-local 원점(z=RAIL_MOUNT_Z), 순수 Xform (world anchor) ─
    # RigidBodyAPI를 붙이지 않음 — kinematic body + articulation 조합이면
    # PhysX가 "cannot create joint between static bodies" 오류를 냄.
    # body0Rel 미설정 → PhysX가 world 고정으로 처리함.
    pivot_prim = stage.DefinePrim(pivot_path, "Xform")
    xf = UsdGeom.Xformable(pivot_prim)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, RAIL_MOUNT_Z))

    # ── RevoluteJoint ─────────────────────────────────────────────────────────
    joint = UsdPhysics.RevoluteJoint.Define(stage, joint_path)
    joint.CreateAxisAttr("Z")

    # body0 미설정 = world anchor, body1 = Carriage (회전체)
    joint.CreateBody1Rel().SetTargets([carriage_path])

    # Joint frame 위치:
    #   body0 (world): pool-local 원점에서 z=RAIL_MOUNT_Z
    #   body1 local: 캐리지 중심에서 레일 반경만큼 pivot 방향
    #                yaw=0 일 때 캐리지는 world (+RAIL_CENTER_R, 0, RAIL_MOUNT_Z)
    #                → body1 local offset = (-RAIL_CENTER_R, 0, 0)
    joint.CreateLocalPos0Attr().Set(Gf.Vec3f(0.0, 0.0, RAIL_MOUNT_Z))
    joint.CreateLocalPos1Attr().Set(Gf.Vec3f(-RAIL_CENTER_R, 0.0, 0.0))
    joint.CreateLocalRot0Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    joint.CreateLocalRot1Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))

    # 회전 한계 없음 (360° 자유)
    joint.CreateLowerLimitAttr(-1e10)
    joint.CreateUpperLimitAttr( 1e10)

    # ── Angular Position Drive (각도 목표값으로 제어) ──────────────────────────
    try:
        drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
        drive.CreateTypeAttr("position")
        drive.CreateTargetPositionAttr(0.0)   # 초기 각도 0°
        drive.CreateStiffnessAttr(1e5)        # 위치 강성
        drive.CreateDampingAttr(1e3)          # 댐핑
        drive.CreateMaxForceAttr(5e3)
    except Exception:
        pass  # DriveAPI 미지원 환경에서도 조인트 자체는 유지

    return joint_path


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
