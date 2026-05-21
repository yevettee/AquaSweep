# ROS2 Planner-Controller 아키텍처

## 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Planner Node                               │
│  (aqua_planner/planner_node.py)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  TaskScheduler   │  │  VisionAnalyzer  │  │  TaskExecutor    │       │
│  │  ──────────────  │  │  ──────────────  │  │  ──────────────  │       │
│  │  - 작업 우선순위    │  │  - TopView 카메라 │  │  - Action Client │       │
│  │  - 의존성 관리      │  │    이미지 분석     │  │  - 태스크 실행     │       │
│  │  - 상태 머신       │  │  - 탱크 상태 판단│  │  - 결과 처리          │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ROS2 Action (MoveFish, CleanFloor, CleanWall)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                             Controller Node                             │
│  (aqua_controller/controller_node.py)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │  ActionServer    │  │  MotionPlanner   │  │  IsaacSimBridge  │       │
│  │  ─────────────   │  │  ─────────────   │  │  ─────────────   │       │
│  │  - MoveFish      │  │  - 경로 생성       │  │  - Prim 제어      │       │
│  │  - CleanFloor    │  │  - Waypoint 관리  │  │  - cmd_vel 발행   │       │
│  │  - CleanWall     │  │  - 충돌 회피       │  │  - 상태 피드백     │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 인터페이스 정의 (aqua_interfaces)

### MoveFish.action (신규)

```
# Goal
string source_tank      # "tank_1"
string target_tank      # "tank_2"
int32 fish_count        # 옮길 물고기 수 (-1 = all)
---
# Result
bool success
int32 fish_moved
string message
---
# Feedback
uint8 phase             # 0=moving_to_source, 1=picking, 2=moving_to_target, 3=placing
float32 progress        # 0.0 ~ 1.0
int32 fish_picked_so_far
```

### CleanFloor.action (수정)

```
# Goal
string tank_id          # "tank_1"
---
# Result
bool success
float32 area_cleaned
---
# Feedback
float32 progress
string current_zone     # "wall_north", "floor_center" 등
```

---

## 2. Planner 노드 기능 단위

### 디렉토리 구조

```
aqua_planner/aqua_planner/
├── planner_node.py          # 메인 노드 (ROS2 lifecycle)
├── task_scheduler.py        # 태스크 스케줄링 로직
├── vision_analyzer.py       # 카메라 데이터 분석
├── task_executor.py         # Action Client 관리
└── state_machine.py         # 전체 상태 관리
```

### 2.1 TaskScheduler

```python
class TaskScheduler:
    """작업 계획 및 우선순위 관리"""

    def create_fish_transfer_plan(self, tank_status: dict) -> List[Task]:
        """물고기 이동 계획 생성
        - Input: 각 탱크의 물고기 상태
        - Output: 순서화된 MoveFish Task 리스트
        """

    def create_cleaning_plan(self, empty_tanks: List[str]) -> List[Task]:
        """청소 계획 생성
        - Input: 비어있는 탱크 목록
        - Output: CleanFloor + CleanWall Task 리스트
        """

    def get_next_task(self) -> Optional[Task]:
        """다음 실행할 태스크 반환 (의존성 고려)"""
```

### 2.2 VisionAnalyzer

```python
class VisionAnalyzer:
    """Top View 카메라 기반 상태 분석"""

    def __init__(self):
        self.tank_subscribers = {}  # 각 탱크별 카메라 구독

    def get_tank_fish_status(self, tank_id: str) -> TankFishStatus:
        """탱크별 물고기 수/위치 분석"""

    def is_tank_empty(self, tank_id: str) -> bool:
        """탱크가 비어있는지 확인 (청소 가능 여부)"""

    def get_transfer_requirements(self) -> List[TransferRequirement]:
        """어떤 탱크에서 어디로 물고기 이동이 필요한지"""
```

### 2.3 TaskExecutor

```python
class TaskExecutor:
    """Controller와 통신하여 태스크 실행"""

    def __init__(self):
        self.move_fish_client = ActionClient(MoveFish)
        self.clean_floor_client = ActionClient(CleanFloor)
        self.clean_wall_client = ActionClient(CleanWall)

    async def execute_move_fish(self, task: MoveFishTask) -> bool:
        """
        until finished:
            tank_src pick → tank_dst place
        """

    async def execute_clean_floor(self, task: CleanFloorTask) -> bool:
        """바닥 청소 실행 및 완료 대기"""
```

---

## 3. Controller 노드 기능 단위

### 디렉토리 구조

```
aqua_controller/aqua_controller/
├── controller_node.py       # 메인 노드 (Action Servers)
├── action_handlers/
│   ├── move_fish_handler.py
│   ├── clean_floor_handler.py
│   └── clean_wall_handler.py
├── motion_planner.py        # 경로 계획
├── isaac_bridge.py          # Isaac Sim 연동
└── completion_checker.py    # 완료 조건 확인
```

