"""
under_cam_ext verification script — standard OmniGraph + ROS2CameraHelper.

Purpose
-------
Verify, with one camera, the chosen rendering path for `under_cam_ext`:

    [OnPlaybackTick]
        -> [IsaacCreateRenderProduct(camera_prim, resolution)]
        -> [ROS2CameraHelper(type="rgb")]  -> /pool_1/under_img_raw

This is the NVIDIA-recommended low-latency path: publishing runs in the
render thread, no Python per-frame callback.

OceanSim is intentionally NOT used. Underwater appearance is delivered by
changing the colour / opacity of the pool's water mesh material — see
set_water_color() below for the helper.

How to use
----------
1. Open Isaac Sim, open Script Editor (Window > Script Editor).
2. Paste this whole file into a new tab. Edit USD_PATH if needed.
3. Press the Script Editor RUN button (not Isaac PLAY).
4. Press Isaac PLAY (timeline play).
5. In another terminal:
       source /opt/ros/humble/setup.bash
       ros2 topic hz   /pool_1/under_img_raw       # FPS / period
       ros2 topic bw   /pool_1/under_img_raw       # bandwidth
       rqt_image_view  /pool_1/under_img_raw       # visual check
6. To exercise turbidity-by-water-color (only if a water mesh exists):
       set_water_color("clear")
       set_water_color("light_teal")
       set_water_color("teal")
   The function looks for a prim under WATER_PRIM_PATH; adjust as needed.
7. stop_verification() to tear everything down.

Outcome interpretation
----------------------
- `ros2 topic hz` reports near render-frame rate, `rqt_image_view` shows
  the live camera view, latency feels live → standard path confirmed,
  build `under_cam_ext` on this pattern for all 7 cameras.
- Topic exists but no frames arrive → render product not attached, or
  ROS2 bridge not loaded. Check the kit log.
- Topic missing → ROS2CameraHelper failed to register; isaacsim.ros2.bridge
  not enabled, or DDS env vars not set.
"""

import os

import omni.usd
from pxr import Gf, Sdf, UsdGeom, UsdShade


# -----------------------------------------------------------------------------
# Editable parameters
# -----------------------------------------------------------------------------

USD_PATH = (
    "/home/rokey/water_ws/src/isaac_sim_extensions/underwater_robot_ext/"
    "data/underwater_robot_camera_v1.usd"
)

# Where the robot reference is mounted on the stage (only used when the
# stage is empty — when a scene is already loaded with cameras, this is
# skipped).
REFERENCE_PRIM_PATH = "/verify_robot"

# Where to expect the pool's water mesh (only used by set_water_color).
# Edit this to point at whatever prim carries the water material in your
# current stage. If it doesn't exist, set_water_color() will print a hint.
# Examples seen in real scenes: "/Item_01/World/Pools/Pool_6/water",
# "/World/pools/pool_1/water" (team-standard naming).
WATER_PRIM_PATH = "/Item_01/World/Pools/Pool_6/water"

# Camera and ROS2 settings
RESOLUTION = (1280, 720)
ROS2_TOPIC = "/pool_1/under_img_raw"
ROS2_FRAME_ID = "pool_1_under_cam_1"

# OmniGraph location — root-level so it works regardless of whether the
# scene uses /World or /Item_01/World as its top-level group.
GRAPH_PATH = "/under_cam_verify_graph"

# Predefined water colour presets (linear RGB, alpha)
# Tuned for a teal-tinted glass-like material. Tweak in viewport if needed.
WATER_COLOR_PRESETS = {
    "clear":      (1.00, 1.00, 1.00, 0.05),   # nearly transparent
    "light_teal": (0.55, 0.90, 0.85, 0.35),   # slight teal haze
    "teal":       (0.10, 0.55, 0.50, 0.75),   # strong teal, low visibility
}


# -----------------------------------------------------------------------------
# Globals exposed to the Script Editor REPL
# -----------------------------------------------------------------------------

