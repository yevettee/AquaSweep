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
from typing import List, Tuple

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

from . import params

# ── 인라인 물리 클래스 (기존 water_tank_env 패키지에서 이전) ─────────────────

_WATER_DENSITY = 1000.0  # kg/m³

# ── 소프트 바닥 구속 파라미터 ──
_WHEEL_LINK = "left_wheel_link"
_WHEEL_RADIUS_FALLBACK = 0.049
_FLOOR_SPRING_K = 100000.0  # N/m — 바닥 침투 시 반발력 (강한 스프링)
_FLOOR_DAMPING = 5000.0     # N·s/m — 속도 댐핑 (진동 방지)


def _get_wheel_low_z(stage, robot_root: str) -> float | None:
    """로봇의 왼쪽 바퀴 최저점 Z 좌표 (world coordinate).

    wheel_low_z = 0.0이 되어야 바퀴가 바닥에 접촉하여 정상 구동된다.
    """
    collision_path = f"{robot_root}/{_WHEEL_LINK}/collisions"
    prim = stage.GetPrimAtPath(collision_path)
    if not prim or not prim.IsValid():
        return None

    cyl = UsdGeom.Cylinder(prim)
    if not cyl:
        return None

    radius = float(cyl.GetRadiusAttr().Get() or _WHEEL_RADIUS_FALLBACK)
    axis = str(cyl.GetAxisAttr().Get() or "Y")

    xf = UsdGeom.Xformable(prim)
    center_z = float(xf.ComputeLocalToWorldTransform(0).ExtractTranslation()[2])

    if axis == "Y":
        return center_z - radius
    elif axis == "Z":
        height = float(cyl.GetHeightAttr().Get() or 0.0)
        return center_z - height / 2.0
    return center_z - radius


class Drag:
    def __init__(self, linear_drag_coeff: float = 10.0, angular_drag_coeff: float = 5.0):
        self.Cd_linear = linear_drag_coeff
        self.Cd_angular = angular_drag_coeff

    def compute(self, linear_velocity: np.ndarray, angular_velocity: np.ndarray):
        return -self.Cd_linear * linear_velocity, -self.Cd_angular * angular_velocity


class AddedMass:
    def __init__(self, robot_volume: float, added_mass_coeff: float = 0.5):
        self._added_mass = added_mass_coeff * _WATER_DENSITY * robot_volume

    def compute(self, linear_acceleration: np.ndarray) -> np.ndarray:
        return -self._added_mass * linear_acceleration


class GroundEffect:
    def __init__(self, influence_height: float = 0.10, max_extra_factor: float = 0.5):
        self.influence_height = influence_height
        self.max_extra_factor = max_extra_factor

    def compute(self, robot_pos_z: float, floor_z: float,
                linear_velocity: np.ndarray, base_drag_coeff: float) -> np.ndarray:
        height = robot_pos_z - floor_z
        if height >= self.influence_height:
            return np.zeros(3)
        closeness = 1.0 - (height / self.influence_height)
        extra_factor = self.max_extra_factor * closeness
        hv = np.array([linear_velocity[0], linear_velocity[1], 0.0])
        return -extra_factor * base_drag_coeff * hv

VOLUME_ATTR = "aquasweep:volume"
HALF_HEIGHT_ATTR = "aquasweep:half_height"
CD_LINEAR_ATTR = "aquasweep:cd_linear"
CD_ANGULAR_ATTR = "aquasweep:cd_angular"
ADDED_MASS_ATTR = "aquasweep:added_mass"
# BCD multiplier — robot scenario 가 매 상태 전환 시 prim.SetAttribute 로 갱신.
# physics_applier 는 매 step 이 값을 읽어 body.buoyancy_multiplier 에 반영.
BUOYANCY_MULT_ATTR = "aquasweep:buoyancy_mult"


