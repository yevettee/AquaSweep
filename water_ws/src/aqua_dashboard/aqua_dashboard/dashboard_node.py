"""Dashboard node for AquaSweep - subscribes to pool/robot status and controls planner.

This node provides a headless interface for monitoring pool status and triggering
cleaning operations. It can serve as a backend for a web UI or CLI testing.

Subscriptions:
    /pool_{id}/status         - Pool status (PoolStatus)
    /under_robot_{id}/status  - Robot status (RobotStatus)
    /pool_{id}/top_img_det    - Top camera detection image (Image)
    /pool_{id}/under_img_det  - Under camera detection image (Image)

Service Clients:
    /planner/start            - Start cleaning for all eligible pools
    /planner/pause            - Pause all cleaning operations
    /pool_{id}/start_clean_wall - Start cleaning sequence (CleanWall → CleanFloor) for a specific pool

For the GUI version with PyQt5, use:
    ros2 run aqua_dashboard dashboard_gui
"""

from functools import partial
from typing import Callable, Dict, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from aqua_interfaces.msg import RobotStatus, PoolStatus

from .ros_topics import (
    planner_pause_service,
    planner_start_service,
    pool_ids,
    pool_robot_status_topic,
    pool_start_clean_wall_service,
    pool_status_topic,
    pool_top_cam_det_topic,
    pool_under_cam_det_topic,
)

ROBOT_STATE_NAMES = {
    RobotStatus.IDLE: "IDLE",
    RobotStatus.RUNNING: "RUNNING",
    RobotStatus.PAUSED: "PAUSED",
    RobotStatus.DISCHARGED: "DISCHARGED",
}


