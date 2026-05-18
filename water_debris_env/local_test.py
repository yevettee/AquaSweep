from omni.isaac.kit import SimulationApp

# 1. 시뮬레이션 앱 초기화 (최상단 필수)
simulation_app = SimulationApp({"headless": False, "renderer": "RaytracedLighting"})

from omni.isaac.core import World
from omni.physx import acquire_physx_interface
from water_debris_env.debris_system import DebrisSystem
from water_debris_env.camera_system import CameraSystem

def main():
    print("\n🚀 [Local Test] 시뮬레이션 실행기 구동")
    print("=" * 60)

    # 2. 월드 생성 및 물리 설정 (GPU 치트키 주입 필수)
    world = World(
        physics_dt=1.0/120.0, 
        rendering_dt=1.0/60.0, 
        stage_units_in_meters=1.0, 
        backend="torch", 
        device="cpu"
    )
    # 물리 충돌 관통 방지를 위한 GPU 설정 강제 적용
    acquire_physx_interface().overwrite_gpu_setting(1)
    
    # 디폴트 바닥 설치
    world.scene.add_default_ground_plane()
    print("  ✓ defaultGroundPlane 생성 및 120Hz 물리 엔진 설정 완료")

    stage = world.stage

    # 3. 이물질 시스템(DebrisSystem) OOP 컴포넌트 스폰
    debris_sys = DebrisSystem(
        count=10, 
        radius=0.015, 
        color_hex="#5C3D1E", 
        tank_range=0.9, 
        z_floor=0.0
    )
    debris_sys.spawn(stage)

    # 4. 카메라 시스템(CameraSystem) OOP 컴포넌트 스폰
    camera_sys = CameraSystem(
        prim_path="/World/Camera", 
        position=(0.0, 0.0, 2.5), 
        rotation=(0.0, 180.0, 0.0), # 카메라가 아래를 내려다보도록 설정
        resolution=(640, 480)
    )
    camera_sys.spawn_camera(stage)
    
    # 🛰️ OmniGraph ROS2 브릿지 연결 자동 활성화
    camera_sys.setup_ros2_omnigraph_bridge(
        topic_name="camera/image_raw", 
        frame_id="camera_optical_frame"
    )

    # 5. 시뮬레이션 물리 리셋 및 루프 기동
    world.reset()
    print("\n✅ 모든 컴포넌트 조립 완료! 시뮬레이션을 시작합니다.")
    print("=" * 60)

    while simulation_app.is_running():
        world.step(render=True)

    print("\n👋 시뮬레이션 종료")
    simulation_app.close()

if __name__ == "__main__":
    main()
