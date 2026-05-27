"""이물질 파티클 시나리오 — 스폰/클리어 생명주기 관리."""
import importlib

from isaacsim.core.utils.stage import get_current_stage

from .debris_system import DebrisSystem
from . import global_variables as gv


def _resolve_debris_config() -> tuple[list[int], tuple[int, int], float]:
    """Pull spawn pools and counts from water_tank_env_ext params; fall back to gv."""
    try:
        p = importlib.import_module("water_tank_env_python.params")
        indices = list(getattr(p, "DEBRIS_SPAWN_POOLS", gv.DEBRIS_SPAWN_POOLS))
        lo = int(getattr(p, "DEBRIS_COUNT_MIN", gv.DEBRIS_COUNT_MIN))
        hi = int(getattr(p, "DEBRIS_COUNT_MAX", gv.DEBRIS_COUNT_MAX))
        radius = float(getattr(p, "DEBRIS_RADIUS", gv.DEBRIS_RADIUS))
        return indices, (lo, hi), radius
    except ImportError:
        return list(gv.DEBRIS_SPAWN_POOLS), (gv.DEBRIS_COUNT_MIN, gv.DEBRIS_COUNT_MAX), gv.DEBRIS_RADIUS


def _resolve_floor_z() -> float:
    """Pull TANK_FLOOR_Z from water_tank_env_ext; fall back to gv.FLOOR_Z."""
    try:
        params = importlib.import_module("water_tank_env_python.params")
        return float(getattr(params, "TANK_FLOOR_Z", gv.FLOOR_Z))
    except ImportError:
        return gv.FLOOR_Z


class DebrisScenario:
    def __init__(self):
        self._debris: DebrisSystem | None = None

    def setup_scenario(
        self,
        count_range: tuple[int, int] | None = None,
        radius: float | None = None,
        pool_indices: list[int] | None = None,
    ) -> None:
        stage = get_current_stage()
        default_indices, default_range, default_radius = _resolve_debris_config()
        self._debris = DebrisSystem(
            count_range=count_range if count_range is not None else default_range,
            radius=radius if radius is not None else default_radius,
            color_hex=gv.DEBRIS_COLOR_HEX,
            tank_range=gv.TANK_RANGE,
            z_floor=_resolve_floor_z(),
            pool_indices=pool_indices if pool_indices is not None else default_indices,
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

    def pool_counts(self) -> dict[int, int] | None:
        if self._debris is None or not self._debris.is_spawned:
            return None
        return self._debris.pool_counts

    def update_scenario(self, step: float) -> None:
        pass
