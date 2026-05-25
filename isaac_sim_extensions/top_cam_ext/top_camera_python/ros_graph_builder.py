"""Build / tear down the single OmniGraph that publishes every pool's
top-down camera. Mirrors under_cam_ext.ros_graph_builder.

Also supports a single global camera that views all pools at once,
reducing GPU render passes from 7 to 1 for significant performance gains.
"""

from __future__ import annotations

import traceback
from typing import Iterable, Optional

import omni.kit.commands
import omni.usd
from pxr import Sdf

from .camera_discovery import CameraEntry, GlobalCameraEntry
from .global_variables import (
    DEFAULT_RESOLUTION,
    FRAME_ID_TEMPLATE,
    GRAPH_PATH,
    TOPIC_TEMPLATE,
    GLOBAL_GRAPH_PATH,
    GLOBAL_TOPIC,
    GLOBAL_FRAME_ID,
    GLOBAL_RESOLUTION,
)

# 성능 최적화: 카메라 발행 프레임레이트 제한
# 24fps 시뮬레이션에서 step=3 → ~8fps 발행 (블러링 감소, detection 품질 향상)
PUBLISH_STEP_INTERVAL = 3


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
        # 1. Collect render product paths BEFORE deleting the graph
        rp_paths = _collect_render_product_paths(GRAPH_PATH)
        
        # 2. Delete the graph first (stops the rendering pipeline)
        omni.kit.commands.execute("DeletePrims", paths=[GRAPH_PATH])
        
        # 3. Schedule render product cleanup after a frame update
        # This allows Hydra to finish processing before we delete the prims
        if rp_paths:
            _schedule_render_product_cleanup(rp_paths)
    except Exception:
        traceback.print_exc()


def _schedule_render_product_cleanup(rp_paths: list[str]) -> None:
    """Schedule render product cleanup after next frame update."""
    import asyncio
    import omni.kit.app
    
    async def _cleanup_after_frame():
        # Wait for next frame update
        await omni.kit.app.get_app().next_update_async()
        # Now safe to delete render products
        _destroy_render_products_by_paths(rp_paths)
    
    # Run cleanup asynchronously
    try:
        asyncio.ensure_future(_cleanup_after_frame())
    except Exception:
        # Fallback: try immediate cleanup anyway
        _destroy_render_products_by_paths(rp_paths)


def _collect_render_product_paths(graph_path: str) -> list[str]:
    """Collect render product paths from IsaacCreateRenderProduct nodes in the graph."""
    rp_paths = []
    try:
        import omni.graph.core as og
        
        graph = og.get_graph_by_path(graph_path)
        if graph is None:
            return rp_paths
        
        for node in graph.get_nodes():
            node_type = node.get_type_name()
            if "CreateRenderProduct" in node_type:
                rp_attr = node.get_attribute("outputs:renderProductPath")
                if rp_attr is not None:
                    rp_path = rp_attr.get()
                    if rp_path:
                        rp_paths.append(str(rp_path))
    except Exception:
        pass
    return rp_paths


def _destroy_render_products_by_paths(rp_paths: list[str]) -> None:
    """Destroy render product prims by their paths to release GPU memory.
    
    Should be called AFTER the OmniGraph is deleted to avoid Hydra errors.
    """
    if not rp_paths:
        return
        
    try:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
            
        import carb
        for rp_path in rp_paths:
            try:
                prim = stage.GetPrimAtPath(rp_path)
                if prim and prim.IsValid():
                    stage.RemovePrim(rp_path)
                    carb.log_info(f"[top_cam] Destroyed render product: {rp_path}")
            except Exception as e:
                carb.log_warn(f"[top_cam] Failed to destroy render product {rp_path}: {e}")
            
    except Exception as e:
        import carb
        carb.log_warn(f"[top_cam] _destroy_render_products error: {e}")


