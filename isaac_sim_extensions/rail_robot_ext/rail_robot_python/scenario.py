"""Rail robot scenario — 수조 벽면 자율 순환 청소.

동작 순서 (1수조 기준):
  1. ARM_SWEEP: 팔을 벽면 상단에서 하단으로 천천히 쓸어내려 이물질을 바닥으로 밀어냄.
  2. RAIL_MOVE: 레일 캐리지를 다음 각도(10°)로 이동.
  3. 36 단계(360°) 완료 후 처음 각도로 돌아와 반복.
"""

import math
from typing import Optional, Tuple

import carb
import numpy as np
from pxr import Gf, UsdGeom, UsdPhysics

from .global_variables import (
    JOINT_NAMES,
    RAIL_CENTER_R,
    RAIL_MOUNT_Z,
    WALL_REACH_JOINTS,
    SWEEP_J2_TOP,
    SWEEP_J2_BOTTOM,
    RAIL_STEPS,
    ARM_SWEEP_DURATION,
    RAIL_MOVE_DURATION,
)

LOG_TAG = "[rail_robot]"

_ARM_SWEEP = 0
_RAIL_MOVE = 1


class RailRobotScenario:
    """레일 kinematic 순환 + 6DOF 암 자율 스윕.

    carriage_prim 은 수조 Pool Xform 의 자식으로 배치되므로,
    pool_center=(0,0) 으로 넘기면 pool-local 좌표계에서 동작한다.
    """

    def __init__(self, pool_idx: int, pool_center: Tuple[float, float] = (0.0, 0.0)):
        self._pool_idx = pool_idx
        self._pool_center = pool_center
        self._articulation = None
        self._carriage_prim = None
        self._joint_drive = None   # RevoluteJoint DriveAPI (경첩 각도 제어)
        self._bridge = None
        self._stage = None

        self._running = False
        self._phase = _ARM_SWEEP
        self._rail_angle = 0.0   # 현재 각도 (radian)
        self._phase_elapsed = 0.0

    # ── 초기화 ─────────────────────────────────────────────────────────────────

    def initialize(self, stage, articulation, carriage_prim_path: str) -> None:
        self._stage = stage
        self._articulation = articulation
        prim = stage.GetPrimAtPath(carriage_prim_path)
        if prim.IsValid():
            self._carriage_prim = UsdGeom.Xformable(prim)
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} initialized @ {carriage_prim_path}")

    def set_bridge(self, bridge) -> None:
        self._bridge = bridge

    def set_joint_drive(self, joint_prim_path: str) -> None:
        """RevoluteJoint DriveAPI를 연결한다 (경첩 각도 제어용)."""
        if not joint_prim_path or self._stage is None:
            return
        try:
            prim = self._stage.GetPrimAtPath(joint_prim_path)
            if prim.IsValid():
                self._joint_drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} joint drive 연결 실패: {e}")

    # ── 제어 진입점 ───────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._rail_angle = 0.0
        self._phase = _ARM_SWEEP
        self._phase_elapsed = 0.0
        self.set_rail_angle(self._rail_angle)
        self.set_arm_joints(self._top_pose())
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} sweep started")

    def stop(self) -> None:
        self._running = False
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} sweep stopped")

    # ── physics step 메인 루프 ────────────────────────────────────────────────

    def on_physics_step(self, step_size: float) -> None:
        if not self._running:
            return

        # ROS2 bridge 에서 override 명령이 오면 수동 제어 우선
        if self._bridge is not None:
            cmd = self._bridge.get_command()
            if cmd is not None and cmd.get("override"):
                self.set_rail_angle(cmd["rail_angle"])
                self.set_arm_joints(cmd["joint_positions"])
                self._publish_state()
                return

        self._phase_elapsed += step_size

        if self._phase == _ARM_SWEEP:
            # 상단→하단 선형 보간
            ratio = min(1.0, self._phase_elapsed / ARM_SWEEP_DURATION)
            pose = self._sweep_pose(height_ratio=1.0 - ratio)
            self.set_arm_joints(pose)

            if ratio >= 1.0:
                self._phase = _RAIL_MOVE
                self._phase_elapsed = 0.0

        elif self._phase == _RAIL_MOVE:
            if self._phase_elapsed >= RAIL_MOVE_DURATION:
                step = 2.0 * math.pi / RAIL_STEPS
                self._rail_angle = (self._rail_angle + step) % (2.0 * math.pi)
                self.set_rail_angle(self._rail_angle)
                self.set_arm_joints(self._top_pose())  # 팔 다시 상단으로
                self._phase = _ARM_SWEEP
                self._phase_elapsed = 0.0

        self._publish_state()

    # ── 저수준 액추에이터 ────────────────────────────────────────────────────

    def set_rail_angle(self, angle_rad: float) -> None:
        """레일 각도를 설정한다.

        경첩 RevoluteJoint DriveAPI 가 연결되어 있으면 drive target 으로 제어하고,
        없으면 kinematic Transform 으로 직접 이동한다 (fallback).
        """
        angle_deg = math.degrees(angle_rad)

        # ── 경첩 드라이브 우선 ────────────────────────────────────────────────
        if self._joint_drive is not None:
            try:
                self._joint_drive.GetTargetPositionAttr().Set(angle_deg)
                return
            except Exception:
                pass  # 실패 시 kinematic fallback

        # ── kinematic fallback: carriage Transform 직접 설정 ─────────────────
        if self._carriage_prim is None:
            return
        cx, cy = self._pool_center
        x = cx + RAIL_CENTER_R * math.cos(angle_rad)
        y = cy + RAIL_CENTER_R * math.sin(angle_rad)
        yaw_deg = angle_deg + 180.0   # 수조 중심을 향하도록

        xf = self._carriage_prim
        xf.ClearXformOpOrder()
        xf.AddTranslateOp().Set(Gf.Vec3d(x, y, RAIL_MOUNT_Z))
        xf.AddRotateZOp().Set(yaw_deg)

    def set_arm_joints(self, joint_positions: dict) -> None:
        if self._articulation is None:
            return
        try:
            current = list(self._articulation.get_joint_positions())
            for i, name in enumerate(JOINT_NAMES):
                if name in joint_positions:
                    current[i] = joint_positions[name]
            self._articulation.set_joint_positions(np.array(current, dtype=float))
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} set_arm_joints: {e}")

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    def _top_pose(self) -> dict:
        """팔을 벽면 상단을 향한 초기 자세로."""
        pose = {"joint_1": 0.0}
        pose.update(WALL_REACH_JOINTS)
        pose["joint_2"] = SWEEP_J2_TOP
        return pose

    def _sweep_pose(self, height_ratio: float) -> dict:
        """height_ratio: 1.0=상단, 0.0=하단."""
        j2 = SWEEP_J2_BOTTOM + height_ratio * (SWEEP_J2_TOP - SWEEP_J2_BOTTOM)
        pose = {"joint_1": 0.0}
        pose.update(WALL_REACH_JOINTS)
        pose["joint_2"] = j2
        return pose

    def _publish_state(self) -> None:
        if self._bridge is None:
            return
        positions = self._safe_get_positions()
        self._bridge.publish_joint_states(positions)

    def _safe_get_positions(self) -> list:
        if self._articulation is None:
            return [0.0] * len(JOINT_NAMES)
        try:
            return list(self._articulation.get_joint_positions())
        except Exception:
            return [0.0] * len(JOINT_NAMES)

    # ── 상태 조회 ─────────────────────────────────────────────────────────────

    @property
    def rail_angle_deg(self) -> float:
        return math.degrees(self._rail_angle)

    @property
    def is_running(self) -> bool:
        return self._running
