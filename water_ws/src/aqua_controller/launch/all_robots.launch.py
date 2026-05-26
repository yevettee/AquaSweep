"""Launch one controller_node per robot (under_robot_1 … under_robot_7)."""

from launch import LaunchDescription
from launch_ros.actions import Node

_NUM_ROBOTS = 7


def generate_launch_description() -> LaunchDescription:
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
                    'tank_margin': 0.5,
                    'robot_footprint': 0.3,
                }],
                output='screen',
            )
        )
    return LaunchDescription(nodes)
