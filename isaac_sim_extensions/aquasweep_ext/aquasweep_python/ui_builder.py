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
from underwater_robot_python.actiongraph_setup import remove_cmd_vel_graph
from underwater_robot_python.suction_system import SuctionSystem
from underwater_robot_python.trail_debug import reset_center_trail_debug, tick_center_trail_debug
from .sturgeon_animation_service import SturgeonAnimationService
from .robot_activation_service import RobotActivationService, RobotSpec
from underwater_robot_python.global_variables import (
    DEBUG_CENTER_TRAIL_ENABLED,
    DEBUG_ENABLE_SUCTION,
    HIPPO_USD_FILENAME,
    HIPPO_WHEEL_BASE_M,
    HIPPO_WHEEL_RADIUS_M,
    ROBOT_SPAWN_Z_M,
)

# Top Camera integration (per-pool publishing)
from top_camera_python.ros_graph_builder import (
    build_graph as build_top_cam_graph,
    teardown_graph as teardown_top_cam_graph,
    graph_exists as top_cam_graph_exists,
)
from top_camera_python.camera_discovery import discover_top_cameras
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
        # Stop robot activation ROS2 service
        if self._robot_activation_service is not None:
            self._robot_activation_service.stop()
            self._robot_activation_service = None

    # ── UI 빌드 ───────────────────────────────────────────────────────────────

    def build_ui(self):
        # ── 1. World Controls ─────────────────────────────────────────────────
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

        # ── 2. Debris (토글 스타일) ────────────────────────────────────────────
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
                self._debris_toggle_btn = ui.Button(
                    "SPAWN", height=36, clicked_fn=self._on_debris_toggle_click,
                    style={"background_color": 0xFF1A6B2E},
                )

        # ── 3. Run Scenario ────────────────────────────────────────────────────
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

        # ── 4. Sturgeon Animation (토글 스타일) ─────────────────────────────────
        sturgeon_frame = CollapsableFrame("Sturgeon Animation", collapsed=False)
        with sturgeon_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                with ui.HStack(height=28):
                    ui.Label("상태:", width=50)
                    self._sturgeon_status_label = ui.Label("Paused", width=80,
                        style={"color": 0xFF8B4513})
                self._sturgeon_toggle_btn = ui.Button(
                    "RESUME", height=32, clicked_fn=self._on_sturgeon_toggle_click,
                    style={"background_color": 0xFF2E8B57},
                )
                self._sturgeon_toggle_btn.enabled = False  # RUN 전까지 비활성화
                ui.Label("CLI: ros2 service call /sturgeon/resume std_srvs/srv/Trigger",
                         style={"font_size": 10, "color": 0xFF888888})

        # ── 5. Robot Activation (개별 토글) ────────────────────────────────────
        robot_frame = CollapsableFrame("Robot Activation", collapsed=False)
        with robot_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                ui.Label("Toggle to activate/deactivate each robot:", style={"font_size": 11})
                
                # Robot toggles (row 1: 1-4)
                self._robot_toggle_btns: dict[int, ui.Button] = {}
                with ui.HStack(spacing=4, height=32):
                    for pool_id in range(1, 5):
                        btn = ui.Button(
                            f"Pool {pool_id}", height=28, width=65,
                            clicked_fn=lambda pid=pool_id: self._on_robot_toggle_click(pid),
                            style={"background_color": 0xFF555555},  # OFF state (gray)
                        )
                        btn.enabled = False  # RUN 전까지 비활성화
                        self._robot_toggle_btns[pool_id] = btn
                
                # Robot toggles (row 2: 5-7)
                with ui.HStack(spacing=4, height=32):
                    for pool_id in range(5, _NUM_ROBOTS + 1):
                        btn = ui.Button(
                            f"Pool {pool_id}", height=28, width=65,
                            clicked_fn=lambda pid=pool_id: self._on_robot_toggle_click(pid),
                            style={"background_color": 0xFF555555},  # OFF state (gray)
                        )
                        btn.enabled = False  # RUN 전까지 비활성화
                        self._robot_toggle_btns[pool_id] = btn
                
                ui.Label("(Green = Active, Gray = Inactive)", 
                         style={"font_size": 10, "color": 0xFF888888})
                ui.Label("CLI: ros2 service call /pool_1/activate_robot std_srvs/srv/Trigger",
                         style={"font_size": 10, "color": 0xFF888888})

        # ── 6. Suction Status ──────────────────────────────────────────────────
        suction_frame = CollapsableFrame("Suction Status", collapsed=True)
        with suction_frame:
            with ui.VStack(style=get_style(), spacing=4, height=0):
                with ui.HStack(height=22):
                    ui.Label("수거 완료", width=90)
                    self._suction_label = ui.Label("0 개")

        # ── 7. Top Camera (per-pool) ───────────────────────────────────────────
        topcam_frame = CollapsableFrame("Top Camera", collapsed=False)
        with topcam_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                ui.Label("Per-pool cameras (~8fps each)", style={"font_size": 11})
                ui.Label("Topics: /pool_1/top_img_raw, /pool_2/top_img_raw, ...", 
                         style={"font_size": 10, "color": 0xFF888888})
                with ui.HStack(height=28):
                    ui.Label("상태:", width=50)
                    self._topcam_status_label = ui.Label("Idle", width=100,
                        style={"color": 0xFF888888})
                self._topcam_toggle_btn = ui.Button(
                    "START PUBLISHING", height=32, clicked_fn=self._on_topcam_toggle_click,
                    style={"background_color": 0xFF2E8B57},
                )
                self._topcam_toggle_btn.enabled = False  # RUN 전까지 비활성화
                ui.Label("CLI: (Extension) top_cam_ext → Build selected cameras",
                         style={"font_size": 10, "color": 0xFF888888})

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    def _on_init(self):
        self._water_scenario = WaterTankScenario()
        self._debris_scenario = DebrisScenario()
        # Each pool has its own debris particles path
        self._suctions = [
            SuctionSystem(particles_prim_path=f"/World/Pools/Pool_{i+1}/Debris/Particles")
            for i in range(_NUM_ROBOTS)
        ]
        self._sturgeon_service: SturgeonAnimationService | None = None
        self._robot_activation_service: RobotActivationService | None = None
        
        # Robot activation state tracking (per-robot toggle state)
        self._robot_toggle_models: dict[int, ui.SimpleBoolModel] = {
            pool_id: ui.SimpleBoolModel(False) for pool_id in range(1, _NUM_ROBOTS + 1)
        }
        
        # Top camera state
        self._topcam_publishing = False
        
        # Simulation running state (for UI enable/disable)
        self._is_running = False

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

        # Robot activation ROS2 service 시작
        if self._robot_activation_service is None:
            robot_specs = {
                f"pool_{idx}": RobotSpec(
                    idx=idx,
                    scene_name=scene_name,
                    spawn_path=spawn_path,
                    robot_root_path=robot_root,
                    wheel_radius=HIPPO_WHEEL_RADIUS_M,
                    wheel_base=HIPPO_WHEEL_BASE_M,
                )
                for idx, scene_name, spawn_path, robot_root, _pos in _robot_specs()
            }
            self._robot_activation_service = RobotActivationService(robot_specs)
        self._robot_activation_service.start()

        # Sturgeon 기본 상태: Paused (성능 최적화)
        self._sturgeon_service.pause()

        for suction in self._suctions:
            suction.reset()
        reset_center_trail_debug()

        _set_viewport_lighting_mode("stage")  # 고정된 Stage 조명 사용 (Camera Light 비활성화)

        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        self._reset_btn.enabled = True
        
        # RUN 전까지 컨트롤 비활성화 상태 유지
        self._is_running = False

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
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = True
        
        # Reset debris state on RESET button click
        if hasattr(self, "_debris_toggle_btn"):
            self._debris_scenario = DebrisScenario()
            self._sync_debris_button_state()

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

    def _on_debris_toggle_click(self):
        """Toggle debris spawn/clear."""
        try:
            if self._debris_scenario.is_spawned():
                self._debris_scenario.teardown_scenario()
            else:
                lo = self._debris_count_min_model.get_value_as_int()
                hi = self._debris_count_max_model.get_value_as_int()
                radius = self._debris_radius_model.get_value_as_float()
                self._debris_scenario.setup_scenario(count_range=(lo, hi), radius=radius)
        except Exception as e:
            carb.log_error(f"[aquasweep] debris toggle error: {e}")
        
        # Always sync button state with actual scenario state
        self._sync_debris_button_state()
    
    def _sync_debris_button_state(self):
        """Sync debris button UI with actual scenario state."""
        if self._debris_scenario.is_spawned():
            self._debris_toggle_btn.text = "CLEAR"
            self._debris_toggle_btn.set_style({"background_color": 0xFF6B1A1A})
        else:
            self._debris_toggle_btn.text = "SPAWN"
            self._debris_toggle_btn.set_style({"background_color": 0xFF1A6B2E})

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

        # ActionGraph creation is now handled by RobotActivationService
        # via /{pool_id}/activate_robot service call from planner
        # (no longer auto-created on RUN button click)

        self._timeline.play()
        
        # 시뮬레이션 시작 → 컨트롤 활성화
        self._is_running = True
        self._enable_runtime_controls(True)

    def _on_stop(self):
        self._timeline.pause()
        
        # 시뮬레이션 정지 → 컨트롤 비활성화
        self._is_running = False
        self._enable_runtime_controls(False)

    # ── 런타임 컨트롤 활성화/비활성화 ─────────────────────────────────────────

    def _enable_runtime_controls(self, enabled: bool):
        """Enable/disable controls that require simulation to be running."""
        # Sturgeon toggle
        if hasattr(self, "_sturgeon_toggle_btn"):
            self._sturgeon_toggle_btn.enabled = enabled
        
        # Robot toggles
        if hasattr(self, "_robot_toggle_btns"):
            for btn in self._robot_toggle_btns.values():
                btn.enabled = enabled
        
        # Top camera toggle
        if hasattr(self, "_topcam_toggle_btn"):
            self._topcam_toggle_btn.enabled = enabled

    # ── ROS2 서비스 UI 핸들러 ─────────────────────────────────────────────────

    def _on_sturgeon_toggle_click(self):
        """Toggle sturgeon animation pause/resume."""
        if not self._is_running:
            carb.log_warn("[aquasweep] Simulation not running")
            return
        if self._sturgeon_service is None or not self._sturgeon_service.available:
            carb.log_warn("[aquasweep] Sturgeon service not available")
            return
        
        if self._sturgeon_service.is_paused:
            # Currently paused → Resume
            success, message = self._sturgeon_service.resume()
            if success:
                self._sturgeon_status_label.text = "Running"
                self._sturgeon_status_label.set_style({"color": 0xFF2E8B57})
                self._sturgeon_toggle_btn.text = "PAUSE"
                self._sturgeon_toggle_btn.set_style({"background_color": 0xFF8B4513})
                carb.log_info(f"[aquasweep] {message}")
        else:
            # Currently running → Pause
            success, message = self._sturgeon_service.pause()
            if success:
                self._sturgeon_status_label.text = "Paused"
                self._sturgeon_status_label.set_style({"color": 0xFF8B4513})
                self._sturgeon_toggle_btn.text = "RESUME"
                self._sturgeon_toggle_btn.set_style({"background_color": 0xFF2E8B57})
                carb.log_info(f"[aquasweep] {message}")

    # ── Robot Activation 핸들러 (개별 토글) ────────────────────────────────────

    def _on_robot_toggle_click(self, pool_id: int):
        """Toggle a single robot's activation state."""
        if not self._is_running:
            carb.log_warn("[aquasweep] Simulation not running")
            return
        if self._robot_activation_service is None or not self._robot_activation_service.available:
            carb.log_warn("[aquasweep] Robot activation service not available")
            return
        
        pool_key = f"pool_{pool_id}"
        is_active = self._robot_toggle_models[pool_id].get_value_as_bool()
        btn = self._robot_toggle_btns[pool_id]
        
        if is_active:
            # Currently active → Deactivate
            success, message = self._robot_activation_service.deactivate(pool_key)
            if success:
                self._robot_toggle_models[pool_id].set_value(False)
                btn.set_style({"background_color": 0xFF555555})  # Gray (inactive)
                carb.log_info(f"[aquasweep] {message}")
            else:
                carb.log_warn(f"[aquasweep] {message}")
        else:
            # Currently inactive → Activate
            success, message = self._robot_activation_service.activate(pool_key)
            if success:
                self._robot_toggle_models[pool_id].set_value(True)
                btn.set_style({"background_color": 0xFF2E8B57})  # Green (active)
                carb.log_info(f"[aquasweep] {message}")
            else:
                carb.log_warn(f"[aquasweep] {message}")

    # ── Top Camera 핸들러 (per-pool) ───────────────────────────────────────────

    def _on_topcam_toggle_click(self):
        """Toggle top camera publishing (per-pool cameras)."""
        if not self._is_running:
            carb.log_warn("[aquasweep] Simulation not running")
            return
        
        if self._topcam_publishing:
            # Currently publishing → Stop
            teardown_top_cam_graph()
            self._topcam_publishing = False
            self._topcam_status_label.text = "Stopped"
            self._topcam_status_label.set_style({"color": 0xFF888888})
            self._topcam_toggle_btn.text = "START PUBLISHING"
            self._topcam_toggle_btn.set_style({"background_color": 0xFF2E8B57})
            carb.log_info("[aquasweep] Top camera publishing stopped")
        else:
            # Currently stopped → Start (per-pool cameras)
            entries = discover_top_cameras()
            if not entries:
                carb.log_warn("[aquasweep] No top cameras found. Run LOAD first.")
                self._topcam_status_label.text = "Error: No cameras found"
                self._topcam_status_label.set_style({"color": 0xFFFF4444})
                return
            
            success, message = build_top_cam_graph(entries)
            if success:
                self._topcam_publishing = True
                self._topcam_status_label.text = f"Publishing {len(entries)} cameras"
                self._topcam_status_label.set_style({"color": 0xFF2E8B57})
                self._topcam_toggle_btn.text = "STOP PUBLISHING"
                self._topcam_toggle_btn.set_style({"background_color": 0xFF8B4513})
                carb.log_info(f"[aquasweep] {message}")
            else:
                carb.log_warn(f"[aquasweep] {message}")
                self._topcam_status_label.text = f"Error: {message}"
                self._topcam_status_label.set_style({"color": 0xFFFF4444})

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False
        
        # Reset debris button to match fresh DebrisScenario state
        if hasattr(self, "_debris_toggle_btn"):
            self._sync_debris_button_state()
