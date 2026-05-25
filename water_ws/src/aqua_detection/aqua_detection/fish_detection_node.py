#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ROS2 Fish Detection Node for AquaSweep.

Modular detection pipeline supporting multiple detector backends:
- OpenCV (legacy): Traditional CV with adaptive threshold
- SAM2 (Track A): Zero-shot segmentation
- YOLO (Track B): Learned species classification

Status classification (alive/suspicious) is performed by DINOv2 module
regardless of detector backend.
"""

import json
import os
from collections import deque
from typing import Dict, Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String

try:
    from aqua_interfaces.msg import PoolStatus
except ImportError:
    class PoolStatus:
        def __init__(self):
            self.pollution_level = 0.0
            self.fish_type = "sturgeon"
            self.fish_count = 0
            self.fish_count_suspicious = 0

from aqua_detection.fish_detectors import BaseDetector, FishOpenCVDetector, FishSAM2Detector, FishYOLODetector
from aqua_detection.fish_detectors.base import DetectionResult
from aqua_detection.fish_analyzers import FishVelocityEstimator, SimpleFishStatusClassifier
from aqua_detection.fish_utils.fish_visualization import draw_detection_result
from aqua_detection.image_qos import image_subscription_qos


NUM_POOLS = 7


class PoolState:
    """Per-pool state management."""
    
    def __init__(self):
        self.debris_history = deque(maxlen=30)
        self.frame_count = 0
        self.last_detection: Optional[DetectionResult] = None
        self.velocity_estimator = FishVelocityEstimator(
            use_optical_flow=True,
            use_tracking=True
        )
        self.status_classifier = SimpleFishStatusClassifier()


class FishDetectionNode(Node):
    """Fish detection ROS2 node with pluggable detector backends."""
    
    def __init__(self):
        super().__init__('fish_detection_node')
        
        # Declare parameters
        self.declare_parameter('detector_type', 'opencv')
        self.declare_parameter('num_pools', NUM_POOLS)
        self.declare_parameter('debug_visualization', True)
        self.declare_parameter('image_qos_reliability', 'best_effort')
        self.declare_parameter('image_qos_depth', 10)
        
        # Get parameters
        detector_type = self.get_parameter('detector_type').value
        self.num_pools = self.get_parameter('num_pools').value
        self.debug_viz = self.get_parameter('debug_visualization').value
        image_qos = image_subscription_qos(
            self.get_parameter('image_qos_reliability').value,
            self.get_parameter('image_qos_depth').value,
        )
        self._image_cb_group = ReentrantCallbackGroup()
        self._ros_domain_id = os.environ.get('ROS_DOMAIN_ID', '0 (unset)')
        self._rmw = os.environ.get('RMW_IMPLEMENTATION', '(unset)')
        self._ros_distro = os.environ.get('ROS_DISTRO', '(unset)')
        self.get_logger().info(
            f"ROS env: ROS_DOMAIN_ID={self._ros_domain_id}, "
            f"RMW_IMPLEMENTATION={self._rmw}, ROS_DISTRO={self._ros_distro}"
        )
        
        # Initialize detector
        self.detector = self._create_detector(detector_type)
        self.get_logger().info(f"Using detector: {self.detector.get_name()}")
        
        # ROS2 components
        self.bridge = CvBridge()
        self.pool_states: Dict[int, PoolState] = {}
        
        # Publishers and subscribers per pool
        self.img_subs = {}
        self.pub_status = {}
        self.pub_status_str = {}
        self.pub_debug = {}
        self._frames_received = {pid: 0 for pid in range(1, self.num_pools + 1)}
        
        for pool_id in range(1, self.num_pools + 1):
            self.pool_states[pool_id] = PoolState()
            topic = f'/pool_{pool_id}/top_img_raw'
            
            self.img_subs[pool_id] = self.create_subscription(
                Image,
                topic,
                lambda msg, pid=pool_id: self._image_callback(msg, pid),
                qos_profile=image_qos,
                callback_group=self._image_cb_group,
            )
            
            self.pub_status[pool_id] = self.create_publisher(
                PoolStatus,
                f'/pool_{pool_id}/status',
                10
            )
            
            self.pub_status_str[pool_id] = self.create_publisher(
                String,
                f'/pool_{pool_id}/status_string',
                10
            )
            
            self.pub_debug[pool_id] = self.create_publisher(
                Image,
                f'/pool_{pool_id}/top_img_det',
                10
            )
        
        # Communication monitoring (None = no frame received yet)
        self.last_img_time = {pid: None for pid in range(1, self.num_pools + 1)}
        self.timer = self.create_timer(5.0, self._check_communication_status)
        self._diag_timer = self.create_timer(2.0, self._log_graph_diagnostics)
        
        self.get_logger().info(
            f"Fish Detection Node started. "
            f"Subscribed to {self.num_pools} pools (/pool_1~/pool_{self.num_pools}/top_img_raw) "
            f"with QoS reliability={image_qos.reliability.name}, depth={image_qos.depth}"
        )
    
    def _create_detector(self, detector_type: str) -> BaseDetector:
        """Create detector instance based on type."""
        if detector_type == 'opencv':
            return FishOpenCVDetector()
        elif detector_type == 'sam2':
            try:
                return FishSAM2Detector(
                    model_cfg="sam2.1_hiera_l.yaml",
                    device="cuda"
                )
            except Exception as e:
                self.get_logger().warn(f"SAM2 init failed: {e}, falling back to OpenCV")
                return FishOpenCVDetector()
        elif detector_type == 'yolo':
            try:
                return FishYOLODetector(
                    model_path="models/yolov8_fish_species.pt",
                    confidence_threshold=0.5,
                    device="cuda"
                )
            except Exception as e:
                self.get_logger().warn(f"YOLO init failed: {e}, falling back to OpenCV")
                return FishOpenCVDetector()
        else:
            self.get_logger().error(f"Unknown detector type: {detector_type}, using OpenCV")
            return FishOpenCVDetector()
    
    def _log_graph_diagnostics(self):
        """Log DDS graph info once to help debug subscription issues."""
        self._diag_timer.cancel()
        sample_topic = '/pool_1/top_img_raw'
        try:
            pubs = self.get_publishers_info_by_topic(sample_topic)
            subs = self.get_subscriptions_info_by_topic(sample_topic)
            self.get_logger().info(
                f"Graph check on {sample_topic}: "
                f"{len(pubs)} publisher(s), {len(subs)} subscription(s) including this node"
            )
            for pub in pubs:
                self.get_logger().info(
                    f"  publisher node={pub.node_name}, "
                    f"reliability={pub.qos_profile.reliability.name}, "
                    f"depth={pub.qos_profile.depth}"
                )
            for sub in subs:
                self.get_logger().info(
                    f"  subscriber node={sub.node_name}, "
                    f"reliability={sub.qos_profile.reliability.name}, "
                    f"depth={sub.qos_profile.depth}"
                )
            if not pubs:
                self.get_logger().error(
                    "Isaac Sim publisher not visible in this DDS domain. "
                    f"This node uses ROS_DOMAIN_ID={self._ros_domain_id}. "
                    "Isaac Sim reads ROS_DOMAIN_ID only at launch — restart Isaac after "
                    "export ROS_DOMAIN_ID=<same value> in the shell that starts Isaac Sim. "
                    "Also confirm simulation is playing and top_cam_ext is publishing."
                )
        except Exception as exc:
            self.get_logger().warn(f"Graph diagnostics failed: {exc}")

    def _check_communication_status(self):
        """Monitor communication status with Isaac Sim."""
        now = self.get_clock().now()
        inactive_pools = []
        
        for pool_id in range(1, self.num_pools + 1):
            last_time = self.last_img_time[pool_id]
            if last_time is None or (now - last_time).nanoseconds > 5e9:
                inactive_pools.append(pool_id)
        
        if inactive_pools:
            self.get_logger().warn(
                f"Waiting for data: Pool {inactive_pools} - no images for 5s. "
                f"ROS_DOMAIN_ID={self._ros_domain_id}. "
                f"If graph check showed 0 publishers, Isaac Sim is on a different domain."
            )
    
    def _image_callback(self, msg: Image, pool_id: int):
        """Process incoming image from pool camera."""
        self.last_img_time[pool_id] = self.get_clock().now()
        state = self.pool_states[pool_id]
        state.frame_count += 1
        self._frames_received[pool_id] += 1
        if self._frames_received[pool_id] == 1:
            self.get_logger().info(
                f"Pool_{pool_id}: first image received "
                f"({msg.width}x{msg.height}, encoding={msg.encoding})"
            )
        
        # Convert ROS image to OpenCV (Isaac Sim ROS2CameraHelper publishes rgb8)
        try:
            if msg.encoding.lower() in ('rgb8', 'rgba8'):
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            else:
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(
                f"Pool_{pool_id}: Image conversion failed "
                f"(encoding={msg.encoding}): {e}"
            )
            return
        
        # Run detection
        detection_result = self.detector.detect(cv_image)
        detection_result.frame_id = state.frame_count
        state.last_detection = detection_result
        
        # Calculate pollution level from debris history
        debris_count = max(0, detection_result.debris_count - 5)  # Offset for noise
        state.debris_history.append(debris_count)
        max_debris = max(state.debris_history) if state.debris_history else debris_count
        
        if max_debris <= 50:
            pollution_level = 0.0
        elif max_debris <= 70:
            pollution_level = 1.0
        else:
            pollution_level = 2.0
        
        # Compute velocities for detected fish
        fish_bboxes = [det.bbox for det in detection_result.fish_detections]
        fish_ids = [f"fish_{i}" for i in range(len(fish_bboxes))]
        
        velocities = state.velocity_estimator.update(
            cv_image, fish_bboxes, fish_ids
        )
        
        # Classify fish status (alive/suspicious) using DINOv2-based analysis
        fish_count_suspicious = 0
        for i, det in enumerate(detection_result.fish_detections):
            fish_id = fish_ids[i]
            velocity = velocities.get(fish_id, 0.0)
            
            # Crop fish region for status classification
            x, y, w, h = det.bbox
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(cv_image.shape[1], x + w), min(cv_image.shape[0], y + h)
            
            if x2 > x1 and y2 > y1:
                fish_crop = cv_image[y1:y2, x1:x2]
                status, confidence = state.status_classifier.classify(fish_crop, velocity)
                
                if status == "suspicious":
                    fish_count_suspicious += 1
        
        # Publish PoolStatus
        status_msg = PoolStatus()
        status_msg.pollution_level = float(pollution_level)
        status_msg.fish_type = "sturgeon"  # TODO: Get from detection result
        status_msg.fish_count = detection_result.fish_count
        status_msg.fish_count_suspicious = fish_count_suspicious
        self.pub_status[pool_id].publish(status_msg)
        
        # Publish JSON status for Isaac UI
        try:
            status_str_msg = String()
            status_str_msg.data = json.dumps({
                "pool_id": pool_id,
                "fish_count": detection_result.fish_count,
                "fish_count_suspicious": fish_count_suspicious,
                "pollution_level": float(pollution_level),
                "fish_type": "sturgeon",
                "debris_count": debris_count,
                "max_debris": int(max_debris),
                "detector": self.detector.get_name()
            })
            self.pub_status_str[pool_id].publish(status_str_msg)
        except Exception as e:
            self.get_logger().error(f"Pool_{pool_id}: JSON publish failed: {e}")
        
        # Publish debug visualization
        if self.debug_viz:
            try:
                debug_image = draw_detection_result(
                    cv_image,
                    detection_result,
                    show_stats=True
                )
                debug_msg = self.bridge.cv2_to_imgmsg(debug_image, encoding="bgr8")
                debug_msg.header = msg.header
                self.pub_debug[pool_id].publish(debug_msg)
            except Exception as e:
                self.get_logger().error(f"Pool_{pool_id}: Debug image publish failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = FishDetectionNode()
    executor = MultiThreadedExecutor(num_threads=max(4, node.num_pools))
    executor.add_node(node)
    
    try:
        executor.spin()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
