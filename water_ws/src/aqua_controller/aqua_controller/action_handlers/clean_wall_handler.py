"""CleanWall action handler — Isaac Sim 서비스 모드.

Isaac Sim에 서비스 호출 (start_clean_wall)을 통해 벽면 청소를 시작하고,
Isaac Sim 내부 RailRobotScenario가 모션을 실행합니다.
이 핸들러는 motion_status 토픽으로 진행상황을 모니터링합니다.
"""

import threading
import time

from rclpy.node import Node
from rclpy.action import GoalResponse, CancelResponse
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from aqua_interfaces.action import CleanWall
from aqua_interfaces.msg import MotionStatus
from aqua_interfaces.srv import StartMotion, StopMotion, PauseMotion, ResumeMotion
from .base_handler import BaseHandler

_be1 = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)


class CleanWallHandler(BaseHandler):

    def __init__(self, node: Node, pool_id: str = 'pool_1'):
        super().__init__(node)
        self._pool_id = pool_id

        self._cancel_requested = False
        self._active = False
        self._done_event = threading.Event()
        self._lock = threading.Lock()

        self._motion_progress = 0.0
        self._motion_state = MotionStatus.IDLE

        self._init_service_clients()

    def _init_service_clients(self) -> None:
        """서비스 클라이언트 및 상태 토픽 구독 초기화."""
        self._start_client = self._node.create_client(
            StartMotion, f'/{self._pool_id}/start_clean_wall'
        )
        self._stop_client = self._node.create_client(
            StopMotion, f'/{self._pool_id}/stop_clean_wall'
        )
        self._pause_client = self._node.create_client(
            PauseMotion, f'/{self._pool_id}/pause_clean_wall'
        )
        self._resume_client = self._node.create_client(
            ResumeMotion, f'/{self._pool_id}/resume_clean_wall'
        )
        self._node.create_subscription(
            MotionStatus,
            f'/{self._pool_id}/clean_wall_status',
            self._on_motion_status,
            _be1,
        )
        self.logger.info(f'CleanWallHandler: /{self._pool_id}/start_clean_wall')

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------

    def handle_goal(self, goal_request: CleanWall.Goal) -> GoalResponse:
        self.logger.info('CleanWall goal received')
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle) -> CancelResponse:
        self.logger.info('CleanWall cancel requested')
        self._cancel_requested = True
        self._call_stop_service()
        return CancelResponse.ACCEPT

    def execute(self, goal_handle) -> CleanWall.Result:
        """Isaac Sim 서비스 호출 + motion_status 모니터링."""
        self._cancel_requested = False
        self._done_event.clear()
        self._motion_progress = 0.0

        with self._lock:
            self._active = True

        if not self._call_start_service():
            with self._lock:
                self._active = False
            result = CleanWall.Result()
            result.success = False
            goal_handle.abort()
            return result

        self.logger.info(f'CleanWall started ({self._pool_id})')

        feedback = CleanWall.Feedback()
        result = CleanWall.Result()

        while not self._done_event.is_set():
            if goal_handle.is_cancel_requested or self._cancel_requested:
                with self._lock:
                    self._active = False
                self._call_stop_service()
                goal_handle.canceled()
                result.success = False
                return result

            with self._lock:
                feedback.progress = self._motion_progress

            self.publish_feedback(goal_handle, feedback)
            self._done_event.wait(timeout=0.5)

        result.success = True
        goal_handle.succeed()
        self.logger.info('CleanWall complete')
        return result

    def _call_start_service(self) -> bool:
        """Isaac Sim에 start_clean_wall 서비스 호출."""
        if not self._start_client.wait_for_service(timeout_sec=2.0):
            self.logger.error('start_clean_wall 서비스 없음')
            return False

        request = StartMotion.Request()
        future = self._start_client.call_async(request)

        for _ in range(20):
            if future.done():
                break
            time.sleep(0.1)

        if future.done() and future.result().success:
            return True
        self.logger.error('start_clean_wall 서비스 실패')
        return False

    def _call_stop_service(self) -> None:
        """Isaac Sim에 stop_clean_wall 서비스 호출."""
        if not self._stop_client.wait_for_service(timeout_sec=1.0):
            return
        request = StopMotion.Request()
        self._stop_client.call_async(request)

    def _on_motion_status(self, msg: MotionStatus) -> None:
        """motion_status 토픽 콜백."""
        with self._lock:
            self._motion_progress = msg.progress
            self._motion_state = msg.state

            if msg.state == MotionStatus.DONE:
                self._active = False
                self._done_event.set()
