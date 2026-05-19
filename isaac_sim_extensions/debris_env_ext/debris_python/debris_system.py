import numpy as np
from pxr import UsdGeom, UsdPhysics, UsdShade, PhysxSchema, Gf, Vt, Sdf
from omni.physx.scripts import particleUtils


class DebrisSystem:
    """PhysX GPU 파티클 기반 수조 이물질 생성 및 관리.

    stage를 받아 파티클을 스폰하고, clear()로 제거합니다.
    Extension 프레임워크(scenario.py)를 통해 호출됩니다.
    """

    PARTICLE_SYS_PATH = "/World/Debris/UnifiedSystem"
    PARTICLES_PATH = "/World/Debris/UnifiedParticles"
    DEBRIS_ROOT = "/World/Debris"

    def __init__(self, count: int = 10, radius: float = 0.015,
                 color_hex: str = "#5C3D1E", tank_range: float = 2.3,
                 z_floor: float = 0.0):
        self.count = count
        self.radius = radius
        self.color_hex = color_hex
        self.tank_range = tank_range
        self.z_floor = z_floor
        self._spawned = False

    def spawn(self, stage) -> bool:
        """stage에 이물질 파티클을 생성합니다. 이미 스폰되어 있으면 False 반환."""
        if self._spawned:
            return False

        self._ensure_physics_scene(stage)
        self._define_particle_system(stage)
        self._add_particles(stage)
        self._apply_material(stage)
        self._spawned = True
        return True

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

    def _ensure_physics_scene(self, stage) -> None:
        physics_scene_path = "/physicsScene"
        prim = stage.GetPrimAtPath(physics_scene_path)
        if not prim.IsValid():
            prim = UsdPhysics.Scene.Define(stage, physics_scene_path).GetPrim()
        physx_scene = PhysxSchema.PhysxSceneAPI.Apply(prim)
        physx_scene.CreateEnableGPUDynamicsAttr(True)
        physx_scene.CreateBroadphaseTypeAttr("MBP")
        physx_scene.CreateSolverTypeAttr("TGS")

    def _define_particle_system(self, stage) -> None:
        ps = PhysxSchema.PhysxParticleSystem.Define(stage, self.PARTICLE_SYS_PATH)
        ps.CreateParticleSystemEnabledAttr(True)
        ps.CreateSolverPositionIterationCountAttr(16)
        ps.CreateContactOffsetAttr(self.radius * 1.5)
        ps.CreateSolidRestOffsetAttr(self.radius)
        ps.CreateRestOffsetAttr(self.radius * 0.1)

    def _add_particles(self, stage) -> None:
        rng = np.random.default_rng()
        pos_x = rng.uniform(-self.tank_range, self.tank_range, self.count)
        pos_y = rng.uniform(-self.tank_range, self.tank_range, self.count)
        pos_z = np.full(self.count, self.z_floor + self.radius * 2.5)

        positions = Vt.Vec3fArray([
            Gf.Vec3f(float(pos_x[i]), float(pos_y[i]), float(pos_z[i]))
            for i in range(self.count)
        ])
        widths = Vt.FloatArray([self.radius * 2.0] * self.count)
        velocities = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)] * self.count)

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

    def _apply_material(self, stage) -> None:
        pts = UsdGeom.Points.Get(stage, self.PARTICLES_PATH)
        if not pts:
            return
        mat = self._make_matte_material(stage, self.PARTICLES_PATH + "_Mat", self.color_hex)
        UsdShade.MaterialBindingAPI(pts.GetPrim()).Bind(mat)

    @staticmethod
    def _make_matte_material(stage, path: str, color_hex: str):
        h = color_hex.lstrip("#")
        rgb = Gf.Vec3f(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)
        mat = UsdShade.Material.Define(stage, path)
        shader = UsdShade.Shader.Define(stage, path + "/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(rgb)
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.95)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return mat
