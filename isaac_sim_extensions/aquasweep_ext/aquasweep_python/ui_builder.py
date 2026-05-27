"""AquaSweep 통합 UI — 수조·로봇·이물질을 단일 LOAD/RUN으로 제어한다.

ROS2 cmd_vel은 구독 전용 ActionGraph로 수신하고,
UnderwaterSpiralScenario가 스러스터 힘(Fx, Fy, Mz)으로 변환해 로봇을 구동한다.
바퀴 구동 ActionGraph(DiffController/ArticulationController)는 사용하지 않는다.
"""

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

from ros_isaac_env import configure_isaac_ros_env, AQUA_INTERFACES_INSTALL_HINT  # noqa: E402

# ── 각 서브시스템 임포트 ─────────────────────────────────────────────────────
from water_tank_env_python import scene_builders
from water_tank_env_python.scenario import WaterTankScenario

from water_tank_env_python import sturgeon_spawner
importlib.reload(sturgeon_spawner)  # hot-reload support

from debris_python.scenario import DebrisScenario

from underwater_robot_python.hippo_physics_sanitize import (
    prepare_hippo_usd_on_stage,
    tag_aquasweep_attrs,
    add_planar_constraint,
)
from underwater_robot_python.actiongraph_setup import remove_cmd_vel_graph
from underwater_robot_python.scenario import UnderwaterSpiralScenario
from underwater_robot_python.suction_system import SuctionSystem
from underwater_robot_python.trail_debug import reset_center_trail_debug, tick_center_trail_debug
from underwater_robot_python.global_variables import (
    DEBUG_CENTER_TRAIL_ENABLED,
    DEBUG_ENABLE_SUCTION,
    HIPPO_USD_FILENAME,
    ROBOT_SPAWN_Z_M,
)
# NOTE: ROBOT_PRIM_PATH / ROBOT_SCENE_NAME from globals are NOT imported —
# we redefine them below as aliases of the PRIMARY_ROBOT_* constants so the
# multi-robot spawn (7 hippos, one nested under each /World/Pools/Pool_<n>)
# can address the FSM-driven primary robot explicitly.

