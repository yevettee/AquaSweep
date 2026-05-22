"""Constants and tunable defaults for under_cam_ext.

These are gathered in one place so the UI / extension can expose them
later without hunting through modules.
"""

EXTENSION_TITLE = "under.camera"
EXTENSION_DESCRIPTION = (
    "Publishes every pool's underwater camera as raw sensor_msgs/Image "
    "via a single OmniGraph fanning out to one ROS2CameraHelper per pool."
)

# OmniGraph location on the stage (root-level so it works regardless of
# whether the scene uses /World or /Item_NN/World as its top group).
GRAPH_PATH = "/under_cam_graph"

# ROS2
TOPIC_TEMPLATE = "/pool_{pool_id}/under_img_raw"
FRAME_ID_TEMPLATE = "pool_{pool_id}_under_cam_{pool_id}"
DEFAULT_RESOLUTION = (1280, 720)  # (width, height)

# Camera-prim selection.
#
# The discovery walks every Camera-type prim on the stage, then keeps only
# the ones that look like an under-water robot camera (i.e. NOT a top
# camera, NOT a realsense / stereo helper, NOT a viewport gizmo).
#
# Tokens listed here cause a path to be rejected (case-insensitive substring
# match). Add team-specific names as the USD naming convention firms up.
EXCLUDE_TOKENS = (
    "realsense",
    "stereo",
    "topcamera",
    "top_cam",
    "omniversekit",
)

# When the prim path contains a "pool_<N>" or "Pool_<N>" segment we use that
# integer as the pool id. Otherwise we fall back to assigning sequential
# ids starting from 1 in stage-traversal order.
POOL_ID_REGEX = r"[Pp]ool[_-]?(\d+)"
