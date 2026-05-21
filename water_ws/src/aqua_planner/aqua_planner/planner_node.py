"""Planner node for AquaSweep - orchestrates cleaning tasks.

Services:
    /planner/start  - Start cleaning (CleanFloor goal)
    /planner/pause  - Cancel current task
"""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from .task_executor import TaskExecutor


class PlannerNode(Node):
    """Main planner node with start/pause services."""

    def __init__(self) -> None:
        super().__init__('aqua_planner')

        self.declare_parameter('pool_id', 'pool_1')
        pool_id = self.get_parameter('pool_id').get_parameter_value().string_value

        self._executor = TaskExecutor(self, pool_id=pool_id)
        self._is_running = False

        self._start_srv = self.create_service(
            Trigger, '/planner/start', self._handle_start
        )
        self._pause_srv = self.create_service(
            Trigger, '/planner/pause', self._handle_pause
        )

        self.get_logger().info(
            f'PlannerNode ready | pool={pool_id} | '
            f'services: /planner/start, /planner/pause'
        )

    def _handle_start(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/start service call."""
        if self._is_running:
            response.success = False
            response.message = 'Task already running'
            return response

        success = self._executor.send_clean_floor_goal(
            feedback_callback=self._on_feedback,
            done_callback=self._on_done
        )

        if success:
            self._is_running = True
            response.success = True
            response.message = f'CleanFloor started for {self._executor.pool_id}'
            self.get_logger().info(response.message)
        else:
            response.success = False
            response.message = 'Failed to send goal (server not available)'
            self.get_logger().warn(response.message)

        return response

    def _handle_pause(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /planner/pause service call."""
        if not self._is_running:
            response.success = False
            response.message = 'No task running'
            return response

        if self._executor.cancel_current_goal():
            response.success = True
            response.message = 'Cancellation requested'
            self.get_logger().info(response.message)
        else:
            response.success = False
            response.message = 'No active goal to cancel'

        return response

    def _on_feedback(self, feedback) -> None:
        """Handle feedback from action server."""
        self.get_logger().info(f'Progress: {feedback.progress * 100:.1f}%')

    def _on_done(self, result) -> None:
        """Handle action completion."""
        self._is_running = False
        if result.success:
            self.get_logger().info('Task completed successfully')
        else:
            self.get_logger().warn('Task failed')


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
