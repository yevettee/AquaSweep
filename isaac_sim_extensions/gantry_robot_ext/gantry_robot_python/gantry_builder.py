"""겐트리 로봇 USD 빌더 — AquaSweep 통합용.

build(stage, animator)  : 겐트리 prim 생성 + 상태 머신 훅 등록
remove(stage)           : prim 삭제 + 훅 해제
is_built(stage)         : 현재 빌드 여부 확인

상태 머신 흐름:
  IDLE → SEEK_XY → DESCEND → GRAB(흡착 펄스) → ASCEND → DELIVER → DROP → IDLE
"""
from __future__ import annotations
import math
import carb
import omni.kit.commands
import omni.physx as _physx
import omni.timeline
from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf, Sdf, UsdGeom, UsdShade

ROOT      = "/World/GantryRobot"
BIN_PATH  = "/World/DeadFishBin"
CEILING_Z = 7.0
X_HALF    = 19.0
Y_HALF    = 12.0
Z_STROKE  = 5.7
RAIL_GAP  = 28.0

_FISH_STACK_HEIGHT = 0.5   # 수거함 내 상어 한 마리당 적재 높이 (m)

_YCARR_HALF = 0.11
_ZCARR_HALF = 0.10
_ZCARR_GAP  = 0.17

# ZCarriage 월드 Z = _ZCZ_OFFSET - z_param
_ZCZ_OFFSET = CEILING_Z - 0.18 - _YCARR_HALF - _ZCARR_GAP - _ZCARR_HALF  # 6.44

# 흡착 패드 — ZCarriage 하단 오프셋
_PAD_RADIUS  = 0.10   # m
_PAD_HEIGHT  = 0.025  # m
_PAD_OFFSET  = _ZCARR_HALF + _PAD_HEIGHT / 2  # ZCarriage 중심 기준 아래 거리

# 죽은 물고기 수면 부유 높이 ≈ 1.375 m
_GRAB_ZCZ = 1.375
_GRAB_Z   = min(_ZCZ_OFFSET - _GRAB_ZCZ, Z_STROKE)   # z_param ≈ 5.065

# 운반 높이 — 사람이 걸리지 않을 만큼만 올림 (ZCarriage 3 m)
_CARRY_ZCZ = 3.0
_CARRY_Z   = _ZCZ_OFFSET - _CARRY_ZCZ                # z_param ≈ 3.44

# GRAB 흡착 펄스 지속시간 (초)
_GRAB_PULSE_DURATION = 0.4

# 투하 지점
_DROP_X = 12.75
_DROP_Y = 6.0

# 이동 속도
_XY_SPEED = 3.0
_Z_SPEED  = 1.5

# 도착 허용 오차
_XY_TOL = 0.15
_Z_TOL  = 0.08

# 상태값
_IDLE    = "IDLE"
_SEEK_XY = "SEEK_XY"
_DESCEND = "DESCEND"
_GRAB    = "GRAB"
_ASCEND  = "ASCEND"
_DELIVER = "DELIVER"
_DROP_ST = "DROP"

_HOOKS: dict = {"phys": None, "tl": None}
_OPS:   dict = {}
_SHAFT_T = None
_SHAFT_S = None
_ANIMATOR = None
_BIN_COUNT = 0   # 수거함에 쌓인 상어 수

# 흡착 패드 USD 핸들
_SUCTION_T    = None   # translate op (Xform)
_SUCTION_S    = None   # scale op (Xform) — XY 펄스용
_SUCTION_PRIM = None   # Cylinder prim (재질 교체용)
_MAT_SUCTION_OFF = None
_MAT_SUCTION_ON  = None

_SM: dict = {
    "state": _IDLE,
    "x": 0.0, "y": 0.0, "z": _CARRY_Z,
    "idle_wait": 0.0,
    "grab_t": 0.0,
    "grabbed_prim": None,
    "grabbed_t_op": None,
    "grabbed_pool_cx": 0.0,
    "grabbed_pool_cy": 0.0,
    "grabbed_path": "",
    "bin_x": _DROP_X, "bin_y": _DROP_Y, "bin_z": 0.0,
}


# ── 공개 API ──────────────────────────────────────────────────────────────────

