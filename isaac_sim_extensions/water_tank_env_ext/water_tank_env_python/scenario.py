"""Scenario: drive the water-physics loop + OceanSim UW_Camera."""
import carb

from . import oceansim_camera as _ocam
from .physics_applier import WaterPhysicsApplier
from .sturgeon_animator import SturgeonAnimator
from .water_surface_animator import WaterSurfaceAnimator


class WaterTankScenario:
    def __init__(self):
        self._running_scenario = False
        self._physics = WaterPhysicsApplier()
        self._surface_anim = WaterSurfaceAnimator()
        self._sturgeon_anim = SturgeonAnimator()
        self._uw_cam = None
        self._turbidity = "medium"

    def setup_scenario(self, stage=None, **_ignored):
        if stage is not None:
            self._physics.discover_bodies(stage)
            self._init_uw_camera(stage)
        self._surface_anim.reset()
        self._sturgeon_anim.reset()
        self._running_scenario = True

    def teardown_scenario(self):
        self._running_scenario = False
        self._close_uw_camera()

    def is_loaded(self) -> bool:
        return self._running_scenario

    @property
    def sturgeon_animator(self) -> SturgeonAnimator:
        """SturgeonAnimator 인스턴스 반환 (외부 서비스 연결용)."""
        return self._sturgeon_anim

    def update_scenario(self, step: float):
        from underwater_robot_python.global_variables import (
            DEBUG_ENABLE_WATER_PHYSICS,
            DEBUG_ENABLE_STURGEON_ANIM,
            DEBUG_ENABLE_WATER_SURFACE_ANIM,
        )

        if not self._running_scenario:
            return

        if DEBUG_ENABLE_WATER_PHYSICS:
            self._physics.apply(step)
        if DEBUG_ENABLE_WATER_SURFACE_ANIM:
            self._surface_anim.step(step)
        if DEBUG_ENABLE_STURGEON_ANIM:
            self._sturgeon_anim.step(step)

        if self._uw_cam is not None:
            try:
                self._uw_cam.render()
            except Exception:
                pass

    def set_turbidity(self, turbidity: str, stage=None) -> None:
        self._turbidity = turbidity
        self._close_uw_camera()
        if stage is not None:
            self._init_uw_camera(stage)

    def _init_uw_camera(self, stage) -> None:
        # OceanSim UW_Camera 비활성화 (렌더링 성능 최적화)
        # 다시 활성화하려면 아래 return 주석 처리
        carb.log_info("[water_tank_env] OceanSim UW_Camera 비활성화됨 (성능 최적화)")
        return
        
        if not _ocam.OCEANSIM_AVAILABLE:
            return
        paths = _ocam.discover_camera_prims(stage)
        if not paths:
            carb.log_info("[water_tank_env] stage에 Camera prim 없음 — UW_Camera 건너뜀")
            return
        try:
            self._uw_cam = _ocam.create_uw_camera(paths[0], self._turbidity)
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
