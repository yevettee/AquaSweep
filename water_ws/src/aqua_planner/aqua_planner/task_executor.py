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

        # 각 action별로 별도 goal handle 관리 (동시 실행 지원)
        self._clean_floor_handle: Optional[ClientGoalHandle] = None
        self._clean_wall_handle: Optional[ClientGoalHandle] = None
        self._move_fish_handle: Optional[ClientGoalHandle] = None
        
        self._floor_feedback_callback: Optional[Callable] = None
        self._wall_feedback_callback: Optional[Callable] = None
        self._fish_feedback_callback: Optional[Callable] = None

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
        self._floor_feedback_callback = feedback_callback

        future = self._clean_floor_client.send_goal_async(
            goal,
            feedback_callback=self._handle_floor_feedback
        )
        future.add_done_callback(
            lambda f: self._handle_floor_goal_response(f, done_callback)
        )
        return True

    def send_clean_wall_goal(
        self,
        feedback_callback: Optional[Callable] = None,
        done_callback: Optional[Callable] = None
    ) -> bool:
        """Send CleanWall goal to controller."""
        if not self._clean_wall_client.wait_for_server(timeout_sec=1.0):
            self._node.get_logger().warn(
                f'CleanWall server not available: /{self._pool_id}/clean_wall'
            )
            return False

        goal = CleanWall.Goal()
        self._wall_feedback_callback = feedback_callback

        future = self._clean_wall_client.send_goal_async(
            goal,
            feedback_callback=self._handle_wall_feedback
        )
        future.add_done_callback(
            lambda f: self._handle_wall_goal_response(f, done_callback)
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
        """Send MoveFish goal to controller."""
        if not self._move_fish_client.wait_for_server(timeout_sec=1.0):
            self._node.get_logger().warn(
                f'MoveFish server not available: /{self._pool_id}/move_fish'
            )
            return False

        goal = MoveFish.Goal()
        goal.source_pool = source_pool
        goal.target_pool = target_pool
        goal.fish_count = fish_count
        self._fish_feedback_callback = feedback_callback

        future = self._move_fish_client.send_goal_async(
            goal,
            feedback_callback=self._handle_fish_feedback
        )
        future.add_done_callback(
            lambda f: self._handle_fish_goal_response(f, done_callback)
        )
        return True

    def cancel_current_goal(self) -> bool:
        """Cancel all running goals (CleanWall, CleanFloor, MoveFish)."""
        cancelled = False
        
        if self._clean_wall_handle is not None:
            self._clean_wall_handle.cancel_goal_async()
            self._node.get_logger().info(f'{self._pool_id}: CleanWall cancellation requested')
            cancelled = True
        
        if self._clean_floor_handle is not None:
            self._clean_floor_handle.cancel_goal_async()
            self._node.get_logger().info(f'{self._pool_id}: CleanFloor cancellation requested')
            cancelled = True
        
        if self._move_fish_handle is not None:
            self._move_fish_handle.cancel_goal_async()
            self._node.get_logger().info(f'{self._pool_id}: MoveFish cancellation requested')
            cancelled = True
        
        return cancelled

    # --- CleanFloor handlers ---
    def _handle_floor_feedback(self, feedback_msg) -> None:
        if self._floor_feedback_callback:
            self._floor_feedback_callback(feedback_msg.feedback)

    def _handle_floor_goal_response(self, future, done_callback: Optional[Callable]) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._node.get_logger().warn(f'{self._pool_id}: CleanFloor goal rejected')
            self._clean_floor_handle = None
            return

        self._clean_floor_handle = goal_handle
        self._node.get_logger().info(f'{self._pool_id}: CleanFloor goal accepted')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self._handle_floor_result(f, done_callback)
        )

    def _handle_floor_result(self, future, done_callback: Optional[Callable]) -> None:
        result = future.result().result
        self._clean_floor_handle = None
        if done_callback:
            done_callback(result)

    # --- CleanWall handlers ---
    def _handle_wall_feedback(self, feedback_msg) -> None:
        if self._wall_feedback_callback:
            self._wall_feedback_callback(feedback_msg.feedback)

    def _handle_wall_goal_response(self, future, done_callback: Optional[Callable]) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._node.get_logger().warn(f'{self._pool_id}: CleanWall goal rejected')
            self._clean_wall_handle = None
            return

        self._clean_wall_handle = goal_handle
        self._node.get_logger().info(f'{self._pool_id}: CleanWall goal accepted')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self._handle_wall_result(f, done_callback)
        )

    def _handle_wall_result(self, future, done_callback: Optional[Callable]) -> None:
        result = future.result().result
        self._clean_wall_handle = None
        if done_callback:
            done_callback(result)

    # --- MoveFish handlers ---
    def _handle_fish_feedback(self, feedback_msg) -> None:
        if self._fish_feedback_callback:
            self._fish_feedback_callback(feedback_msg.feedback)

    def _handle_fish_goal_response(self, future, done_callback: Optional[Callable]) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._node.get_logger().warn(f'{self._pool_id}: MoveFish goal rejected')
            self._move_fish_handle = None
            return

        self._move_fish_handle = goal_handle
        self._node.get_logger().info(f'{self._pool_id}: MoveFish goal accepted')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f: self._handle_fish_result(f, done_callback)
        )

    def _handle_fish_result(self, future, done_callback: Optional[Callable]) -> None:
        result = future.result().result
        self._move_fish_handle = None
        if done_callback:
            done_callback(result)
