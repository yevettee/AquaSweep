"""Launch all AquaSweep nodes: controller, detection, planner, dashboard.

Usage:
    ros2 launch aqua_hippo aqua_hippo.launch.py
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    controller_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('aqua_controller'),
                'launch',
                'all_robots.launch.py'
            )
        )
    )

    return LaunchDescription([
        controller_launch,
        Node(
            package='aqua_detection',
            executable='fish_detection_node',
            name='fish_detection_node',
            output='screen',
        ),
        Node(
            package='aqua_planner',
            executable='planner_node',
            name='planner_node',
            output='screen',
        ),
        Node(
            package='aqua_dashboard',
            executable='dashboard_gui',
            name='dashboard_gui',
            output='screen',
        ),
    ])
