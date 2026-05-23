"""
Wheel-Floor Contact Diagnosis Script
Run in Isaac Sim Script Editor to check wheel collision cylinder dimensions
and verify proper floor contact at each robot location.
"""
from pxr import UsdGeom, UsdPhysics, Gf

stage = omni.usd.get_context().get_stage()

print("=" * 70)
print("Wheel Collision Cylinder Dimension & Floor Contact Analysis")
print("=" * 70)

# First, get the floor collision info
floor_path = "/World/Building/Floor"
floor_prim = stage.GetPrimAtPath(floor_path)
if floor_prim.IsValid():
    xformable = UsdGeom.Xformable(floor_prim)
    world_xform = xformable.ComputeLocalToWorldTransform(0)
    floor_translation = world_xform.ExtractTranslation()
    
    # Get scale
    scale = Gf.Vec3f(1, 1, 1)
    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeScale:
            scale = op.Get()
            break
    
    floor_top_z = floor_translation[2] + scale[2] / 2
    floor_extent_x = (-scale[0]/2, scale[0]/2)
    floor_extent_y = (-scale[1]/2, scale[1]/2)
    
    print(f"\n[Building Floor]")
    print(f"  Top Surface Z: {floor_top_z:.4f}")
    print(f"  X extent: {floor_extent_x[0]:.2f} to {floor_extent_x[1]:.2f}")
    print(f"  Y extent: {floor_extent_y[0]:.2f} to {floor_extent_y[1]:.2f}")
    print(f"  Has CollisionAPI: {floor_prim.HasAPI(UsdPhysics.CollisionAPI)}")
else:
    print("\n[Building Floor] NOT FOUND!")
    floor_top_z = 0.0

# Now check each robot's wheel collision cylinders
print("\n" + "-" * 70)
print("Wheel Collision Cylinder Dimensions")
print("-" * 70)

for robot_id in range(1, 8):
    robot_path = f"/World/Pools/Pool_{robot_id}/Robot/dingo"
    robot_prim = stage.GetPrimAtPath(robot_path)
    
    if not robot_prim.IsValid():
        print(f"\nRobot {robot_id}: NOT FOUND")
        continue
    
    # Get robot world position using USD native API
    xformable = UsdGeom.Xformable(robot_prim)
    world_xform = xformable.ComputeLocalToWorldTransform(0)
    pos = world_xform.ExtractTranslation()
    robot_z = pos[2]
    
    print(f"\n[Robot {robot_id}] at ({pos[0]:.2f}, {pos[1]:.2f}, {robot_z:.4f})")
    
    for wheel in ["left_wheel_link", "right_wheel_link"]:
        wheel_path = f"{robot_path}/{wheel}"
        collision_path = f"{wheel_path}/collisions"
        
        collision_prim = stage.GetPrimAtPath(collision_path)
        if not collision_prim.IsValid():
            print(f"  {wheel}: collision prim NOT FOUND")
            continue
        
        # Check if it's a Cylinder
        cyl = UsdGeom.Cylinder(collision_prim)
        if not cyl:
            print(f"  {wheel}: NOT a Cylinder")
            continue
        
        # Get cylinder dimensions
        radius = cyl.GetRadiusAttr().Get()
        height = cyl.GetHeightAttr().Get()
        axis = cyl.GetAxisAttr().Get()
        
        # Get world transform of the collision prim
        xformable = UsdGeom.Xformable(collision_prim)
        world_xform = xformable.ComputeLocalToWorldTransform(0)
        coll_translation = world_xform.ExtractTranslation()
        
        # Calculate the bottom of the wheel cylinder (assuming Y-axis cylinder)
        if axis == "Y":
            wheel_bottom_z = coll_translation[2]  # For Y-axis cylinder, Z is the center
            wheel_lowest = wheel_bottom_z - radius  # The lowest point of the wheel
        elif axis == "Z":
            wheel_bottom_z = coll_translation[2] - height / 2
            wheel_lowest = wheel_bottom_z
        else:  # X axis
            wheel_bottom_z = coll_translation[2]
            wheel_lowest = wheel_bottom_z - radius
        
        gap = wheel_lowest - floor_top_z
        
        print(f"  {wheel}:")
        print(f"    Radius: {radius:.4f}, Height: {height:.4f}, Axis: {axis}")
        print(f"    Collision World Pos: ({coll_translation[0]:.3f}, {coll_translation[1]:.3f}, {coll_translation[2]:.4f})")
        print(f"    Wheel lowest point Z: {wheel_lowest:.4f}")
        print(f"    Gap to floor: {gap:.4f} {'(PENETRATING!)' if gap < 0 else '(OK)' if gap < 0.01 else '(floating?)'}")

# Summary by row
print("\n" + "-" * 70)
print("Position Summary by Pool Row")
print("-" * 70)

lower_row_z = []
upper_row_z = []

for robot_id in range(1, 8):
    robot_path = f"/World/Pools/Pool_{robot_id}/Robot/dingo"
    robot_prim = stage.GetPrimAtPath(robot_path)
    if robot_prim.IsValid():
        xformable = UsdGeom.Xformable(robot_prim)
        world_xform = xformable.ComputeLocalToWorldTransform(0)
        pos = world_xform.ExtractTranslation()
        if pos[1] < 0:  # Lower row (y = -5.0)
            lower_row_z.append((robot_id, pos[2]))
        else:  # Upper row (y = 5.0)
            upper_row_z.append((robot_id, pos[2]))

print(f"\nLower row (Y=-5.0): Pools 1-4")
for rid, z in lower_row_z:
    status = "OK" if z > 0.012 else "SINKING"
    print(f"  Robot {rid}: Z = {z:.4f} [{status}]")

print(f"\nUpper row (Y=+5.0): Pools 5-7")
for rid, z in upper_row_z:
    status = "OK" if z > 0.012 else "SINKING"
    print(f"  Robot {rid}: Z = {z:.4f} [{status}]")

avg_lower = sum(z for _, z in lower_row_z) / len(lower_row_z) if lower_row_z else 0
avg_upper = sum(z for _, z in upper_row_z) / len(upper_row_z) if upper_row_z else 0

print(f"\nAverage Z:")
print(f"  Lower row: {avg_lower:.4f}")
print(f"  Upper row: {avg_upper:.4f}")
print(f"  Difference: {avg_upper - avg_lower:.4f}")

print("\n" + "=" * 70)
print("If some robots have much lower Z, the issue is likely:")
print("1. Spawn timing - some robots start physics earlier")
print("2. GPU dynamics contact resolution order")
print("3. Pool Xform slightly affecting robot position")
print("=" * 70)
