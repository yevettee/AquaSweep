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
    "2007_Jeep_Wrangler_Rubicon.usdz",
)
CAR_STALL_INDICES = (1, 4, 6, 3)
CAR_BASE_SCALE = 0.01                       # cm → m
# X +90: Y-up → Z-up (puts +Y[up] onto +Z[up]).  Z +90: rotates car's forward
# (originally along its local +X after the X-tilt) so the long axis lies along
# the stall depth direction (our world ±X).
CAR_BASE_ROTATE_XYZ = (90.0, 0.0, 90.0)
# Per-car tuning fields:
#   dx, dy, dz                  : wrapper-level translate offsets (m)
#   yaw_deg                     : extra Z rotation added to base (90,0,90)
#   scale_mul                   : multiplied with CAR_BASE_SCALE (0.01)
#   color                       : (r,g,b) or None — UsdShade override
#   inner_translate / inner_rot : applied to the *inner Model* prim, used when
#                                 the wrapper transform isn't enough and the
#                                 USDZ needs additional in-place offset/rotation
CAR_PER_INDEX_TUNING = (
    # (dx, dy, dz, yaw, scale_mul, color, inner_translate, inner_rotate_xyz)
    ( 0.00, 0.00,  0.023, -180.0,  1.0,  None, None, None),                # Aston Vulcan — GUI yaw flip (Z: +90 → -90)
    ( 0.00, 0.00, -0.517, 90.0,    0.6,  None, None, None),                # Cybertruck
    ( 0.00, 0.00,  0.676,  0.0,    0.55, None, None, None),                # Pickup
    ( 0.00, 0.00,  0.000,  0.0,  100.0,  None,
      (0.8, 0.0, -1.5), (-180.0, 0.0, -180.0)),                            # Jeep Wrangler — model in m + GUI-tuned inner Model
)

# ── Steel hangar door on west wall (visual-only placeholder) ─────────────────
# Values match the user-tuned cube in the Isaac Sim viewport.
DOOR_TRANSLATE = (-20.0, 5.2, 2.7)
DOOR_SCALE = (0.60376, 2.44149, 5.12779)

# ── Dead-sturgeon collection bin (fish_bin.usdz reference) ───────────────────
# External Sketchfab dumpster asset (Y-up + cm). Wrapper Xform pattern:
#   - RotateXYZ X=90 fixes Y-up → Z-up
#   - RotateXYZ Z=yaw orients the bin
#   - Per-axis scale combines cm→m (0.01) with non-uniform shrink to fit footprint.
DEAD_FISH_BIN_TRANSLATE: tuple[float, float, float] = (17.0, 3.5, 0.0)
DEAD_FISH_BIN_ROTATE_XYZ: tuple[float, float, float] = (90.0, 0.0, -90.0)  # X for axis, Z for yaw
DEAD_FISH_BIN_SCALE: tuple[float, float, float] = (0.03, 0.015, 0.02)

# ── Default viewport camera applied on every LOAD ─────────────────────────────
# Tuned by user via /OmniverseKit_Persp in Isaac Sim viewport.
# Looks down at the building from south-above at a 45° pitch.
DEFAULT_VIEW_TRANSLATE = (-3.0, -80.0, 100.0)
DEFAULT_VIEW_ROTATE_XYZ = (40.0, 0.0, 0.0)     # degrees, applied as RotateXYZ

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
# 1-indexed pool IDs. None → spawn in every pool on stage.
STURGEON_SPAWN_POOLS: list[int] | None = [1, 3, 6]
STURGEON_PER_POOL_MIN = 5
STURGEON_PER_POOL_MAX = 7
STURGEON_FLIPPED_MIN_RATIO = 0.10   # belly-up (suspicious) floor per pool
STURGEON_FLIPPED_MAX_RATIO = 0.20   # belly-up (suspicious) cap per pool

# ── Debris spawn settings ─────────────────────────────────────────────────────
DEBRIS_SPAWN_POOLS: list[int] = [1, 2, 3, 4, 5, 6, 7]
DEBRIS_COUNT_MIN = 30
DEBRIS_COUNT_MAX = 50
DEBRIS_RADIUS = 0.03
DEBRIS_POLLUTION_SCALE = 200.0      # remaining count → pollution_level = N / scale

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


def pool_centers_for_indices(
    indices: list[int],
) -> list[tuple[int, tuple[float, float]]]:
    """Return (1-based pool_id, center) for valid indices into POOL_CENTERS."""
    out: list[tuple[int, tuple[float, float]]] = []
    n = len(POOL_CENTERS)
    for pool_id in indices:
        if 1 <= pool_id <= n:
            out.append((pool_id, POOL_CENTERS[pool_id - 1]))
    return out
