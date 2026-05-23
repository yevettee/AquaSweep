#!/usr/bin/env python3
"""Debug cmd_vel publisher for testing robot movement.

Usage:
    # Source ROS2 first
    source /opt/ros/humble/setup.bash
    
    # Run with default (under_robot_1, linear=0.5, angular=0.3)
    python3 debug_cmd_vel.py
    
    # Specify robot and velocities
    python3 debug_cmd_vel.py --robot 1 --linear 0.8 --angular 0.5
    
    # Test all robots 1,3,5,7 with same command
    python3 debug_cmd_vel.py --robot 1 3 5 7 --linear 0.5 --angular 0.3
    
    # Pure rotation (spin in place)
    python3 debug_cmd_vel.py --robot 1 --linear 0.0 --angular 1.0
    
    # Pure forward
    python3 debug_cmd_vel.py --robot 1 --linear 0.5 --angular 0.0
    
    # Reverse
    python3 debug_cmd_vel.py --robot 1 --linear -0.5 --angular 0.0
    
    # Arc motion (spiral-like)
    python3 debug_cmd_vel.py --robot 1 --linear 0.55 --angular 0.8
"""

import argparse
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy


class CmdVelDebugPublisher(Node):
    def __init__(self, robot_ids: list[int], linear_x: float, angular_z: float, rate_hz: float):
        super().__init__('cmd_vel_debug_publisher')
        
        self.linear_x = linear_x
        self.angular_z = angular_z
        self.robot_ids = robot_ids
        
        # Use RELIABLE to match Isaac Sim's ROS2SubscribeTwist node
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )
        
        self._pubs = {}
        for rid in robot_ids:
            topic = f'/under_robot_{rid}/cmd_vel'
            self._pubs[rid] = self.create_publisher(Twist, topic, qos)
            self.get_logger().info(f'Publishing to {topic}')
        
        self.timer = self.create_timer(1.0 / rate_hz, self.publish_cmd)
        self.get_logger().info(
            f'Started: linear_x={linear_x:.3f} m/s, angular_z={angular_z:.3f} rad/s @ {rate_hz} Hz'
        )

    def publish_cmd(self):
        msg = Twist()
        msg.linear.x = self.linear_x
        msg.angular.z = self.angular_z
        
        for rid, pub in self._pubs.items():
            pub.publish(msg)


def main():
    parser = argparse.ArgumentParser(description='Debug cmd_vel publisher')
    parser.add_argument('--robot', '-r', type=int, nargs='+', default=[1],
                        help='Robot ID(s) to control (e.g., 1 or 1 3 5 7)')
    parser.add_argument('--linear', '-l', type=float, default=0.5,
                        help='Linear velocity (m/s), positive=forward')
    parser.add_argument('--angular', '-a', type=float, default=0.3,
                        help='Angular velocity (rad/s), positive=CCW')
    parser.add_argument('--rate', type=float, default=60.0,
                        help='Publish rate (Hz)')
    parser.add_argument('--duration', '-d', type=float, default=0.0,
                        help='Duration in seconds (0=infinite)')
    
    args = parser.parse_args()
    
    rclpy.init()
    node = CmdVelDebugPublisher(args.robot, args.linear, args.angular, args.rate)
    
    try:
        if args.duration > 0:
            start = time.time()
            while rclpy.ok() and (time.time() - start) < args.duration:
                rclpy.spin_once(node, timeout_sec=0.1)
            # Send stop command
            node.linear_x = 0.0
            node.angular_z = 0.0
            node.publish_cmd()
            node.get_logger().info('Duration reached, stopping.')
        else:
            rclpy.spin(node)
    except KeyboardInterrupt:
        # Send stop command on Ctrl+C
        node.linear_x = 0.0
        node.angular_z = 0.0
        node.publish_cmd()
        node.get_logger().info('Stopped by user.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
