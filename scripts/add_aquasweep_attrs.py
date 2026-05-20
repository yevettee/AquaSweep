"""Tag a robot USD with aquasweep:* custom attributes so the water.tank.env
extension automatically applies buoyancy / drag / ground-effect to it.

Run via Isaac Sim's Python (headless SimulationApp boots before pxr import):

    ~/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/python.sh \
        src/scripts/add_aquasweep_attrs.py \
        --usd src/assets/robots/underwater_robot_v1.usd

Default behavior:
    - Picks the first RigidBodyAPI prim in the USD (use --all to tag every body)
    - Volume defaults to the prim's AABB volume (m^3)
    - half_height defaults to AABB half-extent in Z (m)
    - Original USD backed up to <file>.bak unless --no-backup is given
"""
import argparse
import functools
import os
import shutil
import sys

print = functools.partial(print, flush=True)  # noqa: A001 — SimApp swallows buffered stdout

# Boot SimulationApp first — pxr is only on the path after this.
from isaacsim import SimulationApp  # noqa: E402

_app = SimulationApp({"headless": True})

from pxr import Sdf, Usd, UsdGeom, UsdPhysics  # noqa: E402


def find_rigid_bodies(stage):
    return [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]


def compute_aabb_size(prim) -> tuple[float, float, float]:
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    rng = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    size = rng.GetSize()
    return float(size[0]), float(size[1]), float(size[2])


def _set_float(prim, name, value):
    attr = prim.GetAttribute(name)
    if not attr:
        attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.Float)
    attr.Set(float(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--usd", required=True, help="Path to the USD to tag")
    parser.add_argument("--volume", type=float, help="m^3; default = AABB volume")
    parser.add_argument("--half-height", type=float,
                        help="m; default = AABB half-extent in Z")
    parser.add_argument("--mass", type=float,
                        help="kg; sets UsdPhysics.MassAPI mass on the prim "
                             "(useful when the USD ships with mass=0)")
    parser.add_argument("--cd-linear", type=float, help="N*s/m; default 10.0")
    parser.add_argument("--cd-angular", type=float, help="N*m*s/rad; default 5.0")
    parser.add_argument("--added-mass", type=float, help="dimensionless; default 0.5")
    parser.add_argument("--prim", help="Specific RigidBody prim path to tag")
    parser.add_argument("--all", action="store_true",
                        help="Tag every RigidBody (default: only the first)")
    parser.add_argument("--no-backup", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without saving")
    args = parser.parse_args()

    usd_path = os.path.abspath(args.usd)
    if not os.path.isfile(usd_path):
        raise SystemExit(f"USD not found: {usd_path}")

    stage = Usd.Stage.Open(usd_path)
    if stage is None:
        raise SystemExit(f"Failed to open USD: {usd_path}")

    if args.prim:
        target = stage.GetPrimAtPath(args.prim)
        if not target.IsValid():
            raise SystemExit(f"Prim not found: {args.prim}")
        targets = [target]
    else:
        bodies = find_rigid_bodies(stage)
        if not bodies:
            raise SystemExit("No prim with UsdPhysics.RigidBodyAPI in this USD.")
        targets = bodies if args.all else [bodies[0]]

    for prim in targets:
        sx, sy, sz = compute_aabb_size(prim)
        volume = args.volume if args.volume is not None else sx * sy * sz
        half_h = args.half_height if args.half_height is not None else sz / 2.0

        # Inspect existing mass and decide effective mass after this run.
        existing_mass_api = UsdPhysics.MassAPI(prim)
        usd_mass = None
        if existing_mass_api:
            attr = existing_mass_api.GetMassAttr()
            if attr and attr.HasValue():
                usd_mass = float(attr.Get())

        effective_mass = args.mass if args.mass is not None else usd_mass

        print(f"[target] {prim.GetPath()}")
        print(f"  AABB size : ({sx:.4f}, {sy:.4f}, {sz:.4f}) m")
        print(f"  volume    : {volume:.6f} m^3")
        print(f"  half_h    : {half_h:.4f} m")
        if usd_mass is not None:
            print(f"  mass(USD) : {usd_mass:.3f} kg")
        else:
            print("  mass(USD) : (not declared)")
        if args.mass is not None:
            print(f"  mass(set) : {args.mass:.3f} kg  (--mass)")

        if effective_mass is not None and effective_mass > 0:
            buoy = 1000.0 * volume * 9.81
            grav = effective_mass * 9.81
            ratio = (1000.0 * volume) / effective_mass
            verdict = ("FLOAT (떠오름)" if ratio > 1.05
                       else "NEUTRAL (평형)" if 0.95 <= ratio <= 1.05
                       else "SINK (바닥 안착)")
            print(f"  buoyancy F: {buoy:.2f} N   gravity F: {grav:.2f} N")
            print(f"  rho*V/m   : {ratio:.3f}  → {verdict}")
        elif effective_mass == 0:
            print("  ⚠ mass=0 → PhysX 동작 이상 가능. --mass 로 양의 값 지정 권장.")

        if args.dry_run:
            continue

        if args.mass is not None:
            mass_api = UsdPhysics.MassAPI(prim)
            if not mass_api:
                mass_api = UsdPhysics.MassAPI.Apply(prim)
            mass_attr = mass_api.GetMassAttr()
            if not mass_attr:
                mass_attr = mass_api.CreateMassAttr()
            mass_attr.Set(float(args.mass))

        _set_float(prim, "aquasweep:volume", volume)
        _set_float(prim, "aquasweep:half_height", half_h)
        if args.cd_linear is not None:
            _set_float(prim, "aquasweep:cd_linear", args.cd_linear)
        if args.cd_angular is not None:
            _set_float(prim, "aquasweep:cd_angular", args.cd_angular)
        if args.added_mass is not None:
            _set_float(prim, "aquasweep:added_mass", args.added_mass)

    if args.dry_run:
        print("[dry-run] nothing saved.")
        return

    if not args.no_backup:
        bak = usd_path + ".bak"
        if not os.path.exists(bak):
            shutil.copy2(usd_path, bak)
            print(f"[backup] {bak}")

    stage.Save()
    print(f"[saved] {usd_path}")


if __name__ == "__main__":
    try:
        main()
    finally:
        _app.close()
