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

# ── 카메라 퍼블리싱 익스텐션 임포트 (optional) ─────────────────────────────────
try:
    from top_camera_python import ros_graph_builder as top_graph
    from top_camera_python.camera_discovery import discover_top_cameras
    from top_camera_python.global_variables import DEFAULT_RESOLUTION as TOP_CAM_RESOLUTION
    _TOP_CAM_AVAILABLE = True
except ImportError:
    _TOP_CAM_AVAILABLE = False

try:
    from under_camera_python import ros_graph_builder as under_graph
    from under_camera_python.camera_discovery import discover_under_cameras
    _UNDER_CAM_AVAILABLE = True
except ImportError:
    _UNDER_CAM_AVAILABLE = False

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
import underwater_robot_python.global_variables as _uw_gv
from underwater_robot_python.global_variables import (
    DEBUG_ENABLE_SUCTION,
    HIPPO_USD_FILENAME,
    ROBOT_SPAWN_Z_M,
    WATER_ROTATION_OMEGA,
)
# NOTE: ROBOT_PRIM_PATH / ROBOT_SCENE_NAME from globals are NOT imported —
# we redefine them below as aliases of the PRIMARY_ROBOT_* constants so the
# multi-robot spawn (7 hippos, one nested under each /World/Pools/Pool_<n>)
# can address the FSM-driven primary robot explicitly.

# ── Rail Robot 임포트 ─────────────────────────────────────────────────────────
from rail_robot_python.scenario import RailRobotScenario
from rail_robot_python.rail_builder import (
    build_rails,
    build_hinge_bracket,
    build_revolute_joint,
    build_scraper_tool,
)
from rail_robot_python.joint_state_bridge import create_bridge as create_rail_bridge
from rail_robot_python.global_variables import (
    COBOT_USD_PATH,
    RAIL_CENTER_R,
    RAIL_MOUNT_Z,
)
from rail_robot_python.clean_wall_action_server import create_clean_wall_manager

PHYSICS_DT = 1.0 / 60.0
_ROBOT_USD_PATH = (
    Path(__file__).resolve().parents[2]
    / "underwater_robot_ext" / "data" / HIPPO_USD_FILENAME
)

# Pools root path
POOLS_ROOT = "/World/Pools"

# ── Multi-pool robot specs ─────────────────────────────────────────────────────
from water_tank_env_python import params as _params  # noqa: E402
_POOL_CENTERS: list[tuple[float, float]] = list(getattr(_params, "POOL_CENTERS", []))
_NUM_ROBOTS = len(_POOL_CENTERS)

# ── Rail Robot 설정 ───────────────────────────────────────────────────────────
# 렌더링 부하 감소를 위해 Rail Robot을 생성할 풀 인덱스 지정 (1-based)
# 예: [1] = pool_1만, [1, 2, 3] = pool_1~3, [] = 비활성화
# None = 모든 풀에 생성 (주의: 7개 전부 로드 시 매우 무거움)
RAIL_ROBOT_ENABLED_POOLS: list[int] | None = None  # 기본값: pool_1만 활성화

