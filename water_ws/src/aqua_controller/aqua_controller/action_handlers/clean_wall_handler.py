"""CleanWall action handler - stub implementation."""

import time

from rclpy.action import GoalResponse, CancelResponse

from aqua_interfaces.action import CleanWall
from .base_handler import BaseHandler


class CleanWallHandler(BaseHandler):
    """Handles CleanWall action (stub - returns success immediately).
    
    TODO: Implement actual wall cleaning logic with rail_robot control.
    """

    def handle_goal(self, goal_request: CleanWall.Goal) -> GoalResponse:
        """Accept or reject incoming goal."""
        self.logger.info('CleanWall goal received (stub)')
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        """Handle cancel request."""
        self.logger.info('CleanWall cancel requested')
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> CleanWall.Result:
        """Execute CleanWall action (stub - simulates work).
        
        TODO: Replace with actual rail_robot control logic.
        """
        self.logger.info('CleanWall execution started (stub)')

        feedback = CleanWall.Feedback()
        result = CleanWall.Result()

        for i in range(5):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.logger.info('CleanWall canceled')
                result.success = False
                return result

            feedback.progress = (i + 1) / 5.0
            self.publish_feedback(goal_handle, feedback)
            time.sleep(0.5)

        self.logger.info('CleanWall completed (stub)')
        result.success = True
        goal_handle.succeed()
        return result
