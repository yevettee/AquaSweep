"""UI for the water.tank.env extension.

LOAD  → build_scene: lighting + tank + water added to the *current* stage
           + discover rigid bodies for the water-physics applier
RUN   → timeline play; each physics step applies buoyancy/drag + OceanSim render
RESET → tear down & re-setup the scenario
"""
import omni.timeline
import omni.ui as ui
from isaacsim.core.utils.stage import get_current_stage
from isaacsim.examples.extension.core_connectors import LoadButton, ResetButton
from isaacsim.gui.components.element_wrappers import CollapsableFrame, StateButton
from isaacsim.gui.components.ui_utils import get_style
from omni.usd import StageEventType
from pxr import UsdGeom

from . import oceansim_camera as _ocam
from . import scene_builders
from . import sturgeon_spawner
from .scenario import WaterTankScenario


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()
        self._on_init()

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            self._scenario_state_btn.reset()
            self._scenario_state_btn.enabled = False

    def on_physics_step(self, step):
        pass

    def on_stage_event(self, event):
        if event.type == int(StageEventType.OPENED):
            self._reset_extension()

    def cleanup(self):
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()
        self._scenario.teardown_scenario()

    def build_ui(self):
        world_controls_frame = CollapsableFrame("World Controls", collapsed=False)
        with world_controls_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._load_btn = LoadButton(
                    "Load Button", "LOAD",
                    setup_scene_fn=self._setup_scene,
                    setup_post_load_fn=self._setup_scenario,
                )
                self._load_btn.set_world_settings(physics_dt=1 / 60.0, rendering_dt=1 / 60.0)
                self.wrapped_ui_elements.append(self._load_btn)

                self._reset_btn = ResetButton(
                    "Reset Button", "RESET",
                    pre_reset_fn=None, post_reset_fn=self._on_post_reset_btn,
                )
                self._reset_btn.enabled = False
                self.wrapped_ui_elements.append(self._reset_btn)

        run_scenario_frame = CollapsableFrame("Run Scenario")
        with run_scenario_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._scenario_state_btn = StateButton(
                    "Run Scenario", "RUN", "STOP",
                    on_a_click_fn=self._on_run_scenario_a_text,
                    on_b_click_fn=self._on_run_scenario_b_text,
                    physics_callback_fn=self._update_scenario,
                )
                self._scenario_state_btn.enabled = False
                self.wrapped_ui_elements.append(self._scenario_state_btn)

        oceansim_frame = CollapsableFrame("OceanSim Camera", collapsed=False)
        with oceansim_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                if _ocam.OCEANSIM_AVAILABLE:
                    ui.Label("탁도 (Turbidity)")
                    self._turbidity_combo = ui.ComboBox(
                        1, *_ocam.TURBIDITY_LABELS  # 기본 index 1 = "medium"
                    )
                    self._turbidity_combo.model.add_item_changed_fn(
                        self._on_turbidity_changed
                    )
                else:
                    ui.Label("OceanSim 미설치 — extsUser/OceanSim 확인")

    def _on_init(self):
        self._scenario = WaterTankScenario()

    def _setup_scene(self):
        stage = get_current_stage()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        scene_builders.enable_gpu_dynamics(stage)
        scene_builders.add_lighting(stage)
        scene_builders.build_building(stage)
        scene_builders.build_outdoor_ground(stage)
        scene_builders.build_parking_lot(stage)
        scene_builders.build_parked_cars(stage)
        scene_builders.build_door(stage)
        scene_builders.build_pools(stage)
        scene_builders.build_top_cameras(stage)
        scene_builders.build_global_top_camera(stage)  # 전체 수조를 보는 단일 글로벌 카메라
        scene_builders.build_equipment(stage)
        sturgeon_spawner.spawn_sturgeons(stage)

        # Snap viewport LAST so a camera failure can't drop later spawns.
        try:
            scene_builders.set_default_view(stage)
        except Exception as exc:
            import carb
            carb.log_warn(f"[water_tank_env] set_default_view skipped: {exc}")

    def _setup_scenario(self):
        scene_builders.enable_gpu_dynamics(get_current_stage())
        self._reset_scenario()
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        self._reset_btn.enabled = True

    def _reset_scenario(self):
        self._scenario.teardown_scenario()
        self._scenario.setup_scenario(stage=get_current_stage())

    def _on_post_reset_btn(self):
        self._reset_scenario()
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step):
        self._scenario.update_scenario(step)

    def _on_turbidity_changed(self, model, _) -> None:
        idx = model.get_item_value_model().as_int
        turbidity = _ocam.TURBIDITY_LABELS[idx]
        stage = get_current_stage()
        self._scenario.set_turbidity(turbidity, stage)

    def _on_run_scenario_a_text(self):
        self._timeline.play()

    def _on_run_scenario_b_text(self):
        self._timeline.pause()

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False
