EXTENSION_TITLE = "rail_robot"
EXTENSION_DESCRIPTION = "수조 벽면 청소용 원형 레일 협동로봇 (Doosan M1013)"

# M1013: 리치 1.3m, 페이로드 10kg — 벽 높이 1.5m 커버에 가장 적합한 physics-ready 모델
COBOT_USD_PATH = (
    "/home/rokey/dev_ws/isaac_sim/src/doosan-robot2"
    "/usd/m1013.usd"
)

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
RAIL_STEPS = 36          # 360° ÷ 36 = 10° 단위 이동
ARM_SWEEP_DURATION = 8.0 # 팔이 상단→하단 쓸기까지 걸리는 시간 (초)
RAIL_MOVE_DURATION = 1.5 # 다음 각도 위치로 이동하는 시간 (초)

# 벽면을 향한 기본 자세 (joint 각도, 단위: radian)
# M1013은 M0609보다 링크가 길어 같은 각도에서 더 멀리 도달
WALL_REACH_JOINTS = {
    "joint_2": -1.0,    # shoulder: 앞으로 내림
    "joint_3":  1.5,    # elbow: 굽힘
    "joint_4":  0.0,
    "joint_5":  0.5,    # wrist: 벽면 수직
    "joint_6":  0.0,
}

# 스윕 시 joint_2 범위 (상단→하단)
# M1013 링크 길이가 더 길므로 joint_2 범위를 넓게 잡음
SWEEP_J2_TOP    = -1.3  # 벽면 상단 (mount 높이에서 위로 약간)
SWEEP_J2_BOTTOM = -0.2  # 벽면 하단 (바닥 근처까지)
