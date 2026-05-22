"""이물질 파티클 시나리오 — 스폰/클리어 생명주기 관리."""
import importlib

from isaacsim.core.utils.stage import get_current_stage

from .debris_system import DebrisSystem
from . import global_variables as gv


def _resolve_pool_centers() -> list[tuple[float, float]]:
    """Pull POOL_CENTERS from water_tank_env_ext; fall back to single origin pool."""
    try:
        params = importlib.import_module("water_tank_env_python.params")
        centers = list(getattr(params, "POOL_CENTERS", []))
        return centers if centers else [(0.0, 0.0)]
    except ImportError:
        return [(0.0, 0.0)]


class DebrisScenario:
    def __init__(self):
        self._debris: DebrisSystem | None = None

    def setup_scenario(
        self,
        count_range: tuple[int, int] | None = None,
        radius: float | None = None,
    ) -> None:
        stage = get_current_stage()
        self._debris = DebrisSystem(
            count_range=count_range if count_range is not None
                       else (gv.DEBRIS_COUNT_MIN, gv.DEBRIS_COUNT_MAX),
            radius=radius if radius is not None else gv.DEBRIS_RADIUS,
            color_hex=gv.DEBRIS_COLOR_HEX,
            tank_range=gv.TANK_RANGE,
            z_floor=gv.FLOOR_Z,
            pool_centers=_resolve_pool_centers(),
        )
        self._debris.spawn(stage)

    def teardown_scenario(self) -> None:
        if self._debris is None:
            return
        stage = get_current_stage()
        if stage is not None:
            self._debris.clear(stage)
        self._debris = None

    def is_spawned(self) -> bool:
        return self._debris is not None and self._debris.is_spawned

    def update_scenario(self, step: float) -> None:
        pass
