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
        
        self.num_pools = 7
        self.active_pool_id = 1
        self.auto_select = True
        
        self.latest_status = {i: {} for i in range(1, self.num_pools + 1)}
        self.latest_cmd = {i: Twist() for i in range(1, self.num_pools + 1)}
        
        # 동적 구독 생성
        self.sub_imgs = {}
        self.sub_statuses = {}
        self.sub_cmds = {}
        
        for i in range(1, self.num_pools + 1):
            # 람다 캡처 문제 해결을 위해 pool_id를 기본 인자로 전달
            self.sub_imgs[i] = self.create_subscription(
                Image, f'/pool_{i}/top_img_det', lambda msg, pid=i: self.img_callback(msg, pid), 10)
            self.sub_statuses[i] = self.create_subscription(
                String, f'/pool_{i}/status_string', lambda msg, pid=i: self.status_callback(msg, pid), 10)
            self.sub_cmds[i] = self.create_subscription(
                Twist, f'/under_robot_{i}/cmd_vel', lambda msg, pid=i: self.cmd_callback(msg, pid), 10)
                
        self.get_logger().info("통합 뷰어 노드가 시작되었습니다! (키보드 1~7을 눌러 수동으로 수조 변경 가능)")

    def status_callback(self, msg, pool_id):
        try:
            status_data = json.loads(msg.data)
            self.latest_status[pool_id] = status_data
            
            # 자동 선택 모드일 경우, 가장 "대표적인" 수조를 찾습니다 (이물질과 상어가 모두 있는 곳)
            if self.auto_select:
                best_pool = self.active_pool_id
                max_score = -1
                for pid in range(1, self.num_pools + 1):
                    s = self.latest_status.get(pid, {})
                    debris_count = s.get("debris_count", 0)
                    fish_count = s.get("fish_count", 0)
                    suspicious_count = s.get("fish_count_suspicious", 0)
                    
                    # 점수: 상어가 있고 이물질이 있으면 높은 점수
                    score = 0
                    if fish_count > 0: score += 10
                    if suspicious_count > 0: score += 5
                    if debris_count > 0: score += 20 + debris_count
                    
                    if score > max_score and score > 0:
                        max_score = score
                        best_pool = pid
                
                if best_pool != self.active_pool_id and max_score > 0:
                    self.active_pool_id = best_pool
                    self.get_logger().info(f"대표 수조 자동 선택: Pool_{self.active_pool_id} (이물질 및 상어 스폰 감지됨)")
                    
        except Exception:
            pass

    def cmd_callback(self, msg, pool_id):
        self.latest_cmd[pool_id] = msg

    def img_callback(self, msg, pool_id):
        # 현재 활성화된 수조의 이미지만 렌더링
        if pool_id != self.active_pool_id:
            return
            
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"이미지 변환 실패: {e}")
            return
            
        status = self.latest_status.get(pool_id, {})
        cmd = self.latest_cmd.get(pool_id, Twist())
            
        # 1. VLM 최종 통과한 이물질(상어똥) 개수 파악
        debris_positions = status.get("debris_positions", [])
        # 마커와 텍스트는 가시성을 위해 제거 (fish_detection_node에서 바운딩 박스로 그려짐)
            
        # 2. 로봇 현재 Action 상태 표시
        linear_x = cmd.linear.x
        angular_z = cmd.angular.z
        
        if abs(linear_x) > 0.01 or abs(angular_z) > 0.01:
            robot_state = f"ROBOT ACTION: Moving to target (v: {linear_x:.2f}, w: {angular_z:.2f})"
            color = (0, 255, 0)
        else:
            robot_state = "ROBOT ACTION: Idle / Scanning"
            color = (200, 200, 200)
            
        # 상단 오버레이 패널
        overlay = cv_image.copy()
        cv2.rectangle(overlay, (10, 10), (600, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, cv_image, 0.4, 0, cv_image)
        
        cv2.putText(cv_image, f"[Pool {pool_id} View] Perception -> VLM -> Action", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(cv_image, robot_state, (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        mode_text = "Mode: AUTO (finding best pool)" if self.auto_select else f"Mode: MANUAL (Pool {self.active_pool_id})"
        cv2.putText(cv_image, mode_text, (20, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        cv2.imshow("AquaSweep - Integrated Process Viewer", cv_image)
        
        key = cv2.waitKey(1) & 0xFF
        if ord('1') <= key <= ord('7'):
            self.active_pool_id = key - ord('0')
            self.auto_select = False
            self.get_logger().info(f"수동으로 수조 {self.active_pool_id}번으로 변경했습니다.")
        elif key == ord('a') or key == ord('A'):
            self.auto_select = True
            self.get_logger().info("자동 수조 선택 모드로 변경했습니다.")

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
