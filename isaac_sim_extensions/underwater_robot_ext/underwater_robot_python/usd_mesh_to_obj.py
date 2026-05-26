#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extract a single USD Mesh prim to .obj for external DCC handoff (Blender, etc.).

Usage:
  PYTHONPATH=/home/rokey/dev_ws/isaac_sim/isaacsim/_build/target-deps/usd/release/lib/python \\
    python3 usd_mesh_to_obj.py <input.usd> <mesh_prim_path> <output.obj>

Example (default — exports CombinedTracks for Blender decimation):
  PYTHONPATH=... python3 usd_mesh_to_obj.py

OBJ format notes:
  - 1-indexed face vertices
  - No normals / UVs (Blender recomputes after decimation)
  - Vertex positions written in USD-local units (cm for our hippo USD)
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from pxr import Usd, UsdGeom
except ImportError:
    print("SKIP: pxr not found. Set PYTHONPATH to Isaac Sim's usd lib.", file=sys.stderr)
    sys.exit(0)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DEFAULT_SRC = _DATA_DIR / "hippo_v1_combined.usd"
_DEFAULT_PRIM = "/Root/hippo/base_link/VisualWheels/CombinedTracks"
_DEFAULT_DST = _DATA_DIR / "combined_tracks.obj"


def export_obj(src: Path, prim_path: str, dst: Path) -> int:
    if not src.is_file():
        print(f"FAIL: source not found: {src}")
        return 1

    stage = Usd.Stage.Open(str(src))
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid() or prim.GetTypeName() != "Mesh":
        print(f"FAIL: {prim_path} is not a Mesh prim")
        return 1

    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    fvc = mesh.GetFaceVertexCountsAttr().Get()
    fvi = mesh.GetFaceVertexIndicesAttr().Get()

    if not points or not fvc or not fvi:
        print("FAIL: mesh has empty points / face data")
        return 1

    print(f"input:  {src.name}  prim={prim_path}")
    print(f"        {len(points):,} verts, {len(fvc):,} faces")
    print(f"writing {dst.name} ...")

    # Stream write — avoids building huge string in memory
    with dst.open("w", buffering=1024 * 1024) as f:
        f.write(f"# Exported from {src.name}\n")
        f.write(f"# prim: {prim_path}\n")
        f.write(f"# verts: {len(points)}, faces: {len(fvc)}\n")
        f.write("o CombinedTracks\n")

        # Vertices
        for p in points:
            f.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")

        # Faces — n-gon supported. OBJ is 1-indexed.
        cursor = 0
        for count in fvc:
            idxs = fvi[cursor : cursor + count]
            cursor += count
            f.write("f " + " ".join(str(int(i) + 1) for i in idxs) + "\n")

    size_mb = dst.stat().st_size / 1024 / 1024
    print(f"DONE:   {dst}  ({size_mb:.1f} MB)")
    return 0


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_SRC
    prim_path = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_PRIM
    dst = Path(sys.argv[3]) if len(sys.argv) > 3 else _DEFAULT_DST
    return export_obj(src, prim_path, dst)


if __name__ == "__main__":
    sys.exit(main())
