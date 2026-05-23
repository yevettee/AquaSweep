"""
Wheel Transform Detail Diagnosis
Check the exact transform chain from robot root to wheel collision.
"""
from pxr import UsdGeom, Gf

stage = omni.usd.get_context().get_stage()

print("=" * 70)
print("Wheel Transform Chain Analysis")
print("=" * 70)

def get_local_transform(prim):
    """Get local transform (translate, rotate, scale) of a prim."""
    xformable = UsdGeom.Xformable(prim)
    ops = xformable.GetOrderedXformOps()
    
    translate = Gf.Vec3d(0, 0, 0)
    rotate = None
    scale = Gf.Vec3f(1, 1, 1)
    
    for op in ops:
        op_type = op.GetOpType()
        if op_type == UsdGeom.XformOp.TypeTranslate:
            translate = op.Get()
        elif op_type == UsdGeom.XformOp.TypeScale:
            scale = op.Get()
        elif op_type in [UsdGeom.XformOp.TypeRotateXYZ, UsdGeom.XformOp.TypeOrient]:
            rotate = op.Get()
    
    return translate, rotate, scale

def print_transform_chain(robot_id, wheel_name):
    """Print the transform chain from robot root to wheel collision."""
    robot_path = f"/World/Pools/Pool_{robot_id}/Robot/dingo"
    wheel_path = f"{robot_path}/{wheel_name}"
    collision_path = f"{wheel_path}/collisions"
    
    print(f"\n[Robot {robot_id}] {wheel_name}")
    print("-" * 50)
    
    # Robot root
    robot_prim = stage.GetPrimAtPath(robot_path)
    if robot_prim.IsValid():
        t, r, s = get_local_transform(robot_prim)
        xformable = UsdGeom.Xformable(robot_prim)
        world = xformable.ComputeLocalToWorldTransform(0).ExtractTranslation()
        print(f"  dingo (root):")
        print(f"    Local translate: ({t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f})")
        print(f"    World position:  ({world[0]:.4f}, {world[1]:.4f}, {world[2]:.4f})")
    
    # Wheel link
    wheel_prim = stage.GetPrimAtPath(wheel_path)
    if wheel_prim.IsValid():
        t, r, s = get_local_transform(wheel_prim)
        xformable = UsdGeom.Xformable(wheel_prim)
        world = xformable.ComputeLocalToWorldTransform(0).ExtractTranslation()
        print(f"  {wheel_name}:")
        print(f"    Local translate: ({t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f})")
        print(f"    World position:  ({world[0]:.4f}, {world[1]:.4f}, {world[2]:.4f})")
    
    # Collision prim
    collision_prim = stage.GetPrimAtPath(collision_path)
    if collision_prim.IsValid():
        t, r, s = get_local_transform(collision_prim)
        xformable = UsdGeom.Xformable(collision_prim)
        world = xformable.ComputeLocalToWorldTransform(0).ExtractTranslation()
        print(f"  collisions:")
        print(f"    Local translate: ({t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f})")
        print(f"    World position:  ({world[0]:.4f}, {world[1]:.4f}, {world[2]:.4f})")

# Check a working robot (5) vs non-working robot (1)
print("\n" + "=" * 70)
print("Comparing Robot 1 (lower row, Z issue) vs Robot 5 (upper row, working)")
print("=" * 70)

for robot_id in [1, 5]:
    print_transform_chain(robot_id, "left_wheel_link")

# Also check robot 7 (upper row but not working)
print("\n" + "=" * 70)
print("Robot 7 (upper row, but has Z issue like lower row)")
print("=" * 70)
print_transform_chain(7, "left_wheel_link")

# Summary comparison
print("\n" + "=" * 70)
print("All Robots - Wheel Collision World Z Position")
print("=" * 70)

data = []
for robot_id in range(1, 8):
    collision_path = f"/World/Pools/Pool_{robot_id}/Robot/dingo/left_wheel_link/collisions"
    prim = stage.GetPrimAtPath(collision_path)
    if prim.IsValid():
        xformable = UsdGeom.Xformable(prim)
        world = xformable.ComputeLocalToWorldTransform(0).ExtractTranslation()
        data.append((robot_id, world[2]))
        print(f"  Robot {robot_id}: left_wheel collision Z = {world[2]:.4f}")

# Find the pattern
print("\n" + "-" * 70)
print("Pattern Analysis")
print("-" * 70)

z_values = [z for _, z in data]
max_z = max(z_values)
min_z = min(z_values)

print(f"  Max wheel Z: {max_z:.4f}")
print(f"  Min wheel Z: {min_z:.4f}")
print(f"  Difference:  {max_z - min_z:.4f}")

high_z_robots = [rid for rid, z in data if z > (max_z + min_z) / 2]
low_z_robots = [rid for rid, z in data if z <= (max_z + min_z) / 2]

print(f"\n  Higher Z robots: {high_z_robots}")
print(f"  Lower Z robots:  {low_z_robots}")

print("\n" + "=" * 70)
print("If wheel Z differs BEFORE physics, it's a USD loading/spawn issue.")
print("If wheel Z is same before but differs after physics, it's a simulation issue.")
print("=" * 70)
