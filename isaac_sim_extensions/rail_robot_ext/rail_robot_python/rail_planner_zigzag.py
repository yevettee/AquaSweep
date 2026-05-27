"""Zigzag rail wall planner — simultaneous rail angle and sweep height."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .global_variables import (
    COUPLED_SWEEP_DURATION,
    RAIL_CENTER_R,
    RAIL_STEP_ANGLE_RAD,
    ZIGZAG_DOWN_UP_DURATION,
    ZIGZAG_FULL_ROTATION_DURATION,
)
from .rail_planner import PlannerStepResult

PHASE_COUPLED_SWEEP = "coupled_sweep"


@dataclass(frozen=True)
class CoupledSegment:
    rail_start_rad: float
    rail_end_rad: float
    height_start: float
    height_end: float
    duration_s: float


@dataclass(frozen=True)
class ZigzagTiming:
    """Resolved zigzag timing (simulation seconds)."""

    segment_count: int
    segment_duration_s: float
    half_stroke_duration_s: float
    down_up_duration_s: float
    lap_duration_s: float
    step_angle_rad: float
    rail_arc_length_m: float

    def summary(self) -> str:
        return (
            f"segments={self.segment_count} "
            f"stroke={self.segment_duration_s:.3f}s "
            f"down+up={self.down_up_duration_s:.3f}s "
            f"lap={self.lap_duration_s:.3f}s "
            f"step={math.degrees(self.step_angle_rad):.2f}° "
            f"arc={self.rail_arc_length_m:.2f}m"
        )


def compute_zigzag_timing(
    *,
    total_angle_rad: float = 2.0 * math.pi,
    lap_duration_s: float = ZIGZAG_FULL_ROTATION_DURATION,
    down_up_duration_s: float = ZIGZAG_DOWN_UP_DURATION,
    manual_segment_duration_s: Optional[float] = COUPLED_SWEEP_DURATION,
    manual_step_angle_rad: Optional[float] = RAIL_STEP_ANGLE_RAD,
) -> ZigzagTiming:
    """Derive segment count/duration so lap sim-time matches lap_duration_s."""
    if lap_duration_s <= 0.0:
        raise ValueError("lap_duration_s must be positive")
    if down_up_duration_s <= 0.0:
        raise ValueError("down_up_duration_s must be positive")

    half_stroke_target = (
        float(manual_segment_duration_s)
        if manual_segment_duration_s is not None
        else down_up_duration_s / 2.0
    )
    if half_stroke_target <= 0.0:
        raise ValueError("half stroke duration must be positive")

    if manual_step_angle_rad is not None:
        if manual_step_angle_rad <= 0.0:
            raise ValueError("manual_step_angle_rad must be positive")
        segment_count = max(1, int(math.ceil(total_angle_rad / manual_step_angle_rad)))
    else:
        segment_count = max(1, int(round(lap_duration_s / half_stroke_target)))

    segment_duration_s = lap_duration_s / segment_count
    step_angle_rad = total_angle_rad / segment_count
    rail_arc_length_m = RAIL_CENTER_R * total_angle_rad

    return ZigzagTiming(
        segment_count=segment_count,
        segment_duration_s=segment_duration_s,
        half_stroke_duration_s=segment_duration_s,
        down_up_duration_s=segment_duration_s * 2.0,
        lap_duration_s=segment_duration_s * segment_count,
        step_angle_rad=step_angle_rad,
        rail_arc_length_m=rail_arc_length_m,
    )


def estimate_lap_duration_s() -> float:
    """Total simulation time for one 360° zigzag lap."""
    return compute_zigzag_timing().lap_duration_s


def build_zigzag_path(
    *,
    total_angle_rad: float = 2.0 * math.pi,
    timing: Optional[ZigzagTiming] = None,
) -> Tuple[List[CoupledSegment], ZigzagTiming]:
    """Build alternating up/down diagonal segments around the rail."""
    timing = timing or compute_zigzag_timing(total_angle_rad=total_angle_rad)
    stroke_s = timing.segment_duration_s
    n_segments = timing.segment_count
    actual_step = timing.step_angle_rad

    segments: List[CoupledSegment] = []
    rail = 0.0
    for i in range(n_segments):
        rail_end = rail + actual_step
        if i % 2 == 0:
            height_start, height_end = 0.0, 1.0
        else:
            height_start, height_end = 1.0, 0.0
        segments.append(
            CoupledSegment(
                rail_start_rad=rail,
                rail_end_rad=rail_end,
                height_start=height_start,
                height_end=height_end,
                duration_s=stroke_s,
            )
        )
        rail = rail_end

    return segments, timing


class RailPlannerZigzag:
    """W-pattern planner: rail angle and arm height move together per segment."""

    def __init__(
        self,
        segments: Optional[List[CoupledSegment]] = None,
        timing: Optional[ZigzagTiming] = None,
    ) -> None:
        if segments is None:
            segments, timing = build_zigzag_path()
        self._segments = segments
        self._timing = timing or compute_zigzag_timing()
        self._seg_idx = 0
        self._phase_elapsed = 0.0
        self._rail_angle = 0.0
        self._elapsed_s = 0.0

    @property
    def timing(self) -> ZigzagTiming:
        return self._timing

    @property
    def rail_angle(self) -> float:
        return self._rail_angle

    @property
    def elapsed_s(self) -> float:
        return self._elapsed_s

    @property
    def current_step(self) -> int:
        return self._seg_idx

    @property
    def total_steps(self) -> int:
        return len(self._segments)

    @property
    def phase_name(self) -> str:
        return PHASE_COUPLED_SWEEP

    def calculate_progress(self) -> float:
        if self._timing.lap_duration_s <= 0.0:
            return 1.0
        return min(1.0, self._elapsed_s / self._timing.lap_duration_s)

    def reset(self, rail_angle: float = 0.0) -> None:
        self._seg_idx = 0
        self._phase_elapsed = 0.0
        self._rail_angle = rail_angle
        self._elapsed_s = 0.0

    def step(self, dt: float, pose_from_table=None) -> PlannerStepResult:
        del pose_from_table  # height_ratio only; scenario applies IK table

        if self._seg_idx >= len(self._segments):
            return PlannerStepResult(
                rail_angle=self._rail_angle,
                height_ratio=0.0,
                phase_name=PHASE_COUPLED_SWEEP,
                current_step=self._seg_idx,
                total_steps=len(self._segments),
                done=True,
                phase_progress=1.0,
            )

        seg = self._segments[self._seg_idx]
        self._phase_elapsed += dt
        self._elapsed_s += dt
        ratio = min(1.0, self._phase_elapsed / seg.duration_s) if seg.duration_s > 0 else 1.0
        t = ratio  # linear: rail + height move together at constant rate

        rail_angle = seg.rail_start_rad + t * (seg.rail_end_rad - seg.rail_start_rad)
        height_ratio = seg.height_start + t * (seg.height_end - seg.height_start)

        if ratio >= 1.0:
            self._rail_angle = seg.rail_end_rad
            self._seg_idx += 1
            self._phase_elapsed = 0.0
            if self._seg_idx >= len(self._segments):
                return PlannerStepResult(
                    rail_angle=self._rail_angle,
                    height_ratio=seg.height_end,
                    phase_name=PHASE_COUPLED_SWEEP,
                    current_step=self._seg_idx,
                    total_steps=len(self._segments),
                    done=True,
                    phase_progress=1.0,
                )
        else:
            self._rail_angle = rail_angle

        return PlannerStepResult(
            rail_angle=rail_angle,
            height_ratio=height_ratio,
            phase_name=PHASE_COUPLED_SWEEP,
            current_step=self._seg_idx,
            total_steps=len(self._segments),
            phase_progress=ratio,
        )
