"""AquaSweep 통합 UI — 수조·로봇·이물질을 단일 LOAD/RUN으로 제어한다."""

import importlib
import sys
import threading
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

_common = Path(__file__).resolve().parents[2] / "common"
if str(_common) not in sys.path:
    sys.path.insert(0, str(_common))

from ros_isaac_env import AQUA_INTERFACES_INSTALL_HINT, configure_isaac_ros_env  # noqa: E402

# ── 각 서브시스템 임포트 ─────────────────────────────────────────────────────
from water_tank_env_python import scene_builders
from water_tank_env_python.scenario import WaterTankScenario

from water_tank_env_python import sturgeon_spawner
importlib.reload(sturgeon_spawner)  # hot-reload support

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
    ROBOT_SPAWN_Z_M,
)
# NOTE: ROBOT_PRIM_PATH / ROBOT_SCENE_NAME from globals are NOT imported —
# we redefine them below as aliases of the PRIMARY_ROBOT_* constants so the
# multi-robot spawn (7 dingos, one nested under each /World/Pools/Pool_<n>)
# can address the FSM-driven primary robot explicitly.

PHYSICS_DT = 1.0 / 60.0
_ROBOT_USD_PATH = (
    Path(__file__).resolve().parents[2]
    / "underwater_robot_ext" / "data" / DINGO_USD_FILENAME
)

# ── Multi-pool robot specs ─────────────────────────────────────────────────────
from water_tank_env_python import params as _params  # noqa: E402
_POOL_CENTERS: list[tuple[float, float]] = list(getattr(_params, "POOL_CENTERS", []))
_NUM_ROBOTS = len(_POOL_CENTERS)


def _set_viewport_lighting_mode(mode: str) -> None:
    try:
        import omni.kit.commands
        omni.kit.commands.execute("SetLightingMenuMode", lighting_mode=mode)
    except Exception as e:  # noqa: BLE001
        carb.log_warn(f"[aquasweep] couldn't set viewport lighting mode='{mode}': {e}")


def _robot_specs() -> list[tuple[int, str, str, np.ndarray]]:
    """Return per-pool robot (idx, scene_name, prim_path, world_position). Index is 1-based."""
    specs: list[tuple[int, str, str, np.ndarray]] = []
    for i, (cx, cy) in enumerate(_POOL_CENTERS, start=1):
        scene_name = f"dingo_{i}"
        prim_path  = f"/World/Pools/Pool_{i}/Robot"
        position   = np.array([cx, cy, float(ROBOT_SPAWN_Z_M)])
        specs.append((i, scene_name, prim_path, position))
    return specs


