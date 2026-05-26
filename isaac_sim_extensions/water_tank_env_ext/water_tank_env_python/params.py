"""Single source of truth for building/tank/water dimensions and physical constants.

Coordinates are in metres, building centre at world origin.
"""

# ── Building (fish-farm warehouse) ─────────────────────────────────────────────
BUILDING_X = 40.0   # long axis: 4 pools in a row
BUILDING_Y = 30.0
BUILDING_FLOOR_Z = 0.0

# ── Single pool dimensions ────────────────────────────────────────────────────
TANK_RADIUS = 4.0           # diameter 8 m
TANK_INNER_Z = 1.5
WALL_THICKNESS = 0.03

WATER_LEVEL = 1.2
TANK_FLOOR_Z = 0.0

# ── Pool layout (4 bottom + 3 top, plus one equipment slot) ───────────────────
# Spacing: 0.5 m horizontal gap → 8.5 m centre-to-centre on x.
#          2.0 m vertical   gap → 10  m centre-to-centre on y.
POOL_CENTERS: list[tuple[float, float]] = [
     (-12.75, -5.0),   # Pool_1
     ( -4.25, -5.0),   # Pool_2
     (  4.25, -5.0),   # Pool_3
     ( 12.75, -5.0),   # Pool_4
     (-12.75,  5.0),   # Pool_5
     ( -4.25,  5.0),   # Pool_6
     (  4.25,  5.0),   # Pool_7
]

EQUIPMENT_CENTER: tuple[float, float] = (12.75, 5.0)

# ── Sturgeon spawn settings ──────────────────────────────────────────────────
# 상어 spawn할 풀 번호 (1-indexed). None이면 랜덤 선택 유지
# 예: [2, 5, 7] → Pool_2, Pool_5, Pool_7에만 상어 spawn
STURGEON_SPAWN_POOLS: list[int] | None = [2, 5, 7]

# ── Physical constants ────────────────────────────────────────────────────────
WATER_DENSITY = 1000.0
GRAVITY = 9.81


def water_surface_z() -> float:
    return TANK_FLOOR_Z + WATER_LEVEL


def tank_inner_bounds(center: tuple[float, float] = (0.0, 0.0)) -> tuple[
    float, float, float, float, float, float
]:
    """AABB of one pool's usable inner volume (circumscribes the cylinder)."""
    cx, cy = center
    return (
        cx - TANK_RADIUS, cx + TANK_RADIUS,
        cy - TANK_RADIUS, cy + TANK_RADIUS,
        TANK_FLOOR_Z, TANK_FLOOR_Z + TANK_INNER_Z,
    )


def is_inside_any_pool(x: float, y: float, margin: float = 0.0) -> int | None:
    """Return 1-based pool index containing (x, y), or None if outside all pools."""
    r_eff = TANK_RADIUS - margin
    r_sq = r_eff * r_eff
    for i, (cx, cy) in enumerate(POOL_CENTERS, start=1):
        dx, dy = x - cx, y - cy
        if dx * dx + dy * dy <= r_sq:
            return i
    return None


def is_inside_tank(x: float, y: float, margin: float = 0.0) -> bool:
    """Backwards-compatible single-pool check (any pool)."""
    return is_inside_any_pool(x, y, margin) is not None
