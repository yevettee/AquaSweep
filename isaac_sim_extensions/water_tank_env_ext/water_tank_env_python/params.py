"""Single source of truth for tank/water dimensions and physical constants."""

TANK_RADIUS = 4.0
TANK_INNER_Z = 1.5
WALL_THICKNESS = 0.03

WATER_LEVEL = 1.2

TANK_FLOOR_Z = 0.0

WATER_DENSITY = 1000.0
GRAVITY = 9.81


def water_surface_z() -> float:
    return TANK_FLOOR_Z + WATER_LEVEL


def tank_inner_bounds() -> tuple[float, float, float, float, float, float]:
    """AABB of the usable inner volume (circumscribes the cylinder)."""
    return (
        -TANK_RADIUS, TANK_RADIUS,
        -TANK_RADIUS, TANK_RADIUS,
        TANK_FLOOR_Z, TANK_FLOOR_Z + TANK_INNER_Z,
    )


def is_inside_tank(x: float, y: float, margin: float = 0.0) -> bool:
    r_eff = TANK_RADIUS - margin
    return (x * x + y * y) <= (r_eff * r_eff)