# Back-compat alias for any external code referencing the primary robot.
PRIMARY_ROBOT_SCENE_NAME = "dingo_1"
PRIMARY_ROBOT_PRIM_PATH  = "/World/Pools/Pool_1/Robot"
# Back-compat aliases for any external code still importing the old names.
ROBOT_SCENE_NAME = PRIMARY_ROBOT_SCENE_NAME
ROBOT_PRIM_PATH  = PRIMARY_ROBOT_PRIM_PATH


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()

        self._ros_executor = None
        self._ros_thread = None
        # Per-robot lists — index 0 == robot_1
        self._cmd_receivers: list = []
        self._robot_scenarios: list[UnderwaterTankJetbotFsm] = []
        self._suctions: list[SuctionSystem] = []

        self._on_init()
        self._start_ros()

    # ── extension 콜백 ────────────────────────────────────────────────────────

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            self._scenario_state_btn.reset()
            self._scenario_state_btn.enabled = False

    def on_physics_step(self, step: float):
        try:
            robot = World.instance().scene.get_object(PRIMARY_ROBOT_SCENE_NAME)
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
        self._stop_ros()

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
                    ui.Label("Count Min", width=80)
                    self._debris_count_min_model = ui.SimpleIntModel(30)
                    ui.IntDrag(model=self._debris_count_min_model, min=1, max=500)
                with ui.HStack(height=24):
                    ui.Label("Count Max", width=80)
                    self._debris_count_max_model = ui.SimpleIntModel(70)
                    ui.IntDrag(model=self._debris_count_max_model, min=1, max=500)
                with ui.HStack(height=24):
                    ui.Label("Radius (m)", width=80)
                    self._debris_radius_model = ui.SimpleFloatModel(0.05)
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
        self._debris_scenario = DebrisScenario()

        self._robot_scenarios = [UnderwaterTankJetbotFsm() for _ in range(_NUM_ROBOTS)]
        self._suctions = [SuctionSystem() for _ in range(_NUM_ROBOTS)]

        # 이미 ROS가 실행 중이면(stage 리셋 시) 수신기를 재연결
        for i, receiver in enumerate(self._cmd_receivers):
            if receiver is not None:
                self._robot_scenarios[i].set_cmd_vel_receiver(receiver)

    def _start_ros(self) -> None:
        import traceback

        try:
            import rclpy as _probe
            _already_ok = _probe.ok()
        except ImportError:
            _already_ok = False

        if not _already_ok:
            if not configure_isaac_ros_env():
                carb.log_warn(
                    f"[aquasweep] ROS env setup failed. {AQUA_INTERFACES_INSTALL_HINT}"
                )
                return

        try:
            import rclpy
            from rclpy.executors import SingleThreadedExecutor
            from underwater_robot_python.cmd_vel_receiver import (
                create_cmd_vel_receiver,
                get_last_ros_import_error,
            )

            if not rclpy.ok():
                rclpy.init()

            self._ros_executor = SingleThreadedExecutor()

        except Exception as exc:
            carb.log_warn(f"[aquasweep] ROS2 executor init failed: {exc}")
            carb.log_warn(traceback.format_exc())
            return

        from underwater_robot_python.cmd_vel_receiver import (
            create_cmd_vel_receiver,
            get_last_ros_import_error,
        )

        self._cmd_receivers = [None] * _NUM_ROBOTS
        for i in range(_NUM_ROBOTS):
            robot_name = f"under_robot_{i + 1}"
            try:
                receiver = create_cmd_vel_receiver(robot_name)
                if receiver is not None:
                    self._ros_executor.add_node(receiver)
                    self._robot_scenarios[i].set_cmd_vel_receiver(receiver)
                    self._cmd_receivers[i] = receiver
                    carb.log_warn(
                        f"[aquasweep] robot_{i+1} cmd_vel subscriber STARTED — /{robot_name}/cmd_vel"
                    )
                else:
                    carb.log_warn(
                        f"[aquasweep] robot_{i+1} receiver None — {get_last_ros_import_error()}"
                    )
            except Exception as exc:
                carb.log_warn(f"[aquasweep] robot_{i+1} receiver FAILED: {exc}")
                carb.log_warn(traceback.format_exc())

        self._ros_thread = threading.Thread(
            target=self._ros_executor.spin,
            daemon=True,
            name="aquasweep_ros_spin",
        )
        self._ros_thread.start()

    def _stop_ros(self) -> None:
        if self._ros_executor is not None:
            self._ros_executor.shutdown(timeout_sec=1.0)
            self._ros_executor = None
        self._cmd_receivers = [None] * _NUM_ROBOTS

    def _setup_scene(self):
        stage = get_current_stage()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        scene_builders.enable_gpu_dynamics(stage)
        scene_builders.add_lighting(stage)
        scene_builders.build_building(stage)
        scene_builders.build_pools(stage)
        scene_builders.build_top_cameras(stage)
        scene_builders.build_equipment(stage)
        sturgeon_spawner.spawn_sturgeons(stage)

        if not _ROBOT_USD_PATH.is_file():
            carb.log_error(f"[aquasweep] Robot USD not found: {_ROBOT_USD_PATH}")
            return

        for _idx, scene_name, prim_path, position in _robot_specs():
            World.instance().scene.add(
                WheeledRobot(
                    prim_path=prim_path,
                    name=scene_name,
                    wheel_dof_names=["left_wheel_joint", "right_wheel_joint"],
                    create_robot=True,
                    usd_path=str(_ROBOT_USD_PATH),
                    position=position,
                )
            )

    def _setup_scenario(self):
        scene_builders.enable_gpu_dynamics(get_current_stage())
        for _idx, _scene_name, prim_path, _pos in _robot_specs():
            prepare_dingo_usd_on_stage(prim_path)
            tag_aquasweep_attrs(prim_path)

        for i, (_idx, scene_name, _prim_path, _pos) in enumerate(_robot_specs()):
            robot = World.instance().scene.get_object(scene_name)
            if robot is not None:
                cx, cy = _POOL_CENTERS[i]
                self._robot_scenarios[i].initialize(robot, PHYSICS_DT, pool_center=(cx, cy))
                if self._cmd_receivers[i] is not None:
                    self._robot_scenarios[i].set_cmd_vel_receiver(self._cmd_receivers[i])

        self._water_scenario.teardown_scenario()
        self._water_scenario.setup_scenario(stage=get_current_stage())

        for suction in self._suctions:
            suction.reset()
        reset_center_trail_debug()

        _set_viewport_lighting_mode("camera")

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
        for suction in self._suctions:
            suction.reset()
        if hasattr(self, "_suction_label"):
            self._suction_label.text = "0 개"
        for i, (_idx, scene_name, _prim_path, _pos) in enumerate(_robot_specs()):
            robot = World.instance().scene.get_object(scene_name)
            self._robot_scenarios[i].sync_after_world_reset(robot, PHYSICS_DT)
        reset_center_trail_debug()
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step: float):
        self._water_scenario.update_scenario(step)

        for i, (_idx, scene_name, _prim_path, _pos) in enumerate(_robot_specs()):
            self._robot_scenarios[i].on_physics_step(step)
            try:
                robot = World.instance().scene.get_object(scene_name)
                if robot is not None:
                    pos, orient = robot.get_world_pose()
                    newly = self._suctions[i].step(
                        get_current_stage(),
                        np.asarray(pos, dtype=float),
                        np.asarray(orient, dtype=float),
                        step,
                    )
                    if newly > 0:
                        total = sum(s.collected_count for s in self._suctions)
                        self._suction_label.text = f"{total} 개"
            except Exception:
                pass

    def _on_spawn_debris(self):
        if self._debris_scenario.is_spawned():
            return
        lo = self._debris_count_min_model.get_value_as_int()
        hi = self._debris_count_max_model.get_value_as_int()
        radius = self._debris_radius_model.get_value_as_float()
        self._debris_scenario.setup_scenario(count_range=(lo, hi), radius=radius)

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
