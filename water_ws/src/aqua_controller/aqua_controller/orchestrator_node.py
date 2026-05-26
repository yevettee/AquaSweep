"""AquaSweep Orchestrator Node

대시보드의 "Global Start" 버튼 → /planner/start (Trigger 서비스) → 전체 로봇 동시 청소 시작.
개별 풀은 대시보드의 "Start Pool N" 버튼이 /pool_N/clean_floor 액션으로 직접 트리거합니다.

Parameters
----------
pool_ids : string[]
    이번 청소 대상 pool ID 목록. 기본값: ['pool_1', ..., 'pool_7']
    상황에 따라 일부만 지정하면 해당 로봇들만 동시 시작합니다.
"""

from functools import partial

import rclpy
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Trigger

from aqua_interfaces.action import CleanFloor

_DEFAULT_POOLS = [f'pool_{i}' for i in range(1, 8)]


class OrchestratorNode(Node):

    def __init__(self) -> None:
        super().__init__('aqua_orchestrator')

        self.declare_parameter('pool_ids', _DEFAULT_POOLS)
        pool_ids: list = self.get_parameter('pool_ids').value

        self._cb = ReentrantCallbackGroup()
        self._action_clients: dict[str, ActionClient] = {
            pid: ActionClient(
                self, CleanFloor, f'/{pid}/clean_floor',
                callback_group=self._cb,
            )
            for pid in pool_ids
        }

        self._total    = len(self._action_clients)
        self._running  = False
        self._done:     dict[str, bool]  = {}
        self._progress: dict[str, float] = {pid: 0.0 for pid in pool_ids}

        # 대시보드 "Global Start" 버튼이 호출하는 서비스
        self.create_service(
            Trigger, '/planner/start', self._handle_start,
            callback_group=self._cb,
        )

        self.get_logger().info(
            f'Orchestrator ready | target pools ({self._total}): {pool_ids}\n'
            f'  trigger: /planner/start (std_srvs/Trigger)'
        )

    # ------------------------------------------------------------------
    # /planner/start 서비스 핸들러
    # ------------------------------------------------------------------

    def _handle_start(self, request: Trigger.Request, response: Trigger.Response):
        if self._running:
            response.success = False
            response.message = 'Cleaning already in progress'
            self.get_logger().warn('Global start rejected: already running')
            return response

        not_ready = [
            pid for pid, c in self._action_clients.items()
            if not c.server_is_ready()
        ]
        if not_ready:
            response.success = False
            response.message = f'Action servers not ready: {not_ready}'
            self.get_logger().error(response.message)
            return response

        # 상태 초기화 후 전체 동시 시작
        self._running  = True
        self._done     = {}
        self._progress = {pid: 0.0 for pid in self._action_clients}

        self.get_logger().info(
            f'Global start — sending goals to {self._total} pools simultaneously'
        )
        self._send_all_goals()

        response.success = True
        response.message = f'Started {self._total} pools'
        return response

    # ------------------------------------------------------------------
    # Goal dispatch
    # ------------------------------------------------------------------

    def _send_all_goals(self) -> None:
        for pool_id, client in self._action_clients.items():
            future = client.send_goal_async(
                CleanFloor.Goal(),
                feedback_callback=partial(self._feedback_cb, pool_id),
            )
            future.add_done_callback(partial(self._goal_response_cb, pool_id))

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _feedback_cb(self, pool_id: str, feedback_msg) -> None:
        p    = feedback_msg.feedback.progress
        prev = self._progress[pool_id]
        self._progress[pool_id] = p

        # 10% 단위 마일스톤에서만 로그
        if int(p * 10) > int(prev * 10):
            overall = sum(self._progress.values()) / self._total
            self.get_logger().info(
                f'[{pool_id}] {p:.0%} | 전체 진행: {overall:.0%}'
            )

    def _goal_response_cb(self, pool_id: str, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f'[{pool_id}] goal REJECTED')
            self._done[pool_id] = False
            self._check_all_done()
            return
        self.get_logger().info(f'[{pool_id}] 청소 시작')
        goal_handle.get_result_async().add_done_callback(
            partial(self._result_cb, pool_id)
        )

    def _result_cb(self, pool_id: str, future) -> None:
        result = future.result().result
        self._done[pool_id] = result.success
        status = '완료' if result.success else 'FAILED'
        self.get_logger().info(
            f'[{pool_id}] {status}  ({len(self._done)}/{self._total} 완료)'
        )
        self._check_all_done()

    def _check_all_done(self) -> None:
        if len(self._done) < self._total:
            return

        self._running = False
        ok     = sum(self._done.values())
        failed = [pid for pid, s in self._done.items() if not s]
        if failed:
            self.get_logger().warn(
                f'전체 청소 종료 — {ok}/{self._total} 성공 | 실패: {failed}'
            )
        else:
            self.get_logger().info(f'전체 청소 완료 — {self._total}대 모두 성공')


# ---------------------------------------------------------------------------

def main(args=None) -> None:
    rclpy.init(args=args)
    node = OrchestratorNode()
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
