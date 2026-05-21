"""Task executor for aqua_planner - manages Action Clients."""

from typing import Optional, Callable
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.action.client import ClientGoalHandle

from aqua_interfaces.action import CleanFloor, CleanWall, MoveFish


class TaskExecutor:
    """Manages Action Clients for controller communication."""

    def __init__(self, node: Node, pool_id: str = 'pool_1'):
        self._node = node
        self._pool_id = pool_id

        self._clean_floor_client = ActionClient(
            node, CleanFloor, f'/{pool_id}/clean_floor'
        )
        self._clean_wall_client = ActionClient(
            node, CleanWall, f'/{pool_id}/clean_wall'
        )
        self._move_fish_client = ActionClient(
            node, MoveFish, f'/{pool_id}/move_fish'
        )

        self._current_goal_handle: Optional[ClientGoalHandle] = None
        self._feedback_callback: Optional[Callable] = None

    @property
    def pool_id(self) -> str:
        return self._pool_id

    def set_pool(self, pool_id: str) -> None:
        """Change target pool (recreates action clients)."""
        self._pool_id = pool_id
        self._clean_floor_client = ActionClient(
            self._node, CleanFloor, f'/{pool_id}/clean_floor'
        )
        self._clean_wall_client = ActionClient(
            self._node, CleanWall, f'/{pool_id}/clean_wall'
        )
        self._move_fish_client = ActionClient(
            self._node, MoveFish, f'/{pool_id}/move_fish'
        )

    def send_clean_floor_goal(
        self,
        feedback_callback: Optional[Callable] = None,
        done_callback: Optional[Callable] = None
    ) -> bool:
        """Send CleanFloor goal to controller."""
        if not self._clean_floor_client.wait_for_server(timeout_sec=1.0):
            self._node.get_logger().warn(
                f'CleanFloor server not available: /{self._pool_id}/clean_floor'
            )
            return False

        goal = CleanFloor.Goal()
        self._feedback_callback = feedback_callback

        future = self._clean_floor_client.send_goal_async(
            goal,
            feedback_callback=self._handle_feedback
        )
        future.add_done_callback(
            lambda f: self._handle_goal_response(f, done_callback)
        )
        return True

    def send_clean_wall_goal(
        self,
        feedback_callback: Optional[Callable] = None,
        done_callback: Optional[Callable] = None
    ) -> bool:
        """Send CleanWall goal to controller (stub - not fully implemented)."""
        if not self._clean_wall_client.wait_for_server(timeout_sec=1.0):
            self._node.get_logger().warn(
                f'CleanWall server not available: /{self._pool_id}/clean_wall'
            )
            return False

        goal = CleanWall.Goal()
        self._feedback_callback = feedback_callback

        future = self._clean_wall_client.send_goal_async(
            goal,
            feedback_callback=self._handle_feedback
        )
        future.add_done_callback(
            lambda f: self._handle_goal_response(f, done_callback)
        )
        return True

    def send_move_fish_goal(
        self,
        source_pool: str,
        target_pool: str,
        fish_count: int = -1,
        feedback_callback: Optional[Callable] = None,
        done_callback: Optional[Callable] = None
    ) -> bool:
        """Send MoveFish goal to controller (stub - not fully implemented)."""
        if not self._move_fish_client.wait_for_server(timeout_sec=1.0):
            self._node.get_logger().warn(
                f'MoveFish server not available: /{self._pool_id}/move_fish'
            )
            return False

        goal = MoveFish.Goal()
        goal.source_pool = source_pool
        goal.target_pool = target_pool
        goal.fish_count = fish_count
        self._feedback_callback = feedback_callback

        future = self._move_fish_client.send_goal_async(
            goal,
            feedback_callback=self._handle_feedback
        )
        future.add_done_callback(
            lambda f: self._handle_goal_response(f, done_callback)
        )
        return True

    def cancel_current_goal(self) -> bool:
        """Cancel currently running goal."""
        if self._current_goal_handle is None:
            return False

        cancel_future = self._current_goal_handle.cancel_goal_async()
        self._node.get_logger().info('Cancellation requested')
        return True

    def _handle_feedback(self, feedback_msg) -> None:
        """Internal feedback handler."""
        if self._feedback_callback:
            self._feedback_callback(feedback_msg.feedback)

    def _handle_goal_response(self, future, done_callback: Optional[Callable]) -> None:
        """Handle goal acceptance/rejection."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._node.get_logger().warn('Goal rejected')
            self._current_goal_handle = None
            return

        self._current_goal_handle = goal_handle
        self._node.get_logger().info('Goal accepted')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self._handle_result(f, done_callback)
        )

    def _handle_result(self, future, done_callback: Optional[Callable]) -> None:
        """Handle action result."""
        result = future.result().result
        self._current_goal_handle = None

        if done_callback:
            done_callback(result)
