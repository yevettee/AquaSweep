"""AquaSweep 통합 UI — 수조·로봇·이물질을 단일 LOAD/RUN으로 제어한다.

cmd_vel 제어는 ActionGraph를 통해 처리됨 (rclpy import 불필요).
"""

import importlib
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

from water_tank_env_python import sturgeon_spawner
importlib.reload(sturgeon_spawner)  # hot-reload support

from debris_python.scenario import DebrisScenario

from underwater_robot_python.hippo_physics_sanitize import (
    prepare_hippo_usd_on_stage,
    tag_aquasweep_attrs,
    add_planar_constraint,
)
from underwater_robot_python.actiongraph_setup import (
    create_cmd_vel_graph,
    remove_cmd_vel_graph,
    graph_exists,
)
from underwater_robot_python.suction_system import SuctionSystem
from underwater_robot_python.trail_debug import reset_center_trail_debug, tick_center_trail_debug
from .sturgeon_animation_service import SturgeonAnimationService
from underwater_robot_python.global_variables import (
    DEBUG_CENTER_TRAIL_ENABLED,
    DEBUG_ENABLE_SUCTION,
    HIPPO_USD_FILENAME,
    HIPPO_WHEEL_BASE_M,
    HIPPO_WHEEL_RADIUS_M,
    ROBOT_SPAWN_Z_M,
)
# NOTE: ROBOT_PRIM_PATH / ROBOT_SCENE_NAME from globals are NOT imported —
# we redefine them below as aliases of the PRIMARY_ROBOT_* constants so the
# multi-robot spawn (7 hippos, one nested under each /World/Pools/Pool_<n>)
# can address the FSM-driven primary robot explicitly.

PHYSICS_DT = 1.0 / 24.0
_ROBOT_USD_PATH = (
    Path(__file__).resolve().parents[2]
    / "underwater_robot_ext" / "data" / HIPPO_USD_FILENAME
)

# ── Multi-pool robot specs ─────────────────────────────────────────────────────
from water_tank_env_python import params as _params  # noqa: E402
_POOL_CENTERS: list[tuple[float, float]] = list(getattr(_params, "POOL_CENTERS", []))
_NUM_ROBOTS = len(_POOL_CENTERS)