_graph_controller = None
_camera_prim_path = None


def _log(msg: str) -> None:
    print(f"[verify_under_cam] {msg}")


# -----------------------------------------------------------------------------
# Setup helpers
# -----------------------------------------------------------------------------

def _ensure_ros2_bridge() -> bool:
    import omni.kit.app

    manager = omni.kit.app.get_app().get_extension_manager()
    if not manager.is_extension_enabled("isaacsim.ros2.bridge"):
        _log("Enabling isaacsim.ros2.bridge")
        manager.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
    return manager.is_extension_enabled("isaacsim.ros2.bridge")


def _find_all_camera_prims() -> list[str]:
    """Return every Camera-type prim path on the current stage."""
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return []
    return [
        str(prim.GetPath())
        for prim in stage.Traverse()
        if prim.GetTypeName() == "Camera"
    ]


def _maybe_reference_robot_usd() -> None:
    """Reference underwater_robot_camera_v1.usd only when the current stage
    has no Camera prim. If the user already loaded a scene containing the
    robot (e.g. a Pool_N scene), we leave it alone."""
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        omni.usd.get_context().new_stage()
        stage = omni.usd.get_context().get_stage()

    if _find_all_camera_prims():
        _log("Stage already contains Camera prim(s). Skipping USD reference.")
        return

    if not stage.GetPrimAtPath(REFERENCE_PRIM_PATH).IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path(REFERENCE_PRIM_PATH))
        stage.GetPrimAtPath(REFERENCE_PRIM_PATH).GetReferences().AddReference(USD_PATH)
        _log(f"Empty stage: referenced {USD_PATH} -> {REFERENCE_PRIM_PATH}")
    else:
        _log(f"Reusing existing prim at {REFERENCE_PRIM_PATH}")


def _pick_main_camera(paths: list[str]) -> str | None:
    """Select the most likely under-water main camera from candidates.

    Priority, matching team interface doc (under_cam_*) first, then a
    generic "camera" while excluding realsense/stereo helper cameras.
    """
    if not paths:
        return None

    def lower_basename(p: str) -> str:
        return p.rsplit("/", 1)[-1].lower()

    def looks_team_standard(p: str) -> bool:
        return lower_basename(p).startswith("under_cam")

    def is_realsense_or_stereo(p: str) -> bool:
        pl = p.lower()
        return "realsense" in pl or "stereo" in pl

    team_standard = [p for p in paths if looks_team_standard(p)]
    if team_standard:
        return team_standard[0]

    generic_main = [
        p for p in paths
        if lower_basename(p) == "camera" and not is_realsense_or_stereo(p)
    ]
    if generic_main:
        return generic_main[0]

    non_helper = [p for p in paths if not is_realsense_or_stereo(p)]
    if non_helper:
        return non_helper[0]

    return paths[0]


def _find_camera_prim() -> str | None:
    paths = _find_all_camera_prims()
    if not paths:
        _log("No Camera prim on stage.")
        return None
    _log(f"Camera prims on stage ({len(paths)}):")
    for p in paths:
        _log(f"  - {p}")
    chosen = _pick_main_camera(paths)
    _log(f"Selected: {chosen}")
    _log("  (override by editing start_verification() to pass an explicit path)")
    return chosen


