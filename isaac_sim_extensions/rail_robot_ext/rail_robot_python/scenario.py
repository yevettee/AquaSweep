"""Rail robot scenario — 수조 벽면 자율 순환 청소.

동작 순서 (1수조 기준):
  0. CALIBRATE : 시뮬레이션 첫 실행 시 자동 IK 보정 (약 0.4초, 이후 캐싱)
       - 높이별 블레이드 반경을 읽어 j3 보정값을 결정
  1. ARM_SWEEP  : 아래→위 직선 스윕 (IK 테이블 이용, 벽면 수직 유지)
  2. ARM_HOME   : 홈 자세 [0,0,90°,0,90°,0] 으로 이동 (이동 중 충돌 회피)
  3. RAIL_MOVE  : 레일 캐리지 20° 스무스 회전 (코사인 이징)
  4. ARM_RESET  : 홈 자세 → 스윕 시작(하단) 자세로 복귀
  5. 18단계(360°) 완료 후 반복

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
    RAIL_STEPS,
    ARM_SWEEP_DURATION,
    ARM_HOME_DURATION,
    ARM_HOME_JOINTS,
    ARM_RESET_DURATION,
    RAIL_MOVE_DURATION,
    TANK_RADIUS,
    SCRAPER_TOOL_Z,
    IK_CAL_N_SAMPLES,
)

LOG_TAG = "[rail_robot]"

_ARM_SWEEP = 0   # 아래→위 스윕
_RAIL_MOVE = 1   # 레일 이동 (캐리지 20° 회전, 코사인 이징)
_ARM_RESET = 2   # 홈 자세 → 스윕 시작 자세 복귀
_CALIBRATE = 3   # 첫 실행 전 IK 보정 (일회성)
_ARM_HOME  = 4   # 스윕 완료 후 홈 자세로 이동

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
    """

    # Phase names for status reporting
    PHASE_CALIBRATE = "calibrate"
    PHASE_ARM_SWEEP = "arm_sweep"
    PHASE_ARM_HOME = "arm_home"
    PHASE_RAIL_MOVE = "rail_move"
    PHASE_ARM_RESET = "arm_reset"
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
        self._phase = _ARM_SWEEP
        self._rail_angle = 0.0
        self._rail_angle_start = 0.0   # 레일 이동 시작 각도
        self._rail_angle_target = 0.0  # 레일 이동 목표 각도
        self._phase_elapsed = 0.0
        self._rail_step_count = 0      # 완료된 레일 이동 횟수

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
        """MotionCommandBridge에서 start 서비스 호출 시."""
        self.start()

    def _on_motion_stop(self) -> None:
        """MotionCommandBridge에서 stop 서비스 호출 시."""
        self.stop()

    def _on_motion_pause(self) -> int:
        """MotionCommandBridge에서 pause 서비스 호출 시."""
        self._paused = True
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} paused at step {self._rail_step_count}")
        return self._rail_step_count

    def _on_motion_resume(self) -> int:
        """MotionCommandBridge에서 resume 서비스 호출 시."""
        self._paused = False
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} resumed from step {self._rail_step_count}")
        return self._rail_step_count

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
        self._running = True
        self._rail_angle = 0.0
        self._phase_elapsed = 0.0
        self._rail_step_count = 0
        self.set_rail_angle(self._rail_angle)

        if self._sweep_table is None:
            # 첫 실행: 보정 페이즈 진입
            self._phase = _CALIBRATE
            self._cal_frame = 0
            self._cal_data = []
            # 중간점 j3=1.40 설정 (frame 1에서 r1 읽힘)
            self._set_cal_probe(0.5, SWEEP_J3_BOTTOM)
            carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} IK 보정 시작 ({IK_CAL_N_SAMPLES}샘플)")
        else:
            # 이후 실행: 캐시된 테이블 사용
            self._phase = _ARM_SWEEP
            self._phase_elapsed = 0.0
            self.set_arm_joints(self._sweep_table[0])

        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} sweep started")

    def stop(self) -> None:
        self._running = False
        self._paused = False
        carb.log_info(f"{LOG_TAG} pool_{self._pool_idx} sweep stopped")

    # ── physics step 메인 루프 ────────────────────────────────────────────────

    def on_physics_step(self, step_size: float) -> None:
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

        if self._phase == _CALIBRATE:
            self._do_calibrate()
            return

        self._phase_elapsed += step_size

        if self._phase == _ARM_SWEEP:
            ratio = min(1.0, self._phase_elapsed / ARM_SWEEP_DURATION)
            self.set_arm_joints(self._pose_from_table(ratio))
            if ratio >= 1.0:
                self._phase = _ARM_HOME
                self._phase_elapsed = 0.0

        elif self._phase == _ARM_HOME:
            ratio = min(1.0, self._phase_elapsed / ARM_HOME_DURATION)
            t = 0.5 * (1.0 - math.cos(math.pi * ratio))
            top_pose = self._pose_from_table(1.0)
            pose = {k: top_pose[k] + t * (ARM_HOME_JOINTS[k] - top_pose[k]) for k in top_pose}
            self.set_arm_joints(pose)
            if ratio >= 1.0:
                self._rail_angle_start = self._rail_angle
                step = 2.0 * math.pi / RAIL_STEPS
                self._rail_angle_target = (self._rail_angle + step) % (2.0 * math.pi)
                self._phase = _RAIL_MOVE
                self._phase_elapsed = 0.0

        elif self._phase == _RAIL_MOVE:
            ratio = min(1.0, self._phase_elapsed / RAIL_MOVE_DURATION)
            t = 0.5 * (1.0 - math.cos(math.pi * ratio))
            self.set_rail_angle(self._rail_angle_start + t * (self._rail_angle_target - self._rail_angle_start))
            self.set_arm_joints(ARM_HOME_JOINTS)  # 매 스텝 홈 자세 고정 (물리 흔들림 방지)
            if ratio >= 1.0:
                self._rail_angle = self._rail_angle_target
                self._rail_step_count += 1
                if self._rail_step_count >= RAIL_STEPS:
                    carb.log_warn(f"{LOG_TAG} pool_{self._pool_idx} 360° 청소 완료 — 정지")
                    self.stop()
                    if self._motion_bridge is not None:
                        self._motion_bridge.mark_done()
                    return
                self._phase = _ARM_RESET
                self._phase_elapsed = 0.0

        elif self._phase == _ARM_RESET:
            ratio = min(1.0, self._phase_elapsed / ARM_RESET_DURATION)
            t = 0.5 * (1.0 - math.cos(math.pi * ratio))
            bottom_pose = self._pose_from_table(0.0)
            pose = {k: ARM_HOME_JOINTS[k] + t * (bottom_pose[k] - ARM_HOME_JOINTS[k]) for k in ARM_HOME_JOINTS}
            self.set_arm_joints(pose)
            if ratio >= 1.0:
                self._phase = _ARM_SWEEP
                self._phase_elapsed = 0.0

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
            f"{len(self._sweep_table)}샘플 → ARM_SWEEP 진입"
        )
        self._phase = _ARM_SWEEP
        self._phase_elapsed = 0.0
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
        
        self._motion_bridge.publish_status(
            progress=progress,
            current_step=self._rail_step_count,
            total_steps=RAIL_STEPS,
            phase=phase_name,
        )

    def _calculate_progress(self) -> float:
        """전체 진행률 계산 (0.0 ~ 1.0)."""
        if RAIL_STEPS == 0:
            return 1.0
        
        # 기본 진행률: 완료된 rail step 수 기준
        base_progress = self._rail_step_count / RAIL_STEPS
        
        # 현재 phase 내 진행률 추가
        phase_weight = 1.0 / RAIL_STEPS
        if self._phase == _ARM_SWEEP:
            phase_progress = min(1.0, self._phase_elapsed / ARM_SWEEP_DURATION)
        elif self._phase == _ARM_HOME:
            phase_progress = min(1.0, self._phase_elapsed / ARM_HOME_DURATION)
        elif self._phase == _RAIL_MOVE:
            phase_progress = min(1.0, self._phase_elapsed / RAIL_MOVE_DURATION)
        elif self._phase == _ARM_RESET:
            phase_progress = min(1.0, self._phase_elapsed / ARM_RESET_DURATION)
        else:
            phase_progress = 0.0
        
        return min(1.0, base_progress + phase_progress * phase_weight * 0.25)

    def _get_phase_name(self) -> str:
        """현재 phase 이름 반환."""
        if self._phase == _CALIBRATE:
            return self.PHASE_CALIBRATE
        elif self._phase == _ARM_SWEEP:
            return self.PHASE_ARM_SWEEP
        elif self._phase == _ARM_HOME:
            return self.PHASE_ARM_HOME
        elif self._phase == _RAIL_MOVE:
            return self.PHASE_RAIL_MOVE
        elif self._phase == _ARM_RESET:
            return self.PHASE_ARM_RESET
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
