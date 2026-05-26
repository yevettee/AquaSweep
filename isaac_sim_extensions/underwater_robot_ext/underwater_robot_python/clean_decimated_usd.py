#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Clean up Blender-exported USD: strip scene scaffolding + reset rotation + fix unit.

Blender USD export always includes:
  - Default Light, Camera, env_light prims (scene scaffolding)
  - A spurious X+90 rotation on imported OBJ meshes (Y-up convention assumption)
  - metersPerUnit=1.0 (Blender default)

This script processes:
  data/caterpillar_decimate01.usd   -> caterpillar_decimate01_clean.usd
  data/caterpillar_decimate005.usd  -> caterpillar_decimate005_clean.usd

Output is a minimal USD with just /root/CombinedTracks/CombinedTracks (mesh).
metersPerUnit=0.01 to match hippo_v1.usd convention.

Usage:
  PYTHONPATH=/home/rokey/dev_ws/isaac_sim/isaacsim/_build/target-deps/usd/release/lib/python \\
    python3 clean_decimated_usd.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    from pxr import Sdf, Usd, UsdGeom
except ImportError:
    print("SKIP: pxr not found. Set PYTHONPATH to Isaac Sim's usd lib.", file=sys.stderr)
    sys.exit(0)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Top-level prims to remove (Blender scene scaffolding)
_BLENDER_SCAFFOLD = {"Light", "Camera", "env_light"}

# Path to the Xform that wraps the imported mesh (Blender naming convention)
_WRAPPER_XFORM_PATH = "/root/CombinedTracks"


def clean_file(src: Path, dst: Path) -> int:
    if not src.is_file():
        print(f"FAIL: source not found: {src}")
        return 1

    print(f"\n=== {src.name} -> {dst.name} ===")
    shutil.copy2(src, dst)
    stage = Usd.Stage.Open(str(dst))
    root = stage.GetPrimAtPath("/root")
    if not root.IsValid():
        print(f"FAIL: /root prim not found in {dst}")
        return 1

    # 1) Remove Blender scaffolding (Light, Camera, env_light)
    removed = []
    for child in list(root.GetChildren()):
        if child.GetName() in _BLENDER_SCAFFOLD:
            removed.append(child.GetName())
            stage.RemovePrim(child.GetPath())
    print(f"  removed scaffolding: {removed}")

    # 2) Reset rotateXYZ on the wrapper Xform (Y-up artifact from OBJ import)
    wrapper = stage.GetPrimAtPath(_WRAPPER_XFORM_PATH)
    if wrapper.IsValid() and wrapper.IsA(UsdGeom.Xformable):
        xf = UsdGeom.Xformable(wrapper)
        ops = xf.GetOrderedXformOps()
        kept_ops = []
        cleared = []
        for op in ops:
            if op.GetOpType() in (UsdGeom.XformOp.TypeRotateXYZ,
                                  UsdGeom.XformOp.TypeRotateX,
                                  UsdGeom.XformOp.TypeRotateY,
                                  UsdGeom.XformOp.TypeRotateZ):
                cleared.append(op.GetOpName())
                wrapper.RemoveProperty(op.GetName())
                continue
            kept_ops.append(op)
        xf.SetXformOpOrder(kept_ops)
        print(f"  cleared rotation ops: {cleared}")

    # 3) Set metersPerUnit to match hippo USD (numerical values stay the same;
    #    only metadata changes to reflect actual unit convention)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    print(f"  metersPerUnit -> 0.01")

    # 4) Ensure defaultPrim is set so references can target the file without specifying a path
    stage.SetDefaultPrim(root)
    print(f"  defaultPrim   -> /root")

    stage.GetRootLayer().Save()
    size_mb = dst.stat().st_size / 1024 / 1024
    print(f"  saved: {dst.name} ({size_mb:.2f} MB)")
    return 0


def main() -> int:
    targets = [
        ("caterpillar_decimate01.usd",  "caterpillar_decimate01_clean.usd"),
        ("caterpillar_decimate005.usd", "caterpillar_decimate005_clean.usd"),
    ]
    rc = 0
    for src_name, dst_name in targets:
        rc |= clean_file(_DATA_DIR / src_name, _DATA_DIR / dst_name)
    return rc


if __name__ == "__main__":
    sys.exit(main())
