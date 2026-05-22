"""Planner node for AquaSweep - orchestrates cleaning tasks.

Services:
    /planner/start            - Start cleaning for all eligible pools (fish_count == 0)
    /planner/pause            - Cancel all current tasks
    /{pool_id}/start_clean_floor - Start cleaning for a specific pool
"""

from functools import partial
from typing import Dict, Optional

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from aqua_interfaces.msg import PoolStatus

from .task_executor import TaskExecutor


class PlannerNode(Node):
    """Main planner node with global and per-pool start services."""

    def __init__(self) -> None:
        super().__init__('aqua_planner')

        self.declare_parameter('pool_ids', ['pool_1', 'pool_2', 'pool_3', 'pool_4', 'pool_5', 'pool_6', 'pool_7'])
        pool_ids = self.get_parameter('pool_ids').get_parameter_value().string_array_value

        self._pool_ids = list(pool_ids)
        self._executors: Dict[str, TaskExecutor] = {}
        self._pool_status: Dict[str, Optional[PoolStatus]] = {}
        self._is_running: Dict[str, bool] = {}
        self._global_task_active = False

        for pool_id in self._pool_ids:
            self._executors[pool_id] = TaskExecutor(self, pool_id=pool_id)
            self._pool_status[pool_id] = None
            self._is_running[pool_id] = False

            self.create_subscription(
                PoolStatus,
                f'/{pool_id}/status',
                partial(self._on_pool_status, pool_id),
                10
            )

            self.create_service(
                Trigger,
                f'/{pool_id}/start_clean_floor',
                partial(self._handle_pool_start, pool_id)
            )

        self._start_srv = self.create_service(
            Trigger, '/planner/start', self._handle_global_start
        )
        self._pause_srv = self.create_service(
            Trigger, '/planner/pause', self._handle_pause
        )

        pool_services = ', '.join(f'/{pid}/start_clean_floor' for pid in self._pool_ids)
        self.get_logger().info(
            f'PlannerNode ready | pools={self._pool_ids}\n'
            f'  global services: /planner/start, /planner/pause\n'
            f'  pool services: {pool_services}'
        )

    def _on_pool_status(self, pool_id: str, msg: PoolStatus) -> None:
        """Cache the latest status for each pool."""
        self._pool_status[pool_id] = msg

    def _handle_global_start(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/start - start cleaning for pools with fish_count == 0."""
        if self._global_task_active or any(self._is_running.values()):
            response.success = False
            response.message = 'Task already running'
            return response

        eligible_pools = []
        skipped_pools = []

        for pool_id in self._pool_ids:
            status = self._pool_status.get(pool_id)
            if status is None:
                skipped_pools.append(f'{pool_id}(no status)')
                continue
            if status.fish_count != 0:
                skipped_pools.append(f'{pool_id}(fish_count={status.fish_count})')
                continue
            eligible_pools.append(pool_id)

        if not eligible_pools:
            response.success = False
            response.message = f'No eligible pools (fish_count != 0 or no status). Skipped: {skipped_pools}'
            self.get_logger().warn(response.message)
            return response

        self._global_task_active = True
        started = []

        for pool_id in eligible_pools:
            success = self._start_pool_cleaning(pool_id)
            if success:
                started.append(pool_id)

        if started:
            response.success = True
            response.message = f'CleanFloor started for: {started}'
            if skipped_pools:
                response.message += f' | Skipped: {skipped_pools}'
            self.get_logger().info(response.message)
        else:
            self._global_task_active = False
            response.success = False
            response.message = 'Failed to start any pool (action servers not available)'
            self.get_logger().warn(response.message)

        return response

    def _handle_pool_start(
        self, pool_id: str, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /{pool_id}/start_clean_floor service call."""
        if self._is_running.get(pool_id, False):
            response.success = False
            response.message = f'{pool_id}: Task already running'
            return response

        if self._global_task_active:
            response.success = False
            response.message = f'{pool_id}: Global task in progress'
            return response

        success = self._start_pool_cleaning(pool_id)

        if success:
            response.success = True
            response.message = f'CleanFloor started for {pool_id}'
            self.get_logger().info(response.message)
        else:
            response.success = False
            response.message = f'{pool_id}: Failed to send goal (server not available)'
            self.get_logger().warn(response.message)

        return response

    def _start_pool_cleaning(self, pool_id: str) -> bool:
        """Start CleanFloor action for a specific pool."""
        executor = self._executors.get(pool_id)
        if executor is None:
            return False

        success = executor.send_clean_floor_goal(
            feedback_callback=partial(self._on_feedback, pool_id),
            done_callback=partial(self._on_done, pool_id)
        )

        if success:
            self._is_running[pool_id] = True

        return success

    def _handle_pause(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/pause - cancel all running tasks."""
        if not any(self._is_running.values()):
            response.success = False
            response.message = 'No tasks running'
            return response

        cancelled = []
        for pool_id, running in self._is_running.items():
            if running:
                executor = self._executors.get(pool_id)
                if executor and executor.cancel_current_goal():
                    cancelled.append(pool_id)

        if cancelled:
            response.success = True
            response.message = f'Cancellation requested for: {cancelled}'
            self.get_logger().info(response.message)
        else:
            response.success = False
            response.message = 'No active goals to cancel'

        return response

    def _on_feedback(self, pool_id: str, feedback) -> None:
        """Handle feedback from action server."""
        self.get_logger().info(f'{pool_id}: Progress {feedback.progress * 100:.1f}%')

    def _on_done(self, pool_id: str, result) -> None:
        """Handle action completion for a pool."""
        self._is_running[pool_id] = False

        if result.success:
            self.get_logger().info(f'{pool_id}: Task completed successfully')
        else:
            self.get_logger().warn(f'{pool_id}: Task failed')

        if not any(self._is_running.values()):
            self._global_task_active = False
            self.get_logger().info('All pool tasks completed')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