PHYSICS_DT = 1.0 / 60.0
_ROBOT_USD_PATH = (
    Path(__file__).resolve().parents[2]
    / "underwater_robot_ext" / "data" / HIPPO_USD_FILENAME
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


def _robot_specs() -> list[tuple[int, str, str, str, np.ndarray]]:
    """Return per-pool robot (idx, scene_name, spawn_path, robot_root_path, world_position).
    
    - spawn_path: Where WheeledRobot loads the USD reference
    - robot_root_path: Actual articulation root inside the USD (spawn_path + /hippo)
    Index is 1-based.
    """
    specs: list[tuple[int, str, str, str, np.ndarray]] = []
    for i, (cx, cy) in enumerate(_POOL_CENTERS, start=1):
        scene_name = f"hippo_{i}"
        spawn_path = f"/World/Pools/Pool_{i}/Robot"
        robot_root_path = f"{spawn_path}/hippo"
        position   = np.array([cx, cy, float(ROBOT_SPAWN_Z_M)])
        specs.append((i, scene_name, spawn_path, robot_root_path, position))
    return specs


# Back-compat alias for any external code referencing the primary robot.
PRIMARY_ROBOT_SCENE_NAME = "hippo_1"
PRIMARY_ROBOT_PRIM_PATH  = "/World/Pools/Pool_1/Robot/hippo"
# Back-compat aliases for any external code still importing the old names.
ROBOT_SCENE_NAME = PRIMARY_ROBOT_SCENE_NAME
ROBOT_PRIM_PATH  = PRIMARY_ROBOT_PRIM_PATH


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()

        # Per-robot suction systems — index 0 == robot_1
        self._suctions: list[SuctionSystem] = []
        # Per-robot thruster scenarios — index 0 == robot_1
        self._scenarios: list[UnderwaterSpiralScenario] = []
        # ROS2 cmd_vel 구독자 (rclpy, Isaac 내장 py3.11)
        self._cmd_receivers: list = []
        self._ros_executor = None
        self._ros_thread = None

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
        # ── StateButton과 독립적으로 항상 water scenario 실행 ──
        # Debris spawn 시 timeline stop/play 사이클에서도 Z 클램핑 유지
        if self._water_scenario.is_loaded():
            self._water_scenario.update_scenario(step)

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
        for scenario in self._scenarios:
            scenario.stop()
        self._water_scenario.teardown_scenario()
        reset_center_trail_debug()
        self._stop_ros()
        for i in range(_NUM_ROBOTS):
            remove_cmd_vel_graph(f"under_robot_{i + 1}")

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
        # Each pool has its own debris particles path
        self._suctions = [
            SuctionSystem(particles_prim_path=f"/World/Pools/Pool_{i+1}/Debris/Particles")
            for i in range(_NUM_ROBOTS)
        ]
        # Per-robot thruster scenarios (initialized in _setup_scenario)
        self._scenarios = [UnderwaterSpiralScenario() for _ in range(_NUM_ROBOTS)]
        # ROS가 이미 살아있으면(stage 리셋 시) receiver를 시나리오에 재연결
        for i, receiver in enumerate(self._cmd_receivers):
            if receiver is not None:
                self._scenarios[i].set_cmd_vel_receiver(receiver)

    def _setup_scene(self):
        stage = get_current_stage()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        scene_builders.enable_gpu_dynamics(stage)
        scene_builders.add_lighting(stage)
        scene_builders.build_building(stage)
        scene_builders.build_pools(stage)
        scene_builders.build_top_cameras(stage)
        scene_builders.build_global_top_camera(stage)
        scene_builders.build_equipment(stage)
        sturgeon_spawner.spawn_sturgeons(stage)

        if not _ROBOT_USD_PATH.is_file():
            carb.log_error(f"[aquasweep] Robot USD not found: {_ROBOT_USD_PATH}")
            return

        for _idx, scene_name, spawn_path, _robot_root, position in _robot_specs():
            World.instance().scene.add(
                WheeledRobot(
                    prim_path=spawn_path,
                    name=scene_name,
                    wheel_dof_names=["left_wheel_joint", "right_wheel_joint"],
                    create_robot=True,
                    usd_path=str(_ROBOT_USD_PATH),
                    position=position,
                )
            )

    def _setup_scenario(self):
        scene_builders.enable_gpu_dynamics(get_current_stage())
        for _idx, _scene_name, _spawn_path, robot_root, _pos in _robot_specs():
            prepare_hippo_usd_on_stage(robot_root)
            tag_aquasweep_attrs(robot_root)
            add_planar_constraint(robot_root)

        # 각 로봇의 스러스터 시나리오 초기화 + cmd_vel receiver 연결
        carb.log_warn(f"[aquasweep] _setup_scenario 시작 — {_NUM_ROBOTS}개 로봇 초기화")
        for i, (idx, scene_name, _spawn_path, robot_root, _pos) in enumerate(_robot_specs()):
            try:
                robot = World.instance().scene.get_object(scene_name)
            except Exception:
                robot = None
            carb.log_warn(f"[aquasweep] scenario[{i}] initialize: robot={scene_name} {'OK' if robot else 'None'} path={robot_root}")
            self._scenarios[i].initialize(
                robot, PHYSICS_DT, robot_root, f"under_robot_{idx}"
            )
            # cmd_vel receiver 연결 (ROS가 살아있으면)
            if i < len(self._cmd_receivers) and self._cmd_receivers[i] is not None:
                self._scenarios[i].set_cmd_vel_receiver(self._cmd_receivers[i])
                carb.log_warn(f"[aquasweep] scenario[{i}] receiver 연결 완료")

        self._water_scenario.teardown_scenario()
        self._water_scenario.setup_scenario(stage=get_current_stage())

        for suction in self._suctions:
            suction.reset()
        reset_center_trail_debug()

        _set_viewport_lighting_mode("stage")

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
        reset_center_trail_debug()
        # 리셋 후 각 로봇 객체를 시나리오에 재동기화
        for i, (_idx, scene_name, _spawn_path, _robot_root, _pos) in enumerate(_robot_specs()):
            try:
                robot = World.instance().scene.get_object(scene_name)
            except Exception:
                robot = None
            self._scenarios[i].sync_after_reset(robot)
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step: float):
        """매 physics step — 스러스터 힘 인가 + 이물질 흡입.

        water_scenario.update_scenario()는 on_physics_step()에서 항상 실행되므로 여기선 생략.
        """
        for i, (_idx, scene_name, _spawn_path, _robot_root, _pos) in enumerate(_robot_specs()):
            # 스러스터 힘 인가 (cmd_vel → Fx, Fy, Mz)
            self._scenarios[i].on_physics_step(step)

            if not DEBUG_ENABLE_SUCTION:
                continue

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

    def _start_ros(self) -> None:
        """Isaac Sim 내장 py3.11 rclpy로 cmd_vel 구독자 노드를 생성하고 백그라운드 스핀."""
        import traceback

        try:
            import rclpy as _probe
            _already_ok = _probe.ok()
        except ImportError:
            _already_ok = False

        if not _already_ok:
            if not configure_isaac_ros_env():
                carb.log_warn(
                    f"[aquasweep] ROS env 설정 실패 — cmd_vel 수신 불가. {AQUA_INTERFACES_INSTALL_HINT}"
                )
                return

        try:
            import rclpy
            from rclpy.executors import SingleThreadedExecutor
            if not rclpy.ok():
                rclpy.init()
            self._ros_executor = SingleThreadedExecutor()
        except Exception as exc:
            carb.log_warn(f"[aquasweep] ROS executor 초기화 실패: {exc}\n{traceback.format_exc()}")
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
                    self._cmd_receivers[i] = receiver
                    carb.log_warn(f"[aquasweep] robot_{i+1} cmd_vel 구독 시작 → /{robot_name}/cmd_vel")
                else:
                    carb.log_warn(f"[aquasweep] robot_{i+1} receiver 생성 실패: {get_last_ros_import_error()}")
            except Exception as exc:
                carb.log_warn(f"[aquasweep] robot_{i+1} receiver 오류: {exc}")

        self._ros_thread = threading.Thread(
            target=self._ros_executor.spin,
            daemon=True,
            name="aquasweep_ros_spin",
        )
        self._ros_thread.start()
        carb.log_warn(f"[aquasweep] ROS spin thread 시작 완료")

    def _stop_ros(self) -> None:
        if self._ros_executor is not None:
            self._ros_executor.shutdown(timeout_sec=1.0)
            self._ros_executor = None
        self._cmd_receivers = [None] * _NUM_ROBOTS

    def _on_run(self):
        # PhysX UI 오류 방지
        try:
            import omni.usd
            ctx = omni.usd.get_context()
            if ctx:
                ctx.get_selection().clear_selected_prim_paths()
        except Exception:
            pass

        carb.log_warn(f"[aquasweep] RUN — {len(self._scenarios)}개 시나리오 start()")
        for scenario in self._scenarios:
            scenario.start()
        self._timeline.play()

    def _on_stop(self):
        for scenario in self._scenarios:
            scenario.stop()
        self._timeline.pause()

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False
