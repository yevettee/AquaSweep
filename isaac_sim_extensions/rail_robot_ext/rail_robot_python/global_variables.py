EXTENSION_TITLE = "rail_robot"
EXTENSION_DESCRIPTION = "수조 벽면 청소용 원형 레일 협동로봇 (Doosan M1013)"

# M1013: 리치 1.3m, 페이로드 10kg — 벽 높이 1.5m 커버에 가장 적합한 physics-ready 모델
# 경로는 AquaSweep 리포지토리 기준 상대 경로로 계산
import os as _os
_REPO_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
COBOT_USD_PATH = _os.path.join(_REPO_ROOT, "assets", "robot", "m1013.usd")

# Doosan M시리즈 공통 조인트 이름 (M0609·M1013 동일)
JOINT_NAMES = [
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6",
]

# 수조 파라미터 (water_tank_env_python/params.py 와 동기화)
TANK_RADIUS = 4.0       # 수조 내경 반경 (m)
TANK_INNER_Z = 1.5      # 벽면 높이 (m)
WALL_THICKNESS = 0.03   # 벽 두께 (m)

# 레일 치수 (rail_builder._RAIL_W / _RAIL_H 와 동기화)
RAIL_W = 0.08           # 레일 단면 폭 (m)
RAIL_H = 0.06           # 레일 단면 높이 (m)

# 레일 중심 반경: 벽 외면에서 레일 단면 중심까지
RAIL_CENTER_R = TANK_RADIUS + WALL_THICKNESS + RAIL_W * 0.5  # = 4.07 m

# 캐리지 마운트 높이: 레일 단면 중심 (경첩 pivot 높이)
# M1013 리치 1.3m 기준: 레일 중심(1.53m)에서 바닥까지 1.53m → 하단 23cm 미도달
# 실제 청소 도달 범위: z = 0.23 m ~ 1.5 m (벽 상단)
RAIL_MOUNT_Z = TANK_INNER_Z + RAIL_H * 0.5  # = 1.53 m

# ── 자율 청소 궤적 파라미터 ──────────────────────────────────────────────────
RAIL_PLANNER_MODE = "zigzag"   # "classic" | "zigzag"

RAIL_STEPS = 6           # 360° ÷ 6 = 60° 단위 이동 (classic 전용)
ARM_SWEEP_DURATION = 1.2 # 팔이 상단→하단 쓸기까지 걸리는 시간 (초)
ARM_HOME_DURATION  = 0.3 # 스윕 완료 후 홈 자세로 이동하는 시간 (초)
ARM_RESET_DURATION = 0.3 # 홈 자세에서 스윕 시작 자세로 복귀하는 시간 (초)
RAIL_MOVE_DURATION = 0.3 # 다음 각도 위치로 이동하는 시간 (초)

# zigzag 전용 (rail_planner_zigzag.py)
# ZIGZAG_FULL_ROTATION_DURATION 이 1바퀴 sim-time 의 기준 (초).
# ZIGZAG_DOWN_UP_DURATION 으로 half-stroke 개수를 정하고, 세그먼트 시간은 lap/n 으로 맞춤.
RAIL_STEP_ANGLE_RAD = None   # None → segment count 로 step 자동
ZIGZAG_DOWN_UP_DURATION = 2.0        # 팔 하단↔상단 1주기 목표 (초)
ZIGZAG_FULL_ROTATION_DURATION = 60.0 # 레일 360° 1바퀴 목표 sim-time (초, 8mØ≈25.6m)
COUPLED_SWEEP_DURATION = None        # None → lap / segment_count 자동

# 레일 이동 전후 홈 자세 [j1=0, j2=0, j3=90°, j4=0, j5=90°, j6=0]
ARM_HOME_JOINTS = {
    "joint_1": 0.0,
    "joint_2": 0.0,
    "joint_3": 1.5708,  # 90°
    "joint_4": 0.0,
    "joint_5": 1.5708,  # 90°
    "joint_6": 0.0,
}

# 벽면을 향한 기본 자세 — SWEEP_J*_TOP 과 동일하게 유지 (일관성)
# 레일(z=1.53m) 위 로봇이 수조 안쪽 벽을 긁으려면 joint_2가
# 충분히 음수여야 팔이 벽 위를 넘어 안으로 들어갈 수 있음
# 초기 자세: [j1=0, j2=0, j3=90°, j4=0, j5=90°, j6=0] (사용자 확인값)
# 스윕은 아래(j2=1.8) → 위(j2=0.0) 방향
# joint_3을 1.571→1.40으로 줄여 블레이드가 벽면 표면에만 닿고 뚫지 않도록
WALL_REACH_JOINTS = {
    "joint_2":  0.0,    # = SWEEP_J2_TOP  (벽면 상단)
    "joint_3":  1.40,   # 90°→80° 로 줄여 penetration 방지
    "joint_4":  0.0,
    "joint_5":  1.571,  # 90° = π/2 유지
    "joint_6":  0.0,
}

# 스윕 방향: 아래(BOTTOM) → 위(TOP)
# joint_2: 양수 클수록 팔이 안쪽/아래, 0에 가까울수록 위쪽
SWEEP_J2_TOP    =  0.0   # 벽면 상단 (스윕 종료 위치)
SWEEP_J2_BOTTOM =  1.8   # 벽면 하단 (스윕 시작 위치, 필요 시 조정)

# 상단 자세 보정
SWEEP_J3_TOP    =  1.40   # 80° (penetration 방지)
SWEEP_J5_TOP    =  1.571  # 90°

# 하단 자세 보정
SWEEP_J3_BOTTOM =  1.40   # 동일하게 유지 (일정한 벽 거리)
SWEEP_J5_BOTTOM =  1.0    # wrist 각도 보정

# ── 스크레이퍼(긁개) 도구 ────────────────────────────────────────────────────
# M1013 USD default prim이 "m1013" 컨테이너이므로 상대 경로로 지정
SCRAPER_ATTACH_LINK = "m1013/link_6"

# 블레이드 치수 (m)
SCRAPER_BLADE_WIDTH  = 0.20   # Y 방향 (벽면 수평 폭)
SCRAPER_BLADE_HEIGHT = 0.15   # Z 방향 (벽면 수직 높이)
SCRAPER_BLADE_THICK  = 0.012  # X 방향 (블레이드 두께)

# ── 벽면 스윕 IK 런타임 보정 파라미터 ────────────────────────────────────────
# 블레이드 팁 ~ link_6 원점 간 거리 (link_6 로컬 +Z 방향, 단위 m)
# 넥 300mm + 팬플레이트 56mm + 블레이드 15mm 끝단 = 371mm ≈ 0.378m
SCRAPER_TOOL_Z = 0.378

# 런타임 보정 샘플 수 (물리 프레임 기준, 프레임당 1샘플 읽기)
# 23 = 3(부호 탐침) + 20(샘플) → 60fps 기준 약 0.4초
IK_CAL_N_SAMPLES = 20
