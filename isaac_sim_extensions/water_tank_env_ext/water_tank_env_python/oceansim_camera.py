"""OceanSim UW_Camera 헬퍼.

OceanSim이 설치되지 않은 환경에서도 extension이 로드되도록
모든 import를 런타임까지 지연하고 OCEANSIM_AVAILABLE 플래그로 분기한다.
"""
import os

try:
    from isaacsim.oceansim.sensors.UW_Camera import UW_Camera as _UW_Camera
    OCEANSIM_AVAILABLE = True
except ImportError:
    _UW_Camera = None
    OCEANSIM_AVAILABLE = False

DEFAULT_RESOLUTION = (1280, 720)
DEFAULT_FOCAL_LENGTH = 2.1  # ≈80° horizontal FOV

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "oceansim_configs")

YAML_BY_TURBIDITY = {
    "clear":  os.path.join(_CONFIG_DIR, "water_clear.yaml"),
    "medium": os.path.join(_CONFIG_DIR, "water_medium.yaml"),
    "turbid": os.path.join(_CONFIG_DIR, "water_turbid.yaml"),
}

TURBIDITY_LABELS = list(YAML_BY_TURBIDITY.keys())  # ["clear", "medium", "turbid"]


def discover_camera_prims(stage) -> list:
    """Stage를 순회하여 Camera 타입 prim 경로 목록을 반환한다."""
    return [str(p.GetPath()) for p in stage.Traverse() if p.GetTypeName() == "Camera"]


def create_uw_camera(prim_path: str, turbidity: str = "medium",
                     resolution=DEFAULT_RESOLUTION,
                     ros2_topic_name: str = None):
    """OceanSim UW_Camera를 생성·초기화하여 반환한다.

    Args:
        ros2_topic_name: ROS2 토픽명. 지정 시 탁도 이미지를 해당 토픽으로 발행한다.
    """
    if not OCEANSIM_AVAILABLE:
        return None
    if turbidity not in YAML_BY_TURBIDITY:
        turbidity = "medium"

    cam = _UW_Camera(prim_path=prim_path, resolution=resolution)
    cam.set_focal_length(DEFAULT_FOCAL_LENGTH)
    cam.set_clipping_range(0.05, 50.0)
    cam.initialize(
        UW_yaml_path=YAML_BY_TURBIDITY[turbidity],
        viewport=True,
        ros2_topic_name=ros2_topic_name,
    )
    return cam
