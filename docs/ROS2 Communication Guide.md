# ROS2 Communication Guide

> AquaSweep ROS2 패키지, 인터페이스, 통신 Entity 통합 문서입니다. 작업하실 때 꼭 필독해주세요.
> 

---

---

## 1. 패키지 구조

| 패키지 | 설명 | 비고 |
| --- | --- | --- |
| **aqua_interfaces** | 커스텀 메시지 및 액션 정의 | msg/, action/ |
| **aqua_detection** | Isaac Cam 이미지 구독 → Detection 결과 발행 |  |
| **aqua_controller** | 로봇 제어 (저수준 제어, 궤적/속도 계산, cmd_vel 발행) | Action Server |
| **aqua_planner** | 고수준 제어 (작업 스케줄링, Action Client) | optional, 확장용 |
| **aqua_dashboard** | Isaac 대시보드에 필요한 정보 수합 & 전달 |  |

### 아키텍처 다이어그램

![image.png](ROS2%20Communication%20Guide/image.png)

---

## 2. 네이밍 규칙

### 2.1 Entity 네이밍

| 항목 | 네이밍 패턴 | 예시 |
| --- | --- | --- |
| 풀 | `pool_{id}` | `pool_1`, `pool_2` |
| 수중 로봇 | `under_robot_{id}` | `under_robot_1` |
| 레일 로봇 | `rail_robot_{id}` | `rail_robot_1` |
| 수중 카메라 | `under_cam_{id}` | `under_cam_1` |
| 상단 카메라 | `top_cam_{id}` | `top_cam_1` |

### 2.2 Prim Path 구조 (Isaac Sim)

```
#### 확인 필요 #####

world/
├── ground/
├── pools/
│   └── pool_1/
│       ├── water/
│       ├── under_robot_1/
│       │   ├── base_link/
│       │   └── under_cam_1/
│       └── top_cam_1/
└── rails/
    └── rail_1/
        └── rail_robot_1/
```

---

## 3. 인터페이스 정의

### 3.1 Built-in Messages

### geometry_msgs/msg/Twist

**Topic:** `/under_robot_1/cmd_vel`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| linear | Vector3 | 선속도 (m/s) - x: 전진/후진, y: 좌우, z: 상하 |
| angular | Vector3 | 각속도 (rad/s) - x: roll, y: pitch, z: **yaw (핵심)** |

---

### sensor_msgs/msg/JointState

**Topics:** `/under_robot_1/joint_state`, `/rail_robot_1/joint_state`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| name | string[] | joint 이름 배열 (예: `["left_wheel", "right_wheel"]`) |
| position | float64[] | 각 joint 위치 (rad 또는 m) |
| velocity | float64[] | 각 joint 속도 (rad/s 또는 m/s) |
| effort | float64[] | 각 joint 토크/힘 (Nm 또는 N) — **외력·부하 측정** |

---

### sensor_msgs/msg/Image

**Topics:**

- `/pool_1/under_img_raw` - 수중 카메라 원본
- `/pool_1/under_img_det` - 수중 카메라 Detection 결과
- `/pool_1/top_img_raw` - 상단 카메라 원본
- `/pool_1/top_img_det` - 상단 카메라 Detection 결과

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| height | uint32 | 이미지 높이 (px) |
| width | uint32 | 이미지 너비 (px) |
| encoding | string | `"rgb8"`, `"bgr8"`, `"mono8"`, `"16UC1"` 등 |
| is_bigendian | uint8 | 0 = little endian |
| step | uint32 | 한 row의 바이트 길이 |
| data | uint8[] | 이미지 데이터 (1D 배열) |

---

### sensor_msgs/msg/Imu

**Topic:** `/under_robot_1/imu`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| orientation | Quaternion | 자세 (x, y, z, w) |
| orientation_covariance | float64[9] | 자세 공분산 |
| angular_velocity | Vector3 | 각속도 (rad/s) |
| angular_velocity_covariance | float64[9] | 각속도 공분산 |
| linear_acceleration | Vector3 | 선가속도 (m/s²) |
| linear_acceleration_covariance | float64[9] | 선가속도 공분산 |

---

### nav_msgs/msg/Odometry

