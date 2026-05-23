"""Robot / wheel world-Z snapshot before vs after Run Scenario.

Run inside Isaac Sim Script Editor (Window → Script Editor).
After exec(): snap_before() → UI RUN → wait → snap_after() → compare_saved()

Paths: hippo (current) with dingo fallback. Multi-pool: /World/Pools/Pool_<n>/Robot/<name>
Single robot: /World/Hippo (underwater_robot_ext).
"""

from __future__ import annotations

from pxr import UsdGeom

try:
    from underwater_robot_python.global_variables import HIPPO_WHEEL_RADIUS_M as _WHEEL_RADIUS
except ImportError:
    _WHEEL_RADIUS = 0.049

_FLOOR_TOP_Z = 0.0  # /World/Building/Floor top face (scene_builders)

_ROBOT_LINK_NAMES = ("hippo", "dingo")
_WHEEL_LINK = "left_wheel_link"
_SNAPSHOT_BEFORE: dict | None = None
_SNAPSHOT_AFTER: dict | None = None


def _stage():
    return omni.usd.get_context().get_stage()


def _world_z(prim_path: str) -> float | None:
    prim = _stage().GetPrimAtPath(prim_path)
    if not prim.IsValid():
        return None
    xf = UsdGeom.Xformable(prim)
    return float(xf.ComputeLocalToWorldTransform(0).ExtractTranslation()[2])


def _wheel_lowest_z(robot_root: str) -> tuple[float | None, float | None]:
    """Return (collision center Z, lowest point Z) for left wheel collision cylinder."""
    collision_path = f"{robot_root}/{_WHEEL_LINK}/collisions"
    prim = _stage().GetPrimAtPath(collision_path)
    if not prim.IsValid():
        return None, None

    cyl = UsdGeom.Cylinder(prim)
    if not cyl:
        center = _world_z(collision_path)
        return center, center

    radius = float(cyl.GetRadiusAttr().Get() or _WHEEL_RADIUS)
    height = float(cyl.GetHeightAttr().Get() or 0.0)
    axis = str(cyl.GetAxisAttr().Get() or "Y")
    center = _world_z(collision_path)
    if center is None:
        return None, None

    if axis == "Y":
        lowest = center - radius
    elif axis == "Z":
        lowest = center - height / 2.0
    else:
        lowest = center - radius
    return center, lowest


def _gap_to_floor(wheel_low: float | None) -> float | None:
    """Distance from wheel lowest point to building floor top (positive = above floor)."""
    if wheel_low is None:
        return None
    return wheel_low - _FLOOR_TOP_Z


def discover_robots() -> list[tuple[int, str, str]]:
    """(pool_id, robot_root_path, label). pool_id=0 for standalone /World/Hippo."""
    stage = _stage()
    found: list[tuple[int, str, str]] = []

    for i in range(1, 16):
        for link in _ROBOT_LINK_NAMES:
            root = f"/World/Pools/Pool_{i}/Robot/{link}"
            if stage.GetPrimAtPath(root).IsValid():
                found.append((i, root, f"Pool_{i}"))
                break

    if stage.GetPrimAtPath("/World/Hippo").IsValid():
        found.append((0, "/World/Hippo", "World/Hippo"))

    return found


def _enrich_row(pool_id: int, name: str, root: str) -> dict:
    robot_z = _world_z(root)
    wheel_center_z, wheel_lowest_z = _wheel_lowest_z(root)
    gap = _gap_to_floor(wheel_lowest_z)
    return {
        "pool_id": pool_id,
        "name": name,
        "root": root,
        "robot_z": robot_z,
        "wheel_center_z": wheel_center_z,
        "wheel_lowest_z": wheel_lowest_z,
        "gap_to_floor": gap,
    }


def snap(label: str = "", robot_ids: list[int] | None = None) -> dict:
    """Capture robot root Z and left-wheel collision Z for all (or selected) robots."""
    rows: list[dict] = []
    for pool_id, root, name in discover_robots():
        if robot_ids is not None and pool_id not in robot_ids:
            continue
        rows.append(_enrich_row(pool_id, name, root))

    snapshot = {"label": label or "(unlabeled)", "rows": rows}
    print(f"\n[compare_z] snapshot: {snapshot['label']}  ({len(rows)} robot(s))")
    _print_snapshot_table(snapshot, title=f"VALUES @ {snapshot['label']}")
    return snapshot


def _fmt(v: float | None) -> str:
    return f"{v:.4f}" if v is not None else "N/A"


