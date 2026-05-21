"""Temporary mock publishers and CleanFloor action servers for dashboard development."""

import math
import time

import rclpy
from aqua_interfaces.action import CleanFloor
from aqua_interfaces.msg import RobotStatus, TankStatus
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from aqua_dashboard.ros_topics import (
    TANK_COUNT,
    tank_clean_floor_action,
    tank_ids,
    tank_robot_status_topic,
    tank_status_topic,
)


class MockTelemetryNode(Node):
    def __init__(self):
        super().__init__("mock_telemetry_node")
        self._tick = 0
        self._callback_group = ReentrantCallbackGroup()

        self._tank_pubs = {}
        self._robot_pubs = {}
        self._clean_servers = []

        for tank_id in tank_ids():
            self._tank_pubs[tank_id] = self.create_publisher(
                TankStatus,
                tank_status_topic(tank_id),
                10,
            )
            self._robot_pubs[tank_id] = self.create_publisher(
                RobotStatus,
                tank_robot_status_topic(tank_id),
                10,
            )
            server = ActionServer(
                self,
                CleanFloor,
                tank_clean_floor_action(tank_id),
                execute_callback=self._make_execute_callback(tank_id),
                callback_group=self._callback_group,
            )
            self._clean_servers.append(server)

        self.create_timer(1.0, self._publish_telemetry)
        self.get_logger().info(
            f"Mock telemetry active for {TANK_COUNT} tanks "
            f"(topics under /aqua/tank_<id>/...)"
        )

    def _make_execute_callback(self, tank_id: int):
        def execute_callback(goal_handle):
            self.get_logger().info(f"Tank {tank_id}: CleanFloor goal received")
            feedback = CleanFloor.Feedback()
            for step in range(6):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    self.get_logger().info(f"Tank {tank_id}: CleanFloor canceled")
                    return CleanFloor.Result()

                feedback.progress = step / 5.0
                goal_handle.publish_feedback(feedback)
                time.sleep(0.2)

            goal_handle.succeed()
            result = CleanFloor.Result()
            result.success = True
            self.get_logger().info(f"Tank {tank_id}: CleanFloor finished (success=True)")
            return result

        return execute_callback

    def _publish_telemetry(self):
        self._tick += 1
        phase = self._tick * 0.5

        for tank_id in tank_ids():
            tank_msg = TankStatus()
            tank_msg.pollution_level = 0.5 + 0.4 * math.sin(phase + tank_id)
            tank_msg.fish_type = f"mock_species_{tank_id}"
            tank_msg.fish_count = (self._tick + tank_id) % 20
            tank_msg.fish_count_suspicious = tank_id % 4
            self._tank_pubs[tank_id].publish(tank_msg)

            robot_msg = RobotStatus()
            robot_msg.state = (
                RobotStatus.RUNNING if (self._tick + tank_id) % 2 == 0 else RobotStatus.IDLE
            )
            robot_msg.battery_level = 0.5 + 0.45 * math.sin(phase * 0.7 + tank_id * 0.3)
            robot_msg.collision_force = 0.1 * (tank_id % 3)
            self._robot_pubs[tank_id].publish(robot_msg)


def main(args=None):
    rclpy.init(args=args)
    node = MockTelemetryNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
