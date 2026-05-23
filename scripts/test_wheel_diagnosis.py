"""Wheel physics diagnosis script.

Run in Isaac Sim Script Editor.
"""

from isaacsim.core.api.world import World
from isaacsim.core.utils.stage import get_current_stage
from pxr import UsdPhysics, PhysxSchema
import numpy as np

TEST_ROBOT_IDS = [1, 5]  # Compare non-moving robot 1 vs working robot 5


def diagnose_robot(robot_id):
    print(f"\n{'='*60}")
    print(f"Robot {robot_id} Diagnosis")
    print(f"{'='*60}")
    
    world = World.instance()
    stage = get_current_stage()
    
    scene_name = f"dingo_{robot_id}"
    robot_root = f"/World/Pools/Pool_{robot_id}/Robot/dingo"
    
    # 1. WheeledRobot object check
    try:
        robot = world.scene.get_object(scene_name)
        print(f"[1] WheeledRobot object: {'OK' if robot else 'NOT FOUND'}")
    except Exception as e:
        print(f"[1] WheeledRobot object: ERROR - {e}")
        return
    
    # 2. Robot position
    try:
        pos, orient = robot.get_world_pose()
        print(f"[2] Robot position: x={pos[0]:.2f}, y={pos[1]:.2f}, z={pos[2]:.4f}")
    except Exception as e:
        print(f"[2] Robot position: ERROR - {e}")
    
    # 3. DOF (joint) info
    try:
        dof_names = robot.dof_names
        print(f"[3] DOF names: {dof_names}")
        
        dof_positions = robot.get_joint_positions()
        print(f"[4] Joint positions: {dof_positions}")
        
        dof_velocities = robot.get_joint_velocities()
        print(f"[5] Joint velocities: {dof_velocities}")
    except Exception as e:
        print(f"[3-5] DOF info: ERROR - {e}")
    
    # 4. Articulation Root check
    root_prim = stage.GetPrimAtPath(robot_root)
    if root_prim.IsValid():
        has_articulation = root_prim.HasAPI(UsdPhysics.ArticulationRootAPI)
        print(f"[6] ArticulationRootAPI: {'OK' if has_articulation else 'MISSING!'}")
    else:
        print(f"[6] Robot root prim: NOT FOUND")
    
    # 5. Wheel joint drive settings
    for wheel_name in ["left_wheel_joint", "right_wheel_joint"]:
        joint_path = f"{robot_root}/{wheel_name}"
        joint_prim = stage.GetPrimAtPath(joint_path)
        
        if not joint_prim.IsValid():
            print(f"[7] {wheel_name}: NOT FOUND at {joint_path}")
            continue
        
        # DriveAPI check
        has_drive = joint_prim.HasAPI(UsdPhysics.DriveAPI)
        print(f"[7] {wheel_name} DriveAPI: {'OK' if has_drive else 'MISSING!'}")
        
        if has_drive:
            # Read drive properties
            drive = UsdPhysics.DriveAPI.Get(joint_prim, "angular")
            if drive:
                stiffness = drive.GetStiffnessAttr().Get() if drive.GetStiffnessAttr() else "N/A"
                damping = drive.GetDampingAttr().Get() if drive.GetDampingAttr() else "N/A"
                max_force = drive.GetMaxForceAttr().Get() if drive.GetMaxForceAttr() else "N/A"
                print(f"    stiffness={stiffness}, damping={damping}, maxForce={max_force}")
    
    # 6. base_link RigidBody check
    base_link_path = f"{robot_root}/base_link"
    base_prim = stage.GetPrimAtPath(base_link_path)
    if base_prim.IsValid():
        has_rigid = base_prim.HasAPI(UsdPhysics.RigidBodyAPI)
        print(f"[8] base_link RigidBodyAPI: {'OK' if has_rigid else 'MISSING!'}")
        
        # kinematic check (is it fixed?)
        if has_rigid:
            rigid_api = UsdPhysics.RigidBodyAPI(base_prim)
            kinematic_attr = rigid_api.GetKinematicEnabledAttr()
            is_kinematic = kinematic_attr.Get() if kinematic_attr else False
            print(f"[9] base_link kinematic (fixed): {is_kinematic}")
    
    # 7. Wheel collision check
    for wheel_name in ["left_wheel_link", "right_wheel_link"]:
        wheel_path = f"{robot_root}/{wheel_name}"
        wheel_prim = stage.GetPrimAtPath(wheel_path)
        if wheel_prim.IsValid():
            has_collision = wheel_prim.HasAPI(UsdPhysics.CollisionAPI)
            print(f"[10] {wheel_name} CollisionAPI: {'OK' if has_collision else 'MISSING!'}")


# Run
print("Wheel physics diagnosis starting...")
for rid in TEST_ROBOT_IDS:
    diagnose_robot(rid)

print(f"\n{'='*60}")
print("Diagnosis complete! Check differences between robot 1 and 5.")
print(f"{'='*60}")