def build(stage, animator=None) -> None:
    """겐트리를 스테이지에 빌드하고 상태 머신 훅을 등록한다."""
    global _SHAFT_T, _SHAFT_S, _ANIMATOR, _BIN_COUNT
    global _SUCTION_T, _SUCTION_S, _SUCTION_PRIM, _MAT_SUCTION_OFF, _MAT_SUCTION_ON
    if stage is None:
        carb.log_error("[GantryRobot] stage is None — 빌드 취소")
        return
    _ANIMATOR = animator
    _BIN_COUNT = 0
    _OPS.clear()
    _SHAFT_T = _SHAFT_S = None
    _SUCTION_T = _SUCTION_S = _SUCTION_PRIM = None
    _MAT_SUCTION_OFF = _MAT_SUCTION_ON = None
    _SM.update({
        "state": _IDLE, "x": 0.0, "y": 0.0, "z": _CARRY_Z,
        "idle_wait": 0.0, "grab_t": 0.0,
        "grabbed_prim": None, "grabbed_t_op": None,
        "grabbed_pool_cx": 0.0, "grabbed_pool_cy": 0.0, "grabbed_path": "",
        "bin_x": _DROP_X, "bin_y": _DROP_Y, "bin_z": 0.0,
    })
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
    return stage is not None and stage.GetPrimAtPath(ROOT).IsValid()


# ── prim 생성 ─────────────────────────────────────────────────────────────────

def _build_prims(stage) -> None:
    global _SHAFT_T, _SHAFT_S
    global _SUCTION_T, _SUCTION_S, _SUCTION_PRIM, _MAT_SUCTION_OFF, _MAT_SUCTION_ON

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

    m_steel  = mat("Steel",      (0.62, 0.64, 0.67))
    m_dark   = mat("Dark",       (0.22, 0.23, 0.25), metallic=0.5, roughness=0.4)
    m_slider = mat("Slider",     (0.35, 0.36, 0.40))
    # 흡착 패드: 비활성(어두운 고무) / 활성(주황-적색 가압)
    _MAT_SUCTION_OFF = mat("SuctionOff", (0.12, 0.12, 0.12), metallic=0.0, roughness=0.95)
    _MAT_SUCTION_ON  = mat("SuctionOn",  (0.90, 0.28, 0.04), metallic=0.0, roughness=0.45)

    def cube_mesh(path, scale, pos, material, static=False):
        xf   = UsdGeom.Xform.Define(stage, path)
        t_op = UsdGeom.Xformable(xf).AddTranslateOp()
        t_op.Set(Gf.Vec3d(*pos))
        c = UsdGeom.Cube.Define(stage, path + "/M")
        c.CreateSizeAttr(1.0)
        s_op = UsdGeom.Xformable(c).AddScaleOp()
        s_op.Set(Gf.Vec3f(*scale))
        UsdShade.MaterialBindingAPI(c.GetPrim()).Bind(material)
        return (None, None) if static else (t_op, s_op)

    xrail_len = X_HALF * 2 + 2.0
    cube_mesh(ROOT + "/XRailFront", (xrail_len, 0.18, 0.18),
              (0.0, +RAIL_GAP / 2, CEILING_Z), m_steel, static=True)
    cube_mesh(ROOT + "/XRailBack",  (xrail_len, 0.18, 0.18),
              (0.0, -RAIL_GAP / 2, CEILING_Z), m_steel, static=True)

    _OPS["crossbeam"], _ = cube_mesh(ROOT + "/Crossbeam",
                                     (0.13, RAIL_GAP, 0.13),
                                     (0.0, 0.0, CEILING_Z), m_steel)
    _OPS["sl_f"], _ = cube_mesh(ROOT + "/SliderFront", (0.26, 0.22, 0.20),
                                (0.0, +RAIL_GAP / 2, CEILING_Z), m_slider)
    _OPS["sl_b"], _ = cube_mesh(ROOT + "/SliderBack",  (0.26, 0.22, 0.20),
                                (0.0, -RAIL_GAP / 2, CEILING_Z), m_slider)

    cz = CEILING_Z - 0.18
    _OPS["ycarr"], _ = cube_mesh(ROOT + "/YCarriage", (0.26, 0.26, 0.22),
                                 (0.0, 0.0, cz), m_dark)

    init_shaft_len = _ZCARR_GAP
    init_shaft_cen = cz - _YCARR_HALF - init_shaft_len / 2
    _SHAFT_T, _SHAFT_S = cube_mesh(ROOT + "/ZShaft",
                                   (0.09, 0.09, init_shaft_len),
                                   (0.0, 0.0, init_shaft_cen), m_steel)

    init_zcz = cz - _YCARR_HALF - _ZCARR_GAP - _ZCARR_HALF
    _OPS["zcarr"], _ = cube_mesh(ROOT + "/ZCarriage", (0.22, 0.22, 0.20),
                                 (0.0, 0.0, init_zcz), m_slider)

    # ── 흡착 패드 ────────────────────────────────────────────────────────────
    # Xform: translate + XY scale (펄스 애니메이션용)
    pad_path = ROOT + "/SuctionPad"
    xf_pad = UsdGeom.Xform.Define(stage, pad_path)
    _SUCTION_T = UsdGeom.Xformable(xf_pad).AddTranslateOp()
    _SUCTION_T.Set(Gf.Vec3d(0.0, 0.0, init_zcz - _PAD_OFFSET))
    _SUCTION_S = UsdGeom.Xformable(xf_pad).AddScaleOp()
    _SUCTION_S.Set(Gf.Vec3f(1.0, 1.0, 1.0))

    # 납작한 원반 — Cylinder(axis=Z)
    cyl = UsdGeom.Cylinder.Define(stage, pad_path + "/Disc")
    cyl.CreateRadiusAttr(_PAD_RADIUS)
    cyl.CreateHeightAttr(_PAD_HEIGHT)
    cyl.CreateAxisAttr("Z")
    _SUCTION_PRIM = cyl.GetPrim()
    UsdShade.MaterialBindingAPI(_SUCTION_PRIM).Bind(_MAT_SUCTION_OFF)

    # 외곽 립(lip) — 얇은 링 표현
    lip_path = pad_path + "/Lip"
    xf_lip = UsdGeom.Xform.Define(stage, lip_path)
    lip_t = UsdGeom.Xformable(xf_lip).AddTranslateOp()
    lip_t.Set(Gf.Vec3d(0.0, 0.0, 0.0))   # SuctionPad Xform 기준 로컬 0
    lip_cyl = UsdGeom.Cylinder.Define(stage, lip_path + "/M")
    lip_cyl.CreateRadiusAttr(_PAD_RADIUS + 0.015)
    lip_cyl.CreateHeightAttr(0.008)
    lip_cyl.CreateAxisAttr("Z")
    UsdShade.MaterialBindingAPI(lip_cyl.GetPrim()).Bind(_MAT_SUCTION_OFF)
    _OPS["lip_t"] = lip_t     # 흡착 활성 시 색상 재바인딩을 위해 저장
    _OPS["lip_prim"] = lip_cyl.GetPrim()


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

    # 흡착 패드 — ZCarriage 하단에 고정 추종
    if _SUCTION_T is not None:
        _SUCTION_T.Set(Gf.Vec3d(x, y, zcz - _PAD_OFFSET))


