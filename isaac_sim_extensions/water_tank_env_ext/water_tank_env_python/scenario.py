"""Scenario: drive the water-physics loop + OceanSim UW_Camera."""
import carb

from . import oceansim_camera as _ocam
from .physics_applier import WaterPhysicsApplier

# perception_node.py가 구독하는 ROS2 토픽 — 탁도 적용된 이미지를 여기로 발행
ROS2_IMAGE_TOPIC = "/cleaner/camera/image_raw"


class WaterTankScenario:
    _instance = None

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __init__(self):
        WaterTankScenario._instance = self
        self._running_scenario = False
        self._physics = WaterPhysicsApplier()
        self._uw_cam = None
        self._turbidity = "medium"

    def setup_scenario(self, stage=None, **_ignored):
        if stage is not None:
            self._physics.discover_bodies(stage)
        self._running_scenario = True

    def teardown_scenario(self):
        self._running_scenario = False
        self._close_uw_camera()

    def is_loaded(self) -> bool:
        return self._running_scenario

    def update_scenario(self, step: float):
        if not self._running_scenario:
            return
        self._physics.apply(step)
        self.render_camera()

    def render_camera(self):
        """매 프레임마다 탁도 카메라 화면 갱신 및 ROS2 토픽 발행 (지연 초기화 적용)"""
        if not self._running_scenario:
            return

        # [지연 초기화] 처음 실행 시점에 안전하게 카메라를 개설
        if self._uw_cam is None:
            from isaacsim.core.utils.stage import get_current_stage
            stage = get_current_stage()
            if stage is not None:
                self._init_uw_camera(stage)

        if self._uw_cam is not None:
            try:
                self._uw_cam.render()
            except Exception as e:
                import traceback
                import carb
                carb.log_error(f"[water_tank_env] UW_Camera render 실패: {e}")
                traceback.print_exc()

    def set_turbidity(self, turbidity: str, stage=None) -> None:
        self._turbidity = turbidity
        self._close_uw_camera()
        # 이전에 실행 중이었다면 바로 재초기화
        if self._running_scenario and stage is not None:
            self._init_uw_camera(stage)

    def _init_uw_camera(self, stage) -> None:
        if not _ocam.OCEANSIM_AVAILABLE:
            return

        # 1순위: 로봇의 실제 전방 카메라 prim 경로 지정
        robot_cam_path = "/World/Dingo/dingo/base_link/camera"
        target_path = None

        if stage.GetPrimAtPath(robot_cam_path).IsValid():
            target_path = robot_cam_path
        else:
            # 2순위: 로봇 카메라가 아직 준비 안 되었거나 경로가 다르면 탐색
            paths = _ocam.discover_camera_prims(stage)
            if paths:
                # 뷰포트용 카메라는 배제하고 최우선으로 로봇 측 카메라 경로 찾기
                for p in paths:
                    if "dingo" in p.lower() or "camera" in p.lower():
                        target_path = p
                        break
                if target_path is None:
                    target_path = paths[0]

        if target_path is None:
            carb.log_info("[water_tank_env] stage에 유효한 Camera prim 없음 — UW_Camera 건너뜀")
            return

        try:
            self._uw_cam = _ocam.create_uw_camera(
                target_path, self._turbidity,
                ros2_topic_name=ROS2_IMAGE_TOPIC,
            )
            print(f"📷 [water_tank_env] UW_Camera 지연 생성 완료 ({target_path}) → ROS2: {ROS2_IMAGE_TOPIC}")
        except Exception as e:
            carb.log_warn(f"[water_tank_env] OceanSim UW_Camera 초기화 실패: {e}")
            self._uw_cam = None

    def _close_uw_camera(self) -> None:
        if self._uw_cam is not None:
            try:
                self._uw_cam.close()
            except Exception:
                pass
            self._uw_cam = None
