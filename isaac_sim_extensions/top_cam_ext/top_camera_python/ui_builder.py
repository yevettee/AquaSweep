"""UI panel for top_cam_ext. Mirrors under_cam_ext.ui_builder."""

from __future__ import annotations

import omni.timeline
import omni.ui as ui
import omni.usd
from isaacsim.gui.components.element_wrappers import CollapsableFrame
from isaacsim.gui.components.ui_utils import get_style

from . import ros_graph_builder

from .camera_discovery import (
    CameraEntry,
    GlobalCameraEntry,
    discover_top_cameras,
    discover_global_camera,
    format_entries,
)
from .global_variables import DEFAULT_RESOLUTION, GLOBAL_RESOLUTION


NUM_POOLS = 7


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()

        self._entries: list[CameraEntry] = []
        self._global_entry: GlobalCameraEntry | None = None
        self._status_label: ui.Label | None = None
        self._discover_label: ui.Label | None = None
        self._global_status_label: ui.Label | None = None
        self._resolution = DEFAULT_RESOLUTION
        
        # Pool selection checkboxes (1-indexed pool_id -> checkbox model)
        self._pool_checkboxes: dict[int, ui.SimpleBoolModel] = {}
        for pool_id in range(1, NUM_POOLS + 1):
            self._pool_checkboxes[pool_id] = ui.SimpleBoolModel(True)  # default: all selected

    # ---- lifecycle hooks called by extension.py ----------------------------

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        pass

    def on_physics_step(self, step: float):
        pass

    def on_stage_event(self, event):
        self._entries = []
        self._refresh_discover_label()

    def cleanup(self):
        for w in self.wrapped_ui_elements:
            try:
                w.cleanup()
            except Exception:
                pass

    # ---- UI ---------------------------------------------------------------

    def build_ui(self):
        cameras_frame = CollapsableFrame("Top Cameras", collapsed=False)
        with cameras_frame:
            with ui.VStack(style=get_style(), spacing=6, height=0):
                ui.Button(
                    "Discover cameras",
                    height=0,
                    clicked_fn=self._on_discover,
                    tooltip="Scan the current stage for per-pool top-down cameras.",
                )
                self._discover_label = ui.Label(
                    "(not scanned yet)", word_wrap=True, height=0,
                )

        publish_frame = CollapsableFrame("Per-Pool Publishing (selective)", collapsed=True)
        with publish_frame:
            with ui.VStack(style=get_style(), spacing=6, height=0):
                ui.Label(
                    "Select pools to publish. Each pool = 1 GPU render pass.",
                    word_wrap=True, height=0,
                )
                
                # Pool selection checkboxes (2 rows: 1-4, 5-7)
                with ui.HStack(spacing=4, height=0):
                    for pool_id in range(1, 5):
                        ui.CheckBox(model=self._pool_checkboxes[pool_id], width=16)
                        ui.Label(f"Pool {pool_id}", width=50)
                with ui.HStack(spacing=4, height=0):
                    for pool_id in range(5, NUM_POOLS + 1):
                        ui.CheckBox(model=self._pool_checkboxes[pool_id], width=16)
                        ui.Label(f"Pool {pool_id}", width=50)
                
                # Select all / none buttons
                with ui.HStack(spacing=4, height=0):
                    ui.Button("Select All", height=0, clicked_fn=self._select_all_pools, width=80)
                    ui.Button("Select None", height=0, clicked_fn=self._select_no_pools, width=80)
                
                ui.Button(
                    "Build selected cameras",
                    height=0,
                    clicked_fn=self._on_build,
                    tooltip="Create OmniGraph for selected pool cameras.",
                )
                ui.Button(
                    "Stop publishing",
                    height=0,
                    clicked_fn=self._on_stop,
                    tooltip="Delete the publishing graph.",
                )
                self._status_label = ui.Label(
                    "(idle)", word_wrap=True, height=0,
                )

        # Global Camera Publishing (recommended for performance)
        global_frame = CollapsableFrame("Global Camera (1 camera, recommended)", collapsed=False)
        with global_frame:
            with ui.VStack(style=get_style(), spacing=6, height=0):
                ui.Label(
                    "Single camera viewing all pools. 86% fewer GPU render passes. "
                    "Detection node crops pool regions from 1920x1440 image.",
                    word_wrap=True, height=0,
                )
                ui.Button(
                    "Build global camera graph",
                    height=0,
                    clicked_fn=self._on_build_global,
                    tooltip="Create OmniGraph for /World/GlobalTopCamera. "
                            "Publishes to /global/top_img_raw at 1920x1440.",
                )
                ui.Button(
                    "Stop global camera",
                    height=0,
                    clicked_fn=self._on_stop_global,
                    tooltip="Delete the global camera graph.",
                )
                self._global_status_label = ui.Label(
                    "(idle)", word_wrap=True, height=0,
                )

        self.frames.extend([cameras_frame, global_frame, publish_frame])

    # ---- button handlers --------------------------------------------------

    def _on_discover(self):
        self._entries = discover_top_cameras()
        self._refresh_discover_label()

    def _on_build(self):
        if not self._entries:
            self._entries = discover_top_cameras()
            self._refresh_discover_label()
        
        # Get selected pool IDs
        selected_pools = self._get_selected_pools()
        if not selected_pools:
            self._set_status("FAIL: No pools selected.")
            return
        
        # Automatically apply camera 20mm and Stage Light setting (handled in ros_graph_builder.build_graph)
        ok, message = ros_graph_builder.build_graph(
            self._entries,
            resolution=self._resolution,
            selected_pools=selected_pools,
        )
        self._set_status(("OK: " if ok else "FAIL: ") + message)

    def _on_stop(self):
        ros_graph_builder.teardown_graph()
        self._set_status("Stopped. Graph removed.")

    def _on_build_global(self):
        """Build and start publishing the global camera."""
        self._global_entry = discover_global_camera()
        if self._global_entry is None:
            self._set_global_status("FAIL: GlobalTopCamera not found. Run LOAD first.")
            return
        
        # Automatically apply camera 20mm and Stage Light setting (handled in ros_graph_builder.build_global_graph)
        ok, message = ros_graph_builder.build_global_graph(
            self._global_entry, resolution=GLOBAL_RESOLUTION
        )
        self._set_global_status(("OK: " if ok else "FAIL: ") + message)

    def _on_stop_global(self):
        """Stop global camera publishing."""
        ros_graph_builder.teardown_global_graph()
        self._set_global_status("Stopped. Global graph removed.")

    # ---- helpers ----------------------------------------------------------
    
    def _get_selected_pools(self) -> list[int]:
        """Get list of selected pool IDs (1-indexed)."""
        return [
            pool_id for pool_id, model in self._pool_checkboxes.items()
            if model.get_value_as_bool()
        ]
    
    def _select_all_pools(self):
        """Select all pool checkboxes."""
        for model in self._pool_checkboxes.values():
            model.set_value(True)
    
    def _select_no_pools(self):
        """Deselect all pool checkboxes."""
        for model in self._pool_checkboxes.values():
            model.set_value(False)

    def _refresh_discover_label(self):
        if self._discover_label is None:
            return
        if not self._entries:
            self._discover_label.text = "(not scanned yet)"
            return
        header = f"Found {len(self._entries)} top camera(s):"
        self._discover_label.text = header + "\n" + format_entries(self._entries)

    def _set_status(self, text: str):
        if self._status_label is not None:
            self._status_label.text = text

    def _set_global_status(self, text: str):
        if self._global_status_label is not None:
            self._global_status_label.text = text
