"""Floor and wheel collision diagnosis.

Run in Isaac Sim Script Editor.
"""

from isaacsim.core.api.world import World
from isaacsim.core.utils.stage import get_current_stage
from pxr import UsdPhysics, UsdGeom, Usd
import numpy as np

TEST_ROBOT_IDS = [1, 5]


def check_floor():
    print(f"\n{'='*60}")
    print("Floor Diagnosis")
    print(f"{'='*60}")
    
    stage = get_current_stage()
    
    # Building floor
    floor_path = "/World/Building/Floor"
    floor_prim = stage.GetPrimAtPath(floor_path)
    
    if floor_prim.IsValid():
        print(f"[F1] Building Floor: EXISTS")
        
        # Get transform
        xform = UsdGeom.Xformable(floor_prim)
        xform_ops = xform.GetOrderedXformOps()
        for op in xform_ops:
            print(f"     {op.GetOpName()}: {op.Get()}")
        
        has_collision = floor_prim.HasAPI(UsdPhysics.CollisionAPI)
        print(f"[F2] Floor CollisionAPI: {'OK' if has_collision else 'MISSING!'}")
    else:
        print(f"[F1] Building Floor: NOT FOUND")
    
    # Check if pools have individual floors
    for pool_id in TEST_ROBOT_IDS:
        pool_floor_path = f"/World/Pools/Pool_{pool_id}/Floor"
        pool_floor = stage.GetPrimAtPath(pool_floor_path)
        print(f"[F3] Pool_{pool_id} Floor: {'EXISTS' if pool_floor.IsValid() else 'NOT FOUND (uses Building floor)'}")


def check_wheel_collision_children(robot_id):
    print(f"\n{'='*60}")
    print(f"Robot {robot_id} Wheel Collision Children")
    print(f"{'='*60}")
    
    stage = get_current_stage()
    robot_root = f"/World/Pools/Pool_{robot_id}/Robot/dingo"
    
    for wheel_name in ["left_wheel_link", "right_wheel_link"]:
        wheel_path = f"{robot_root}/{wheel_name}"
        wheel_prim = stage.GetPrimAtPath(wheel_path)
        
        if not wheel_prim.IsValid():
            print(f"[W] {wheel_name}: NOT FOUND")
            continue
        
        print(f"\n[W] {wheel_name} children:")
        for child in wheel_prim.GetChildren():
            child_path = str(child.GetPath())
            has_collision = child.HasAPI(UsdPhysics.CollisionAPI)
            child_type = child.GetTypeName()
            print(f"     {child.GetName()} ({child_type}): CollisionAPI={'OK' if has_collision else 'NO'}")
            
            # Check grandchildren too
            for grandchild in child.GetChildren():
                gc_has_collision = grandchild.HasAPI(UsdPhysics.CollisionAPI)
                gc_type = grandchild.GetTypeName()
                print(f"       -> {grandchild.GetName()} ({gc_type}): CollisionAPI={'OK' if gc_has_collision else 'NO'}")


def check_physics_scene():
    print(f"\n{'='*60}")
    print("Physics Scene Settings")
    print(f"{'='*60}")
    
    stage = get_current_stage()
    
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.Scene):
            print(f"[P] PhysicsScene: {prim.GetPath()}")
            
            try:
                from pxr import PhysxSchema
                physx_api = PhysxSchema.PhysxSceneAPI(prim)
                
                gpu_enabled = physx_api.GetEnableGPUDynamicsAttr().Get()
                broadphase = physx_api.GetBroadphaseTypeAttr().Get()
                solver = physx_api.GetSolverTypeAttr().Get()
                
                print(f"    GPU Dynamics: {gpu_enabled}")
                print(f"    Broadphase: {broadphase}")
                print(f"    Solver: {solver}")
            except Exception as e:
                print(f"    PhysX API error: {e}")


# Run
print("Floor and collision diagnosis starting...")
check_floor()
check_physics_scene()

for rid in TEST_ROBOT_IDS:
    check_wheel_collision_children(rid)

print(f"\n{'='*60}")
print("Diagnosis complete!")
print(f"{'='*60}")
