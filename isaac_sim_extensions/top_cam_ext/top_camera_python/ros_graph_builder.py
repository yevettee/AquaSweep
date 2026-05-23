"""Build / tear down the single OmniGraph that publishes every pool's
top-down camera. Mirrors under_cam_ext.ros_graph_builder."""

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
    import omni.graph.core as og

    entries = list(entries)
    if not entries:
        return False, "No top-down cameras to publish."

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
        f"Publishing {len(entries)} top camera(s) "
        f"at {resolution[0]}x{resolution[1]}."
    )
    return True, msg
