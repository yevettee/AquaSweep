"""Find every underwater pool camera currently present on the stage.

The verification script proved that stage traversal with a name-based
filter works on the team's existing aquafarm scenes (Pool_1..Pool_7).
This module keeps the same approach so the extension survives whichever
naming convention the scene happens to use at any given moment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import omni.usd

from .global_variables import EXCLUDE_TOKENS, POOL_ID_REGEX


@dataclass(frozen=True)
class CameraEntry:
    """One under-water camera discovered on the stage."""

    pool_id: int
    prim_path: str


def discover_under_cameras() -> list[CameraEntry]:
    """Walk the current stage and return one CameraEntry per pool.

    Selection rules, in order:
      1. Keep prims of type "Camera" only.
      2. Drop any path whose lower-cased form contains an EXCLUDE_TOKENS
         entry (top-camera, realsense, stereo, viewport gizmos, …).
      3. Group by pool id (extracted from "pool_<N>" / "Pool_<N>" in the
         path). If a path has no recognisable pool id, assign one in the
         order it was found.
      4. Within a pool, prefer a prim literally named "under_cam_<N>" if
         present (team interface naming); otherwise fall back to the
         first remaining candidate.
    """
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return []

    by_pool: dict[int, list[str]] = {}
    fallback_seq = 0
    pool_re = re.compile(POOL_ID_REGEX)

    for prim in stage.Traverse():
        if prim.GetTypeName() != "Camera":
            continue
        path = str(prim.GetPath())
        lower = path.lower()
        if any(tok in lower for tok in EXCLUDE_TOKENS):
            continue

        match = pool_re.search(path)
        if match:
            pool_id = int(match.group(1))
        else:
            fallback_seq += 1
            pool_id = fallback_seq

        by_pool.setdefault(pool_id, []).append(path)

    entries: list[CameraEntry] = []
    for pool_id, paths in sorted(by_pool.items()):
        chosen = _pick_within_pool(paths, pool_id)
        entries.append(CameraEntry(pool_id=pool_id, prim_path=chosen))
    return entries


def _pick_within_pool(paths: list[str], pool_id: int) -> str:
    """Prefer team-standard names; otherwise take the first candidate."""
    target = f"under_cam_{pool_id}"
    for p in paths:
        if p.rsplit("/", 1)[-1].lower() == target:
            return p
    return paths[0]


def format_entries(entries: Iterable[CameraEntry]) -> str:
    """Human-readable summary for logs / UI status line."""
    items = list(entries)
    if not items:
        return "(no underwater cameras discovered)"
    lines = [f"  pool_{e.pool_id:>2}  ->  {e.prim_path}" for e in items]
    return "\n".join(lines)