### 3.1 ActionHandler 패턴

```python
class MoveFishHandler:
    """MoveFish 액션 처리"""

    class Phase(Enum):
        MOVE_TO_READY = 0      # tank_src ready 위치로 이동
        PICK_FISH = 1          # 물고기 포획
        MOVE_TO_TARGET = 2     # tank_dst로 이동
        PLACE_FISH = 3         # 물고기 방류
        CHECK_REMAINING = 4    # 남은 물고기 확인

    async def execute(self, goal: MoveFish.Goal):
        # 1. tank_src ready 위치로 이동
        await self.move_to_position(self.get_ready_position(goal.source_tank))

        # 2. pick-place 반복
        while not self.is_transfer_complete(goal):
            self.publish_feedback(phase=Phase.PICK_FISH, progress=...)
            await self.pick_fish(goal.source_tank)

            self.publish_feedback(phase=Phase.MOVE_TO_TARGET, progress=...)
            await self.move_to_position(self.get_ready_position(goal.target_tank))

            self.publish_feedback(phase=Phase.PLACE_FISH, progress=...)
            await self.place_fish(goal.target_tank)

            # 다시 source로 복귀
            await self.move_to_position(self.get_ready_position(goal.source_tank))
```

### 3.2 IsaacBridge

```python
class IsaacBridge:
    """Isaac Sim Prim 제어"""

    def __init__(self):
        self.cmd_vel_pub = Publisher('/cmd_vel', Twist)
        self.suction_client = ...  # 흡입 시스템 서비스

    def send_cmd_vel(self, linear: Vector3, angular: Vector3):
        """로봇 이동 명령"""

    def activate_suction(self, on: bool):
        """흡입 장치 제어"""

    def get_robot_pose(self) -> Pose:
        """현재 로봇 위치 (Isaac Sim에서)"""
```

### 3.3 CompletionChecker

```python
class CompletionChecker:
    """액션 완료 조건 확인"""

    def is_move_complete(self, target_pose: Pose, threshold: float) -> bool:
        """목표 위치 도달 여부"""

    def is_fish_picked(self, suction_status: SuctionStatus) -> bool:
        """물고기 포획 성공 여부"""

    def is_tank_cleaned(self, tank_id: str, coverage_map: CoverageMap) -> bool:
        """청소 완료 여부 (coverage 기반)"""
```

---

## 4. ROS2 토픽/서비스/액션 구조

```
Topics:
  /tank_{n}/camera/image_raw     # Top view 카메라
  /tank_{n}/status               # TankStatus.msg
  /robot/status                  # RobotStatus.msg
  /cmd_vel                       # 로봇 이동 명령

Actions:
  /aqua/move_fish                # MoveFish.action
  /aqua/clean_floor              # CleanFloor.action
  /aqua/clean_wall               # CleanWall.action

Services:
  /planner/start                 # std_srvs/Trigger
  /planner/pause                 # std_srvs/Trigger
  /planner/get_status            # 현재 실행 상태
```

---

## 5. 전체 실행 흐름

```
User clicks "시작"
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Planner: VisionAnalyzer.analyze_all_tanks()    │
│  → fish transfer requirements 생성              │
│  → empty tanks 목록 생성                        │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Planner: TaskScheduler.create_master_plan()    │
│  → [MoveFish(1→2), MoveFish(3→2), ...]         │
│  → [CleanFloor(1), CleanWall(1), ...]          │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Planner: TaskExecutor.execute_next()           │
│  → Action Goal 전송 (MoveFish Goal)             │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Controller: MoveFishHandler.execute()          │
│  → IsaacBridge로 실제 명령 전송                 │
│  → Feedback 발행 (phase, progress)              │
│  → 완료 시 Result 반환                          │
└─────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Planner: 다음 태스크로 진행                    │
│  → 모든 태스크 완료 시 종료                     │
└─────────────────────────────────────────────────┘
```

---

## 6. 핵심 설계 원칙

1. **Planner는 "무엇을"**, **Controller는 "어떻게"** - 역할 분리가 명확
2. **Action 기반 통신** - Goal/Feedback/Result로 진행 상태 추적 가능
3. **Phase 기반 상태 관리** - 각 액션 내에서 세분화된 진행 단계 관리
4. **CompletionChecker 분리** - 완료 조건 로직을 독립적으로 테스트 가능

## 7. 현재 controller_pkg 와의 호환성

| **현재 controller_pkg** | **계획된 aqua_controller** | **호환성** |
| --- | --- | --- |
| `UnderwaterRobotControllerNode` | `ControllerNode` + `CleanFloorHandler` | ✅ 통합 가능 |
| `SpiralPlanner` | `MotionPlanner` | ✅ 그대로 사용 |
| `_pub.publish(Twist)` | `IsaacBridge.send_cmd_vel()` | ✅ 추출 가능 |
| `start()/stop()` | `ActionServer goal handler` | ✅ 이미 준비됨 |