class DashboardNode(Node):
    """Dashboard node for monitoring pools and controlling the planner.

    This node can be extended with callback hooks for GUI integration.
    Set the on_pool_status, on_robot_status, on_top_cam_image, on_under_cam_image
    callbacks to receive data updates.
    """

    def __init__(self, subscribe_images: bool = False) -> None:
        """Initialize the dashboard node.

        Args:
            subscribe_images: If True, subscribe to camera image topics.
                             Set to False for headless mode to save bandwidth.
        """
        super().__init__('aqua_dashboard')

        self._pool_status: Dict[int, Optional[PoolStatus]] = {}
        self._robot_status: Dict[int, Optional[RobotStatus]] = {}
        self._top_cam_image: Dict[int, Optional[Image]] = {}
        self._under_cam_image: Dict[int, Optional[Image]] = {}
        self._pool_start_clients: Dict[int, object] = {}

        self.on_pool_status: Optional[Callable[[int, PoolStatus], None]] = None
        self.on_robot_status: Optional[Callable[[int, RobotStatus], None]] = None
        self.on_top_cam_image: Optional[Callable[[int, Image], None]] = None
        self.on_under_cam_image: Optional[Callable[[int, Image], None]] = None

        for pool_id in pool_ids():
            self._pool_status[pool_id] = None
            self._robot_status[pool_id] = None
            self._top_cam_image[pool_id] = None
            self._under_cam_image[pool_id] = None

            self.create_subscription(
                PoolStatus,
                pool_status_topic(pool_id),
                partial(self._on_pool_status, pool_id),
                10
            )
            self.create_subscription(
                RobotStatus,
                pool_robot_status_topic(pool_id),
                partial(self._on_robot_status, pool_id),
                10
            )

            if subscribe_images:
                self.create_subscription(
                    Image,
                    pool_top_cam_det_topic(pool_id),
                    partial(self._on_top_cam_image, pool_id),
                    10
                )
                self.create_subscription(
                    Image,
                    pool_under_cam_det_topic(pool_id),
                    partial(self._on_under_cam_image, pool_id),
                    10
                )

            self._pool_start_clients[pool_id] = self.create_client(
                Trigger,
                pool_start_clean_wall_service(pool_id)
            )

        self._planner_start_client = self.create_client(
            Trigger,
            planner_start_service()
        )
        self._planner_pause_client = self.create_client(
            Trigger,
            planner_pause_service()
        )

        self.create_timer(5.0, self._log_status)

        self.get_logger().info(
            f'DashboardNode ready | pools={list(pool_ids())}\n'
            f'  Subscriptions: /pool_<id>/status, /under_robot_<id>/status\n'
            f'  Clients: /planner/start, /planner/pause, /pool_<id>/start_clean_wall'
        )

    def _on_pool_status(self, pool_id: int, msg: PoolStatus) -> None:
        """Handle incoming pool status."""
        self._pool_status[pool_id] = msg
        if self.on_pool_status is not None:
            self.on_pool_status(pool_id, msg)

    def _on_robot_status(self, pool_id: int, msg: RobotStatus) -> None:
        """Handle incoming robot status."""
        prev = self._robot_status.get(pool_id)
        self._robot_status[pool_id] = msg

        if prev is not None and prev.state != msg.state:
            state_name = ROBOT_STATE_NAMES.get(msg.state, str(msg.state))
            self.get_logger().info(f'Robot {pool_id} state changed to {state_name}')

        if self.on_robot_status is not None:
            self.on_robot_status(pool_id, msg)

    def _on_top_cam_image(self, pool_id: int, msg: Image) -> None:
        """Handle incoming top camera image."""
        self._top_cam_image[pool_id] = msg
        if self.on_top_cam_image is not None:
            self.on_top_cam_image(pool_id, msg)

    def _on_under_cam_image(self, pool_id: int, msg: Image) -> None:
        """Handle incoming under camera image."""
        self._under_cam_image[pool_id] = msg
        if self.on_under_cam_image is not None:
            self.on_under_cam_image(pool_id, msg)

    def _log_status(self) -> None:
        """Periodically log current status of all pools."""
        for pool_id in pool_ids():
            pool = self._pool_status.get(pool_id)
            robot = self._robot_status.get(pool_id)

            pool_info = "no data"
            if pool is not None:
                pool_info = f"fish={pool.fish_count}, pollution={pool.pollution_level:.2f}"

            robot_info = "no data"
            if robot is not None:
                state_name = ROBOT_STATE_NAMES.get(robot.state, str(robot.state))
                robot_info = f"state={state_name}, battery={robot.battery_level:.2f}"

            self.get_logger().debug(f'Pool {pool_id}: {pool_info} | Robot: {robot_info}')

    def call_global_start(self) -> None:
        """Call /planner/start service asynchronously."""
        if not self._planner_start_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Planner start service not available')
            return

        request = Trigger.Request()
        future = self._planner_start_client.call_async(request)
        future.add_done_callback(self._on_global_start_response)
        self.get_logger().info('Calling /planner/start...')

    def _on_global_start_response(self, future) -> None:
        """Handle response from /planner/start."""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f'Global start success: {response.message}')
            else:
                self.get_logger().warn(f'Global start failed: {response.message}')
        except Exception as exc:
            self.get_logger().error(f'Global start error: {exc}')

    def call_pool_start(self, pool_id: int) -> None:
        """Call /{pool_id}/start_clean_wall service (CleanWall → CleanFloor sequence)."""
        client = self._pool_start_clients.get(pool_id)
        if client is None:
            self.get_logger().warn(f'No client for pool {pool_id}')
            return

        if not client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn(f'Pool {pool_id} start service not available')
            return

        request = Trigger.Request()
        future = client.call_async(request)
        future.add_done_callback(partial(self._on_pool_start_response, pool_id))
        self.get_logger().info(f'Calling /pool_{pool_id}/start_clean_wall (CleanWall → CleanFloor)...')

    def _on_pool_start_response(self, pool_id: int, future) -> None:
        """Handle response from pool start service."""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f'Pool {pool_id} start success: {response.message}')
            else:
                self.get_logger().warn(f'Pool {pool_id} start failed: {response.message}')
        except Exception as exc:
            self.get_logger().error(f'Pool {pool_id} start error: {exc}')

    def call_pause(self) -> None:
        """Call /planner/pause service asynchronously."""
        if not self._planner_pause_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Planner pause service not available')
            return

        request = Trigger.Request()
        future = self._planner_pause_client.call_async(request)
        future.add_done_callback(self._on_pause_response)
        self.get_logger().info('Calling /planner/pause...')

    def _on_pause_response(self, future) -> None:
        """Handle response from /planner/pause."""
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f'Pause success: {response.message}')
            else:
                self.get_logger().warn(f'Pause failed: {response.message}')
        except Exception as exc:
            self.get_logger().error(f'Pause error: {exc}')

    def get_pool_status(self, pool_id: int) -> Optional[PoolStatus]:
        """Get the latest status for a pool."""
        return self._pool_status.get(pool_id)

    def get_robot_status(self, pool_id: int) -> Optional[RobotStatus]:
        """Get the latest status for a robot."""
        return self._robot_status.get(pool_id)

    def get_top_cam_image(self, pool_id: int) -> Optional[Image]:
        """Get the latest top camera image for a pool."""
        return self._top_cam_image.get(pool_id)

    def get_under_cam_image(self, pool_id: int) -> Optional[Image]:
        """Get the latest under camera image for a pool."""
        return self._under_cam_image.get(pool_id)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DashboardNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