def _set_suction_active(active: bool) -> None:
    """흡착 패드 색상 교체 + 립 색상 교체."""
    if _SUCTION_PRIM is None:
        return
    mat = _MAT_SUCTION_ON if active else _MAT_SUCTION_OFF
    UsdShade.MaterialBindingAPI(_SUCTION_PRIM).Bind(mat)
    lip_prim = _OPS.get("lip_prim")
    if lip_prim is not None:
        UsdShade.MaterialBindingAPI(lip_prim).Bind(mat)


# ── 수거함 위치 ──────────────────────────────────────────────────────────────

def _get_bin_pos(stage) -> tuple[float, float, float]:
    """DeadFishBin 월드 X, Y, Z를 반환. prim이 없으면 기본 투하 지점 사용."""
    prim = stage.GetPrimAtPath(BIN_PATH)
    if prim and prim.IsValid():
        t = UsdGeom.XformCache().GetLocalToWorldTransform(prim).ExtractTranslation()
        x, y, z = float(t[0]), float(t[1]), float(t[2])
        carb.log_warn(f"[GantryRobot] DeadFishBin 위치: ({x:.2f}, {y:.2f}, {z:.2f})")
        return x, y, z
    carb.log_warn(f"[GantryRobot] DeadFishBin prim 없음({BIN_PATH}) — 기본값({_DROP_X}, {_DROP_Y}) 사용")
    return _DROP_X, _DROP_Y, 0.0


# ── 죽은 상어 탐색 ────────────────────────────────────────────────────────────