def build_graph(
    entries: Iterable[CameraEntry],
    *,
    resolution: tuple[int, int] = DEFAULT_RESOLUTION,
    selected_pools: Optional[list[int]] = None,
) -> tuple[bool, str]:
    """Build OmniGraph for per-pool cameras.
    
    Args:
        entries: List of CameraEntry from discover_top_cameras()
        resolution: Output resolution (width, height)
        selected_pools: Optional list of pool IDs (1-indexed) to publish.
                       If None, all discovered cameras are published.
    
    Returns:
        (success, message) tuple
    """
    import omni.graph.core as og

    entries = list(entries)
    
    # Filter by selected pools if specified
    if selected_pools is not None:
        entries = [e for e in entries if e.pool_id in selected_pools]
    
    if not entries:
        return False, "No top-down cameras to publish (check selection)."

    teardown_graph()

    create_nodes: list[tuple[str, str]] = [
        ("OnTick", "omni.graph.action.OnPlaybackTick"),
        ("Gate", "isaacsim.core.nodes.IsaacSimulationGate"),  # 프레임레이트 제한
    ]
    set_values: list[tuple[str, object]] = [
        ("Gate.inputs:step", PUBLISH_STEP_INTERVAL),  # N tick마다 1번 발행
    ]
    connect: list[tuple[str, str]] = [
        ("OnTick.outputs:tick", "Gate.inputs:execIn"),  # OnTick → Gate
    ]

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
            ("Gate.outputs:execOut", f"{rp_name}.inputs:execIn"),  # Gate → CreateRP
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

    fps = 24 // PUBLISH_STEP_INTERVAL  # 대략적인 발행 fps (physics 24Hz 기준)
    msg = (
        f"Publishing {len(entries)} top camera(s) "
        f"at {resolution[0]}x{resolution[1]}, ~{fps}fps (step={PUBLISH_STEP_INTERVAL})."
    )
    return True, msg


# ── Global camera graph (single camera for all pools) ────────────────────────


def global_graph_exists() -> bool:
    """Check if the global camera OmniGraph exists."""
    stage = omni.usd.get_context().get_stage()
    return stage is not None and stage.GetPrimAtPath(GLOBAL_GRAPH_PATH).IsValid()


def teardown_global_graph() -> None:
    """Remove the global camera OmniGraph."""
    if not global_graph_exists():
        return
    try:
        # 1. Collect render product paths BEFORE deleting the graph
        rp_paths = _collect_render_product_paths(GLOBAL_GRAPH_PATH)
        
        # 2. Delete the graph first (stops the rendering pipeline)
        omni.kit.commands.execute("DeletePrims", paths=[GLOBAL_GRAPH_PATH])
        
        # 3. Schedule render product cleanup after a frame update
        if rp_paths:
            _schedule_render_product_cleanup(rp_paths)
    except Exception:
        traceback.print_exc()


def build_global_graph(
    entry: Optional[GlobalCameraEntry],
    *,
    resolution: tuple[int, int] = GLOBAL_RESOLUTION,
) -> tuple[bool, str]:
    """Build OmniGraph for the single global top-view camera.
    
    This publishes one large image covering all pools, reducing GPU
    render passes from 7 to 1. The detection node crops pool regions.
    
    Args:
        entry: GlobalCameraEntry from discover_global_camera()
        resolution: Output resolution (default 1920x1440)
    
    Returns:
        (success, message) tuple
    """
    import omni.graph.core as og

    if entry is None:
        return False, "Global camera not found on stage."

    teardown_global_graph()

    create_nodes: list[tuple[str, str]] = [
        ("OnTick", "omni.graph.action.OnPlaybackTick"),
        ("Gate", "isaacsim.core.nodes.IsaacSimulationGate"),
        ("CreateRP", "isaacsim.core.nodes.IsaacCreateRenderProduct"),
        ("CamHelper", "isaacsim.ros2.bridge.ROS2CameraHelper"),
    ]
    set_values: list[tuple[str, object]] = [
        ("Gate.inputs:step", PUBLISH_STEP_INTERVAL),
        ("CreateRP.inputs:cameraPrim", [Sdf.Path(entry.prim_path)]),
        ("CreateRP.inputs:width", resolution[0]),
        ("CreateRP.inputs:height", resolution[1]),
        ("CamHelper.inputs:type", "rgb"),
        ("CamHelper.inputs:topicName", GLOBAL_TOPIC),
        ("CamHelper.inputs:frameId", GLOBAL_FRAME_ID),
    ]
    connect: list[tuple[str, str]] = [
        ("OnTick.outputs:tick", "Gate.inputs:execIn"),
        ("Gate.outputs:execOut", "CreateRP.inputs:execIn"),
        ("CreateRP.outputs:execOut", "CamHelper.inputs:execIn"),
        ("CreateRP.outputs:renderProductPath", "CamHelper.inputs:renderProductPath"),
    ]

    try:
        keys = og.Controller.Keys
        og.Controller.edit(
            {"graph_path": GLOBAL_GRAPH_PATH, "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: create_nodes,
                keys.SET_VALUES: set_values,
                keys.CONNECT: connect,
            },
        )
    except Exception:
        traceback.print_exc()
        return False, "Global OmniGraph build raised; see kit log."

    fps = 24 // PUBLISH_STEP_INTERVAL  # physics 24Hz 기준
    msg = (
        f"Publishing global camera at {resolution[0]}x{resolution[1]}, "
        f"~{fps}fps (step={PUBLISH_STEP_INTERVAL}). "
        f"Topic: {GLOBAL_TOPIC}"
    )
    return True, msg
