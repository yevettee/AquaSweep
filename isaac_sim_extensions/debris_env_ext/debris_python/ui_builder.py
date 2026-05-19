"""UI for the debris.env Extension.

SPAWN → DebrisScenario.setup_scenario(): 파티클 생성
CLEAR → DebrisScenario.teardown_scenario(): 파티클 제거
"""
import omni.ui as ui
from isaacsim.gui.components.element_wrappers import CollapsableFrame
from isaacsim.gui.components.ui_utils import get_style
from omni.usd import StageEventType

from .scenario import DebrisScenario
from . import global_variables as gv


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._scenario = DebrisScenario()
        self._count_model: ui.SimpleIntModel | None = None
        self._radius_model: ui.SimpleFloatModel | None = None

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        pass

    def on_physics_step(self, step):
        pass

    def on_stage_event(self, event):
        if event.type == int(StageEventType.OPENED):
            self._scenario.teardown_scenario()
            self._refresh_button_states()

    def cleanup(self):
        self._scenario.teardown_scenario()

    def build_ui(self):
        config_frame = CollapsableFrame("Debris Settings", collapsed=False)
        with config_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                with ui.HStack(height=24):
                    ui.Label("Count", width=80)
                    self._count_model = ui.SimpleIntModel(gv.DEBRIS_COUNT)
                    ui.IntDrag(model=self._count_model, min=1, max=500)

                with ui.HStack(height=24):
                    ui.Label("Radius (m)", width=80)
                    self._radius_model = ui.SimpleFloatModel(gv.DEBRIS_RADIUS)
                    ui.FloatDrag(model=self._radius_model, min=0.001, max=0.2, step=0.001)

        control_frame = CollapsableFrame("Controls", collapsed=False)
        with control_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._spawn_btn = ui.Button(
                    "SPAWN",
                    height=40,
                    clicked_fn=self._on_spawn,
                    style={"background_color": 0xFF1A6B2E},
                )
                self._clear_btn = ui.Button(
                    "CLEAR",
                    height=40,
                    clicked_fn=self._on_clear,
                    style={"background_color": 0xFF6B1A1A},
                )
        self._refresh_button_states()

    def _on_spawn(self):
        if self._scenario.is_spawned():
            return
        count = self._count_model.get_value_as_int() if self._count_model else gv.DEBRIS_COUNT
        radius = self._radius_model.get_value_as_float() if self._radius_model else gv.DEBRIS_RADIUS
        self._scenario.setup_scenario(count=count, radius=radius)
        self._refresh_button_states()

    def _on_clear(self):
        self._scenario.teardown_scenario()
        self._refresh_button_states()

    def _refresh_button_states(self):
        if not hasattr(self, "_spawn_btn"):
            return
        spawned = self._scenario.is_spawned()
        self._spawn_btn.enabled = not spawned
        self._clear_btn.enabled = spawned
