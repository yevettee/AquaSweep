"""AquaSweep Controller Node

Isaac Sim 내부 플래너와 연동하는 Action Server를 제공합니다.
ROS2 서비스를 통해 Isaac Sim에 모션 시작/정지를 요청하고,
motion_status 토픽으로 진행상황을 모니터링합니다.

Action Servers:
    - /{pool_id}/clean_floor  (aqua_interfaces/action/CleanFloor)
    - /{pool_id}/clean_wall   (aqua_interfaces/action/CleanWall)
    - /{pool_id}/move_fish    (aqua_interfaces/action/MoveFish)

Publishes:
    - /{robot_name}/status   (aqua_interfaces/msg/RobotStatus) @ 2Hz
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from aqua_interfaces.action import CleanFloor, CleanWall, MoveFish
from aqua_interfaces.msg import RobotStatus

from .action_handlers import CleanFloorHandler, CleanWallHandler, MoveFishHandler

STATUS_HZ = 2.0


class ControllerNode(Node):

    def __init__(self) -> None:
        super().__init__('aqua_controller')

        self.declare_parameter('robot_name', 'under_robot_1')
        self.declare_parameter('rail_name', 'rail_robot_1')
        self.declare_parameter('pool_id', 'pool_1')

        robot_name = self.get_parameter('robot_name').get_parameter_value().string_value
        rail_name = self.get_parameter('rail_name').get_parameter_value().string_value
        pool_id = self.get_parameter('pool_id').get_parameter_value().string_value

        self._robot_status_pub = self.create_publisher(
            RobotStatus, f'/{robot_name}/status', 10
        )

        self._clean_floor_handler = CleanFloorHandler(self, pool_id=pool_id)
        self._clean_wall_handler = CleanWallHandler(self, pool_id=pool_id)
        self._move_fish_handler = MoveFishHandler(self)

        cb = ReentrantCallbackGroup()

        ActionServer(
            self, CleanFloor, f'/{pool_id}/clean_floor',
            execute_callback=self._clean_floor_handler.execute,
            goal_callback=self._clean_floor_handler.handle_goal,
            cancel_callback=self._clean_floor_handler.handle_cancel,
            callback_group=cb,
        )
        ActionServer(
            self, CleanWall, f'/{pool_id}/clean_wall',
            execute_callback=self._clean_wall_handler.execute,
            goal_callback=self._clean_wall_handler.handle_goal,
            cancel_callback=self._clean_wall_handler.handle_cancel,
            callback_group=cb,
        )
        ActionServer(
            self, MoveFish, f'/{pool_id}/move_fish',
            execute_callback=self._move_fish_handler.execute,
            goal_callback=self._move_fish_handler.handle_goal,
            cancel_callback=self._move_fish_handler.handle_cancel,
            callback_group=cb,
        )

        self.create_timer(1.0 / STATUS_HZ, self._publish_robot_status)

        self.get_logger().info(
            f'ControllerNode ready | robot={robot_name} | rail={rail_name} | pool={pool_id}\n'
            f'  status  : /{robot_name}/status @ {STATUS_HZ:.0f}Hz\n'
            f'  actions : /{pool_id}/clean_floor | /{pool_id}/clean_wall | /{pool_id}/move_fish'
        )

    def _publish_robot_status(self) -> None:
        any_active = (
            self._clean_floor_handler.is_active
            or self._clean_wall_handler.is_active
            or self._move_fish_handler.is_active
        )
        msg = RobotStatus()
        msg.state = RobotStatus.RUNNING if any_active else RobotStatus.IDLE
        msg.battery_level = 1.0
        msg.collision_force = 0.0
        self._robot_status_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ControllerNode()
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
