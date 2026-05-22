# AquaSweep 통합 테스트 가이드

이 문서는 Dashboard → Planner → Controller → Isaac Sim (underwater_robot_ext) 간의 통합 테스트 방법을 설명합니다.

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Isaac Sim                                    │
│  ┌─────────────────┐              ┌────────────────────────┐        │
│  │  Dashboard Ext  │              │  underwater_robot_ext  │        │
│  │  (UI 버튼)       │              │  (로봇 물리 시뮬레이션)  │        │
│  └────────┬────────┘              └───────────▲────────────┘        │
└───────────┼────────────────────────────────────┼────────────────────┘
            │ /planner/start                     │ /under_robot_1/cmd_vel
            │ /pool_1/start_clean_floor          │
            ▼                                    │
┌───────────────────────┐    /pool_1/clean_floor │
│    aqua_planner       │──────Action────────────┼─────────┐
│  (fish_count 체크)     │                        │         │
└───────────▲───────────┘                        │         ▼
            │ /pool_1/status                     │  ┌──────────────────┐
            │ (PoolStatus)                       │  │  aqua_controller │
            │                                    │  │  (cmd_vel 발행)   │
┌───────────┴───────────┐                        │  └──────────────────┘
│    aqua_mock          │                        │         │
│  (Mock 데이터 발행)    │                        └─────────┘
└───────────────────────┘
```

## 테스트 시나리오

### 시나리오 1: CLI 직접 Action 호출 (fish_count 체크 우회)

Planner의 fish_count 체크를 거치지 않고 Controller에 직접 Action을 보내는 방법입니다.

**장점**: 가장 간단하고 빠른 테스트 방법  
**단점**: fish_count 로직 자체는 테스트되지 않음

#### 실행 순서

```bash
# 터미널 1: Isaac Sim 실행
# 1. Isaac Sim을 실행하고 underwater_robot_ext를 로드
# 2. Isaac Sim UI에서 Play 버튼 클릭

# 터미널 2: ROS2 환경 설정 및 Controller 실행
source /opt/ros/humble/setup.bash
source ~/AquaSweep/water_ws/install_isaac/setup.bash
ros2 run aqua_controller controller_node --ros-args \
    -p pool_id:=pool_1 \
    -p robot_name:=under_robot_1

# 터미널 3: Action 직접 호출
source /opt/ros/humble/setup.bash
source ~/AquaSweep/water_ws/install_isaac/setup.bash
ros2 action send_goal /pool_1/clean_floor aqua_interfaces/action/CleanFloor "{}" --feedback
```

#### 예상 결과
- Controller에서 "Goal accepted" 로그 출력
- Isaac Sim에서 로봇이 나선형 패턴으로 이동
- Action 완료 시 `success: true` 반환

---

### 시나리오 2: fish_count 조절 가능한 통합 테스트

fish_count를 수동으로 조절하여 Planner의 로직까지 테스트합니다.

#### 방법 A: Mock Publisher 파라미터 사용 (권장)

```bash
# 터미널 1: Isaac Sim 실행 및 Play

# 터미널 2: Controller 실행
ros2 run aqua_controller controller_node --ros-args \
    -p pool_id:=pool_1 \
    -p robot_name:=under_robot_1

# 터미널 3: Planner 실행
ros2 run aqua_planner planner_node --ros-args \
    -p pool_ids:="['pool_1']"

# 터미널 4: Mock Publisher 실행 (fish_count를 0으로 고정)
ros2 run aqua_mock mock_publisher --ros-args -p fixed_fish_count:=0

# 터미널 5: 청소 시작 서비스 호출
ros2 service call /planner/start std_srvs/srv/Trigger "{}"
# 또는 개별 풀 시작
ros2 service call /pool_1/start_clean_floor std_srvs/srv/Trigger "{}"
```

#### 방법 B: CLI로 PoolStatus 직접 발행

Mock Publisher 없이 수동으로 상태 발행:

```bash
# fish_count = 0 으로 발행 (청소 시작 가능)
ros2 topic pub /pool_1/status aqua_interfaces/msg/PoolStatus \
    "{pollution_level: 0.5, fish_type: 'sturgeon', fish_count: 0, fish_count_suspicious: 0}" \
    -r 1

