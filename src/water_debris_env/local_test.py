"""
수중 이물질 감지 시뮬레이션 메인 실행기.

실행 방법 (이 한 줄이면 끝):
    /home/rokey/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/python.sh local_test.py

동작:
    1. Isaac Sim GUI 창이 자동으로 열립니다
    2. 바닥, 조명, Blue Robotics 카메라 에셋, 이물질 파티클 10개가 자동 배치됩니다
    3. ROS 2 OmniGraph Bridge가 자동 활성화됩니다 (토픽: cleaner/camera/image_raw)
    4. 뷰포트가 카메라 시야로 자동 전환됩니다
    5. 별도 터미널에서 perception 노드를 실행하면 OpenCV 디버그 화면을 볼 수 있습니다

perception 노드 실행법 (별도 터미널):
    source /opt/ros/humble/setup.bash && source ~/water_ws/install/setup.bash
    python3 ~/water_ws/src/water_debris_env/src/water_debris_env/perception.py
"""
import sys
import os
from omni.isaac.kit import SimulationApp

simulation_app = SimulationApp({"headless": "--headless" in sys.argv})

from omni.isaac.core import World
from omni.physx import acquire_physx_interface
from pxr import UsdLux, Sdf
from omni.isaac.core.utils.prims import create_prim
import omni.kit.viewport.utility as vp_utils
from water_debris_env.debris_system import DebrisSystem
from water_debris_env.camera_system import CameraSystem

# Blue Robotics 카메라 에셋 USD 경로 (실제 3D 메시)
CAMERA_ASSET_USD = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "LOW-LIGHT-HD-USB-CAMERA-R1.usd"
)


