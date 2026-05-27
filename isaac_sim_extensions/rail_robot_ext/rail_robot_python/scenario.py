"""Rail robot scenario — 수조 벽면 자율 순환 청소.

동작 순서 (1수조 기준):
  0. CALIBRATE : 시뮬레이션 첫 실행 시 자동 IK 보정 (약 0.4초, 이후 캐싱)
  1+. Planner  : RAIL_PLANNER_MODE 에 따라 궤적 실행
       - classic : rail_planner.py (스윕 → HOME → 레일 → RESET)
       - zigzag  : rail_planner_zigzag.py (레일+스윕 동시 보간 W 패턴)

MotionCommandBridge 연동:
  - start/stop/pause/resume 서비스 제공
  - clean_wall_status 토픽으로 진행상황 발행
"""

import math
from typing import Optional, Tuple

import carb
import numpy as np
from pxr import Gf, UsdGeom, UsdPhysics

from .global_variables import (
    JOINT_NAMES,
    RAIL_CENTER_R,
    RAIL_MOUNT_Z,
    WALL_REACH_JOINTS,
    SWEEP_J2_TOP,
    SWEEP_J2_BOTTOM,
    SWEEP_J3_TOP,
    SWEEP_J3_BOTTOM,
    SWEEP_J5_TOP,
    SWEEP_J5_BOTTOM,
    RAIL_PLANNER_MODE,
    TANK_RADIUS,
    SCRAPER_TOOL_Z,
    IK_CAL_N_SAMPLES,
)
from .rail_planner import RailPlannerClassic
from .rail_planner_zigzag import RailPlannerZigzag, build_zigzag_path

LOG_TAG = "[rail_robot]"

_CALIBRATE = 3   # 첫 실행 전 IK 보정 (일회성)

# 보정 프레임 인덱스 상수
_CAL_FRAME_SET_MID    = 0   # 중간점 j3=1.40 설정
_CAL_FRAME_READ_R1    = 1   # r1 읽기, j3+0.10 설정
_CAL_FRAME_READ_R2    = 2   # r2 읽기 → 기울기 계산, sample[0] 설정
# frame 3+k : sample[k] 읽기 → 보정 저장, sample[k+1] 설정


