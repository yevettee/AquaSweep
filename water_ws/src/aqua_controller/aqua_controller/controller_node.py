"""AquaSweep Controller Node

Provides Action Servers for robot control:
    - /{pool_id}/clean_floor  (aqua_interfaces/action/CleanFloor)
    - /{pool_id}/clean_wall   (aqua_interfaces/action/CleanWall)
    - /{pool_id}/move_fish    (aqua_interfaces/action/MoveFish)

Publishes:
    - /{robot_name}/cmd_vel  (geometry_msgs/msg/Twist)
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist

from aqua_interfaces.action import CleanFloor, CleanWall, MoveFish

from .action_handlers import CleanFloorHandler, CleanWallHandler, MoveFishHandler
from .spiral_planner import SpiralPlanner

CONTROL_HZ = 60.0


class ControllerNode(Node):

    def __init__(self) -> None:
        super().__init__('aqua_controller')

        self.declare_parameter('robot_name', 'under_robot_1')
        self.declare_parameter('rail_name', 'rail_robot_1')
        self.declare_parameter('pool_id', 'pool_1')

        robot_name = self.get_parameter('robot_name').get_parameter_value().string_value
        rail_name  = self.get_parameter('rail_name').get_parameter_value().string_value
        pool_id    = self.get_parameter('pool_id').get_parameter_value().string_value

        self._cmd_vel_pub = self.create_publisher(Twist, f'/{robot_name}/cmd_vel', 10)
        self._planner = SpiralPlanner(physics_dt=1.0 / CONTROL_HZ)

        # 핸들러 인스턴스 생성
        self._clean_floor_handler = CleanFloorHandler(self, self._planner, self._cmd_vel_pub)
        self._clean_wall_handler  = CleanWallHandler(self)
        self._move_fish_handler   = MoveFishHandler(self)

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

        self.get_logger().info(
            f'ControllerNode ready | robot={robot_name} | pool={pool_id}\n'
            f'  cmd_vel : /{robot_name}/cmd_vel\n'
            f'  actions : /{pool_id}/clean_floor | /{pool_id}/clean_wall | /{pool_id}/move_fish'
        )


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
