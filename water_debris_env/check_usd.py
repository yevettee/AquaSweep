import sys
from omni.isaac.kit import SimulationApp
simulation_app = SimulationApp({"headless": True})

from pxr import Usd, Sdf
import os

camera_usd_path = "/home/rokey/water_ws/src/water_debris_env/src/water_debris_env/camera.usd"
cad_usd_path = "/home/rokey/water_ws/src/water_debris_env/src/water_debris_env/LOW-LIGHT-HD-USB-CAMERA-R1.usd"

print("Checking camera.usd...")
if os.path.exists(camera_usd_path):
    stage = Usd.Stage.Open(camera_usd_path)
    print("=== camera.usd Prim Structure & References ===")
    for prim in stage.Traverse():
        print(f"Prim: {prim.GetPath()}, Type: {prim.GetTypeName()}")
        if prim.HasAuthoredReferences():
            print("  Has references!")
            # Get SdfReference list
            for prim_spec in prim.GetPrimStack():
                for ref in prim_spec.referenceList.GetAddedOrExplicitItems():
                    print(f"    -> Reference: assetPath='{ref.assetPath}', primPath='{ref.primPath}'")
else:
    print("camera.usd does not exist!")

print("\nChecking LOW-LIGHT-HD-USB-CAMERA-R1.usd...")
if os.path.exists(cad_usd_path):
    stage = Usd.Stage.Open(cad_usd_path)
    print("=== LOW-LIGHT-HD-USB-CAMERA-R1.usd Prim Structure & References ===")
    for prim in stage.Traverse():
        if prim.HasAuthoredReferences():
            print(f"Prim {prim.GetPath()} has references:")
            for prim_spec in prim.GetPrimStack():
                for ref in prim_spec.referenceList.GetAddedOrExplicitItems():
                    print(f"    -> Reference: assetPath='{ref.assetPath}', primPath='{ref.primPath}'")
        if prim.HasAttribute("inputs:file"):
            val = prim.GetAttribute("inputs:file").Get()
            print(f"Prim {prim.GetPath()} has texture: {val}")
else:
    print("LOW-LIGHT-HD-USB-CAMERA-R1.usd does not exist!")

simulation_app.close()
