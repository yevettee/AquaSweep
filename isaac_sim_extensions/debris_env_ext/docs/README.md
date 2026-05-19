# debris.env Extension

AquaSweep 프로젝트의 수조 이물질 파티클 시스템 Extension.

## 개요

PhysX GPU 파티클을 이용하여 수조 바닥에 이물질(분변 등)을 시뮬레이션합니다.

## 사용법

1. Isaac Sim Extension Manager에서 `debris.env` 활성화
2. UI 패널에서 이물질 수, 크기 설정
3. **SPAWN** 버튼으로 이물질 생성
4. **CLEAR** 버튼으로 제거

## 다른 Extension과 연동

- `water.tank.env` Extension과 함께 사용하면 수조 씬 위에 이물질이 배치됩니다.
- `underwater.robot` Extension과 함께 사용하면 로봇이 이물질 주변을 주행합니다.

## 파라미터

| 파라미터 | 기본값 | 설명 |
|---|---|---|
| `DEBRIS_COUNT` | 10 | 이물질 파티클 수 |
| `DEBRIS_RADIUS` | 0.015 m | 파티클 반지름 |
| `DEBRIS_COLOR_HEX` | #5C3D1E | 이물질 색상 |
| `TANK_RANGE` | 0.9 m | 스폰 범위 (수조 반경 내) |
| `FLOOR_Z` | 0.0 | 바닥 Z 좌표 |
