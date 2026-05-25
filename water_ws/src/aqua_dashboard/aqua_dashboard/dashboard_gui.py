#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""PyQt5 GUI dashboard for AquaSweep - external process to avoid Isaac Sim rclpy conflicts.

This standalone application provides a graphical interface for monitoring pool and robot
status, viewing camera feeds, and controlling cleaning operations via ROS2 services.

Usage:
    ros2 run aqua_dashboard dashboard_gui
"""

import sys
from functools import partial
from typing import Dict, Optional

import numpy as np
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from aqua_interfaces.msg import PoolStatus, RobotStatus

from .ros_topics import (
    POOL_COUNT,
    planner_pause_service,
    planner_start_service,
    pool_ids,
    pool_robot_status_topic,
    pool_start_clean_floor_service,
    pool_status_topic,
    pool_top_cam_det_topic,
    pool_under_cam_det_topic,
)

ROBOT_STATE_NAMES = {
    RobotStatus.IDLE: "IDLE",
    RobotStatus.RUNNING: "RUNNING",
    RobotStatus.PAUSED: "PAUSED",
    RobotStatus.DISCHARGED: "DISCHARGED",
}


class SignalEmitter(QObject):
    """Qt signal emitter for ROS2 node callbacks.

    Since rclpy.node.Node cannot inherit from QObject, we use a separate
    emitter class to bridge ROS2 callbacks to Qt signals.
    """
    pool_status_received = pyqtSignal(int, object)
    robot_status_received = pyqtSignal(int, object)
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
        self._pool_start_clients: Dict[int, object] = {}

        for pool_id in pool_ids():
            self._pool_status[pool_id] = None
            self._robot_status[pool_id] = None

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
            self.create_subscription(
                Image,
                pool_top_cam_det_topic(pool_id),
                partial(self._on_top_cam_image, pool_id),
                10
            )
            self.create_subscription(
                Image,
                pool_under_cam_det_topic(pool_id),
                partial(self._on_under_cam_image, pool_id),
                10
            )

            self._pool_start_clients[pool_id] = self.create_client(
                Trigger,
                pool_start_clean_floor_service(pool_id)
            )

        self._planner_start_client = self.create_client(
            Trigger,
            planner_start_service()
        )
        self._planner_pause_client = self.create_client(
            Trigger,
            planner_pause_service()
        )

        self.get_logger().info(
            f'DashboardRosNode (GUI) ready | pools={list(pool_ids())}'
        )

    def _on_pool_status(self, pool_id: int, msg: PoolStatus) -> None:
        self._pool_status[pool_id] = msg
        self.signals.pool_status_received.emit(pool_id, msg)

    def _on_robot_status(self, pool_id: int, msg: RobotStatus) -> None:
        self._robot_status[pool_id] = msg
        self.signals.robot_status_received.emit(pool_id, msg)

    def _on_top_cam_image(self, pool_id: int, msg: Image) -> None:
        self.signals.top_cam_received.emit(pool_id, msg)

    def _on_under_cam_image(self, pool_id: int, msg: Image) -> None:
        self.signals.under_cam_received.emit(pool_id, msg)

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

    def call_pool_start(self, pool_id: int) -> None:
        client = self._pool_start_clients.get(pool_id)
        if client is None:
            self.signals.service_response_received.emit(f"pool_{pool_id}_start", False, f"No client for pool {pool_id}")
            return

        if not client.service_is_ready():
            self.signals.service_response_received.emit(f"pool_{pool_id}_start", False, f"Pool {pool_id} start service not available")
            return

        request = Trigger.Request()
        future = client.call_async(request)
        future.add_done_callback(partial(self._on_pool_start_response, pool_id))

    def _on_pool_start_response(self, pool_id: int, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit(f"pool_{pool_id}_start", response.success, response.message)
        except Exception as exc:
            self.signals.service_response_received.emit(f"pool_{pool_id}_start", False, str(exc))

    def call_pause(self) -> None:
        if not self._planner_pause_client.service_is_ready():
            self.signals.service_response_received.emit("pause", False, "Planner pause service not available")
            return

        request = Trigger.Request()
        future = self._planner_pause_client.call_async(request)
        future.add_done_callback(self._on_pause_response)

    def _on_pause_response(self, future) -> None:
        try:
            response = future.result()
            self.signals.service_response_received.emit("pause", response.success, response.message)
        except Exception as exc:
            self.signals.service_response_received.emit("pause", False, str(exc))

    def get_pool_status(self, pool_id: int) -> Optional[PoolStatus]:
        return self._pool_status.get(pool_id)

    def get_robot_status(self, pool_id: int) -> Optional[RobotStatus]:
        return self._robot_status.get(pool_id)


class PoolPanel(QGroupBox):
    """Panel widget for displaying a single pool's status and controls."""

    def __init__(self, pool_id: int, parent=None):
        super().__init__(f"Pool {pool_id} + Robot {pool_id}", parent)
        self.pool_id = pool_id
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        top_cam_label = QLabel("Top Camera")
        top_cam_label.setAlignment(Qt.AlignCenter)
        top_cam_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(top_cam_label)

        self.top_cam_view = QLabel("[No Image]")
        self.top_cam_view.setAlignment(Qt.AlignCenter)
        self.top_cam_view.setMinimumSize(500, 500)
        self.top_cam_view.setStyleSheet("background-color: #2a2a2a; color: #888; font-size: 16px;")
        layout.addWidget(self.top_cam_view)

        pool_status_label = QLabel(f"Pool {self.pool_id} Status")
        pool_status_label.setStyleSheet("font-weight: bold; font-size: 18px; margin-top: 12px;")
        layout.addWidget(pool_status_label)

        self.pollution_label = QLabel("Pollution: —")
        self.fish_type_label = QLabel("Fish type: —")
        self.fish_count_label = QLabel("Fish count: —")
        self.fish_suspicious_label = QLabel("Suspicious fish: —")

        for label in [self.pollution_label, self.fish_type_label, self.fish_count_label, self.fish_suspicious_label]:
            label.setStyleSheet("font-size: 16px; padding-left: 12px;")
            layout.addWidget(label)

        robot_status_label = QLabel(f"Robot {self.pool_id} Status")
        robot_status_label.setStyleSheet("font-weight: bold; font-size: 18px; margin-top: 12px;")
        layout.addWidget(robot_status_label)

        self.robot_state_label = QLabel("Robot state: —")
        self.battery_label = QLabel("Battery: —")
        self.collision_label = QLabel("Collision: —")
        self.clean_progress_label = QLabel("Clean progress: —")

        for label in [self.robot_state_label, self.battery_label, self.collision_label, self.clean_progress_label]:
            label.setStyleSheet("font-size: 16px; padding-left: 12px;")
            layout.addWidget(label)

        self.start_button = QPushButton(f"START POOL {self.pool_id}")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5aa0e9;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        layout.addWidget(self.start_button)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addStretch()

    def update_pool_status(self, msg: PoolStatus):
        self.pollution_label.setText(f"Pollution: {msg.pollution_level:.2f}")
        self.fish_type_label.setText(f"Fish type: {msg.fish_type}")
        self.fish_count_label.setText(f"Fish count: {msg.fish_count}")
        self.fish_suspicious_label.setText(f"Suspicious fish: {msg.fish_count_suspicious}")

    def update_robot_status(self, msg: RobotStatus):
        state_name = ROBOT_STATE_NAMES.get(msg.state, str(msg.state))
        self.robot_state_label.setText(f"Robot state: {state_name}")
        self.battery_label.setText(f"Battery: {msg.battery_level:.2f}")
        self.collision_label.setText(f"Collision: {msg.collision_force:.2f}")

        if msg.state == RobotStatus.RUNNING:
            self.clean_progress_label.setText("Clean progress: running")
            self.start_button.setEnabled(False)
        elif msg.state == RobotStatus.IDLE:
            self.clean_progress_label.setText("Clean progress: —")
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)

    def update_top_cam_image(self, msg: Image):
        pixmap = self._ros_image_to_pixmap(msg)
        if pixmap:
            scaled = pixmap.scaled(
                self.top_cam_view.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.top_cam_view.setPixmap(scaled)
        else:
            self.top_cam_view.setText(f"[{msg.width}x{msg.height}]")

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

    def set_error(self, message: str):
        self.error_label.setText(message)


class DashboardWindow(QMainWindow):
    """Main window for the AquaSweep dashboard."""

    def __init__(self, ros_node: DashboardRosNode):
        super().__init__()
        self.ros_node = ros_node
        self.pool_panels: Dict[int, PoolPanel] = {}

        self.setWindowTitle("AquaSweep Dashboard")
        self.setMinimumSize(1200, 900)
        self._setup_ui()
        self._connect_signals()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_connection_status)
        self.status_timer.start(2000)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        header = QHBoxLayout()

        title = QLabel("AquaSweep Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00bfff;")
        header.addWidget(title)

        header.addStretch()

        self.global_start_btn = QPushButton("START ALL")
        self.global_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #34c759;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.global_start_btn.clicked.connect(self._on_global_start_clicked)
        header.addWidget(self.global_start_btn)

        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                border: none;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ffca2c;
            }
        """)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        header.addWidget(self.pause_btn)

        main_layout.addLayout(header)

        self.status_label = QLabel("ROS2: Connecting...")
        self.status_label.setStyleSheet("font-size: 16px; color: #888; padding: 6px;")
        main_layout.addWidget(self.status_label)

        self.global_error_label = QLabel("")
        self.global_error_label.setStyleSheet("color: #ff6b6b; font-size: 16px;")
        main_layout.addWidget(self.global_error_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(20)

        pool_list = list(pool_ids())
        cols = 2
        for idx, pool_id in enumerate(pool_list):
            row = idx // cols
            col = idx % cols
            panel = PoolPanel(pool_id)
            panel.start_button.clicked.connect(partial(self._on_pool_start_clicked, pool_id))
            grid_layout.addWidget(panel, row, col)
            self.pool_panels[pool_id] = panel

        scroll.setWidget(grid_widget)
        main_layout.addWidget(scroll)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                color: #e0e0e0;
            }
            QGroupBox {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 16px;
                padding: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #00bfff;
                font-weight: bold;
                font-size: 18px;
            }
            QScrollArea {
                background-color: transparent;
            }
        """)

    def _connect_signals(self):
        self.ros_node.signals.pool_status_received.connect(self._on_pool_status)
        self.ros_node.signals.robot_status_received.connect(self._on_robot_status)
        self.ros_node.signals.top_cam_received.connect(self._on_top_cam)
        self.ros_node.signals.under_cam_received.connect(self._on_under_cam)
        self.ros_node.signals.service_response_received.connect(self._on_service_response)

    def _on_pool_status(self, pool_id: int, msg: PoolStatus):
        panel = self.pool_panels.get(pool_id)
        if panel:
            panel.update_pool_status(msg)

    def _on_robot_status(self, pool_id: int, msg: RobotStatus):
        panel = self.pool_panels.get(pool_id)
        if panel:
            panel.update_robot_status(msg)

    def _on_top_cam(self, pool_id: int, msg: Image):
        panel = self.pool_panels.get(pool_id)
        if panel:
            panel.update_top_cam_image(msg)

    def _on_under_cam(self, pool_id: int, msg: Image):
        pass

    def _on_service_response(self, service_name: str, success: bool, message: str):
        if service_name == "global_start":
            if success:
                self.global_error_label.setText(f"Started: {message}")
                self.global_error_label.setStyleSheet("color: #28a745; font-size: 16px;")
            else:
                self.global_error_label.setText(f"Error: {message}")
                self.global_error_label.setStyleSheet("color: #ff6b6b; font-size: 16px;")
        elif service_name == "pause":
            if success:
                self.global_error_label.setText(f"Paused: {message}")
                self.global_error_label.setStyleSheet("color: #ffc107; font-size: 16px;")
            else:
                self.global_error_label.setText(f"Pause error: {message}")
                self.global_error_label.setStyleSheet("color: #ff6b6b; font-size: 16px;")
        elif service_name.startswith("pool_"):
            parts = service_name.split("_")
            if len(parts) >= 2:
                try:
                    pool_id = int(parts[1])
                    panel = self.pool_panels.get(pool_id)
                    if panel:
                        if success:
                            panel.set_error(f"Started: {message}")
                        else:
                            panel.set_error(f"Error: {message}")
                except ValueError:
                    pass

    def _on_global_start_clicked(self):
        self.global_error_label.setText("Starting all pools...")
        self.global_error_label.setStyleSheet("color: #888; font-size: 16px;")
        self.ros_node.call_global_start()

    def _on_pause_clicked(self):
        self.global_error_label.setText("Pausing...")
        self.global_error_label.setStyleSheet("color: #888; font-size: 16px;")
        self.ros_node.call_pause()

    def _on_pool_start_clicked(self, pool_id: int):
        panel = self.pool_panels.get(pool_id)
        if panel:
            panel.set_error("Starting...")
        self.ros_node.call_pool_start(pool_id)

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
