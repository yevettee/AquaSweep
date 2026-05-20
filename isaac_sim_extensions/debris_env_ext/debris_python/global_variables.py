EXTENSION_TITLE = "debris.env"
EXTENSION_DESCRIPTION = "Tank debris particle system for AquaSweep simulation."

DEBRIS_COUNT = 10
DEBRIS_RADIUS = 0.015       # m
DEBRIS_COLOR_HEX = "#5C3D1E"

# 이물질 스폰 범위: water_tank_env_ext params.py의 TANK_RADIUS(4.0m)보다 작아야 함
TANK_RANGE = 3.8            # m (수조 반경 4.0m에서 약간 안쪽)
FLOOR_Z = 0.0               # 수조 바닥 Z 좌표 (water_tank_env_ext params.TANK_FLOOR_Z와 일치)
