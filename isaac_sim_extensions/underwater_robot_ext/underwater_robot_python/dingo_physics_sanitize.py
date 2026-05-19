# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""data/dingo_transformed.usd — VisualWheels 체인 물리만 끔 (계층은 USD 에 맡김)."""

from __future__ import annotations

from typing import Optional

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Usd, UsdPhysics

from . import global_variables as gv

VISUAL_WHEELS_PRIM_NAME = "VisualWheels"
# underwater_robot_camera_v1.usd 휠 링크 MassAPI (플레이스홀더)
DINGO_WHEEL_LINK_MASS_KG = 0.111


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


def _find_base_link_prim(robot_root: Usd.Prim) -> Optional[Usd.Prim]:
    if not robot_root.IsValid():
        return None
    stage = robot_root.GetStage()
    root_path = str(robot_root.GetPath())
    for suffix in ("base_link", "dingo/base_link"):
        prim = stage.GetPrimAtPath(f"{root_path}/{suffix}")
        if prim.IsValid():
            return prim
    for prim in Usd.PrimRange(robot_root):
        if prim.GetName() == "base_link" and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            return prim
    return None


def _apply_robot_mass_override(robot_root: Usd.Prim) -> None:
    """USD 플레이스홀더(~0.22 kg) → global_variables ROBOT_MASS_KG 에 맞춤."""
    base = _find_base_link_prim(robot_root)
    if base is None or not base.IsValid():
        carb.log_warn("[dingo_usd] base_link not found — skip mass override")
        return

    target_total = float(gv.ROBOT_MASS_KG)
    wheel_mass = float(DINGO_WHEEL_LINK_MASS_KG)
    base_mass = max(target_total - 2.0 * wheel_mass, 1.0)

    mass_api = UsdPhysics.MassAPI.Apply(base) if not base.HasAPI(UsdPhysics.MassAPI) else UsdPhysics.MassAPI(base)
    mass_api.CreateMassAttr().Set(base_mass)
    carb.log_info(
        f"[dingo_usd] mass override base_link={base_mass:.2f} kg "
        f"(wheels ~{2*wheel_mass:.2f} kg, target total ~{target_total:.1f} kg)"
    )


def prepare_dingo_usd_on_stage(robot_prim_path: str) -> None:
    """Load 후 1회: 질량 보정, VisualWheels 서브트리 물리 비활성.

    VisualWheels → base_link 계층은 underwater_robot_camera_v1.usd 에서 직접 편집합니다.
    """
    stage = get_current_stage()
    if not stage:
        carb.log_warn("[dingo_usd] no stage")
        return

    root = stage.GetPrimAtPath(robot_prim_path)
    if not root.IsValid():
        carb.log_warn(f"[dingo_usd] robot root invalid: {robot_prim_path}")
        return

    _apply_robot_mass_override(root)

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
