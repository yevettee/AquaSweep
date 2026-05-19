# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""suction_intake 전방 앵커로 XForm만 끌어당기는 최소 테스트 (RigidBody·충돌 없음)."""

from __future__ import annotations

from typing import Any, Optional

import carb
import numpy as np
from isaacsim.core.prims import XFormPrim
from isaacsim.core.utils.stage import get_current_stage
from pxr import Gf, Usd, UsdGeom

from . import global_variables as gv

_intake_path: str | None = None
_debris_obj: Any = None
_debris_xform: XFormPrim | None = None
_warned_missing: bool = False
_bound_once: bool = False


def reset_simple_suction() -> None:
    global _intake_path, _debris_obj, _debris_xform, _warned_missing, _bound_once
    _intake_path = None
    _debris_obj = None
    _debris_xform = None
    _warned_missing = False
    _bound_once = False


def resolve_suction_intake_path(robot_prim_path: str | None = None) -> str | None:
    """Stage에서 suction_intake prim 경로 탐색."""
    stage = get_current_stage()
    if stage is None:
        return None
    root_path = robot_prim_path or gv.ROBOT_PRIM_PATH
    root = stage.GetPrimAtPath(root_path)
    candidates = [
        gv.SUCTION_INTAKE_PRIM_PATH,
        f"{root_path}/dingo/base_link/suction_intake",
        f"{root_path}/Root/dingo/base_link/suction_intake",
        f"{root_path}/base_link/suction_intake",
    ]
    for path in candidates:
        if stage.GetPrimAtPath(path).IsValid():
            return path
    if root.IsValid():
        for prim in Usd.PrimRange(root):
            if prim.GetName() == "suction_intake":
                return str(prim.GetPath())
    return None


def _intake_world_xf() -> Gf.Matrix4d:
    if _intake_path is None:
        raise RuntimeError("intake path not bound")
    stage = get_current_stage()
    if stage is None:
        raise RuntimeError("no stage")
    prim = stage.GetPrimAtPath(_intake_path)
    if not prim.IsValid():
        raise RuntimeError(f"invalid prim {_intake_path}")
    return UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())


def _anchor_world() -> np.ndarray:
    world_xf = _intake_world_xf()
    offset = Gf.Vec3d(float(gv.SUCTION_FORWARD_OFFSET_M), 0.0, 0.0)
    p = world_xf.Transform(offset)
    return np.array([float(p[0]), float(p[1]), float(p[2])], dtype=np.float64)


def _intake_forward_world() -> np.ndarray:
    world_xf = _intake_world_xf()
    fwd = world_xf.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
    v = np.array([float(fwd[0]), float(fwd[1]), float(fwd[2])], dtype=np.float64)
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        return np.array([1.0, 0.0, 0.0], dtype=np.float64)
    return v / n


def _debris_position() -> np.ndarray:
    if _debris_obj is not None and hasattr(_debris_obj, "get_world_pose"):
        pos, _ = _debris_obj.get_world_pose()
        return np.asarray(pos, dtype=np.float64).reshape(3)
    if _debris_xform is not None:
        pos, _ = _debris_xform.get_world_pose()
        return np.asarray(pos, dtype=np.float64).reshape(3)
    raise RuntimeError("debris not bound")


def _set_debris_position(pos: np.ndarray) -> None:
    p = np.asarray(pos, dtype=np.float64).reshape(3)
    if _debris_obj is not None and hasattr(_debris_obj, "set_world_pose"):
        # sample_ext 와 동일: 위치만 전달
        _debris_obj.set_world_pose(p)
        return
    if _debris_xform is not None:
        _debris_xform.set_world_poses(positions=np.array([p]))
        return
    raise RuntimeError("debris not bound")


def place_test_debris_near_intake() -> None:
    """앵커 직전(흡입 구역 안)에 테스트 debris 배치."""
    if _intake_path is None:
        return
    try:
        anchor = _anchor_world()
        forward = _intake_forward_world()
        spawn = anchor - forward * float(gv.SUCTION_TEST_DEBRIS_SPAWN_BEFORE_ANCHOR_M)
        _set_debris_position(spawn)
    except Exception as exc:
        carb.log_warn(f"[underwater.robot] suction: debris spawn failed ({exc})")


def bind_simple_suction_targets(debris_obj: Any | None = None) -> str | None:
    """Load/Reset 직후 호출. 성공 시 intake prim 경로 반환."""
    global _intake_path, _debris_obj, _debris_xform, _warned_missing, _bound_once

    path = resolve_suction_intake_path()
    if path is None:
        if not _warned_missing:
            carb.log_warn(
                "[underwater.robot] suction: suction_intake prim not found under "
                f"{gv.ROBOT_PRIM_PATH} — USD에 Xform 추가 또는 경로 확인"
            )
            _warned_missing = True
        _intake_path = None
        return None

    _intake_path = path
    _debris_obj = debris_obj
    _debris_xform = None
    if _debris_obj is None:
        _debris_xform = XFormPrim(gv.SUCTION_TEST_DEBRIS_PRIM_PATH)
    _warned_missing = False

    try:
        anchor = _anchor_world()
        pos = _debris_position()
        dist = float(np.linalg.norm(anchor - pos))
        carb.log_info(
            f"[underwater.robot] suction bound intake={path} debris dist_to_anchor={dist:.3f}m "
            f"catch_radius={gv.SUCTION_CATCH_RADIUS_M}m"
        )
        _bound_once = True
    except Exception as exc:
        carb.log_warn(f"[underwater.robot] suction: bind verify failed ({exc})")
        return path

    return path


def _try_lazy_bind() -> bool:
    if _intake_path is not None and (_debris_obj is not None or _debris_xform is not None):
        return True
    try:
        from isaacsim.core.api.world import World

        world = World.instance()
        debris = world.scene.get_object("suction_test_debris")
    except Exception:
        debris = None
    path = bind_simple_suction_targets(debris)
    return path is not None


def tick_simple_suction(dt: float) -> None:
    global _warned_missing
    if not gv.SUCTION_KINEMATIC_ENABLED:
        return
    if not _try_lazy_bind():
        return

    try:
        anchor = _anchor_world()
        pos = _debris_position()
    except Exception as exc:
        if not _warned_missing:
            carb.log_warn(f"[underwater.robot] suction: tick failed ({exc})")
            _warned_missing = True
        return

    delta = anchor - pos
    dist = float(np.linalg.norm(delta))
    if dist > gv.SUCTION_CATCH_RADIUS_M or dist < 1e-5:
        return

    step = min(gv.SUCTION_PULL_SPEED_MPS * float(dt), dist)
    new_pos = pos + (delta / dist) * step
    try:
        _set_debris_position(new_pos)
    except Exception as exc:
        if not _warned_missing:
            carb.log_warn(f"[underwater.robot] suction: set pose failed ({exc})")
            _warned_missing = True
