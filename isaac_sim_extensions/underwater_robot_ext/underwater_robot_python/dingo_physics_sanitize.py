# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""data/dingo_transformed.usd — VisualWheels 체인 물리만 끔 (계층은 USD 에 맡김)."""

from __future__ import annotations

from typing import Optional

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Sdf, Usd, UsdPhysics

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


def tag_aquasweep_attrs(robot_prim_path: str) -> None:
    """base_link(또는 chassis)에 aquasweep:* 커스텀 속성을 설정한다.

    water_tank_env의 WaterPhysicsApplier가 이 속성이 있는 RigidBodyAPI prim을
    자동 발견하여 매 step 부력/항력/지면효과를 적용한다.
    prepare_dingo_usd_on_stage() 호출 이후에 실행해야 VisualWheels가 이미
    RigidBodyAPI를 잃은 상태에서 base_link를 올바르게 선택한다.
    """
    from .global_variables import ROBOT_HALF_HEIGHT_M, ROBOT_VOLUME_M3

    stage = get_current_stage()
    if not stage:
        carb.log_warn("[dingo_usd] tag_aquasweep: stage 없음")
        return

    # 로봇 루트 아래 전체 트리에서 RigidBodyAPI가 있는 첫 번째 prim 탐색
    # (USD 구조가 /World/Dingo/dingo/base_link처럼 중간 Xform이 있을 수 있음)
    root = stage.GetPrimAtPath(robot_prim_path)
    target: Optional[Usd.Prim] = None
    if root.IsValid():
        for prim in Usd.PrimRange(root):
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                target = prim
                break

    if target is None:
        carb.log_warn(
            f"[dingo_usd] tag_aquasweep: {robot_prim_path} 아래에 RigidBodyAPI prim 없음 — "
            "physics_applier가 로봇을 발견하지 못합니다."
        )
        return

    for attr_name, value in (
        ("aquasweep:volume",      ROBOT_VOLUME_M3),
        ("aquasweep:half_height", ROBOT_HALF_HEIGHT_M),
    ):
        attr = target.GetAttribute(attr_name)
        if not (attr and attr.IsValid()):
            attr = target.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float)
        attr.Set(float(value))

    carb.log_info(
        f"[dingo_usd] aquasweep attrs → {target.GetPath()} "
        f"(volume={ROBOT_VOLUME_M3} m³, half_height={ROBOT_HALF_HEIGHT_M} m)"
    )
