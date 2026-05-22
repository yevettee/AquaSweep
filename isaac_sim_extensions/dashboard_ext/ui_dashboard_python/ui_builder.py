# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import omni.kit.app
import omni.ui as ui
from isaacsim.gui.components.element_wrappers import Button, CollapsableFrame, TextBlock
from isaacsim.gui.components.ui_utils import get_style

from .ros_bridge import ROBOT_STATE_NAMES, RosBridge
from .ros_config import POOL_COUNT, pool_ids


class UIBuilder:
    _REFRESH_EVERY_N_UPDATES = 12

    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._ros_bridge = RosBridge()
        self._update_sub = None
        self._update_counter = 0
        self._connection_field = None
        self._global_start_button = None
        self._global_error_field = None
        self._pool_widgets = {}

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        pass

    def on_physics_step(self, step):
        pass

    def on_stage_event(self, event):
        pass

    def start_ros(self):
        if self._ros_bridge.start():
            self._set_connection_text("ROS2 connected")
        else:
            reason = self._ros_bridge.unavailable_reason or "ROS2 unavailable"
            self._set_connection_text(reason)

    def stop_ros(self):
        self._ros_bridge.stop()
        self._stop_ui_refresh()

    def cleanup(self):
        self.stop_ros()
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()
        self.wrapped_ui_elements.clear()
        self._pool_widgets.clear()

    def build_ui(self):
        self.frames = []
        self._pool_widgets = {}
        self._create_header()
        self._create_connection_frame()
        self._create_pool_grid()
        self.start_ros()
        self._start_ui_refresh()

    def _create_header(self):
        """Create header with AquaSweep title and global start button."""
        with ui.HStack(style=get_style(), spacing=10, height=50):
            ui.Label(
                "AquaSweep",
                style={"font_size": 24, "color": 0xFF00BFFF},
                width=ui.Fraction(1),
            )
            with ui.VStack(width=120):
                ui.Spacer(height=5)
                self._global_start_button = Button(
                    "Global Start",
                    "START ALL",
                    tooltip="Start cleaning for all eligible pools (fish_count == 0)",
                    on_click_fn=self._on_global_start_clicked,
                )
                self.wrapped_ui_elements.append(self._global_start_button)

        self._global_error_field = TextBlock(
            "Status",
            num_lines=1,
            tooltip="Global operation status",
            include_copy_button=False,
        )
        self._global_error_field.set_text("")

    def _create_connection_frame(self):
        frame = CollapsableFrame("ROS2 Connection", collapsed=True)
        self.frames.append(frame)
        with frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._connection_field = TextBlock(
                    "Connection",
                    num_lines=2,
                    tooltip="ROS2 bridge status",
                    include_copy_button=False,
                )

    def _create_pool_grid(self):
        """Create 2x2 grid of pool panels."""
        pool_list = list(pool_ids())
        for row_start in range(0, POOL_COUNT, 2):
            with ui.HStack(style=get_style(), spacing=8, height=0):
                for pool_id in pool_list[row_start : row_start + 2]:
                    self._create_pool_panel(pool_id)

    def _create_pool_panel(self, pool_id: int):
        """Create a panel for a single pool with camera views and status."""
        frame = CollapsableFrame(f"Pool {pool_id} + Robot {pool_id}", collapsed=False)
        self.frames.append(frame)

        widgets = {
            "top_cam_label": None,
            "under_cam_label": None,
            "pollution": None,
            "fish_type": None,
            "fish_count": None,
            "fish_suspicious": None,
            "robot_state": None,
            "battery": None,
            "collision": None,
            "clean_progress": None,
            "error": None,
            "start_button": None,
        }

        with frame:
            with ui.VStack(style=get_style(), spacing=4, height=0):
                with ui.HStack(spacing=8, height=80):
                    with ui.VStack(width=ui.Fraction(1)):
                        ui.Label("Top Camera Detection", style={"font_size": 12})
                        widgets["top_cam_label"] = ui.Label(
                            "[No Image]",
                            style={"font_size": 10, "color": 0xFF888888},
                            alignment=ui.Alignment.CENTER,
                        )

                    with ui.VStack(width=ui.Fraction(1)):
                        ui.Label("Under Camera Detection", style={"font_size": 12})
                        widgets["under_cam_label"] = ui.Label(
                            "[No Image]",
                            style={"font_size": 10, "color": 0xFF888888},
                            alignment=ui.Alignment.CENTER,
                        )

                ui.Spacer(height=4)
                ui.Label(f"Pool {pool_id} Status", style={"font_size": 14})
                widgets["pollution"] = self._labeled_line("Pollution")
                widgets["fish_type"] = self._labeled_line("Fish type")
                widgets["fish_count"] = self._labeled_line("Fish count")
                widgets["fish_suspicious"] = self._labeled_line("Suspicious fish")

                ui.Spacer(height=4)
                ui.Label(f"Robot {pool_id} Status", style={"font_size": 14})
                widgets["robot_state"] = self._labeled_line("Robot state")
                widgets["battery"] = self._labeled_line("Battery")
                widgets["collision"] = self._labeled_line("Collision")
                widgets["clean_progress"] = self._labeled_line("Clean progress")

                ui.Spacer(height=4)
                start_btn = Button(
                    f"Start Pool {pool_id}",
                    f"START POOL {pool_id}",
                    tooltip=f"Start floor cleaning for pool {pool_id}",
                    on_click_fn=lambda pid=pool_id: self._on_pool_start_clicked(pid),
                )
                self.wrapped_ui_elements.append(start_btn)
                widgets["start_button"] = start_btn

                widgets["error"] = TextBlock(
                    "Error",
                    num_lines=2,
                    tooltip="Last ROS/action error for this pool",
                    include_copy_button=False,
                )

        self._pool_widgets[pool_id] = widgets

    def _labeled_line(self, label: str) -> TextBlock:
        field = TextBlock(
            label,
            num_lines=1,
            tooltip=label,
            include_copy_button=False,
        )
        field.set_text(f"{label}: —")
        return field

    def _start_ui_refresh(self):
        self._stop_ui_refresh()
        stream = omni.kit.app.get_app().get_update_event_stream()
        self._update_sub = stream.create_subscription_to_pop(self._on_app_update, order=0)

    def _stop_ui_refresh(self):
        self._update_sub = None
        self._update_counter = 0

    def _on_app_update(self, _event):
        self._update_counter += 1
        if self._update_counter % self._REFRESH_EVERY_N_UPDATES != 0:
            return
        self._refresh_all()

    def _refresh_all(self):
        self._update_button_states()
        for pool_id in pool_ids():
            self._refresh_pool(pool_id)

    def _update_button_states(self):
        """Update button enabled/disabled states based on running tasks."""
        global_active = self._ros_bridge.global_task_active
        any_running = self._ros_bridge.any_pool_running()

        if self._global_start_button is not None:
            try:
                self._global_start_button.enabled = not (global_active or any_running)
            except Exception:
                pass

        for pool_id in pool_ids():
            widgets = self._pool_widgets.get(pool_id)
            if widgets is None:
                continue

            snap = self._ros_bridge.get_snapshot(pool_id)
            pool_running = snap.clean_running

            btn = widgets.get("start_button")
            if btn is not None:
                try:
                    btn.enabled = not (global_active or pool_running)
                except Exception:
                    pass

    def _refresh_pool(self, pool_id: int):
        widgets = self._pool_widgets.get(pool_id)
        if widgets is None:
            return

        snap = self._ros_bridge.get_snapshot(pool_id)

        if snap.top_cam_dims[0] > 0:
            widgets["top_cam_label"].text = f"[{snap.top_cam_dims[0]}x{snap.top_cam_dims[1]}]"
        else:
            widgets["top_cam_label"].text = "[No Image]"

        if snap.under_cam_dims[0] > 0:
            widgets["under_cam_label"].text = f"[{snap.under_cam_dims[0]}x{snap.under_cam_dims[1]}]"
        else:
            widgets["under_cam_label"].text = "[No Image]"

        if snap.tank is not None:
            widgets["pollution"].set_text(f"Pollution: {snap.tank.pollution_level:.2f}")
            widgets["fish_type"].set_text(f"Fish type: {snap.tank.fish_type}")
            widgets["fish_count"].set_text(f"Fish count: {snap.tank.fish_count}")
            widgets["fish_suspicious"].set_text(f"Suspicious fish: {snap.tank.fish_count_suspicious}")
        else:
            widgets["pollution"].set_text("Pollution: —")
            widgets["fish_type"].set_text("Fish type: —")
            widgets["fish_count"].set_text("Fish count: —")
            widgets["fish_suspicious"].set_text("Suspicious fish: —")

        if snap.robot is not None:
            state_name = ROBOT_STATE_NAMES.get(snap.robot.state, str(snap.robot.state))
            widgets["robot_state"].set_text(f"Robot state: {state_name}")
            widgets["battery"].set_text(f"Battery: {snap.robot.battery_level:.2f}")
            widgets["collision"].set_text(f"Collision: {snap.robot.collision_force:.2f}")
        else:
            widgets["robot_state"].set_text("Robot state: —")
            widgets["battery"].set_text("Battery: —")
            widgets["collision"].set_text("Collision: —")

        if snap.clean_running:
            prog = snap.clean_progress if snap.clean_progress is not None else 0.0
            widgets["clean_progress"].set_text(f"Clean progress: running ({prog:.0%})")
        elif snap.clean_progress is not None:
            widgets["clean_progress"].set_text(f"Clean progress: {snap.clean_progress:.0%}")
        else:
            widgets["clean_progress"].set_text("Clean progress: —")

        if snap.last_error:
            widgets["error"].set_text(snap.last_error)
        else:
            widgets["error"].set_text("")

    def _on_global_start_clicked(self):
        """Handle global start button click."""
        err = self._ros_bridge.call_global_start()
        if self._global_error_field is not None:
            if err:
                self._global_error_field.set_text(f"Error: {err}")
            else:
                self._global_error_field.set_text("Starting all eligible pools...")
        self._refresh_all()

    def _on_pool_start_clicked(self, pool_id: int):
        """Handle individual pool start button click."""
        err = self._ros_bridge.call_pool_start(pool_id)
        widgets = self._pool_widgets.get(pool_id)
        if widgets is not None and err:
            widgets["error"].set_text(err)
        self._refresh_pool(pool_id)

    def _set_connection_text(self, text: str):
        if self._connection_field is not None:
            self._connection_field.set_text(text)
