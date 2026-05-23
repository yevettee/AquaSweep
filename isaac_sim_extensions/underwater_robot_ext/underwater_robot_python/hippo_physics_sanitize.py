# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""data/hippo_v1.usd — VisualWheels 체인 물리만 끔 (계층은 USD 에 맡김).

Hippo 는 Clearpath Dingo-D 플랫폼을 기반으로 우리가 개조한 수중 청소 로봇입니다.
이 모듈은 USD 안에 박혀 있는 정적 부속물 (VisualWheels 체인) 의 물리를 끄는 역할.
"""

from __future__ import annotations

from typing import Optional

import carb
from isaacsim.core.utils.stage import get_current_stage
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

VISUAL_WHEELS_PRIM_NAME = "VisualWheels"


def _fix_wheel_collision(root: Usd.Prim) -> None:
    """Fix wheel collision: ensure CollisionAPI is applied and axis is correct.

    1. Apply CollisionAPI if missing (required for physics collision detection)
    2. Change cylinder axis from Z to Y for stable floor contact
    """
    wheel_link_names = ("left_wheel_link", "right_wheel_link")
    axis_fixed = 0
    collision_api_added = 0
    
    for prim in Usd.PrimRange(root):
        if prim.GetName() == "collisions" and prim.GetTypeName() == "Cylinder":
            parent = prim.GetParent()
            if parent.IsValid() and parent.GetName() in wheel_link_names:
                cyl = UsdGeom.Cylinder(prim)
                
                # 1. Ensure CollisionAPI is applied
                if not prim.HasAPI(UsdPhysics.CollisionAPI):
                    UsdPhysics.CollisionAPI.Apply(prim)
                    collision_api_added += 1
                    carb.log_info(f"[hippo_usd] CollisionAPI applied: {prim.GetPath()}")
                
                # 2. Fix cylinder axis
                current_axis = cyl.GetAxisAttr().Get()
                if current_axis != "Y":
                    cyl.GetAxisAttr().Set("Y")
                    axis_fixed += 1
                    carb.log_info(f"[hippo_usd] wheel collision axis {current_axis} -> Y: {prim.GetPath()}")
    
    if collision_api_added > 0:
        carb.log_info(f"[hippo_usd] added CollisionAPI to {collision_api_added} wheel prims")
    if axis_fixed > 0:
        carb.log_info(f"[hippo_usd] fixed {axis_fixed} wheel collision axes")


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


def prepare_hippo_usd_on_stage(robot_prim_path: str) -> None:
    """Load 후 1회: VisualWheels 서브트리 조인트·강체·충돌 비활성.

    VisualWheels → base_link 계층은 hippo_v1.usd 에서 직접 편집합니다.
    hippo_v1.usd는 realsense / lidar / viewport gizmo가 이미 진짜로 제거된
    flatten 결과이므로 런타임에 추가로 deactivate 할 prim이 없습니다.
    """
    stage = get_current_stage()
    if not stage:
        carb.log_warn("[hippo_usd] no stage")
        return

    root = stage.GetPrimAtPath(robot_prim_path)
    # #region agent log
    import json, time
    _log_path = "/home/woody/AquaSweep/.cursor/debug-acdc9b.log"
    _all_children = []
    _joint_info = []
    if root and root.IsValid():
        for p in Usd.PrimRange(root):
            _all_children.append(str(p.GetPath()))
            if p.IsA(UsdPhysics.Joint):
                _joint_info.append({"path": str(p.GetPath()), "name": p.GetName()})
            if len(_all_children) > 50: break
    with open(_log_path, "a") as _f: _f.write(json.dumps({"sessionId":"acdc9b","hypothesisId":"D","location":"hippo_physics_sanitize.py:prepare_hippo_usd_on_stage","message":"robot prim tree and joints","data":{"robot_prim_path":robot_prim_path,"root_valid":root.IsValid() if root else False,"prim_count":len(_all_children),"joint_info":_joint_info[:10]},"timestamp":int(time.time()*1000)})+"\n")
    # #endregion
    if not root.IsValid():
        carb.log_warn(f"[hippo_usd] robot root invalid: {robot_prim_path}")
        return

    _fix_wheel_collision(root)

    visual = _find_visual_wheels_prim(root)
    # #region agent log
    with open(_log_path, "a") as _f: _f.write(json.dumps({"sessionId":"acdc9b","hypothesisId":"D2","location":"hippo_physics_sanitize.py:prepare_hippo_usd_on_stage","message":"VisualWheels check","data":{"robot_prim_path":robot_prim_path,"visual_found":visual is not None and visual.IsValid() if visual else False,"visual_path":str(visual.GetPath()) if visual and visual.IsValid() else None},"timestamp":int(time.time()*1000)})+"\n")
    # #endregion
    if visual is None or not visual.IsValid():
        carb.log_info("[hippo_usd] VisualWheels not found — skip physics strip")
        return

    # Clear selection before modifying prims to avoid Isaac Sim UI errors
    # (omni.physxsupportui raises "Accessed invalid null prim" when selection
    # references prims that are being deactivated)
    try:
        import omni.usd
        ctx = omni.usd.get_context()
        if ctx:
            ctx.get_selection().clear_selected_prim_paths()
    except Exception:
        pass

    parent = visual.GetParent()
    if parent.IsValid() and parent.GetName() == "base_link":
        carb.log_info(f"[hippo_usd] VisualWheels under base_link @ {visual.GetPath()}")
    else:
        carb.log_warn(
            f"[hippo_usd] VisualWheels parent is {parent.GetPath() if parent.IsValid() else '?'}"
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
        f"[hippo_usd] VisualWheels physics off (~{joint_count} joints, ~{body_count} bodies)"
    )


def tag_aquasweep_attrs(robot_prim_path: str) -> None:
    """base_link(또는 chassis)에 aquasweep:* 커스텀 속성을 설정한다.

    water_tank_env의 WaterPhysicsApplier가 이 속성이 있는 RigidBodyAPI prim을
    자동 발견하여 매 step 부력/항력/지면효과를 적용한다.
    prepare_hippo_usd_on_stage() 호출 이후에 실행해야 VisualWheels가 이미
    RigidBodyAPI를 잃은 상태에서 base_link를 올바르게 선택한다.
    """
    from .global_variables import (
        ROBOT_HALF_HEIGHT_M, ROBOT_VOLUME_M3,
        DRAG_LINEAR_XY, DRAG_LINEAR_Z, DRAG_ANGULAR,
    )

    stage = get_current_stage()
    if not stage:
        carb.log_warn("[hippo_usd] tag_aquasweep: stage 없음")
        return

    # 로봇 루트 아래 전체 트리에서 RigidBodyAPI가 있는 첫 번째 prim 탐색
    # (USD 구조가 /World/Pools/Pool_N/Robot/hippo/base_link처럼 중간 Xform이 있을 수 있음)
    root = stage.GetPrimAtPath(robot_prim_path)
    target: Optional[Usd.Prim] = None
    if root.IsValid():
        for prim in Usd.PrimRange(root):
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                target = prim
                break

    if target is None:
        carb.log_warn(
            f"[hippo_usd] tag_aquasweep: {robot_prim_path} 아래에 RigidBodyAPI prim 없음 — "
            "physics_applier가 로봇을 발견하지 못합니다."
        )
        return

    for attr_name, value in (
        ("aquasweep:volume",      ROBOT_VOLUME_M3),
        ("aquasweep:half_height", ROBOT_HALF_HEIGHT_M),
        ("aquasweep:cd_linear",   DRAG_LINEAR_XY),
        ("aquasweep:cd_angular",  DRAG_ANGULAR),
    ):
        attr = target.GetAttribute(attr_name)
        if not (attr and attr.IsValid()):
            attr = target.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float)
        attr.Set(float(value))

    carb.log_info(
        f"[hippo_usd] aquasweep attrs → {target.GetPath()} "
        f"(volume={ROBOT_VOLUME_M3} m³, half_height={ROBOT_HALF_HEIGHT_M} m)"
    )
