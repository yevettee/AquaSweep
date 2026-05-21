#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np

# 사용자 정의 ROS2 메시지 패키지 임포트 (인터페이스 명세서 준수)
try:
    from cleaner_msgs.msg import Detection, DetectionArray
    _CLEANER_MSGS_AVAILABLE = True
except ImportError:
    class Detection: pass
    class DetectionArray: pass
    _CLEANER_MSGS_AVAILABLE = False


class PerceptionNode(Node):
    """
    Isaac Sim 내부에서 카메라 영상을 구독하여 이물질(분변)을 탐지하고,
    탐지된 결과를 ROS2 토픽으로 발행하는 비전 파이프라인 노드.
    추후 내부의 detect_debris 로직만 YOLO 기반 딥러닝 추론으로 교체할 수 있도록 
    입출력(I/O)이 완전히 분리된 모듈형 구조입니다.
    """
    def __init__(self):
        super().__init__('perception_node')
        
        # ROS2 인터페이스 규격에 따른 구독(Subscribe) 설정 (원시 이미지 수신)
        self.subscription = self.create_subscription(
            Image,
            '/cleaner/camera/image_raw',
            self.image_callback,
            10
        )
        
        # ROS2 인터페이스 규격에 따른 발행(Publish) 설정
        self._msg_available = _CLEANER_MSGS_AVAILABLE
        if self._msg_available:
            try:
                self.publisher_detections = self.create_publisher(
                    DetectionArray,
                    '/cleaner/perception/detections',
                    10
                )
            except Exception as e:
                self.get_logger().error(f"Failed to create publisher for detections: {e}")
                self._msg_available = False
        
        if not self._msg_available:
            self.get_logger().warn("⚠️ [Warning] cleaner_msgs 패키지가 빌드되어 있지 않거나 환경에 없습니다. 3D 좌표 결과 발행은 비활성화되며, 실시간 OpenCV 디버깅 비디오 화면 창만 활성화됩니다.")

        self.publisher_debug = self.create_publisher(
            Image,
            '/cleaner/perception/image_debug',
            10
        )
        
        self.bridge = CvBridge()
        
        # 내부 카메라 입력 주기는 30Hz일 수 있으나, 
        # 웹 UI 및 대시보드 부하를 고려해 처리는 10Hz로 Throttle (타이머 콜백 활용)
        self.process_timer = self.create_timer(0.1, self.timer_callback)
        self.latest_image = None
        self._last_image_time = None  # 마지막 이미지 수신 시각 (자동 종료 감지용)
        self._no_signal_timeout = 5.0  # 5초간 이미지가 안 오면 자동 종료
        
        self.get_logger().info('Perception node initialized. Waiting for /cleaner/camera/image_raw...')

    def image_callback(self, msg):
        """카메라로부터 수신한 가장 최신 이미지를 캐싱 (30Hz 수신)"""
        self.latest_image = msg
        self._last_image_time = self.get_clock().now()

    def timer_callback(self):
        """10Hz 주기로 캐싱된 이미지를 처리하고 결과를 발행"""
        # 이미지 수신 타임아웃 체크 → Isaac Sim이 종료되면 자동으로 창 닫고 노드 종료
        if self._last_image_time is not None:
            elapsed = (self.get_clock().now() - self._last_image_time).nanoseconds / 1e9
            if elapsed > self._no_signal_timeout:
                self.get_logger().warn(f'⚠️ {self._no_signal_timeout}초간 카메라 신호 없음 — Isaac Sim 종료 감지. 자동 종료합니다.')
                cv2.destroyAllWindows()
                cv2.waitKey(1)  # 창 닫기 이벤트 처리 필수
                import os as _os
                _os._exit(0)  # 프로세스 강제 종료 (좀비 방지)
        
        if self.latest_image is None:
            return
        
        try:
            # 1. ROS Image 메시지를 OpenCV BGR 이미지 포맷으로 변환
            cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, "bgr8")
        except Exception as e:
            self.get_logger().error(f"Failed to convert ROS Image to OpenCV: {e}")
            return
            
        # 2. OpenCV 비전 파이프라인(HSV 마스킹) 수행
        detections, debug_image = self.detect_debris(cv_image)
        
        # 실시간 OpenCV 디버그 창 팝업 (사용자 화면 DISPLAY에 직접 실시간 렌더링)
        if debug_image is not None:
            # 디버그 창 크기를 640x480으로 리사이즈하여 화면 점유 최소화
            debug_resized = cv2.resize(debug_image, (640, 480))
            cv2.imshow("Blue Robotics Low-Light Vision Debugger", debug_resized)
            cv2.waitKey(1)
        
        # 실시간 모니터링 로그 출력 (사용자 실행 검증 증명용)
        if len(detections) > 0:
            self.get_logger().info(f"🟢 [Active] Blue Robotics 수중 저조도 이물질 {len(detections)}개 실시간 탐지 성공!")
            for idx, det in enumerate(detections):
                self.get_logger().info(f"   ↳ [이물질 #{idx+1}] 픽셀: ({det.u:.0f}, {det.v:.0f}) ➔ 3D 로봇 좌표: ({det.world_x:.2f}m, {det.world_y:.2f}m)")
        else:
            if not hasattr(self, '_idle_cnt'):
                self._idle_cnt = 0
            self._idle_cnt += 1
            if self._idle_cnt % 30 == 0:
                self.get_logger().info("🔵 [Idle] Blue Robotics 카메라 피드 정상 수신 중... (이물질 대기)")

        # 3. 탐지 결과(DetectionArray) 발행
        if self._msg_available:
            try:
                det_msg = DetectionArray()
                det_msg.header = self.latest_image.header
                det_msg.detections = detections
                self.publisher_detections.publish(det_msg)
            except Exception as e:
                self.get_logger().warn(f"Failed to publish detections (Missing msg definitions?): {e}")
        
        # 4. 디버그용 이미지(Bounding Box 오버레이) 발행 (구독하는 노드가 있을 경우에만)
        if debug_image is not None and self.publisher_debug.get_subscription_count() > 0:
            try:
                debug_msg = self.bridge.cv2_to_imgmsg(debug_image, "bgr8")
                debug_msg.header = self.latest_image.header
                self.publisher_debug.publish(debug_msg)
            except Exception as e:
                self.get_logger().error(f"Failed to publish debug image: {e}")

    def detect_debris(self, cv_image):
        """
        OpenCV 전통 기법(CLAHE 저조도 보정 + HSV 마스킹)을 이용한 5단계 분변 탐지 파이프라인.
        Blue Robotics Low-Light HD USB Camera의 저조도/수중 특성을 반영하여
        HSV 변환 전에 CLAHE(적응형 히스토그램 평활화) 대비 강화를 선행 실행합니다.
        
        [파이프라인 단계]
        1) 전처리: CLAHE 대비 강화 (저조도 환경 극복) & 가우시안 블러 (노이즈 제거)
        2) 색공간 변환: BGR -> HSV
        3) 색상 마스킹: 명도 대비가 복원된 환경을 고려한 정밀 갈색/어두운색 임계값 적용
        4) 모폴로지 연산: Opening 및 Closing으로 노이즈 제거 및 외곽선 보정
        5) 윤곽선 추출: 면적 및 종횡비 필터링을 통해 타겟 도출
        """
        # 1-1) 저조도 수중 환경을 극복하기 위해 명도(Luminance) 채널에 CLAHE 적용
        # LAB 색공간으로 변환하여 밝기(L) 채널만 대비 강화 후 다시 BGR로 복원
        lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 1-2) 전처리: 가우시안 블러 (Kernel 5x5) 노이즈 제거
        blurred = cv2.GaussianBlur(enhanced_bgr, (5, 5), 0)
        
        # 2) 색공간 변환: BGR -> HSV
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        # 3) 색상 마스킹: 시뮬레이터 조명 환경을 고려한 갈색/베이지색 분변 탐지 범위
        # H(5~35): 붉은색~갈색~주황 영역
        # S(20~255): 배경(하늘색 바닥)과 구분 — 채도가 낮은 배경 제외
        # V(80~255): 강한 조명(DistantLight 3000) 아래에서 밝게 렌더링되는 파티클 포착
        lower_bound = np.array([5, 20, 80])
        upper_bound = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # 4) 모폴로지 연산: Opening (3x3) 수행 후 Closing (5x5)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        
        mask_opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        mask_closed = cv2.morphologyEx(mask_opened, cv2.MORPH_CLOSE, kernel_close)
        
        # 5) 윤곽선 추출 및 필터링
        contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        debug_image = cv_image.copy()
        
        # 이미지 크기 동적 획득 (해상도 독립 좌표계 연산용)
        height, width = cv_image.shape[:2]
        
        for cnt in contours:
            # 면적 계산 및 필터링 (50px^2 이상)
            area = cv2.contourArea(cnt)
            if area < 50:
                continue
                
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h if h != 0 else 0
            
            # 종횡비 필터링 (0.2 ~ 5.0 범위)
            if 0.2 <= aspect_ratio <= 5.0:
                # 픽셀 중심 좌표 계산
                u = int(x + w / 2)
                v = int(y + h / 2)
                
                # 로봇 좌표계로 변환 (월드 좌표 x, y)
                world_x, world_y = self.pixel_to_robot_frame(u, v, width, height)
                
                # Detection 메시지 구성
                try:
                    det = Detection()
                    det.class_name = "debris"
                    det.u = float(u)
                    det.v = float(v)
                    det.world_x = float(world_x)
                    det.world_y = float(world_y)
                    det.area_px = float(area)
                    detections.append(det)
                except Exception:
                    pass
                
                # 디버깅용 시각화 오버레이 적용 (Bounding Box, Center Point, Text)
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(debug_image, (u, v), 4, (0, 0, 255), -1)
                cv2.putText(debug_image, f"Debris ({world_x:.2f}, {world_y:.2f})", (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 2)
                
        return detections, debug_image

    def pixel_to_robot_frame(self, u, v, width, height):
        """
        카메라 픽셀 좌표(u, v)를 바닥 평면(z=0) 가정을 통해
        로봇 좌표계(world_x, world_y)로 변환하는 함수.
        
        기본 기하학 수식:
        1. 이미지 평면 -> 정규 좌표계 (Intrinsic K 역행렬 적용)
           X_c = (u - cx) * Z_c / fx
           Y_c = (v - cy) * Z_c / fy
        2. 정규 좌표계 -> 로봇 베이스 프레임 (Extrinsic T 적용)
        3. 바닥 평면 가정: Z_w = 0 인 조건을 이용해 Z_c를 산출하고 X_w, Y_w 도출.
        """
        # 현재는 Placeholder로 임의의 스케일 맵핑을 수행합니다.
        # 카메라 높이 2.5m, 80도 FOV 기준 간이 투영
        import math
        fov_rad = math.radians(80.0)
        camera_height = 2.5
        half_w = width / 2.0
        half_h = height / 2.0
        fx = half_w / math.tan(fov_rad / 2.0)
        
        world_x = (u - half_w) / fx * camera_height
        world_y = (v - half_h) / fx * camera_height
        return world_x, world_y


def main(args=None):
    rclpy.init(args=args)
    
    perception_node = PerceptionNode()
    
    try:
        rclpy.spin(perception_node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        perception_node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass

if __name__ == '__main__':
    main()
