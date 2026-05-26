"""AquaSweep Controller Node

Provides Action Servers for robot control:
    - /{pool_id}/clean_floor  (aqua_interfaces/action/CleanFloor)
    - /{pool_id}/clean_wall   (aqua_interfaces/action/CleanWall)
    - /{pool_id}/move_fish    (aqua_interfaces/action/MoveFish)

Publishes:
    - /{robot_name}/cmd_vel  (geometry_msgs/msg/Twist)
    - /{robot_name}/status   (aqua_interfaces/msg/RobotStatus) @ 2Hz
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist

from aqua_interfaces.action import CleanFloor, CleanWall, MoveFish
from aqua_interfaces.msg import RobotStatus

from .action_handlers import CleanFloorHandler, CleanWallHandler, MoveFishHandler
from .spiral_planner import SpiralPlanner

CONTROL_HZ = 60.0
STATUS_HZ = 2.0


class ControllerNode(Node):

    def __init__(self) -> None:
        super().__init__('aqua_controller')

        self.declare_parameter('robot_name', 'under_robot_1')
        self.declare_parameter('rail_name', 'rail_robot_1')
        self.declare_parameter('pool_id', 'pool_1')
        self.declare_parameter('tank_diameter', 8.0)
        self.declare_parameter('tank_margin', 0.08)
        self.declare_parameter('robot_footprint', 0.686)
        self.declare_parameter('linear_speed', 0.55)
        self.declare_parameter('omega_max', 2.8)

        robot_name     = self.get_parameter('robot_name').get_parameter_value().string_value
        rail_name      = self.get_parameter('rail_name').get_parameter_value().string_value
        pool_id        = self.get_parameter('pool_id').get_parameter_value().string_value
        tank_diameter  = self.get_parameter('tank_diameter').get_parameter_value().double_value
        tank_margin    = self.get_parameter('tank_margin').get_parameter_value().double_value
        robot_footprint = self.get_parameter('robot_footprint').get_parameter_value().double_value
        linear_speed   = self.get_parameter('linear_speed').get_parameter_value().double_value
        omega_max      = self.get_parameter('omega_max').get_parameter_value().double_value

        self._cmd_vel_pub = self.create_publisher(Twist, f'/{robot_name}/cmd_vel', 10)
        self._robot_status_pub = self.create_publisher(
            RobotStatus, f'/{robot_name}/status', 10
        )
        self._planner = SpiralPlanner(
            physics_dt=1.0 / CONTROL_HZ,
            tank_diameter=tank_diameter,
            tank_margin=tank_margin,
            robot_footprint=robot_footprint,
            linear_speed=linear_speed,
            omega_max=omega_max,
        )

        # 핸들러 인스턴스 생성
        self._clean_floor_handler = CleanFloorHandler(
            self, self._planner, self._cmd_vel_pub, pool_id=pool_id
        )
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

        self.create_timer(1.0 / STATUS_HZ, self._publish_robot_status)

        self.get_logger().info(
            f'ControllerNode ready | robot={robot_name} | pool={pool_id}\n'
            f'  cmd_vel : /{robot_name}/cmd_vel\n'
            f'  status  : /{robot_name}/status @ {STATUS_HZ:.0f}Hz\n'
            f'  actions : /{pool_id}/clean_floor | /{pool_id}/clean_wall | /{pool_id}/move_fish\n'
            f'  spiral  : tank_diameter={tank_diameter}m  linear_speed={linear_speed}m/s'
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
