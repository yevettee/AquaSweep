"""Planner node for AquaSweep - orchestrates cleaning tasks.

Services:
    /planner/start               - Start cleaning sequence (CleanWall → CleanFloor) 
                                   for all eligible pools (fish_count == 0)
    /planner/pause               - Cancel all current tasks
    /planner/status              - Get current status summary
    /{pool_id}/start_clean_floor - Start CleanFloor only for a specific pool
    /{pool_id}/start_clean_wall  - Start CleanWall → CleanFloor for a specific pool
"""

from functools import partial

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger

from aqua_interfaces.msg import PoolStatus

from .pool_state import PoolStateManager
from .task_executor import TaskExecutor
from .cleaning_orchestrator import CleaningOrchestrator


class PlannerNode(Node):
    """Main planner node with global and per-pool cleaning services."""

    def __init__(self) -> None:
        super().__init__('aqua_planner')

        self.declare_parameter(
            'pool_ids',
            ['pool_1', 'pool_2', 'pool_3', 'pool_4', 'pool_5', 'pool_6', 'pool_7']
        )
        pool_ids = list(
            self.get_parameter('pool_ids').get_parameter_value().string_array_value
        )

        self._state = PoolStateManager(pool_ids)
        self._executors: dict[str, TaskExecutor] = {}
        self._cb = ReentrantCallbackGroup()

        for pool_id in pool_ids:
            self._executors[pool_id] = TaskExecutor(self, pool_id=pool_id)
            self._setup_pool_subscriptions(pool_id)
            self._setup_pool_services(pool_id)

        self._orchestrator = CleaningOrchestrator(
            node=self,
            state_manager=self._state,
            executors=self._executors,
        )

        self._setup_global_services()
        self._log_startup_info(pool_ids)

    def _setup_pool_subscriptions(self, pool_id: str) -> None:
        """Setup ROS subscriptions for a pool."""
        self.create_subscription(
            PoolStatus,
            f'/{pool_id}/status',
            partial(self._on_pool_status, pool_id),
            10,
            callback_group=self._cb,
        )

    def _setup_pool_services(self, pool_id: str) -> None:
        """Setup per-pool ROS services."""
        self.create_service(
            Trigger,
            f'/{pool_id}/start_clean_floor',
            partial(self._handle_pool_floor_start, pool_id),
            callback_group=self._cb,
        )
        self.create_service(
            Trigger,
            f'/{pool_id}/start_clean_wall',
            partial(self._handle_pool_wall_start, pool_id),
            callback_group=self._cb,
        )

    def _setup_global_services(self) -> None:
        """Setup global ROS services."""
        self.create_service(
            Trigger, '/planner/start',
            self._handle_global_start,
            callback_group=self._cb
        )
        self.create_service(
            Trigger, '/planner/pause',
            self._handle_pause,
            callback_group=self._cb
        )
        self.create_service(
            Trigger, '/planner/status',
            self._handle_status,
            callback_group=self._cb
        )

    def _log_startup_info(self, pool_ids: list[str]) -> None:
        """Log startup information."""
        floor_services = ', '.join(f'/{pid}/start_clean_floor' for pid in pool_ids)
        wall_services = ', '.join(f'/{pid}/start_clean_wall' for pid in pool_ids)
        self.get_logger().info(
            f'PlannerNode ready | pools={pool_ids}\n'
            f'  global services: /planner/start, /planner/pause, /planner/status\n'
            f'  floor services: {floor_services}\n'
            f'  wall services: {wall_services}'
        )

    # ── Subscription Callbacks ─────────────────────────────────────────────

    def _on_pool_status(self, pool_id: str, msg: PoolStatus) -> None:
        """Cache the latest status for each pool."""
        self._state.update_status(pool_id, msg)

    # ── Service Handlers ───────────────────────────────────────────────────

    def _handle_global_start(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/start - start CleanWall → CleanFloor for eligible pools."""
        success, message = self._orchestrator.start_global_cleaning()
        response.success = success
        response.message = message
        if not success:
            self.get_logger().warn(message)
        return response

    def _handle_pool_floor_start(
        self, pool_id: str, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /{pool_id}/start_clean_floor - CleanFloor only (legacy)."""
        success, message = self._orchestrator.start_pool_cleaning(
            pool_id, wall_first=False
        )
        response.success = success
        response.message = message
        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().warn(message)
        return response

    def _handle_pool_wall_start(
        self, pool_id: str, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /{pool_id}/start_clean_wall - CleanWall → CleanFloor sequence."""
        success, message = self._orchestrator.start_pool_cleaning(
            pool_id, wall_first=True
        )
        response.success = success
        response.message = message
        if success:
            self.get_logger().info(message)
        else:
            self.get_logger().warn(message)
        return response

    def _handle_pause(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/pause - cancel all running tasks."""
        success, message = self._orchestrator.cancel_all()
        response.success = success
        response.message = message
        if success:
            self.get_logger().info(message)
        return response

    def _handle_status(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/status - return status summary."""
        response.success = True
        response.message = self._state.get_status_summary()
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PlannerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
