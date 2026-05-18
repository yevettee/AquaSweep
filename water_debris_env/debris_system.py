import numpy as np
from pxr import UsdGeom, UsdPhysics, UsdShade, PhysxSchema, Gf, Vt, Sdf
from omni.physx.scripts import particleUtils

class DebrisSystem:
    def __init__(self, count=10, radius=0.015, color_hex="#5C3D1E", tank_range=0.9, z_floor=0.0):
        """
        이물질 생성 및 물리 시스템 관리 클래스
        
        Args:
            count (int): 총 이물질 개수
            radius (float): 이물질의 반지름 (단위: m)
            color_hex (str): 이물질 무광 재질의 색상 (Hex 코드)
            tank_range (float): 이물질이 스폰될 탱크 내 범위 (-tank_range ~ tank_range)
            z_floor (float): 바닥의 Z축 높이
        """
        self.count = count
        self.radius = radius
        self.color_hex = color_hex
        self.tank_range = tank_range
        self.z_floor = z_floor

    def _make_matte_material(self, stage, path, color_hex):
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

    def spawn(self, stage):
        """넘겨받은 Stage 상에 이물질 파티클을 물리/비주얼과 함께 스폰합니다."""
        print(f"\n✨ [DebrisSystem] 모든 이물질 규격 통일 버전 생성 시작 (총 {self.count}개)")
        print("=" * 60)

        # 1. 물리 씬 설정 (GPU 가속 필수 세팅)
        # 만약 월드에 이미 물리 씬이 선언되어 있지 않다면 생성 및 설정 진행
        physics_scene_path = "/physicsScene"
        if not stage.GetPrimAtPath(physics_scene_path).IsValid():
            scene_prim = UsdPhysics.Scene.Define(stage, physics_scene_path)
            physx_scene = PhysxSchema.PhysxSceneAPI.Apply(scene_prim.GetPrim())
            physx_scene.CreateEnableGPUDynamicsAttr(True)
            physx_scene.CreateBroadphaseTypeAttr("MBP")
            physx_scene.CreateSolverTypeAttr("TGS")
            print("  ✓ physicsScene 생성 및 GPU Dynamics 가속 설정 완료")

        # 2. 통합 파티클 시스템 정의
        sys_path = "/World/Debris/UnifiedSystem"
        ps = PhysxSchema.PhysxParticleSystem.Define(stage, sys_path)
        ps.CreateParticleSystemEnabledAttr(True)
        ps.CreateSolverPositionIterationCountAttr(16)
        
        # 바닥 관통 방지를 위한 Offset 설정
        ps.CreateContactOffsetAttr(self.radius * 1.5)
        ps.CreateSolidRestOffsetAttr(self.radius)
        ps.CreateRestOffsetAttr(self.radius * 0.1)

        # 3. 동일한 규격의 파티클 생성
        print("  ✓ [Layer A] 통합 물리 파티클 생성 중...")
        pts_path = "/World/Debris/UnifiedParticles"
        
        # 랜덤 위치 생성
        pos_x = np.random.uniform(-self.tank_range, self.tank_range, self.count)
        pos_y = np.random.uniform(-self.tank_range, self.tank_range, self.count)
        pos_z = np.full(self.count, self.z_floor + self.radius)
        
        positions = Vt.Vec3fArray([Gf.Vec3f(float(pos_x[i]), float(pos_y[i]), float(pos_z[i])) for i in range(self.count)])
        widths = Vt.FloatArray([self.radius * 2.0] * self.count)
        velocities = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)] * self.count)

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

        # 4. 시각적 재질 적용
        pts = UsdGeom.Points.Get(stage, pts_path)
        mat = self._make_matte_material(stage, pts_path + "_Mat", self.color_hex)
        UsdShade.MaterialBindingAPI(pts.GetPrim()).Bind(mat)

        print(f"  ✓ 모든 이물질({self.count}개)이 동일 규격으로 생성 완료")