def main():
    print("\n🚀 수중 이물질 감지 시뮬레이션 시작")
    print("=" * 50)

    # 1. 월드 생성 (팀 표준: 120Hz 물리 루프)
    world = World(
        physics_dt=1.0 / 120.0,
        rendering_dt=1.0 / 60.0,
        stage_units_in_meters=1.0,
        backend="torch",
        device="cpu"
    )

    # [GPU 강제 인식 스위치] — 팀 가이드 §3 필수 적용
    acquire_physx_interface().overwrite_gpu_setting(1)

    world.scene.add_default_ground_plane()
    stage = world.stage

    # 2. 조명 배치
    if not stage.GetPrimAtPath("/World/DistantLight").IsValid():
        create_prim("/World/DistantLight", "DistantLight", position=(0, 0, 10))
        light = UsdLux.DistantLight(stage.GetPrimAtPath("/World/DistantLight"))
        light.CreateIntensityAttr(3000.0)
        light.CreateAngleAttr(1.0)
        light.CreateColorAttr((1.0, 0.98, 0.95))
    print("  ✓ 조명 배치 완료")

    # 3. 이물질 (GPU 물리 파티클) — 코드 절대 미수정
    debris_sys = DebrisSystem(
        count=10, radius=0.015, color_hex="#5C3D1E",
        tank_range=0.9, z_floor=0.0
    )
    debris_sys.spawn(stage)
    print("  ✓ 이물질 파티클 10개 스폰 완료")

    # 4. 카메라 센서 + ROS 2 Bridge
    camera_sys = CameraSystem(
        prim_path="/World/Camera",
        position=(0.0, 0.0, 2.5),
        rotation=(0.0, 0.0, 0.0),    # 아래쪽 바라봄
        resolution=(1280, 720)
    )
    camera_sys.spawn_camera(stage)
    camera_sys.setup_ros2_omnigraph_bridge(
        topic_name="cleaner/camera/image_raw",
        frame_id="camera_optical_frame"
    )

    # 5. Blue Robotics 카메라 3D 에셋 (Camera 센서의 자식으로 배치 → 항상 동기)
    camera_model_path = "/World/Camera/Model"
    if not stage.GetPrimAtPath(camera_model_path).IsValid():
        from pxr import UsdGeom, Gf
        camera_model_prim = stage.DefinePrim(camera_model_path, "Xform")
        refs = camera_model_prim.GetReferences()
        refs.AddReference(CAMERA_ASSET_USD)
        # 부모(Camera)의 위치를 그대로 상속 → translate 불필요
        xformable = UsdGeom.Xformable(camera_model_prim)
        # 렌즈가 아래를 바라보도록 회전 (X축 -90도)
        xformable.AddRotateXYZOp().Set(Gf.Vec3f(-90.0, 0.0, 0.0))
        # CAD 원본 mm 단위 → m 단위 변환
        xformable.AddScaleOp().Set(Gf.Vec3f(0.001, 0.001, 0.001))
        print(f"  ✓ Blue Robotics 카메라 에셋 배치 완료 (Camera 센서에 부착)")

    # 5-1. 카메라 렌즈 유리 생성 — CAD 모델의 실제 하단(배럴 끝)에 자동 배치
    lens_path = "/World/Camera/Lens"
    if not stage.GetPrimAtPath(lens_path).IsValid():
        from pxr import UsdGeom, UsdShade, Gf, Sdf, Usd

        model_xf = UsdGeom.Xformable(camera_model_prim)
        # 1. 스케일 및 회전 먼저 적용 (바운딩 박스 계산을 위해 필수)
        model_xf.ClearXformOpOrder()
        rotate_op = model_xf.AddRotateXYZOp()
        rotate_op.Set(Gf.Vec3f(-90.0, 0.0, 0.0))
        scale_op = model_xf.AddScaleOp()
        scale_op.Set(Gf.Vec3f(0.001, 0.001, 0.001))

        # 2. 바운딩 박스를 계산하여 실제 배럴의 중앙 및 하단 위치 탐색
        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
        model_bbox = bbox_cache.ComputeWorldBound(camera_model_prim)
        model_range = model_bbox.ComputeAlignedRange()
        
        barrel_bottom_z = model_range.GetMin()[2]
        barrel_center_x = (model_range.GetMin()[0] + model_range.GetMax()[0]) / 2.0
        barrel_center_y = (model_range.GetMin()[1] + model_range.GetMax()[1]) / 2.0

        # 3. 모델 중심점 오프셋 보정 (카메라 센서가 배럴 중앙+끝에 오도록 모델 이동)
        # Camera 센서는 World (0, 0, 2.5)에 위치함
        offset_x = 0.0 - barrel_center_x
        offset_y = 0.0 - barrel_center_y
        offset_z = 2.5 - barrel_bottom_z
        
        # TranslateOp를 추가하고 가장 먼저 적용되도록 순서 변경 (Translate -> Rotate -> Scale)
        translate_op = model_xf.AddTranslateOp()
        translate_op.Set(Gf.Vec3d(offset_x, offset_y, offset_z))
        
        model_xf.SetXformOpOrder([translate_op, rotate_op, scale_op])

        lens_radius = 0.0055  # 11mm 지름
        print(f"  📐 렌즈 보정 오프셋: X={offset_x*1000:.1f}mm, Y={offset_y*1000:.1f}mm, Z={offset_z*1000:.1f}mm")

        # 4. 렌즈 실린더 생성 (부모 Camera의 기준점(local Z=0)이 곧 완벽한 배럴 입구임)
        lens = UsdGeom.Cylinder.Define(stage, lens_path)
        lens.CreateRadiusAttr(lens_radius)
        lens.CreateHeightAttr(0.001)   # 두께 1mm (얇은 유리)
        lens.CreateAxisAttr("Z")
        xf = UsdGeom.Xformable(lens.GetPrim())
        xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 0.0))

        # 다크 글래스 재질 (반사 코팅된 카메라 렌즈)
        mat_path = "/World/Camera/Lens/GlassMaterial"
        material = UsdShade.Material.Define(stage, mat_path)
        shader = UsdShade.Shader.Define(stage, f"{mat_path}/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.01, 0.01, 0.04))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.9)
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.03)
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.8)
        shader.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.52)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        UsdShade.MaterialBindingAPI(lens.GetPrim()).Bind(material)
        print("  ✓ 카메라 렌즈 유리 → 배럴 하단에 자동 배치 완료")

        # =========================================================================
        # 💾 [Option A] 완벽 정렬된 카메라 객체를 독립 에셋(camera.usd)으로 패키징
        # =========================================================================
        export_path = "/home/rokey/water_ws/src/water_debris_env/src/water_debris_env/camera.usd"
        try:
            import os
            # 기존 패키징 파일 삭제
            if os.path.exists(export_path):
                os.remove(export_path)
                
            export_stage = Usd.Stage.CreateInMemory()
            # /World/Camera 트리를 새 스테이지의 /Camera 루트로 복사
            Sdf.CopySpec(stage.GetRootLayer(), Sdf.Path("/World/Camera"), export_stage.GetRootLayer(), Sdf.Path("/Camera"))
            export_stage.SetDefaultPrim(export_stage.GetPrimAtPath("/Camera"))
            
            # 복사본의 재질 바인딩 경로 재정렬 (절대 경로 보정)
            export_lens = export_stage.GetPrimAtPath("/Camera/Lens")
            export_mat = export_stage.GetPrimAtPath("/Camera/Lens/GlassMaterial")
            if export_lens.IsValid() and export_mat.IsValid():
                UsdShade.MaterialBindingAPI(export_lens).UnbindAllBindings()
                UsdShade.MaterialBindingAPI(export_lens).Bind(UsdShade.Material(export_mat))
                
            export_stage.GetRootLayer().Export(export_path)
            print(f"  💾 [패키징 완료] 독립형 카메라 에셋이 완벽하게 저장되었습니다: {export_path}")
        except Exception as e:
            print(f"  ⚠️ [패키징 실패] camera.usd 생성 중 오류 발생: {e}")

    # 6. 물리 리셋 및 뷰포트 자동 전환
    world.reset()
    try:
        vp = vp_utils.get_active_viewport()
        if vp:
            vp.camera_path = "/World/Camera"
            print("  ✓ 뷰포트 → 카메라 시야 자동 전환")
    except Exception:
        pass

    print("\n✅ 준비 완료! 시뮬레이션 실행 중...")
    print("   종료: 창 닫기 또는 Ctrl+C")
    print("=" * 50)

    # 메인 루프
    while simulation_app.is_running():
        world.step(render=True)

    simulation_app.close()


if __name__ == "__main__":
    main()
