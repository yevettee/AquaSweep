import carb
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, PhysxSchema, Gf, Vt, Sdf
from omni.physx.scripts import particleUtils


class DebrisSystem:
    """PhysX GPU 파티클 기반 수조 이물질 생성 및 관리.

    stage를 받아 파티클을 스폰하고, clear()로 제거합니다.
    Extension 프레임워크(scenario.py)를 통해 호출됩니다.
    """

    PARTICLE_SYS_PATH = "/World/Debris/UnifiedSystem"
    PARTICLES_PATH    = "/World/Debris/UnifiedParticles"
    DEBRIS_ROOT       = "/World/Debris"

    def __init__(self, count: int = 10, radius: float = 0.015,
                 color_hex: str = "#5C3D1E", tank_range: float = 3.8,
                 z_floor: float = 0.0):
        self.count      = count
        self.radius     = radius
        self.color_hex  = color_hex
        self.tank_range = tank_range
        self.z_floor    = z_floor
        self._spawned   = False

    def spawn(self, stage) -> bool:
        """stage에 이물질 파티클을 생성합니다. 이미 스폰되어 있으면 False 반환.

        GPU 파티클은 반드시 시뮬레이션 시작 전에 생성해야 합니다.
        시뮬레이션이 실행 중이면 자동으로 stop → 파티클 생성 → play 순서를 처리합니다.
        timeline.stop()은 PhysX 컨텍스트를 재초기화하므로, 이후 play() 시
        GPU dynamics 설정이 올바르게 적용됩니다.
        """
        if self._spawned:
            return False

        import omni.timeline as _tl_mod
        _tl = _tl_mod.get_timeline_interface()
        was_playing = _tl.is_playing()

        try:
            # 실행 중이면 stop → GPU dynamics 적용 → spawn → play
            if was_playing:
                carb.log_info("[debris] GPU particle 스폰을 위해 시뮬레이션을 재시작합니다.")
                _tl.stop()

            scene_path = self._ensure_physics_scene(stage)
            self._define_particle_system(stage, scene_path)
            self._add_particles(stage)
            self._apply_material(stage)
            self._spawned = True
            carb.log_info(f"[debris] {self.count}개 파티클 스폰 완료 (scene={scene_path})")

            # stop 했으면 play 재시작 (GPU dynamics가 이제 활성화된 상태로 시작)
            if was_playing:
                _tl.play()
            return True

        except Exception as e:
            carb.log_error(f"[debris] spawn 실패: {e}")
            if was_playing:
                try:
                    _tl.play()
                except Exception:
                    pass
            return False

    def clear(self, stage) -> None:
        """stage에서 이물질 파티클을 제거합니다."""
        root = stage.GetPrimAtPath(self.DEBRIS_ROOT)
        if root.IsValid():
            stage.RemovePrim(self.DEBRIS_ROOT)
        self._spawned = False

    @property
    def is_spawned(self) -> bool:
        return self._spawned

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_physics_scene(self, stage) -> str:
        """기존 UsdPhysics.Scene을 탐색해 GPU dynamics를 활성화한다.

        physx plugin은 USD prim 속성을 직접 읽으므로 CreateXxxAttr(value) 대신
        .Set(True)를 명시적으로 호출해야 기존 False 값을 덮어쓸 수 있다.
        """
        # World API로도 갱신 (런타임 physics context)
        try:
            from isaacsim.core.api.world import World
            world = World.instance()
            if world is not None:
                world.get_physics_context().enable_gpu_dynamics(True)
        except Exception:
            pass

        # 기존 UsdPhysics.Scene prim 탐색해 GPU dynamics 속성 갱신
        for prim in stage.Traverse():
            if prim.IsA(UsdPhysics.Scene):
                api = PhysxSchema.PhysxSceneAPI.Apply(prim)
                api.CreateEnableGPUDynamicsAttr().Set(True)   # .Set() 필수
                api.CreateBroadphaseTypeAttr().Set("MBP")
                api.CreateSolverTypeAttr().Set("TGS")
                path = str(prim.GetPath())
                carb.log_info(f"[debris] GPU dynamics 활성화: {path}")
                return path

        # 없으면 새로 생성
        scene_path = "/World/PhysicsScene"
        prim = UsdPhysics.Scene.Define(stage, scene_path).GetPrim()
        api  = PhysxSchema.PhysxSceneAPI.Apply(prim)
        api.CreateEnableGPUDynamicsAttr().Set(True)
        api.CreateBroadphaseTypeAttr().Set("MBP")
        api.CreateSolverTypeAttr().Set("TGS")
        carb.log_info(f"[debris] 새 physics scene 생성: {scene_path}")
        return scene_path

    def _define_particle_system(self, stage, scene_path: str) -> None:
        """GPU 파티클 시스템 정의.

        Isaac Sim 4.x에서는 simulationOwner를 physics scene으로 명시해야
        GPU dynamics가 파티클 시스템을 인식한다.
        contactOffset > solidRestOffset > restOffset 순서를 지켜야 한다.
        """
        ps = PhysxSchema.PhysxParticleSystem.Define(stage, self.PARTICLE_SYS_PATH)
        ps.CreateParticleSystemEnabledAttr(True)
        ps.CreateSolverPositionIterationCountAttr(16)

        contact_offset    = self.radius * 1.5
        solid_rest_offset = self.radius * 1.0   # solidRestOffset < contactOffset
        rest_offset       = self.radius * 0.5   # restOffset < solidRestOffset

        ps.CreateContactOffsetAttr(contact_offset)
        ps.CreateSolidRestOffsetAttr(solid_rest_offset)
        ps.CreateRestOffsetAttr(rest_offset)

        # Isaac Sim 4.x 필수: GPU particle system → physics scene 연결
        sim_owner = ps.CreateSimulationOwnerRel()
        sim_owner.SetTargets([Sdf.Path(scene_path)])

    def _add_particles(self, stage) -> None:
        rng   = np.random.default_rng()
        # 원형 수조 내부 균등 분포: sqrt 트릭으로 반경 편향 제거
        r     = np.sqrt(rng.uniform(0.0, self.tank_range ** 2, self.count))
        theta = rng.uniform(0.0, 2.0 * np.pi, self.count)
        pos_x = r * np.cos(theta)
        pos_y = r * np.sin(theta)
        pos_z = np.full(self.count, self.z_floor + self.radius * 2.5)

        positions  = Vt.Vec3fArray([
            Gf.Vec3f(float(pos_x[i]), float(pos_y[i]), float(pos_z[i]))
            for i in range(self.count)
        ])
        widths     = Vt.FloatArray([self.radius * 2.0] * self.count)
        velocities = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)] * self.count)

        # density 파라미터는 Isaac Sim 버전에 따라 지원 여부가 다르므로 분기 처리
        try:
            particleUtils.add_physx_particleset_points(
                stage=stage,
                path=self.PARTICLES_PATH,
                positions_list=positions,
                velocities_list=velocities,
                widths_list=widths,
                particle_system_path=self.PARTICLE_SYS_PATH,
                self_collision=True,
                fluid=False,
                particle_group=0,
                particle_mass=0.001,
                density=0.0,
            )
        except TypeError:
            # 일부 Isaac Sim 4.x 버전에서 density 파라미터 미지원
            particleUtils.add_physx_particleset_points(
                stage=stage,
                path=self.PARTICLES_PATH,
                positions_list=positions,
                velocities_list=velocities,
                widths_list=widths,
                particle_system_path=self.PARTICLE_SYS_PATH,
                self_collision=True,
                fluid=False,
                particle_group=0,
                particle_mass=0.001,
            )

    def _apply_material(self, stage) -> None:
        pts = UsdGeom.Points.Get(stage, self.PARTICLES_PATH)
        if not pts:
            return
        mat = self._make_matte_material(stage, self.PARTICLES_PATH + "_Mat", self.color_hex)
        UsdShade.MaterialBindingAPI(pts.GetPrim()).Bind(mat)

    @staticmethod
    def _make_matte_material(stage, path: str, color_hex: str):
        h   = color_hex.lstrip("#")
        rgb = Gf.Vec3f(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
        mat    = UsdShade.Material.Define(stage, path)
        shader = UsdShade.Shader.Define(stage, path + "/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(rgb)
        shader.CreateInput("roughness",    Sdf.ValueTypeNames.Float).Set(0.95)
        shader.CreateInput("metallic",     Sdf.ValueTypeNames.Float).Set(0.0)
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return mat