**Topic:** `/under_robot_1/odom`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| child_frame_id | string | `"base_link"` (로봇 본체 프레임) |
| pose | PoseWithCovariance | 위치 + 방향 + 공분산 (**position.x, y, orientation.z** 핵심) |
| twist | TwistWithCovariance | 현재 속도 + 공분산 (**linear.x, angular.z** 핵심) |

---

### nav_msgs/msg/Path

**Topic:** `/under_robot_1/planned_path` *(planner 고도화 시 사용)*

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| poses | PoseStamped[] | 경로상의 waypoint 배열 |

---

### std_srvs/Trigger

**Services:**

- `/planner/start` - 전체 청소 시작 (fish_count == 0인 풀에 CleanWall → CleanFloor 순차 실행)
- `/planner/pause` - 대시보드 전체 일시 정지
- `/{pool_id}/start_clean_floor` - 개별 풀 바닥 청소만 시작 (CleanFloor만)
- `/{pool_id}/start_clean_wall` - 개별 풀 벽면+바닥 청소 시작 (CleanWall → CleanFloor 순차)
- `/sturgeon/pause` - 철갑상어 애니메이션 일시 정지 (청소 시작 시 자동 호출)
- `/sturgeon/resume` - 철갑상어 애니메이션 재개 (청소 완료 시 자동 호출)
- `/{pool_id}/activate_robot` - 로봇 ActionGraph 생성 (청소 시작 시 자동 호출)
- `/{pool_id}/deactivate_robot` - 로봇 ActionGraph 제거

**Request**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| (없음) | ㅡ | 빈 요청, 파라미터 없이 단순 트리거 |

**Response**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| success | bool | 요청 성공 여부 |
| message | string | 결과 메시지 (성공/실패 이유) |

---

### 3.2 Custom Messages (aqua_interfaces/msg/)

### RobotStatus

**Topic:** `/under_robot_1/status`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| state | uint8 | 상태 코드: `IDLE=0`, `RUNNING=1`, `PAUSED=2`, `DISCHARGED=3` |
| battery_level | float32 | 배터리 잔량 (0.0 ~ 1.0) |
| collision_force | float32 | 충돌 힘 (N) |

---

### PoolStatus

**Topic:** `/pool_1/status`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| pollution_level | float | 오염 수준 |
| fish_type | string | 물고기 종류 |
| fish_count | int32 | 물고기 수 |
| fish_count_suspicious | int32 | 의심 물고기 수 |

---

### PoolPhysicalVariables

**Topic:** `/pool_1/physical_variables`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| buoyancy | float | 부력 |
| drag | float | 항력 |
| lift | float | 양력 |
| viscosity | float | 점성 |

---

### 3.3 Custom Actions (aqua_interfaces/action/)

| Action | Topic | 설명 |
| --- | --- | --- |
| **CleanFloor** | `/pool_1/clean_floor` | 바닥 청소 |
| **CleanWall** | `/pool_1/clean_wall` | 벽면 청소 |
| **MoveFish** | `/pool_1/move_fish` | 물고기 이동 |

---

## 4. 통신 Entity 정리

> **Topic**: 1:N 통신 (Publisher → Subscribers)
> 
> 
> **Action**: 1:1 통신 (Client → Server)
> 

### 4.1 Topics

| Topic | Publisher | Subscribers | 우선순위 |
| --- | --- | --- | --- |
| `/pool_1/status` | detection node  | dashboard, planner | **1차 필수** |
| `/pool_1/under_img_raw` | `under_cam_ext/` | detection | **1차 필수** |
| `/pool_1/under_img_det` | detection node | dashboard | **1차 필수** |
| `/pool_1/top_img_raw` | `top_cam_ext/` | detection | **1차 필수** |
| `/pool_1/physical_variables`  | `water_tank_env/` or `underwater_robot/`  
**** 확인 필요 **** | controller | **1차 필수** |
| `/under_robot_1/status` | `underwater_robot_env/` | dashboard, planner | **1차 필수** |
| `/under_robot_1/cmd_vel` | `underwater_robot_ext/` (내부 플래너) | `underwater_robot_ext/` | 내부 사용 |
| `/under_robot_1/joint_state` | `underwater_robot_ext/` | controller node | 확장 |
| `/under_robot_1/planned_path` | controller node | `underwater_robot_env/` | 확장 |
| `/under_robot_1/imu` | `underwater_robot_env/` | controller | 확장 |
| `/under_robot_1/odom` | `underwater_robot_env/` | controller | 확장 |

