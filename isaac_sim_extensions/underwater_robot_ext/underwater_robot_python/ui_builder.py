# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import carb
import numpy as np
import omni.timeline
import omni.ui as ui
from isaacsim.core.api.world import World
from isaacsim.core.utils.stage import get_current_stage
from isaacsim.examples.extension.core_connectors import LoadButton, ResetButton
from isaacsim.gui.components.element_wrappers import CollapsableFrame, StateButton
from isaacsim.gui.components.ui_utils import get_style
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from omni.usd import StageEventType

from .global_variables import (
    DEBUG_CENTER_TRAIL_ENABLED,
    HIPPO_USD_FILENAME,
    HIPPO_WHEEL_BASE_M,
    HIPPO_WHEEL_RADIUS_M,
    ROBOT_PRIM_PATH,
    ROBOT_SCENE_NAME,
    ROBOT_SPAWN_Z_M,
)
from .hippo_physics_sanitize import prepare_hippo_usd_on_stage, tag_aquasweep_attrs
from .actiongraph_setup import create_cmd_vel_subscriber_graph
from .scenario import UnderwaterSpiralScenario
from .suction_system import SuctionSystem
from .trail_debug import reset_center_trail_debug, tick_center_trail_debug

PHYSICS_DT = 1.0 / 60.0


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()
        self._on_init()

    # ── extension.py 자동 콜백 ─────────────────────────────────────────────

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            self._scenario_state_btn.reset()
            self._scenario_state_btn.enabled = False

    def on_physics_step(self, step: float):
        try:
            world = World.instance()
            robot = world.scene.get_object(ROBOT_SCENE_NAME)
        except (AttributeError, KeyError, RuntimeError, ValueError):
            return
        if robot is None:
            return
        if DEBUG_CENTER_TRAIL_ENABLED:
            tick_center_trail_debug(robot)

    def on_stage_event(self, event):
        if event.type == int(StageEventType.OPENED):
            self._reset_extension()

    def cleanup(self):
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()
        reset_center_trail_debug()

    def build_ui(self):
        world_controls_frame = CollapsableFrame("World Controls", collapsed=False)
        with world_controls_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._load_btn = LoadButton(
                    "Load Button", "LOAD",
                    setup_scene_fn=self._setup_scene,
                    setup_post_load_fn=self._setup_scenario,
                )
                self._load_btn.set_world_settings(physics_dt=PHYSICS_DT, rendering_dt=PHYSICS_DT)
                self.wrapped_ui_elements.append(self._load_btn)

                self._reset_btn = ResetButton(
                    "Reset Button", "RESET",
                    pre_reset_fn=self._on_pre_reset_btn,
                    post_reset_fn=self._on_post_reset_btn,
                )
                self._reset_btn.enabled = False
                self.wrapped_ui_elements.append(self._reset_btn)

        run_scenario_frame = CollapsableFrame("청소 제어")
        with run_scenario_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._scenario_state_btn = StateButton(
                    "Run Scenario", "RUN — 나선 청소 시작", "STOP",
                    on_a_click_fn=self._on_run_scenario_a_text,
                    on_b_click_fn=self._on_run_scenario_b_text,
                    physics_callback_fn=self._update_scenario,
                )
                self._scenario_state_btn.enabled = False
                self.wrapped_ui_elements.append(self._scenario_state_btn)

        suction_frame = CollapsableFrame("Suction Status", collapsed=False)
        with suction_frame:
            with ui.VStack(style=get_style(), spacing=4, height=0):
                with ui.HStack(height=22):
                    ui.Label("반경 (m)", width=90)
                    ui.Label(f"{SuctionSystem().suction_radius:.2f} / "
                             f"수거 {SuctionSystem().collection_radius:.2f}")
                with ui.HStack(height=22):
                    ui.Label("수거 완료", width=90)
                    self._suction_label = ui.Label("0 개")

    # ── scene / scenario 설정 ──────────────────────────────────────────────

    def _on_init(self):
        self._suction = SuctionSystem()
        self._scenario = UnderwaterSpiralScenario()

    def _setup_scene(self):
        hippo_usd_path = Path(__file__).resolve().parents[1] / "data" / HIPPO_USD_FILENAME
        if not hippo_usd_path.is_file():
            carb.log_error(f"[underwater.robot] Hippo USD not found: {hippo_usd_path}")
            return

        World.instance().scene.add(
            WheeledRobot(
                prim_path=ROBOT_PRIM_PATH,
                name=ROBOT_SCENE_NAME,
                wheel_dof_names=["left_wheel_joint", "right_wheel_joint"],
                create_robot=True,
                usd_path=str(hippo_usd_path),
                position=np.array([0.0, 0.0, float(ROBOT_SPAWN_Z_M)]),
            )
        )
        carb.log_info(f"[underwater.robot] Loaded Hippo from {hippo_usd_path}")

    def _setup_scenario(self):
        reset_center_trail_debug()
        prepare_hippo_usd_on_stage(ROBOT_PRIM_PATH)
        tag_aquasweep_attrs(ROBOT_PRIM_PATH)

        try:
            robot = World.instance().scene.get_object(ROBOT_SCENE_NAME)
        except Exception:
            robot = None

        robot_name = "under_robot_1"
        graph_path = create_cmd_vel_subscriber_graph(robot_name)
        if graph_path:
            carb.log_info(f"[underwater.robot] cmd_vel subscriber graph: {graph_path}")
        else:
            carb.log_warn("[underwater.robot] cmd_vel subscriber graph 생성 실패 — ROS2 없이도 동작")

        self._scenario = UnderwaterSpiralScenario()
        self._scenario.initialize(robot, PHYSICS_DT, ROBOT_PRIM_PATH, robot_name)

        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        self._reset_btn.enabled = True

    # ── 버튼 콜백 ─────────────────────────────────────────────────────────

    def _on_pre_reset_btn(self):
        self._timeline.stop()
        self._scenario.stop()
        try:
            self._scenario_state_btn.reset()
        except AttributeError:
            pass

    def _on_post_reset_btn(self):
        self._suction.reset()
        if hasattr(self, "_suction_label"):
            self._suction_label.text = "0 개"

        try:
            robot = World.instance().scene.get_object(ROBOT_SCENE_NAME)
        except Exception:
            robot = None
        self._scenario.sync_after_reset(robot)

        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step: float):
        """매 physics step — 추진력 적용 + 흡입 시스템."""
        self._scenario.on_physics_step(step)

        try:
            world = World.instance()
            robot = world.scene.get_object(ROBOT_SCENE_NAME)
            if robot is not None:
                pos, orient = robot.get_world_pose()
                newly = self._suction.step(
                    get_current_stage(),
                    np.asarray(pos, dtype=float),
                    np.asarray(orient, dtype=float),
                    step,
                )
                if newly > 0:
                    self._suction_label.text = f"{self._suction.collected_count} 개"
        except Exception:
            pass

    def _on_run_scenario_a_text(self):
        self._scenario.start()
        self._timeline.play()

    def _on_run_scenario_b_text(self):
        self._scenario.stop()
        self._timeline.pause()

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False
