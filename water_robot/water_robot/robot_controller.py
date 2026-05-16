# Isaac Sim Interactive Sample: JetBot 차동 주행으로 수조 청소(간단 왕복) 패턴.
# DifferentialController: command=[v, ω] → 좌/우 바퀴 속도. 직진 구간은 개루프 ω=0.
# Examples Browser에서 Load 후 Play 시 물리 콜백으로 FSM 구동.
from enum import Enum, auto

import carb
import numpy as np
from isaacsim.examples.interactive.base_sample import BaseSample
from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController
from isaacsim.robot.wheeled_robots.robots import WheeledRobot
from isaacsim.storage.native import get_assets_root_path

# JetBot 물리 파라미터 (공식 예제와 동일)
JETBOT_WHEEL_RADIUS = 0.03
JETBOT_WHEEL_BASE = 0.1125

# 수조·로봇 치수 (m) — 실제 수조에 맞게 조정
TANK_WIDTH_M = 2
ROBOT_DIAMETER_M = 0.14

# 명령 속도: DifferentialController.forward(command=[선속도 v, 각속도 ω])
ROW_LINEAR = 1
TURN_ANGULAR = np.pi / 2

# 종료 허용 오차
DIST_TOL_M = 0.02
YAW_TOL_RAD = 0.04

PHYSICS_CB_NAME = "water_tank_cleaner_fsm"
JETBOT_SCENE_NAME = "water_tank_jetbot"

# 시뮬 중 속도 vs 명령 비교 (콜백 매 스텝마다 출력). 끄려면 False.
DEBUG_LOG_VEL = True
# 1이면 모든 물리 스텝, N>1이면 N스텝마다 (로그 과다 방지용).
DEBUG_LOG_VEL_EVERY_N_PHYSICS_STEPS = 1


class _MotionKind(Enum):
    MOVE = auto()
    TURN = auto()


