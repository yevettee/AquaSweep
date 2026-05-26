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
        # 1. Collect render product paths BEFORE deleting the graph
        rp_paths = _collect_render_product_paths(GRAPH_PATH)
        
        # 2. Set render product prims inactive immediately to stop Hydra rendering
        stage = omni.usd.get_context().get_stage()
        if stage is not None and rp_paths:
            for rp_path in rp_paths:
                try:
                    prim = stage.GetPrimAtPath(rp_path)
                    if prim and prim.IsValid():
                        prim.SetActive(False)
                except Exception:
                    pass
        
        # 3. Delete the graph first (stops the rendering pipeline)
        omni.kit.commands.execute("DeletePrims", paths=[GRAPH_PATH])
        
        # 4. Schedule render product cleanup after a frame update
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
        
        # Try to use Replicator's ViewportManager to cleanly destroy the render products first
        try:
            from omni.replicator.core.scripts.utils.viewport_manager import ViewportManager
            vm = ViewportManager()
        except Exception as e:
            vm = None
            carb.log_warn(f"[under_cam] Failed to import Replicator ViewportManager: {e}")
            
        for rp_path in rp_paths:
            destroyed_by_replicator = False
            if vm is not None:
                # Try all available contexts to find and destroy the texture
                contexts = list(vm._hydra_textures._hydra_textures.keys())
                if "default" not in contexts:
                    contexts.append("default")
                if None not in contexts:
                    contexts.append(None)
                    
                for ctx in contexts:
                    try:
                        texture = vm._hydra_textures.get(ctx, rp_path)
                        if texture is not None:
                            texture.destroy()
                            destroyed_by_replicator = True
                            carb.log_info(f"[under_cam] Cleanly destroyed replicator render product: {rp_path} in context '{ctx}'")
                            break
                    except Exception:
                        pass
            
            # Fallback if Replicator couldn't destroy it or wasn't available
            if not destroyed_by_replicator:
                try:
                    prim = stage.GetPrimAtPath(rp_path)
                    if prim and prim.IsValid():
                        stage.RemovePrim(rp_path)
                        carb.log_info(f"[under_cam] Fallback destroyed render product prim: {rp_path}")
                except Exception as e:
                    carb.log_warn(f"[under_cam] Failed fallback destroy for {rp_path}: {e}")
            
    except Exception as e:
        import carb
        carb.log_warn(f"[under_cam] _destroy_render_products error: {e}")


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
