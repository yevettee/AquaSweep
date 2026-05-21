"""Mockup controller server for testing planner-controller communication.

Provides Action Servers that accept goals and return dummy results.
Use this to test planner without actual robot control.

Actions:
    /pool_{id}/clean_floor
    /pool_{id}/clean_wall
    /pool_{id}/move_fish
"""

import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from aqua_interfaces.action import CleanFloor, CleanWall, MoveFish


class MockupControllerServer(Node):
    """Mockup Action Servers for testing."""

    def __init__(self) -> None:
        super().__init__('mockup_controller_server')

        self.declare_parameter('pool_id', 'pool_1')
        self.declare_parameter('action_duration', 3.0)

        pool_id = self.get_parameter('pool_id').get_parameter_value().string_value
        self._duration = self.get_parameter('action_duration').get_parameter_value().double_value

        callback_group = ReentrantCallbackGroup()

        self._clean_floor_server = ActionServer(
            self,
            CleanFloor,
            f'/{pool_id}/clean_floor',
            execute_callback=self._execute_clean_floor,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=callback_group
        )

        self._clean_wall_server = ActionServer(
            self,
            CleanWall,
            f'/{pool_id}/clean_wall',
            execute_callback=self._execute_clean_wall,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=callback_group
        )

        self._move_fish_server = ActionServer(
            self,
            MoveFish,
            f'/{pool_id}/move_fish',
            execute_callback=self._execute_move_fish,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=callback_group
        )

        self.get_logger().info(
            f'MockupControllerServer ready | pool={pool_id}\n'
            f'  Actions: /{pool_id}/clean_floor, /{pool_id}/clean_wall, /{pool_id}/move_fish\n'
            f'  Duration: {self._duration}s per action'
        )

    def _execute_clean_floor(self, goal_handle) -> CleanFloor.Result:
        """Simulate CleanFloor action."""
        self.get_logger().info('MockupController: CleanFloor started')

        feedback = CleanFloor.Feedback()
        steps = 10
        step_duration = self._duration / steps

        for i in range(steps):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('MockupController: CleanFloor canceled')
                return CleanFloor.Result(success=False)

            feedback.progress = (i + 1) / steps
            goal_handle.publish_feedback(feedback)
            time.sleep(step_duration)

        self.get_logger().info('MockupController: CleanFloor completed')
        goal_handle.succeed()
        return CleanFloor.Result(success=True)

    def _execute_clean_wall(self, goal_handle) -> CleanWall.Result:
        """Simulate CleanWall action."""
        self.get_logger().info('MockupController: CleanWall started')

        feedback = CleanWall.Feedback()
        steps = 10
        step_duration = self._duration / steps

        for i in range(steps):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('MockupController: CleanWall canceled')
                return CleanWall.Result(success=False)

            feedback.progress = (i + 1) / steps
            goal_handle.publish_feedback(feedback)
            time.sleep(step_duration)

        self.get_logger().info('MockupController: CleanWall completed')
        goal_handle.succeed()
        return CleanWall.Result(success=True)

    def _execute_move_fish(self, goal_handle) -> MoveFish.Result:
        """Simulate MoveFish action."""
        goal = goal_handle.request
        self.get_logger().info(
            f'MockupController: MoveFish started '
            f'({goal.source_pool} -> {goal.target_pool}, count={goal.fish_count})'
        )

        feedback = MoveFish.Feedback()
        phases = [0, 1, 2, 3]
        phase_duration = self._duration / len(phases)

        for i, phase in enumerate(phases):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('MockupController: MoveFish canceled')
                return MoveFish.Result(success=False, fish_moved=0, message='Canceled')

            feedback.phase = phase
            feedback.progress = (i + 1) / len(phases)
            feedback.fish_picked_so_far = goal.fish_count if phase >= 1 else 0
            goal_handle.publish_feedback(feedback)
            time.sleep(phase_duration)

        fish_moved = goal.fish_count if goal.fish_count > 0 else 5
        self.get_logger().info(f'MockupController: MoveFish completed (moved {fish_moved})')
        goal_handle.succeed()
        return MoveFish.Result(
            success=True,
            fish_moved=fish_moved,
            message=f'Moved {fish_moved} fish'
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockupControllerServer()
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