def _fmt_delta(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return "N/A"
    return f"{a - b:+.4f}"


def _floor_status(gap: float | None) -> str:
    if gap is None:
        return ""
    if gap < -0.001:
        return "PENETRATE"
    if gap < 0.002:
        return "on floor"
    return "floating"


def _print_snapshot_table(snapshot: dict, title: str = "") -> None:
    """Single-phase table (before OR after)."""
    if title:
        print(f"\n  [{title}]  (floor top z = {_FLOOR_TOP_Z:.4f})")
    hdr = (
        f"{'Pool':>8}  {'robot_Z':>9}  {'wheel_ctr':>9}  {'wheel_low':>9}  "
        f"{'gap_floor':>9}  status"
    )
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for r in snapshot["rows"]:
        gap = r.get("gap_to_floor")
        print(
            f"{r['name']:>8}  "
            f"{_fmt(r['robot_z']):>9}  "
            f"{_fmt(r['wheel_center_z']):>9}  "
            f"{_fmt(r['wheel_lowest_z']):>9}  "
            f"{_fmt(gap):>9}  {_floor_status(gap)}"
        )


def _print_compare_table(before: dict, after: dict) -> None:
    """Side-by-side before / after / delta for each pool."""
    before_by_pool = {r["pool_id"]: r for r in before["rows"]}
    after_by_pool = {r["pool_id"]: r for r in after["rows"]}
    pool_ids = sorted(set(before_by_pool) | set(after_by_pool))

    print("\n  [BEFORE vs AFTER vs CHANGE (after − before)]")
    hdr = (
        f"{'Pool':>8}  "
        f"{'robot bef':>9} {'robot aft':>9} {'Δ rob':>8}  "
        f"{'w_ctr bef':>9} {'w_ctr aft':>9} {'Δ ctr':>8}  "
        f"{'w_low bef':>9} {'w_low aft':>9} {'Δ low':>8}  "
        f"{'gap aft':>8}  note"
    )
    print(hdr)
    print("-" * len(hdr))

    for pid in pool_ids:
        b = before_by_pool.get(pid)
        a = after_by_pool.get(pid)
        name = (a or b)["name"]

        def _g(row: dict | None, key: str) -> float | None:
            return row[key] if row else None

        gap_a = _g(a, "gap_to_floor")
        print(
            f"{name:>8}  "
            f"{_fmt(_g(b, 'robot_z')):>9} {_fmt(_g(a, 'robot_z')):>9} {_fmt_delta(_g(a, 'robot_z'), _g(b, 'robot_z')):>8}  "
            f"{_fmt(_g(b, 'wheel_center_z')):>9} {_fmt(_g(a, 'wheel_center_z')):>9} "
            f"{_fmt_delta(_g(a, 'wheel_center_z'), _g(b, 'wheel_center_z')):>8}  "
            f"{_fmt(_g(b, 'wheel_lowest_z')):>9} {_fmt(_g(a, 'wheel_lowest_z')):>9} "
            f"{_fmt_delta(_g(a, 'wheel_lowest_z'), _g(b, 'wheel_lowest_z')):>8}  "
            f"{_fmt(gap_a):>8}  {_floor_status(gap_a)}"
        )


def _print_summary(before: dict, after: dict) -> None:
    before_by_pool = {r["pool_id"]: r for r in before["rows"]}
    after_by_pool = {r["pool_id"]: r for r in after["rows"]}

    dz_ctr = []
    penetrating = []
    for pid, a in after_by_pool.items():
        b = before_by_pool.get(pid)
        if b and a["wheel_center_z"] is not None and b["wheel_center_z"] is not None:
            dz_ctr.append(a["wheel_center_z"] - b["wheel_center_z"])
        gap = a.get("gap_to_floor")
        if gap is not None and gap < -0.001:
            penetrating.append(a["name"])

    ctr_after = [r["wheel_center_z"] for r in after["rows"] if r["wheel_center_z"] is not None]
    spread = (max(ctr_after) - min(ctr_after)) if len(ctr_after) > 1 else 0.0

    print("\n  [SUMMARY]")
    print(f"    floor top z        : {_FLOOR_TOP_Z:.4f}")
    print(f"    gap_to_floor       : wheel_low - floor  (+ above, - penetrating)")
    if dz_ctr:
        print(f"    Δ wheel_ctr range  : {min(dz_ctr):+.4f} … {max(dz_ctr):+.4f}  (after − before)")
    print(f"    after wheel_ctr spread across pools: {spread:.4f} m")
    if penetrating:
        print(f"    penetrating (aft)  : {', '.join(penetrating)}")
    else:
        print("    penetrating (aft)  : none (all gap >= -1 mm)")


def compare(before: dict, after: dict) -> None:
    """Print BEFORE table, AFTER table, then side-by-side comparison."""
    print("\n" + "=" * 100)
    print(f"RUN SCENARIO Z COMPARE")
    print(f"  BEFORE : {before['label']}")
    print(f"  AFTER  : {after['label']}")
    print("=" * 100)

    _print_snapshot_table(before, title="BEFORE (pre-RUN)")
    _print_snapshot_table(after, title="AFTER (post-RUN)")
    _print_compare_table(before, after)
    _print_summary(before, after)
    print()


def snap_before(label: str = "before RUN") -> dict:
    global _SNAPSHOT_BEFORE
    _SNAPSHOT_BEFORE = snap(label)
    return _SNAPSHOT_BEFORE


def snap_after(label: str = "after RUN") -> dict:
    global _SNAPSHOT_AFTER
    _SNAPSHOT_AFTER = snap(label)
    return _SNAPSHOT_AFTER


def compare_saved() -> None:
    if _SNAPSHOT_BEFORE is None or _SNAPSHOT_AFTER is None:
        print("[compare_z] Call snap_before() and snap_after() first.")
        return
    compare(_SNAPSHOT_BEFORE, _SNAPSHOT_AFTER)


print(
    "[compare_z] loaded.\n"
    "  snap_before()  → RUN 전 (timeline 정지)\n"
    "  snap_after()   → RUN 후\n"
    "  compare_saved() → BEFORE / AFTER / CHANGE 표 출력"
)