class RailRobotScenario:
    """레일 kinematic 순환 + 6DOF 암 IK 보정 스윕.

    첫 번째 RUN 시 약 20 physics 프레임 동안 자동 보정하여
    블레이드 팁이 수조 벽면을 따라 수직 직선 궤적을 그리도록 j3를 최적화.
    이후 실행에서는 캐싱된 테이블을 재사용 (추가 오버헤드 없음).
    
    Thread Safety:
        ROS 콜백(서비스 핸들러)은 PhysX 스레드와 다른 스레드에서 실행됨.
        USD/Physics 객체 접근은 on_physics_step()에서만 수행하고,
        ROS 콜백에서는 플래그만 설정하여 race condition 방지.
    """

    # Phase names for status reporting
    PHASE_CALIBRATE = "calibrate"
    PHASE_ARM_SWEEP = "arm_sweep"
    PHASE_ARM_HOME = "arm_home"
    PHASE_RAIL_MOVE = "rail_move"
    PHASE_ARM_RESET = "arm_reset"
    PHASE_COUPLED_SWEEP = "coupled_sweep"
    PHASE_DONE = "done"

    def __init__(self, pool_idx: int, pool_center: Tuple[float, float] = (0.0, 0.0)):
        self._pool_idx = pool_idx
        self._pool_center = pool_center
        self._articulation = None
        self._carriage_prim = None
        self._carriage_prim_path = ""
        self._joint_drive = None
        self._bridge = None
        self._motion_bridge = None  # MotionCommandBridge 인스턴스
        self._stage = None
        self._dof_index: dict = {}

        self._running = False
        self._paused = False
        self._phase = _CALIBRATE
        self._rail_angle = 0.0
        self._planner = None

        # Thread-safe 요청 플래그 (ROS 콜백 → Physics 스레드)
        self._start_requested = False
        self._stop_requested = False
        self._pause_requested = False

        # IK 테이블 (보정 완료 후 캐싱)
        self._sweep_table: Optional[list] = None

        # 보정 상태 변수
        self._cal_frame  = 0
        self._cal_r1     = 0.0
        self._cal_slope  = 2.0    # d_j3 / d_r 기울기 (부호 탐침으로 결정)
        self._cal_data   = []     # (j2, j3_corrected, j5) 목록

    # ── 초기화 ─────────────────────────────────────────────────────────────────

    def initialize(self, stage, articulation, carriage_prim_path: str) -> None:
        self._stage = stage
        self._articulation = articulation
        self._carriage_prim_path = carriage_prim_path
        prim = stage.GetPrimAtPath(carriage_prim_path)
        if prim.IsValid():
            self._carriage_prim = UsdGeom.Xformable(prim)

        self._dof_index = {}
        if articulation is not None:
            try:
                dof_names = list(articulation.dof_names)
                for i, n in enumerate(dof_names):
                    self._dof_index[n] = i
                carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} DOF: {dof_names}")
            except Exception:
                for i, n in enumerate(JOINT_NAMES):
                    self._dof_index[n] = i

        carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} initialized @ {carriage_prim_path}")

    def set_bridge(self, bridge) -> None:
        """기존 joint_state_bridge 설정."""
        self._bridge = bridge

    def set_motion_bridge(self, motion_bridge) -> None:
        """MotionCommandBridge 인스턴스 설정 (ui_builder에서 호출)."""
        self._motion_bridge = motion_bridge
        if motion_bridge is not None:
            motion_bridge.set_scenario_callbacks(
                on_start=self._on_motion_start,
                on_stop=self._on_motion_stop,
                on_pause=self._on_motion_pause,
                on_resume=self._on_motion_resume,
            )
            carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} MotionCommandBridge 연결됨")

    def _on_motion_start(self, params: dict) -> None:
        """MotionCommandBridge에서 start 서비스 호출 시 — 시작 요청.
        
        NOTE: ROS 콜백 스레드에서 호출됨. USD/Physics 객체 직접 접근 금지!
        플래그만 설정하고, 실제 시작은 on_physics_step()에서 처리.
        """
        self._start_requested = True
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} start requested")

    def _on_motion_stop(self) -> None:
        """MotionCommandBridge에서 stop 서비스 호출 시 — 정지 요청.
        
        NOTE: ROS 콜백 스레드에서 호출됨. USD/Physics 객체 직접 접근 금지!
        플래그만 설정하고, 실제 정지는 on_physics_step()에서 처리.
        """
        self._stop_requested = True
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} stop requested")

    def _on_motion_pause(self) -> int:
        """MotionCommandBridge에서 pause 서비스 호출 시 — 일시정지 요청.
        
        NOTE: ROS 콜백 스레드에서 호출됨. USD/Physics 객체 직접 접근 금지!
        플래그만 설정하고, 실제 정지는 on_physics_step()에서 처리.
        """
        self._pause_requested = True
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} pause requested at step {self._current_step}")
        return self._current_step

    def _on_motion_resume(self) -> int:
        """MotionCommandBridge에서 resume 서비스 호출 시."""
        self._paused = False
        self._pause_requested = False
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} resumed from step {self._current_step}")
        return self._current_step

    def set_joint_drive(self, joint_prim_path: str) -> None:
        if not joint_prim_path or self._stage is None:
            return
        try:
            prim = self._stage.GetPrimAtPath(joint_prim_path)
            if prim.IsValid():
                self._joint_drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} joint drive 연결 실패: {e}")

    # ── 제어 진입점 ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """시작 요청 (외부에서 호출용 — 플래그만 설정).
        
        실제 시작 로직은 _do_start()에서 Physics 스레드 안에서 처리.
        """
        self._start_requested = True
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} start requested (direct)")

    def _create_planner(self):
        if RAIL_PLANNER_MODE == "zigzag":
            segments, timing = build_zigzag_path()
            carb.log_warn(
                f"{LOG_TAG} pool_{self._pool_idx} zigzag plan: {timing.summary()}"
            )
            return RailPlannerZigzag(segments, timing)
        return RailPlannerClassic()

    def _current_step(self) -> int:
        if self._planner is None:
            return 0
        return self._planner.current_step

    def _do_start(self) -> None:
        """실제 시작 로직 (Physics 스레드에서만 호출)."""
        self._running = True
        self._rail_angle = 0.0
        self._planner = self._create_planner()
        self.set_rail_angle(self._rail_angle)

        # Bridge 상태를 RUNNING으로 설정 (직접 시작 시에도 상태 동기화)
        if self._motion_bridge is not None:
            self._motion_bridge.set_state_running()

        if self._sweep_table is None:
            # 첫 실행: 보정 페이즈 진입
            self._phase = _CALIBRATE
            self._cal_frame = 0
            self._cal_data = []
            # 중간점 j3=1.40 설정 (frame 1에서 r1 읽힘)
            self._set_cal_probe(0.5, SWEEP_J3_BOTTOM)
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} IK 보정 시작 ({IK_CAL_N_SAMPLES}샘플)")
        else:
            self._planner.reset(self._rail_angle)
            self._phase = self._planner.phase_name
            self.set_arm_joints(self._sweep_table[0])

        carb.log_info(
            f"{LOG_TAG} pool_{self._pool_idx} sweep started (planner={RAIL_PLANNER_MODE})"
        )

    def stop(self) -> None:
        self._running = False
        self._paused = False
        # Bridge 상태도 리셋
        if self._motion_bridge is not None:
            self._motion_bridge.reset()
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} sweep stopped")

    # ── physics step 메인 루프 ────────────────────────────────────────────────

    def on_physics_step(self, step_size: float) -> None:
        # Thread-safe 요청 처리 (ROS 콜백에서 설정된 플래그)
        self._process_pending_requests()
        
        # 외부 명령(override 모드)은 running 상태와 무관하게 처리
        if self._bridge is not None:
            cmd = self._bridge.get_command()
            if cmd is not None and cmd.get("override"):
                self.set_rail_angle(cmd["rail_angle"])
                self.set_arm_joints(cmd["joint_positions"])
                self._publish_state()
                return

        if not self._running:
            # running 아니어도 step_sync는 발행 (aqua_controller 연동용)
            if self._bridge is not None:
                self._bridge.publish_step_sync()
            self._publish_motion_status()
            return

        # 일시정지 상태 체크
        if self._paused:
            self._publish_motion_status()
            return

        # 메인 로직 실행
        self._run_physics_logic(step_size)

    def _process_pending_requests(self) -> None:
        """ROS 콜백에서 요청된 start/stop/pause를 Physics 스레드에서 안전하게 처리.
        
        우선순위: Stop > Pause > Start (Stop이 가장 높음)
        """
        # Stop 요청 처리 (최우선)
        if self._stop_requested:
            self._stop_requested = False
            self._start_requested = False  # Start 요청도 취소
            self._pause_requested = False  # Pause 요청도 취소
            self._running = False
            self._paused = False
            if self._motion_bridge is not None:
                self._motion_bridge.reset()
            carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} sweep stopped (deferred)")
            return
        
        # Pause 요청 처리
        if self._pause_requested:
            self._pause_requested = False
            self._paused = True
            # 현재 위치를 타겟으로 설정하여 즉시 멈춤
            self.set_rail_angle(self._rail_angle)
            carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} paused at step {self._current_step()} (deferred)")
            return
        
        # Start 요청 처리 (가장 낮은 우선순위)
        if self._start_requested:
            self._start_requested = False
            self._do_start()

    def _run_physics_logic(self, step_size: float) -> None:
        """Physics step 메인 로직 (on_physics_step에서 호출)."""
        if self._phase == _CALIBRATE:
            self._do_calibrate()
            return

        if self._planner is None:
            return

        result = self._planner.step(step_size, self._pose_from_table)
        self._rail_angle = result.rail_angle
        self.set_rail_angle(result.rail_angle)

        if result.arm_joints is not None:
            self.set_arm_joints(result.arm_joints)
        elif result.height_ratio is not None:
            self.set_arm_joints(self._pose_from_table(result.height_ratio))

        self._phase = result.phase_name

        if result.done:
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} 360° 청소 완료 — 정지")
            self.stop()
            if self._motion_bridge is not None:
                self._motion_bridge.mark_done()
            return

        self._publish_state()

    # ── IK 런타임 보정 ────────────────────────────────────────────────────────

    def _do_calibrate(self) -> None:
        """물리 스텝마다 호출. 3+N 프레임으로 IK 테이블 구축."""
        f = self._cal_frame
        self._cal_frame += 1

        # Frame 0: joints already set in start() → wait one step
        if f == _CAL_FRAME_SET_MID:
            return

        # Frame 1: read r1 at midpoint j3=1.40, then set j3+0.10 for sign probe
        if f == _CAL_FRAME_READ_R1:
            self._cal_r1 = self._blade_radius()
            self._set_cal_probe(0.5, SWEEP_J3_BOTTOM + 0.10)
            return

        # Frame 2: read r2, compute slope, set first sample
        if f == _CAL_FRAME_READ_R2:
            r2 = self._blade_radius()
            dr = r2 - self._cal_r1
            if abs(dr) > 5e-4:
                # slope = Δj3 / Δr  (can be negative or positive)
                self._cal_slope = 0.10 / dr
            else:
                self._cal_slope = 2.0  # safe default
            carb.log_warn(
                f"{LOG_TAG} pool_{self._pool_idx} IK probe: r1={self._cal_r1:.4f} "
                f"r2={r2:.4f} slope={self._cal_slope:.3f}"
            )
            # Set sample[0] with nominal j3
            self._set_cal_sample(0)
            return

        # Frame 3+k: read r for sample[k], store corrected j3
        k = f - 3
        if k < IK_CAL_N_SAMPLES:
            r = self._blade_radius()
            dr = r - TANK_RADIUS

            t = k / max(1, IK_CAL_N_SAMPLES - 1)
            j2 = SWEEP_J2_BOTTOM + t * (SWEEP_J2_TOP - SWEEP_J2_BOTTOM)
            j5 = SWEEP_J5_BOTTOM + t * (SWEEP_J5_TOP - SWEEP_J5_BOTTOM)
            j3_nom = SWEEP_J3_BOTTOM + t * (SWEEP_J3_TOP - SWEEP_J3_BOTTOM)

            # 1차 보정: j3 = j3_nom - slope * dr
            j3 = j3_nom - self._cal_slope * dr
            j3 = max(0.3, min(2.8, j3))   # 안전 범위 클램프

            self._cal_data.append((j2, j3, j5))
            carb.log_warn(
                f"{LOG_TAG} pool_{self._pool_idx} cal[{k:02d}] "
                f"r={r:.4f} dr={dr:+.4f} j3_nom={j3_nom:.3f} j3={j3:.3f}"
            )

            if k + 1 < IK_CAL_N_SAMPLES:
                self._set_cal_sample(k + 1)
                return

        # 보정 완료 — 테이블 생성
        self._sweep_table = [
            {
                "joint_1": 0.0,
                "joint_2": float(j2),
                "joint_3": float(j3),
                "joint_4": 0.0,
                "joint_5": float(j5),
                "joint_6": 0.0,
            }
            for j2, j3, j5 in self._cal_data
        ]
        carb.log_warn(
            f"{LOG_TAG} pool_{self._pool_idx} IK 보정 완료: "
            f"{len(self._sweep_table)}샘플 → planner 진입"
        )
        if self._planner is None:
            self._planner = self._create_planner()
        self._planner.reset(self._rail_angle)
        self._phase = self._planner.phase_name
        self.set_arm_joints(self._sweep_table[0])

    def _set_cal_probe(self, t: float, j3: float) -> None:
        """보정 탐침용 joints 설정 (부호 검출)."""
        j2 = SWEEP_J2_BOTTOM + t * (SWEEP_J2_TOP - SWEEP_J2_BOTTOM)
        j5 = SWEEP_J5_BOTTOM + t * (SWEEP_J5_TOP - SWEEP_J5_BOTTOM)
        self.set_arm_joints({
            "joint_1": 0.0, "joint_2": j2,
            "joint_3": j3,  "joint_4": 0.0,
            "joint_5": j5,  "joint_6": 0.0,
        })

    def _set_cal_sample(self, idx: int) -> None:
        """샘플 idx 에 해당하는 초기 joints 설정 (j3 = 공칭값 1.40)."""
        t = idx / max(1, IK_CAL_N_SAMPLES - 1)
        j2 = SWEEP_J2_BOTTOM + t * (SWEEP_J2_TOP - SWEEP_J2_BOTTOM)
        j3 = SWEEP_J3_BOTTOM + t * (SWEEP_J3_TOP - SWEEP_J3_BOTTOM)
        j5 = SWEEP_J5_BOTTOM + t * (SWEEP_J5_TOP - SWEEP_J5_BOTTOM)
        self.set_arm_joints({
            "joint_1": 0.0, "joint_2": j2,
            "joint_3": j3,  "joint_4": 0.0,
            "joint_5": j5,  "joint_6": 0.0,
        })

    def _blade_radius(self) -> float:
        """link_6 world transform 읽어 블레이드 팁의 pool-local 수평 반경 반환.

        link_6 로컬 +Z 방향으로 SCRAPER_TOOL_Z 만큼 이동한 점이 블레이드 팁.
        USD Gf.Matrix4d 행-벡터 규약 (p_world = p_local * M):
          mat[2][0..2] = 로컬 Z축의 world 방향 (row 2)
          mat[3][0..2] = 이동(translation, row 3)

        주의: blade tip 및 pool center 모두 world 좌표로 읽어야 함.
        pool_center=(0,0)은 pool-local 원점이므로 world 반경 계산에 사용 불가.
        """
        try:
            from pxr import Usd
            link6_path = f"{self._carriage_prim_path}/m1013/link_6"
            prim = self._stage.GetPrimAtPath(link6_path)
            if not prim.IsValid():
                return TANK_RADIUS
            cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            mat = cache.GetLocalToWorldTransform(prim)
            # USD row-vector convention: 로컬 Z축 = row 2, translation = row 3
            tx, ty = mat[3][0], mat[3][1]
            zx, zy = mat[2][0], mat[2][1]
            tip_x = tx + SCRAPER_TOOL_Z * zx
            tip_y = ty + SCRAPER_TOOL_Z * zy

            # Pool_n Xform의 world 위치를 읽어 pool 중심 좌표 획득
            # (self._pool_center 는 pool-local (0,0) — world 반경 계산에 사용 불가)
            pool_prim = self._stage.GetPrimAtPath(f"/World/Pools/Pool_{self._pool_idx}")
            if pool_prim.IsValid():
                pm = cache.GetLocalToWorldTransform(pool_prim)
                cx, cy = pm[3][0], pm[3][1]
            else:
                cx, cy = self._pool_center   # standalone 환경 fallback

            return math.sqrt((tip_x - cx) ** 2 + (tip_y - cy) ** 2)
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} _blade_radius: {e}")
            return TANK_RADIUS

    # ── IK 테이블 보간 ────────────────────────────────────────────────────────

    def _pose_from_table(self, height_ratio: float) -> dict:
        """height_ratio 0.0=하단, 1.0=상단. 테이블 선형 보간.

        테이블이 없으면 기존 _sweep_pose 로 fallback.
        """
        if not self._sweep_table:
            return self._sweep_pose(height_ratio)

        n = len(self._sweep_table)
        idx_f = max(0.0, min(float(n - 1), height_ratio * (n - 1)))
        i0 = int(idx_f)
        frac = idx_f - i0

        if i0 >= n - 1:
            return dict(self._sweep_table[-1])

        p0, p1 = self._sweep_table[i0], self._sweep_table[i0 + 1]
        return {k: p0[k] + frac * (p1[k] - p0[k]) for k in p0}

    # ── 저수준 액추에이터 ────────────────────────────────────────────────────

    def set_rail_angle(self, angle_rad: float) -> None:
        angle_deg = math.degrees(angle_rad)

        if self._joint_drive is not None:
            try:
                self._joint_drive.GetTargetPositionAttr().Set(angle_deg)
                return
            except Exception:
                pass

        if self._carriage_prim is None:
            return
        cx, cy = self._pool_center
        x = cx + RAIL_CENTER_R * math.cos(angle_rad)
        y = cy + RAIL_CENTER_R * math.sin(angle_rad)
        yaw_deg = angle_deg + 180.0

        xf = self._carriage_prim
        xf.ClearXformOpOrder()
        xf.AddTranslateOp().Set(Gf.Vec3d(x, y, RAIL_MOUNT_Z))
        xf.AddRotateZOp().Set(yaw_deg)

    def set_arm_joints(self, joint_positions: dict) -> None:
        if self._articulation is None:
            return
        try:
            current = list(self._articulation.get_joint_positions())
            for name, value in joint_positions.items():
                idx = self._dof_index.get(name)
                if idx is not None and idx < len(current):
                    current[idx] = value
            self._articulation.set_joint_positions(np.array(current, dtype=float))
        except Exception as e:
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} set_arm_joints: {e}")

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    def _sweep_pose(self, height_ratio: float) -> dict:
        """fallback: 테이블 없을 때 사용하는 선형 보간 pose."""
        j2 = SWEEP_J2_BOTTOM + height_ratio * (SWEEP_J2_TOP - SWEEP_J2_BOTTOM)
        j3 = SWEEP_J3_BOTTOM + height_ratio * (SWEEP_J3_TOP - SWEEP_J3_BOTTOM)
        j5 = SWEEP_J5_BOTTOM + height_ratio * (SWEEP_J5_TOP - SWEEP_J5_BOTTOM)
        pose = {"joint_1": 0.0}
        pose.update(WALL_REACH_JOINTS)
        pose["joint_2"] = j2
        pose["joint_3"] = j3
        pose["joint_5"] = j5
        return pose

    def _publish_state(self) -> None:
        if self._bridge is None:
            return
        self._bridge.publish_joint_states(self._safe_get_positions(), self._rail_angle)
        self._bridge.publish_step_sync()
        self._publish_motion_status()

    def _publish_motion_status(self) -> None:
        """MotionCommandBridge로 진행상황 발행."""
        if self._motion_bridge is None:
            return

        progress = self._calculate_progress()
        phase_name = self._get_phase_name()
        current_step = self._current_step()
        total_steps = self._planner.total_steps if self._planner is not None else 0

        self._motion_bridge.publish_status(
            progress=progress,
            current_step=current_step,
            total_steps=total_steps,
            phase=phase_name,
        )

    def _calculate_progress(self) -> float:
        """전체 진행률 계산 (0.0 ~ 1.0)."""
        if self._phase == _CALIBRATE:
            return 0.0
        if self._planner is None:
            return 0.0
        return self._planner.calculate_progress()

    def _get_phase_name(self) -> str:
        """현재 phase 이름 반환."""
        if self._phase == _CALIBRATE:
            return self.PHASE_CALIBRATE
        if isinstance(self._phase, str):
            return self._phase
        return self.PHASE_DONE

    def _safe_get_positions(self) -> list:
        if self._articulation is None:
            return [0.0] * len(JOINT_NAMES)
        try:
            return list(self._articulation.get_joint_positions())
        except Exception:
            return [0.0] * len(JOINT_NAMES)

    # ── 상태 조회 ─────────────────────────────────────────────────────────────

    @property
    def rail_angle_deg(self) -> float:
        return math.degrees(self._rail_angle)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def progress(self) -> float:
        return self._calculate_progress()
