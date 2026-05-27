# Controller ↔ Isaac Sim 아키텍처

> Controller와 Isaac Sim 간 통신 구조 리팩토링 요약

---

## 1. 리팩토링 배경

### 기존 아키텍처 (cmd_vel 방식)

```
Controller Node                    Isaac Sim
    │                                  │
    ├── 경로 계획 (SpiralPlanner)       │
    ├── cmd_vel 계산                   │
    └────── /cmd_vel ─────────────────→ DifferentialController
```

**문제점:**
- Controller에서 physics_dt 동기화 필요 → Isaac Sim 타이밍과 불일치 가능
- 네트워크 지연으로 인한 cmd_vel 누락/지연
- ROS2 노드에서 물리 시뮬레이션 타이밍을 정확히 맞추기 어려움

### 새 아키텍처 (서비스 + 내부 플래너)

```
Controller Node                    Isaac Sim (underwater_robot_ext)
    │                                  │
    ├── Action Server                  ├── SpiralPlanner (내부)
    │   (CleanFloor/CleanWall)         ├── Service Server
    │                                  │   (start/stop/pause/resume)
    │                                  │
    └── start_clean_floor ────────────→ 모션 시작
    ←── clean_floor_status ─────────── 진행상황 publish
```

**개선점:**
- 물리 시뮬레이션과 동일한 tick에서 cmd_vel 생성 → 타이밍 완벽 동기화
- 네트워크 지연 영향 최소화 (시작/정지만 서비스 호출)
- Isaac Sim 내부에서 physics_dt 직접 사용 가능

---

## 2. 구성 요소

### 2.1 Controller Node (ROS2)

**위치:** `water_ws/src/aqua_controller/`

| 컴포넌트 | 역할 |
| --- | --- |
| `controller_node.py` | Action Server 호스팅 |
| `CleanFloorHandler` | Isaac Sim 서비스 호출 + motion_status 모니터링 |
| `CleanWallHandler` | 동일 패턴 |

**흐름:**
1. Planner로부터 Action Goal 수신
2. Isaac Sim에 `/{pool_id}/isaac/start_clean_floor` 서비스 호출
3. `/{pool_id}/clean_floor_status` 토픽 구독하여 진행상황 모니터링
4. `MotionStatus.state == DONE` 시 Action 완료

### 2.2 Isaac Sim Extension

**위치:** `isaac_sim_extensions/underwater_robot_ext/`

| 컴포넌트 | 역할 |
| --- | --- |
| `spiral_planner.py` | 아르키메데스 나선 경로 생성 |
| `robot_motion_controller.py` | 서비스 서버 + 모션 실행 |

**SpiralPlanner 구조:**
```
1. spiral_out   (중심 → 외곽)  ~50%
2. turn         (180° 회전)
3. spiral_return (외곽 → 중심)  ~50%
```

---

## 3. 인터페이스 요약

### Services (Controller → Isaac Sim)

| Service | 타입 |
| --- | --- |
| `/{pool_id}/isaac/start_clean_floor` | StartMotion |
| `/{pool_id}/isaac/stop_clean_floor` | StopMotion |
| `/{pool_id}/isaac/pause_clean_floor` | PauseMotion |
| `/{pool_id}/isaac/resume_clean_floor` | ResumeMotion |

> `/isaac/` prefix로 Planner 서비스와 구분

### Topics (Isaac Sim → Controller)

| Topic | 타입 |
| --- | --- |
| `/{pool_id}/clean_floor_status` | MotionStatus |

### MotionStatus 필드

| 필드 | 설명 |
| --- | --- |
| state | IDLE(0), RUNNING(1), PAUSED(2), DONE(3) |
| progress | 0.0 ~ 1.0 |
| phase | spiral_out / turn / spiral_return |

---

## 4. 시퀀스 다이어그램

```
Dashboard  →  Planner  →  Controller  →  Isaac Sim
    │            │            │              │
    │ start      │            │              │
    ├───────────→│ Action     │              │
    │            ├───────────→│ Service      │
    │            │            ├─────────────→│
    │            │            │              │ (모션 실행)
    │            │            │←─ status ────│
    │            │            │              │
    │            │←─ feedback ┤              │
    │            │            │←─ DONE ──────│
    │←─ success ─┤←─ success ─┤              │
```

---

## 5. 파라미터 관리

모션 파라미터는 `spiral_planner.py`에서 단일 관리:

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| tank_diameter | 8.0m | 수조 직경 |
| tank_margin | 0.8m | 벽면 여유 |
| robot_footprint | 0.686m | 로봇 폭 |
| linear_speed | 4.5 m/s | 선속도 |
| omega_max | 15.0 rad/s | 최대 각속도 |

Controller에서 `StartMotion.Request.params`로 오버라이드 가능 (0.0 = 기본값 사용).

---

## 6. CLI 테스트 명령어

### 서비스 호출

```bash
# 바닥 청소 시작
ros2 service call /pool_1/isaac/start_clean_floor aqua_interfaces/srv/StartMotion "{}"

# 파라미터 오버라이드로 시작
ros2 service call /pool_1/isaac/start_clean_floor aqua_interfaces/srv/StartMotion "{params: {linear_speed: 3.0, omega_max: 10.0}}"

# 일시정지
ros2 service call /pool_1/isaac/pause_clean_floor aqua_interfaces/srv/PauseMotion "{}"

# 재개
ros2 service call /pool_1/isaac/resume_clean_floor aqua_interfaces/srv/ResumeMotion "{}"

# 정지
ros2 service call /pool_1/isaac/stop_clean_floor aqua_interfaces/srv/StopMotion "{}"
```

### 토픽 모니터링

```bash
# 모션 상태 확인
ros2 topic echo /pool_1/clean_floor_status

# 상태 필드만 확인 (간략)
ros2 topic echo /pool_1/clean_floor_status --field state

# 진행률 확인
ros2 topic echo /pool_1/clean_floor_status --field progress
```

### 서비스/토픽 확인

```bash
# Isaac Sim 서비스 목록
ros2 service list | grep isaac

# 서비스 타입 확인
ros2 service type /pool_1/isaac/start_clean_floor

# 토픽 목록
ros2 topic list | grep clean_floor

# 토픽 발행 빈도 확인
ros2 topic hz /pool_1/clean_floor_status
```

### Action 테스트 (Planner → Controller)

```bash
# CleanFloor Action 전송
ros2 action send_goal /pool_1/clean_floor aqua_interfaces/action/CleanFloor "{}" --feedback

# Action 목록 확인
ros2 action list
```
