"""AquaSweep 통합 UI — 수조·로봇·이물질을 단일 LOAD/RUN으로 제어한다."""

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
from pxr import UsdGeom

# ── 각 서브시스템 임포트 ─────────────────────────────────────────────────────
from water_tank_env_python import scene_builders
from water_tank_env_python.scenario import WaterTankScenario

from debris_python.scenario import DebrisScenario

from underwater_robot_python.dingo_physics_sanitize import (
    prepare_dingo_usd_on_stage,
    tag_aquasweep_attrs,
)
from underwater_robot_python.scenario import UnderwaterTankJetbotFsm
from underwater_robot_python.suction_system import SuctionSystem
from underwater_robot_python.trail_debug import reset_center_trail_debug, tick_center_trail_debug
from underwater_robot_python.global_variables import (
    DEBUG_CENTER_TRAIL_ENABLED,
    DINGO_USD_FILENAME,
    ROBOT_PRIM_PATH,
    ROBOT_SCENE_NAME,
    ROBOT_SPAWN_Z_M,
)

PHYSICS_DT = 1.0 / 60.0
_ROBOT_USD_PATH = (
    Path(__file__).resolve().parents[2]
    / "underwater_robot_ext" / "data" / DINGO_USD_FILENAME
)


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()
        self._on_init()

    # ── extension 콜백 ────────────────────────────────────────────────────────

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            self._scenario_state_btn.reset()
            self._scenario_state_btn.enabled = False

    def on_physics_step(self, step: float):
        try:
            robot = World.instance().scene.get_object(ROBOT_SCENE_NAME)
        except Exception:
            return
        if robot is not None and DEBUG_CENTER_TRAIL_ENABLED:
            tick_center_trail_debug(robot)

    def on_stage_event(self, event):
        if event.type == int(StageEventType.OPENED):
            self._reset_extension()

    def cleanup(self):
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()
        self._water_scenario.teardown_scenario()
        reset_center_trail_debug()

    # ── UI 빌드 ───────────────────────────────────────────────────────────────

    def build_ui(self):
        world_frame = CollapsableFrame("World Controls", collapsed=False)
        with world_frame:
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
                    pre_reset_fn=self._on_pre_reset,
                    post_reset_fn=self._on_post_reset,
                )
                self._reset_btn.enabled = False
                self.wrapped_ui_elements.append(self._reset_btn)

        run_frame = CollapsableFrame("Run Scenario", collapsed=False)
        with run_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._scenario_state_btn = StateButton(
                    "Run Scenario", "RUN", "STOP",
                    on_a_click_fn=self._on_run,
                    on_b_click_fn=self._on_stop,
                    physics_callback_fn=self._update_scenario,
                )
                self._scenario_state_btn.enabled = False
                self.wrapped_ui_elements.append(self._scenario_state_btn)

        debris_frame = CollapsableFrame("Debris", collapsed=False)
        with debris_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                with ui.HStack(height=24):
                    ui.Label("Count", width=80)
                    self._debris_count_model = ui.SimpleIntModel(10)
                    ui.IntDrag(model=self._debris_count_model, min=1, max=500)
                with ui.HStack(height=24):
                    ui.Label("Radius (m)", width=80)
                    self._debris_radius_model = ui.SimpleFloatModel(0.015)
                    ui.FloatDrag(model=self._debris_radius_model, min=0.001, max=0.2, step=0.001)
                self._spawn_btn = ui.Button(
                    "SPAWN", height=36, clicked_fn=self._on_spawn_debris,
                    style={"background_color": 0xFF1A6B2E},
                )
                self._clear_btn = ui.Button(
                    "CLEAR", height=36, clicked_fn=self._on_clear_debris,
                    style={"background_color": 0xFF6B1A1A},
                )

        suction_frame = CollapsableFrame("Suction Status", collapsed=False)
        with suction_frame:
            with ui.VStack(style=get_style(), spacing=4, height=0):
                with ui.HStack(height=22):
                    ui.Label("수거 완료", width=90)
                    self._suction_label = ui.Label("0 개")

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    def _on_init(self):
        self._water_scenario = WaterTankScenario()
        self._robot_scenario = UnderwaterTankJetbotFsm()
        self._debris_scenario = DebrisScenario()
        self._suction = SuctionSystem()

    def _setup_scene(self):
        stage = get_current_stage()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        scene_builders.enable_gpu_dynamics(stage)
        scene_builders.add_lighting(stage)
        scene_builders.build_tank(stage)
        scene_builders.build_water(stage)
        scene_builders.build_water_surface(stage)

        if not _ROBOT_USD_PATH.is_file():
            carb.log_error(f"[aquasweep] Robot USD not found: {_ROBOT_USD_PATH}")
            return

        World.instance().scene.add(
            WheeledRobot(
                prim_path=ROBOT_PRIM_PATH,
                name=ROBOT_SCENE_NAME,
                wheel_dof_names=["left_wheel_joint", "right_wheel_joint"],
                create_robot=True,
                usd_path=str(_ROBOT_USD_PATH),
                position=np.array([0.0, 0.0, float(ROBOT_SPAWN_Z_M)]),
            )
        )

    def _setup_scenario(self):
        scene_builders.enable_gpu_dynamics(get_current_stage())
        prepare_dingo_usd_on_stage(ROBOT_PRIM_PATH)
        tag_aquasweep_attrs(ROBOT_PRIM_PATH)

        robot = World.instance().scene.get_object(ROBOT_SCENE_NAME)
        self._robot_scenario.initialize(robot, PHYSICS_DT)

        self._water_scenario.teardown_scenario()
        self._water_scenario.setup_scenario(stage=get_current_stage())

        self._suction.reset()
        reset_center_trail_debug()

        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        self._reset_btn.enabled = True

    def _on_pre_reset(self):
        self._timeline.stop()
        try:
            self._scenario_state_btn.reset()
        except AttributeError:
            pass

    def _on_post_reset(self):
        self._water_scenario.teardown_scenario()
        self._water_scenario.setup_scenario(stage=get_current_stage())
        self._suction.reset()
        if hasattr(self, "_suction_label"):
            self._suction_label.text = "0 개"
        robot = World.instance().scene.get_object(ROBOT_SCENE_NAME)
        self._robot_scenario.sync_after_world_reset(robot, PHYSICS_DT)
        reset_center_trail_debug()
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step: float):
        # 수조 물리 (부력·항력·수면 애니메이션)
        self._water_scenario.update_scenario(step)
        # 로봇 나선 이동
        self._robot_scenario.on_physics_step(step)
        # 흡입 시스템
        try:
            robot = World.instance().scene.get_object(ROBOT_SCENE_NAME)
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

    def _on_spawn_debris(self):
        if self._debris_scenario.is_spawned():
            return
        count = self._debris_count_model.get_value_as_int()
        radius = self._debris_radius_model.get_value_as_float()
        self._debris_scenario.setup_scenario(count=count, radius=radius)

    def _on_clear_debris(self):
        self._debris_scenario.teardown_scenario()

    def _on_run(self):
        self._timeline.play()

    def _on_stop(self):
        self._timeline.pause()

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False
