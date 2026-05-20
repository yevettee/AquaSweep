import sys
from omni.isaac.kit import SimulationApp

# 1. USD 파일 추출용 헤드리스 시뮬레이터 구동
simulation_app = SimulationApp({"headless": True})

from omni.isaac.core import World
from omni.physx import acquire_physx_interface
from pxr import UsdPhysics, PhysxSchema, UsdGeom, UsdLux
from omni.isaac.core.utils.prims import create_prim
from water_debris_env.debris_system import DebrisSystem
from water_debris_env.camera_system import CameraSystem

def main():
    print("🎬 [USD Exporter] 3D 수중 씬 빌드 시작 (GPU 파티클 & 물리 조명 주입)...")
    
    world = World(
        physics_dt=1.0/120.0, 
        rendering_dt=1.0/60.0, 
        stage_units_in_meters=1.0, 
        backend="torch", 
        device="cpu"
    )
    # GPU 물리 충돌 치트키 주입
    acquire_physx_interface().overwrite_gpu_setting(1)
    
    # 2. 디폴트 바닥 추가
    world.scene.add_default_ground_plane()
    stage = world.stage

    # 3. [Isaac Sim 5.1 지침] physicsScene의 GPU Dynamics 및 Broadphase MBP 명시적 적용
    physics_scene_prim = stage.GetPrimAtPath("/physicsScene")
    if not physics_scene_prim.IsValid():
        physics_scene = UsdPhysics.Scene.Define(stage, "/physicsScene")
        physics_scene_prim = physics_scene.GetPrim()
    
    physx_scene_api = PhysxSchema.PhysxSceneAPI.Apply(physics_scene_prim)
    physx_scene_api.CreateEnableGPUDynamicsAttr(True)
    physx_scene_api.CreateBroadphaseTypeAttr("MBP")

    # 4. [치명적 핵심 해결책] 씬을 환하게 비출 물리적인 조명(DistantLight) 주입!
    light_prim = stage.GetPrimAtPath("/World/DistantLight")
    if not light_prim.IsValid():
        create_prim(
            prim_path="/World/DistantLight",
            prim_type="DistantLight",
            position=(0.0, 0.0, 10.0),
            orientation=[0.9, 0.0, 0.4, 0.0]  # 비스듬한 조각광 연출
        )
        # 조명 밝기 및 태양빛 화각 설정
        light = UsdLux.DistantLight(stage.GetPrimAtPath("/World/DistantLight"))
        light.CreateIntensityAttr(3000.0)
        light.CreateAngleAttr(1.0)
        light.CreateColorAttr((1.0, 0.98, 0.95)) # 따뜻한 수조 광원 구현
        print("  ✓ physicsScene GPU 설정 및 물리 DistantLight 광원 조립 완료!")

    # 5. Blue Robotics 카메라 시스템 스폰 (3D 실물 하우징 메쉬 조립판)
    camera_sys = CameraSystem(
        prim_path="/World/Camera", 
        position=(0.0, 0.0, 2.5), 
        rotation=(0.0, 0.0, 0.0),  # 회전 없음 = 아래쪽 바라봄
        resolution=(1280, 720) # Blue Robotics HD 규격 탑재
    )
    camera_sys.spawn_camera(stage)
    camera_sys.setup_ros2_omnigraph_bridge(
        topic_name="cleaner/camera/image_raw", 
        frame_id="camera_optical_frame"
    )

    # 6. 이물질 시스템(DebrisSystem) 스폰 (10개 고유 분변)
    debris_sys = DebrisSystem(
        count=10, 
        radius=0.015, 
        color_hex="#5C3D1E", 
        tank_range=0.9, 
        z_floor=0.0
    )
    debris_sys.spawn(stage)

    # 7. 월드 물리 리셋을 거쳐 데이터 구조를 동결 및 USD 영구 저장
    world.reset()
    
    # USD 파일 최종 추출 경로 지정
    usd_export_path = "/home/rokey/water_ws/src/water_debris_env/src/water_debris_env/water_debris_scene.usd"
    
    # 현재 스테이지 저장 및 내보내기
    stage.Export(usd_export_path)
    print(f"✅ [USD Exporter] 3D 수중 씬 GPU 및 조광 최적화 USD 내보내기 완료! 경로: {usd_export_path}")
    
    simulation_app.close()

if __name__ == "__main__":
    main()
