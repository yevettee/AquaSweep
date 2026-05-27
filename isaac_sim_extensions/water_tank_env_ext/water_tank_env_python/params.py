"""Single source of truth for building/tank/water dimensions and physical constants.

Coordinates are in metres, building centre at world origin.
"""

# ── Building (fish-farm warehouse) ─────────────────────────────────────────────
BUILDING_X = 40.0   # long axis: 4 pools in a row
BUILDING_Y = 30.0
BUILDING_FLOOR_Z = 0.0

# ── Outdoor ground (visual-only dry-earth plane around the building) ──────────
# Mountain fish-farm setting: barren plain encircling the warehouse.
# Z = -0.10 sits at the bottom of aquafarm Floor mesh (top=0, bottom=-0.10),
# so the Floor occludes it indoors. Outside, the building reads as resting
# on a 10 cm concrete plinth above the surrounding earth.
GROUND_X = 200.0
GROUND_Y = 160.0
GROUND_Z = -0.10

# ── Parking lot along the west short wall (x = -20) ──────────────────────────
PARKING_STALL_COUNT = 8         # 8 × 3.5 = 28 m, leaves 1 m at each y-end
PARKING_STALL_WIDTH = 3.5       # m (Y, along the wall, ×1.4 of the original 2.5)
PARKING_STALL_DEPTH = 5.0       # m (X, away from the wall)
PARKING_OFFSET_FROM_WALL = 2.0  # gap between wall and stall front
PARKING_LINE_WIDTH = 0.12       # m (paint stripe thickness)
PARKING_WALL_X = -20.0          # building west wall x-coordinate

# ── Parked cars (real USDZ assets referenced into 3 of the 8 stalls) ─────────
# All three USDZs are cm-scale and Y-up, so each gets a uniform 0.01 scale and
# an X-axis −90° rotation to land in our metres / Z-up stage. Tweak per-car
# overrides below if a model lands rotated, sunk, or floating.
CAR_USD_FILES = (
    "ASTON_MARTIN_VULCAN.usdz",
    "Cyber_Truck.usdz",
    "Pickup_Truck_Commercial_Vehicle.usdz",
)
CAR_STALL_INDICES = (1, 4, 6)
CAR_BASE_SCALE = 0.01                       # cm → m
# X +90: Y-up → Z-up (puts +Y[up] onto +Z[up]).  Z +90: rotates car's forward
# (originally along its local +X after the X-tilt) so the long axis lies along
# the stall depth direction (our world ±X).
CAR_BASE_ROTATE_XYZ = (90.0, 0.0, 90.0)
# Per-car extra (translate_z, yaw_deg, scale_multiplier) tuning.
# dz values offset each car's bbox-min-Y (in cm × scale_total) so wheels rest
# on the ground (z=0):
#   Aston:      bbox_min_Y = -2.3cm  × 0.01    = -0.023 m below origin
#   Cybertruck: bbox_min_Y = +86cm   × 0.006   = +0.517 m above origin
#   Pickup:     bbox_min_Y = -123cm  × 0.0055  = -0.676 m below origin
CAR_PER_INDEX_TUNING = (
    ( 0.023,  0.0,  1.0 ),    # Aston   — slight lift
    (-0.517, 90.0,  0.6 ),    # Cyber   — drop to ground + 90° yaw
    ( 0.676,  0.0,  0.55),    # Pickup  — lift up out of asphalt
)

# ── Steel hangar door on east wall (visual-only placeholder) ─────────────────
# Values match the user-tuned cube in the Isaac Sim viewport.
DOOR_TRANSLATE = (19.98567, 3.46947, 2.85436)
DOOR_SCALE = (0.60376, 2.44149, 5.12779)

# ── Default viewport camera applied on every LOAD ─────────────────────────────
# Tuned by user via /OmniverseKit_Persp in Isaac Sim viewport.
# Looks down at the building from south-above at a 45° pitch.
DEFAULT_VIEW_TRANSLATE = (-3.0, -45.0, 50.0)
DEFAULT_VIEW_ROTATE_XYZ = (45.0, 0.0, 0.0)     # degrees, applied as RotateXYZ

# ── Single pool dimensions ────────────────────────────────────────────────────
TANK_RADIUS = 4.0           # diameter 8 m
TANK_INNER_Z = 1.5
WALL_THICKNESS = 0.03

WATER_LEVEL = 1.10            # water depth (surface at z = TANK_FLOOR_Z + WATER_LEVEL = 1.35)
TANK_FLOOR_Z = 0.25           # USD Bottom mesh top surface

# ── Pool layout (4 bottom + 3 top, plus one equipment slot) ───────────────────
# Aligned with aquafarm_environment.usda (B01~B04 bottom, T01~T03 top).
# Spacing: 8.5 m centre-to-centre on x, 12 m centre-to-centre on y.
POOL_CENTERS: list[tuple[float, float]] = [
     (-12.75, -6.0),   # Pool_1  ← B01
     ( -4.25, -6.0),   # Pool_2  ← B02
     (  4.25, -6.0),   # Pool_3  ← B03
     ( 12.75, -6.0),   # Pool_4  ← B04
     (-12.75,  6.0),   # Pool_5  ← T01
     ( -4.25,  6.0),   # Pool_6  ← T02
     (  4.25,  6.0),   # Pool_7  ← T03
]

EQUIPMENT_CENTER: tuple[float, float] = (12.75, 6.0)

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
