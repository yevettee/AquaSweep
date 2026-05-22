"""Planner node for AquaSweep - 전체 풀 오케스트레이션.

Services:
    /planner/start                  - 전체 풀 CleanFloor 동시 시작
    /planner/pause                  - 전체 풀 작업 취소
    /{pool_id}/start_clean_floor    - 개별 풀 CleanFloor 시작 (pool_1 ~ pool_N)
"""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from .task_executor import TaskExecutor


class PlannerNode(Node):
    """풀 전체/개별 CleanFloor 제어 플래너."""

    def __init__(self) -> None:
        super().__init__('aqua_planner')

        self.declare_parameter('num_pools', 7)
        num_pools = self.get_parameter('num_pools').get_parameter_value().integer_value

        pool_ids = [f'pool_{i}' for i in range(1, num_pools + 1)]

        # 풀별 TaskExecutor 및 실행 상태
        self._executors: dict[str, TaskExecutor] = {
            pid: TaskExecutor(self, pool_id=pid) for pid in pool_ids
        }
        self._running: dict[str, bool] = {pid: False for pid in pool_ids}

        # 전체 제어 서비스
        self.create_service(Trigger, '/planner/start', self._handle_start_all)
        self.create_service(Trigger, '/planner/pause', self._handle_pause_all)

        # 개별 풀 서비스 — 람다에서 pool_id를 기본값으로 캡처
        for pid in pool_ids:
            self.create_service(
                Trigger,
                f'/{pid}/start_clean_floor',
                lambda req, res, p=pid: self._handle_start_pool(req, res, p),
            )

        svc_list = ' | '.join(f'/{p}/start_clean_floor' for p in pool_ids)
        self.get_logger().info(
            f'PlannerNode ready | pools={pool_ids}\n'
            f'  global  : /planner/start | /planner/pause\n'
            f'  per-pool: {svc_list}'
        )

    # ------------------------------------------------------------------
    # 전체 제어
    # ------------------------------------------------------------------

    def _handle_start_all(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """전체 풀 CleanFloor 동시 시작."""
        already = [p for p, r in self._running.items() if r]
        if already:
            response.success = False
            response.message = f'Already running: {already}'
            return response

        started, failed = [], []
        for pid, executor in self._executors.items():
            ok = executor.send_clean_floor_goal(
                feedback_callback=lambda fb, p=pid: self._on_feedback(p, fb),
                done_callback=lambda res, p=pid: self._on_done(p, res),
            )
            if ok:
                self._running[pid] = True
                started.append(pid)
            else:
                failed.append(pid)

        if started:
            response.success = True
            response.message = f'Started: {started}' + (f' | Failed: {failed}' if failed else '')
        else:
            response.success = False
            response.message = f'All failed: {failed}'

        self.get_logger().info(response.message)
        return response

    def _handle_pause_all(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """실행 중인 전체 풀 취소."""
        running = [p for p, r in self._running.items() if r]
        if not running:
            response.success = False
            response.message = 'No tasks running'
            return response

        for pid in running:
            self._executors[pid].cancel_current_goal()

        response.success = True
        response.message = f'Cancellation requested: {running}'
        self.get_logger().info(response.message)
        return response

    # ------------------------------------------------------------------
    # 개별 풀 제어
    # ------------------------------------------------------------------

    def _handle_start_pool(
        self, request: Trigger.Request, response: Trigger.Response, pool_id: str
    ) -> Trigger.Response:
        """특정 풀만 CleanFloor 시작."""
        if self._running.get(pool_id):
            response.success = False
            response.message = f'{pool_id} already running'
            return response

        ok = self._executors[pool_id].send_clean_floor_goal(
            feedback_callback=lambda fb: self._on_feedback(pool_id, fb),
            done_callback=lambda res: self._on_done(pool_id, res),
        )

        if ok:
            self._running[pool_id] = True
            response.success = True
            response.message = f'CleanFloor started: {pool_id}'
        else:
            response.success = False
            response.message = f'Failed to start {pool_id} (server not available)'

        self.get_logger().info(response.message)
        return response

    # ------------------------------------------------------------------
    # 콜백
    # ------------------------------------------------------------------

    def _on_feedback(self, pool_id: str, feedback) -> None:
        self.get_logger().info(f'[{pool_id}] Progress: {feedback.progress * 100:.1f}%')

    def _on_done(self, pool_id: str, result) -> None:
        self._running[pool_id] = False
        if result.success:
            self.get_logger().info(f'[{pool_id}] Completed')
        else:
            self.get_logger().warn(f'[{pool_id}] Failed')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
