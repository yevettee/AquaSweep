"""Constants and tunable defaults for top_cam_ext.

Mirrors `under_cam_ext.global_variables` but targets the per-pool
TopCamera (looking straight down) instead of the under-water robot
camera. Kept as a separate file rather than imported from sibling ext
because Isaac Sim extensions are loaded independently.
"""

EXTENSION_TITLE = "top.camera"
EXTENSION_DESCRIPTION = (
    "Publishes every pool's top-down camera as raw sensor_msgs/Image "
    "via a single OmniGraph fanning out to one ROS2CameraHelper per pool."
)

GRAPH_PATH = "/top_cam_graph"

TOPIC_TEMPLATE = "/pool_{pool_id}/top_img_raw"
FRAME_ID_TEMPLATE = "pool_{pool_id}_top_cam_{pool_id}"
DEFAULT_RESOLUTION = (1280, 720)

# Selection — opposite polarity from under_cam_ext: we *require* a "top"
# token in the path and reject anything that looks like an under-water
# robot camera, realsense, stereo helper, or viewport gizmo.
INCLUDE_TOKENS = (
    "topcamera",
    "top_cam",
    "top_camera",
)
EXCLUDE_TOKENS = (
    "under_cam",
    "undercam",
    "realsense",
    "stereo",
    "omniversekit",
    "/dingo/",        # legacy dingo USD's onboard cameras
    "/hippo/",        # hippo USD's onboard under_cam (under_cam_ext takes those)
)

POOL_ID_REGEX = r"[Pp]ool[_-]?(\d+)"
