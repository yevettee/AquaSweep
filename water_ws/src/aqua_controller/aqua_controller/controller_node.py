"""AquaSweep Controller Node

Provides Action Servers for robot control:
    - /{pool_id}/clean_floor (CleanFloor.action)
    - /{pool_id}/clean_wall (CleanWall.action)
    - /{pool_id}/move_fish (MoveFish.action)

Publishes:
    - /{robot_name}/cmd_vel (geometry_msgs/Twist)
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist

from aqua_interfaces.action import CleanFloor, CleanWall, MoveFish

from .spiral_planner import SpiralPlanner
from .action_handlers import CleanFloorHandler, CleanWallHandler, MoveFishHandler

CONTROL_HZ = 60.0


class ControllerNode(Node):
    """Main controller node with Action Servers."""

    def __init__(self) -> None:
        super().__init__('aqua_controller')

        self.declare_parameter('robot_name', 'under_robot_1')
        self.declare_parameter('pool_id', 'pool_1')

        robot_name = self.get_parameter('robot_name').get_parameter_value().string_value
        pool_id = self.get_parameter('pool_id').get_parameter_value().string_value

        self._cmd_vel_topic = f'/{robot_name}/cmd_vel'
        self._cmd_vel_pub = self.create_publisher(Twist, self._cmd_vel_topic, 10)

        self._planner = SpiralPlanner(physics_dt=1.0 / CONTROL_HZ)

        callback_group = ReentrantCallbackGroup()

        self._clean_floor_handler = CleanFloorHandler(
            self, self._planner, self._cmd_vel_pub, CONTROL_HZ
        )
        self._clean_wall_handler = CleanWallHandler(self)
        self._move_fish_handler = MoveFishHandler(self)

        self._clean_floor_server = ActionServer(
            self,
            CleanFloor,
            f'/{pool_id}/clean_floor',
            execute_callback=self._clean_floor_handler.execute,
            goal_callback=self._clean_floor_handler.handle_goal,
            cancel_callback=self._clean_floor_handler.handle_cancel,
            callback_group=callback_group
        )

        self._clean_wall_server = ActionServer(
            self,
            CleanWall,
            f'/{pool_id}/clean_wall',
            execute_callback=self._clean_wall_handler.execute,
            goal_callback=self._clean_wall_handler.handle_goal,
            cancel_callback=self._clean_wall_handler.handle_cancel,
            callback_group=callback_group
        )

        self._move_fish_server = ActionServer(
            self,
            MoveFish,
            f'/{pool_id}/move_fish',
            execute_callback=self._move_fish_handler.execute,
            goal_callback=self._move_fish_handler.handle_goal,
            cancel_callback=self._move_fish_handler.handle_cancel,
            callback_group=callback_group
        )

        self.get_logger().info(
            f'ControllerNode ready | robot={robot_name} | pool={pool_id}\n'
            f'  cmd_vel: {self._cmd_vel_topic}\n'
            f'  actions: /{pool_id}/clean_floor, /{pool_id}/clean_wall, /{pool_id}/move_fish'
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
