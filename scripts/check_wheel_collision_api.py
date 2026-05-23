"""
Check if wheel collision prims have CollisionAPI applied.
Run in Isaac Sim Script Editor.
"""
from pxr import UsdPhysics, UsdGeom

stage = omni.usd.get_context().get_stage()

print("=" * 70)
print("Wheel Collision API Check")
print("=" * 70)

for robot_id in range(1, 8):
    print(f"\n[Robot {robot_id}]")
    
    for wheel in ["left_wheel_link", "right_wheel_link"]:
        collision_path = f"/World/Pools/Pool_{robot_id}/Robot/dingo/{wheel}/collisions"
        prim = stage.GetPrimAtPath(collision_path)
        
        if not prim.IsValid():
            print(f"  {wheel}/collisions: NOT FOUND")
            continue
        
        has_collision_api = prim.HasAPI(UsdPhysics.CollisionAPI)
        has_mesh_collision_api = prim.HasAPI(UsdPhysics.MeshCollisionAPI) if hasattr(UsdPhysics, "MeshCollisionAPI") else False
        
        # Check cylinder properties
        cyl = UsdGeom.Cylinder(prim)
        axis = cyl.GetAxisAttr().Get() if cyl else "N/A"
        radius = cyl.GetRadiusAttr().Get() if cyl else "N/A"
        
        print(f"  {wheel}/collisions:")
        print(f"    Type: {prim.GetTypeName()}")
        print(f"    CollisionAPI: {has_collision_api}")
        print(f"    MeshCollisionAPI: {has_mesh_collision_api}")
        print(f"    Cylinder Axis: {axis}, Radius: {radius}")

print("\n" + "=" * 70)
print("If CollisionAPI is False, collision detection won't work!")
print("=" * 70)
