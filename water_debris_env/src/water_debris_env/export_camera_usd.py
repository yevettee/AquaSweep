"""
카메라 전용 USD 파일 생성 스크립트.

사용법:
    python.sh export_camera_usd.py

출력:
    camera.usd — 팀원이 자신의 메인 스크립트에서 Reference로 불러올 수 있는
    독립형 카메라 센서 USD 파일.
"""
from omni.isaac.kit import SimulationApp
simulation_app = SimulationApp({"headless": True})

from pxr import UsdGeom, Gf, Usd

def main():
    print("📷 [Camera USD Exporter] 카메라 전용 USD 생성 시작...")

    # 새 빈 스테이지 생성
    stage = Usd.Stage.CreateNew(
        "/home/rokey/water_ws/src/water_debris_env/src/water_debris_env/camera.usd"
    )
    stage.SetDefaultPrim(stage.DefinePrim("/Camera"))

    # Camera Prim 생성
    camera = UsdGeom.Camera.Define(stage, "/Camera")
    camera.CreateFocalLengthAttr(15.0)
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100.0))

    # 기본 위치: Z=2.5m 상공, 회전 없음 (아래 바라봄)
    xformable = UsdGeom.Xformable(camera.GetPrim())
    xformable.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 2.5))

    stage.Save()
    print("✅ camera.usd 생성 완료!")
    print("   경로: /home/rokey/water_ws/src/water_debris_env/src/water_debris_env/camera.usd")
    print()
    print("   팀원 사용법:")
    print("   1. 메인 스크립트에서 stage.GetRootLayer().subLayerPaths.append('camera.usd')")
    print("   2. 또는 create_prim()으로 Reference 추가")
    print("   3. CameraSystem.setup_ros2_omnigraph_bridge() 호출하여 ROS2 연동")

    simulation_app.close()

if __name__ == "__main__":
    main()
