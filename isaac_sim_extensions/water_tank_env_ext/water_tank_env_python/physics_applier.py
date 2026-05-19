"""매 physics step마다 rigid body에 부력·항력·추가질량·지면효과를 적용한다.

prim에 아래 custom attribute를 선언하면 자동으로 물리 적용 대상이 된다:

    aquasweep:volume       (float, m³)         — 필수. 부력 계산용 부피
    aquasweep:half_height  (float, m)          — 선택. 기본 0.15
    aquasweep:cd_linear    (float, N·s/m)      — 선택. 기본 10.0
    aquasweep:cd_angular   (float, N·m·s/rad)  — 선택. 기본 5.0
    aquasweep:added_mass   (float)             — 선택. 기본 0.5

aquasweep:volume 없는 prim은 무시된다.
Drag·AddedMass·GroundEffect는 <repo>/water_tank_env/water_tank_env/ 에서 import.
부력은 Buoyancy 클래스 대신 _compute_buoyancy()로 직접 계산한다
(Buoyancy 클래스가 half_height를 0.15로 하드코딩하므로 per-body 값 적용 불가).
"""
import os
import sys
from typing import List, Tuple

import numpy as np
from pxr import Usd, UsdPhysics

from . import params

# ── Make the standalone water_tank_env package importable ───────────────────
# _HERE is .../src/isaac_sim_extensions/water_tank_env_ext/water_tank_env_python/
# Old package is at .../src/water_tank_env/water_tank_env/ — to `import
# water_tank_env.buoyancy` we need `.../src/water_tank_env/` on sys.path,
# which is THREE levels up from _HERE.
_HERE = os.path.dirname(os.path.realpath(__file__))
_OLD_PKG_PARENT = os.path.normpath(
    os.path.join(_HERE, "..", "..", "..", "water_tank_env")
)
if not os.path.isdir(_OLD_PKG_PARENT):
    raise ImportError(
        f"water_tank_env package directory not found at: {_OLD_PKG_PARENT}. "
        "physics_applier expects the old standalone package to live at "
        "<repo>/water_tank_env/water_tank_env/."
    )
if _OLD_PKG_PARENT not in sys.path:
    sys.path.insert(0, _OLD_PKG_PARENT)

from water_tank_env.drag import AddedMass, Drag      # noqa: E402
from water_tank_env.ground_effect import GroundEffect  # noqa: E402

VOLUME_ATTR = "aquasweep:volume"
HALF_HEIGHT_ATTR = "aquasweep:half_height"
CD_LINEAR_ATTR = "aquasweep:cd_linear"
CD_ANGULAR_ATTR = "aquasweep:cd_angular"
ADDED_MASS_ATTR = "aquasweep:added_mass"


class _Body:
    """Per-body cached state for the physics applier."""

    __slots__ = (
        "prim_path", "volume", "half_height",
        "drag", "added_mass", "ground_effect",
        "view", "prev_velocity",
    )

    def __init__(self, prim_path, volume, half_height, cd_linear, cd_angular,
                 added_mass_coeff, view):
        self.prim_path = prim_path
        self.volume = volume
        self.half_height = half_height
        self.drag = Drag(linear_drag_coeff=cd_linear, angular_drag_coeff=cd_angular)
        self.added_mass = AddedMass(volume, added_mass_coeff=added_mass_coeff)
        self.ground_effect = GroundEffect()
        self.view = view
        self.prev_velocity = np.zeros(3)


def _get_attr(prim: Usd.Prim, name: str, default: float) -> float:
    attr = prim.GetAttribute(name)
    if attr and attr.HasValue():
        return float(attr.Get())
    return default