### 4.2 Services

| Service | Client | Server | 우선 순위 |
| --- | --- | --- | --- |
| `/planner/start` | dashboard node | planner node | **1차 필수** |
| `/planner/pause` | dashboard node | planner node | **1차 필수** |
| `/{pool_id}/start_clean_floor` | dashboard node | planner node | **1차 필수** |
| `/{pool_id}/start_clean_wall` | dashboard node | planner node | **1차 필수** |
| `/sturgeon/pause` | planner node | `aquasweep_ext` (Isaac Sim) | **1차 필수** |
| `/sturgeon/resume` | planner node | `aquasweep_ext` (Isaac Sim) | **1차 필수** |
| `/{pool_id}/activate_robot` | planner node | `aquasweep_ext` (Isaac Sim) | **1차 필수** |
| `/{pool_id}/deactivate_robot` | planner node | `aquasweep_ext` (Isaac Sim) | 확장 |

> **청소 시퀀스 흐름 (CleanWall → CleanFloor):**
> - `/planner/start` 호출 시 fish_count == 0인 풀에 대해 CleanWall 먼저 시작
> - CleanWall 완료 후 자동으로 CleanFloor 시작
> - 모든 풀 청소 완료 시 global_task_active = False

> **철갑상어 애니메이션 제어 흐름:**
> - 청소 시작 시 (`/planner/start` 또는 `/{pool_id}/start_clean_floor`) → planner가 `/sturgeon/pause` 자동 호출
> - 모든 청소 완료 시 → planner가 `/sturgeon/resume` 자동 호출
> - 성능 최적화 목적: 청소 중 불필요한 철갑상어 transform 업데이트 (~35 USD Set() calls/step) 중단

> **로봇 활성화 제어 흐름:**
> - 청소 시작 시 → planner가 `/{pool_id}/activate_robot` 자동 호출
> - ActionGraph 생성: cmd_vel 토픽 구독 + DifferentialController 연결
> - 개별 풀 로봇만 활성화하여 불필요한 리소스 사용 방지

### 4.3 Actions

| Action | Client | Server | 구현 상태 |
| --- | --- | --- | --- |
| `/{pool_id}/clean_floor` | planner node | controller node | ✅ 실제 구현 |
| `/{pool_id}/clean_wall` | planner node | controller node | ✅ 실제 구현 |
| `/{pool_id}/move_fish` | planner node | controller node | stub |

### 4.4 모션 제어 인터페이스

> Isaac Sim 내부 플래너(SpiralPlanner)를 사용하는 서비스 기반 아키텍처입니다.
> Controller는 Isaac Sim에 모션 시작/정지 서비스를 호출하고, motion_status 토픽으로 진행상황을 모니터링합니다.

#### Services (Controller → Isaac Sim)

> **중요**: Isaac Sim 서비스는 `/isaac/` prefix를 사용하여 Planner 서비스와 구분됩니다.

| Service | 타입 | 설명 |
| --- | --- | --- |
| `/{pool_id}/isaac/start_clean_floor` | StartMotion | 바닥 청소 시작 (파라미터 포함) |
| `/{pool_id}/isaac/stop_clean_floor` | StopMotion | 바닥 청소 정지 |
| `/{pool_id}/isaac/pause_clean_floor` | PauseMotion | 바닥 청소 일시정지 |
| `/{pool_id}/isaac/resume_clean_floor` | ResumeMotion | 바닥 청소 재개 |
| `/{pool_id}/isaac/start_clean_wall` | StartMotion | 벽면 청소 시작 |
| `/{pool_id}/isaac/stop_clean_wall` | StopMotion | 벽면 청소 정지 |
| `/{pool_id}/isaac/pause_clean_wall` | PauseMotion | 벽면 청소 일시정지 |
| `/{pool_id}/isaac/resume_clean_wall` | ResumeMotion | 벽면 청소 재개 |

#### Topics (Isaac Sim → Controller)

| Topic | 타입 | 설명 |
| --- | --- | --- |
| `/{pool_id}/clean_floor_status` | MotionStatus | 바닥 청소 진행상황 (state, progress, phase) |
| `/{pool_id}/clean_wall_status` | MotionStatus | 벽면 청소 진행상황 |

---

## 5. 패키지 상세 구조

### 5.1 aqua_interfaces

