# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Sketchfab 등 외부 트랙 메시를 JetBot 차동 휠 링크 아래에 시각 전용으로 붙입니다.

Blender 등에서 좌·우 트랙을 분리해 `track_left.usd` / `track_right.usd` 로 내보낸 뒤
`data/track_visuals/` 에 두거나, 환경 변수 AQUASWEEP_TRACK_LEFT_USD / AQUASWEEP_TRACK_RIGHT_USD
로 절대 경로를 지정합니다.

한 파일에 두 루트 프림이 있으면 `AQUASWEEP_TRACK_USD` 만 지정할 수 있으며,
`AQUASWEEP_TRACK_LEFT_PRIM_PATH` / `AQUASWEEP_TRACK_RIGHT_PRIM_PATH` 가 비어 있으면
각각 `/TrackLeft`, `/TrackRight` 를 참조합니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from .global_variables import TRACK_VISUAL_CHILD_NAME


def _usd_path_is_prim_path_for_geometry(p: Sdf.Path) -> bool:
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


def _ref_prim_from_env(key: str, default_abs: str) -> Sdf.Path:
    """USD 참조용 prim 경로 — 상대 문자열이면 선행 '/' 추가해 Ill-formed SdfPath 경고를 피합니다."""
    raw = os.environ.get(key, "").strip()
    if not raw:
        return Sdf.Path(default_abs)
    if not raw.startswith("/"):
        raw = "/" + raw.lstrip("/")
    p = Sdf.Path(raw)
    if not _usd_path_is_prim_path_for_geometry(p):
        carb.log_warn(f"[track_visual] {key}={raw!r} 는 유효한 prim 경로가 아닙니다. {default_abs} 사용.")
        return Sdf.Path(default_abs)
    return p


def _extension_track_vis_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "track_visuals"


def _resolve_track_asset_paths() -> Tuple[
    Optional[str], Optional[str], Optional[Sdf.Path], Optional[Sdf.Path]
]:
    """Returns (left_usd, right_usd, left_ref_prim, right_ref_prim). ref prim optional for whole-file ref."""
    single = os.environ.get("AQUASWEEP_TRACK_USD", "").strip()
    left_env = os.environ.get("AQUASWEEP_TRACK_LEFT_USD", "").strip()
    right_env = os.environ.get("AQUASWEEP_TRACK_RIGHT_USD", "").strip()

    d = _extension_track_vis_dir()
    default_left = d / "track_left.usd"
    default_right = d / "track_right.usd"

    if single:
        lp = _ref_prim_from_env("AQUASWEEP_TRACK_LEFT_PRIM_PATH", "/TrackLeft")
        rp = _ref_prim_from_env("AQUASWEEP_TRACK_RIGHT_PRIM_PATH", "/TrackRight")
        return single, single, lp, rp

    left_usd = left_env or (str(default_left) if default_left.is_file() else "")
    right_usd = right_env or (str(default_right) if default_right.is_file() else "")
    if not left_usd or not right_usd:
        return None, None, None, None
    return left_usd, right_usd, None, None


def _find_wheel_link_paths(stage: Usd.Stage, robot_root: str) -> Tuple[Optional[Sdf.Path], Optional[Sdf.Path]]:
    """JetBot USD에서 회전하는 휠 링크 경로 탐색 (조인트 프림은 제외)."""
    root = stage.GetPrimAtPath(robot_root)
    if not root.IsValid():
        return None, None

    exact_pairs = [
        ("left_wheel_link", "right_wheel_link"),
        ("left_wheel", "right_wheel"),
    ]
    for ln, rn in exact_pairs:
        lp = rp = None
        for prim in Usd.PrimRange(root):
            name = prim.GetName()
            if name == ln:
                lp = prim.GetPath()
            elif name == rn:
                rp = prim.GetPath()
        if lp and rp:
            return lp, rp

    left_candidates = []
    right_candidates = []
    for prim in Usd.PrimRange(root):
        name_lower = prim.GetName().lower()
        if "joint" in name_lower:
            continue
        if "wheel" not in name_lower:
            continue
        if "left" in name_lower or name_lower.startswith("l_"):
            left_candidates.append(prim.GetPath())
        elif "right" in name_lower or name_lower.startswith("r_"):
            right_candidates.append(prim.GetPath())

    if len(left_candidates) == 1 and len(right_candidates) == 1:
        return left_candidates[0], right_candidates[0]

    return None, None


def _strip_physics_under(root: Usd.Prim) -> None:
    """레퍼런스된 트랙에 실수로 붙은 rigid body / collision 을 최대한 제거."""
    for prim in Usd.PrimRange(root):
        try:
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                prim.RemoveAPI(UsdPhysics.RigidBodyAPI)
            if prim.HasAPI(UsdPhysics.CollisionAPI):
                prim.RemoveAPI(UsdPhysics.CollisionAPI)
        except Exception:
            pass
        try:
            if hasattr(UsdPhysics, "MeshCollisionAPI") and prim.HasAPI(UsdPhysics.MeshCollisionAPI):
                prim.RemoveAPI(UsdPhysics.MeshCollisionAPI)
        except Exception:
            pass


def _define_reference_xform(
    stage: Usd.Stage,
    parent_path: Sdf.Path,
    child_name: str,
    asset_path: str,
    ref_prim: Optional[Sdf.Path],
) -> Usd.Prim:
    path = parent_path.AppendChild(child_name)
    xform = UsdGeom.Xform.Define(stage, path)
    ref_api = xform.GetPrim().GetReferences()
    ref_api.ClearReferences()
    if ref_prim is not None and not ref_prim.isEmpty:
        ref_api.AddReference(asset_path, ref_prim)
    else:
        ref_api.AddReference(asset_path)
    return xform.GetPrim()


def attach_track_visuals_to_jetbot(robot_prim_path: str = "/World/Jetbot") -> None:
    """DifferentialController 가 돌리는 휠 링크 아래에 트랙 비주얼 USD 를 붙입니다."""
    left_usd, right_usd, left_ref, right_ref = _resolve_track_asset_paths()
    if not left_usd or not right_usd:
        carb.log_info(
            "[track_visual] 트랙 비주얼 USD 가 없습니다. "
            f"{_extension_track_vis_dir()}/track_left.usd · track_right.usd 저장 또는 AQUASWEEP_TRACK_* 환경 변수를 설정하세요."
        )
        return

    stage = get_current_stage()
    if not stage:
        carb.log_warn("[track_visual] 현재 스테이지가 없습니다.")
        return

    left_link, right_link = _find_wheel_link_paths(stage, robot_prim_path)
    if not left_link or not right_link:
        carb.log_warn(
            f"[track_visual] 휠 링크를 찾지 못했습니다 (root={robot_prim_path}). "
            "Stage에서 left_wheel / right_wheel 등 링크 이름을 확인하세요."
        )
        return

    try:
        l_prim = _define_reference_xform(stage, left_link, TRACK_VISUAL_CHILD_NAME, left_usd, left_ref)
        r_prim = _define_reference_xform(stage, right_link, TRACK_VISUAL_CHILD_NAME, right_usd, right_ref)
        _strip_physics_under(l_prim)
        _strip_physics_under(r_prim)
    except Exception as exc:
        carb.log_error(f"[track_visual] 레퍼런스 추가 실패: {exc}")
        return

    carb.log_info(
        f"[track_visual] 트랙 비주얼 연결: L={left_usd} @ {left_link} , R={right_usd} @ {right_link}"
    )
