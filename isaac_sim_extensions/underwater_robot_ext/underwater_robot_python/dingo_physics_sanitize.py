# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""data/dingo_transformed.usd — VisualWheels 체인 물리만 끔 (계층은 USD 에 맡김)."""

from __future__ import annotations

from typing import Optional

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Usd, UsdPhysics

VISUAL_WHEELS_PRIM_NAME = "VisualWheels"


def _find_visual_wheels_prim(robot_root: Usd.Prim) -> Optional[Usd.Prim]:
    if not robot_root.IsValid():
        return None
    if robot_root.GetName() == VISUAL_WHEELS_PRIM_NAME:
        return robot_root
    for prim in Usd.PrimRange(robot_root):
        if prim.GetName() == VISUAL_WHEELS_PRIM_NAME:
            return prim
    return None


def _strip_physics_prim(prim: Usd.Prim) -> None:
    if prim.IsA(UsdPhysics.Joint):
        prim.SetActive(False)
        return
    try:
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            prim.RemoveAPI(UsdPhysics.RigidBodyAPI)
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            prim.RemoveAPI(UsdPhysics.CollisionAPI)
        if hasattr(UsdPhysics, "MeshCollisionAPI") and prim.HasAPI(UsdPhysics.MeshCollisionAPI):
            prim.RemoveAPI(UsdPhysics.MeshCollisionAPI)
    except Exception:
        pass
    try:
        if prim.HasAPI(UsdPhysics.MassAPI):
            prim.RemoveAPI(UsdPhysics.MassAPI)
    except Exception:
        pass


def prepare_dingo_usd_on_stage(robot_prim_path: str) -> None:
    """Load 후 1회: VisualWheels 서브트리 조인트·강체·충돌 비활성.

    VisualWheels → base_link 계층은 dingo_transformed.usd 에서 직접 편집합니다.
    """
    stage = get_current_stage()
    if not stage:
        carb.log_warn("[dingo_usd] no stage")
        return

    root = stage.GetPrimAtPath(robot_prim_path)
    if not root.IsValid():
        carb.log_warn(f"[dingo_usd] robot root invalid: {robot_prim_path}")
        return

    visual = _find_visual_wheels_prim(root)
    if visual is None or not visual.IsValid():
        carb.log_info("[dingo_usd] VisualWheels not found — skip physics strip")
        return

    parent = visual.GetParent()
    if parent.IsValid() and parent.GetName() == "base_link":
        carb.log_info(f"[dingo_usd] VisualWheels under base_link @ {visual.GetPath()}")
    else:
        carb.log_warn(
            f"[dingo_usd] VisualWheels parent is {parent.GetPath() if parent.IsValid() else '?'}"
            " — base_link 아래에 두면 차체 회전과 같이 움직입니다."
        )

    joint_count = 0
    body_count = 0
    for prim in Usd.PrimRange(visual):
        if prim.IsA(UsdPhysics.Joint):
            joint_count += 1
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            body_count += 1
        _strip_physics_prim(prim)

    carb.log_info(
        f"[dingo_usd] VisualWheels physics off (~{joint_count} joints, ~{body_count} bodies)"
    )
