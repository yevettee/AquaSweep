"""CleanFloor action handler — Isaac Sim step_sync 신호 기반 나선 구동.

Isaac Sim이 매 physics step 끝마다 /{pool_id}/step_sync 를 발행하면
이 핸들러가 플래너를 한 스텝 진행하고 cmd_vel을 발행한다.

장점: time.sleep() 대신 물리스텝과 1:1 동기화 → 시뮬레이션이 느려도 나선 궤적 유지.
"""

import threading
from typing import TYPE_CHECKING

from rclpy.node import Node
from rclpy.action import GoalResponse, CancelResponse
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty

from aqua_interfaces.action import CleanFloor
from .base_handler import BaseHandler

if TYPE_CHECKING:
    from ..spiral_planner import SpiralPlanner

_be1 = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)


class CleanFloorHandler(BaseHandler):

    def __init__(
        self,
        node: Node,
        planner: 'SpiralPlanner',
        cmd_vel_publisher,
        pool_id: str = 'pool_1',
    ):
        super().__init__(node)
        self._planner = planner
        self._cmd_vel_pub = cmd_vel_publisher
        self._pool_id = pool_id

        self._cancel_requested = False
        self._spiral_active = False
        self._spiral_done = threading.Event()
        self._lock = threading.Lock()

        # Isaac Sim 물리스텝 동기 신호 구독
        self._node.create_subscription(
            Empty,
            f'/{pool_id}/step_sync',
            self._on_step_sync,
            _be1,
        )
        self.logger.info(f'CleanFloorHandler: step_sync 구독 → /{pool_id}/step_sync')

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._spiral_active

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
        self._spiral_done.clear()

        with self._lock:
            self._spiral_active = True

        self.logger.info(f'CleanFloor started — Isaac Sim step_sync 대기 중 ({self._pool_id})')

        feedback = CleanFloor.Feedback()
        result = CleanFloor.Result()
        total = self._planner.total_segments

        # Isaac Sim step_sync 콜백이 플래너를 구동하는 동안 대기
        while not self._spiral_done.is_set():
            if goal_handle.is_cancel_requested or self._cancel_requested:
                with self._lock:
                    self._spiral_active = False
                self._publish_zero()
                goal_handle.canceled()
                result.success = False
                return result

            cur = self._planner.current_segment
            if total > 0:
                feedback.progress = float(cur) / float(total)
                self.publish_feedback(goal_handle, feedback)

            self._spiral_done.wait(timeout=0.5)

        result.success = True
        goal_handle.succeed()
        self.logger.info('CleanFloor complete')
        return result

    # ------------------------------------------------------------------
    # Step sync callback — Isaac Sim 물리스텝마다 호출됨
    # ------------------------------------------------------------------

    def _on_step_sync(self, _msg: Empty) -> None:
        """Isaac Sim physics step 1회 = 플래너 1스텝 진행 + cmd_vel 발행."""
        with self._lock:
            if not self._spiral_active:
                return

            if self._planner.is_done:
                self._spiral_active = False
                self._publish_zero()
                self._spiral_done.set()
                return

            v, omega = self._planner.next_cmd()

        twist = Twist()
        twist.linear.x = v
        twist.angular.z = omega
        self._cmd_vel_pub.publish(twist)

        with self._lock:
            if self._planner.is_done:
                self._spiral_active = False
                self._publish_zero()
                self._spiral_done.set()

    # ------------------------------------------------------------------

    def _publish_zero(self) -> None:
        self._cmd_vel_pub.publish(Twist())