# ── 내부 플래너 설정 ───────────────────────────────────────────────────────────
# True: Isaac Sim 내부 SpiralPlanner 사용 (MotionCommandBridge 서비스로 제어)
# False: 기존 방식 유지 (aqua_controller에서 cmd_vel 발행)
USE_INTERNAL_PLANNER: bool = True  # 기본값: 기존 방식 유지


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
        # Per-pool rail robot scenarios — index 0 == pool_1
        self._rail_scenarios: list[RailRobotScenario] = []
        self._rail_bridges: list = []
        # ROS2 cmd_vel 구독자 (rclpy, Isaac 내장 py3.11)
        self._cmd_receivers: list = []
        self._ros_executor = None
        self._ros_thread = None
        # MotionCommandBridge 인스턴스 (내부 플래너 모드용)
        self._floor_bridges: list = []
        self._wall_bridges: list = []
        # CleanWall action server (per pool)
        self._clean_wall_server = None

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
        if self._water_scenario.is_loaded():
            self._water_scenario.update_scenario(step)

        # 레일 로봇: 매 physics step (60Hz) — StateButton 콜백(렌더 Hz)에 두면
        # sim-time이 wall-clock 대비 ~5× 느려짐 (60s 설정 → ~5min).
        for rail_scenario in self._rail_scenarios:
            rail_scenario.on_physics_step(step)

        try:
            robot = World.instance().scene.get_object(PRIMARY_ROBOT_SCENE_NAME)
        except Exception:
            return
        if robot is not None and _uw_gv.DEBUG_CENTER_TRAIL_ENABLED:
            tick_center_trail_debug(robot)

    def on_stage_event(self, event):
        if event.type == int(StageEventType.OPENED):
            self._reset_extension()

    def cleanup(self):
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()
        for scenario in self._scenarios:
            scenario.stop()
        for rail_scenario in self._rail_scenarios:
            rail_scenario.stop()
        self._water_scenario.teardown_scenario()
        reset_center_trail_debug()
        self._cleanup_rail_bridges()
        self._cleanup_clean_wall_server()
        self._cleanup_camera_graphs()
        self._stop_ros()
        for i in range(_NUM_ROBOTS):
            remove_cmd_vel_graph(f"under_robot_{i + 1}")

    def _cleanup_rail_bridges(self) -> None:
        """Cleanup rail robot ROS bridges."""
        for bridge in self._rail_bridges:
            if bridge is not None:
                try:
                    bridge.destroy_node()
                except Exception:
                    pass
        self._rail_bridges = [None] * _NUM_ROBOTS

    def _cleanup_clean_wall_server(self) -> None:
        """Cleanup CleanWall action server manager."""
        if self._clean_wall_server is not None:
            self._clean_wall_server.cleanup()
            self._clean_wall_server = None

    def _cleanup_camera_graphs(self) -> None:
        """Cleanup camera publishing OmniGraphs."""
        if _TOP_CAM_AVAILABLE:
            try:
                top_graph.teardown_graph()
            except Exception:
                pass
        if _UNDER_CAM_AVAILABLE:
            try:
                under_graph.teardown_graph()
            except Exception:
                pass

    # ── UI 빌드 ───────────────────────────────────────────────────────────────

    def build_ui(self):
        # ── Quick Setup (단계별 버튼) ─────────────────────────────────────────
        quick_frame = CollapsableFrame("Quick Setup", collapsed=False)
        with quick_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                # 안내 텍스트
                ui.Label(
                    "순서: LOAD → SPAWN DEBRIS → RUN → PUBLISH CAMS",
                    style={"color": 0xFF888888, "font_size": 12},
                    word_wrap=True,
                )
                ui.Spacer(height=4)

                # 1. LOAD
                self._load_btn = LoadButton(
                    "Load Button", "LOAD",
                    setup_scene_fn=self._setup_scene,
                    setup_post_load_fn=self._setup_scenario,
                )
                self._load_btn.set_world_settings(physics_dt=PHYSICS_DT, rendering_dt=PHYSICS_DT)
                self.wrapped_ui_elements.append(self._load_btn)

                # 2. SPAWN DEBRIS
                self._spawn_debris_btn = ui.Button(
                    "SPAWN DEBRIS",
                    height=36,
                    clicked_fn=self._on_spawn_debris,
                    enabled=False,
                )

                # 3. RUN
                self._scenario_state_btn = StateButton(
                    "Run Scenario", "RUN", "STOP",
                    on_a_click_fn=self._on_run,
                    on_b_click_fn=self._on_stop,
                    physics_callback_fn=self._update_scenario,
                )
                self._scenario_state_btn.enabled = False
                self.wrapped_ui_elements.append(self._scenario_state_btn)

                # 4. PUBLISH CAMS
                self._publish_cams_btn = ui.Button(
                    "PUBLISH CAMS",
                    height=36,
                    clicked_fn=self._on_publish_cams,
                    style={"background_color": 0xFF1A6B2E},
                    enabled=False,
                )

                ui.Spacer(height=4)

                # RESET
                self._reset_btn = ResetButton(
                    "Reset Button", "RESET",
                    pre_reset_fn=self._on_pre_reset,
                    post_reset_fn=self._on_post_reset,
                )
                self._reset_btn.enabled = False
                self.wrapped_ui_elements.append(self._reset_btn)

        # ── Debris Settings (상세 설정) ───────────────────────────────────────
        debris_frame = CollapsableFrame("Debris Settings", collapsed=True)
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
                ui.Button(
                    "CLEAR DEBRIS", height=36, clicked_fn=self._on_clear_debris,
                    style={"background_color": 0xFF6B1A1A},
                )

        # ── 시각화 ───────────────────────────────────────────────────────────
        viz_frame = CollapsableFrame("시각화", collapsed=True)
        with viz_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._trail_btn = StateButton(
                    "Trail", "경로 Trail 켜기", "경로 Trail 끄기",
                    on_a_click_fn=self._on_trail_on,
                    on_b_click_fn=self._on_trail_off,
                )
                self.wrapped_ui_elements.append(self._trail_btn)

        # ── 수류 설정 ─────────────────────────────────────────────────────────
        water_frame = CollapsableFrame("수류 설정", collapsed=True)
        with water_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._water_current_btn = StateButton(
                    "Water Current", "수류 켜기", "수류 끄기",
                    on_a_click_fn=self._on_water_current_on,
                    on_b_click_fn=self._on_water_current_off,
                )
                self.wrapped_ui_elements.append(self._water_current_btn)

        # ── Suction Status (DEBUG_ENABLE_SUCTION이 True일 때만 표시) ──────────
        if DEBUG_ENABLE_SUCTION:
            suction_frame = CollapsableFrame("Suction Status", collapsed=True)
            with suction_frame:
                with ui.VStack(style=get_style(), spacing=4, height=0):
                    with ui.HStack(height=22):
                        ui.Label("수거 완료", width=90)
                        self._suction_label = ui.Label("0 개")
        else:
            self._suction_label = None

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    def _on_init(self):
        self._water_scenario = WaterTankScenario()
        self._debris_scenario = DebrisScenario()
        # Each pool has its own debris particles path
        self._suctions = [
            SuctionSystem(
                particles_prim_path=f"/World/Pools/Pool_{i+1}/Debris/Particles",
                pool_center=_POOL_CENTERS[i],
            )
            for i in range(_NUM_ROBOTS)
        ]
        # Per-robot thruster scenarios (initialized in _setup_scenario)
        self._scenarios = [
            UnderwaterSpiralScenario(use_internal_planner=USE_INTERNAL_PLANNER)
            for _ in range(_NUM_ROBOTS)
        ]
        # Per-pool rail robot scenarios (initialized in _setup_scenario)
        self._rail_scenarios = [
            RailRobotScenario(pool_idx=i+1, pool_center=(0.0, 0.0))
            for i in range(_NUM_ROBOTS)
        ]
        self._rail_bridges = [None] * _NUM_ROBOTS
        # ROS가 이미 살아있으면(stage 리셋 시) receiver를 시나리오에 재연결
        for i, receiver in enumerate(self._cmd_receivers):
            if receiver is not None:
                self._scenarios[i].set_cmd_vel_receiver(receiver)

    def _setup_scene(self):
        from pxr import Gf

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

        # Spawn underwater robots
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

        # Build rail robots for wall cleaning
        self._setup_rail_robots(stage)

    def _setup_rail_robots(self, stage) -> None:
        """Setup rail robot USD prims and rails for enabled pools only."""
        from pathlib import Path
        from pxr import Gf

        # 활성화된 풀만 처리
        enabled = RAIL_ROBOT_ENABLED_POOLS
        if enabled is not None and len(enabled) == 0:
            carb.log_info("[aquasweep] Rail robots disabled (RAIL_ROBOT_ENABLED_POOLS=[])")
            return

        cobot_path = Path(COBOT_USD_PATH)
        if not cobot_path.is_file():
            carb.log_warn(f"[aquasweep] Rail robot USD not found: {COBOT_USD_PATH}")
            return

        # Build circular rails on top of pool walls (visual only, always build)
        build_rails(stage, POOLS_ROOT)

        spawned_count = 0
        for i in range(1, _NUM_ROBOTS + 1):
            # enabled가 None이면 모든 풀, 아니면 지정된 풀만
            if enabled is not None and i not in enabled:
                continue

            pool_path = f"{POOLS_ROOT}/Pool_{i}"
            rail_path = f"{pool_path}/RailRobot"
            carriage_path = f"{rail_path}/Carriage"

            if stage.GetPrimAtPath(carriage_path).IsValid():
                spawned_count += 1
                continue  # Already loaded (hot-reload)

            stage.DefinePrim(rail_path, "Xform")
            carriage_prim = stage.DefinePrim(carriage_path, "Xform")
            carriage_prim.GetReferences().AddReference(str(cobot_path))

            # Initial position: angle=0, centered on rail (pool-local coordinates)
            xf = UsdGeom.Xformable(carriage_prim)
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(RAIL_CENTER_R, 0.0, RAIL_MOUNT_Z))
            xf.AddRotateZOp().Set(180.0)  # Face toward pool center

            # Build hinge bracket (visual C-clamp)
            build_hinge_bracket(stage, carriage_path, i)
            spawned_count += 1

        carb.log_info(f"[aquasweep] Rail robots spawned for {spawned_count} pools (enabled: {enabled})")

    def _setup_rail_scenarios(self) -> None:
        """Initialize rail robot articulations and scenarios."""
        from isaacsim.core.prims import SingleArticulation

        stage = get_current_stage()

        for i in range(1, _NUM_ROBOTS + 1):
            pool_path = f"{POOLS_ROOT}/Pool_{i}"
            carriage_path = f"{pool_path}/RailRobot/Carriage"

            if not stage.GetPrimAtPath(carriage_path).IsValid():
                carb.log_warn(f"[aquasweep] Pool_{i} rail carriage not found, skipping")
                continue

            articulation = None
            try:
                articulation = SingleArticulation(
                    prim_path=carriage_path,
                    name=f"rail_robot_{i}",
                )
                World.instance().scene.add(articulation)
            except Exception as e:
                carb.log_warn(f"[aquasweep] Pool_{i} rail articulation failed: {e}")

            # Initialize scenario (index is 0-based)
            idx = i - 1
            self._rail_scenarios[idx].initialize(stage, articulation, carriage_path)

            # Build revolute joint and scraper tool
            joint_path = build_revolute_joint(stage, pool_path, i)
            if joint_path:
                self._rail_scenarios[idx].set_joint_drive(joint_path)
            build_scraper_tool(stage, carriage_path, i, articulation=articulation)

            # Create ROS2 bridge for joint state publishing + step_sync
            bridge = create_rail_bridge(f"rail_robot_{i}", f"pool_{i}")
            if bridge is not None:
                self._rail_scenarios[idx].set_bridge(bridge)
                if self._ros_executor is not None:
                    self._ros_executor.add_node(bridge)
            self._rail_bridges[idx] = bridge

        carb.log_info(f"[aquasweep] Rail robot scenarios initialized for {_NUM_ROBOTS} pools")

        # CleanWall action server는 aqua_controller에서 제공
        # (Isaac Sim 내부 action server는 비활성화 — 중복 방지)
        # self._init_clean_wall_servers()

    def _init_clean_wall_servers(self) -> None:
        """Initialize CleanWall action servers for enabled pools only."""
        if self._clean_wall_server is not None:
            self._clean_wall_server.cleanup()

        # 활성화된 풀만 action server 생성
        enabled = RAIL_ROBOT_ENABLED_POOLS
        if enabled is not None and len(enabled) == 0:
            carb.log_info("[aquasweep] CleanWall servers disabled (no enabled pools)")
            return

        self._clean_wall_server = create_clean_wall_manager()
        if self._clean_wall_server is None:
            carb.log_warn("[aquasweep] CleanWall action server manager not available")
            return

        # enabled가 None이면 모든 풀, 아니면 지정된 풀만
        if enabled is None:
            pool_ids = [f"pool_{i+1}" for i in range(_NUM_ROBOTS)]
            scenarios = self._rail_scenarios
        else:
            pool_ids = [f"pool_{i}" for i in enabled]
            scenarios = [self._rail_scenarios[i-1] for i in enabled if i-1 < len(self._rail_scenarios)]

        success = self._clean_wall_server.initialize(
            self._ros_executor,
            pool_ids,
            scenarios,
        )
        if success:
            carb.log_info(f"[aquasweep] CleanWall action servers ready for: {pool_ids}")
        else:
            carb.log_warn("[aquasweep] CleanWall action servers failed to initialize")

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

        # Initialize rail robot scenarios
        self._setup_rail_scenarios()

        self._water_scenario.teardown_scenario()
        self._water_scenario.setup_scenario(stage=get_current_stage())

        for suction in self._suctions:
            suction.reset()
        reset_center_trail_debug()

        _set_viewport_lighting_mode("stage")

        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        self._reset_btn.enabled = True
        self._spawn_debris_btn.enabled = True
        self._publish_cams_btn.enabled = True

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
        if hasattr(self, "_suction_label") and self._suction_label is not None:
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
        """매 physics step — 스러스터 힘 인가 + 이물질 흡입 + 레일 로봇 업데이트.

        water_scenario.update_scenario()는 on_physics_step()에서 항상 실행되므로 여기선 생략.
        """
        # Update underwater robot scenarios
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
                    if newly > 0 and self._suction_label is not None:
                        total = sum(s.collected_count for s in self._suctions)
                        self._suction_label.text = f"{total} 개"
            except Exception:
                pass

        # Update rail robot scenarios — moved to on_physics_step() (every physics tick)

    def _on_spawn_debris(self):
        if self._debris_scenario.is_spawned():
            return
        lo = self._debris_count_min_model.get_value_as_int()
        hi = self._debris_count_max_model.get_value_as_int()
        radius = self._debris_radius_model.get_value_as_float()
        self._debris_scenario.setup_scenario(count_range=(lo, hi), radius=radius)

    def _on_clear_debris(self):
        self._debris_scenario.teardown_scenario()

    def _on_publish_cams(self):
        """Publish all cameras (top + under)."""
        carb.log_info("[aquasweep] PUBLISH CAMS: starting...")

        # 1. Publish per-pool top cameras
        if _TOP_CAM_AVAILABLE:
            entries = discover_top_cameras()
            if entries:
                ok, msg = top_graph.build_graph(entries, resolution=TOP_CAM_RESOLUTION)
                carb.log_info(f"[aquasweep] PUBLISH CAMS: top cameras {'OK' if ok else 'FAIL'} - {msg}")
            else:
                carb.log_warn("[aquasweep] PUBLISH CAMS: no top cameras found")
        else:
            carb.log_warn("[aquasweep] PUBLISH CAMS: top_cam_ext not available")

        # 2. Publish under cameras
        if _UNDER_CAM_AVAILABLE:
            entries = discover_under_cameras()
            if entries:
                ok, msg = under_graph.build_graph(entries)
                carb.log_info(f"[aquasweep] PUBLISH CAMS: under cameras {'OK' if ok else 'FAIL'} - {msg}")
            else:
                carb.log_warn("[aquasweep] PUBLISH CAMS: no under cameras found")
        else:
            carb.log_warn("[aquasweep] PUBLISH CAMS: under_cam_ext not available")

        carb.log_info("[aquasweep] PUBLISH CAMS: done")

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
            pool_id    = f"pool_{i + 1}"
            try:
                receiver = create_cmd_vel_receiver(robot_name, pool_id)
                if receiver is not None:
                    self._ros_executor.add_node(receiver)
                    self._cmd_receivers[i] = receiver
                    carb.log_warn(f"[aquasweep] robot_{i+1} cmd_vel 구독 + step_sync 발행 시작 → /{robot_name}/cmd_vel, /{pool_id}/step_sync")
                else:
                    carb.log_warn(f"[aquasweep] robot_{i+1} receiver 생성 실패: {get_last_ros_import_error()}")
            except Exception as exc:
                carb.log_warn(f"[aquasweep] robot_{i+1} receiver 오류: {exc}")

        # 내부 플래너 모드: MotionCommandBridge 생성 및 Scenario 연결
        if USE_INTERNAL_PLANNER:
            self._init_motion_bridges()

        self._ros_thread = threading.Thread(
            target=self._ros_executor.spin,
            daemon=True,
            name="aquasweep_ros_spin",
        )
        self._ros_thread.start()
        carb.log_warn(f"[aquasweep] ROS spin thread 시작 완료")

    def _init_motion_bridges(self) -> None:
        """내부 플래너 모드: MotionCommandBridge 생성 및 Scenario 연결."""
        try:
            from motion_command_bridge import create_motion_bridge
        except ImportError as e:
            carb.log_warn(f"[aquasweep] MotionCommandBridge import 실패: {e}")
            return

        self._floor_bridges = []
        self._wall_bridges = []

        # CleanFloor 브릿지 (underwater robot용)
        for i in range(_NUM_ROBOTS):
            pool_id = f"pool_{i + 1}"
            try:
                bridge = create_motion_bridge(pool_id, "clean_floor")
                if bridge is not None:
                    self._ros_executor.add_node(bridge)
                    if i < len(self._scenarios):
                        self._scenarios[i].set_motion_bridge(bridge)
                    self._floor_bridges.append(bridge)
                    carb.log_warn(f"[aquasweep] {pool_id} CleanFloor MotionBridge 생성 완료")
            except Exception as e:
                carb.log_warn(f"[aquasweep] {pool_id} CleanFloor MotionBridge 생성 실패: {e}")

        # CleanWall 브릿지 (rail robot용)
        enabled_pools = RAIL_ROBOT_ENABLED_POOLS or list(range(1, _NUM_ROBOTS + 1))
        for pool_idx in enabled_pools:
            if pool_idx < 1 or pool_idx > _NUM_ROBOTS:
                continue
            pool_id = f"pool_{pool_idx}"
            try:
                bridge = create_motion_bridge(pool_id, "clean_wall")
                if bridge is not None:
                    self._ros_executor.add_node(bridge)
                    # rail_scenarios 인덱스는 enabled_pools 기준
                    scenario_idx = enabled_pools.index(pool_idx)
                    if scenario_idx < len(self._rail_scenarios):
                        self._rail_scenarios[scenario_idx].set_motion_bridge(bridge)
                    self._wall_bridges.append(bridge)
                    carb.log_warn(f"[aquasweep] {pool_id} CleanWall MotionBridge 생성 완료")
            except Exception as e:
                carb.log_warn(f"[aquasweep] {pool_id} CleanWall MotionBridge 생성 실패: {e}")

    def _stop_ros(self) -> None:
        if self._ros_executor is not None:
            self._ros_executor.shutdown(timeout_sec=1.0)
            self._ros_executor = None
        self._cmd_receivers = [None] * _NUM_ROBOTS
        self._floor_bridges = []
        self._wall_bridges = []

    def _on_trail_on(self):
        _uw_gv.DEBUG_CENTER_TRAIL_ENABLED = True

    def _on_trail_off(self):
        _uw_gv.DEBUG_CENTER_TRAIL_ENABLED = False
        reset_center_trail_debug()

    def _on_water_current_on(self):
        for i, scenario in enumerate(self._scenarios):
            center = _POOL_CENTERS[i] if i < len(_POOL_CENTERS) else (0.0, 0.0)
            scenario.set_water_current(True, omega=WATER_ROTATION_OMEGA, center=center)

    def _on_water_current_off(self):
        for scenario in self._scenarios:
            scenario.set_water_current(False)

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
        if hasattr(self, "_spawn_debris_btn"):
            self._spawn_debris_btn.enabled = False
        if hasattr(self, "_publish_cams_btn"):
            self._publish_cams_btn.enabled = False
