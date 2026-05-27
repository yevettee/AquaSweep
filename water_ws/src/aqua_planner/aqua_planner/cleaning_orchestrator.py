"""Cleaning orchestrator for aqua_planner.

레일 로봇(CleanWall)과 바닥 청소 로봇(CleanFloor)을 동시에 실행한다.
"""

from functools import partial
from typing import Callable, Optional
from rclpy.node import Node

from .pool_state import PoolStateManager, CleaningPhase
from .task_executor import TaskExecutor


class CleaningOrchestrator:
    """Orchestrates concurrent cleaning: CleanWall ∥ CleanFloor."""

    def __init__(
        self,
        node: Node,
        state_manager: PoolStateManager,
        executors: dict[str, TaskExecutor],
    ):
        self._node = node
        self._state = state_manager
        self._executors = executors
        self._on_all_complete: Optional[Callable[[], None]] = None
        # 풀별 완료 추적: {pool_id: {'wall': bool, 'floor': bool}}
        self._completion: dict[str, dict[str, bool]] = {}

    def set_completion_callback(self, callback: Callable[[], None]) -> None:
        """Set callback to be invoked when all cleaning is complete."""
        self._on_all_complete = callback

    def start_global_cleaning(self) -> tuple[bool, str]:
        """모든 적합한 수조에서 CleanWall ∥ CleanFloor 동시 시작."""
        if self._state.global_task_active or self._state.any_active():
            return False, "Task already running"

        eligible = self._state.get_eligible_pools()
        skipped = self._state.get_ineligible_reasons()

        if not eligible:
            return False, f"No eligible pools. Skipped: {skipped}"

        self._state.global_task_active = True
        started = []

        for pool_id in eligible:
            self._completion[pool_id] = {'wall': False, 'floor': False}
            wall_ok  = self._start_wall_cleaning(pool_id)
            floor_ok = self._start_floor_cleaning(pool_id)
            if wall_ok or floor_ok:
                started.append(pool_id)
                if not wall_ok:
                    self._completion[pool_id]['wall'] = True   # 서버 없으면 완료로 간주
                if not floor_ok:
                    self._completion[pool_id]['floor'] = True

        if not started:
            self._state.global_task_active = False
            return False, "Failed to start any pool (action servers not available)"

        msg = f"CleanWall ∥ CleanFloor 동시 시작: {started}"
        if skipped:
            msg += f" | Skipped: {skipped}"
        self._node.get_logger().info(msg)
        return True, msg

    def start_pool_cleaning(self, pool_id: str, wall_first: bool = True) -> tuple[bool, str]:
        """특정 수조 청소 시작.

        wall_first=True  : CleanWall ∥ CleanFloor 동시 실행
        wall_first=False : CleanFloor만 실행 (레거시)
        """
        state = self._state.get_state(pool_id)
        if state is None:
            return False, f"Unknown pool: {pool_id}"

        if state.is_active:
            return False, f"{pool_id}: Task already running"

        if self._state.global_task_active:
            return False, f"{pool_id}: Global task in progress"

        if wall_first:
            self._completion[pool_id] = {'wall': False, 'floor': False}
            wall_ok  = self._start_wall_cleaning(pool_id)
            floor_ok = self._start_floor_cleaning(pool_id)
            if not wall_ok:
                self._completion[pool_id]['wall'] = True
            if not floor_ok:
                self._completion[pool_id]['floor'] = True
            success = wall_ok or floor_ok
            action = "CleanWall ∥ CleanFloor"
        else:
            success = self._start_floor_cleaning(pool_id)
            action = "CleanFloor"

        if success:
            return True, f"{action} started for {pool_id}"
        return False, f"{pool_id}: Failed to send goal (server not available)"

    def cancel_all(self) -> tuple[bool, str]:
        """Cancel all running cleaning tasks.

        Returns:
            (success, message) tuple
        """
        active_pools = self._state.get_active_pools()
        if not active_pools:
            return False, "No tasks running"

        cancelled = []
        for pool_id in active_pools:
            executor = self._executors.get(pool_id)
            if executor and executor.cancel_current_goal():
                cancelled.append(pool_id)
                self._state.set_phase(pool_id, CleaningPhase.IDLE)

        if cancelled:
            self._check_global_completion()
            return True, f"Cancellation requested for: {cancelled}"
        return False, "No active goals to cancel"

    # ── Wall Cleaning ──────────────────────────────────────────────────────

    def _start_wall_cleaning(self, pool_id: str) -> bool:
        """Start CleanWall action for a pool."""
        executor = self._executors.get(pool_id)
        if executor is None:
            return False

        success = executor.send_clean_wall_goal(
            feedback_callback=partial(self._on_wall_feedback, pool_id),
            done_callback=partial(self._on_wall_done, pool_id),
        )

        if success:
            self._state.set_phase(pool_id, CleaningPhase.CLEANING_WALL)
            self._node.get_logger().info(f"{pool_id}: CleanWall started")

        return success

    def _on_wall_feedback(self, pool_id: str, feedback) -> None:
        """Handle CleanWall feedback."""
        progress = feedback.progress
        self._state.set_progress(pool_id, CleaningPhase.CLEANING_WALL, progress)
        self._node.get_logger().info(f"{pool_id}: CleanWall progress {progress * 100:.1f}%")

    def _on_wall_done(self, pool_id: str, result) -> None:
        """CleanWall 완료 처리 — CleanFloor는 이미 동시에 실행 중."""
        if result.success:
            self._node.get_logger().info(f"{pool_id}: CleanWall 완료")
        else:
            self._node.get_logger().warn(f"{pool_id}: CleanWall 실패")

        if pool_id in self._completion:
            self._completion[pool_id]['wall'] = True
            self._check_pool_completion(pool_id)
        else:
            self._check_global_completion()

    # ── Floor Cleaning ─────────────────────────────────────────────────────

    def _start_floor_cleaning(self, pool_id: str) -> bool:
        """Start CleanFloor action for a pool."""
        executor = self._executors.get(pool_id)
        if executor is None:
            return False

        success = executor.send_clean_floor_goal(
            feedback_callback=partial(self._on_floor_feedback, pool_id),
            done_callback=partial(self._on_floor_done, pool_id),
        )

        if success:
            self._state.set_phase(pool_id, CleaningPhase.CLEANING_FLOOR)
            self._node.get_logger().info(f"{pool_id}: CleanFloor started")

        return success

    def _on_floor_feedback(self, pool_id: str, feedback) -> None:
        """Handle CleanFloor feedback."""
        progress = feedback.progress
        self._state.set_progress(pool_id, CleaningPhase.CLEANING_FLOOR, progress)
        self._node.get_logger().info(f"{pool_id}: CleanFloor progress {progress * 100:.1f}%")

    def _on_floor_done(self, pool_id: str, result) -> None:
        """CleanFloor 완료 처리."""
        if result.success:
            self._node.get_logger().info(f"{pool_id}: CleanFloor 완료")
            self._state.set_phase(pool_id, CleaningPhase.COMPLETED)
        else:
            self._node.get_logger().warn(f"{pool_id}: CleanFloor 실패")
            self._state.mark_failed(pool_id, "CleanFloor failed")

        if pool_id in self._completion:
            self._completion[pool_id]['floor'] = True
            self._check_pool_completion(pool_id)
        else:
            self._check_global_completion()

    # ── Completion Check ───────────────────────────────────────────────────

    def _check_pool_completion(self, pool_id: str) -> None:
        """수조 1개의 wall+floor 모두 완료됐는지 확인."""
        status = self._completion.get(pool_id, {})
        if status.get('wall') and status.get('floor'):
            self._node.get_logger().info(f"{pool_id}: CleanWall ∥ CleanFloor 모두 완료")
            self._check_global_completion()

    def _check_global_completion(self) -> None:
        """전체 청소 완료 여부 확인 후 콜백 호출."""
        if self._state.all_completed_or_idle():
            self._state.global_task_active = False
            self._node.get_logger().info("전체 수조 청소 완료")
            if self._on_all_complete:
                self._on_all_complete()
