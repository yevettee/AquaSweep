"""UI panel for top_cam_ext. Mirrors under_cam_ext.ui_builder."""

from __future__ import annotations

import json
import omni.timeline
import omni.ui as ui
import omni.usd
from isaacsim.gui.components.element_wrappers import CollapsableFrame
from isaacsim.gui.components.ui_utils import get_style

from . import ros_graph_builder
from .camera_discovery import CameraEntry, discover_top_cameras, format_entries
from .global_variables import DEFAULT_RESOLUTION
from .fish_gt_publisher import FishGTPublisher


class UIBuilder:
    def __init__(self):
        self.frames = []
        self.wrapped_ui_elements = []
        self._timeline = omni.timeline.get_timeline_interface()

        self._entries: list[CameraEntry] = []
        self._status_label: ui.Label | None = None
        self._discover_label: ui.Label | None = None
        self._gt_status_label: ui.Label | None = None
        self._resolution = DEFAULT_RESOLUTION
        
        # Fish GT Publisher
        self._gt_publisher = FishGTPublisher()
        self._gt_enabled = False
        self._gt_frame_count = 0
        self._rclpy_node = None
        self._gt_publishers = {}  # pool_id -> publisher

    # ---- lifecycle hooks called by extension.py ----------------------------

    def on_menu_callback(self):
        pass

    def on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.STOP):
            self._gt_enabled = False
            self._set_gt_status("GT publishing stopped (timeline stopped)")

    def on_physics_step(self, step: float):
        """Publish fish GT on each physics step if enabled."""
        if not self._gt_enabled:
            return
        
        self._gt_frame_count += 1
        
        # Publish every 10 frames (~3Hz at 30fps physics)
        if self._gt_frame_count % 10 != 0:
            return
        
        try:
            # Get current stage
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return
            
            self._gt_publisher.set_stage(stage)
            
            # Collect GT for all pools
            gt_data = self._gt_publisher.collect_all_pools(num_pools=7)
            
            # Publish via ROS2 if available
            if self._rclpy_node is not None:
                self._publish_gt_ros2(gt_data)
            
        except Exception as e:
            print(f"GT publish error: {e}")

    def on_stage_event(self, event):
        self._entries = []
        self._refresh_discover_label()
        self._gt_enabled = False

    def cleanup(self):
        self._gt_enabled = False
        self._cleanup_ros2()
        for w in self.wrapped_ui_elements:
            try:
                w.cleanup()
            except Exception:
                pass
    
    def _init_ros2_gt_publishers(self):
        """Initialize ROS2 publishers for GT data."""
        try:
            # Use Isaac's ROS environment
            import sys
            from pathlib import Path
            
            # Try to import from common ros_isaac_env
            common_path = Path(__file__).parent.parent.parent / "common"
            if common_path.exists() and str(common_path) not in sys.path:
                sys.path.insert(0, str(common_path))
            
            try:
                from ros_isaac_env import configure_isaac_ros_env
                configure_isaac_ros_env()
            except ImportError:
                pass
            
            import rclpy
            from rclpy.node import Node
            from std_msgs.msg import String
            
            if not rclpy.ok():
                rclpy.init()
            
            self._rclpy_node = rclpy.create_node('fish_gt_publisher')
            
            # Create publishers for each pool
            for pool_id in range(1, 8):
                self._gt_publishers[pool_id] = self._rclpy_node.create_publisher(
                    String,
                    f'/pool_{pool_id}/fish_gt',
                    10
                )
            
            return True
            
        except Exception as e:
            print(f"ROS2 GT publisher init failed: {e}")
            print("GT will be collected but not published to ROS2")
            return False
    
    def _publish_gt_ros2(self, gt_data: dict):
        """Publish GT data to ROS2 topics."""
        if self._rclpy_node is None:
            return
        
        try:
            from std_msgs.msg import String
            
            for pool_id, fish_list in gt_data.items():
                if pool_id not in self._gt_publishers:
                    continue
                
                msg = String()
                msg.data = json.dumps({
                    f"pool_{pool_id}": [f.to_dict() for f in fish_list]
                })
                self._gt_publishers[pool_id].publish(msg)
                
        except Exception as e:
            print(f"GT ROS2 publish error: {e}")
    
    def _cleanup_ros2(self):
        """Cleanup ROS2 resources."""
        try:
            if self._rclpy_node is not None:
                self._rclpy_node.destroy_node()
                self._rclpy_node = None
            self._gt_publishers.clear()
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

        publish_frame = CollapsableFrame("Image Publishing", collapsed=False)
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

        # Fish Ground Truth Publishing
        gt_frame = CollapsableFrame("Fish Ground Truth", collapsed=False)
        with gt_frame:
            with ui.VStack(style=get_style(), spacing=6, height=0):
                ui.Label(
                    "Publish fish GT (position, species, status) to /pool_N/fish_gt",
                    word_wrap=True, height=0,
                )
                ui.Button(
                    "Start GT Publishing",
                    height=0,
                    clicked_fn=self._on_start_gt,
                    tooltip="Start publishing fish ground truth on physics step. "
                            "Used for YOLO training and performance evaluation.",
                )
                ui.Button(
                    "Stop GT Publishing",
                    height=0,
                    clicked_fn=self._on_stop_gt,
                    tooltip="Stop GT publishing.",
                )
                self._gt_status_label = ui.Label(
                    "(GT idle)", word_wrap=True, height=0,
                )

        self.frames.extend([cameras_frame, publish_frame, gt_frame])

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

    def _on_start_gt(self):
        """Start fish GT publishing."""
        if self._gt_enabled:
            self._set_gt_status("GT already running")
            return
        
        # Initialize ROS2 publishers
        ros_ok = self._init_ros2_gt_publishers()
        
        self._gt_enabled = True
        self._gt_frame_count = 0
        
        if ros_ok:
            self._set_gt_status("GT publishing started (ROS2 enabled)")
        else:
            self._set_gt_status("GT publishing started (ROS2 not available)")
    
    def _on_stop_gt(self):
        """Stop fish GT publishing."""
        self._gt_enabled = False
        self._cleanup_ros2()
        self._set_gt_status("GT publishing stopped")

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
    
    def _set_gt_status(self, text: str):
        if self._gt_status_label is not None:
            self._gt_status_label.text = text
