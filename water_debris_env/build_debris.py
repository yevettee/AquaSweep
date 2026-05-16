from omni.isaac.kit import SimulationApp

# 1. 시뮬레이션 앱 초기화 (최상단 필수)
simulation_app = SimulationApp({"headless": False, "renderer": "RaytracedLighting"})

import numpy as np
from pxr import UsdGeom, UsdPhysics, UsdShade, PhysxSchema, Gf, Vt, Sdf
from omni.isaac.core import World
from omni.isaac.core.utils.stage import get_current_stage
from omni.physx.scripts import particleUtils
from omni.physx import acquire_physx_interface

# ============================================================
# ⚙️  환경 및 이물질 통합 설정 (모든 이물질 동일 규격)
# ============================================================
TOTAL_DEBRIS_COUNT = 10        # 총 이물질 개수
UNIFIED_RADIUS     = 0.015     # 1.5cm로 크기 통일
UNIFIED_COLOR      = "#5C3D1E"   # 갈색으로 색상 통일

Z_FLOOR    = 0.0
TANK_RANGE = 0.9 # -0.9m ~ 0.9m 범위 내 생성

# ============================================================

def make_matte_material(stage, path, color_hex):
    """무광(매트) 시각적 재질 생성 유틸리티"""
    h = color_hex.lstrip("#")
    rgb = Gf.Vec3f(int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255)
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, path + "/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(rgb)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.95)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat

def main():
    print(f"\n✨ 모든 이물질 규격 통일 버전 (총 {TOTAL_DEBRIS_COUNT}개)")
    print("=" * 60)

    stage = get_current_stage()
    
    # 1. 물리 씬 설정 (GPU 가속 필수 세팅)
    scene_prim = UsdPhysics.Scene.Define(stage, "/physicsScene")
    physx_scene = PhysxSchema.PhysxSceneAPI.Apply(scene_prim.GetPrim())
    physx_scene.CreateEnableGPUDynamicsAttr(True)
    physx_scene.CreateBroadphaseTypeAttr("MBP")
    physx_scene.CreateSolverTypeAttr("TGS")

    # 2. 월드 생성 및 GPU 치트키 주입
    world = World(physics_dt=1.0/120.0, rendering_dt=1.0/60.0, stage_units_in_meters=1.0, backend="torch", device="cpu")
    acquire_physx_interface().overwrite_gpu_setting(1)
    world.scene.add_default_ground_plane()

    print("  ✓ 추가 바닥 없이 defaultGroundPlane과 120Hz 물리 연산으로 관통 방어")

    # 3. 통합 파티클 시스템 정의
    sys_path = "/World/Debris/UnifiedSystem"
    ps = PhysxSchema.PhysxParticleSystem.Define(stage, sys_path)
    ps.CreateParticleSystemEnabledAttr(True)
    ps.CreateSolverPositionIterationCountAttr(16)
    
    # 바닥 관통 방지를 위한 Offset 설정
    ps.CreateContactOffsetAttr(UNIFIED_RADIUS * 1.5)
    ps.CreateSolidRestOffsetAttr(UNIFIED_RADIUS)
    ps.CreateRestOffsetAttr(UNIFIED_RADIUS * 0.1)

    # 4. 동일한 규격의 파티클 생성
    print("\n[Layer A] 통합 물리 파티클 생성 중...")
    pts_path = "/World/Debris/UnifiedParticles"
    
    # 랜덤 위치 생성
    pos_x = np.random.uniform(-TANK_RANGE, TANK_RANGE, TOTAL_DEBRIS_COUNT)
    pos_y = np.random.uniform(-TANK_RANGE, TANK_RANGE, TOTAL_DEBRIS_COUNT)
    pos_z = np.full(TOTAL_DEBRIS_COUNT, Z_FLOOR + UNIFIED_RADIUS)
    
    positions = Vt.Vec3fArray([Gf.Vec3f(float(pos_x[i]), float(pos_y[i]), float(pos_z[i])) for i in range(TOTAL_DEBRIS_COUNT)])
    widths = Vt.FloatArray([UNIFIED_RADIUS * 2.0] * TOTAL_DEBRIS_COUNT)
    velocities = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)] * TOTAL_DEBRIS_COUNT)

    # ✅ 필수 인자인 particle_group을 포함하여 호출합니다.
    particleUtils.add_physx_particleset_points(
        stage=stage,
        path=pts_path,
        positions_list=positions,
        velocities_list=velocities,
        widths_list=widths,
        particle_system_path=sys_path,
        self_collision=True,
        fluid=False,
        particle_group=0,      # 필수 인자 추가
        particle_mass=0.001,
        density=0.0
    )

    # 시각적 재질 적용
    pts = UsdGeom.Points.Get(stage, pts_path)
    mat = make_matte_material(stage, pts_path + "_Mat", UNIFIED_COLOR)
    UsdShade.MaterialBindingAPI(pts.GetPrim()).Bind(mat)

    world.reset()
    print(f"  ✓ 모든 이물질({TOTAL_DEBRIS_COUNT}개)이 동일 규격으로 생성 완료")

    print("\n✅ 완료! 시뮬레이션 시작")
    
    while simulation_app.is_running():
        world.step(render=True)

    simulation_app.close()

if __name__ == "__main__":
    main()
