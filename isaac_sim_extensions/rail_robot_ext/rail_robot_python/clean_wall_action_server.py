"""CleanWall Action Server for Isaac Sim.

Provides ROS2 action server interface for wall cleaning via rail robots.
This runs inside Isaac Sim and controls RailRobotScenario instances.

IMPORTANT: Do not import rclpy at module level. Use lazy import pattern
after configure_isaac_ros_env() is called. See common/README.md.
"""

from typing import Optional
import threading
import time

import carb

from .scenario import RailRobotScenario
from .global_variables import RAIL_STEPS

LOG_TAG = "[rail_robot]"

# Lazy-loaded class placeholder
_CleanWallActionServer = None
_CleanWallActionServerManager = None


def _build_action_server_classes() -> bool:
    """Build action server classes with lazy ROS2 import.
    
    This must be called AFTER configure_isaac_ros_env() has been invoked.
    """
    global _CleanWallActionServer, _CleanWallActionServerManager
    
    if _CleanWallActionServer is not None:
        return True
    
    try:
        from rclpy.node import Node
        from rclpy.action import ActionServer, GoalResponse, CancelResponse
        from rclpy.action.server import ServerGoalHandle
        from rclpy.callback_groups import ReentrantCallbackGroup
        from aqua_interfaces.action import CleanWall
    except ImportError as e:
        carb.log_warn(f"{LOG_TAG} ROS2 import failed: {e}")
        return False

    class CleanWallActionServerImpl:
        """Action server for CleanWall that controls RailRobotScenario."""

        def __init__(
            self,
            node: Node,
            pool_id: str,
            scenario: RailRobotScenario,
        ):
            self._node = node
            self._pool_id = pool_id
            self._scenario = scenario
            self._current_goal: Optional[ServerGoalHandle] = None
            self._lock = threading.Lock()

            self._server = ActionServer(
                node,
                CleanWall,
                f'/{pool_id}/clean_wall',
                execute_callback=self._execute_callback,
                goal_callback=self._goal_callback,
                cancel_callback=self._cancel_callback,
                callback_group=ReentrantCallbackGroup(),
            )
            carb.log_info(f"{LOG_TAG} CleanWall action server ready: /{pool_id}/clean_wall")

        def _goal_callback(self, goal_request) -> GoalResponse:
            """Handle incoming goal request."""
            with self._lock:
                if self._current_goal is not None:
                    carb.log_warn(f"{LOG_TAG} [{self._pool_id}] CleanWall: rejecting goal, task in progress")
                    return GoalResponse.REJECT
                if self._scenario.is_running:
                    carb.log_warn(f"{LOG_TAG} [{self._pool_id}] CleanWall: rejecting goal, scenario running")
                    return GoalResponse.REJECT
            carb.log_info(f"{LOG_TAG} [{self._pool_id}] CleanWall: accepting goal")
            return GoalResponse.ACCEPT

        def _cancel_callback(self, goal_handle: ServerGoalHandle) -> CancelResponse:
            """Handle cancel request."""
            carb.log_info(f"{LOG_TAG} [{self._pool_id}] CleanWall: cancel requested")
            return CancelResponse.ACCEPT

        def _execute_callback(self, goal_handle: ServerGoalHandle) -> CleanWall.Result:
            """Execute the CleanWall action."""
            result = CleanWall.Result()
            feedback = CleanWall.Feedback()

            with self._lock:
                self._current_goal = goal_handle

            carb.log_info(f"{LOG_TAG} [{self._pool_id}] CleanWall: starting wall cleaning")

            try:
                self._scenario.start()

                while self._scenario.is_running:
                    if goal_handle.is_cancel_requested:
                        self._scenario.stop()
                        goal_handle.canceled()
                        carb.log_info(f"{LOG_TAG} [{self._pool_id}] CleanWall: canceled")
                        result.success = False
                        return result

                    progress = self._get_progress()
                    feedback.progress = progress
                    goal_handle.publish_feedback(feedback)
                    time.sleep(0.1)

                result.success = True
                goal_handle.succeed()
                carb.log_info(f"{LOG_TAG} [{self._pool_id}] CleanWall: completed successfully")

            except Exception as e:
                carb.log_error(f"{LOG_TAG} [{self._pool_id}] CleanWall: error - {e}")
                result.success = False
                goal_handle.abort()

            finally:
                with self._lock:
                    self._current_goal = None

            return result

        def _get_progress(self) -> float:
            """Calculate cleaning progress from scenario state."""
            try:
                step_count = self._scenario._rail_step_count
                return min(1.0, step_count / float(RAIL_STEPS))
            except Exception:
                return 0.0

    class CleanWallActionServerManagerImpl:
        """Manages CleanWall action servers for all pools."""

        def __init__(self):
            self._node: Optional[Node] = None
            self._servers: dict[str, CleanWallActionServerImpl] = {}

        def initialize(
            self,
            ros_executor,
            pool_ids: list[str],
            rail_scenarios: list[RailRobotScenario],
        ) -> bool:
            """Initialize action servers for all pools.

            Args:
                ros_executor: ROS executor to add node to
                pool_ids: List of pool IDs (e.g., ['pool_1', 'pool_2', ...])
                rail_scenarios: List of RailRobotScenario instances (same order as pool_ids)

            Returns:
                True if successful, False otherwise
            """
            if ros_executor is None:
                carb.log_warn(f"{LOG_TAG} CleanWall server: no ROS executor")
                return False

            try:
                self._node = Node('rail_robot_clean_wall_server')
                ros_executor.add_node(self._node)

                for i, pool_id in enumerate(pool_ids):
                    if i < len(rail_scenarios):
                        server = CleanWallActionServerImpl(
                            self._node,
                            pool_id,
                            rail_scenarios[i],
                        )
                        self._servers[pool_id] = server

                carb.log_info(f"{LOG_TAG} CleanWall servers initialized for {len(self._servers)} pools")
                return True

            except Exception as e:
                carb.log_error(f"{LOG_TAG} CleanWall server init failed: {e}")
                return False

        def cleanup(self) -> None:
            """Cleanup action servers."""
            self._servers.clear()
            if self._node is not None:
                try:
                    self._node.destroy_node()
                except Exception:
                    pass
                self._node = None

    _CleanWallActionServer = CleanWallActionServerImpl
    _CleanWallActionServerManager = CleanWallActionServerManagerImpl
    return True


def create_clean_wall_manager() -> Optional["_CleanWallActionServerManager"]:
    """Factory function to create CleanWall action server manager.
    
    This must be called AFTER configure_isaac_ros_env() has been invoked.
    Returns None if ROS2 is not available.
    """
    if not _build_action_server_classes():
        return None
    return _CleanWallActionServerManager()
