# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""타임라인 재생 중 매 물리 스텝 JetBot 루트에 부력·선형 항력 근사를 적용합니다."""

from __future__ import annotations

import carb
import numpy as np

from . import global_variables as gv

_warned_force_path: bool = False
_warned_bad_velocity: bool = False
_rigid_force_view = None
_rigid_force_path: str | None = None


def _linear_velocity_world_xyz(jetbot) -> np.ndarray:
    """루트 선속도 (3,) — 불안정 시뮬/API에서 길이가 3이 아니면 항력용 0."""
    global _warned_bad_velocity
    try:
        raw = jetbot.get_linear_velocity()
        v = np.asarray(raw, dtype=np.float64).reshape(-1)
    except Exception:
        v = np.array([], dtype=np.float64)

    if v.size >= 3:
        return v[:3].copy()

    if v.size != 0 and not _warned_bad_velocity:
        carb.log_warn(
            f"[underwater.robot] fluid_forces: get_linear_velocity length={v.size}, "
            "expected 3 — using zeros for drag."
        )
        _warned_bad_velocity = True
    return np.zeros(3, dtype=np.float64)


def apply_default_fluid_forces(jetbot, dt: float) -> None:
    """jetbot: World.scene 에 등록된 WheeledRobot (또는 Articulation 래퍼)."""
    del dt
    if not gv.DEFAULT_FLUID_FORCES_ENABLED:
        return

    mass = _resolve_mass_kg(jetbot)
    v = _linear_velocity_world_xyz(jetbot)

    f_buoy = np.array([0.0, 0.0, gv.BUOYANCY_WEIGHT_FRACTION * mass * gv.GRAVITY_MPS2], dtype=np.float64)
    f_drag = np.array(
        [
            -gv.DRAG_LINEAR_XY * v[0],
            -gv.DRAG_LINEAR_XY * v[1],
            -gv.DRAG_LINEAR_Z * v[2],
        ],
        dtype=np.float64,
    )
    f_total = f_buoy + f_drag

    if not _apply_force_world_newton(jetbot, f_total):
        global _warned_force_path
        if not _warned_force_path:
            carb.log_warn(
                "[underwater.robot] fluid_forces: could not apply force (articulation/RigidPrim path); "
                "check Isaac Sim API / JetBot prim layout."
            )
            _warned_force_path = True


def _resolve_mass_kg(jetbot) -> float:
    view = getattr(jetbot, "_articulation_view", None)
    if view is not None:
        gm = getattr(view, "get_body_masses", None)
        if callable(gm):
            try:
                raw = gm()
                m = np.asarray(raw, dtype=np.float64).reshape(-1)
                if m.size > 0:
                    return float(np.sum(m))
            except Exception:
                pass
    return float(gv.ROBOT_MASS_KG)


def _apply_force_world_newton(jetbot, f_world: np.ndarray) -> bool:
    f = np.asarray(f_world, dtype=np.float64).reshape(3)
    forces = f.reshape(1, 3)

    view = getattr(jetbot, "_articulation_view", None)
    if view is not None:
        af = getattr(view, "apply_forces", None)
        if callable(af):
            try:
                af(forces, is_global=True)
                return True
            except TypeError:
                try:
                    af(forces, indices=np.array([0], dtype=np.int32), is_global=True)
                    return True
                except Exception:
                    pass
            except Exception:
                pass

        aft = getattr(view, "apply_forces_and_torques_at_pos", None)
        if callable(aft):
            try:
                aft(forces=forces, torques=None, positions=None, is_global=True)
                return True
            except Exception:
                pass

    af_robot = getattr(jetbot, "apply_forces", None)
    if callable(af_robot):
        try:
            af_robot(forces, is_global=True)
            return True
        except Exception:
            pass

    prim_path = getattr(jetbot, "prim_path", None) or getattr(jetbot, "_prim_path", None)
    if isinstance(prim_path, str) and prim_path:
        return _apply_via_rigid_prim_cache(prim_path, f)

    return False


def _apply_via_rigid_prim_cache(articulation_root_path: str, f_world: np.ndarray) -> bool:
    """Articulation 에 force API 가 없을 때 첫 번째 링크 RigidPrim 으로 시도."""
    global _rigid_force_view, _rigid_force_path

    from isaacsim.core.prims import RigidPrim

    candidates = [
        f"{articulation_root_path}/chassis",
        f"{articulation_root_path}/base_link",
        articulation_root_path,
    ]

    target_path = _rigid_force_path
    if target_path is None:
        from isaacsim.core.utils.stage import get_current_stage

        stage = get_current_stage()
        for p in candidates:
            prim = stage.GetPrimAtPath(p)
            if prim.IsValid():
                target_path = p
                break
        _rigid_force_path = target_path

    if target_path is None:
        return False

    if _rigid_force_view is None:
        try:
            _rigid_force_view = RigidPrim(prim_paths_expr=target_path, name="underwater_fluid_force_body")
            _rigid_force_view.initialize()
        except Exception:
            _rigid_force_view = None
            return False

    try:
        fw = np.asarray(f_world, dtype=np.float64).reshape(1, 3)
        _rigid_force_view.apply_forces(fw, is_global=True)
        return True
    except Exception:
        return False


def reset_fluid_force_rigid_cache() -> None:
    """스테이지 리셋 후 RigidPrim 래퍼를 버리고 링크 경로 탐색을 다시 하도록 할 때 호출."""
    global _rigid_force_view, _rigid_force_path
    _rigid_force_view = None
    _rigid_force_path = None