# fish_count = 5 로 발행 (청소 불가 - 물고기 있음)
ros2 topic pub /pool_1/status aqua_interfaces/msg/PoolStatus \
    "{pollution_level: 0.5, fish_type: 'sturgeon', fish_count: 5, fish_count_suspicious: 0}" \
    -r 1
```

---

### 시나리오 3: Dashboard UI 통합 테스트

Isaac Sim 내 Dashboard Extension을 통한 전체 통합 테스트입니다.

#### 실행 순서

```bash
# 터미널 1: Isaac Sim 실행
# - water_tank_env_ext 로드
# - underwater_robot_ext 로드  
# - dashboard_ext 로드
# - Play 버튼 클릭

# 터미널 2: Controller 실행
ros2 run aqua_controller controller_node --ros-args \
    -p pool_id:=pool_1 \
    -p robot_name:=under_robot_1

# 터미널 3: Planner 실행
ros2 run aqua_planner planner_node

# 터미널 4: Mock Publisher 실행 (fish_count = 0)
ros2 run aqua_mock mock_publisher --ros-args -p fixed_fish_count:=0
```

#### Dashboard UI 테스트
1. Dashboard Extension UI에서 "Global Start" 버튼 클릭
2. 또는 "Start Pool 1" 버튼 클릭
3. 로봇 동작 확인

---

## fish_count 조절 옵션 상세

### 옵션 1: Mock Publisher 파라미터

```bash
# fish_count를 0으로 고정 (청소 가능)
ros2 run aqua_mock mock_publisher --ros-args -p fixed_fish_count:=0

# fish_count를 5로 고정 (청소 불가)
ros2 run aqua_mock mock_publisher --ros-args -p fixed_fish_count:=5

# 기본값 (-1): 0~4 사이 cycling
ros2 run aqua_mock mock_publisher
```

### 옵션 2: ros2 param set (런타임 변경)

```bash
# Mock Publisher 실행 중 파라미터 변경
ros2 param set /mock_publisher_node fixed_fish_count 0
ros2 param set /mock_publisher_node fixed_fish_count 5
```

---

## 디버깅 명령어

### 토픽 모니터링

```bash
# Pool 상태 확인
ros2 topic echo /pool_1/status

# Robot 상태 확인
ros2 topic echo /under_robot_1/status

# cmd_vel 명령 확인 (로봇 제어 명령)
ros2 topic echo /under_robot_1/cmd_vel
```

### 서비스 및 액션 확인

```bash
# 사용 가능한 서비스 목록
ros2 service list | grep -E "(planner|clean)"

# 사용 가능한 액션 목록
ros2 action list

# 액션 서버 상태 확인
ros2 action info /pool_1/clean_floor
```

### 노드 상태 확인

```bash
# 실행 중인 노드 목록
ros2 node list

# 특정 노드 정보
ros2 node info /aqua_planner
ros2 node info /aqua_controller
```

---

## 문제 해결

### "CleanFloor server not available" 오류
- Controller 노드가 실행 중인지 확인
- pool_id 파라미터가 일치하는지 확인

```bash
ros2 action list  # /pool_1/clean_floor 가 있는지 확인
```

### "No eligible pools" 오류
- Planner가 fish_count를 확인할 수 없음
- Mock Publisher가 실행 중인지 확인
- fish_count가 0인지 확인

```bash
ros2 topic echo /pool_1/status --once  # fish_count 확인
```

### Isaac Sim에서 로봇이 움직이지 않음
- Isaac Sim이 Play 상태인지 확인
- underwater_robot_ext가 로드되었는지 확인
- cmd_vel 토픽에 메시지가 발행되는지 확인

```bash
ros2 topic echo /under_robot_1/cmd_vel  # 메시지가 오는지 확인
```

---

## 빠른 테스트 체크리스트

- [ ] Isaac Sim 실행 및 Play 상태
- [ ] underwater_robot_ext 로드 확인
- [ ] Controller 노드 실행
- [ ] (통합 테스트 시) Planner 노드 실행
- [ ] (통합 테스트 시) Mock Publisher 실행 (`-p fixed_fish_count:=0`)
- [ ] Action 또는 Service 호출
- [ ] 로봇 동작 확인
