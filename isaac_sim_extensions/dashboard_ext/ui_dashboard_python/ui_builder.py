# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import omni.kit.app
import omni.ui as ui
from isaacsim.gui.components.element_wrappers import Button, CollapsableFrame, TextBlock
from isaacsim.gui.components.ui_utils import get_style

from .ros_bridge import ROBOT_STATE_NAMES, RosBridge
from .ros_config import TANK_COUNT, tank_ids


class UIBuilder:
    _REFRESH_EVERY_N_UPDATES = 12

    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._ros_bridge = RosBridge()
        self._update_sub = None
        self._update_counter = 0
        self._connection_field = None
        self._tank_widgets = {}

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
        self._tank_widgets.clear()

    def build_ui(self):
        self.frames = []
        self._tank_widgets = {}
        self._create_connection_frame()
        self._create_tank_grid()
        self.start_ros()
        self._start_ui_refresh()

    def _create_connection_frame(self):
        frame = CollapsableFrame("ROS2", collapsed=False)
        self.frames.append(frame)
        with frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._connection_field = TextBlock(
                    "Connection",
                    num_lines=2,
                    tooltip="ROS2 bridge status",
                    include_copy_button=False,
                )

    def _create_tank_grid(self):
        tank_list = list(tank_ids())
        for row_start in range(0, TANK_COUNT, 2):
            with ui.HStack(style=get_style(), spacing=8, height=0):
                for tank_id in tank_list[row_start : row_start + 2]:
                    self._create_tank_panel(tank_id)

    def _create_tank_panel(self, tank_id: int):
        frame = CollapsableFrame(f"Tank {tank_id}", collapsed=True)
        self.frames.append(frame)

        widgets = {
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
                widgets["pollution"] = self._labeled_line("Pollution")
                widgets["fish_type"] = self._labeled_line("Fish type")
                widgets["fish_count"] = self._labeled_line("Fish count")
                widgets["fish_suspicious"] = self._labeled_line("Suspicious fish")
                widgets["robot_state"] = self._labeled_line("Robot state")
                widgets["battery"] = self._labeled_line("Battery")
                widgets["collision"] = self._labeled_line("Collision")
                widgets["clean_progress"] = self._labeled_line("Clean progress")

                start_btn = Button(
                    "Start",
                    "START",
                    tooltip=f"Send CleanFloor goal for tank {tank_id}",
                    on_click_fn=lambda tid=tank_id: self._on_start_clicked(tid),
                )
                self.wrapped_ui_elements.append(start_btn)
                widgets["start_button"] = start_btn

                widgets["error"] = TextBlock(
                    "Error",
                    num_lines=2,
                    tooltip="Last ROS/action error for this tank",
                    include_copy_button=False,
                )

        self._tank_widgets[tank_id] = widgets

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
        self._refresh_all_tanks()

    def _refresh_all_tanks(self):
        for tank_id in tank_ids():
            self._refresh_tank(tank_id)

    def _refresh_tank(self, tank_id: int):
        widgets = self._tank_widgets.get(tank_id)
        if widgets is None:
            return

        snap = self._ros_bridge.get_snapshot(tank_id)

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

    def _on_start_clicked(self, tank_id: int):
        err = self._ros_bridge.send_clean_floor(tank_id)
        widgets = self._tank_widgets.get(tank_id)
        if widgets is not None and err:
            widgets["error"].set_text(err)
        self._refresh_tank(tank_id)

    def _set_connection_text(self, text: str):
        if self._connection_field is not None:
            self._connection_field.set_text(text)
