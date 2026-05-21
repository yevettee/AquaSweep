"""MoveFish action handler - stub implementation."""

import time

from rclpy.action import GoalResponse, CancelResponse

from aqua_interfaces.action import MoveFish
from .base_handler import BaseHandler


class MoveFishHandler(BaseHandler):
    """Handles MoveFish action (stub - returns success immediately).
    
    TODO: Implement actual fish transfer logic:
        1. Move to source pool
        2. Pick fish (suction)
        3. Move to target pool
        4. Place fish
        5. Repeat until fish_count reached
    """

    PHASE_MOVING_TO_SOURCE = 0
    PHASE_PICKING = 1
    PHASE_MOVING_TO_TARGET = 2
    PHASE_PLACING = 3

    def handle_goal(self, goal_request: MoveFish.Goal) -> GoalResponse:
        """Accept or reject incoming goal."""
        self.logger.info(
            f'MoveFish goal received (stub): '
            f'{goal_request.source_pool} -> {goal_request.target_pool}, '
            f'count={goal_request.fish_count}'
        )
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        """Handle cancel request."""
        self.logger.info('MoveFish cancel requested')
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> MoveFish.Result:
        """Execute MoveFish action (stub - simulates phases).
        
        TODO: Replace with actual robot control and fish handling logic.
        """
        goal = goal_handle.request
        self.logger.info(
            f'MoveFish execution started (stub): '
            f'{goal.source_pool} -> {goal.target_pool}'
        )

        feedback = MoveFish.Feedback()
        result = MoveFish.Result()

        phases = [
            (self.PHASE_MOVING_TO_SOURCE, 'Moving to source'),
            (self.PHASE_PICKING, 'Picking fish'),
            (self.PHASE_MOVING_TO_TARGET, 'Moving to target'),
            (self.PHASE_PLACING, 'Placing fish'),
        ]

        fish_to_move = goal.fish_count if goal.fish_count > 0 else 3
        fish_moved = 0

        for phase_id, phase_name in phases:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.logger.info('MoveFish canceled')
                result.success = False
                result.fish_moved = fish_moved
                result.message = 'Canceled'
                return result

            self.logger.info(f'  Phase: {phase_name}')
            feedback.phase = phase_id
            feedback.progress = (phase_id + 1) / 4.0
            feedback.fish_picked_so_far = fish_moved
            self.publish_feedback(goal_handle, feedback)
            time.sleep(0.5)

        fish_moved = fish_to_move

        self.logger.info(f'MoveFish completed (stub): moved {fish_moved} fish')
        result.success = True
        result.fish_moved = fish_moved
        result.message = f'Moved {fish_moved} fish from {goal.source_pool} to {goal.target_pool}'
        goal_handle.succeed()
        return result
