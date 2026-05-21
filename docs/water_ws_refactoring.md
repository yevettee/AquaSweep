# Water WS 리팩토링 가이드

## 개요

`water_ws`의 `aqua_planner`, `aqua_controller` 패키지를 Planner-Controller 아키텍처로 리팩토링하고, 통신 테스트를 위한 Mockup 노드를 추가했습니다.

## 아키텍처

```
┌─────────────────────────┐         Action Goal         ┌─────────────────────────┐
│   aqua_planner          │ ─────────────────────────▶  │  aqua_controller        │
│                         │                              │                         │
│  TaskExecutor           │  ◀───────────────────────── │  ActionServers          │
│  (Action Client)        │     Feedback / Result        │  - CleanFloor           │
└─────────────────────────┘                              │  - CleanWall            │
                                                         │  - MoveFish             │
                                                         └──────────┬──────────────┘
                                                                    │
                                                         ┌──────────▼──────────────┐
                                                         │  /under_robot_1/cmd_vel │
                                                         │  (Isaac Sim 수신)        │
                                                         └─────────────────────────┘
```

## 네이밍 규칙

| 항목 | 네이밍 | 예시 |
|------|--------|------|
| 풀 | `pool_{id}` | `pool_1`, `pool_2` |
| 수중 로봇 | `under_robot_{id}` | `under_robot_1` |
| 레일 로봇 | `rail_robot_{id}` | `rail_robot_1` |
| CleanFloor Action | `/pool_{id}/clean_floor` | `/pool_1/clean_floor` |
| CleanWall Action | `/pool_{id}/clean_wall` | `/pool_1/clean_wall` |
| MoveFish Action | `/pool_{id}/move_fish` | `/pool_1/move_fish` |
| 풀 상태 토픽 | `/pool_{id}/status` | `/pool_1/status` |
| 로봇 제어 | `/under_robot_{id}/cmd_vel` | `/under_robot_1/cmd_vel` |
| 로봇 상태 | `/under_robot_{id}/status` | `/under_robot_1/status` |

## 패키지 구조

### aqua_interfaces

```
aqua_interfaces/
├── action/
│   ├── CleanFloor.action    # 바닥 청소
│   ├── CleanWall.action     # 벽면 청소
│   └── MoveFish.action      # 물고기 이동 (신규)
└── msg/
    ├── RobotStatus.msg
    ├── TankStatus.msg
    └── TankPhysicalVariables.msg
```

### aqua_planner

```
aqua_planner/aqua_planner/
├── planner_node.py              # 메인 노드 + 서비스
├── task_executor.py             # Action Client 관리
└── mockup_vision_publisher.py   # 테스트용 풀 상태 발행
```

**주요 기능:**
- `/planner/start` 서비스: CleanFloor Action Goal 전송
- `/planner/pause` 서비스: 현재 작업 취소

### aqua_controller

```
aqua_controller/aqua_controller/
├── controller_node.py           # 메인 노드 + Action Servers
├── spiral_planner.py            # 나선형 경로 계획 (기존 유지)
├── action_handlers/
│   ├── __init__.py
│   ├── base_handler.py          # 추상 기본 클래스
│   ├── clean_floor_handler.py   # ✅ 실제 구현 (SpiralPlanner 연결)
│   ├── clean_wall_handler.py    # stub
│   └── move_fish_handler.py     # stub
├── mockup_controller_server.py  # 테스트용 Action Server
└── mockup_robot_status.py       # 테스트용 로봇 상태 발행
```

**구현 상태:**
| Handler | 상태 | 설명 |
|---------|------|------|
| CleanFloorHandler | ✅ 실제 구현 | SpiralPlanner + cmd_vel 발행 |
| CleanWallHandler | stub | 요청 수락 → 바로 성공 반환 |
| MoveFishHandler | stub | 요청 수락 → 바로 성공 반환 |

## 빌드 방법

```bash
cd ~/AquaSweep/water_ws

# 전체 빌드
colcon build

# 특정 패키지만 빌드
colcon build --packages-select aqua_interfaces aqua_planner aqua_controller

# 환경 설정
source install/setup.bash
```

## 테스트 방법

### 1. Mockup Controller로 통신 테스트 (Isaac Sim Dashboard 연동)

Isaac Sim Dashboard가 Action Client로 동작할 때, Mockup Server가 응답합니다.

```bash
# 터미널 1: Mockup Controller Server 실행
source ~/AquaSweep/water_ws/install/setup.bash
ros2 run aqua_controller mockup_controller_server --ros-args -p pool_id:=pool_1

# Isaac Sim에서 dashboard_ext 로드 후 START 버튼 클릭
# → Mockup이 Goal 수신 → Feedback 발행 → Result 반환
```

**예상 로그:**
```
[INFO] MockupControllerServer ready | pool=pool_1
  Actions: /pool_1/clean_floor, /pool_1/clean_wall, /pool_1/move_fish
[INFO] MockupController: CleanFloor started
[INFO] MockupController: CleanFloor completed
```

### 2. 실제 Controller로 테스트 (cmd_vel 발행)

```bash
# 터미널 1: Controller 실행
ros2 run aqua_controller controller_node --ros-args \
    -p robot_name:=under_robot_1 \
    -p pool_id:=pool_1

# 터미널 2: Action 직접 호출
ros2 action send_goal /pool_1/clean_floor aqua_interfaces/action/CleanFloor "{}" --feedback

# 터미널 3: cmd_vel 모니터링
ros2 topic echo /under_robot_1/cmd_vel
```

### 3. Planner + Controller 연동 테스트

```bash
# 터미널 1: Mockup Controller
ros2 run aqua_controller mockup_controller_server --ros-args -p pool_id:=pool_1

# 터미널 2: Planner
ros2 run aqua_planner planner_node --ros-args -p pool_id:=pool_1

# 터미널 3: Planner 시작
ros2 service call /planner/start std_srvs/srv/Trigger
```

### 4. 통신 상태 확인

```bash
# Action 목록
ros2 action list
# /pool_1/clean_floor
# /pool_1/clean_wall
# /pool_1/move_fish

# Action 상세 정보
ros2 action info /pool_1/clean_floor

# Topic 목록
ros2 topic list

# Service 목록
ros2 service list
```

## 확장 가이드

### 새로운 Action Handler 추가

1. `action_handlers/` 디렉토리에 새 핸들러 파일 생성
2. `BaseHandler` 상속
3. `handle_goal()`, `handle_cancel()`, `execute()` 구현
4. `controller_node.py`에 ActionServer 등록

```python
# action_handlers/new_handler.py
from .base_handler import BaseHandler

class NewHandler(BaseHandler):
    def handle_goal(self, goal_request):
        return GoalResponse.ACCEPT

    def handle_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        # 실제 로직 구현
        result = NewAction.Result()
        result.success = True
        goal_handle.succeed()
        return result
```

### stub을 실제 구현으로 교체

`clean_wall_handler.py`, `move_fish_handler.py`의 `execute()` 메서드 내용을 실제 로직으로 교체:

- **CleanWall**: rail_robot 제어 로직
- **MoveFish**: 
  1. source pool로 이동
  2. 물고기 흡입 (suction)
  3. target pool로 이동
  4. 물고기 방류
  5. 반복

## 관련 문서

- [water_ws_interface_guide.md](../water_ws_interface_guide.md) - 인터페이스 네이밍 규칙
- [water_ws_planner_controller.md](../water_ws_planner_controller.md) - 전체 아키텍처 설계
