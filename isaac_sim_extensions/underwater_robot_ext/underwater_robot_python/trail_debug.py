# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""JetBot 루트 월드 위치를 빨간 BasisCurves 로 누적 표시 (디버그 전용)."""

from __future__ import annotations

from typing import List

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf, Sdf, UsdGeom, Vt

from . import global_variables as gv

_points: List[Gf.Vec3f] = []
_warned_once: bool = False
_warn_bad_trail_path: bool = False


def _usd_path_ok_for_curve_prim(p: Sdf.Path) -> bool:
    if p.isEmpty:
        return False
    fn = getattr(p, "IsPrimPath", None)
    if callable(fn):
        try:
            return bool(fn())
        except Exception:
            pass
    s = str(p)
    return s.startswith("/") and len(s) > 1


def _curve_path_sdf() -> Sdf.Path | None:
    """BasisCurves용 절대 Sdf 경로. 잘못된 상수 또는 상대 문자열 시 None (Ill-formed SdfPath 경고 방지)."""
    global _warn_bad_trail_path
    raw = (gv.DEBUG_TRAIL_CURVE_PRIM_PATH or "").strip()
    if not raw.startswith("/"):
        if not _warn_bad_trail_path:
            carb.log_warn(
                f"[underwater.robot] trail DEBUG_TRAIL_CURVE_PRIM_PATH는 '/' 로 시작해야 합니다: {raw!r} — 트레일 비활성 처리"
            )
            _warn_bad_trail_path = True
        return None
    p = Sdf.Path(raw)
    if not _usd_path_ok_for_curve_prim(p):
        if not _warn_bad_trail_path:
            carb.log_warn(
                "[underwater.robot] trail: DEBUG_TRAIL_CURVE_PRIM_PATH 가 유효한 절대 prim 경로가 아닙니다 — 트레일 비활성"
            )
            _warn_bad_trail_path = True
        return None
    return p


def reset_center_trail_debug() -> None:
    """포인트 버퍼 비우고 기존 커브 프림 제거 (다음 틱에서 재생성)."""
    global _points
    _points.clear()
    curve_path = _curve_path_sdf()
    if curve_path is None:
        return
    stage = get_current_stage()
    if stage is None:
        return
    prim = stage.GetPrimAtPath(curve_path)
    if prim.IsValid():
        stage.RemovePrim(curve_path)


def tick_center_trail_debug(jetbot) -> None:
    if not gv.DEBUG_CENTER_TRAIL_ENABLED:
        return
    curve_path = _curve_path_sdf()
    if curve_path is None:
        return
    stage = get_current_stage()
    if stage is None:
        return
    try:
        pos, _ = jetbot.get_world_pose()
        p = Gf.Vec3f(float(pos[0]), float(pos[1]), float(pos[2]))
    except Exception as e:
        global _warned_once
        if not _warned_once:
            carb.log_warn(f"[underwater.robot] trail_debug: get_world_pose failed: {e}")
            _warned_once = True
        return

    _points.append(p)
    max_n = int(gv.DEBUG_TRAIL_MAX_POINTS)
    if max_n > 0 and len(_points) > max_n:
        del _points[: len(_points) - max_n]

    _ensure_debug_xform(stage, curve_path)
    _ensure_curve_prim(stage, curve_path)
    _update_curve_geometry(stage, curve_path)


def _ensure_debug_xform(stage, curve_path: Sdf.Path) -> None:
    parent = curve_path.GetParentPath()
    if parent.isEmpty:
        return
    if not stage.GetPrimAtPath(parent).IsValid():
        UsdGeom.Xform.Define(stage, parent)


def _ensure_curve_prim(stage, curve_path: Sdf.Path) -> None:
    if stage.GetPrimAtPath(curve_path).IsValid():
        return
    bc = UsdGeom.BasisCurves.Define(stage, curve_path)
    bc.CreateTypeAttr().Set(UsdGeom.Tokens.linear)
    bc.CreateBasisAttr().Set(UsdGeom.Tokens.bspline)
    bc.CreateWrapAttr().Set(UsdGeom.Tokens.nonperiodic)
    gprim = UsdGeom.Gprim(bc.GetPrim())
    gprim.CreateDisplayColorAttr(Vt.Vec3fArray([Gf.Vec3f(1.0, 0.05, 0.05)]))


def _update_curve_geometry(stage, curve_path: Sdf.Path) -> None:
    prim = stage.GetPrimAtPath(curve_path)
    if not prim.IsValid():
        return
    bc = UsdGeom.BasisCurves(prim)
    if len(_points) < 2:
        z0 = _points[0] if len(_points) == 1 else Gf.Vec3f(0.0, 0.0, 0.0)
        dup = Vt.Vec3fArray([z0, z0])
        bc.CreatePointsAttr(dup)
        bc.CreateCurveVertexCountsAttr(Vt.IntArray([2]))
        w = float(gv.DEBUG_TRAIL_LINE_WIDTH_WORLD)
        bc.CreateWidthsAttr(Vt.FloatArray([w, w]))
        return

    pts = Vt.Vec3fArray(_points)
    bc.CreatePointsAttr(pts)
    bc.CreateCurveVertexCountsAttr(Vt.IntArray([len(_points)]))
    w = float(gv.DEBUG_TRAIL_LINE_WIDTH_WORLD)
    bc.CreateWidthsAttr(Vt.FloatArray([w] * len(_points)))
