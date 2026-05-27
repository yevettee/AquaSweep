#!/usr/bin/env python3
"""
AquaSweep Integrated Viewer
- ROS spin은 별도 스레드에서 실행
- OpenCV imshow/waitKey는 메인 스레드에서만 실행 (GUI 동결 방지)
"""
import threading
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
        self._lock = threading.Lock()

        self.num_pools = 7
        self.active_pool_id = 1
        self.auto_select = True
        self._representative_locked = False  # True가 되면 대표 수조 더 이상 변경 안 함

        self.latest_status = {i: {} for i in range(1, self.num_pools + 1)}
        self.latest_cmd = {i: Twist() for i in range(1, self.num_pools + 1)}
        # 메인 스레드로 전달할 최신 이미지 (pool_id → cv_image)
        self.latest_frame: dict[int, np.ndarray] = {}

        # 동적 구독 생성
        self.sub_imgs = {}
        self.sub_statuses = {}
        self.sub_cmds = {}
        for i in range(1, self.num_pools + 1):
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
            with self._lock:
                self.latest_status[pool_id] = status_data

            # 자동 선택: 이미 대표 수조가 결정됐으면 다시 선택하지 않음
            if self.auto_select and not self._representative_locked:
                best_pool = self.active_pool_id
                max_score = -1
                with self._lock:
                    status_snapshot = dict(self.latest_status)

                for pid in range(1, self.num_pools + 1):
                    s = status_snapshot.get(pid, {})
                    debris_count = s.get("debris_count", 0)
                    fish_count = s.get("fish_count", 0)
                    suspicious_count = s.get("fish_count_suspicious", 0)

                    has_alive = fish_count > 0
                    has_dead = suspicious_count > 0
                    has_debris = debris_count > 0

                    if has_alive and has_dead and has_debris:
                        score = 1000 + fish_count + suspicious_count + debris_count
                    elif has_alive and has_debris:
                        score = 100 + fish_count + debris_count
                    elif has_dead and has_debris:
                        score = 80 + suspicious_count + debris_count
                    elif has_alive:
                        score = 10 + fish_count
                    elif has_debris:
                        score = 5 + debris_count
                    else:
                        score = 0

                    if score > max_score and score > 0:
                        max_score = score
                        best_pool = pid

                if best_pool != self.active_pool_id and max_score > 0:
                    self.active_pool_id = best_pool
                    s = status_snapshot.get(best_pool, {})
                    self.get_logger().info(
                        f"대표 수조 자동 선택: Pool_{self.active_pool_id} "
                        f"(alive={s.get('fish_count', 0)}, "
                        f"dead={s.get('fish_count_suspicious', 0)}, "
                        f"debris={s.get('debris_count', 0)})"
                    )

                # 이물질이 있는 수조가 결정되면 잠금 (더 이상 변경 안 함)
                if max_score >= 5:
                    self._representative_locked = True
                    self.get_logger().info(f"대표 수조 확정: Pool_{self.active_pool_id} (이후 변경 없음)")

        except Exception:
            pass

    def cmd_callback(self, msg, pool_id):
        with self._lock:
            self.latest_cmd[pool_id] = msg

    def img_callback(self, msg, pool_id):
        """수신한 이미지를 버퍼에 저장 (GUI는 메인 스레드에서 그림)."""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            with self._lock:
                self.latest_frame[pool_id] = cv_image
        except Exception as e:
            self.get_logger().error(f"이미지 변환 실패: {e}")

    def render_frame(self):
        """메인 스레드에서 호출: 현재 활성 수조 이미지를 화면에 그린다."""
        with self._lock:
            pool_id = self.active_pool_id
            cv_image = self.latest_frame.get(pool_id)
            status = dict(self.latest_status.get(pool_id, {}))
            cmd = self.latest_cmd.get(pool_id, Twist())

        if cv_image is None:
            return

        frame = cv_image.copy()
        h, w = frame.shape[:2]

        fish_count = status.get("fish_count", 0)
        suspicious = status.get("fish_count_suspicious", 0)
        debris_count = status.get("debris_count", 0)

        linear_x = cmd.linear.x
        angular_z = cmd.angular.z
        if abs(linear_x) > 0.01 or abs(angular_z) > 0.01:
            robot_state = f"Moving (v={linear_x:.2f}, w={angular_z:.2f})"
            rob_color = (0, 255, 0)
        else:
            robot_state = "Idle / Scanning"
            rob_color = (200, 200, 200)

        # 상단 오버레이 (이미지 폭에 맞게)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cv2.putText(frame, f"[Pool {pool_id}] Alive:{fish_count}  Dead:{suspicious}  Debris:{debris_count}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Robot: {robot_state}",
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, rob_color, 2)
        mode_text = "AUTO" if self.auto_select else f"MANUAL"
        cv2.putText(frame, f"Mode: {mode_text}  |  press 1-7 to switch pool, A=auto",
                    (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        cv2.imshow("AquaSweep - Integrated Process Viewer", frame)


def main(args=None):
    rclpy.init(args=args)
    viewer = IntegratedViewer()

    # ROS spin을 별도 스레드에서 실행
    spin_thread = threading.Thread(target=rclpy.spin, args=(viewer,), daemon=True)
    spin_thread.start()

    try:
        while rclpy.ok():
            viewer.render_frame()
            key = cv2.waitKey(30) & 0xFF  # 메인 스레드에서만 waitKey
            if key == ord('q') or key == 27:
                break
            elif ord('1') <= key <= ord('7'):
                viewer.active_pool_id = key - ord('0')
                viewer.auto_select = False
                viewer.get_logger().info(f"수동으로 수조 {viewer.active_pool_id}번으로 변경")
            elif key in (ord('a'), ord('A')):
                viewer.auto_select = True
                viewer.get_logger().info("자동 수조 선택 모드")
    except KeyboardInterrupt:
        pass
    finally:
        viewer.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