class _Body:
    """Per-body cached state for the physics applier."""

    __slots__ = (
        "prim_path", "robot_root", "volume", "half_height",
        "drag", "added_mass", "ground_effect",
        "view", "prev_velocity", "buoyancy_multiplier",
    )

    def __init__(self, prim_path, robot_root, volume, half_height, cd_linear, cd_angular,
                 added_mass_coeff, view):
        self.prim_path = prim_path
        self.robot_root = robot_root  # 바퀴 Z 계산용 (e.g., /World/Pools/Pool_1/Robot/hippo)
        self.volume = volume
        self.half_height = half_height
        self.drag = Drag(linear_drag_coeff=cd_linear, angular_drag_coeff=cd_angular)
        self.added_mass = AddedMass(volume, added_mass_coeff=added_mass_coeff)
        self.ground_effect = GroundEffect()
        self.view = view
        self.prev_velocity = np.zeros(3)
        # BCD (buoyancy control device) — scenario 가 상태별로 조정
        # 1.0=중성, >1=떠오름, <1=가라앉음. _compute_buoyancy 에서 magnitude 에 곱함.
        self.buoyancy_multiplier = 1.0


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
        """Scan stage for rigid bodies with ``aquasweep:volume`` attribute set.
        
        Note: volume 값이 0이어도 발견됨 (부력 비활성화 + 소프트 바닥 구속 지원).
        """
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
            # volume = 0도 허용 (부력 비활성화 상태)

            path = prim.GetPath().pathString
            view = RigidPrim(prim_paths_expr=path)
            try:
                view.initialize()
            except Exception:
                continue

            # robot_root 추출: base_link의 부모 경로 (바퀴 Z 계산용)
            # 예: /World/Pools/Pool_1/Robot/hippo/base_link → /World/Pools/Pool_1/Robot/hippo
            if path.endswith("/base_link"):
                robot_root = str(prim.GetParent().GetPath())
            else:
                robot_root = path

            body = _Body(
                prim_path=path,
                robot_root=robot_root,
                volume=volume,
                half_height=_get_attr(prim, HALF_HEIGHT_ATTR, 0.15),
                cd_linear=_get_attr(prim, CD_LINEAR_ATTR, 10.0),
                cd_angular=_get_attr(prim, CD_ANGULAR_ATTR, 5.0),
                added_mass_coeff=_get_attr(prim, ADDED_MASS_ATTR, 0.5),
                view=view,
            )
            self._bodies.append(body)

    def set_buoyancy_multiplier(self, prim_path_substring: str, multiplier: float) -> bool:
        """robot_root 또는 prim_path 에 ``prim_path_substring`` 이 포함된 body 의
        부력 multiplier 를 설정한다. scenario 가 IDLE/SINK/CLEAN/ASCEND 상태에 따라 호출.
        매칭된 body 가 있으면 True 반환."""
        matched = False
        for body in self._bodies:
            if prim_path_substring in body.robot_root or prim_path_substring in body.prim_path:
                body.buoyancy_multiplier = float(multiplier)
                matched = True
        return matched

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

            # USD attr 로부터 buoyancy_multiplier 동기화 (없으면 직전 값 유지).
            # 로봇 scenario 가 IDLE/SINK/CLEAN/ASCEND 전환 시 prim attr 만 set 하면 됨.
            if self._stage is not None:
                prim = self._stage.GetPrimAtPath(body.prim_path)
                if prim and prim.IsValid():
                    mult_attr = prim.GetAttribute(BUOYANCY_MULT_ATTR)
                    if mult_attr and mult_attr.HasValue():
                        body.buoyancy_multiplier = float(mult_attr.Get())

            pos = np.asarray(positions[0], dtype=float)
            lv = np.asarray(lin_vels[0], dtype=float)
            av = np.asarray(ang_vels[0], dtype=float)

            # ── 바닥 구속: wheel_low_z = 0.0 유지 ──
            # 하이브리드 방식: 작은 침투는 힘으로, 큰 침투는 직접 보정
            floor_push_force = np.zeros(3)
            wheel_low = _get_wheel_low_z(self._stage, body.robot_root)
            if wheel_low is not None and wheel_low < 0.0:
                penetration = abs(wheel_low)
                
                if penetration >= 0.003:
                    # 큰 침투: 직접 위치 보정 (wheel_low = 0이 되도록)
                    try:
                        _, orientations = body.view.get_world_poses()
                        corrected_z = pos[2] + penetration
                        body.view.set_world_poses(
                            positions=np.array([[pos[0], pos[1], corrected_z]]),
                            orientations=orientations,
                        )
                        # Z 속도 제거
                        if lv[2] < -0.01:
                            body.view.set_linear_velocities(
                                np.array([[lv[0], lv[1], 0.0]])
                            )
                            lv[2] = 0.0
                        pos[2] = corrected_z
                    except Exception:
                        pass
                else:
                    # 작은 침투: 스프링-댐퍼로 부드럽게 보정
                    spring_force = _FLOOR_SPRING_K * penetration
                    damping_force = -_FLOOR_DAMPING * lv[2] if lv[2] < 0 else 0.0
                    floor_push_force[2] = spring_force + damping_force

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

            total_force = buoyancy_force + drag_force + added_force + ground_force + floor_push_force

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
        magnitude = params.WATER_DENSITY * submerged_volume * params.GRAVITY * body.buoyancy_multiplier
        return np.array([0.0, 0.0, magnitude]), pos