def _build_graph(camera_prim_path: str) -> None:
    """Programmatically build OnPlaybackTick -> IsaacCreateRenderProduct
    -> ROS2CameraHelper.

    Note: `IsaacCreateRenderProduct.inputs:cameraPrim` is a target
    relationship, not a string attribute. It must be assigned as a list
    of `Sdf.Path` objects via SET_VALUES; passing a bare string fails
    silently in og.Controller.edit.
    """
    import traceback

    import omni.graph.core as og

    try:
        keys = og.Controller.Keys
        og.Controller.edit(
            {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: [
                    ("OnTick",    "omni.graph.action.OnPlaybackTick"),
                    ("CreateRP",  "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                    ("CamHelper", "isaacsim.ros2.bridge.ROS2CameraHelper"),
                ],
                keys.SET_VALUES: [
                    ("CreateRP.inputs:cameraPrim", [Sdf.Path(camera_prim_path)]),
                    ("CreateRP.inputs:width",  RESOLUTION[0]),
                    ("CreateRP.inputs:height", RESOLUTION[1]),
                    ("CamHelper.inputs:type",      "rgb"),
                    ("CamHelper.inputs:topicName", ROS2_TOPIC),
                    ("CamHelper.inputs:frameId",   ROS2_FRAME_ID),
                ],
                keys.CONNECT: [
                    ("OnTick.outputs:tick", "CreateRP.inputs:execIn"),
                    ("CreateRP.outputs:execOut", "CamHelper.inputs:execIn"),
                    ("CreateRP.outputs:renderProductPath",
                     "CamHelper.inputs:renderProductPath"),
                ],
            },
        )
        _log(f"OmniGraph built at {GRAPH_PATH}")
    except Exception:
        _log("OmniGraph build FAILED:")
        traceback.print_exc()


# -----------------------------------------------------------------------------
# Water material helper — turbidity by colour
# -----------------------------------------------------------------------------

def set_water_color(preset: str) -> None:
    """Tint the pool water by editing the bound material's diffuse + opacity.

    Assumes the water prim under WATER_PRIM_PATH has a UsdShade material
    binding whose surface shader exposes `diffuseColor` and `opacity`
    inputs. This is the default for OmniPBR / UsdPreviewSurface materials.
    """
    if preset not in WATER_COLOR_PRESETS:
        _log(f"Unknown preset '{preset}'. Options: {list(WATER_COLOR_PRESETS)}.")
        return

    stage = omni.usd.get_context().get_stage()
    water = stage.GetPrimAtPath(WATER_PRIM_PATH)
    if not water.IsValid():
        _log(
            f"WATER_PRIM_PATH not found ({WATER_PRIM_PATH}). "
            "Edit WATER_PRIM_PATH in this script to point at the pool's "
            "water mesh prim, or skip this helper."
        )
        return

    binding_api = UsdShade.MaterialBindingAPI(water)
    material, _ = binding_api.ComputeBoundMaterial()
    if not material:
        _log(f"No bound material on {WATER_PRIM_PATH}.")
        return

    shader = material.ComputeSurfaceSource()[0]
    if not shader:
        _log(f"Material on {WATER_PRIM_PATH} has no surface shader.")
        return

    r, g, b, a = WATER_COLOR_PRESETS[preset]
    diffuse = shader.GetInput("diffuseColor")
    if diffuse:
        diffuse.Set(Gf.Vec3f(r, g, b))
    opacity = shader.GetInput("opacity")
    if opacity:
        opacity.Set(float(a))
    _log(f"Water color → '{preset}'  rgba=({r:.2f},{g:.2f},{b:.2f},{a:.2f})")


# -----------------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------------

def start_verification() -> None:
    global _camera_prim_path

    if not _ensure_ros2_bridge():
        _log("isaacsim.ros2.bridge could not be enabled. Abort.")
        return

    _maybe_reference_robot_usd()
    camera_prim_path = _find_camera_prim()
    if camera_prim_path is None:
        return
    _camera_prim_path = camera_prim_path

    _build_graph(camera_prim_path)
    _log(
        "Setup complete. Press Isaac PLAY to start publishing on "
        f"{ROS2_TOPIC}."
    )


def stop_verification() -> None:
    """Delete the OmniGraph prim. The render product is owned by the
    graph, so deleting the graph cleans up the publisher too."""
    import omni.kit.commands

    _log("Stopping.")
    try:
        omni.kit.commands.execute("DeletePrims", paths=[GRAPH_PATH])
    except Exception as exc:
        _log(f"DeletePrims raised: {exc}")


# Auto-start when the script is run.
start_verification()