def _find_dead_sturgeons(stage) -> list[dict]:
    pools_prim = stage.GetPrimAtPath("/World/Pools")
    if not pools_prim or not pools_prim.IsValid():
        return []

    already_grabbed: set[str] = set()
    if _ANIMATOR is not None and hasattr(_ANIMATOR, "grabbed_paths"):
        already_grabbed = _ANIMATOR.grabbed_paths

    xform_cache = UsdGeom.XformCache()
    results: list[dict] = []

    for pool_prim in pools_prim.GetChildren():
        pool_t   = xform_cache.GetLocalToWorldTransform(pool_prim).ExtractTranslation()
        pool_cx, pool_cy = float(pool_t[0]), float(pool_t[1])

        for child in pool_prim.GetChildren():
            if not child.GetName().startswith("Sturgeon"):
                continue
            path_str = str(child.GetPath())
            if path_str in already_grabbed:
                continue
            flip_attr = child.GetAttribute("aquasweep:isFlipped")
            if not (flip_attr and flip_attr.IsValid() and flip_attr.Get()):
                continue

            world_t = xform_cache.GetLocalToWorldTransform(child).ExtractTranslation()

            translate_op = None
            for op in UsdGeom.Xformable(child).GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                    translate_op = op
                    break
            if translate_op is None:
                continue

            results.append({
                "world_x": float(world_t[0]), "world_y": float(world_t[1]),
                "translate_op": translate_op,
                "pool_cx": pool_cx, "pool_cy": pool_cy,
                "path": path_str, "prim": child,
            })

    return results


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _step_toward(current: float, target: float, speed: float, dt: float) -> float:
    diff = target - current
    step = speed * dt
    if abs(diff) <= step:
        return target
    return current + math.copysign(step, diff)


def _carry_sturgeon(x: float, y: float, z: float) -> None:
    t_op = _SM["grabbed_t_op"]
    if t_op is None:
        return
    zcz = _ZCZ_OFFSET - z
    t_op.Set(Gf.Vec3d(
        x - _SM["grabbed_pool_cx"],
        y - _SM["grabbed_pool_cy"],
        zcz,
    ))


# ── 상태 머신 ─────────────────────────────────────────────────────────────────

