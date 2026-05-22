"""CleanFloor action handler — drives SpiralPlanner over an Action Server execute callback.

Blocking execute loop: time.sleep() is correct here because ActionServer
callbacks run in a dedicated thread (MultiThreadedExecutor).
"""

import time
from typing import TYPE_CHECKING

from rclpy.node import Node
from rclpy.action import GoalResponse, CancelResponse
from geometry_msgs.msg import Twist

from aqua_interfaces.action import CleanFloor
from .base_handler import BaseHandler

if TYPE_CHECKING:
    from ..spiral_planner import SpiralPlanner

CONTROL_HZ = 60.0


class CleanFloorHandler(BaseHandler):

    def __init__(
        self,
        node: Node,
        planner: 'SpiralPlanner',
        cmd_vel_publisher,
        control_hz: float = CONTROL_HZ,
    ):
        super().__init__(node)
        self._planner = planner
        self._cmd_vel_pub = cmd_vel_publisher
        self._control_period = 1.0 / control_hz
        self._cancel_requested = False

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def handle_goal(self, goal_request: CleanFloor.Goal) -> GoalResponse:
        self.logger.info('CleanFloor goal received')
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        self.logger.info('CleanFloor cancel requested')
        self._cancel_requested = True
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> CleanFloor.Result:
        self._cancel_requested = False
        self._planner.reset()
        self.logger.info('CleanFloor started')

        feedback = CleanFloor.Feedback()
        result = CleanFloor.Result()
        total = self._planner.total_segments
        last_seg = 0

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

            cur = self._planner.current_segment
            if cur > last_seg:
                last_seg = cur
                feedback.progress = float(cur) / float(total)
                self.publish_feedback(goal_handle, feedback)

            time.sleep(self._control_period)

        self._publish_zero()
        self.logger.info('CleanFloor complete')
        result.success = True
        goal_handle.succeed()
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _publish_zero(self) -> None:
        self._cmd_vel_pub.publish(Twist())
