"""CleanWall action handler — stub (rail_robot not yet integrated)."""

import time

from rclpy.action import GoalResponse, CancelResponse

from aqua_interfaces.action import CleanWall
from .base_handler import BaseHandler

_STUB_STEPS = 5
_STUB_STEP_DURATION = 0.5


class CleanWallHandler(BaseHandler):

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def handle_goal(self, goal_request: CleanWall.Goal) -> GoalResponse:
        self.logger.info('CleanWall goal received')
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        self.logger.info('CleanWall cancel requested')
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> CleanWall.Result:
        self.logger.info('CleanWall started (stub)')
        feedback = CleanWall.Feedback()
        result = CleanWall.Result()

        for i in range(_STUB_STEPS):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.logger.info('CleanWall canceled')
                result.success = False
                return result

            feedback.progress = (i + 1) / float(_STUB_STEPS)
            self.publish_feedback(goal_handle, feedback)
            time.sleep(_STUB_STEP_DURATION)

        self.logger.info('CleanWall complete (stub)')
        result.success = True
        goal_handle.succeed()
        return result