def _apply_viewport_performance_settings() -> None:
    """뷰포트 렌더링 성능 최적화 - ROS 카메라 품질은 유지."""
    try:
        import carb.settings
        settings = carb.settings.get_settings()
        
        # 뷰포트 해상도 스케일 50%로 낮춤
        settings.set("/app/renderer/resolution/scaleFactor", 0.5)
        
        # 추가 최적화 옵션
        settings.set("/rtx/post/aa/op", 0)  # AA 비활성화
        settings.set("/rtx/ambientOcclusion/enabled", False)  # AO 비활성화
        
        carb.log_info("[aquasweep] Viewport performance settings applied (50% scale)")
    except Exception as e:
        carb.log_warn(f"[aquasweep] Failed to apply viewport settings: {e}")


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

        self._on_init()

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
        self._water_scenario.teardown_scenario()
        reset_center_trail_debug()
        # Remove ActionGraphs for all robots
        for i in range(_NUM_ROBOTS):
            remove_cmd_vel_graph(f"under_robot_{i + 1}")
        # Stop sturgeon animation ROS2 service
        if self._sturgeon_service is not None:
            self._sturgeon_service.stop()
            self._sturgeon_service = None

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
        self._graphs_created = False
        self._sturgeon_service: SturgeonAnimationService | None = None

    def _setup_scene(self):
        _apply_viewport_performance_settings()
        stage = get_current_stage()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        scene_builders.enable_gpu_dynamics(stage)
        scene_builders.add_lighting(stage)
        scene_builders.build_building(stage)
        scene_builders.build_pools(stage)
        scene_builders.build_top_cameras(stage)
        scene_builders.build_equipment(stage)
        sturgeon_spawner.spawn_sturgeons(stage)

        # [DEBUG] Robot spawn 비활성화 - FPS 영향 테스트
        try:
            from underwater_robot_python.global_variables import DEBUG_ENABLE_ROBOT_SPAWN
            if not DEBUG_ENABLE_ROBOT_SPAWN:
                carb.log_info("[aquasweep] DEBUG_ENABLE_ROBOT_SPAWN=False, skipping robot spawn")
                return
        except ImportError:
            pass  # 플래그 없으면 정상 spawn

        if not _ROBOT_USD_PATH.is_file():
            carb.log_error(f"[aquasweep] Robot USD not found: {_ROBOT_USD_PATH}")
            return

        # WheeledRobot으로 직접 로드 (기존 방식)
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

        # Physics 설정 적용
        for _idx, scene_name, spawn_path, robot_root, _pos in _robot_specs():
            prepare_hippo_usd_on_stage(robot_root)
            tag_aquasweep_attrs(robot_root)
            add_planar_constraint(robot_root)

        self._water_scenario.teardown_scenario()
        self._water_scenario.setup_scenario(stage=get_current_stage())

        # Sturgeon animation ROS2 service 시작
        if self._sturgeon_service is None:
            self._sturgeon_service = SturgeonAnimationService(
                self._water_scenario.sturgeon_animator
            )
        self._sturgeon_service.start()

        for suction in self._suctions:
            suction.reset()
        reset_center_trail_debug()

        _set_viewport_lighting_mode("stage")  # 고정된 Stage 조명 사용 (Camera Light 비활성화)

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
        # Reset graph flag so they can be recreated on next RUN if needed
        self._graphs_created = False
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True

    def _update_scenario(self, step: float):
        """매 physics step마다 흡입 시스템을 실행.
        
        cmd_vel 제어는 ActionGraph가 자동으로 처리하고,
        수조 물리(부력, 항력, 착지 감지)는 on_physics_step()에서 항상 실행된다.
        여기서는 debris 흡입만 담당한다.
        """
        # water_scenario.update_scenario()는 on_physics_step()에서 호출됨
        # (StateButton 상태와 무관하게 항상 실행되어야 하므로)

        if not DEBUG_ENABLE_SUCTION:
            return

        for i, (_idx, scene_name, _spawn_path, _robot_root, _pos) in enumerate(_robot_specs()):
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
        # Clear selection to prevent PhysX UI errors during simulation
        # (avoids "Accessed invalid null prim" when selected prims are modified)
        try:
            import omni.usd
            ctx = omni.usd.get_context()
            if ctx:
                ctx.get_selection().clear_selected_prim_paths()
        except Exception:
            pass

        # Create ActionGraphs for all robots if not yet created
        if not self._graphs_created:
            self._create_action_graphs()

        self._timeline.play()

    def _create_action_graphs(self):
        """Create ActionGraph for each robot's cmd_vel control."""
        success_count = 0
        for idx, _scene_name, _spawn_path, robot_root, _pos in _robot_specs():
            robot_name = f"under_robot_{idx}"
            # Skip if graph already exists
            if graph_exists(robot_name):
                carb.log_info(f"[aquasweep] ActionGraph already exists for {robot_name}")
                success_count += 1
                continue
            graph_path = create_cmd_vel_graph(
                robot_prim_path=robot_root,
                robot_name=robot_name,
                wheel_radius=HIPPO_WHEEL_RADIUS_M,
                wheel_base=HIPPO_WHEEL_BASE_M,
            )
            if graph_path:
                carb.log_info(f"[aquasweep] ActionGraph created: {graph_path} for {robot_name}")
                success_count += 1
            else:
                carb.log_warn(f"[aquasweep] Failed to create ActionGraph for {robot_name}")
        
        if success_count == _NUM_ROBOTS:
            self._graphs_created = True
            carb.log_info(f"[aquasweep] All {_NUM_ROBOTS} ActionGraphs created successfully")

    def _on_stop(self):
        self._timeline.pause()

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False
