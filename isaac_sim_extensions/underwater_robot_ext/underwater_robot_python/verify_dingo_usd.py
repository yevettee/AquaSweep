#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""로봇 USD 구조·치수가 global_variables 와 일치하는지 오프라인 검증 (Isaac Sim 불필요)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

try:
    from pxr import Usd, UsdGeom, UsdPhysics
except ImportError:
    print("SKIP: pip install usd-core 후 재실행", file=sys.stderr)
    sys.exit(0)

if __package__:
    from . import global_variables as gv
else:
    import global_variables as gv  # type: ignore

_EXT_DATA = Path(__file__).resolve().parents[1] / "data" / gv.DINGO_USD_FILENAME


def main() -> int:
    if not _EXT_DATA.is_file():
        print(f"FAIL: missing {_EXT_DATA}")
        return 1

    stage = Usd.Stage.Open(str(_EXT_DATA))
    dingo = stage.GetPrimAtPath("/Root/dingo")
    if not dingo.IsValid():
        print("FAIL: /Root/dingo not found")
        return 1

    wheel_radius = None
    wheel_pos = {}
    footprint_xy = None

    for prim in Usd.PrimRange(dingo):
        path = str(prim.GetPath())
        if path.endswith("left_wheel_link/collisions") and prim.GetTypeName() == "Cylinder":
            wheel_radius = float(UsdGeom.Cylinder(prim).GetRadiusAttr().Get())
        name = prim.GetName()
        if name in ("left_wheel_link", "right_wheel_link"):
            t = (
                UsdGeom.Xformable(prim)
                .ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                .ExtractTranslation()
            )
            wheel_pos[name] = (float(t[0]), float(t[1]))
        if name == "base_link":
            cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
            sz = cache.ComputeWorldBound(prim).GetRange().GetSize()
            footprint_xy = max(float(sz[0]), float(sz[1]))

    errors = []
    if wheel_radius is None:
        errors.append("wheel cylinder radius not found")
    elif abs(wheel_radius - gv.DINGO_WHEEL_RADIUS_M) > 0.002:
        errors.append(f"wheel_radius {wheel_radius} != {gv.DINGO_WHEEL_RADIUS_M}")

    if len(wheel_pos) != 2:
        errors.append("left/right wheel_link not found")
    else:
        wb = math.hypot(
            wheel_pos["left_wheel_link"][0] - wheel_pos["right_wheel_link"][0],
            wheel_pos["left_wheel_link"][1] - wheel_pos["right_wheel_link"][1],
        )
        if abs(wb - gv.DINGO_WHEEL_BASE_M) > 0.01:
            errors.append(f"wheel_base {wb:.4f} != {gv.DINGO_WHEEL_BASE_M}")

    if footprint_xy is None:
        errors.append("base_link bbox not found")
    elif abs(footprint_xy - gv.ROBOT_FOOTPRINT_M) > 0.02:
        errors.append(f"footprint {footprint_xy:.4f} != {gv.ROBOT_FOOTPRINT_M}")

    for joint_name in ("left_wheel_joint", "right_wheel_joint"):
        found = any(p.GetName() == joint_name for p in Usd.PrimRange(dingo))
        if not found:
            errors.append(f"missing joint {joint_name}")

    visual_wheels = None
    for prim in Usd.PrimRange(dingo):
        if prim.GetName() == "VisualWheels":
            visual_wheels = prim
            break
    has_tracks = visual_wheels is not None and visual_wheels.IsValid()
    if has_tracks:
        parent = visual_wheels.GetParent()
        if parent.GetName() != "base_link":
            errors.append(
                f"VisualWheels parent is {parent.GetPath()} — move under base_link for chassis rotation"
            )

    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1

    print(f"OK: {gv.DINGO_USD_FILENAME} matches global_variables")
    print(f"  wheel_radius={wheel_radius:.4f} wheel_base={wb:.4f} footprint_xy={footprint_xy:.4f}")
    print(f"  VisualWheels under base_link: {has_tracks}")
    print(f"  wheel_dof_names: left_wheel_joint, right_wheel_joint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
