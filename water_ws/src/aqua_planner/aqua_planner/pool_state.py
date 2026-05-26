"""Pool cleaning state management for aqua_planner.

Provides state enum and per-pool state tracking for the cleaning orchestration.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from aqua_interfaces.msg import PoolStatus


class CleaningPhase(Enum):
    """Cleaning phase for each pool."""
    IDLE = "idle"
    CLEANING_WALL = "cleaning_wall"
    CLEANING_FLOOR = "cleaning_floor"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PoolState:
    """State container for a single pool."""
    pool_id: str
    phase: CleaningPhase = CleaningPhase.IDLE
    status: Optional[PoolStatus] = None
    wall_progress: float = 0.0
    floor_progress: float = 0.0
    error_message: str = ""

    @property
    def fish_count(self) -> Optional[int]:
        """Get fish count from cached status."""
        if self.status is None:
            return None
        return self.status.fish_count

    @property
    def is_active(self) -> bool:
        """Check if pool is in an active cleaning phase."""
        return self.phase in (CleaningPhase.CLEANING_WALL, CleaningPhase.CLEANING_FLOOR)

    @property
    def is_eligible_for_cleaning(self) -> bool:
        """Check if pool is eligible for cleaning (fish_count == 0 and status known)."""
        return self.status is not None and self.status.fish_count == 0

    def reset(self) -> None:
        """Reset state to idle."""
        self.phase = CleaningPhase.IDLE
        self.wall_progress = 0.0
        self.floor_progress = 0.0
        self.error_message = ""


class PoolStateManager:
    """Manages state for all pools."""

    def __init__(self, pool_ids: list[str]):
        self._states: Dict[str, PoolState] = {
            pid: PoolState(pool_id=pid) for pid in pool_ids
        }
        self._global_task_active = False

    @property
    def pool_ids(self) -> list[str]:
        """Get list of managed pool IDs."""
        return list(self._states.keys())

    @property
    def global_task_active(self) -> bool:
        """Check if a global cleaning task is in progress."""
        return self._global_task_active

    @global_task_active.setter
    def global_task_active(self, value: bool) -> None:
        self._global_task_active = value

    def get_state(self, pool_id: str) -> Optional[PoolState]:
        """Get state for a specific pool."""
        return self._states.get(pool_id)

    def update_status(self, pool_id: str, status: PoolStatus) -> None:
        """Update pool status from ROS message."""
        state = self._states.get(pool_id)
        if state:
            state.status = status

    def set_phase(self, pool_id: str, phase: CleaningPhase) -> None:
        """Set cleaning phase for a pool."""
        state = self._states.get(pool_id)
        if state:
            state.phase = phase

    def set_progress(self, pool_id: str, phase: CleaningPhase, progress: float) -> None:
        """Update progress for current phase."""
        state = self._states.get(pool_id)
        if state:
            if phase == CleaningPhase.CLEANING_WALL:
                state.wall_progress = progress
            elif phase == CleaningPhase.CLEANING_FLOOR:
                state.floor_progress = progress

    def mark_failed(self, pool_id: str, error: str = "") -> None:
        """Mark a pool as failed."""
        state = self._states.get(pool_id)
        if state:
            state.phase = CleaningPhase.FAILED
            state.error_message = error

    def get_eligible_pools(self) -> list[str]:
        """Get list of pools eligible for cleaning (fish_count == 0)."""
        return [
            pid for pid, state in self._states.items()
            if state.is_eligible_for_cleaning
        ]

    def get_ineligible_reasons(self) -> list[str]:
        """Get list of reasons why pools are not eligible."""
        reasons = []
        for pid, state in self._states.items():
            if state.status is None:
                reasons.append(f"{pid}(no status)")
            elif state.status.fish_count != 0:
                reasons.append(f"{pid}(fish_count={state.status.fish_count})")
        return reasons

    def get_active_pools(self) -> list[str]:
        """Get list of pools currently in active cleaning."""
        return [pid for pid, state in self._states.items() if state.is_active]

    def any_active(self) -> bool:
        """Check if any pool is actively cleaning."""
        return any(state.is_active for state in self._states.values())

    def all_completed_or_idle(self) -> bool:
        """Check if all pools are completed or idle (no active cleaning)."""
        return not self.any_active()

    def reset_all(self) -> None:
        """Reset all pools to idle state."""
        for state in self._states.values():
            state.reset()
        self._global_task_active = False

    def get_status_summary(self) -> str:
        """Get status summary string for all pools."""
        lines = []
        for pid, state in self._states.items():
            fish = str(state.fish_count) if state.fish_count is not None else "N/A"
            lines.append(f"{pid}: fish={fish} phase={state.phase.value}")
        return " | ".join(lines)
