"""
Pool Floor Z-Value Diagnosis Script
Run in Isaac Sim Script Editor to check actual floor positions and collision states.
"""
from pxr import UsdGeom, UsdPhysics, Gf

stage = omni.usd.get_context().get_stage()

print("=" * 70)
print("Pool Floor Z-Value and Collision Diagnosis")
print("=" * 70)

# Check Building Floor
building_floor_path = "/World/Building/Floor"
floor_prim = stage.GetPrimAtPath(building_floor_path)
if floor_prim.IsValid():
    xformable = UsdGeom.Xformable(floor_prim)
    world_xform = xformable.ComputeLocalToWorldTransform(0)
    translation = world_xform.ExtractTranslation()
    
    # Get scale (size of the box)
    cube = UsdGeom.Cube(floor_prim)
    size_attr = cube.GetSizeAttr()
    size = size_attr.Get() if size_attr else 1.0
    
    # Get scale ops
    scale = Gf.Vec3f(1, 1, 1)
    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeScale:
            scale = op.Get()
            break
    
    has_collision = floor_prim.HasAPI(UsdPhysics.CollisionAPI)
    
    print(f"\n[Building Floor]")
    print(f"  Path: {building_floor_path}")
    print(f"  World Translation: ({translation[0]:.4f}, {translation[1]:.4f}, {translation[2]:.4f})")
    print(f"  Scale (Size): ({scale[0]:.2f}, {scale[1]:.2f}, {scale[2]:.2f})")
    print(f"  Floor Top Surface Z: {translation[2] + scale[2]/2:.4f}")
    print(f"  CollisionAPI: {has_collision}")
else:
    print(f"\n[Building Floor] NOT FOUND at {building_floor_path}")

# Check Pool Xform positions
print("\n" + "-" * 70)
print("Pool Xform Positions (world coordinates)")
print("-" * 70)

pool_data = []
for i in range(1, 8):
    pool_path = f"/World/Pools/Pool_{i}"
    pool_prim = stage.GetPrimAtPath(pool_path)
    
    if pool_prim.IsValid():
        xformable = UsdGeom.Xformable(pool_prim)
        world_xform = xformable.ComputeLocalToWorldTransform(0)
        translation = world_xform.ExtractTranslation()
        pool_data.append((i, translation))
        print(f"  Pool_{i}: X={translation[0]:7.2f}, Y={translation[1]:7.2f}, Z={translation[2]:.4f}")
    else:
        print(f"  Pool_{i}: NOT FOUND")

# Check for any Z differences
print("\n" + "-" * 70)
print("Pool Z-Value Analysis")
print("-" * 70)
if pool_data:
    z_values = [t[2] for _, t in pool_data]
    unique_z = set(round(z, 4) for z in z_values)
    if len(unique_z) == 1:
        print(f"  All pools have the same Z: {z_values[0]:.4f}")
    else:
        print(f"  WARNING: Pools have different Z values!")
        for i, t in pool_data:
            print(f"    Pool_{i}: Z = {t[2]:.6f}")

# Check Pool Wall/Floor meshes for collision
print("\n" + "-" * 70)
print("Pool Component Collision Status")
print("-" * 70)

for i in range(1, 8):
    pool_path = f"/World/Pools/Pool_{i}"
    wall_path = f"{pool_path}/Wall"
    
    wall_prim = stage.GetPrimAtPath(wall_path)
    if wall_prim.IsValid():
        has_collision = wall_prim.HasAPI(UsdPhysics.CollisionAPI)
        has_mesh_collision = wall_prim.HasAPI(UsdPhysics.MeshCollisionAPI)
        print(f"  Pool_{i}/Wall: CollisionAPI={has_collision}, MeshCollisionAPI={has_mesh_collision}")

# Check robot current Z positions
print("\n" + "-" * 70)
print("Robot Current Z Positions (after physics)")
print("-" * 70)

working_robots = []
non_working_robots = []

for i in range(1, 8):
    robot_path = f"/World/Pools/Pool_{i}/Robot/dingo"
    prim = stage.GetPrimAtPath(robot_path)
    
    if prim.IsValid():
        xformable = UsdGeom.Xformable(prim)
        world_xform = xformable.ComputeLocalToWorldTransform(0)
        pos = world_xform.ExtractTranslation()
        z = pos[2]
        
        status = "OK" if z > 0.012 else "LOW"
        if status == "OK":
            working_robots.append(i)
        else:
            non_working_robots.append(i)
        
        print(f"  Robot {i}: Z = {z:.6f} [{status}]")
    else:
        print(f"  Robot {i}: NOT FOUND")

print("\n" + "-" * 70)
print("Summary")
print("-" * 70)
print(f"  Working robots (Z > 0.012): {working_robots}")
print(f"  Low Z robots (possible sinking): {non_working_robots}")

# Check if there's a pattern based on pool Y position
if pool_data:
    print("\n  Pool positions by row:")
    lower_row = [(i, t) for i, t in pool_data if t[1] < 0]  # y = -5.0
    upper_row = [(i, t) for i, t in pool_data if t[1] > 0]  # y = 5.0
    
    print(f"    Lower row (Y=-5.0): Pools {[i for i, _ in lower_row]}")
    print(f"    Upper row (Y=+5.0): Pools {[i for i, _ in upper_row]}")
    
    lower_non_working = [r for r in non_working_robots if r in [i for i, _ in lower_row]]
    upper_non_working = [r for r in non_working_robots if r in [i for i, _ in upper_row]]
    
    print(f"\n    Non-working in lower row: {lower_non_working}")
    print(f"    Non-working in upper row: {upper_non_working}")

print("\n" + "=" * 70)
