"""Scenario: drive the water-physics loop + OceanSim UW_Camera."""
import carb

from . import oceansim_camera as _ocam
from .physics_applier import WaterPhysicsApplier


class WaterTankScenario:
    def __init__(self):
        self._running_scenario = False
        self._physics = WaterPhysicsApplier()
        self._uw_cam = None
        self._turbidity = "medium"

    def setup_scenario(self, stage=None, **_ignored):
        if stage is not None:
            self._physics.discover_bodies(stage)
            self._init_uw_camera(stage)
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
