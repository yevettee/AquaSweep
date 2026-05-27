"""겐트리 로봇 USD 빌더 — AquaSweep 통합용.

build(stage)  : 겐트리 prim 생성 + physics step 훅 등록
remove(stage) : prim 삭제 + 훅 해제
is_built(stage): 현재 빌드 여부 확인
"""
from __future__ import annotations
import math
import carb
import omni.kit.commands
import omni.physx as _physx
import omni.timeline
from pxr import Gf, Sdf, UsdGeom, UsdShade

ROOT      = "/World/GantryRobot"
CEILING_Z = 7.0    # 레일 설치 높이 — 7 m (충분한 사람 통행 공간 확보)
X_HALF    = 19.0   # X 이동 범위 ±19 m (양식장 전체 커버)
Y_HALF    = 12.0   # Y 캐리지 이동 범위 ±12 m
Z_STROKE  = 5.7    # Z 하강 거리 (7.0 → 1.3 m, 수면 1.35 m 도달)
RAIL_GAP  = 28.0   # X레일 간격 Y = ±14 m (장축 벽 안쪽)

_YCARR_HALF = 0.11
_ZCARR_HALF = 0.10
_ZCARR_GAP  = 0.17

_HOOKS: dict = {"phys": None, "tl": None, "time": 0.0}
_OPS:   dict = {}
_SHAFT_T = None
_SHAFT_S = None


# ── 공개 API ──────────────────────────────────────────────────────────────────

def build(stage) -> None:
    """겐트리를 스테이지에 빌드하고 타임라인 훅을 등록한다."""
    global _SHAFT_T, _SHAFT_S
    if stage is None:
        carb.log_error("[GantryRobot] stage is None — 빌드 취소")
        return
    _OPS.clear()
    _SHAFT_T = None
    _SHAFT_S = None
    _build_prims(stage)
    _hook_timeline()
    carb.log_info("[GantryRobot] 빌드 완료 — PLAY 누르면 동작")


def remove(stage) -> None:
    """겐트리 prim을 삭제하고 훅을 해제한다."""
    _HOOKS["phys"] = None
    if stage is not None and stage.GetPrimAtPath(ROOT).IsValid():
        omni.kit.commands.execute("DeletePrims", paths=[Sdf.Path(ROOT)])
    _OPS.clear()
    carb.log_info("[GantryRobot] 제거됨")


def is_built(stage) -> bool:
    """현재 스테이지에 겐트리 prim이 존재하는지 확인."""
    return stage is not None and stage.GetPrimAtPath(ROOT).IsValid()


# ── prim 생성 ─────────────────────────────────────────────────────────────────

