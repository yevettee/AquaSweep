import carb
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, PhysxSchema, Gf, Vt, Sdf
from omni.physx.scripts import particleUtils


class DebrisSystem:
    """PhysX GPU 파티클 기반 수조 이물질 — 풀별 독립 시스템.

    각 풀은 자체 ParticleSystem + Particles Points 를 가진다:

        /World/Pools/Pool_<n>/Debris/ParticleSystem
        /World/Pools/Pool_<n>/Debris/Particles

    Points 좌표는 Pool_<n> Xform 의 local frame (xy: 풀 중심 기준 원판,
    z: 빌딩 바닥 위). 풀 Xform 의 translate 가 world 좌표로 보정해 준다.
    """

    # ── Path helpers (per-pool) ──────────────────────────────────────────────
    @staticmethod
    def pool_debris_root(pool_idx: int) -> str:
        return f"/World/Pools/Pool_{pool_idx}/Debris"

    @staticmethod
    def pool_particle_system(pool_idx: int) -> str:
        return f"{DebrisSystem.pool_debris_root(pool_idx)}/ParticleSystem"

    @staticmethod
    def pool_particles(pool_idx: int) -> str:
        return f"{DebrisSystem.pool_debris_root(pool_idx)}/Particles"

    # Preferred simulationOwner scene paths, in priority order.
    # Referenced assets may bring their own UsdPhysics.Scene prims with GPU
    # dynamics OFF — we enable GPU on every scene and pick a known-good one
    # as the particle system's sim_owner.
    _PREFERRED_SCENE_PATHS = ("/physicsScene", "/World/PhysicsScene")

    # Single near-black dark-brown debris colour (#221911).
    _COLOR_RGB = (0.13, 0.10, 0.06)

    def __init__(self, count_range: tuple[int, int] = (30, 70),
                 radius: float = 0.05,
                 color_hex: str = "#221911", tank_range: float = 3.8,
                 z_floor: float = 0.0,
                 pool_centers: list[tuple[float, float]] | None = None):
        """``count_range`` is the inclusive (min, max) of debris per pool;
        each pool draws its own random count. ``pool_centers`` indexes
        Pool_1..Pool_N.

        ``color_hex`` is kept for backwards compatibility / logging — every
        particle is rendered with a single ``displayColor`` primvar set to
        ``_COLOR_RGB``.
        """
        lo, hi = count_range
        if lo > hi:
            lo, hi = hi, lo
        self.count_range = (max(1, int(lo)), max(1, int(hi)))
        self.radius      = radius
        self.color_hex   = color_hex  # retained for back-compat / logging
        self.tank_range  = tank_range
        self.z_floor     = z_floor
        self.pool_centers = pool_centers if pool_centers else [(0.0, 0.0)]
        self._particle_paths: list[str] = []
        self._pool_counts: list[int] = []
        self._spawned    = False

    def spawn(self, stage) -> bool:
        """모든 풀에 파티클을 스폰. 이미 스폰돼 있으면 False."""
        if self._spawned:
            return False

        import omni.timeline as _tl_mod
        _tl = _tl_mod.get_timeline_interface()
        was_playing = _tl.is_playing()

        try:
            if was_playing:
                carb.log_info("[debris] GPU particle 스폰을 위해 시뮬레이션을 재시작합니다.")
                _tl.stop()

            scene_path = self._ensure_physics_scene(stage)
            rng = np.random.default_rng()
            lo, hi = self.count_range
            self._pool_counts = []
            for idx, _center in enumerate(self.pool_centers, start=1):
                pool_count = int(rng.integers(lo, hi + 1))
                self._pool_counts.append(pool_count)
                sys_path = self.pool_particle_system(idx)
                pts_path = self.pool_particles(idx)
                self._define_particle_system_at(stage, scene_path, sys_path)
                self._add_particles_at(stage, sys_path, pts_path, pool_count)
                self._apply_material_to(stage, pts_path)
                self._particle_paths.append(pts_path)

            self._spawned = True
            total = sum(self._pool_counts)
            carb.log_info(
                f"[debris] {self._pool_counts} (per-pool, range "
                f"{lo}~{hi}) = total {total} 파티클 스폰 완료 "
                f"(scene={scene_path})"
            )

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
        """모든 풀의 Debris 서브트리를 제거."""
        for idx in range(1, len(self.pool_centers) + 1):
            root = self.pool_debris_root(idx)
            prim = stage.GetPrimAtPath(root)
            if prim and prim.IsValid():
                stage.RemovePrim(root)
        self._particle_paths.clear()
        self._pool_counts.clear()
        self._spawned = False

    @property
    def is_spawned(self) -> bool:
        return self._spawned

    def get_particle_paths(self) -> list[str]:
        """Snapshot of the particle Points prim paths (one per pool)."""
        return list(self._particle_paths)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_physics_scene(self, stage) -> str:
        """모든 UsdPhysics.Scene 에 GPU dynamics를 적용하고 sim_owner 후보를 반환.

        physx plugin은 USD prim 속성을 직접 읽으므로 CreateXxxAttr(value) 대신
        .Set(True)를 명시적으로 호출해야 기존 False 값을 덮어쓸 수 있다.
        """
        try:
            from isaacsim.core.api.world import World
            world = World.instance()
            if world is not None:
                world.get_physics_context().enable_gpu_dynamics(True)
        except Exception:
            pass

        scene_paths: list[str] = []
        for prim in stage.Traverse():
            if prim.IsA(UsdPhysics.Scene):
                api = PhysxSchema.PhysxSceneAPI.Apply(prim)
                api.CreateEnableGPUDynamicsAttr().Set(True)
                api.CreateBroadphaseTypeAttr().Set("MBP")
                api.CreateSolverTypeAttr().Set("TGS")
                scene_paths.append(str(prim.GetPath()))

        if scene_paths:
            for preferred in self._PREFERRED_SCENE_PATHS:
                if preferred in scene_paths:
                    carb.log_info(
                        f"[debris] GPU dynamics 활성화: {len(scene_paths)} scene(s); "
                        f"sim_owner={preferred}"
                    )
                    return preferred
            carb.log_info(
                f"[debris] GPU dynamics 활성화: {len(scene_paths)} scene(s); "
                f"sim_owner={scene_paths[0]} (fallback)"
            )
            return scene_paths[0]

        # 없으면 새로 생성
        scene_path = "/World/PhysicsScene"
        prim = UsdPhysics.Scene.Define(stage, scene_path).GetPrim()
        api  = PhysxSchema.PhysxSceneAPI.Apply(prim)
        api.CreateEnableGPUDynamicsAttr().Set(True)
        api.CreateBroadphaseTypeAttr().Set("MBP")
        api.CreateSolverTypeAttr().Set("TGS")
        carb.log_info(f"[debris] 새 physics scene 생성: {scene_path}")
        return scene_path

    def _define_particle_system_at(self, stage, scene_path: str, system_path: str) -> None:
        """단일 풀의 GPU 파티클 시스템 정의.

        Isaac Sim 4.x/5.x: simulationOwner 를 physics scene 으로 명시해야
        GPU dynamics 가 파티클 시스템을 인식한다.
        contactOffset > solidRestOffset > restOffset 순서를 지킬 것.
        """
        ps = PhysxSchema.PhysxParticleSystem.Define(stage, system_path)
        ps.CreateParticleSystemEnabledAttr(True)
        ps.CreateSolverPositionIterationCountAttr(16)

        contact_offset    = self.radius * 1.5
        solid_rest_offset = self.radius * 1.0
        rest_offset       = self.radius * 0.5

        ps.CreateContactOffsetAttr(contact_offset)
        ps.CreateSolidRestOffsetAttr(solid_rest_offset)
        ps.CreateRestOffsetAttr(rest_offset)

        sim_owner = ps.CreateSimulationOwnerRel()
        sim_owner.SetTargets([Sdf.Path(scene_path)])

    def _add_particles_at(self, stage, system_path: str, particles_path: str, count: int) -> None:
        """단일 풀에 ``count`` 개 파티클을 풀-로컬 좌표로 스폰."""
        rng   = np.random.default_rng()
        n     = count
        # sqrt 트릭으로 반경 균등 분포
        r     = np.sqrt(rng.uniform(0.0, self.tank_range ** 2, n))
        theta = rng.uniform(0.0, 2.0 * np.pi, n)
        pos_x = r * np.cos(theta)
        pos_y = r * np.sin(theta)
        pos_z = np.full(n, self.z_floor + self.radius * 2.5)

        positions  = Vt.Vec3fArray([
            Gf.Vec3f(float(pos_x[i]), float(pos_y[i]), float(pos_z[i]))
            for i in range(n)
        ])
        widths     = Vt.FloatArray([self.radius * 2.0] * n)
        velocities = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)] * n)

        try:
            particleUtils.add_physx_particleset_points(
                stage=stage,
                path=particles_path,
                positions_list=positions,
                velocities_list=velocities,
                widths_list=widths,
                particle_system_path=system_path,
                self_collision=True,
                fluid=False,
                particle_group=0,
                particle_mass=0.001,
                density=0.0,
            )
        except TypeError:
            particleUtils.add_physx_particleset_points(
                stage=stage,
                path=particles_path,
                positions_list=positions,
                velocities_list=velocities,
                widths_list=widths,
                particle_system_path=system_path,
                self_collision=True,
                fluid=False,
                particle_group=0,
                particle_mass=0.001,
            )

    def _apply_material_to(self, stage, particles_path: str) -> None:
        """Single near-black dark-brown colour via ``primvars:displayColor``
        (constant interp). Hydra renders the Points using the primvar
        directly — no UsdShade.Material binding is needed.
        """
        pts = UsdGeom.Points.Get(stage, particles_path)
        if not pts:
            return

        single_color = Vt.Vec3fArray([
            Gf.Vec3f(float(self._COLOR_RGB[0]),
                     float(self._COLOR_RGB[1]),
                     float(self._COLOR_RGB[2]))
        ])

        primvars_api = UsdGeom.PrimvarsAPI(pts.GetPrim())
        display_color = primvars_api.CreatePrimvar(
            "displayColor",
            Sdf.ValueTypeNames.Color3fArray,
            interpolation=UsdGeom.Tokens.constant,
        )
        display_color.Set(single_color)
