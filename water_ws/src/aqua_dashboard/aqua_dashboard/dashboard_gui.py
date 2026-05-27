#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""PyQt5 GUI dashboard for AquaSweep - external process to avoid Isaac Sim rclpy conflicts.

Single-pool view with a dropdown to switch between pools. Only the active pool's
camera streams are subscribed; pool/robot status feeds for all pools stay live so
switching is instant from cached state.

Usage:
    ros2 run aqua_dashboard dashboard_gui
"""

import sys
from functools import partial
from typing import Dict, Optional

import numpy as np
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from aqua_interfaces.action import CleanFloor, CleanWall
from aqua_interfaces.msg import MotionStatus, PoolStatus, RobotStatus
from aqua_interfaces.srv import PauseMotion, ResumeMotion

from .ros_topics import (
    planner_pause_service,
    planner_start_service,
    pool_clean_floor_action,
    pool_clean_wall_action,
    pool_ids,
    pool_motion_status_topic,
    pool_pause_motion_service,
    pool_resume_motion_service,
    pool_robot_status_topic,
    pool_status_topic,
    pool_top_cam_det_topic,
    pool_under_cam_det_topic,
)

_BEST_EFFORT_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)

MOTION_STATE_NAMES = {
    MotionStatus.IDLE: "IDLE",
    MotionStatus.RUNNING: "RUNNING",
    MotionStatus.PAUSED: "PAUSED",
    MotionStatus.DONE: "DONE",
}


class SignalEmitter(QObject):
    """Qt signal emitter for ROS2 node callbacks."""
    pool_status_received = pyqtSignal(int, object)
    robot_status_received = pyqtSignal(int, object)
    motion_status_received = pyqtSignal(int, str, object)  # pool_id, motion_type, msg
    top_cam_received = pyqtSignal(int, object)
    under_cam_received = pyqtSignal(int, object)
    service_response_received = pyqtSignal(str, bool, str)


class RosSpinThread(QThread):
    """Thread for spinning the ROS2 node without blocking the Qt event loop."""

    def __init__(self, node: Node, parent=None):
        super().__init__(parent)
        self._node = node
        self._executor = MultiThreadedExecutor()
        self._running = True

    def run(self):
        self._executor.add_node(self._node)
        while self._running and rclpy.ok():
            self._executor.spin_once(timeout_sec=0.05)
        self._executor.remove_node(self._node)

    def stop(self):
        self._running = False
        self.wait(2000)


class DashboardRosNode(Node):
    """ROS2 node for the dashboard with Qt signal integration."""

    def __init__(self, signal_emitter: SignalEmitter):
        super().__init__('aqua_dashboard_gui')
        self.signals = signal_emitter

        self._pool_status: Dict[int, Optional[PoolStatus]] = {}
        self._robot_status: Dict[int, Optional[RobotStatus]] = {}
        self._motion_status: Dict[int, Dict[str, Optional[MotionStatus]]] = {}
        self._clean_wall_clients: Dict[int, ActionClient] = {}
        self._clean_floor_clients: Dict[int, ActionClient] = {}

        for pool_id in pool_ids():
            self._pool_status[pool_id] = None
            self._robot_status[pool_id] = None
            self._motion_status[pool_id] = {'clean_floor': None, 'clean_wall': None}

            self.create_subscription(
                PoolStatus,
                pool_status_topic(pool_id),
                partial(self._on_pool_status, pool_id),
                10
            )
            self.create_subscription(
                RobotStatus,
                pool_robot_status_topic(pool_id),
                partial(self._on_robot_status, pool_id),
                10
            )

            for motion_type in ('clean_floor', 'clean_wall'):
                self.create_subscription(
                    MotionStatus,
                    pool_motion_status_topic(pool_id, motion_type),
                    partial(self._on_motion_status, pool_id, motion_type),
                    _BEST_EFFORT_QOS
                )

            # Per-pool actions — controller 직접 호출 (planner 우회, Wall/Floor 분리)
            self._clean_wall_clients[pool_id] = ActionClient(
                self, CleanWall, pool_clean_wall_action(pool_id)
            )
            self._clean_floor_clients[pool_id] = ActionClient(
                self, CleanFloor, pool_clean_floor_action(pool_id)
            )

        # Per-pool pause/resume services (Isaac Sim direct)
        self._pause_floor_clients: Dict[int, any] = {}
        self._resume_floor_clients: Dict[int, any] = {}
        self._pause_wall_clients: Dict[int, any] = {}
        self._resume_wall_clients: Dict[int, any] = {}
        for pool_id in pool_ids():
            self._pause_floor_clients[pool_id] = self.create_client(
                PauseMotion, pool_pause_motion_service(pool_id, 'clean_floor')
            )
            self._resume_floor_clients[pool_id] = self.create_client(
                ResumeMotion, pool_resume_motion_service(pool_id, 'clean_floor')
            )
            self._pause_wall_clients[pool_id] = self.create_client(
                PauseMotion, pool_pause_motion_service(pool_id, 'clean_wall')
            )
            self._resume_wall_clients[pool_id] = self.create_client(
                ResumeMotion, pool_resume_motion_service(pool_id, 'clean_wall')
            )

        self._active_pool_id: Optional[int] = None
        self._top_cam_sub = None
        self._under_cam_sub = None

        # Global planner services
        self._planner_start_client = self.create_client(Trigger, planner_start_service())
        self._planner_pause_client = self.create_client(Trigger, planner_pause_service())

        self.get_logger().info(f'DashboardRosNode ready | pools={list(pool_ids())}')

    def set_active_pool(self, pool_id: int) -> None:
        if self._active_pool_id == pool_id:
            return

        if self._top_cam_sub is not None:
            self.destroy_subscription(self._top_cam_sub)
            self._top_cam_sub = None
        if self._under_cam_sub is not None:
            self.destroy_subscription(self._under_cam_sub)
            self._under_cam_sub = None

        self._active_pool_id = pool_id

        self._top_cam_sub = self.create_subscription(
            Image,
            pool_top_cam_det_topic(pool_id),
            partial(self._on_top_cam_image, pool_id),
            10
        )
        self._under_cam_sub = self.create_subscription(
            Image,
            pool_under_cam_det_topic(pool_id),
            partial(self._on_under_cam_image, pool_id),
            10
        )

    def _on_pool_status(self, pool_id: int, msg: PoolStatus) -> None:
        self._pool_status[pool_id] = msg
        self.signals.pool_status_received.emit(pool_id, msg)

    def _on_robot_status(self, pool_id: int, msg: RobotStatus) -> None:
        self._robot_status[pool_id] = msg
        self.signals.robot_status_received.emit(pool_id, msg)

    def _on_motion_status(self, pool_id: int, motion_type: str, msg: MotionStatus) -> None:
        self._motion_status[pool_id][motion_type] = msg
        self.signals.motion_status_received.emit(pool_id, motion_type, msg)

    def _on_top_cam_image(self, pool_id: int, msg: Image) -> None:
        self.signals.top_cam_received.emit(pool_id, msg)

    def _on_under_cam_image(self, pool_id: int, msg: Image) -> None:
        self.signals.under_cam_received.emit(pool_id, msg)

    # --- Global Planner Services ---
    def call_global_start(self) -> None:
        if not self._planner_start_client.service_is_ready():
            self.signals.service_response_received.emit("global_start", False, "Planner start service not available")
            return
        request = Trigger.Request()
        future = self._planner_start_client.call_async(request)
        future.add_done_callback(self._on_global_start_response)

    def _on_global_start_response(self, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit("global_start", response.success, response.message)
        except Exception as exc:
            self.signals.service_response_received.emit("global_start", False, str(exc))

    def call_global_stop(self) -> None:
        if not self._planner_pause_client.service_is_ready():
            self.signals.service_response_received.emit("global_stop", False, "Planner pause service not available")
            return
        request = Trigger.Request()
        future = self._planner_pause_client.call_async(request)
        future.add_done_callback(self._on_global_stop_response)

    def _on_global_stop_response(self, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit("global_stop", response.success, response.message)
        except Exception as exc:
            self.signals.service_response_received.emit("global_stop", False, str(exc))

    # --- Per-Pool Actions (Dashboard → Controller → Isaac Sim) ---
    def call_pool_clean_wall(self, pool_id: int) -> None:
        client = self._clean_wall_clients.get(pool_id)
        if client is None or not client.wait_for_server(timeout_sec=1.0):
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_clean_wall", False, "CleanWall action not available"
            )
            return
        future = client.send_goal_async(CleanWall.Goal())
        future.add_done_callback(partial(self._on_clean_wall_goal_response, pool_id))

    def _on_clean_wall_goal_response(self, pool_id: int, future) -> None:
        try:
            handle = future.result()
            if handle.accepted:
                self.signals.service_response_received.emit(
                    f"pool_{pool_id}_clean_wall", True, "CleanWall started"
                )
            else:
                self.signals.service_response_received.emit(
                    f"pool_{pool_id}_clean_wall", False, "CleanWall goal rejected"
                )
        except Exception as exc:
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_clean_wall", False, str(exc)
            )

    def call_pool_clean_floor(self, pool_id: int) -> None:
        client = self._clean_floor_clients.get(pool_id)
        if client is None or not client.wait_for_server(timeout_sec=1.0):
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_clean_floor", False, "CleanFloor action not available"
            )
            return
        future = client.send_goal_async(CleanFloor.Goal())
        future.add_done_callback(partial(self._on_clean_floor_goal_response, pool_id))

    def _on_clean_floor_goal_response(self, pool_id: int, future) -> None:
        try:
            handle = future.result()
            if handle.accepted:
                self.signals.service_response_received.emit(
                    f"pool_{pool_id}_clean_floor", True, "CleanFloor started"
                )
            else:
                self.signals.service_response_received.emit(
                    f"pool_{pool_id}_clean_floor", False, "CleanFloor goal rejected"
                )
        except Exception as exc:
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_clean_floor", False, str(exc)
            )

    # --- Per-Pool Pause/Resume Services (Dashboard → Isaac Sim direct) ---
    def call_pause_floor(self, pool_id: int) -> None:
        client = self._pause_floor_clients.get(pool_id)
        if client is None or not client.service_is_ready():
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_pause_floor", False, "Pause floor service not available"
            )
            return
        future = client.call_async(PauseMotion.Request())
        future.add_done_callback(partial(self._on_pause_floor_response, pool_id))

    def _on_pause_floor_response(self, pool_id: int, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_pause_floor", response.success, response.message
            )
        except Exception as exc:
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_pause_floor", False, str(exc)
            )

    def call_resume_floor(self, pool_id: int) -> None:
        client = self._resume_floor_clients.get(pool_id)
        if client is None or not client.service_is_ready():
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_resume_floor", False, "Resume floor service not available"
            )
            return
        future = client.call_async(ResumeMotion.Request())
        future.add_done_callback(partial(self._on_resume_floor_response, pool_id))

    def _on_resume_floor_response(self, pool_id: int, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_resume_floor", response.success, response.message
            )
        except Exception as exc:
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_resume_floor", False, str(exc)
            )

    def call_pause_wall(self, pool_id: int) -> None:
        client = self._pause_wall_clients.get(pool_id)
        if client is None or not client.service_is_ready():
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_pause_wall", False, "Pause wall service not available"
            )
            return
        future = client.call_async(PauseMotion.Request())
        future.add_done_callback(partial(self._on_pause_wall_response, pool_id))

    def _on_pause_wall_response(self, pool_id: int, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_pause_wall", response.success, response.message
            )
        except Exception as exc:
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_pause_wall", False, str(exc)
            )

    def call_resume_wall(self, pool_id: int) -> None:
        client = self._resume_wall_clients.get(pool_id)
        if client is None or not client.service_is_ready():
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_resume_wall", False, "Resume wall service not available"
            )
            return
        future = client.call_async(ResumeMotion.Request())
        future.add_done_callback(partial(self._on_resume_wall_response, pool_id))

    def _on_resume_wall_response(self, pool_id: int, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_resume_wall", response.success, response.message
            )
        except Exception as exc:
            self.signals.service_response_received.emit(
                f"pool_{pool_id}_resume_wall", False, str(exc)
            )

    def get_pool_status(self, pool_id: int) -> Optional[PoolStatus]:
        return self._pool_status.get(pool_id)

    def get_robot_status(self, pool_id: int) -> Optional[RobotStatus]:
        return self._robot_status.get(pool_id)

    def get_motion_status(self, pool_id: int) -> Dict[str, Optional[MotionStatus]]:
        return self._motion_status.get(pool_id, {'clean_floor': None, 'clean_wall': None})


class PoolPanel(QGroupBox):
    """Single-pool panel: status info, controls (CleanWall/CleanFloor), and camera views."""

    # Signals for button clicks
    clean_wall_clicked = pyqtSignal(int)  # pool_id
    clean_floor_clicked = pyqtSignal(int)  # pool_id
    pause_wall_clicked = pyqtSignal(int)  # pool_id
    pause_floor_clicked = pyqtSignal(int)  # pool_id
    resume_wall_clicked = pyqtSignal(int)  # pool_id
    resume_floor_clicked = pyqtSignal(int)  # pool_id

    def __init__(self, pool_id: int, parent=None):
        super().__init__(parent)
        self.pool_id = pool_id
        
        # Motion states
        self._wall_state = MotionStatus.IDLE
        self._floor_state = MotionStatus.IDLE
        
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        outer.setContentsMargins(16, 16, 16, 16)

        # Row 1: Pool Status + Control buttons
        top_row = QHBoxLayout()
        top_row.setSpacing(30)

        # Left: Pool Status info
        status_col = QVBoxLayout()
        status_col.setSpacing(6)

        self.fish_type_label = QLabel("Fish type: —")
        self.fish_count_label = QLabel("Fish count: —")
        self.fish_suspicious_label = QLabel("Suspicious fish: —")

        for label in [self.fish_type_label, self.fish_count_label, self.fish_suspicious_label]:
            label.setStyleSheet("font-size: 18px;")
            status_col.addWidget(label)

        status_col.addStretch()
        top_row.addLayout(status_col)
        top_row.addStretch()

        # Right: Control section - Two buttons (CleanWall, CleanFloor)
        control_col = QVBoxLayout()
        control_col.setSpacing(10)
        control_col.setAlignment(Qt.AlignTop)

        control_label = QLabel("Manual Control (Debug)")
        control_label.setStyleSheet("font-size: 16px; color: #888; font-weight: bold;")
        control_col.addWidget(control_label)

        # CleanWall button (dynamic: Start / Pause / Resume)
        self.clean_wall_btn = QPushButton("Clean Wall")
        self.clean_wall_btn.setFixedSize(150, 45)
        self.clean_wall_btn.clicked.connect(self._on_wall_btn_clicked)
        control_col.addWidget(self.clean_wall_btn)

        # CleanFloor button (dynamic: Start / Pause / Resume)
        self.clean_floor_btn = QPushButton("Clean Floor")
        self.clean_floor_btn.setFixedSize(150, 45)
        self.clean_floor_btn.clicked.connect(self._on_floor_btn_clicked)
        control_col.addWidget(self.clean_floor_btn)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 14px;")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumWidth(180)
        control_col.addWidget(self.status_label)

        top_row.addLayout(control_col)
        outer.addLayout(top_row)

        # Row 2: Cameras side by side
        cam_row = QHBoxLayout()
        cam_row.setSpacing(20)

        # Left camera
        left_cam = QVBoxLayout()
        left_cam.setSpacing(6)

        top_cam_title = QLabel("Top Camera Detection")
        top_cam_title.setAlignment(Qt.AlignCenter)
        top_cam_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_cam.addWidget(top_cam_title)

        self.top_cam_view = QLabel("Loading...")
        self.top_cam_view.setAlignment(Qt.AlignCenter)
        self.top_cam_view.setMinimumSize(400, 300)
        self.top_cam_view.setStyleSheet(
            "background-color: #2a2a2a; color: #888; font-size: 16px; border: 1px solid #444; border-radius: 4px;"
        )
        self.top_cam_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_cam.addWidget(self.top_cam_view, 1)

        # Right camera
        right_cam = QVBoxLayout()
        right_cam.setSpacing(6)

        under_cam_title = QLabel("Under Camera")
        under_cam_title.setAlignment(Qt.AlignCenter)
        under_cam_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_cam.addWidget(under_cam_title)

        self.under_cam_view = QLabel("Loading...")
        self.under_cam_view.setAlignment(Qt.AlignCenter)
        self.under_cam_view.setMinimumSize(400, 300)
        self.under_cam_view.setStyleSheet(
            "background-color: #2a2a2a; color: #888; font-size: 16px; border: 1px solid #444; border-radius: 4px;"
        )
        self.under_cam_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_cam.addWidget(self.under_cam_view, 1)

        cam_row.addLayout(left_cam, 1)
        cam_row.addLayout(right_cam, 1)
        outer.addLayout(cam_row, 1)

        self._apply_button_styles()

    def _apply_button_styles(self):
        """Apply button styles based on current states (IDLE, RUNNING, PAUSED)."""
        # CleanWall button style
        if self._wall_state == MotionStatus.RUNNING:
            self.clean_wall_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: black;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #e0a800; }
            """)
            self.clean_wall_btn.setText("Pause Wall")
        elif self._wall_state == MotionStatus.PAUSED:
            self.clean_wall_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17a2b8;
                    color: white;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #138496; }
            """)
            self.clean_wall_btn.setText("Resume Wall")
        else:
            self.clean_wall_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #0056b3; }
                QPushButton:disabled { background-color: #555; color: #888; }
            """)
            self.clean_wall_btn.setText("Clean Wall")

        # CleanFloor button style
        if self._floor_state == MotionStatus.RUNNING:
            self.clean_floor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    color: black;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #e0a800; }
            """)
            self.clean_floor_btn.setText("Pause Floor")
        elif self._floor_state == MotionStatus.PAUSED:
            self.clean_floor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17a2b8;
                    color: white;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #138496; }
            """)
            self.clean_floor_btn.setText("Resume Floor")
        else:
            self.clean_floor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #34c759; }
                QPushButton:disabled { background-color: #555; color: #888; }
            """)
            self.clean_floor_btn.setText("Clean Floor")

    def _on_wall_btn_clicked(self):
        """Handle wall button click - Start/Pause/Resume based on state."""
        if self._wall_state == MotionStatus.RUNNING:
            self.pause_wall_clicked.emit(self.pool_id)
        elif self._wall_state == MotionStatus.PAUSED:
            self.resume_wall_clicked.emit(self.pool_id)
        else:
            self.clean_wall_clicked.emit(self.pool_id)

    def _on_floor_btn_clicked(self):
        """Handle floor button click - Start/Pause/Resume based on state."""
        if self._floor_state == MotionStatus.RUNNING:
            self.pause_floor_clicked.emit(self.pool_id)
        elif self._floor_state == MotionStatus.PAUSED:
            self.resume_floor_clicked.emit(self.pool_id)
        else:
            self.clean_floor_clicked.emit(self.pool_id)

    def set_pool(self, pool_id: int):
        self.pool_id = pool_id
        self._wall_state = MotionStatus.IDLE
        self._floor_state = MotionStatus.IDLE
        self.clear_data()

    def clear_data(self):
        self.fish_type_label.setText("Fish type: —")
        self.fish_count_label.setText("Fish count: —")
        self.fish_suspicious_label.setText("Suspicious fish: —")
        self.top_cam_view.setPixmap(QPixmap())
        self.top_cam_view.setText("Loading...")
        self.under_cam_view.setPixmap(QPixmap())
        self.under_cam_view.setText("Loading...")
        self.status_label.setText("")
        self._wall_state = MotionStatus.IDLE
        self._floor_state = MotionStatus.IDLE
        self._apply_button_styles()

    def update_pool_status(self, msg: PoolStatus):
        self.fish_type_label.setText(f"Fish type: {msg.fish_type}")
        self.fish_count_label.setText(f"Fish count: {msg.fish_count}")
        self.fish_suspicious_label.setText(f"Suspicious fish: {msg.fish_count_suspicious}")

    def update_robot_status(self, msg: RobotStatus):
        pass

    def update_motion_status(self, motion_type: str, msg: MotionStatus):
        """Update motion status and button states."""
        if motion_type == 'clean_wall':
            self._wall_state = msg.state
        elif motion_type == 'clean_floor':
            self._floor_state = msg.state
        self._apply_button_styles()

    def set_buttons_enabled(self, enabled: bool):
        """Enable/disable both CleanWall and CleanFloor buttons."""
        self.clean_wall_btn.setEnabled(enabled)
        self.clean_floor_btn.setEnabled(enabled)
        if not enabled:
            disabled_style = """
                QPushButton {
                    background-color: #3a3a3a;
                    color: #666;
                    border: 2px dashed #555;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 6px;
                }
            """
            self.clean_wall_btn.setStyleSheet(disabled_style)
            self.clean_wall_btn.setText("Clean Wall (Locked)")
            self.clean_floor_btn.setStyleSheet(disabled_style)
            self.clean_floor_btn.setText("Clean Floor (Locked)")
        else:
            self.clean_wall_btn.setText("Clean Wall")
            self.clean_floor_btn.setText("Clean Floor")
            self._apply_button_styles()

    def update_button_enable_state(self):
        """Wall/Floor 버튼은 항상 활성화 (Start/Pause/Resume 모두 가능)."""
        self.clean_wall_btn.setEnabled(True)
        self.clean_floor_btn.setEnabled(True)

    @property
    def is_any_running(self) -> bool:
        """RUNNING 또는 PAUSED 상태이면 청소가 진행 중으로 판단."""
        return self._wall_state in (MotionStatus.RUNNING, MotionStatus.PAUSED) or \
               self._floor_state in (MotionStatus.RUNNING, MotionStatus.PAUSED)

    def reset_motion_states(self):
        """Force reset motion states to IDLE (called after STOP ALL)."""
        self._wall_state = MotionStatus.IDLE
        self._floor_state = MotionStatus.IDLE
        self._apply_button_styles()

    def update_top_cam_image(self, msg: Image):
        self._set_image(self.top_cam_view, msg)

    def update_under_cam_image(self, msg: Image):
        self._set_image(self.under_cam_view, msg)

    def _set_image(self, view: QLabel, msg: Image):
        pixmap = self._ros_image_to_pixmap(msg)
        if pixmap:
            scaled = pixmap.scaled(view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            view.setPixmap(scaled)
        else:
            view.setText(f"[{msg.width}x{msg.height}]")

    def _ros_image_to_pixmap(self, msg: Image) -> Optional[QPixmap]:
        try:
            if msg.encoding in ("rgb8", "bgr8"):
                height, width = msg.height, msg.width
                data = np.frombuffer(msg.data, dtype=np.uint8).reshape((height, width, 3))
                if msg.encoding == "bgr8":
                    data = data[:, :, ::-1].copy()
                qimg = QImage(data.data, width, height, 3 * width, QImage.Format_RGB888)
                return QPixmap.fromImage(qimg)
            elif msg.encoding == "mono8":
                height, width = msg.height, msg.width
                data = np.frombuffer(msg.data, dtype=np.uint8).reshape((height, width))
                qimg = QImage(data.data, width, height, width, QImage.Format_Grayscale8)
                return QPixmap.fromImage(qimg)
        except Exception:
            pass
        return None

    def set_status(self, message: str, color: str = "#888"):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 14px;")


class DashboardWindow(QMainWindow):
    """Main window: header (title + global controls), pool selector, single panel."""

    def __init__(self, ros_node: DashboardRosNode):
        super().__init__()
        self.ros_node = ros_node
        self.active_pool_id: int = next(iter(pool_ids()))

        # State: planner mode or individual mode
        self._planner_active = False
        self._individual_active = False

        self.setWindowTitle("AquaSweep Dashboard")
        self.setMinimumSize(1200, 900)
        self._setup_ui()
        self._connect_signals()

        self.ros_node.set_active_pool(self.active_pool_id)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_connection_status)
        self.status_timer.start(2000)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QHBoxLayout()

        title = QLabel("AquaSweep Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00bfff;")
        header.addWidget(title)

        header.addStretch()

        # AUTO START button
        self.auto_start_btn = QPushButton("AUTO START")
        self.auto_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #34c759; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """)
        self.auto_start_btn.clicked.connect(self._on_auto_start_clicked)
        header.addWidget(self.auto_start_btn)

        # STOP ALL button (initially hidden)
        self.stop_all_btn = QPushButton("STOP ALL")
        self.stop_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #c82333; }
        """)
        self.stop_all_btn.clicked.connect(self._on_stop_all_clicked)
        self.stop_all_btn.hide()
        header.addWidget(self.stop_all_btn)

        main_layout.addLayout(header)

        # Status box
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        status_layout.setSpacing(20)

        self.status_label = QLabel("ROS2: Connecting...")
        self.status_label.setStyleSheet("font-size: 16px; color: #888; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.global_status_label = QLabel("")
        self.global_status_label.setStyleSheet("color: #888; font-size: 16px;")
        status_layout.addWidget(self.global_status_label, 1)

        main_layout.addWidget(status_frame)

        # Pool tab buttons
        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)

        self.pool_tabs: Dict[int, QPushButton] = {}

        for pid in pool_ids():
            tab_btn = QPushButton(f"Pool {pid}")
            tab_btn.setCheckable(True)
            tab_btn.setProperty("pool_id", pid)
            tab_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #888;
                    border: 1px solid #444;
                    border-bottom: none;
                    padding: 10px 20px;
                    font-size: 16px;
                    font-weight: bold;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }
                QPushButton:hover { background-color: #3a3a3a; color: #e0e0e0; }
                QPushButton:checked {
                    background-color: #2d2d2d;
                    color: #00bfff;
                    border-bottom: 2px solid #00bfff;
                }
            """)
            tab_btn.clicked.connect(partial(self._on_pool_tab_clicked, pid))
            self.pool_tabs[pid] = tab_btn
            tab_row.addWidget(tab_btn)

        self.pool_tabs[self.active_pool_id].setChecked(True)
        tab_row.addStretch()
        main_layout.addLayout(tab_row)

        # Pool panel
        self.pool_panel = PoolPanel(self.active_pool_id)
        self.pool_panel.clean_wall_clicked.connect(self._on_clean_wall_clicked)
        self.pool_panel.clean_floor_clicked.connect(self._on_clean_floor_clicked)
        self.pool_panel.pause_wall_clicked.connect(self._on_pause_wall_clicked)
        self.pool_panel.pause_floor_clicked.connect(self._on_pause_floor_clicked)
        self.pool_panel.resume_wall_clicked.connect(self._on_resume_wall_clicked)
        self.pool_panel.resume_floor_clicked.connect(self._on_resume_floor_clicked)
        main_layout.addWidget(self.pool_panel, 1)

        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { color: #e0e0e0; }
            QGroupBox {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 8px;
                padding: 16px;
                padding-top: 24px;
            }
            QGroupBox::title {
                subcontrol-origin: padding;
                subcontrol-position: top left;
                left: 16px;
                top: 4px;
                padding: 0 8px;
                color: #00bfff;
                font-weight: bold;
                font-size: 18px;
            }
        """)

    def _connect_signals(self):
        self.ros_node.signals.pool_status_received.connect(self._on_pool_status)
        self.ros_node.signals.robot_status_received.connect(self._on_robot_status)
        self.ros_node.signals.motion_status_received.connect(self._on_motion_status)
        self.ros_node.signals.top_cam_received.connect(self._on_top_cam)
        self.ros_node.signals.under_cam_received.connect(self._on_under_cam)
        self.ros_node.signals.service_response_received.connect(self._on_service_response)

    def _on_pool_tab_clicked(self, pool_id: int):
        if pool_id == self.active_pool_id:
            return
        
        # Update tab checked states
        for pid, btn in self.pool_tabs.items():
            btn.setChecked(pid == pool_id)
        
        self.active_pool_id = pool_id
        self.pool_panel.set_pool(self.active_pool_id)
        self.ros_node.set_active_pool(self.active_pool_id)

        # Load cached status
        cached_pool = self.ros_node.get_pool_status(self.active_pool_id)
        if cached_pool is not None:
            self.pool_panel.update_pool_status(cached_pool)
        cached_robot = self.ros_node.get_robot_status(self.active_pool_id)
        if cached_robot is not None:
            self.pool_panel.update_robot_status(cached_robot)
        cached_motion = self.ros_node.get_motion_status(self.active_pool_id)
        for motion_type, msg in cached_motion.items():
            if msg is not None:
                self.pool_panel.update_motion_status(motion_type, msg)

        # Update button states based on current mode
        self._update_ui_state()

    def _on_pool_status(self, pool_id: int, msg: PoolStatus):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_pool_status(msg)

    def _on_robot_status(self, pool_id: int, msg: RobotStatus):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_robot_status(msg)

    def _on_motion_status(self, pool_id: int, motion_type: str, msg: MotionStatus):
        # RUNNING 또는 PAUSED 상태이면 individual 모드 활성
        if msg.state in (MotionStatus.RUNNING, MotionStatus.PAUSED) and not self._planner_active:
            self._individual_active = True
            self._update_ui_state()

        if pool_id == self.active_pool_id:
            self.pool_panel.update_motion_status(motion_type, msg)
            if self._individual_active and not self._planner_active:
                self.pool_panel.update_button_enable_state()

        # Check if any pool has finished
        if msg.state == MotionStatus.DONE or msg.state == MotionStatus.IDLE:
            self._check_all_idle()

    def _check_all_idle(self):
        """Check if all pools are idle and reset state if so."""
        all_idle = True
        for pid in pool_ids():
            statuses = self.ros_node.get_motion_status(pid)
            for status in statuses.values():
                # RUNNING 또는 PAUSED이면 아직 진행 중
                if status is not None and status.state in (MotionStatus.RUNNING, MotionStatus.PAUSED):
                    all_idle = False
                    break
            if not all_idle:
                break

        if all_idle:
            if self._planner_active or self._individual_active:
                self._planner_active = False
                self._individual_active = False
                self._update_ui_state()
                self.global_status_label.setText("All tasks completed")
                self.global_status_label.setStyleSheet("color: #28a745; font-size: 16px;")

    def _on_top_cam(self, pool_id: int, msg: Image):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_top_cam_image(msg)

    def _on_under_cam(self, pool_id: int, msg: Image):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_under_cam_image(msg)

    def _on_service_response(self, service_name: str, success: bool, message: str):
        if service_name == "global_start":
            # Restore button
            self.auto_start_btn.setText("AUTO START")
            self.auto_start_btn.setEnabled(True)
            
            if success:
                self.global_status_label.setText(f"AUTO START: {message}")
                self.global_status_label.setStyleSheet("color: #28a745; font-size: 16px;")
                # SUCCESS: set planner active
                self._planner_active = True
                self._individual_active = False
            else:
                self.global_status_label.setText(f"Error: {message}")
                self.global_status_label.setStyleSheet("color: #ff6b6b; font-size: 16px;")
                # FAILED: restore to idle
                self._planner_active = False
                self._individual_active = False
            self._update_ui_state()

        elif service_name == "global_stop":
            # Restore button
            self.stop_all_btn.setText("STOP ALL")
            self.stop_all_btn.setEnabled(True)
            
            if success:
                self.global_status_label.setText(f"STOPPED: {message}")
                self.global_status_label.setStyleSheet("color: #ffc107; font-size: 16px;")
            else:
                self.global_status_label.setText(f"Stop error: {message}")
                self.global_status_label.setStyleSheet("color: #ff6b6b; font-size: 16px;")
            
            # Planner mode 해제 - 실제 motion 상태는 Isaac Sim status에 의해 결정됨
            # (reset_motion_states 호출 제거 - 비동기 stop 완료 전에 강제 리셋하면 상태 불일치)
            self._planner_active = False
            # individual_active는 motion status가 IDLE이 되면 _check_all_idle에서 자동 해제
            self._update_ui_state()

        elif service_name.startswith("pool_"):
            # Parse: pool_{id}_clean_wall or pool_{id}_clean_floor
            parts = service_name.split("_")
            if len(parts) >= 4:
                try:
                    pool_id = int(parts[1])
                    action = "_".join(parts[2:])  # clean_wall or clean_floor
                    
                    # Restore button text
                    if "clean_wall" in action:
                        self.pool_panel.clean_wall_btn.setText("Clean Wall")
                    else:
                        self.pool_panel.clean_floor_btn.setText("Clean Floor")
                    
                    if pool_id == self.active_pool_id:
                        if success:
                            self.pool_panel.set_status(f"{action}: {message}", "#28a745")
                            self._individual_active = True
                        else:
                            self.pool_panel.set_status(f"Error: {message}", "#ff6b6b")
                        self._update_ui_state()
                except ValueError:
                    pass

    def _update_ui_state(self):
        """Update UI based on current state.
        
        상태 관리:
        - _planner_active: AUTO START로 시작된 전체 청소 (STOP ALL 표시)
        - _individual_active: 개별 버튼으로 시작된 청소 (AUTO START 유지, 비활성화)
        """
        if self._planner_active:
            # Planner mode (AUTO START): show STOP ALL, disable pool buttons
            self.auto_start_btn.hide()
            self.stop_all_btn.show()
            self.stop_all_btn.setEnabled(True)
            self.stop_all_btn.setText("STOP ALL")
            self.pool_panel.set_buttons_enabled(False)
        elif self._individual_active:
            # Individual mode: keep AUTO START visible but disabled
            self.auto_start_btn.show()
            self.auto_start_btn.setEnabled(False)
            self.auto_start_btn.setText("AUTO START")
            self.stop_all_btn.hide()
            # Update button states based on running status
            self.pool_panel.update_button_enable_state()
        else:
            # Idle state: show AUTO START, enable all
            self.auto_start_btn.show()
            self.auto_start_btn.setEnabled(True)
            self.auto_start_btn.setText("AUTO START")
            self.stop_all_btn.hide()
            self.pool_panel.set_buttons_enabled(True)

    def _on_auto_start_clicked(self):
        # PENDING state: disable button, show loading text
        self.auto_start_btn.setEnabled(False)
        self.auto_start_btn.setText("Starting...")
        self.pool_panel.set_buttons_enabled(False)
        
        self.global_status_label.setText("Starting all pools...")
        self.global_status_label.setStyleSheet("color: #888; font-size: 16px;")
        self.ros_node.call_global_start()

    def _on_stop_all_clicked(self):
        # PENDING state: disable button, show loading text
        self.stop_all_btn.setEnabled(False)
        self.stop_all_btn.setText("Stopping...")
        
        self.global_status_label.setText("Stopping all...")
        self.global_status_label.setStyleSheet("color: #888; font-size: 16px;")
        self.ros_node.call_global_stop()

    def _on_clean_wall_clicked(self, pool_id: int):
        if self._planner_active:
            return

        self.pool_panel.clean_wall_btn.setEnabled(False)
        self.pool_panel.clean_wall_btn.setText("Starting...")
        self.pool_panel.set_status("Starting CleanWall...", "#888")
        self.ros_node.call_pool_clean_wall(pool_id)

    def _on_clean_floor_clicked(self, pool_id: int):
        if self._planner_active:
            return

        self.pool_panel.clean_floor_btn.setEnabled(False)
        self.pool_panel.clean_floor_btn.setText("Starting...")
        self.pool_panel.set_status("Starting CleanFloor...", "#888")
        self.ros_node.call_pool_clean_floor(pool_id)

    def _on_pause_wall_clicked(self, pool_id: int):
        self.pool_panel.clean_wall_btn.setEnabled(False)
        self.pool_panel.clean_wall_btn.setText("Pausing...")
        self.pool_panel.set_status("Pausing CleanWall...", "#888")
        self.ros_node.call_pause_wall(pool_id)

    def _on_pause_floor_clicked(self, pool_id: int):
        self.pool_panel.clean_floor_btn.setEnabled(False)
        self.pool_panel.clean_floor_btn.setText("Pausing...")
        self.pool_panel.set_status("Pausing CleanFloor...", "#888")
        self.ros_node.call_pause_floor(pool_id)

    def _on_resume_wall_clicked(self, pool_id: int):
        self.pool_panel.clean_wall_btn.setEnabled(False)
        self.pool_panel.clean_wall_btn.setText("Resuming...")
        self.pool_panel.set_status("Resuming CleanWall...", "#888")
        self.ros_node.call_resume_wall(pool_id)

    def _on_resume_floor_clicked(self, pool_id: int):
        self.pool_panel.clean_floor_btn.setEnabled(False)
        self.pool_panel.clean_floor_btn.setText("Resuming...")
        self.pool_panel.set_status("Resuming CleanFloor...", "#888")
        self.ros_node.call_resume_floor(pool_id)

    def _update_connection_status(self):
        if rclpy.ok():
            self.status_label.setText("ROS2: Connected")
            self.status_label.setStyleSheet("font-size: 16px; color: #28a745; padding: 6px;")
        else:
            self.status_label.setText("ROS2: Disconnected")
            self.status_label.setStyleSheet("font-size: 16px; color: #ff6b6b; padding: 6px;")


def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    signal_emitter = SignalEmitter()
    ros_node = DashboardRosNode(signal_emitter)
    ros_thread = RosSpinThread(ros_node)
    ros_thread.start()

    window = DashboardWindow(ros_node)
    window.show()

    exit_code = app.exec_()

    ros_thread.stop()
    ros_node.destroy_node()
    rclpy.shutdown()

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