```
aqua_interfaces/
├── action/
│   ├── CleanFloor.action
│   ├── CleanWall.action
│   └── MoveFish.action
├── msg/
│   ├── RobotStatus.msg               # 로봇 상태 (state: uint8 상수)
│   ├── PoolStatus.msg
│   ├── PoolPhysicalVariables.msg
│   ├── MotionParams.msg              # 모션 파라미터 (SpiralPlanner용)
│   └── MotionStatus.msg              # 모션 상태 (state: uint8 상수)
└── srv/
    ├── StartMotion.srv               # 모션 시작 (MotionParams 포함)
    ├── StopMotion.srv                # 모션 정지
    ├── PauseMotion.srv               # 모션 일시정지
    └── ResumeMotion.srv              # 모션 재개
```

**MotionStatus 상태 코드:**
| 상수 | 값 | 설명 |
| --- | --- | --- |
| IDLE | 0 | 대기 중 |
| RUNNING | 1 | 모션 실행 중 |
| PAUSED | 2 | 일시정지 |
| DONE | 3 | 완료 |

### 5.2 aqua_planner

```
aqua_planner/aqua_planner/
├── __init__.py                  # 패키지 초기화
├── planner_node.py              # 메인 노드 + 서비스
├── pool_state.py                # 풀 상태 관리 (CleaningPhase enum)
├── cleaning_orchestrator.py     # CleanWall → CleanFloor 시퀀스 오케스트레이션
├── task_executor.py             # Action Client 관리
└── mockup_vision_publisher.py   # 테스트용 풀 상태 발행
```

**Services:**

- `/planner/start` - CleanWall → CleanFloor 순차 Action Goal 전송 (fish_count == 0인 풀)
- `/planner/pause` - 현재 작업 취소
- `/{pool_id}/start_clean_floor` - 개별 풀 CleanFloor만 시작
- `/{pool_id}/start_clean_wall` - 개별 풀 CleanWall → CleanFloor 순차 시작

### 5.3 aqua_controller

> Isaac Sim 내부 플래너와 연동하는 서비스 기반 아키텍처입니다.
> Controller는 Action Server를 제공하며, Isaac Sim에 서비스 호출로 모션을 요청합니다.

```
aqua_controller/aqua_controller/
├── controller_node.py           # 메인 노드 + Action Servers
├── action_handlers/
│   ├── __init__.py
│   ├── base_handler.py          # 추상 기본 클래스
│   ├── clean_floor_handler.py   # ✅ 실제 구현 (Isaac Sim 서비스 연동)
│   ├── clean_wall_handler.py    # ✅ 실제 구현 (Isaac Sim 서비스 연동)
│   └── move_fish_handler.py     # stub
├── mockup_controller_server.py  # 테스트용 Action Server
└── mockup_robot_status.py       # 테스트용 로봇 상태 발행
```

**Action Server 구현 상태:**

| Handler | 상태 | 설명 |
| --- | --- | --- |
| CleanFloorHandler | ✅ 실제 구현 | Isaac Sim start_clean_floor 서비스 호출 + motion_status 모니터링 |
| CleanWallHandler | ✅ 실제 구현 | Isaac Sim start_clean_wall 서비스 호출 + motion_status 모니터링 |
| MoveFishHandler | stub | 요청 수락 → 바로 성공 반환 |

---

## 6. 빠른 참조

> 아래 내용은 github version 에 따라 변할 수 있으니 가볍게만 참고
> 

### 테스트 명령어

```bash
# 빌드
cd ~/AquaSweep/water_ws
colcon build --packages-select aqua_interfaces aqua_planner aqua_controller
source install/setup.bash

# Mockup Controller 실행
ros2 run aqua_controller mockup_controller_server --ros-args -p pool_id:=pool_1

# 실제 Controller 실행
ros2 run aqua_controller controller_node --ros-args \\
    -p robot_name:=under_robot_1 \\
    -p pool_id:=pool_1

# Planner 실행
ros2 run aqua_planner planner_node --ros-args -p pool_id:=pool_1

# Action 직접 호출
ros2 action send_goal /pool_1/clean_floor aqua_interfaces/action/CleanFloor "{}" --feedback

# 상태 확인
ros2 action list
ros2 topic list
ros2 service list
ros2 topic echo /under_robot_1/cmd_vel
```