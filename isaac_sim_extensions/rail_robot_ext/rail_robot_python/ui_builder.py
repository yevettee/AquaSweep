"""Rail Robot UI builder — 각 원형 수조마다 레일 협동로봇을 배치·제어."""

import math
from pathlib import Path

import carb
import omni.timeline
import omni.ui as ui
from isaacsim.core.api.world import World
from isaacsim.core.utils.stage import get_current_stage
from isaacsim.examples.extension.core_connectors import LoadButton, ResetButton
from isaacsim.gui.components.element_wrappers import CollapsableFrame, StateButton
from isaacsim.gui.components.ui_utils import get_style
from omni.usd import StageEventType
from pxr import Gf, UsdGeom

from .global_variables import (
    COBOT_USD_PATH,
    EXTENSION_TITLE,
    RAIL_CENTER_R,
    RAIL_MOUNT_Z,
)
from .scenario import RailRobotScenario
from .joint_state_bridge import create_bridge
from .rail_builder import build_rails, build_hinge_bracket, build_revolute_joint, build_scraper_tool

PHYSICS_DT = 1.0 / 60.0
POOLS_ROOT = "/World/Pools"


def _carriage_path(pool_idx: int) -> str:
    return f"{POOLS_ROOT}/Pool_{pool_idx}/RailRobot/Carriage"