class WaterPhysicsApplier:
    """Discovers opted-in rigid bodies on LOAD and applies water forces each
    physics step while RUN is active."""

    def __init__(self):
        self._bodies: List[_Body] = []
        self._stage = None
        self._rediscover_cooldown = 0  # frames remaining before next rediscover attempt

    def discover_bodies(self, stage):
        """Scan stage for rigid bodies with ``aquasweep:volume`` set."""
        # Local import: isaacsim.core.prims only loads inside Isaac Sim.
        from isaacsim.core.prims import RigidPrim

        self._stage = stage
        self._bodies.clear()
        for prim in stage.Traverse():
            if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
                continue
            volume_attr = prim.GetAttribute(VOLUME_ATTR)
            if not volume_attr or not volume_attr.HasValue():
                continue

            volume = float(volume_attr.Get())
            if volume <= 0.0:
                continue

            path = prim.GetPath().pathString
            view = RigidPrim(prim_paths_expr=path)
            try:
                view.initialize()
            except Exception:
                continue

            body = _Body(
                prim_path=path,
                volume=volume,
                half_height=_get_attr(prim, HALF_HEIGHT_ATTR, 0.15),
                cd_linear=_get_attr(prim, CD_LINEAR_ATTR, 10.0),
                cd_angular=_get_attr(prim, CD_ANGULAR_ATTR, 5.0),
                added_mass_coeff=_get_attr(prim, ADDED_MASS_ATTR, 0.5),
                view=view,
            )
            self._bodies.append(body)

    def apply(self, dt: float) -> None:
        # underwater_robot_ext가 water_tank_env보다 나중에 LOAD되면 discover_bodies
        # 시점에 로봇이 없어서 _bodies가 비어있을 수 있다. 60프레임마다 재탐색한다.
        if not self._bodies:
            if self._rediscover_cooldown > 0:
                self._rediscover_cooldown -= 1
                return
            if self._stage is not None:
                self.discover_bodies(self._stage)
                self._rediscover_cooldown = 60
            if not self._bodies:
                return

        water_surface_z = params.water_surface_z()
        floor_z = params.TANK_FLOOR_Z

        for body in self._bodies:
            try:
                positions, _ = body.view.get_world_poses()
                lin_vels = body.view.get_linear_velocities()
                ang_vels = body.view.get_angular_velocities()
            except Exception:
                continue

            pos = np.asarray(positions[0], dtype=float)
            lv = np.asarray(lin_vels[0], dtype=float)
            av = np.asarray(ang_vels[0], dtype=float)

            accel = (lv - body.prev_velocity) / max(dt, 1e-6)
            body.prev_velocity = lv.copy()

            buoyancy_force, cob = self._compute_buoyancy(
                body, pos, water_surface_z
            )
            drag_force, drag_torque = body.drag.compute(lv, av)
            added_force = body.added_mass.compute(accel)
            ground_force = body.ground_effect.compute(
                robot_pos_z=pos[2],
                floor_z=floor_z,
                linear_velocity=lv,
                base_drag_coeff=body.drag.Cd_linear,
            )

            total_force = buoyancy_force + drag_force + added_force + ground_force

            try:
                body.view.apply_forces_and_torques_at_pos(
                    forces=total_force.reshape(1, 3),
                    torques=drag_torque.reshape(1, 3),
                    positions=cob.reshape(1, 3),
                    is_global=True,
                )
            except Exception:
                continue

    def _compute_buoyancy(self, body: _Body, pos: np.ndarray,
                          water_surface_z: float) -> Tuple[np.ndarray, np.ndarray]:
        """Buoyancy with the body's own half-height (Buoyancy class hard-codes
        0.15; we wrap to honor the per-body value)."""
        top_z = pos[2] + body.half_height
        bottom_z = pos[2] - body.half_height
        if bottom_z >= water_surface_z:
            return np.zeros(3), pos

        if top_z <= water_surface_z:
            submerged_ratio = 1.0
        else:
            submerged_height = water_surface_z - bottom_z
            total_height = top_z - bottom_z
            submerged_ratio = float(np.clip(submerged_height / total_height, 0.0, 1.0))

        submerged_volume = body.volume * submerged_ratio
        magnitude = params.WATER_DENSITY * submerged_volume * params.GRAVITY
        return np.array([0.0, 0.0, magnitude]), pos
