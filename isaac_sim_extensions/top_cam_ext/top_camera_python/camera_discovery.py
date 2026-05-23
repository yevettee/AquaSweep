"""Find every per-pool top-down camera on the stage.

Same shape as under_cam_ext's discovery, with two differences:
- a positive INCLUDE filter (must contain a "top*camera" token)
- a slightly different EXCLUDE list (drops hippo's onboard cameras)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import omni.usd

from .global_variables import EXCLUDE_TOKENS, INCLUDE_TOKENS, POOL_ID_REGEX


@dataclass(frozen=True)
class CameraEntry:
    pool_id: int
    prim_path: str


def discover_top_cameras() -> list[CameraEntry]:
    """Walk the current stage, returning one CameraEntry per pool."""
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
        if not any(tok in lower for tok in INCLUDE_TOKENS):
            continue
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
    """Prefer the team-standard name `top_cam_{N}` when present."""
    target = f"top_cam_{pool_id}"
    for p in paths:
        if p.rsplit("/", 1)[-1].lower() == target:
            return p
    return paths[0]


def format_entries(entries: Iterable[CameraEntry]) -> str:
    items = list(entries)
    if not items:
        return "(no top-down cameras discovered)"
    lines = [f"  pool_{e.pool_id:>2}  ->  {e.prim_path}" for e in items]
    return "\n".join(lines)
