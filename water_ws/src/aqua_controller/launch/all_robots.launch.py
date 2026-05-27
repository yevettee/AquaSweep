"""Launch one controller_node per robot (under_robot_1 … under_robot_7).

Arguments:
    use_service_mode (str): 'true'=서비스 모드(Isaac 내부 플래너, 기본값), 'false'=기존 모드(step_sync)

Usage:
    # 서비스 모드 (기본값)
    ros2 launch aqua_controller all_robots.launch.py

    # 기존 모드 (step_sync)
    ros2 launch aqua_controller all_robots.launch.py use_service_mode:=false
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

_NUM_ROBOTS = 7


def generate_launch_description() -> LaunchDescription:
    use_service_mode_arg = DeclareLaunchArgument(
        'use_service_mode',
        default_value='true',
        description='Use service mode (Isaac internal planner) instead of step_sync mode'
    )

    use_service_mode = LaunchConfiguration('use_service_mode')

    nodes = []
    for i in range(1, _NUM_ROBOTS + 1):
        nodes.append(
            Node(
                package='aqua_controller',
                executable='controller_node',
                name=f'aqua_controller_{i}',
                parameters=[{
                    'robot_name': f'under_robot_{i}',
                    'rail_name':  f'rail_robot_{i}',
                    'pool_id':    f'pool_{i}',
                    'tank_margin': 0.45,
                    'robot_footprint': 0.686,
                    'linear_speed': 3.0,
                    'omega_max': 8.0,
                    'use_service_mode': ParameterValue(use_service_mode, value_type=bool),
                }],
                output='screen',
            )
        )

    return LaunchDescription([use_service_mode_arg] + nodes)
