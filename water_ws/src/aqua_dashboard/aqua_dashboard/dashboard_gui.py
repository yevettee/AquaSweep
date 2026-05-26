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
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from aqua_interfaces.msg import PoolStatus, RobotStatus

from .ros_topics import (
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
    """ROS2 node for the dashboard with Qt signal integration.

    Status feeds for every pool stay subscribed so cached values are available on
    pool switch. Camera image feeds are tied to a single active pool and are
    rebuilt by set_active_pool().
    """

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

            self._pool_start_clients[pool_id] = self.create_client(
                Trigger,
                pool_start_clean_floor_service(pool_id)
            )

        self._active_pool_id: Optional[int] = None
        self._top_cam_sub = None
        self._under_cam_sub = None

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
    """Single-pool panel: left column status+button, right column stacked cameras.

    The panel can be retargeted to any pool via set_pool().
    """

    def __init__(self, pool_id: int, parent=None):
        super().__init__(parent)
        self.pool_id = pool_id
        self._setup_ui()
        self._retitle()

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setSpacing(20)
        outer.setContentsMargins(16, 24, 16, 16)

        left = QVBoxLayout()
        left.setSpacing(6)

        self.pool_status_title = QLabel("Pool Status")
        self.pool_status_title.setStyleSheet("font-weight: bold; font-size: 18px; margin-top: 4px;")
        left.addWidget(self.pool_status_title)

        self.pollution_label = QLabel("Pollution: —")
        self.fish_type_label = QLabel("Fish type: —")
        self.fish_count_label = QLabel("Fish count: —")
        self.fish_suspicious_label = QLabel("Suspicious fish: —")
        for label in [self.pollution_label, self.fish_type_label, self.fish_count_label, self.fish_suspicious_label]:
            label.setStyleSheet("font-size: 16px; padding-left: 12px;")
            left.addWidget(label)

        self.robot_status_title = QLabel("Robot Status")
        self.robot_status_title.setStyleSheet("font-weight: bold; font-size: 18px; margin-top: 12px;")
        left.addWidget(self.robot_status_title)

        self.robot_state_label = QLabel("Robot state: —")
        self.battery_label = QLabel("Battery: —")
        self.collision_label = QLabel("Collision: —")
        self.clean_progress_label = QLabel("Clean progress: —")
        for label in [self.robot_state_label, self.battery_label, self.collision_label, self.clean_progress_label]:
            label.setStyleSheet("font-size: 16px; padding-left: 12px;")
            left.addWidget(label)

        left.addSpacing(16)
        self.start_button = QPushButton("START POOL")
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
        left.addWidget(self.start_button)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff6b6b; font-size: 14px;")
        self.error_label.setWordWrap(True)
        left.addWidget(self.error_label)

        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(10)

        top_cam_title = QLabel("Top Camera Detection")
        top_cam_title.setAlignment(Qt.AlignCenter)
        top_cam_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        right.addWidget(top_cam_title)

        self.top_cam_view = QLabel("Loading...")
        self.top_cam_view.setAlignment(Qt.AlignCenter)
        self.top_cam_view.setMinimumSize(480, 320)
        self.top_cam_view.setStyleSheet(
            "background-color: #2a2a2a; color: #888; font-size: 16px; border: 1px solid #444; border-radius: 4px;"
        )
        self.top_cam_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right.addWidget(self.top_cam_view, 1)

        under_cam_title = QLabel("Under Camera Detection")
        under_cam_title.setAlignment(Qt.AlignCenter)
        under_cam_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 4px;")
        right.addWidget(under_cam_title)

        self.under_cam_view = QLabel("Loading...")
        self.under_cam_view.setAlignment(Qt.AlignCenter)
        self.under_cam_view.setMinimumSize(480, 320)
        self.under_cam_view.setStyleSheet(
            "background-color: #2a2a2a; color: #888; font-size: 16px; border: 1px solid #444; border-radius: 4px;"
        )
        self.under_cam_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right.addWidget(self.under_cam_view, 1)

        outer.addLayout(left, 1)
        outer.addLayout(right, 2)

    def _retitle(self):
        self.setTitle(f"Pool {self.pool_id} + Robot {self.pool_id}")
        self.pool_status_title.setText(f"Pool {self.pool_id} Status")
        self.robot_status_title.setText(f"Robot {self.pool_id} Status")
        self.start_button.setText(f"START POOL {self.pool_id}")

    def set_pool(self, pool_id: int):
        self.pool_id = pool_id
        self._retitle()
        self.clear_data()

    def clear_data(self):
        self.pollution_label.setText("Pollution: —")
        self.fish_type_label.setText("Fish type: —")
        self.fish_count_label.setText("Fish count: —")
        self.fish_suspicious_label.setText("Suspicious fish: —")
        self.robot_state_label.setText("Robot state: —")
        self.battery_label.setText("Battery: —")
        self.collision_label.setText("Collision: —")
        self.clean_progress_label.setText("Clean progress: —")
        self.top_cam_view.setPixmap(QPixmap())
        self.top_cam_view.setText("Loading...")
        self.under_cam_view.setPixmap(QPixmap())
        self.under_cam_view.setText("Loading...")
        self.error_label.setText("")
        self.start_button.setEnabled(True)

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
        self._set_image(self.top_cam_view, msg)

    def update_under_cam_image(self, msg: Image):
        self._set_image(self.under_cam_view, msg)

    def _set_image(self, view: QLabel, msg: Image):
        pixmap = self._ros_image_to_pixmap(msg)
        if pixmap:
            scaled = pixmap.scaled(
                view.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
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

    def set_error(self, message: str):
        self.error_label.setText(message)


class DashboardWindow(QMainWindow):
    """Main window: header (title + global controls), pool selector, single panel."""

    def __init__(self, ros_node: DashboardRosNode):
        super().__init__()
        self.ros_node = ros_node
        self.active_pool_id: int = next(iter(pool_ids()))

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

        selector_row = QHBoxLayout()
        selector_label = QLabel("Pool:")
        selector_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        selector_row.addWidget(selector_label)

        self.pool_selector = QComboBox()
        for pid in pool_ids():
            self.pool_selector.addItem(f"Pool {pid}", pid)
        self.pool_selector.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 16px;
                min-width: 140px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #4a90d9;
            }
        """)
        self.pool_selector.currentIndexChanged.connect(self._on_pool_selected)
        selector_row.addWidget(self.pool_selector)
        selector_row.addStretch()
        main_layout.addLayout(selector_row)

        self.pool_panel = PoolPanel(self.active_pool_id)
        self.pool_panel.start_button.clicked.connect(self._on_pool_start_clicked)
        main_layout.addWidget(self.pool_panel, 1)

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
        """)

    def _connect_signals(self):
        self.ros_node.signals.pool_status_received.connect(self._on_pool_status)
        self.ros_node.signals.robot_status_received.connect(self._on_robot_status)
        self.ros_node.signals.top_cam_received.connect(self._on_top_cam)
        self.ros_node.signals.under_cam_received.connect(self._on_under_cam)
        self.ros_node.signals.service_response_received.connect(self._on_service_response)

    def _on_pool_selected(self, index: int):
        new_pool_id = self.pool_selector.itemData(index)
        if new_pool_id is None or new_pool_id == self.active_pool_id:
            return
        self.active_pool_id = int(new_pool_id)
        self.pool_panel.set_pool(self.active_pool_id)
        self.ros_node.set_active_pool(self.active_pool_id)

        cached_pool = self.ros_node.get_pool_status(self.active_pool_id)
        if cached_pool is not None:
            self.pool_panel.update_pool_status(cached_pool)
        cached_robot = self.ros_node.get_robot_status(self.active_pool_id)
        if cached_robot is not None:
            self.pool_panel.update_robot_status(cached_robot)

    def _on_pool_status(self, pool_id: int, msg: PoolStatus):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_pool_status(msg)

    def _on_robot_status(self, pool_id: int, msg: RobotStatus):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_robot_status(msg)

    def _on_top_cam(self, pool_id: int, msg: Image):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_top_cam_image(msg)

    def _on_under_cam(self, pool_id: int, msg: Image):
        if pool_id == self.active_pool_id:
            self.pool_panel.update_under_cam_image(msg)

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
                    if pool_id == self.active_pool_id:
                        if success:
                            self.pool_panel.set_error(f"Started: {message}")
                        else:
                            self.pool_panel.set_error(f"Error: {message}")
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

    def _on_pool_start_clicked(self):
        self.pool_panel.set_error("Starting...")
        self.ros_node.call_pool_start(self.active_pool_id)

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
