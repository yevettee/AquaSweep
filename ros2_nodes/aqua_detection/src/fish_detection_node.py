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
from collections import deque
from typing import Dict, Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
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

from fish_detectors import BaseDetector, FishOpenCVDetector, FishSAM2Detector
from fish_detectors.base import DetectionResult
from fish_analyzers import FishVelocityEstimator, SimpleFishStatusClassifier
from fish_utils.fish_visualization import draw_detection_result


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
        
        # Get parameters
        detector_type = self.get_parameter('detector_type').value
        self.num_pools = self.get_parameter('num_pools').value
        self.debug_viz = self.get_parameter('debug_visualization').value
        
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
        
        for pool_id in range(1, self.num_pools + 1):
            self.pool_states[pool_id] = PoolState()
            
            self.img_subs[pool_id] = self.create_subscription(
                Image,
                f'/pool_{pool_id}/top_img_raw',
                lambda msg, pid=pool_id: self._image_callback(msg, pid),
                qos_profile_sensor_data,
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
        
        # Communication monitoring
        self.last_img_time = {
            pid: self.get_clock().now() 
            for pid in range(1, self.num_pools + 1)
        }
        self.timer = self.create_timer(5.0, self._check_communication_status)
        
        self.get_logger().info(
            f"Fish Detection Node started. "
            f"Subscribed to {self.num_pools} pools (/pool_1~/pool_{self.num_pools}/top_img_raw)"
        )
    
    def _create_detector(self, detector_type: str) -> BaseDetector:
        """Create detector instance based on type."""
        if detector_type == 'opencv':
            return FishOpenCVDetector()
        elif detector_type == 'sam2':
            try:
                return FishSAM2Detector(
                    model_cfg="configs/sam2.1/sam2.1_hiera_l.yaml",
                    checkpoint_path="models/sam2.1_hiera_large.pt",
                    device="cuda"
                )
            except Exception as e:
                self.get_logger().warn(f"SAM2 init failed: {e}, falling back to OpenCV")
                return FishOpenCVDetector()
        elif detector_type == 'yolo':
            # TODO: Implement YOLO detector (Phase 7)
            self.get_logger().warn("YOLO detector not yet implemented, falling back to OpenCV")
            return FishOpenCVDetector()
        else:
            self.get_logger().error(f"Unknown detector type: {detector_type}, using OpenCV")
            return FishOpenCVDetector()
    
    def _check_communication_status(self):
        """Monitor communication status with Isaac Sim."""
        now = self.get_clock().now()
        inactive_pools = []
        
        for pool_id in range(1, self.num_pools + 1):
            if (now - self.last_img_time[pool_id]).nanoseconds > 5e9:
                inactive_pools.append(pool_id)
        
        if inactive_pools:
            self.get_logger().warn(
                f"Waiting for data: Pool {inactive_pools} - no images for 5s. "
                f"Check if publish_frame() is called and ROS_DOMAIN_ID=152"
            )
    
    def _image_callback(self, msg: Image, pool_id: int):
        """Process incoming image from pool camera."""
        self.last_img_time[pool_id] = self.get_clock().now()
        state = self.pool_states[pool_id]
        state.frame_count += 1
        
        # Convert ROS image to OpenCV
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"Pool_{pool_id}: Image conversion failed: {e}")
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
    
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
