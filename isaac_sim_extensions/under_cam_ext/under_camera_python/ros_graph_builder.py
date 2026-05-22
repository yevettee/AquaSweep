"""Build / tear down the single OmniGraph that publishes every pool's
underwater camera.

Architecture (validated by the verify script):

    OnPlaybackTick ─┬─ IsaacCreateRenderProduct (pool 1) ─ ROS2CameraHelper → /pool_1/under_img_raw
                    ├─ IsaacCreateRenderProduct (pool 2) ─ ROS2CameraHelper → /pool_2/under_img_raw
                    └─ ... one chain per discovered pool

Why one graph, not one per pool: a single Action Graph with one
OnPlaybackTick + one ROS2Context is the lowest-overhead form; multiple
graphs only add scheduler bookkeeping for no rendering benefit.

Why `cameraPrim` is wrapped in `Sdf.Path` and passed as a *list*: that
input is a target relationship, not a string attribute, so a bare string
silently fails in og.Controller.edit.
"""

from __future__ import annotations

import traceback
from typing import Iterable

import omni.kit.commands
import omni.usd
from pxr import Sdf

from .camera_discovery import CameraEntry
from .global_variables import (
    DEFAULT_RESOLUTION,
    FRAME_ID_TEMPLATE,
    GRAPH_PATH,
    TOPIC_TEMPLATE,
)


def topic_for(pool_id: int) -> str:
    return TOPIC_TEMPLATE.format(pool_id=pool_id)


def frame_id_for(pool_id: int) -> str:
    return FRAME_ID_TEMPLATE.format(pool_id=pool_id)


def graph_exists() -> bool:
    stage = omni.usd.get_context().get_stage()
    return stage is not None and stage.GetPrimAtPath(GRAPH_PATH).IsValid()


def teardown_graph() -> None:
    """Delete the graph prim. Render products owned by the graph go with
    it, so the ROS2 publishers stop cleanly."""
    if not graph_exists():
        return
    try:
        omni.kit.commands.execute("DeletePrims", paths=[GRAPH_PATH])
    except Exception:
        traceback.print_exc()


def build_graph(
    entries: Iterable[CameraEntry],
    *,
    resolution: tuple[int, int] = DEFAULT_RESOLUTION,
) -> tuple[bool, str]:
    """Create the graph and one render-product + publisher chain per entry.

    Returns:
        (success, message). On failure `message` contains a short reason
        suitable for the UI status line; full traceback is printed.
    """
    import omni.graph.core as og

    entries = list(entries)
    if not entries:
        return False, "No under-water cameras to publish."

    # Always rebuild from scratch — simpler than diffing.
    teardown_graph()

    create_nodes: list[tuple[str, str]] = [
        ("OnTick", "omni.graph.action.OnPlaybackTick"),
    ]
    set_values: list[tuple[str, object]] = []
    connect: list[tuple[str, str]] = []

    for e in entries:
        rp_name = f"CreateRP_{e.pool_id}"
        helper_name = f"CamHelper_{e.pool_id}"

        create_nodes.append((rp_name, "isaacsim.core.nodes.IsaacCreateRenderProduct"))
        create_nodes.append((helper_name, "isaacsim.ros2.bridge.ROS2CameraHelper"))

        set_values.extend([
            (f"{rp_name}.inputs:cameraPrim", [Sdf.Path(e.prim_path)]),
            (f"{rp_name}.inputs:width", resolution[0]),
            (f"{rp_name}.inputs:height", resolution[1]),
            (f"{helper_name}.inputs:type", "rgb"),
            (f"{helper_name}.inputs:topicName", topic_for(e.pool_id)),
            (f"{helper_name}.inputs:frameId", frame_id_for(e.pool_id)),
        ])

        connect.extend([
            ("OnTick.outputs:tick", f"{rp_name}.inputs:execIn"),
            (f"{rp_name}.outputs:execOut", f"{helper_name}.inputs:execIn"),
            (f"{rp_name}.outputs:renderProductPath",
             f"{helper_name}.inputs:renderProductPath"),
        ])

    try:
        keys = og.Controller.Keys
        og.Controller.edit(
            {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: create_nodes,
                keys.SET_VALUES: set_values,
                keys.CONNECT: connect,
            },
        )
    except Exception:
        traceback.print_exc()
        return False, "OmniGraph build raised; see kit log."

    msg = (
        f"Publishing {len(entries)} camera(s) "
        f"at {resolution[0]}x{resolution[1]}."
    )
    return True, msg
