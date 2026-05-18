import omni
from omni.isaac.core.utils.prims import create_prim
from pxr import UsdGeom, Gf
import omni.graph.core as og
from omni.isaac.core.utils.extensions import enable_extension

class CameraSystem:
    def __init__(self, prim_path="/World/Camera", position=(0.0, 0.0, 2.5), rotation=(0.0, 180.0, 0.0), resolution=(640, 480)):
        """
        카메라 생성 및 ROS 2 통신을 전담하는 클래스
        
        Args:
            prim_path (str): USD 상의 카메라 경로
            position (tuple): 카메라의 월드 위치 (X, Y, Z)
            rotation (tuple): 카메라의 회전 값 (Roll, Pitch, Yaw) - 도(Degree) 단위
            resolution (tuple): 카메라 이미지 해상도 (Width, Height)
        """
        self.prim_path = prim_path
        self.position = position
        self.rotation = rotation
        self.resolution = resolution
        self.camera_prim = None
        self.graph_path = "/World/ROS2_Camera_Graph"

    def spawn_camera(self, stage):
        """USD Stage 상에 카메라 Prim을 생성하고 위치와 회전을 설정합니다."""
        print(f"\n📷 [CameraSystem] 카메라 생성 시작 (경로: {self.prim_path})")
        
        # 1. USD Camera Prim 생성
        self.camera_prim = stage.GetPrimAtPath(self.prim_path)
        if not self.camera_prim.IsValid():
            # omni.isaac.core.utils.prims를 사용해 생성
            create_prim(
                prim_path=self.prim_path,
                prim_type="Camera",
                position=self.position,
                orientation=self._euler_to_quaternion(self.rotation)
            )
            self.camera_prim = stage.GetPrimAtPath(self.prim_path)
            print("  ✓ USD Camera Prim 생성 완료")
        else:
            print("  ✓ 이미 카메라 Prim이 존재합니다.")

        # 2. 카메라의 기본 속성 조정 (초점 거리 등)
        camera_geom = UsdGeom.Camera(self.camera_prim)
        camera_geom.CreateFocalLengthAttr(15.0)  # 예시 초점 거리 설정
        print("  ✓ 카메라 렌즈 속성 설정 완료")

    def _euler_to_quaternion(self, rotation):
        """Euler 각도를 USD Quaternion (W, X, Y, Z)으로 변환"""
        rot_x = Gf.Rotation(Gf.Vec3d(1, 0, 0), rotation[0])
        rot_y = Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation[1])
        rot_z = Gf.Rotation(Gf.Vec3d(0, 0, 1), rotation[2])
        final_rot = rot_z * rot_y * rot_x
        q = final_rot.GetQuaternion()
        return q

    # =========================================================================
    # 🛰️ ROS 2 통신 연동 설계 (OmniGraph ROS2 Camera Bridge)
    # =========================================================================

    def setup_ros2_omnigraph_bridge(self, topic_name="camera/image_raw", frame_id="camera_optical_frame"):
        """
        OmniGraph ROS2 Camera Bridge를 생성하여 카메라 데이터를 ROS2 토픽으로 고속 퍼블리시합니다.
        GPU Direct 렌더링 파이프라인을 사용해 성능을 최대화합니다.
        
        Args:
            topic_name (str): 발행할 ROS 2 토픽명
            frame_id (str): ROS 2 메시지 헤더에 매핑될 TF frame ID
        """
        print(f"\n🛰️ [CameraSystem] OmniGraph ROS2 Camera Bridge 구성 중 (토픽: {topic_name})...")
        
        # 1. ROS 2 Bridge 확장 프로그램 활성화
        try:
            enable_extension("omni.isaac.ros2_bridge")
            print("  ✓ omni.isaac.ros2_bridge 확장 프로그램 활성화 완료")
        except Exception as e:
            print(f"  ⚠️ 확장 프로그램 활성화 중 경고 (이미 켜져 있을 수 있음): {e}")

        # 2. Action Graph 생성 및 편집
        controller = og.Controller()
        
        # 기존에 동일한 경로의 그래프가 있으면 제거하여 꼬임 방지
        graph_prim = og.Controller.get_graph_by_path(self.graph_path)
        if graph_prim:
            print(f"  ✓ 기존에 존재하는 {self.graph_path} 제거 후 재구성")
            controller.edit({"graph_path": self.graph_path}, {og.Controller.Keys.DELETE_NODES: [self.graph_path]})

        # 그래프 정의 및 연결
        graph_config = {"graph_path": self.graph_path, "evaluator_name": "execution"}
        
        try:
            controller.edit(graph_config, {
                og.Controller.Keys.CREATE_NODES: [
                    ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                    ("CreateRenderProduct", "omni.isaac.core_nodes.IsaacCreateRenderProduct"),
                    ("ROS2CameraHelper", "omni.isaac.ros2_bridge.ROS2CameraHelper"),
                ],
                og.Controller.Keys.CONNECT: [
                    ("OnPlaybackTick.outputs:tick", "CreateRenderProduct.inputs:execIn"),
                    ("CreateRenderProduct.outputs:execOut", "ROS2CameraHelper.inputs:execIn"),
                    ("CreateRenderProduct.outputs:renderProductPath", "ROS2CameraHelper.inputs:renderProductPath"),
                ],
                og.Controller.Keys.SET_VALUES: [
                    ("CreateRenderProduct.inputs:cameraPrim", [self.prim_path]),
                    ("CreateRenderProduct.inputs:width", self.resolution[0]),
                    ("CreateRenderProduct.inputs:height", self.resolution[1]),
                    ("ROS2CameraHelper.inputs:type", "rgb"),
                    ("ROS2CameraHelper.inputs:topicName", topic_name),
                    ("ROS2CameraHelper.inputs:frameId", frame_id),
                ]
            })
            print("  ✓ OmniGraph ROS2 Bridge 구축 성공!")
        except Exception as e:
            print(f"  ❌ OmniGraph 구축 실패: {e}")
            raise e
