#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ROS2 Fish Detection Node for AquaSweep.

Modular detection pipeline supporting multiple detector backends:
- OpenCV (legacy): Traditional CV with adaptive threshold
- SAM2 (Track A): Zero-shot segmentation
- YOLO (Track B): Learned species classification

Status classification (alive/suspicious) is performed by DINOv2 module
regardless of detector backend.

Supports two camera modes:
- Per-pool mode: 7 separate camera topics (/pool_N/top_img_raw)
- Global mode: Single camera (/global/top_img_raw) with region cropping
"""

import json
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

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

from aqua_detection.fish_detectors import (
    BaseDetector,
    FishOpenCVDetector,
    FishSAM2Detector,
    FishYOLODetector,
    FishYOLOWorldDetector,
)
from aqua_detection.fish_detectors.vlm_validator import VLMValidator
from aqua_detection.fish_detectors.base import DetectionResult, FishDetection, DebrisDetection
from aqua_detection.fish_analyzers import FishVelocityEstimator, SimpleFishStatusClassifier
from aqua_detection.fish_utils.fish_visualization import draw_detection_result
from aqua_detection.image_qos import image_subscription_qos


NUM_POOLS = 7

# ── Global camera pool regions ───────────────────────────────────────────────
# Pixel coordinates (x1, y1, x2, y2) for each pool in the 2560x1920 global image.
# Derived from pool world positions and camera projection:
#   Building: 40m x 30m, Camera at (0, 0, 12m), FOV ~120°
#   Image: 2560x1920, center at (1280, 960)
#   Scale: ~64 px/m horizontal, ~64 px/m vertical
#
# Pool layout (world coords, meters):
#   Pool_5(-12.75, 5)   Pool_6(-4.25, 5)   Pool_7(4.25, 5)    [Equipment]
#   Pool_1(-12.75,-5)   Pool_2(-4.25,-5)   Pool_3(4.25,-5)   Pool_4(12.75,-5)
#
# Pool radius: 4m → ~256px, using 320px margin for safety
GLOBAL_POOL_REGIONS: Dict[int, Tuple[int, int, int, int]] = {
    # Bottom row (y=-5m → image y=1300)
    1: (116, 980, 756, 1620),    # Pool_1: center (-12.75, -5) → px (436, 1300)
    2: (679, 980, 1319, 1620),   # Pool_2: center (-4.25, -5) → px (999, 1300)
    3: (1241, 980, 1881, 1620),  # Pool_3: center (4.25, -5) → px (1561, 1300)
    4: (1804, 980, 2444, 1620),  # Pool_4: center (12.75, -5) → px (2124, 1300)
    # Top row (y=5m → image y=620)
    5: (116, 300, 756, 940),     # Pool_5: center (-12.75, 5) → px (436, 620)
    6: (679, 300, 1319, 940),    # Pool_6: center (-4.25, 5) → px (999, 620)
    7: (1241, 300, 1881, 940),   # Pool_7: center (4.25, 5) → px (1561, 620)
}


class PoolState:
    """Per-pool state management."""
    
    def __init__(
        self,
        velocity_config: Optional[Dict] = None,
        classifier_config: Optional[Dict] = None,
    ):
        """Initialize pool state.
        
        Args:
            velocity_config: Velocity estimator config dict
            classifier_config: Status classifier config dict
        """
        self.debris_history = deque(maxlen=30)
        self.frame_count = 0
        self.last_detection: Optional[DetectionResult] = None
        
        self.fish_count_history = deque(maxlen=7)
        self.fish_suspicious_history = deque(maxlen=7)
        
        # Initialize velocity estimator with config
        vel_cfg = velocity_config or {}
        self.velocity_estimator = FishVelocityEstimator(
            use_optical_flow=vel_cfg.get('use_optical_flow', False),
            use_tracking=vel_cfg.get('use_tracking', True),
            frame_skip=vel_cfg.get('frame_skip', 10),
        )
        
        # Initialize status classifier with config
        cls_cfg = classifier_config or {}
        self.status_classifier = SimpleFishStatusClassifier(
            contrast_threshold=cls_cfg.get('contrast_threshold', 8.0),
            water_similarity_threshold=cls_cfg.get('water_similarity_threshold', 0.3),
            value_std_threshold=cls_cfg.get('value_std_threshold', 40.0),
            saturation_std_threshold=cls_cfg.get('saturation_std_threshold', 30.0),
            velocity_threshold=cls_cfg.get('velocity_threshold', 0.02),
            use_velocity=cls_cfg.get('use_velocity', True),
            velocity_weight=cls_cfg.get('velocity_weight', 0.20),
        )


class FishDetectionNode(Node):
    """Fish detection ROS2 node with pluggable detector backends."""
    
    def __init__(self):
        super().__init__('fish_detection_node')
        
        # Declare parameters
        self.declare_parameter('detector_type', 'yolo')
        self.declare_parameter('use_vlm', True)
        self.declare_parameter('num_pools', NUM_POOLS)
        self.declare_parameter('debug_visualization', True)
        self.declare_parameter('image_qos_reliability', 'best_effort')
        self.declare_parameter('image_qos_depth', 10)
        self.declare_parameter('use_global_camera', False)
        
        # Velocity estimator parameters
        self.declare_parameter('velocity.use_optical_flow', False)
        self.declare_parameter('velocity.use_tracking', True)
        self.declare_parameter('velocity.frame_skip', 10)
        
        # Status classifier parameters
        self.declare_parameter('classifier.use_velocity', True)
        self.declare_parameter('classifier.velocity_threshold', 0.02)
        self.declare_parameter('classifier.velocity_weight', 0.20)
        self.declare_parameter('classifier.contrast_threshold', 8.0)
        self.declare_parameter('classifier.water_similarity_threshold', 0.3)
        self.declare_parameter('classifier.value_std_threshold', 40.0)
        self.declare_parameter('classifier.saturation_std_threshold', 30.0)
        
        # Get parameters
        detector_type = self.get_parameter('detector_type').value
        self.use_vlm = self.get_parameter('use_vlm').value
        self.num_pools = self.get_parameter('num_pools').value
        self.debug_viz = self.get_parameter('debug_visualization').value
        self.use_global_camera = self.get_parameter('use_global_camera').value
        
        # Build config dicts for velocity and classifier
        self._velocity_config = {
            'use_optical_flow': self.get_parameter('velocity.use_optical_flow').value,
            'use_tracking': self.get_parameter('velocity.use_tracking').value,
            'frame_skip': self.get_parameter('velocity.frame_skip').value,
        }
        self._classifier_config = {
            'use_velocity': self.get_parameter('classifier.use_velocity').value,
            'velocity_threshold': self.get_parameter('classifier.velocity_threshold').value,
            'velocity_weight': self.get_parameter('classifier.velocity_weight').value,
            'contrast_threshold': self.get_parameter('classifier.contrast_threshold').value,
            'water_similarity_threshold': self.get_parameter('classifier.water_similarity_threshold').value,
            'value_std_threshold': self.get_parameter('classifier.value_std_threshold').value,
            'saturation_std_threshold': self.get_parameter('classifier.saturation_std_threshold').value,
        }
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
        self.get_logger().info(
            f"Classifier config: contrast_threshold={self._classifier_config['contrast_threshold']}, "
            f"use_velocity={self._classifier_config['use_velocity']}, "
            f"velocity_weight={self._classifier_config['velocity_weight']}"
        )
        
        # Initialize detector
        self.detector = self._create_detector(detector_type)
        self.get_logger().info(f"Using detector: {self.detector.get_name()}")
        
        # Initialize VLM Validator
        self.vlm_validator = VLMValidator() if self.use_vlm else None
        
        # ROS2 components
        self.bridge = CvBridge()
        self.pool_states: Dict[int, PoolState] = {}
        self.is_processing = {i: False for i in range(1, 8)}
        self._representative_pool: int = 1  # VLM 검증을 수행할 대표 수조 (YOLO 탐지 개수 기반으로 동적 선정)
        self._pool_candidate_count: Dict[int, int] = {i: 0 for i in range(1, 8)}  # 수조별 탐지 개수 축적
        
        # Publishers and subscribers per pool
        self.img_subs = {}
        self.pub_status = {}
        self.pub_status_str = {}
        self.pub_debug = {}
        self._frames_received = {pid: 0 for pid in range(1, self.num_pools + 1)}
        self._global_frames_received = 0
        
        # Initialize pool states and publishers (used by both modes)
        for pool_id in range(1, self.num_pools + 1):
            self.pool_states[pool_id] = PoolState(
                velocity_config=self._velocity_config,
                classifier_config=self._classifier_config,
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
        
        # Subscribe based on camera mode
        if self.use_global_camera:
            # Global camera mode: single subscription, crop per pool
            self._global_sub = self.create_subscription(
                Image,
                '/global/top_img_raw',
                self._global_image_callback,
                qos_profile=image_qos,
                callback_group=self._image_cb_group,
            )
            mode_info = "GLOBAL camera mode (/global/top_img_raw → crop per pool)"
        else:
            # Per-pool mode: one subscription per pool
            for pool_id in range(1, self.num_pools + 1):
                topic = f'/pool_{pool_id}/top_img_raw'
                
                self.img_subs[pool_id] = self.create_subscription(
                    Image,
                    topic,
                    lambda msg, pid=pool_id: self._image_callback(msg, pid),
                    qos_profile=image_qos,
                    callback_group=self._image_cb_group,
                )
            mode_info = f"PER-POOL mode ({self.num_pools} cameras)"
        
        # Communication monitoring (None = no frame received yet)
        self.last_img_time = {pid: None for pid in range(1, self.num_pools + 1)}
        self.timer = self.create_timer(5.0, self._check_communication_status)
        self._diag_timer = self.create_timer(2.0, self._log_graph_diagnostics)
        
        self.get_logger().info(
            f"Fish Detection Node started. {mode_info}. "
            f"QoS reliability={image_qos.reliability.name}, depth={image_qos.depth}"
        )
    
    def _create_detector(self, detector_type: str) -> BaseDetector:
        """Create detector instance based on type."""
        if detector_type == 'opencv':
            return FishOpenCVDetector()
        elif detector_type == 'sam2':
            try:
                return FishSAM2Detector(
                    model_cfg="configs/sam2.1/sam2.1_hiera_t.yaml",
                    device="cuda"
                )
            except Exception as e:
                self.get_logger().warn(f"SAM2 init failed: {e}, falling back to OpenCV")
                return FishOpenCVDetector()
        elif detector_type == 'yolo_world':
            try:
                detector = FishYOLOWorldDetector(
                    model_id="yolov8s-world.pt",
                    device="cuda"
                )
                return detector
            except Exception as e:
                self.get_logger().warn(f"YOLO-World init failed: {e}, falling back to OpenCV")
                return FishOpenCVDetector()
        elif detector_type == 'yolo':
            try:
                detector = FishYOLODetector(
                    model_path="models/yolov8_fish_species.pt",
                    confidence_threshold=0.5,
                    device="cuda",
                    imgsz=640,
                    half=True,
                    use_tracking=False,  # Disabled - slow rendering breaks tracking
                    debris_min_area=3,    # OpenCV blob detector
                    debris_max_area=8,
                    debris_debug=True,    # Print debris keypoint info for tuning
                )
                detector.warmup()
                if not detector._initialized:
                    raise RuntimeError("YOLO model components not installed or model file missing")
                return detector
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
    
    def _draw_detection_with_status(
        self,
        image: np.ndarray,
        detection_result: DetectionResult,
        fish_statuses: List[Dict]
    ) -> np.ndarray:
        """Draw detections with status-based coloring.
        
        - Alive fish: Green bbox
        - Suspicious fish: Yellow bbox with features display
        - Candidate Debris: Cyan bbox
        - VLM Verified Debris: Red bbox
        """
        output = image.copy()
        
        # Colors (BGR)
        COLOR_ALIVE = (0, 255, 0)       # Green (Alive Shark)
        COLOR_DEAD = (0, 0, 255)        # Red (Dead Shark)
        COLOR_DEBRIS = (255, 255, 0)    # Cyan (Debris/Poop)
        
        # Draw fish with status-based colors
        for fs in fish_statuses:
            fish_id = fs.get('fish_id', '?')
            x, y, w, h = fs['bbox']
            status = fs['status']
            species = fs['species']
            confidence = fs['confidence']
            velocity = fs['velocity']
            
            # Choose color based on status
            color = COLOR_DEAD if status == "suspicious" else COLOR_ALIVE
            thickness = 3 if status == "suspicious" else 2
            
            # Draw bbox only (no text label)
            cv2.rectangle(output, (x, y), (x + w, y + h), color, thickness)
        
        # Draw VLM Verified debris as Cyan boxes (no text)
        for det in detection_result.debris_detections:
            x, y, w, h = det.bbox
            cv2.rectangle(output, (x, y), (x + w, y + h), COLOR_DEBRIS, 2)
        
        # 통계 오버레이는 뷰어에서 그리므로 여기선 생략
        
        return output

    def _check_communication_status(self):
        """Monitor communication status with Isaac Sim."""
        now = self.get_clock().now()
        inactive_pools = []
        
        for pool_id in range(1, self.num_pools + 1):
            last_time = self.last_img_time[pool_id]
            if last_time is None or (now - last_time).nanoseconds > 5e9:
                inactive_pools.append(pool_id)
        
        if inactive_pools:
            topic_hint = "/global/top_img_raw" if self.use_global_camera else "/pool_N/top_img_raw"
            self.get_logger().warn(
                f"Waiting for data: Pool {inactive_pools} - no images for 5s. "
                f"ROS_DOMAIN_ID={self._ros_domain_id}. Topic: {topic_hint}"
            )

    def _global_image_callback(self, msg: Image):
        """Process global camera image by cropping and detecting each pool region.
        
        This is more efficient than 7 separate cameras because:
        - Only 1 GPU render pass instead of 7
        - Single ROS2 image transfer instead of 7
        - Cropping is cheap CPU operation
        """
        self._global_frames_received += 1
        if self._global_frames_received == 1:
            self.get_logger().info(
                f"Global camera: first image received "
                f"({msg.width}x{msg.height}, encoding={msg.encoding})"
            )
        
        # Convert ROS image to OpenCV
        try:
            if msg.encoding.lower() in ('rgb8', 'rgba8'):
                full_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            else:
                full_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"Global image conversion failed: {e}")
            return
        
        img_h, img_w = full_image.shape[:2]
        
        # Process each pool region
        for pool_id in range(1, self.num_pools + 1):
            if pool_id not in GLOBAL_POOL_REGIONS:
                continue
            
            x1, y1, x2, y2 = GLOBAL_POOL_REGIONS[pool_id]
            
            # Clamp to image bounds
            x1 = max(0, min(x1, img_w))
            x2 = max(0, min(x2, img_w))
            y1 = max(0, min(y1, img_h))
            y2 = max(0, min(y2, img_h))
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Crop pool region
            pool_image = full_image[y1:y2, x1:x2].copy()
            
            # Process this pool's image through the detection pipeline
            self._process_pool_image(pool_image, pool_id, msg.header)
    
    def _process_pool_image(self, cv_image: np.ndarray, pool_id: int, header=None):
        """Process a single pool's image (used by both per-pool and global modes)."""
        if self.is_processing.get(pool_id, False):
            return
        
        self.is_processing[pool_id] = True
        now = self.get_clock().now()
        self.last_img_time[pool_id] = now
        state = self.pool_states[pool_id]
        state.frame_count += 1
        self._frames_received[pool_id] += 1
        
        # Run detection
        detection_result = self.detector.detect(cv_image)
        
        # VLM Validation for ALL candidate objects
        validated_debris = []
        validated_fish = []
        fish_statuses_temp = {}
        
        # 대표 수조 후보 가중치 업데이트 (탐지 개수 기록)
        self._pool_candidate_count[pool_id] = len(detection_result.debris_detections)
        
        # VLM 적용: 현재 대표 수조의 '물고기 후보' 객체에 대해서만 생사 판별 (속도 최적화 및 정확도 향상)
        if self.vlm_validator and pool_id == self._representative_pool and detection_result.fish_detections:
            self.get_logger().info(f"Pool_{pool_id}: VLM 검증 시작 (상어 후보 {len(detection_result.fish_detections)}개)")
            validated_fish = []
            fish_statuses_temp = {}
            for i, det in enumerate(detection_result.fish_detections):
                x, y, w, h = det.bbox
                margin = 20
                y1, y2 = max(0, y - margin), min(cv_image.shape[0], y + h + margin)
                x1, x2 = max(0, x - margin), min(cv_image.shape[1], x + w + margin)
                if y2 > y1 and x2 > x1:
                    crop = cv_image[y1:y2, x1:x2]
                    category = self.vlm_validator.classify_object(crop)
                    
                    if category == "alive" or category == "dead":
                        validated_fish.append(det)
                        fish_statuses_temp[len(validated_fish)-1] = "suspicious" if category == "dead" else "alive"
                    else:
                        # VLM thinks it's debris, move to debris list
                        d_det = DebrisDetection(bbox=det.bbox, confidence=det.confidence)
                        detection_result.debris_detections.append(d_det)
            
            # Update fish detections with only validated ones
            detection_result.fish_detections = validated_fish
            
            self.get_logger().info(f"Pool_{pool_id}: VLM 검증 완료")
            
            # VLM 검증 완료 후 다음 대표 수조 선정 (가장 많은 객체가 있는 수조)
            if self._pool_candidate_count:
                new_rep = max(self._pool_candidate_count, key=self._pool_candidate_count.get)
                if new_rep != self._representative_pool:
                    self.get_logger().info(f"대표 수조 변경: Pool_{self._representative_pool} → Pool_{new_rep} (객체 수: {self._pool_candidate_count[new_rep]})")
                    self._representative_pool = new_rep

        detection_result.frame_id = state.frame_count
        state.last_detection = detection_result
        
        # Calculate pollution level from debris history
        debris_count = max(0, detection_result.debris_count - 5)
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
        fish_ids = []
        for i, det in enumerate(detection_result.fish_detections):
            track_id = getattr(det, '_track_id', None)
            if track_id is not None:
                fish_ids.append(f"fish_{track_id}")
            else:
                fish_ids.append(f"fish_{i}")
        
        velocities = state.velocity_estimator.update(
            cv_image, fish_bboxes, fish_ids
        )
        
        # Classify fish status and store results
        fish_count_suspicious = 0
        fish_statuses = []
        
        for i, det in enumerate(detection_result.fish_detections):
            fish_id = fish_ids[i]
            velocity = velocities.get(fish_id, 0.0)
            
            # The status was determined by the VLM earlier
            status = fish_statuses_temp.get(i, "alive")
            
            fish_statuses.append({
                'fish_id': fish_id,
                'bbox': det.bbox,
                'species': det.species,
                'status': status,
                'confidence': det.confidence,
                'velocity': velocity,
                'features': {},
            })
            
            if status == "suspicious":
                fish_count_suspicious += 1
        
        # VLM이 실행된 프레임에서만 fish count 기록 업데이트 (non-VLM 프레임의 0으로 덮어쓰는 버그 방지)
        if pool_id == self._representative_pool and self.vlm_validator:
            state.fish_count_history.append(detection_result.fish_count)
            state.fish_suspicious_history.append(fish_count_suspicious)
        elif not state.fish_count_history:
            # 아직 기록이 없으면 현재 값 추가 (초기화 목적)
            state.fish_count_history.append(0)
            state.fish_suspicious_history.append(0)
        smoothed_fish_count = int(np.median(state.fish_count_history))
        smoothed_suspicious = int(np.median(state.fish_suspicious_history))
        
        # Publish PoolStatus
        status_msg = PoolStatus()
        status_msg.pollution_level = float(pollution_level)
        status_msg.fish_type = "sturgeon"
        status_msg.fish_count = smoothed_fish_count
        status_msg.fish_count_suspicious = smoothed_suspicious
        self.pub_status[pool_id].publish(status_msg)
        
        # Collect debris positions
        debris_positions = []
        for det in detection_result.debris_detections:
            x, y, w, h = det.bbox
            center_x = x + w // 2
            center_y = y + h // 2
            debris_positions.append([center_x, center_y])

        # Publish JSON status
        try:
            status_str_msg = String()
            status_str_msg.data = json.dumps({
                "pool_id": pool_id,
                "fish_count": smoothed_fish_count,
                "fish_count_suspicious": smoothed_suspicious,
                "pollution_level": float(pollution_level),
                "fish_type": "sturgeon",
                "debris_count": debris_count,
                "max_debris": int(max_debris),
                "debris_positions": debris_positions,
                "detector": self.detector.get_name(),
                "camera_mode": "global" if self.use_global_camera else "per_pool"
            })
            self.pub_status_str[pool_id].publish(status_str_msg)
        except Exception as e:
            self.get_logger().error(f"Pool_{pool_id}: JSON publish failed: {e}")
        
        # Publish debug visualization with status colors
        if self.debug_viz:
            try:
                debug_image = self._draw_detection_with_status(
                    cv_image, detection_result, fish_statuses
                )
                debug_msg = self.bridge.cv2_to_imgmsg(debug_image, encoding="bgr8")
                if header:
                    debug_msg.header = header
                self.pub_debug[pool_id].publish(debug_msg)
            except Exception as e:
                self.get_logger().error(f"Pool_{pool_id}: Debug image publish failed: {e}")
                
        self.is_processing[pool_id] = False
    
    def _center_crop_square(self, image: np.ndarray, size: int = 640) -> np.ndarray:
        """이미지를 중앙 기준 정사각형으로 크롭 (비율 유지, 리사이즈 없음).
        
        양옆에 다른 풀이 살짝 걸리는 문제를 해결하기 위해
        640x480 이미지에서 중앙 480x480 또는 지정된 size로 크롭합니다.
        
        Args:
            image: 입력 이미지 (H, W, C)
            size: 크롭할 정사각형 크기 (기본 640)
        
        Returns:
            중앙 크롭된 정사각형 이미지
        """
        h, w = image.shape[:2]
        
        # 정사각형 크롭 크기 결정 (min(w, h)와 size 중 작은 값)
        crop_size = min(w, h, size)
        
        # 중앙 좌표 계산
        cx, cy = w // 2, h // 2
        x1 = cx - crop_size // 2
        y1 = cy - crop_size // 2
        x2 = x1 + crop_size
        y2 = y1 + crop_size
        
        return image[y1:y2, x1:x2]
    
    def _image_callback(self, msg: Image, pool_id: int):
        """Process incoming image from per-pool camera (delegates to shared method)."""
        if self._frames_received[pool_id] == 0:
            self.get_logger().info(
                f"Pool_{pool_id}: first image received "
                f"({msg.width}x{msg.height}, encoding={msg.encoding})"
            )
        
        # Convert ROS image to OpenCV
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
        
        # 카메라 줌아웃에 맞춰 가로/세로 크롭 설정 (세로 520, 가로 494)
        h, w = cv_image.shape[:2]
        crop_w = 494
        crop_h = 520
        
        x1 = max(0, (w - crop_w) // 2)
        x2 = x1 + crop_w
        y1 = max(0, (h - crop_h) // 2)
        y2 = y1 + crop_h
        
        cv_image = cv_image[y1:y2, x1:x2]
        
        # Use shared processing method
        self._process_pool_image(cv_image, pool_id, msg.header)


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
