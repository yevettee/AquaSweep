# Wheel Ground Contact System

바퀴형 수중 로봇이 수조 바닥에서 마찰력으로 구동되도록 하는 바닥 접촉 시스템.

## 문제 배경

PhysX 시뮬레이션에서 수중 로봇은 부력으로 인해 바닥에서 떠오르거나, solver 오차로 인해 바닥을 뚫고 들어가는 문제가 발생한다.

- **부력 문제**: 로봇이 떠오르면 바퀴가 바닥에 닿지 않아 마찰력 = 0
- **침투 문제**: PhysX contact solver 오차로 `wheel_low_z < 0` (바닥 아래로 침투)

## 해결 전략

### 1. 부력 비활성화

```python
# global_variables.py
ROBOT_VOLUME_M3 = 0.0  # 부력 비활성화
```

부력을 0으로 설정하여 로봇이 중력으로 자연스럽게 바닥에 가라앉도록 한다.

### 2. 하이브리드 바닥 구속

`physics_applier.py`에서 매 physics step마다 `wheel_low_z`를 측정하고 보정한다.

```
wheel_low_z = 바퀴 최저점의 world Z 좌표
목표: wheel_low_z = 0.0 (바닥 표면)
```

#### 보정 방식

| 침투 깊이 | 방식 | 설명 |
|-----------|------|------|
| >= 3mm | 직접 위치 보정 | `base_link_z += penetration` |
| < 3mm | 스프링-댐퍼 힘 | `F = K * penetration + D * velocity` |

- **직접 보정**: 큰 침투는 즉시 위치를 올려서 수정
- **스프링-댐퍼**: 작은 침투는 힘으로 부드럽게 보정 (진동 방지)

## 주요 파라미터

```python
# physics_applier.py
_FLOOR_SPRING_K = 100000.0  # N/m — 스프링 상수
_FLOOR_DAMPING = 5000.0     # N·s/m — 댐핑 계수
_WHEEL_RADIUS_FALLBACK = 0.049  # m — 바퀴 반경 기본값
```

## 구현 위치

### 파일 구조

```
isaac_sim_extensions/
├── underwater_robot_ext/
│   └── underwater_robot_python/
│       └── global_variables.py    # ROBOT_VOLUME_M3 = 0.0
└── water_tank_env_ext/
    └── water_tank_env_python/
        └── physics_applier.py     # 바닥 구속 로직
```

### 핵심 함수

- `_get_wheel_low_z(stage, robot_root)`: 바퀴 최저점 Z 계산
- `WaterPhysicsApplier.apply(dt)`: 매 physics step에서 바닥 구속 적용

## 동작 흐름

```
1. on_physics_step() 호출 (60Hz)
   │
   ▼
2. WaterPhysicsApplier.apply(dt)
   │
   ▼
3. 각 로봇에 대해:
   ├── wheel_low_z 측정
   │
   ├── wheel_low < 0 (침투)?
   │   ├── 침투 >= 3mm → 직접 위치 보정
   │   └── 침투 < 3mm → 스프링-댐퍼 힘 적용
   │
   └── 기타 물리력 적용 (항력, 지면효과 등)
```

## 관련 설정

### aquasweep 속성 (USD)

로봇의 `base_link`에 적용되는 커스텀 속성:

| 속성 | 타입 | 설명 |
|------|------|------|
| `aquasweep:volume` | float | 부력 계산용 부피 (m³) |
| `aquasweep:half_height` | float | 로봇 반높이 (m) |
| `aquasweep:cd_linear` | float | 선형 항력 계수 |
| `aquasweep:cd_angular` | float | 각속도 항력 계수 |

### 스폰 높이

```python
# global_variables.py
ROBOT_SPAWN_Z_M = 0.05  # 초기 스폰 높이 (바퀴 반경 근사)
```

## 테스트

Isaac Sim Script Editor에서:

```python
exec(open("/home/woody/AquaSweep/scripts/compare_z_run_scenario.py").read())
snap_before()
# RUN 실행 후 대기
snap_after()
compare_saved()
```

기대 결과: 모든 로봇의 `wheel_low_z ≈ 0.0` (±0.003m 이내)