def _build_prims(stage) -> None:
    global _SHAFT_T, _SHAFT_S

    if stage.GetPrimAtPath(ROOT).IsValid():
        omni.kit.commands.execute("DeletePrims", paths=[Sdf.Path(ROOT)])

    UsdGeom.Xform.Define(stage, ROOT)

    def mat(name, rgb, metallic=0.75, roughness=0.25):
        p = f"{ROOT}/Mtl/{name}"
        if not stage.GetPrimAtPath(p).IsValid():
            m  = UsdShade.Material.Define(stage, p)
            sh = UsdShade.Shader.Define(stage, p + "/S")
            sh.CreateIdAttr("UsdPreviewSurface")
            sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
            sh.CreateInput("metallic",     Sdf.ValueTypeNames.Float).Set(metallic)
            sh.CreateInput("roughness",    Sdf.ValueTypeNames.Float).Set(roughness)
            m.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        return UsdShade.Material(stage.GetPrimAtPath(p))

    STEEL  = (0.62, 0.64, 0.67)
    DARK   = (0.22, 0.23, 0.25)
    SLIDER = (0.35, 0.36, 0.40)

    m_steel  = mat("Steel",  STEEL)
    m_dark   = mat("Dark",   DARK,   metallic=0.5, roughness=0.4)
    m_slider = mat("Slider", SLIDER)

    def mesh(path, scale, pos, material, static=False):
        xf   = UsdGeom.Xform.Define(stage, path)
        t_op = UsdGeom.Xformable(xf).AddTranslateOp()
        t_op.Set(Gf.Vec3d(*pos))
        cube = UsdGeom.Cube.Define(stage, path + "/M")
        cube.CreateSizeAttr(1.0)
        s_op = UsdGeom.Xformable(cube).AddScaleOp()
        s_op.Set(Gf.Vec3f(*scale))
        UsdShade.MaterialBindingAPI(cube.GetPrim()).Bind(material)
        return (None, None) if static else (t_op, s_op)

    xrail_len = X_HALF * 2 + 2.0   # 40 m

    # 천장 고정 X레일 두 개
    mesh(ROOT + "/XRailFront", (xrail_len, 0.18, 0.18),
         (0.0, +RAIL_GAP / 2, CEILING_Z), m_steel, static=True)
    mesh(ROOT + "/XRailBack",  (xrail_len, 0.18, 0.18),
         (0.0, -RAIL_GAP / 2, CEILING_Z), m_steel, static=True)


    # 움직이는 파트
    _OPS["crossbeam"], _ = mesh(ROOT + "/Crossbeam",
                                (0.13, RAIL_GAP, 0.13),
                                (0.0, 0.0, CEILING_Z), m_steel)
    _OPS["sl_f"], _ = mesh(ROOT + "/SliderFront", (0.26, 0.22, 0.20),
                           (0.0, +RAIL_GAP / 2, CEILING_Z), m_slider)
    _OPS["sl_b"], _ = mesh(ROOT + "/SliderBack",  (0.26, 0.22, 0.20),
                           (0.0, -RAIL_GAP / 2, CEILING_Z), m_slider)

    cz = CEILING_Z - 0.18
    _OPS["ycarr"], _ = mesh(ROOT + "/YCarriage", (0.26, 0.26, 0.22),
                            (0.0, 0.0, cz), m_dark)

    init_shaft_len = _ZCARR_GAP
    init_shaft_cen = cz - _YCARR_HALF - init_shaft_len / 2
    _SHAFT_T, _SHAFT_S = mesh(ROOT + "/ZShaft",
                              (0.09, 0.09, init_shaft_len),
                              (0.0, 0.0, init_shaft_cen), m_steel)

    init_zcz = cz - _YCARR_HALF - _ZCARR_GAP - _ZCARR_HALF
    _OPS["zcarr"], _ = mesh(ROOT + "/ZCarriage", (0.22, 0.22, 0.20),
                            (0.0, 0.0, init_zcz), m_slider)


# ── 위치/스케일 업데이트 ──────────────────────────────────────────────────────

def _update(x: float, y: float, z: float) -> None:
    if not _OPS or _SHAFT_T is None:
        return

    bz  = CEILING_Z
    cz  = CEILING_Z - 0.18

    shaft_top = cz  - _YCARR_HALF
    zcz       = cz  - _YCARR_HALF - _ZCARR_GAP - _ZCARR_HALF - z
    shaft_bot = zcz + _ZCARR_HALF
    shaft_len = max(shaft_top - shaft_bot, 0.04)
    shaft_cen = (shaft_top + shaft_bot) / 2

    _OPS["crossbeam"].Set(Gf.Vec3d(x,  0.0,           bz))
    _OPS["sl_f"].Set(     Gf.Vec3d(x, +RAIL_GAP / 2,  bz))
    _OPS["sl_b"].Set(     Gf.Vec3d(x, -RAIL_GAP / 2,  bz))
    _OPS["ycarr"].Set(    Gf.Vec3d(x,  y,             cz))
    _SHAFT_T.Set(         Gf.Vec3d(x,  y,             shaft_cen))
    _SHAFT_S.Set(         Gf.Vec3f(0.09, 0.09, shaft_len))
    _OPS["zcarr"].Set(    Gf.Vec3d(x,  y,             zcz))


# ── 타임라인 / physics step 훅 ───────────────────────────────────────────────

def _on_step(dt: float) -> None:
    _HOOKS["time"] += dt
    t = _HOOKS["time"]
    x = X_HALF * 0.6 * math.sin(t * 0.5)
    y = Y_HALF * 0.7 * math.sin(t * 0.7 + 1.0)
    z = (Z_STROKE / 2) * (1.0 + math.sin(t * 0.4 + 2.0))
    _update(x, y, z)


def _on_tl(event) -> None:
    play = int(omni.timeline.TimelineEventType.PLAY)
    stop = int(omni.timeline.TimelineEventType.STOP)
    ev   = int(event.type)
    if ev == play and _HOOKS["phys"] is None:
        _HOOKS["time"] = 0.0
        _HOOKS["phys"] = _physx.get_physx_interface().subscribe_physics_step_events(_on_step)
    elif ev == stop:
        _HOOKS["phys"] = None


def _hook_timeline() -> None:
    if _HOOKS["tl"] is not None:
        return
    stream = omni.timeline.get_timeline_interface().get_timeline_event_stream()
    _HOOKS["tl"] = stream.create_subscription_to_pop(_on_tl)
