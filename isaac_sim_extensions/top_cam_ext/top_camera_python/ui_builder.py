"""UI panel for top_cam_ext. Mirrors under_cam_ext.ui_builder."""

from __future__ import annotations

import omni.timeline
import omni.ui as ui
from isaacsim.gui.components.element_wrappers import CollapsableFrame
from isaacsim.gui.components.ui_utils import get_style

from . import ros_graph_builder
from .camera_discovery import CameraEntry, discover_top_cameras, format_entries
from .global_variables import DEFAULT_RESOLUTION


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()

        self._entries: list[CameraEntry] = []
        self._status_label: ui.Label | None = None
        self._discover_label: ui.Label | None = None
        self._resolution = DEFAULT_RESOLUTION

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

        publish_frame = CollapsableFrame("Publishing", collapsed=False)
        with publish_frame:
            with ui.VStack(style=get_style(), spacing=6, height=0):
                ui.Button(
                    "Build & start publishing",
                    height=0,
                    clicked_fn=self._on_build,
                    tooltip="Create the OmniGraph that publishes every "
                            "discovered top camera to /pool_N/top_img_raw.",
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

        self.frames.extend([cameras_frame, publish_frame])

    # ---- button handlers --------------------------------------------------

    def _on_discover(self):
        self._entries = discover_top_cameras()
        self._refresh_discover_label()

    def _on_build(self):
        if not self._entries:
            self._entries = discover_top_cameras()
            self._refresh_discover_label()
        ok, message = ros_graph_builder.build_graph(
            self._entries, resolution=self._resolution
        )
        self._set_status(("OK: " if ok else "FAIL: ") + message)

    def _on_stop(self):
        ros_graph_builder.teardown_graph()
        self._set_status("Stopped. Graph removed.")

    # ---- helpers ----------------------------------------------------------

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
