"""MoveFish action handler — stub (pick-and-place not yet integrated)."""

import time

from rclpy.action import GoalResponse, CancelResponse

from aqua_interfaces.action import MoveFish
from .base_handler import BaseHandler

_DEFAULT_FISH_COUNT = 3
_PHASE_DURATION = 0.5
_PHASES = [
    (0, 'Moving to source'),
    (1, 'Picking fish'),
    (2, 'Moving to target'),
    (3, 'Placing fish'),
]


class MoveFishHandler(BaseHandler):

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def handle_goal(self, goal_request: MoveFish.Goal) -> GoalResponse:
        self.logger.info(
            f'MoveFish goal received: '
            f'{goal_request.source_pool} -> {goal_request.target_pool}, '
            f'count={goal_request.fish_count}'
        )
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        self.logger.info('MoveFish cancel requested')
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> MoveFish.Result:
        goal = goal_handle.request
        self.logger.info(
            f'MoveFish started: {goal.source_pool} -> {goal.target_pool}'
        )

        feedback = MoveFish.Feedback()
        result = MoveFish.Result()
        fish_to_move = goal.fish_count if goal.fish_count > 0 else _DEFAULT_FISH_COUNT

        for phase_id, phase_name in _PHASES:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.logger.info('MoveFish canceled')
                result.success = False
                result.fish_moved = 0
                result.message = 'Canceled'
                return result

            self.logger.info(f'  Phase: {phase_name}')
            feedback.phase = phase_id
            feedback.progress = (phase_id + 1) / float(len(_PHASES))
            feedback.fish_picked_so_far = fish_to_move if phase_id >= 1 else 0
            self.publish_feedback(goal_handle, feedback)
            time.sleep(_PHASE_DURATION)

        self.logger.info(f'MoveFish complete: moved {fish_to_move} fish')
        result.success = True
        result.fish_moved = fish_to_move
        result.message = f'Moved {fish_to_move} fish from {goal.source_pool} to {goal.target_pool}'
        goal_handle.succeed()
        return result
