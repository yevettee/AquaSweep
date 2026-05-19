import omni
from omni.isaac.core.utils.prims import create_prim
from pxr import UsdGeom, Gf
import omni.graph.core as og
from omni.isaac.core.utils.extensions import enable_extension


class CameraSystem:
    """
    Blue Robotics Low-Light HD USB Camera 규격 기반의 카메라 센서 생성 및
    ROS 2 OmniGraph Bridge 통신을 전담하는 클래스.
    
    팀원 사용법:
        1. camera.usd 파일을 Stage에 Reference로 추가
        2. setup_ros2_omnigraph_bridge()를 호출하여 ROS 2 토픽 발행 활성화
    """

    def __init__(self, prim_path="/World/Camera", position=(0.0, 0.0, 2.5),
                 rotation=(0.0, 0.0, 0.0), resolution=(1280, 720)):
        """
        Args:
            prim_path (str): USD 상의 카메라 경로
            position (tuple): 카메라의 월드 위치 (X, Y, Z)
            rotation (tuple): Euler 회전 (Roll, Pitch, Yaw) 도 단위. (0,0,0) = 아래쪽 바라봄
            resolution (tuple): 카메라 이미지 해상도 (Width, Height)
        """
        self.prim_path = prim_path
        self.position = position
        self.rotation = rotation
        self.resolution = resolution
        self.camera_prim = None
        self.graph_path = "/World/ROS2_Camera_Graph"

    def spawn_camera(self, stage):
        """USD Stage에 카메라 센서 Prim을 생성합니다. (3D 외형 모델 없음 — 추후 에셋으로 교체)"""
        print(f"\n📷 [CameraSystem] 카메라 센서 생성 (경로: {self.prim_path})")

        self.camera_prim = stage.GetPrimAtPath(self.prim_path)
        if not self.camera_prim.IsValid():
            create_prim(
                prim_path=self.prim_path,
                prim_type="Camera",
                position=self.position,
                orientation=self._euler_to_quaternion(self.rotation)
            )
            self.camera_prim = stage.GetPrimAtPath(self.prim_path)
            print("  ✓ Camera Prim 생성 완료")
        else:
            print("  ✓ 이미 카메라 Prim이 존재합니다.")

        # 카메라 렌즈 속성 설정
        camera_geom = UsdGeom.Camera(self.camera_prim)
        camera_geom.CreateFocalLengthAttr(15.0)
        # Near/Far Clipping Range: 1cm ~ 100m (2.5m 아래 바닥이 반드시 보이도록)
        camera_geom.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100.0))
        print("  ✓ 렌즈 속성 설정 완료 (focal=15mm, clip=0.01~100m)")

    def _euler_to_quaternion(self, rotation):
        """Euler 각도를 USD Quaternion (W, X, Y, Z)으로 변환"""
        rot_x = Gf.Rotation(Gf.Vec3d(1, 0, 0), rotation[0])
        rot_y = Gf.Rotation(Gf.Vec3d(0, 1, 0), rotation[1])
        rot_z = Gf.Rotation(Gf.Vec3d(0, 0, 1), rotation[2])
        final_rot = rot_z * rot_y * rot_x
        q = final_rot.GetQuaternion()
        real_val = float(q.GetReal())
        imag_val = q.GetImaginary()
        return [real_val, float(imag_val[0]), float(imag_val[1]), float(imag_val[2])]

    # =========================================================================
    # 🛰️ ROS 2 통신 연동 (OmniGraph ROS2 Camera Bridge)
    # =========================================================================

    def setup_ros2_omnigraph_bridge(self, topic_name="camera/image_raw",
                                    frame_id="camera_optical_frame"):
        """
        OmniGraph ROS2 Camera Bridge를 생성하여 카메라 이미지를 ROS2 토픽으로 발행합니다.
        
        Args:
            topic_name (str): 발행할 ROS 2 토픽명
            frame_id (str): TF frame ID
        """
        print(f"\n🛰️ [CameraSystem] OmniGraph ROS2 Bridge 구성 (토픽: {topic_name})...")

        enable_extension("isaacsim.core.nodes")
        enable_extension("isaacsim.ros2.bridge")
        print("  ✓ 확장 프로그램 활성화 완료")

        controller = og.Controller()

        import omni.usd
        stage = omni.usd.get_context().get_stage()
        graph_prim = stage.GetPrimAtPath(self.graph_path)
        if graph_prim.IsValid():
            stage.RemovePrim(self.graph_path)

        graph_config = {"graph_path": self.graph_path, "evaluator_name": "execution"}

        try:
            controller.edit(graph_config, {
                og.Controller.Keys.CREATE_NODES: [
                    ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                    ("CreateRenderProduct", "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                    ("ROS2CameraHelper", "isaacsim.ros2.bridge.ROS2CameraHelper"),
                ],
                og.Controller.Keys.CONNECT: [
                    ("OnPlaybackTick.outputs:tick", "CreateRenderProduct.inputs:execIn"),
                    ("CreateRenderProduct.outputs:execOut", "ROS2CameraHelper.inputs:execIn"),
                    ("CreateRenderProduct.outputs:renderProductPath",
                     "ROS2CameraHelper.inputs:renderProductPath"),
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
