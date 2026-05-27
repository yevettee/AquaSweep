"""Classic rail wall planner — sequential sweep then rail move.

동작 순서 (CALIBRATE 이후):
  1. ARM_SWEEP  : 아래→위 직선 스윕 (레일 각도 고정)
  2. ARM_HOME   : 홈 자세로 이동 (레일 회전 전 충돌 회피)
  3. RAIL_MOVE  : 레일 캐리지 회전 (코사인 이징)
  4. ARM_RESET  : 홈 → 스윕 시작(하단) 자세
  5. RAIL_STEPS 완료 시 종료
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

from .global_variables import (
    ARM_HOME_DURATION,
    ARM_HOME_JOINTS,
    ARM_RESET_DURATION,
    ARM_SWEEP_DURATION,
    RAIL_MOVE_DURATION,
    RAIL_STEPS,
)

_ARM_SWEEP = 0
_RAIL_MOVE = 1
_ARM_RESET = 2
_ARM_HOME = 4

PHASE_ARM_SWEEP = "arm_sweep"
PHASE_ARM_HOME = "arm_home"
PHASE_RAIL_MOVE = "rail_move"
PHASE_ARM_RESET = "arm_reset"


@dataclass
class PlannerStepResult:
    """Single physics-step output from a rail planner."""

    rail_angle: float
    phase_name: str
    current_step: int
    total_steps: int
    done: bool = False
    height_ratio: Optional[float] = None
    arm_joints: Optional[dict] = None
    phase_progress: float = 0.0


PoseFromTable = Callable[[float], dict]


def _cosine_ease(ratio: float) -> float:
    return 0.5 * (1.0 - math.cos(math.pi * ratio))


class RailPlannerClassic:
    """Original 5-phase sequential wall cleaning planner."""

    def __init__(self) -> None:
        self._phase = _ARM_SWEEP
        self._rail_angle = 0.0
        self._rail_angle_start = 0.0
        self._rail_angle_target = 0.0
        self._phase_elapsed = 0.0
        self._rail_step_count = 0

    def reset(self, rail_angle: float = 0.0) -> None:
        self._phase = _ARM_SWEEP
        self._rail_angle = rail_angle
        self._rail_angle_start = rail_angle
        self._rail_angle_target = rail_angle
        self._phase_elapsed = 0.0
        self._rail_step_count = 0

    @property
    def rail_angle(self) -> float:
        return self._rail_angle

    @property
    def current_step(self) -> int:
        return self._rail_step_count

    @property
    def total_steps(self) -> int:
        return RAIL_STEPS

    @property
    def phase_name(self) -> str:
        return _phase_name(self._phase)

    def calculate_progress(self) -> float:
        if RAIL_STEPS == 0:
            return 1.0

        base_progress = self._rail_step_count / RAIL_STEPS
        phase_weight = 1.0 / RAIL_STEPS

        if self._phase == _ARM_SWEEP:
            phase_progress = min(1.0, self._phase_elapsed / ARM_SWEEP_DURATION)
        elif self._phase == _ARM_HOME:
            phase_progress = min(1.0, self._phase_elapsed / ARM_HOME_DURATION)
        elif self._phase == _RAIL_MOVE:
            phase_progress = min(1.0, self._phase_elapsed / RAIL_MOVE_DURATION)
        elif self._phase == _ARM_RESET:
            phase_progress = min(1.0, self._phase_elapsed / ARM_RESET_DURATION)
        else:
            phase_progress = 0.0

        return min(1.0, base_progress + phase_progress * phase_weight * 0.25)

    def step(self, dt: float, pose_from_table: PoseFromTable) -> PlannerStepResult:
        self._phase_elapsed += dt
        phase_progress = 0.0

        if self._phase == _ARM_SWEEP:
            ratio = min(1.0, self._phase_elapsed / ARM_SWEEP_DURATION)
            phase_progress = ratio
            if ratio >= 1.0:
                self._phase = _ARM_HOME
                self._phase_elapsed = 0.0
            return PlannerStepResult(
                rail_angle=self._rail_angle,
                height_ratio=ratio,
                phase_name=PHASE_ARM_SWEEP,
                current_step=self._rail_step_count,
                total_steps=RAIL_STEPS,
                phase_progress=phase_progress,
            )

        if self._phase == _ARM_HOME:
            ratio = min(1.0, self._phase_elapsed / ARM_HOME_DURATION)
            t = _cosine_ease(ratio)
            phase_progress = ratio
            top_pose = pose_from_table(1.0)
            arm_joints = {
                k: top_pose[k] + t * (ARM_HOME_JOINTS[k] - top_pose[k])
                for k in top_pose
            }
            if ratio >= 1.0:
                self._rail_angle_start = self._rail_angle
                step = 2.0 * math.pi / RAIL_STEPS
                self._rail_angle_target = (self._rail_angle + step) % (2.0 * math.pi)
                self._phase = _RAIL_MOVE
                self._phase_elapsed = 0.0
            return PlannerStepResult(
                rail_angle=self._rail_angle,
                arm_joints=arm_joints,
                phase_name=PHASE_ARM_HOME,
                current_step=self._rail_step_count,
                total_steps=RAIL_STEPS,
                phase_progress=phase_progress,
            )

        if self._phase == _RAIL_MOVE:
            ratio = min(1.0, self._phase_elapsed / RAIL_MOVE_DURATION)
            t = _cosine_ease(ratio)
            phase_progress = ratio
            rail_angle = self._rail_angle_start + t * (
                self._rail_angle_target - self._rail_angle_start
            )
            if ratio >= 1.0:
                self._rail_angle = self._rail_angle_target
                self._rail_step_count += 1
                if self._rail_step_count >= RAIL_STEPS:
                    return PlannerStepResult(
                        rail_angle=self._rail_angle,
                        arm_joints=dict(ARM_HOME_JOINTS),
                        phase_name=PHASE_RAIL_MOVE,
                        current_step=self._rail_step_count,
                        total_steps=RAIL_STEPS,
                        done=True,
                        phase_progress=1.0,
                    )
                self._phase = _ARM_RESET
                self._phase_elapsed = 0.0
                rail_angle = self._rail_angle
            return PlannerStepResult(
                rail_angle=rail_angle,
                arm_joints=dict(ARM_HOME_JOINTS),
                phase_name=PHASE_RAIL_MOVE,
                current_step=self._rail_step_count,
                total_steps=RAIL_STEPS,
                phase_progress=phase_progress,
            )

        if self._phase == _ARM_RESET:
            ratio = min(1.0, self._phase_elapsed / ARM_RESET_DURATION)
            t = _cosine_ease(ratio)
            phase_progress = ratio
            bottom_pose = pose_from_table(0.0)
            arm_joints = {
                k: ARM_HOME_JOINTS[k] + t * (bottom_pose[k] - ARM_HOME_JOINTS[k])
                for k in ARM_HOME_JOINTS
            }
            if ratio >= 1.0:
                self._phase = _ARM_SWEEP
                self._phase_elapsed = 0.0
            return PlannerStepResult(
                rail_angle=self._rail_angle,
                arm_joints=arm_joints,
                phase_name=PHASE_ARM_RESET,
                current_step=self._rail_step_count,
                total_steps=RAIL_STEPS,
                phase_progress=phase_progress,
            )

        return PlannerStepResult(
            rail_angle=self._rail_angle,
            height_ratio=0.0,
            phase_name=PHASE_ARM_SWEEP,
            current_step=self._rail_step_count,
            total_steps=RAIL_STEPS,
        )


def _phase_name(phase: int) -> str:
    if phase == _ARM_SWEEP:
        return PHASE_ARM_SWEEP
    if phase == _ARM_HOME:
        return PHASE_ARM_HOME
    if phase == _RAIL_MOVE:
        return PHASE_RAIL_MOVE
    if phase == _ARM_RESET:
        return PHASE_ARM_RESET
    return PHASE_ARM_SWEEP