def _on_step(dt: float) -> None:
    if not _OPS or _SHAFT_T is None:
        return

    sm    = _SM
    state = sm["state"]
    x, y, z = sm["x"], sm["y"], sm["z"]

    # ── IDLE ────────────────────────────────────────────────────────────────
    if state == _IDLE:
        sm["idle_wait"] += dt
        if sm["idle_wait"] < 0.5:
            _update(x, y, z)
            return
        sm["idle_wait"] = 0.0

        stage = get_current_stage()
        if stage is None:
            return
        candidates = _find_dead_sturgeons(stage)
        if not candidates:
            _update(x, y, z)
            return

        best = min(candidates,
                   key=lambda c: (c["world_x"] - x) ** 2 + (c["world_y"] - y) ** 2)
        bx, by, bz = _get_bin_pos(stage)
        sm.update({
            "tx": best["world_x"], "ty": best["world_y"],
            "grabbed_prim":    best["prim"],
            "grabbed_t_op":    best["translate_op"],
            "grabbed_pool_cx": best["pool_cx"],
            "grabbed_pool_cy": best["pool_cy"],
            "grabbed_path":    best["path"],
            "bin_x": bx, "bin_y": by, "bin_z": bz,
            "state": _SEEK_XY,
        })
        carb.log_info(f"[GantryRobot] SEEK_XY → ({best['world_x']:.1f}, {best['world_y']:.1f})")

    # ── SEEK_XY ──────────────────────────────────────────────────────────────
    elif state == _SEEK_XY:
        new_x = _step_toward(x, sm["tx"], _XY_SPEED, dt)
        new_y = _step_toward(y, sm["ty"], _XY_SPEED, dt)
        new_z = _step_toward(z, _CARRY_Z, _Z_SPEED,  dt)
        sm["x"], sm["y"], sm["z"] = new_x, new_y, new_z
        _update(new_x, new_y, new_z)

        if abs(new_x - sm["tx"]) < _XY_TOL and abs(new_y - sm["ty"]) < _XY_TOL:
            sm["state"] = _DESCEND
            carb.log_info(f"[GantryRobot] DESCEND (z_param → {_GRAB_Z:.2f})")

    # ── DESCEND ──────────────────────────────────────────────────────────────
    elif state == _DESCEND:
        new_z = _step_toward(z, _GRAB_Z, _Z_SPEED, dt)
        sm["x"], sm["y"], sm["z"] = x, y, new_z
        _update(x, y, new_z)

        if abs(new_z - _GRAB_Z) < _Z_TOL:
            sm["grab_t"] = 0.0
            sm["state"]  = _GRAB
            carb.log_info("[GantryRobot] GRAB — 흡착 중...")

    # ── GRAB: 흡착 펄스 애니메이션 ──────────────────────────────────────────
    elif state == _GRAB:
        sm["grab_t"] += dt
        t_norm = sm["grab_t"] / _GRAB_PULSE_DURATION  # 0 → 1

        # 처음 진입 시 패드를 주황색으로 전환
        if sm["grab_t"] <= dt + 1e-6:
            _set_suction_active(True)

        # XY 팽창 펄스: sin 반주기 (1.0 → 1.5 → 1.0)
        pulse = 1.0 + 0.5 * math.sin(min(t_norm, 1.0) * math.pi)
        if _SUCTION_S is not None:
            _SUCTION_S.Set(Gf.Vec3f(pulse, pulse, 1.0))

        _update(x, y, z)

        if t_norm >= 1.0:
            # 펄스 끝 — 스케일 복원
            if _SUCTION_S is not None:
                _SUCTION_S.Set(Gf.Vec3f(1.0, 1.0, 1.0))
            if _ANIMATOR is not None and hasattr(_ANIMATOR, "grabbed_paths"):
                _ANIMATOR.grabbed_paths.add(sm["grabbed_path"])
            sm["state"] = _ASCEND
            carb.log_info(f"[GantryRobot] GRAB 완료 — ASCEND")

    # ── ASCEND ───────────────────────────────────────────────────────────────
    elif state == _ASCEND:
        new_z = _step_toward(z, _CARRY_Z, _Z_SPEED, dt)
        sm["x"], sm["y"], sm["z"] = x, y, new_z
        _update(x, y, new_z)
        _carry_sturgeon(x, y, new_z)

        if abs(new_z - _CARRY_Z) < _Z_TOL:
            sm["state"] = _DELIVER
            carb.log_info(f"[GantryRobot] DELIVER → 수거함 ({sm['bin_x']:.1f}, {sm['bin_y']:.1f})")

    # ── DELIVER ──────────────────────────────────────────────────────────────
    elif state == _DELIVER:
        bx, by = sm["bin_x"], sm["bin_y"]
        new_x = _step_toward(x, bx, _XY_SPEED, dt)
        new_y = _step_toward(y, by, _XY_SPEED, dt)
        sm["x"], sm["y"], sm["z"] = new_x, new_y, z
        _update(new_x, new_y, z)
        _carry_sturgeon(new_x, new_y, z)

        if abs(new_x - bx) < _XY_TOL and abs(new_y - by) < _XY_TOL:
            sm["state"] = _DROP_ST
            carb.log_info("[GantryRobot] DROP")

    # ── DROP ─────────────────────────────────────────────────────────────────
    elif state == _DROP_ST:
        global _BIN_COUNT
        _set_suction_active(False)

        t_op = sm["grabbed_t_op"]
        grabbed_prim = sm["grabbed_prim"]
        if grabbed_prim is not None and grabbed_prim.IsValid() and t_op is not None:
            # 수거함 위치에 적재 (pool 로컬 좌표로 변환)
            stack_z = sm["bin_z"] + _BIN_COUNT * _FISH_STACK_HEIGHT
            t_op.Set(Gf.Vec3d(
                sm["bin_x"] - sm["grabbed_pool_cx"],
                sm["bin_y"] - sm["grabbed_pool_cy"],
                stack_z,
            ))
            _BIN_COUNT += 1
            carb.log_info(f"[GantryRobot] 수거함 적재 완료 (누적 {_BIN_COUNT}마리, z={stack_z:.2f})")

        if _ANIMATOR is not None and hasattr(_ANIMATOR, "grabbed_paths"):
            _ANIMATOR.grabbed_paths.discard(sm["grabbed_path"])

        sm.update({
            "grabbed_prim": None, "grabbed_t_op": None, "grabbed_path": "",
            "idle_wait": 0.0, "state": _IDLE,
        })
        carb.log_info("[GantryRobot] IDLE — 다음 상어 탐색")


# ── 타임라인 / physics step 훅 ───────────────────────────────────────────────

def _on_tl(event) -> None:
    play = int(omni.timeline.TimelineEventType.PLAY)
    stop = int(omni.timeline.TimelineEventType.STOP)
    ev   = int(event.type)
    if ev == play and _HOOKS["phys"] is None:
        _SM["idle_wait"] = 0.0
        _HOOKS["phys"] = _physx.get_physx_interface().subscribe_physics_step_events(_on_step)
    elif ev == stop:
        _HOOKS["phys"] = None


def _hook_timeline() -> None:
    if _HOOKS["tl"] is not None:
        return
    stream = omni.timeline.get_timeline_interface().get_timeline_event_stream()
    _HOOKS["tl"] = stream.create_subscription_to_pop(_on_tl)