def _pool_centers() -> list[tuple[float, float]]:
    try:
        from water_tank_env_python import params as _p
        return list(_p.POOL_CENTERS)
    except ImportError:
        return [(0.0, 0.0)]  # standalone: 수조 1개


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()
        self._on_init()

    # ── extension.py 자동 콜백 ────────────────────────────────────────────────

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            self._scenario_state_btn.reset()
            self._scenario_state_btn.enabled = False

    def on_physics_step(self, step: float):
        for scenario in self._scenarios:
            scenario.on_physics_step(step)

    def on_stage_event(self, event):
        if event.type == int(StageEventType.OPENED):
            self._reset_extension()

    def cleanup(self):
        for ui_elem in self.wrapped_ui_elements:
            ui_elem.cleanup()
        for bridge in self._bridges:
            if bridge is not None:
                try:
                    bridge.destroy_node()
                except Exception:
                    pass
        self._bridges.clear()

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
                    pre_reset_fn=self._on_pre_reset_btn,
                    post_reset_fn=self._on_post_reset_btn,
                )
                self._reset_btn.enabled = False
                self.wrapped_ui_elements.append(self._reset_btn)

        run_frame = CollapsableFrame("청소 제어", collapsed=False)
        with run_frame:
            with ui.VStack(style=get_style(), spacing=5, height=0):
                self._scenario_state_btn = StateButton(
                    "Run Scenario", "RUN — 전체 수조 청소 시작", "STOP",
                    on_a_click_fn=self._on_run_scenario_a_text,
                    on_b_click_fn=self._on_run_scenario_b_text,
                    physics_callback_fn=self._update_scenario,
                )
                self._scenario_state_btn.enabled = False
                self.wrapped_ui_elements.append(self._scenario_state_btn)

        status_frame = CollapsableFrame("로봇 상태", collapsed=False)
        with status_frame:
            with ui.VStack(style=get_style(), spacing=3, height=0):
                self._status_label = ui.Label("로드 대기 중...")

    # ── scene / scenario 설정 ─────────────────────────────────────────────────

    def _setup_scene(self) -> None:
        """LOAD — 각 수조 Pool Xform 아래에 캐리지 prim 생성 후 cobot USD 참조."""
        if not Path(COBOT_USD_PATH).is_file():
            carb.log_error(f"[{EXTENSION_TITLE}] Cobot USD 없음: {COBOT_USD_PATH}")
            return

        stage = get_current_stage()
        centers = _pool_centers()

        # /World/Pools 와 Pool_n Xform 이 아직 없으면 (standalone 실행) 직접 생성
        if not stage.GetPrimAtPath(POOLS_ROOT).IsValid():
            UsdGeom.Xform.Define(stage, POOLS_ROOT)
        for i, (cx, cy) in enumerate(centers, start=1):
            pool_path = f"{POOLS_ROOT}/Pool_{i}"
            if not stage.GetPrimAtPath(pool_path).IsValid():
                xf = UsdGeom.Xform.Define(stage, pool_path)
                UsdGeom.Xformable(xf).AddTranslateOp().Set(Gf.Vec3d(cx, cy, 0.0))

        # 수조 상단 원형 레일 메시 생성 (수조 벽 상단에 설치)
        build_rails(stage, POOLS_ROOT)

        for i in range(1, len(centers) + 1):
            pool_path = f"{POOLS_ROOT}/Pool_{i}"
            rail_path = f"{pool_path}/RailRobot"
            cpath = f"{rail_path}/Carriage"

            if stage.GetPrimAtPath(cpath).IsValid():
                continue  # 이미 로드됨 (hot-reload)

            stage.DefinePrim(rail_path, "Xform")
            carriage_prim = stage.DefinePrim(cpath, "Xform")
            carriage_prim.GetReferences().AddReference(COBOT_USD_PATH)

            # 초기 위치: angle=0, 레일 중심 반경에 배치 (pool-local 좌표)
            xf = UsdGeom.Xformable(carriage_prim)
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(RAIL_CENTER_R, 0.0, RAIL_MOUNT_Z))
            xf.AddRotateZOp().Set(180.0)  # 수조 중심을 향하도록

            # C-클램프 경첩 브라켓 (캐리지 자식으로 생성)
            build_hinge_bracket(stage, cpath, i)

        carb.log_info(f"[{EXTENSION_TITLE}] {len(centers)}개 수조 레일·로봇 stage 배치 완료")

    def _setup_scenario(self) -> None:
        """LOAD 완료 후 — Articulation·Scenario·Bridge 초기화."""
        stage = get_current_stage()
        centers = _pool_centers()
        self._scenarios.clear()
        self._bridges.clear()

        loaded = 0
        for i in range(1, len(centers) + 1):
            cpath = _carriage_path(i)
            if not stage.GetPrimAtPath(cpath).IsValid():
                carb.log_warn(f"[{EXTENSION_TITLE}] Pool_{i} 캐리지 없음, 스킵")
                continue

            articulation = None
            try:
                from isaacsim.core.prims import SingleArticulation
                articulation = SingleArticulation(
                    prim_path=cpath,
                    name=f"rail_robot_{i}",
                )
                World.instance().scene.add(articulation)
            except Exception as e:
                carb.log_warn(f"[{EXTENSION_TITLE}] Pool_{i} Articulation 생성 실패: {e}")

            # pool_center=(0,0): 캐리지가 Pool Xform 하위에 있으므로 local 좌표 사용
            scenario = RailRobotScenario(pool_idx=i, pool_center=(0.0, 0.0))
            scenario.initialize(stage, articulation, cpath)

            # 경첩 RevoluteJoint 생성 및 연결
            pool_path = f"{POOLS_ROOT}/Pool_{i}"
            joint_path = build_revolute_joint(stage, pool_path, i)
            if joint_path:
                scenario.set_joint_drive(joint_path)

            # Articulation 로드 완료 후 엔드 이펙터에 스크레이퍼 장착
            build_scraper_tool(stage, cpath, i, articulation=articulation)

            bridge = create_bridge(f"rail_robot_{i}")
            if bridge is not None:
                scenario.set_bridge(bridge)
            self._bridges.append(bridge)
            self._scenarios.append(scenario)
            loaded += 1

        if hasattr(self, "_status_label"):
            self._status_label.text = f"{loaded} / {len(centers)} 수조 로봇 준비됨"

        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = (loaded > 0)
        self._reset_btn.enabled = True

    # ── 버튼 콜백 ─────────────────────────────────────────────────────────────

    def _on_pre_reset_btn(self):
        self._timeline.stop()
        for s in self._scenarios:
            s.stop()
        try:
            self._scenario_state_btn.reset()
        except AttributeError:
            pass

    def _on_post_reset_btn(self):
        self._scenarios.clear()
        self._bridges.clear()
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False

    def _update_scenario(self, step: float):
        """StateButton RUN 중 호출 — rail은 on_physics_step()에서 처리."""
        pass

    def _on_run_scenario_a_text(self):
        for s in self._scenarios:
            s.start()
        self._timeline.play()

    def _on_run_scenario_b_text(self):
        for s in self._scenarios:
            s.stop()
        self._timeline.pause()

    def _reset_extension(self):
        self._on_init()
        self._reset_ui()

    def _reset_ui(self):
        self._scenario_state_btn.reset()
        self._scenario_state_btn.enabled = False
        self._reset_btn.enabled = False

    def _on_init(self):
        self._scenarios: list[RailRobotScenario] = []
        self._bridges: list = []