class WaterTankJetbotSample(BaseSample):
    """수조 너비·로봇 지름 기준 한 번 왕복(아웃바운드 + 역추적 리턴) FSM."""

    def __init__(self) -> None:
        super().__init__()
        self._jetbot = None
        self._controller = None
        self._phase_index = 0
        self._phase_origin_xy = None
        self._phase_target_yaw = None
        self._specs = None
        self._debug_vel_step = 0
        self._cycle_start_xy = None
        self._cycle_start_yaw = None
        return

    def setup_scene(self):
        world = self.get_world()
        world.scene.add_default_ground_plane()

        assets_root_path = get_assets_root_path()
        if assets_root_path is None:
            carb.log_error("Isaac Sim assets 경로를 찾을 수 없습니다.")
            return
        jetbot_asset_path = assets_root_path + "/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd"

        world.scene.add(
            WheeledRobot(
                prim_path="/World/Jetbot",
                name=JETBOT_SCENE_NAME,
                wheel_dof_names=["left_wheel_joint", "right_wheel_joint"],
                create_robot=True,
                usd_path=jetbot_asset_path,
                position=np.array([0.0, 0.0, 0.05]),
            )
        )
        return

    async def setup_post_load(self):
        await super().setup_post_load()
        self._world = self.get_world()
        self._jetbot = self._world.scene.get_object(JETBOT_SCENE_NAME)
        self._controller = DifferentialController(
            name="water_tank_diff",
            wheel_radius=JETBOT_WHEEL_RADIUS,
            wheel_base=JETBOT_WHEEL_BASE,
        )
        self._controller.reset()
        self._build_phase_specs()
        self._reset_fsm()
        self._register_physics_cb()
        return

    async def setup_pre_reset(self):
        await super().setup_pre_reset()
        self._unregister_physics_cb()
        return

    async def setup_post_reset(self):
        await super().setup_post_reset()
        if self._controller is not None:
            self._controller.reset()
        self._jetbot = self._world.scene.get_object(JETBOT_SCENE_NAME)
        self._reset_fsm()
        self._register_physics_cb()
        return

    async def setup_post_clear(self):
        await super().setup_post_clear()
        self._unregister_physics_cb()
        self._jetbot = None
        self._controller = None
        self._specs = None
        return

    def world_cleanup(self):
        self._unregister_physics_cb()
        super().world_cleanup()
        return

    def _build_phase_specs(self):
        hw = np.pi / 2.0
        # 아웃바운드: 전진 W → +90° → 전진 D → +90° → 전진 W
        # 리턴: 역기하 (후진·역회전 순서)로 (0,0) 근처 복귀
        self._specs = [
            (_MotionKind.MOVE, TANK_WIDTH_M, 1.0),
            (_MotionKind.TURN, hw, 1.0),
            (_MotionKind.MOVE, ROBOT_DIAMETER_M, 1.0),
            (_MotionKind.TURN, hw, 1.0),
            (_MotionKind.MOVE, TANK_WIDTH_M, 1.0),
        ]

    def _reset_fsm(self):
        self._phase_index = 0
        self._phase_origin_xy = None
        self._phase_target_yaw = None
        self._debug_vel_step = 0
        self._begin_current_phase()
        self._log_cycle_start_pose()

    def _log_cycle_start_pose(self) -> None:
        """출발 직전(phase 0 시작) 월드 좌표 — Isaac 콘솔/Stdout."""
        if self._jetbot is None:
            return
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        self._cycle_start_xy = np.array([pos[0], pos[1]], dtype=float)
        self._cycle_start_yaw = yaw
        msg = (
            f"[water_tank_jetbot] cycle START world_xyz=({pos[0]:.4f},{pos[1]:.4f},{pos[2]:.4f}) "
            f"yaw_rad={yaw:.4f}"
        )
        carb.log_info(msg)
        print(msg, flush=True)

    def _log_cycle_end_pose(self) -> None:
        """1회 왕복 FSM 종료 직후 월드 좌표 및 평면 위치 오차(m)."""
        if self._jetbot is None or self._cycle_start_xy is None:
            return
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        dx = float(pos[0] - self._cycle_start_xy[0])
        dy = float(pos[1] - self._cycle_start_xy[1])
        err_xy = float(np.hypot(dx, dy))
        dyaw = self._angle_abs_diff(yaw, self._cycle_start_yaw)
        msg = (
            f"[water_tank_jetbot] cycle END   world_xyz=({pos[0]:.4f},{pos[1]:.4f},{pos[2]:.4f}) "
            f"yaw_rad={yaw:.4f} | planar_err={err_xy:.4f} m dx={dx:.4f} dy={dy:.4f} |yaw_err|={dyaw:.4f} rad"
        )
        carb.log_info(msg)
        print(msg, flush=True)

    def _register_physics_cb(self):
        if self._world is None:
            return
        if self._world.physics_callback_exists(PHYSICS_CB_NAME):
            return
        self._world.add_physics_callback(PHYSICS_CB_NAME, callback_fn=self._on_physics_step)

    def _unregister_physics_cb(self):
        if self._world is None:
            return
        if self._world.physics_callback_exists(PHYSICS_CB_NAME):
            self._world.remove_physics_callback(PHYSICS_CB_NAME)

    def _on_physics_step(self, step_size):
        del step_size  # dt 불필요; 거리·자세로 종료 판정
        if self._jetbot is None or self._controller is None or self._specs is None:
            return
        if self._phase_index >= len(self._specs):
            self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, 0.0]))
            return

        kind, mag, sign = self._specs[self._phase_index]
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)

        if kind == _MotionKind.MOVE:
            traveled = float(np.hypot(pos[0] - self._phase_origin_xy[0], pos[1] - self._phase_origin_xy[1]))
            if traveled >= mag - DIST_TOL_M:
                self._advance_phase()
                return
            v = sign * ROW_LINEAR
            w = 0.0
            # self._log_velocity_debug(v_cmd=v, w_cmd=w, phase_tag="MOVE")
            self._jetbot.apply_wheel_actions(self._controller.forward(command=[v, w]))
            return

        if self._angle_abs_diff(yaw, self._phase_target_yaw) <= YAW_TOL_RAD:
            self._advance_phase()
            return
        w = sign * TURN_ANGULAR
        # self._log_velocity_debug(v_cmd=0.0, w_cmd=w, phase_tag="TURN")
        self._jetbot.apply_wheel_actions(self._controller.forward(command=[0.0, w]))

    def _advance_phase(self):
        self._phase_index += 1
        if self._specs is not None and self._phase_index == len(self._specs):
            self._log_cycle_end_pose()
        self._begin_current_phase()

    def _begin_current_phase(self):
        if self._jetbot is None or self._specs is None:
            return
        if self._phase_index >= len(self._specs):
            return
        kind, mag, sign = self._specs[self._phase_index]
        pos, orient = self._jetbot.get_world_pose()
        yaw = self._yaw_from_orientation(orient)
        if kind == _MotionKind.MOVE:
            self._phase_origin_xy = np.array([pos[0], pos[1]], dtype=float)
            self._phase_target_yaw = None
            return
        self._phase_origin_xy = None
        self._phase_target_yaw = self._normalize_angle(yaw + sign * mag)

    # def _log_velocity_debug(self, v_cmd: float, w_cmd: float, phase_tag: str) -> None:
    #     """N 물리 스텝마다 carb + stdout에 속도/명령 로그."""
    #     if not DEBUG_LOG_VEL:
    #         return
    #     self._debug_vel_step += 1
    #     if self._debug_vel_step % DEBUG_LOG_VEL_EVERY_N_PHYSICS_STEPS != 0:
    #         return
    #     try:
    #         lv = np.asarray(self._jetbot.get_linear_velocity(), dtype=float).reshape(-1)
    #         av = np.asarray(self._jetbot.get_angular_velocity(), dtype=float).reshape(-1)
    #         speed_xy = float(np.linalg.norm(lv[:2]))
    #         speed_3d = float(np.linalg.norm(lv))
    #         ang_z = float(av[2]) if av.size > 2 else float("nan")
    #         wh = self._jetbot.get_wheel_velocities()
    #         msg = (
    #             f"[water_tank_jetbot] {phase_tag} phase_idx={self._phase_index} "
    #             f"v_cmd={v_cmd:.3f} w_cmd={w_cmd:.3f} m/s,rad/s | "
    #             f"|v_xy|={speed_xy:.3f} |v|={speed_3d:.3f} m/s ω_z={ang_z:.3f} rad/s | "
    #             f"wheel_dof_vel(rad/s)={wh}"
    #         )
    #         carb.log_info(msg)
    #         print(msg, flush=True)
    #     except Exception as exc:  # noqa: BLE001 — 디버그 보조
    #         carb.log_warn(f"[water_tank_jetbot] velocity debug failed: {exc}")
    #         print(f"[water_tank_jetbot] velocity debug failed: {exc}", flush=True)

    @staticmethod
    def _normalize_angle(a):
        return (float(a) + np.pi) % (2.0 * np.pi) - np.pi

    def _angle_abs_diff(self, a, b):
        return abs(self._normalize_angle(a - b))

    def _yaw_from_orientation(self, orient):
        """로봇 루트 쿼터니언에서 Z축 요 각 추출 (get_world_pose 관례 [w,x,y,z])."""
        q = np.asarray(orient, dtype=float).reshape(-1)
        if q.size != 4:
            return 0.0
        w, x, y, z = q[0], q[1], q[2], q[3]
        return float(np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))
