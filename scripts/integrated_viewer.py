#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
import cv2
import json
import numpy as np

class IntegratedViewer(Node):
    def __init__(self):
        super().__init__('integrated_viewer')
        self.bridge = CvBridge()
        
        # Subscriptions
        # 1. 인지 & VLM 판단 결과가 담긴 이미지 토픽
        self.sub_img = self.create_subscription(
            Image, '/pool_1/top_img_det', self.img_callback, 10)
        # 2. VLM 최종 판단 결과가 담긴 상태 문자열
        self.sub_status = self.create_subscription(
            String, '/pool_1/status_string', self.status_callback, 10)
        # 3. 로봇의 이동 명령 (실행 과정)
        self.sub_cmd = self.create_subscription(
            Twist, '/under_robot_1/cmd_vel', self.cmd_callback, 10)
        
        self.latest_status = {}
        self.latest_cmd = Twist()
        
        self.get_logger().info("통합 뷰어 노드가 시작되었습니다! 데이터를 기다리는 중...")

    def status_callback(self, msg):
        try:
            self.latest_status = json.loads(msg.data)
        except Exception:
            pass

    def cmd_callback(self, msg):
        self.latest_cmd = msg

    def img_callback(self, msg):
        try:
            # ROS 이미지를 OpenCV 이미지로 변환
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"이미지 변환 실패: {e}")
            return
            
        # 1. VLM 최종 통과한 이물질(상어똥) 시각화
        debris_positions = self.latest_status.get("debris_positions", [])
        for pos in debris_positions:
            cx, cy = pos
            # 빨간색 십자 마커와 VLM 검증 완료 텍스트
            cv2.drawMarker(cv_image, (int(cx), int(cy)), (0, 0, 255), markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)
            cv2.putText(cv_image, "VLM Verified: POOP", (int(cx) + 10, int(cy) - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
        # 2. 로봇 현재 Action 상태 표시
        linear_x = self.latest_cmd.linear.x
        angular_z = self.latest_cmd.angular.z
        
        if abs(linear_x) > 0.01 or abs(angular_z) > 0.01:
            robot_state = f"ROBOT ACTION: Moving to target (v: {linear_x:.2f}, w: {angular_z:.2f})"
            color = (0, 255, 0)
        else:
            robot_state = "ROBOT ACTION: Idle / Scanning"
            color = (200, 200, 200)
            
        # 상단 오버레이 패널
        overlay = cv_image.copy()
        cv2.rectangle(overlay, (10, 10), (600, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, cv_image, 0.4, 0, cv_image)
        
        cv2.putText(cv_image, "[Perception -> VLM Validation -> Action]", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(cv_image, robot_state, (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 화면 출력
        cv2.imshow("AquaSweep - Integrated Process Viewer", cv_image)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    viewer = IntegratedViewer()
    
    try:
        rclpy.spin(viewer)
    except KeyboardInterrupt:
        pass
    finally:
        viewer.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
