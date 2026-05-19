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

    # 6. 영롱한 보랏빛/푸른빛 반사의 리얼 렌즈 글래스 삽입 (Sphere 기반 데코레이션)
    lens_glass_path = "/World/Camera/LensGlass"
    if not stage.GetPrimAtPath(lens_glass_path).IsValid():
        from pxr import UsdGeom, Gf
        import omni.kit.commands
        
        # 렌즈 개구부 중심에 구체 생성 (반지름 약 1.4cm)
        lens_sphere = UsdGeom.Sphere.Define(stage, lens_glass_path)
        lens_sphere.CreateRadiusAttr(0.014)
        
        # 카메라 렌즈 중심 오프셋에 위치 (약간 돌출)
        xform = UsdGeom.Xformable(lens_sphere.GetPrim())
        xform.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, -0.015))
        
        # 렌즈 구체 찌그러뜨려서 렌즈알 표면처럼 평평하게 만들기
        xform.AddScaleOp().Set(Gf.Vec3f(1.0, 1.0, 0.3))
        
        # 렌즈 전용 영롱한 보랏빛/딥블루 코팅 유리 재질 생성
        material_path = "/World/Camera/LensMaterial"
        omni.kit.commands.execute("CreateMdlMaterialPrim",
            mtl_link="OmniPBR.mdl",
            material_name="LensMaterial",
            target_path="/World/Camera"
        )
        
        # 재질 물리 속성 튜닝 (투명하고, 반사율이 높고, 보랏빛 코팅이 은은하게 맺히도록)
        shader_path = f"{material_path}/Shader"
        shader_prim = stage.GetPrimAtPath(shader_path)
        if shader_prim.IsValid():
            shader_prim.GetAttribute("inputs:diffuse_color").Set(Gf.Vec3f(0.1, 0.05, 0.45)) # 영롱한 딥 퍼플/블루
            shader_prim.GetAttribute("inputs:roughness").Set(0.0) # 완벽한 반사면 (거칠기 0)
            shader_prim.GetAttribute("inputs:metallic").Set(0.1) # 은은한 금속 느낌 반사광
            shader_prim.GetAttribute("inputs:enable_opacity").Set(True) # 투명 재질 활성화
            shader_prim.GetAttribute("inputs:opacity_amount").Set(0.4) # 40% 정도 투명하게 내부 비침
            
        # 렌즈알에 재질 바인딩
        omni.kit.commands.execute("BindMaterial",
            prim_path=lens_glass_path,
            material_path=material_path
        )
        print("  ✓ 영롱한 보랏빛 렌즈 글래스 이식 완료!")

    # 7. 물리 리셋 및 뷰포트 자동 전환
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
