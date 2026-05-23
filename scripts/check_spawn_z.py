"""Check actual ROBOT_SPAWN_Z_M value in memory.

Run in Isaac Sim Script Editor.
"""

# Method 1: Direct import from underwater_robot_python
try:
    from underwater_robot_python.global_variables import ROBOT_SPAWN_Z_M
    print(f"[1] underwater_robot_python.global_variables.ROBOT_SPAWN_Z_M = {ROBOT_SPAWN_Z_M}")
except Exception as e:
    print(f"[1] ERROR: {e}")

# Method 2: Check aquasweep_ext's imported value
try:
    import aquasweep_python.ui_builder as aqua_ui
    print(f"[2] aquasweep_python.ui_builder.ROBOT_SPAWN_Z_M = {aqua_ui.ROBOT_SPAWN_Z_M}")
except Exception as e:
    print(f"[2] ERROR: {e}")

# Method 3: Check _robot_specs() output
try:
    from aquasweep_python.ui_builder import _robot_specs
    specs = _robot_specs()
    print(f"[3] _robot_specs() z values:")
    for idx, scene_name, spawn_path, robot_root, position in specs:
        print(f"    Robot {idx}: z = {position[2]}")
except Exception as e:
    print(f"[3] ERROR: {e}")

# Method 4: Read file directly
try:
    import os
    gv_path = "/home/woody/AquaSweep/isaac_sim_extensions/underwater_robot_ext/underwater_robot_python/global_variables.py"
    with open(gv_path, 'r') as f:
        for line in f:
            if 'ROBOT_SPAWN_Z_M' in line and '=' in line:
                print(f"[4] File content: {line.strip()}")
except Exception as e:
    print(f"[4] ERROR: {e}")

print("\nIf [1-3] show 0.05 but [4] shows 0.08, it's a module caching issue.")
print("Solution: Disable and re-enable the aquasweep extension, or restart Isaac Sim.")
