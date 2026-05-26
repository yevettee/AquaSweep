#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bake VisualWheels subtree into a single Mesh prim (asset-prep, one-shot).

Reads:  data/hippo_v1.usd
Writes: data/hippo_v1_combined.usd  (original is never modified)

Original VisualWheels has 1,032 Mesh prims (Caterpillar 390F treads, left+right)
with 1,034 unique material bindings -> 1,000+ draw calls per frame.

This script:
  1. Collects every Mesh under /Root/hippo/base_link/VisualWheels
  2. Transforms each mesh's points into VisualWheels-local space
  3. Concatenates points + face indices into a single combined mesh
  4. Deactivates the original child prims
  5. Creates /Root/hippo/base_link/VisualWheels/CombinedTracks (single Mesh)
  6. Binds one shared material (/Root/hippo/Looks/material_dark_grey)

After running: GUI-verify the new file, then switch HIPPO_USD_FILENAME in
global_variables.py.

Usage:
  PYTHONPATH=/home/rokey/dev_ws/isaac_sim/isaacsim/_build/target-deps/usd/release/lib/python \\
    python3 bake_visual_wheels.py [input.usd] [output.usd]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt
except ImportError:
    print("SKIP: pxr not found. Set PYTHONPATH to Isaac Sim's usd lib.", file=sys.stderr)
    sys.exit(0)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DEFAULT_SRC = _DATA_DIR / "hippo_v1.usd"
_DEFAULT_DST = _DATA_DIR / "hippo_v1_combined.usd"

VW_PATH = "/Root/hippo/base_link/VisualWheels"
COMBINED_PRIM_PATH = f"{VW_PATH}/CombinedTracks"
FALLBACK_MATERIAL_PATH = "/Root/hippo/Looks/material_dark_grey"


def _collect_meshes(vw_prim: Usd.Prim) -> list[tuple]:
    """Return list of (points, fvc, fvi, prim_to_vw_matrix) tuples."""
    cache = UsdGeom.XformCache()
    vw_to_world = cache.GetLocalToWorldTransform(vw_prim)
    world_to_vw = vw_to_world.GetInverse()

    meshes = []
    for prim in Usd.PrimRange(vw_prim):
        if prim.GetTypeName() != "Mesh":
            continue
        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get()
        fvc = mesh.GetFaceVertexCountsAttr().Get()
        fvi = mesh.GetFaceVertexIndicesAttr().Get()
        if not pts or not fvc or not fvi:
            continue

        prim_to_world = cache.GetLocalToWorldTransform(prim)
        prim_to_vw = prim_to_world * world_to_vw
        meshes.append((pts, fvc, fvi, prim_to_vw))
    return meshes


def _bake(meshes: list[tuple]) -> tuple:
    """Concatenate all meshes into single point/index arrays in VW-local space.

    Normals are intentionally not baked — Hydra computes face normals automatically.
    Transforming normals correctly requires inverse-transpose of upper-3x3 which
    is fragile across parent xforms with non-uniform scale; skipping avoids that.
    """
    out_points: list[Gf.Vec3f] = []
    out_fvc: list[int] = []
    out_fvi: list[int] = []

    vertex_offset = 0
    for pts, fvc, fvi, mat in meshes:
        for p in pts:
            xp = mat.Transform(Gf.Vec3d(float(p[0]), float(p[1]), float(p[2])))
            out_points.append(Gf.Vec3f(float(xp[0]), float(xp[1]), float(xp[2])))

        out_fvi.extend(int(i) + vertex_offset for i in fvi)
        out_fvc.extend(int(c) for c in fvc)
        vertex_offset += len(pts)

    return out_points, out_fvc, out_fvi


def bake_file(src: Path, dst: Path) -> int:
    if not src.is_file():
        print(f"FAIL: source not found: {src}")
        return 1

    print(f"copying  {src.name} -> {dst.name}")
    shutil.copy2(src, dst)

    stage = Usd.Stage.Open(str(dst))
    vw = stage.GetPrimAtPath(VW_PATH)
    if not vw.IsValid():
        print(f"FAIL: {VW_PATH} not found in {dst}")
        return 1

    print("collecting source meshes...")
    meshes = _collect_meshes(vw)
    orig_mesh_count = len(meshes)
    orig_vert_count = sum(len(m[0]) for m in meshes)
    orig_face_count = sum(len(m[1]) for m in meshes)
    print(f"  found {orig_mesh_count} meshes  "
          f"({orig_vert_count:,} verts, {orig_face_count:,} faces)")

    print("baking into single mesh...")
    points, fvc, fvi = _bake(meshes)
    print(f"  baked: {len(points):,} verts, {len(fvc):,} faces")

    print(f"creating {COMBINED_PRIM_PATH}")
    combined_mesh = UsdGeom.Mesh.Define(stage, COMBINED_PRIM_PATH)
    combined_mesh.CreatePointsAttr(Vt.Vec3fArray(points))
    combined_mesh.CreateFaceVertexCountsAttr(Vt.IntArray(fvc))
    combined_mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(fvi))

    # Bind shared material (exists at /Root/hippo/Looks, outside VW subtree)
    mat_prim = stage.GetPrimAtPath(FALLBACK_MATERIAL_PATH)
    if mat_prim.IsValid():
        binding = UsdShade.MaterialBindingAPI.Apply(combined_mesh.GetPrim())
        binding.Bind(UsdShade.Material(mat_prim))
        print(f"  bound material: {FALLBACK_MATERIAL_PATH}")
    else:
        print(f"  WARN: {FALLBACK_MATERIAL_PATH} not found; combined mesh has no material")

    print("removing original children (destructive — output file only)...")
    combined_path = combined_mesh.GetPrim().GetPath()
    paths_to_remove = [
        child.GetPath() for child in vw.GetChildren()
        if child.GetPath() != combined_path
    ]
    for path in paths_to_remove:
        stage.RemovePrim(path)

    print("saving...")
    stage.GetRootLayer().Save()

    src_size = src.stat().st_size
    dst_size = dst.stat().st_size
    print()
    print("=== DONE ===")
    print(f"  meshes:   {orig_mesh_count} -> 1")
    print(f"  verts:    {orig_vert_count:,} -> {len(points):,}")
    print(f"  faces:    {orig_face_count:,} -> {len(fvc):,}")
    print(f"  file:     {src_size/1024/1024:.2f} MB -> {dst_size/1024/1024:.2f} MB "
          f"({100*dst_size/src_size:.1f}%)")
    print()
    print(f"Output: {dst}")
    print("Verify in Isaac Sim GUI, then set HIPPO_USD_FILENAME in global_variables.py.")
    return 0


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_DST
    return bake_file(src, dst)


if __name__ == "__main__":
    sys.exit(main())
