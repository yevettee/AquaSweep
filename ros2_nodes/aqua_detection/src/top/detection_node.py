#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ROS2 Top Camera Object Detection Node for AquaSweep — 다중 수조(Pool_1~Pool_7) 지원.

단일 프로세스에서 모든 수조의 /pool_N/top_img_raw 를 구독하고,
각 수조별 독립적인 탐지 파이프라인을 실행하여 결과를 발행한다.
"""

import cv2
import numpy as np
from collections import deque
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
import json
from cv_bridge import CvBridge

try:
    from aqua_interfaces.msg import PoolStatus
except ImportError:
    class PoolStatus:
        def __init__(self):
            self.pollution_level = 0.0
            self.fish_type = "sturgeon"
            self.fish_count = 0
            self.fish_count_suspicious = 0


NUM_POOLS = 7


class PoolDetector:
    """각 수조별 독립적인 상태를 유지하는 탐지기."""

    def __init__(self):
        self.debris_history = deque(maxlen=30)
        self.frame_count = 0


class TopDetectionNode(Node):
    def __init__(self):
        super().__init__('top_detection_node')

        self.bridge = CvBridge()
        self.detectors = {}  # {pool_id: PoolDetector}
        self.img_subs = {}
        self.pub_status = {}
        self.pub_status_str = {}
        self.pub_debug = {}

        for pool_id in range(1, NUM_POOLS + 1):
            detector = PoolDetector()
            self.detectors[pool_id] = detector

            self.img_subs[pool_id] = self.create_subscription(
                Image,
                f'/pool_{pool_id}/top_img_raw',
                lambda msg, pid=pool_id: self.image_callback(msg, pid),
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

        # 디버깅용 타이머: 데이터 수신 모니터링 (5초 간격)
        self.last_img_time = {pid: self.get_clock().now() for pid in range(1, NUM_POOLS + 1)}
        self.timer = self.create_timer(5.0, self.check_communication_status)

        self.get_logger().info(
            f'🟢 Top Detection Node 실행 완료! {NUM_POOLS}개 수조 토픽 구독 중 '
            f'(/pool_1~/pool_{NUM_POOLS}/top_img_raw)'
        )

    def check_communication_status(self):
        now = self.get_clock().now()
        inactive_pools = []
        for pool_id in range(1, NUM_POOLS + 1):
            if (now - self.last_img_time[pool_id]).nanoseconds > 5e9:
                inactive_pools.append(pool_id)
        if inactive_pools:
            self.get_logger().warn(
                f'🟡 통신 대기 중: Pool {inactive_pools}에서 5초간 이미지 없음. '
                f'publish_frame()이 호출되고 있는지, ROS_DOMAIN_ID=152인지 확인하세요.'
            )

    def image_callback(self, msg, pool_id: int):
        self.last_img_time[pool_id] = self.get_clock().now()
        detector = self.detectors[pool_id]
        detector.frame_count += 1

        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"🔴 Pool_{pool_id}: ROS Image 변환 실패: {e}")
            return

        # 30프레임 단위로 연산 상태 콘솔 출력
        should_log = (detector.frame_count % 30 == 1)

        fish_present, debris_count, max_debris, pollution_level, debug_image = self.process_image(cv_image, detector)

        status_msg = PoolStatus()
        status_msg.pollution_level = float(pollution_level)
        status_msg.fish_type = "sturgeon"
        # 존재하면 1, 없으면 0으로 토픽값 발행
        status_msg.fish_count = int(fish_present)
        status_msg.fish_count_suspicious = 0
        self.pub_status[pool_id].publish(status_msg)

        # JSON 스트링 메시지 발행 (아이작심 내장 Python 및 UI/콘솔 피드백용)
        try:
            status_str_msg = String()
            status_str_msg.data = json.dumps({
                "pool_id": pool_id,
                "fish_count": int(fish_present),
                "pollution_level": float(pollution_level),
                "fish_type": "sturgeon",
                "raw_debris": int(debris_count),
                "max_debris": int(max_debris)
            })
            self.pub_status_str[pool_id].publish(status_str_msg)
        except Exception as e:
            self.get_logger().error(f"🔴 Pool_{pool_id}: JSON 스트링 발행 실패: {e}")

        # 개발용 콘솔 인지 로그 출력 및 cv2.imshow 팝업창 완전 제거 (상용 릴리즈 세팅)
        if debug_image is not None:
            try:
                debug_msg = self.bridge.cv2_to_imgmsg(debug_image, encoding="bgr8")
                debug_msg.header = msg.header
                self.pub_debug[pool_id].publish(debug_msg)
            except Exception as e:
                self.get_logger().error(f"🔴 Pool_{pool_id}: 디버그 이미지 발행 실패: {e}")

    def process_image(self, cv_image, detector: PoolDetector):
        # 1. 이미지 크기 확인 및 3배 확대 (원래 해상도 유지 보전)
        h_orig, w_orig = cv_image.shape[:2]
        scale_factor = 3.0
        cv_image_resized = cv2.resize(
            cv_image, 
            (int(w_orig * scale_factor), int(h_orig * scale_factor)), 
            interpolation=cv2.INTER_CUBIC
        )

        # 2. 조명 평탄화 (Illumination Normalization)
        illum_bg = cv2.GaussianBlur(cv_image_resized, (151, 151), 0)
        normalized = cv2.divide(cv_image_resized, illum_bg, scale=255)

        # 3. 그레이스케일 변환 및 가우시안 블러
        gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # [개선 1] 수조 테두리 마스크 확장 (기존 -55에서 -25로 조정하여 테두리 스폰 이물질 구출) ⭐
        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        radius = int(min(h, w) // 2 - 25) 
        mask_circle = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask_circle, center, radius, 255, -1)

        # -------------------------------------------------------------
        # 4. [상어(Fish) 탐지 파이프라인]
        # -------------------------------------------------------------
        # 조명 근처의 흐릿한 형체 및 반만 잠긴 상어를 잡기 위해 상수 C를 3으로 대폭 낮춰 감도 극대화
        fish_mask_raw = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 101, 3
        )
        fish_mask = cv2.bitwise_and(fish_mask_raw, mask_circle)

        # 상어 파이프라인용 대형 모폴로지 (수면 위/아래 조각난 상어 몸통을 하나로 결합)
        kernel_fish_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_fish_close = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        fish_mask_processed = cv2.morphologyEx(fish_mask, cv2.MORPH_OPEN, kernel_fish_open)
        fish_mask_processed = cv2.morphologyEx(fish_mask_processed, cv2.MORPH_CLOSE, kernel_fish_close)

        # 상어 윤곽선 추출
        fish_contours_raw, _ = cv2.findContours(fish_mask_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        fish_contours = []
        fish_count_total = 0

        for cnt in fish_contours_raw:
            area = cv2.contourArea(cnt)
            # 수조 테두리선 확장으로 인해 걸릴 수 있는 거대 외곽 노이즈 차단 (면적 45000px 이상 제외)
            if 1200 <= area <= 45000:
                rect = cv2.minAreaRect(cnt)
                (cx, cy), (w_rect, h_rect), angle = rect
                max_dim = max(w_rect, h_rect)
                min_dim = min(w_rect, h_rect)
                aspect_ratio = float(max_dim) / min_dim if min_dim != 0 else 0
                
                # 수조 지름의 절반을 넘는 비정상적 거대 띠 노이즈 제거
                if max_dim > (min(h, w) * 0.65):
                    continue

                # 반만 잠겨 종횡비가 깨진 상어도 잡을 수 있도록 종횡비 기준을 1.4로 완화 ⭐
                if aspect_ratio >= 1.4:
                    fish_contours.append(cnt)
                    
                    # 마릿수 뻥튀기 원천 차단 (실제 기하학적 OBB 면적 기준 정밀 정규화)
                    obb_area = w_rect * h_rect
                    if obb_area >= 70000:
                        fish_count_total += 3
                    elif obb_area >= 36000:
                        fish_count_total += 2
                    else:
                        fish_count_total += 1

        # -------------------------------------------------------------
        # 5. [이물질(Debris) 탐지 파이프라인]
        # -------------------------------------------------------------
        # 조명 근처의 미세 이물질까지 잡도록 초고감도 설정 (C=2)
        debris_mask_raw = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 45, 2
        )
        debris_mask = cv2.bitwise_and(debris_mask_raw, mask_circle)

        # [개선 2] 이물질은 절대 크게 메우면 안 됨! 붙어있는 2개를 유지하기 위해 미세 커널(3x3) 사용 ⭐
        kernel_debris = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        debris_mask_processed = cv2.morphologyEx(debris_mask, cv2.MORPH_OPEN, kernel_debris)
        debris_mask_processed = cv2.morphologyEx(debris_mask_processed, cv2.MORPH_CLOSE, kernel_debris)

        # 상어가 위치한 영역은 이물질 마스크에서 완전히 지워버림 (상어 지느러미 오탐지 방지)
        if len(fish_contours) > 0:
            cv2.drawContours(debris_mask_processed, fish_contours, -1, 0, thickness=cv2.FILLED)

        # 이물질 윤곽선 추출
        debris_contours_raw, _ = cv2.findContours(debris_mask_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        debris_contours = []
        for cnt in debris_contours_raw:
            area = cv2.contourArea(cnt)
            # 3배 확대 스케일 기준, 분리된 개별 이물질 면적 스펙트럼 필터링 (15px ~ 500px)
            if 15 <= area <= 500:
                x_b, y_b, w_b, h_b = cv2.boundingRect(cnt)
                # 수조 벽면 잔여 테두리(너무 정방형으로 길게 남는 선) 필터링
                if w_b > (w * 0.05) or h_b > (h * 0.05):
                    continue
                aspect_ratio = float(w_b) / h_b if h_b != 0 else 0
                if 0.15 <= aspect_ratio <= 6.0:
                    debris_contours.append(cnt)

        # -------------------------------------------------------------
        # 6. 후처리 데이터 매핑 및 시각화 (기존 구조 안정적 유지)
        # -------------------------------------------------------------
        # 로봇 청소선 몸체 파츠 등으로 인해 상시 고정 팝업되는 4~5개의 미세 오탐지 점을 
        # 전체 이물질 개수에서 항상 -5씩 동적 보정 (하한은 0으로 고정)
        current_debris_cnt = max(0, len(debris_contours) - 5)
        detector.debris_history.append(current_debris_cnt)
        max_debris = max(detector.debris_history) if len(detector.debris_history) > 0 else current_debris_cnt

        if max_debris <= 50:
            pollution_level = 0.0
        elif 51 <= max_debris <= 70:
            pollution_level = 1.0
        else:
            pollution_level = 2.0

        fish_present = 1 if fish_count_total > 0 else 0
        debug_image = cv_image.copy()

        # 상어 박스 시각화 (Red OBB)
        for cnt in fish_contours:
            cnt_orig = (cnt / scale_factor).astype(np.int32)
            rect_orig = cv2.minAreaRect(cnt_orig)
            box_orig = np.int64(cv2.boxPoints(rect_orig))
            cv2.drawContours(debug_image, [box_orig], 0, (0, 0, 255), 3)
            
            cx, cy = int(rect_orig[0][0]), int(rect_orig[0][1])
            obb_area_orig = rect_orig[1][0] * rect_orig[1][1]
            
            if obb_area_orig >= 7700:
                lbl = "Sturgeon (x3)"
            elif obb_area_orig >= 4000:
                lbl = "Sturgeon (x2)"
            else:
                lbl = "Sturgeon"
            cv2.putText(debug_image, lbl, (cx - 30, cy - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # 이물질 박스 시각화 (Green Bounding Box)
        for cnt in debris_contours:
            cnt_orig = (cnt / scale_factor).astype(np.int32)
            x_b, y_b, w_b, h_b = cv2.boundingRect(cnt_orig)
            cv2.rectangle(debug_image, (x_b, y_b), (x_b + w_b, y_b + h_b), (0, 255, 0), 2)

        overlay_text = f"Fish: {fish_count_total} | Debris: {current_debris_cnt}/{max_debris} | Poll: {int(pollution_level)}"
        cv2.putText(debug_image, overlay_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

        return fish_present, current_debris_cnt, max_debris, pollution_level, debug_image

def main(args=None):
    rclpy.init(args=args)
    node = TopDetectionNode()
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