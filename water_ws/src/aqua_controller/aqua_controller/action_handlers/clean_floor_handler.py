"""CleanFloor action handler - actual implementation with SpiralPlanner."""

import time
from typing import TYPE_CHECKING

from rclpy.node import Node
from rclpy.action import GoalResponse, CancelResponse
from geometry_msgs.msg import Twist

from aqua_interfaces.action import CleanFloor
from .base_handler import BaseHandler

if TYPE_CHECKING:
    from ..spiral_planner import SpiralPlanner


class CleanFloorHandler(BaseHandler):
    """Handles CleanFloor action with SpiralPlanner integration."""

    def __init__(
        self,
        node: Node,
        planner: 'SpiralPlanner',
        cmd_vel_publisher,
        control_hz: float = 60.0
    ):
        super().__init__(node)
        self._planner = planner
        self._cmd_vel_pub = cmd_vel_publisher
        self._control_period = 1.0 / control_hz
        self._cancel_requested = False

    def handle_goal(self, goal_request: CleanFloor.Goal) -> GoalResponse:
        """Accept or reject incoming goal."""
        self.logger.info('CleanFloor goal received')
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        """Handle cancel request."""
        self.logger.info('CleanFloor cancel requested')
        self._cancel_requested = True
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> CleanFloor.Result:
        """Execute CleanFloor action using SpiralPlanner."""
        self.logger.info('CleanFloor execution started')
        self._cancel_requested = False
        self._planner.reset()

        feedback = CleanFloor.Feedback()
        result = CleanFloor.Result()

        total_segments = self._planner.total_segments
        segments_done = 0

        while not self._planner.is_done:
            if goal_handle.is_cancel_requested or self._cancel_requested:
                self._publish_zero()
                goal_handle.canceled()
                self.logger.info('CleanFloor canceled')
                result.success = False
                return result

            v, omega = self._planner.next_cmd()
            msg = Twist()
            msg.linear.x = v
            msg.angular.z = omega
            self._cmd_vel_pub.publish(msg)

            if self._planner._seg_idx > segments_done:
                segments_done = self._planner._seg_idx
                feedback.progress = float(segments_done) / float(total_segments)
                self.publish_feedback(goal_handle, feedback)

            time.sleep(self._control_period)

        self._publish_zero()
        self.logger.info('CleanFloor completed')

        result.success = True
        goal_handle.succeed()
        return result

    def _publish_zero(self) -> None:
        """Stop the robot."""
        self._cmd_vel_pub.publish(Twist())
