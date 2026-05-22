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
                10
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

        # 개발 중에만 크롭 상태를 모니터링할 수 있도록 Pool_1에 대한 간의 raw_img 창 기동
        if pool_id == 1:
            try:
                cv2.imshow("pool_1_raw_img (ROI Cropped)", cv_image)
                cv2.waitKey(1)
            except Exception as e:
                pass

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

        if should_log:
            self.get_logger().info(
                f"🟢 [Pool_{pool_id} | 프레임: {detector.frame_count}] "
                f"Fish: {fish_present} | Debris: {debris_count}/{max_debris} | "
                f"Pollution: {pollution_level}"
            )

        if debug_image is not None:
            try:
                debug_msg = self.bridge.cv2_to_imgmsg(debug_image, encoding="bgr8")
                debug_msg.header = msg.header
                self.pub_debug[pool_id].publish(debug_msg)
            except Exception as e:
                self.get_logger().error(f"🔴 Pool_{pool_id}: 디버그 이미지 발행 실패: {e}")

    def process_image(self, cv_image, detector: PoolDetector):
        # 1. 전처리: LAB 색공간 기반 CLAHE 적용 후 Gaussian Blur
        lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        blurred = cv2.GaussianBlur(enhanced_bgr, (5, 5), 0)

        # 2. 색공간 변환 및 마스킹 (지정된 단일 HSV 임계값 범위 완벽 준수)
        # H: 5~35, S: 20~255, V: 80~255
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        lower_hsv = np.array([5, 20, 80])
        upper_hsv = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

        # 3. 모폴로지 연산 (3x3 커널로 Opening 노이즈 제거 -> 5x5 커널로 Closing 내부 채우기)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask_opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        mask_closed = cv2.morphologyEx(mask_opened, cv2.MORPH_CLOSE, kernel_close)

        # 4. 윤곽선 추출 (물고기 먼저 검출)
        contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        fish_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 물고기 탐지 기준: 윤곽선 면적이 1000 픽셀 이상이면서 가로/세로 종횡비(Aspect Ratio)가 2.0 이상인 객체
            if area >= 1000:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = max(w / h if h != 0 else 0, h / w if w != 0 else 0)
                if aspect_ratio >= 2.0:
                    fish_contours.append(cnt)

        # 물고기로 판별된 윤곽선 영역을 이물질 마스크에서 완전히 제외 (0으로 채움)
        debris_mask = mask_closed.copy()
        if len(fish_contours) > 0:
            cv2.drawContours(debris_mask, fish_contours, -1, 0, thickness=cv2.FILLED)

        # 물고기가 완전히 제외된 마스크에서 이물질 윤곽선 추출
        debris_contours_raw, _ = cv2.findContours(debris_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        debris_contours = []
        for cnt in debris_contours_raw:
            area = cv2.contourArea(cnt)
            # 이물질 탐지 기준: 윤곽선의 넓이가 50 픽셀 이상이면서 종횡비가 0.2 ~ 5.0 사이인 객체
            if area >= 50:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = float(w) / h if h != 0 else 0
                if 0.2 <= aspect_ratio <= 5.0:
                    debris_contours.append(cnt)

        # 5. 오염도 데이터 보정 (Max-Hold Filter)
        current_debris_cnt = len(debris_contours)
        detector.debris_history.append(current_debris_cnt)
        
        # 30프레임 미만이더라도 현재 들어온 데이터들 내에서 실시간 최댓값 반환 (지연 없음)
        max_debris = max(detector.debris_history) if len(detector.debris_history) > 0 else current_debris_cnt

        # 6. Pollution Level 산정 (50 이하: 0, 51 ~ 70: 1, 71 이상: 2)
        if max_debris <= 50:
            pollution_level = 0.0
        elif 51 <= max_debris <= 70:
            pollution_level = 1.0
        else:
            pollution_level = 2.0

        # 수조 내 물고기 존재 여부 (있으면 1, 없으면 0)
        fish_present = 1 if len(fish_contours) > 0 else 0

        # 7. 시각화
        debug_image = cv_image.copy()

        for cnt in fish_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 0, 255), 3)
            cv2.putText(debug_image, "Sturgeon", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        for cnt in debris_contours:
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        overlay_text = f"Fish Present: {fish_present} | Debris: {current_debris_cnt}/{max_debris} | Poll: {int(pollution_level)}"
        cv2.putText(debug_image, overlay_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

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