"""Planner node for AquaSweep - orchestrates cleaning tasks.

Services:
    /planner/start            - Start cleaning for all eligible pools (fish_count == 0)
    /planner/pause            - Cancel all current tasks
    /{pool_id}/start_clean_floor - Start cleaning for a specific pool

Sturgeon Animation Control:
    - Automatically pauses sturgeon animation when cleaning starts
    - Resumes animation when all cleaning tasks complete

Robot Activation Control:
    - Automatically activates robot (creates ActionGraph) before cleaning starts
    - Deactivates robot after cleaning completes (optional)
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
        self._sturgeon_paused = False

        # Sturgeon animation control service clients
        self._sturgeon_pause_cli = self.create_client(Trigger, '/sturgeon/pause')
        self._sturgeon_resume_cli = self.create_client(Trigger, '/sturgeon/resume')

        # Robot activation control service clients (per pool)
        self._activate_robot_cli: Dict[str, any] = {}
        self._deactivate_robot_cli: Dict[str, any] = {}

        cb = ReentrantCallbackGroup()

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

            # Robot activation service clients for this pool
            self._activate_robot_cli[pool_id] = self.create_client(
                Trigger, f'/{pool_id}/activate_robot'
            )
            self._deactivate_robot_cli[pool_id] = self.create_client(
                Trigger, f'/{pool_id}/deactivate_robot'
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

        # Pause sturgeon animation before cleaning starts (performance optimization)
        if not self._sturgeon_paused:
            self._call_sturgeon_pause()

        # Activate robot ActionGraph before cleaning starts
        self._call_activate_robot(pool_id)

        success = executor.send_clean_floor_goal(
            feedback_callback=partial(self._on_feedback, pool_id),
            done_callback=partial(self._on_done, pool_id)
        )

        if success:
            self._is_running[pool_id] = True

        return success

    def _call_sturgeon_pause(self) -> None:
        """Call /sturgeon/pause service (non-blocking)."""
        if not self._sturgeon_pause_cli.service_is_ready():
            self.get_logger().warn('Sturgeon pause service not available, skipping')
            return
        
        future = self._sturgeon_pause_cli.call_async(Trigger.Request())
        future.add_done_callback(self._on_sturgeon_pause_done)

    def _on_sturgeon_pause_done(self, future) -> None:
        """Handle sturgeon pause service response."""
        try:
            result = future.result()
            if result.success:
                self._sturgeon_paused = True
                self.get_logger().info(f'Sturgeon animation paused: {result.message}')
            else:
                self.get_logger().warn(f'Sturgeon pause failed: {result.message}')
        except Exception as e:
            self.get_logger().error(f'Sturgeon pause service error: {e}')

    def _call_sturgeon_resume(self) -> None:
        """Call /sturgeon/resume service (non-blocking)."""
        if not self._sturgeon_resume_cli.service_is_ready():
            self.get_logger().warn('Sturgeon resume service not available, skipping')
            return
        
        future = self._sturgeon_resume_cli.call_async(Trigger.Request())
        future.add_done_callback(self._on_sturgeon_resume_done)

    def _on_sturgeon_resume_done(self, future) -> None:
        """Handle sturgeon resume service response."""
        try:
            result = future.result()
            if result.success:
                self._sturgeon_paused = False
                self.get_logger().info(f'Sturgeon animation resumed: {result.message}')
            else:
                self.get_logger().warn(f'Sturgeon resume failed: {result.message}')
        except Exception as e:
            self.get_logger().error(f'Sturgeon resume service error: {e}')

    def _call_activate_robot(self, pool_id: str) -> None:
        """Call /{pool_id}/activate_robot service (non-blocking)."""
        cli = self._activate_robot_cli.get(pool_id)
        if cli is None:
            self.get_logger().warn(f'No activate_robot client for {pool_id}')
            return
        if not cli.service_is_ready():
            self.get_logger().warn(f'{pool_id}/activate_robot service not available, skipping')
            return
        
        future = cli.call_async(Trigger.Request())
        future.add_done_callback(partial(self._on_activate_robot_done, pool_id))

    def _on_activate_robot_done(self, pool_id: str, future) -> None:
        """Handle activate_robot service response."""
        try:
            result = future.result()
            if result.success:
                self.get_logger().info(f'{pool_id} robot activated: {result.message}')
            else:
                self.get_logger().warn(f'{pool_id} robot activation failed: {result.message}')
        except Exception as e:
            self.get_logger().error(f'{pool_id} activate_robot service error: {e}')

    def _call_deactivate_robot(self, pool_id: str) -> None:
        """Call /{pool_id}/deactivate_robot service (non-blocking)."""
        cli = self._deactivate_robot_cli.get(pool_id)
        if cli is None:
            self.get_logger().warn(f'No deactivate_robot client for {pool_id}')
            return
        if not cli.service_is_ready():
            self.get_logger().warn(f'{pool_id}/deactivate_robot service not available, skipping')
            return
        
        future = cli.call_async(Trigger.Request())
        future.add_done_callback(partial(self._on_deactivate_robot_done, pool_id))

    def _on_deactivate_robot_done(self, pool_id: str, future) -> None:
        """Handle deactivate_robot service response."""
        try:
            result = future.result()
            if result.success:
                self.get_logger().info(f'{pool_id} robot deactivated: {result.message}')
            else:
                self.get_logger().warn(f'{pool_id} robot deactivation failed: {result.message}')
        except Exception as e:
            self.get_logger().error(f'{pool_id} deactivate_robot service error: {e}')

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
            # Resume sturgeon animation after all cleaning tasks complete
            if self._sturgeon_paused:
                self._call_sturgeon_resume()


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
